#!/usr/bin/env python3
"""LLM re-verification of untrusted_reading rows via magpie deepseek pro.

Targets rows with 'untrusted_reading' in flags. For each entry LLM judges
the current plain pinyin as correct / incorrect (suggests fix) / variant
(alternate reading). Suggested fixes are post-validated: every per-char
syllable must exist in the store's known pinyin set for that char, otherwise
the row stays blocked for manual review.

Usage:
    python scripts/llm_verify_reading.py [--workers 2] [--batch 30] [--dry-run] [--limit N]
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

API = "http://127.0.0.1:3425/v1/chat/completions"
KEY = "magpie"
MODEL = "workbuddy/deepseek-v4-pro"
CHECKPOINT = Path("data/eval/llm-verify-reading.jsonl")
VERDICTS = {"correct", "incorrect", "variant"}
_HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]"
                  r"|[\U00020000-\U0002a6df\U0002a700-\U0002ebef]")

SYSTEM = (
    "You are a Mandarin Putonghua pinyin verifier. Each entry is 'surface|plain_pinyin' "
    "(no tones, u-umlaut written as v). Judge whether the plain pinyin matches standard "
    "Putonghua readings (XianDai HanYu CiDian convention). Polyphone words: pick the "
    "reading the word actually uses.\n"
    "Verdicts:\n"
    "- correct: current plain pinyin is standard for this word\n"
    "- incorrect: current plain pinyin is wrong; give corrected plain pinyin\n"
    "- variant: an acceptable alternate reading, not an error\n"
    'Reply ONLY with JSON lines: {"s":"surface","v":"correct|incorrect|variant","c":"corrected_plain_pinyin_or_empty","d":"short reason"}\n'
    "Rules: one syllable per hanzi, same word length. No markdown fences."
)


def fetch_rows() -> list[tuple[str, str]]:
    db = sqlite3.connect("data/store/lemmas.sqlite")
    rows = db.execute(
        "SELECT surface, pinyin_plain FROM lemmas "
        "WHERE flags LIKE '%untrusted_reading%' ORDER BY rank ASC"
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def load_known_pinyin() -> dict[str, set[str]]:
    """Build char -> set of known plain pinyin from store."""
    db = sqlite3.connect("data/store/lemmas.sqlite")
    known: dict[str, set[str]] = {}
    for surface, plain in db.execute(
        "SELECT surface, pinyin_plain FROM lemmas WHERE LENGTH(surface)=1 AND pinyin_plain IS NOT NULL"
    ):
        known.setdefault(surface, set()).add(plain)
    return known


def load_done() -> set[str]:
    done = set()
    if CHECKPOINT.exists():
        for line in CHECKPOINT.read_text().splitlines():
            if line.strip():
                try:
                    rec = json.loads(line)
                    done.add(rec["s"])
                except (json.JSONDecodeError, KeyError):
                    pass
    return done


def strip_fences(text: str) -> str:
    text = text.strip()
    m = re.match(r"^```(?:json)?\s*\n(.*?)\n```\s*$", text, re.DOTALL)
    return m.group(1).strip() if m else text


def call_llm(batch: list[tuple[str, str]]) -> str:
    lines = "\n".join(f"{s}|{p}" for s, p in batch)
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Entries:\n{lines}"},
        ],
        "temperature": 0,
        "max_tokens": 8000,
    }).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=240) as resp:
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"] or ""


def validate_correction(surface: str, corrected: str, known: dict[str, set[str]]) -> str | None:
    """Return a reason string if correction is invalid, else None."""
    if not corrected:
        return "empty corrected pinyin"
    corrected = corrected.strip().lower().replace("  ", " ")
    syllables = corrected.split()
    chars = [ch for ch in surface if _HAN.match(ch)]
    if len(syllables) != len(chars):
        return f"syllable count {len(syllables)} != hanzi count {len(chars)}"
    for ch, syl in zip(chars, syllables):
        if ch not in known:
            return f"no known pinyin for char {ch!r}"
        if syl not in known[ch]:
            return f"syllable {syl!r} not known for char {ch!r} (have: {sorted(known[ch])})"
    return None


def parse_results(content: str, known: dict[str, set[str]]) -> list[dict]:
    results = []
    for line in strip_fences(content).split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            s = rec.get("s")
            v = rec.get("v")
            if v not in VERDICTS or not s:
                continue
            corrected = (rec.get("c") or "").strip()
            block_reason = None
            if v == "incorrect":
                block_reason = validate_correction(s, corrected, known)
            results.append({
                "s": s,
                "v": v,
                "c": corrected,
                "d": rec.get("d", ""),
                "blocked": block_reason,
            })
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    return results


def process_batch(batch: list[tuple[str, str]], known: dict[str, set[str]]) -> list[dict]:
    for attempt in range(3):
        try:
            content = call_llm(batch)
            results = parse_results(content, known)
            if results:
                return results
        except Exception as e:
            if attempt == 2:
                print(f"  batch failed after 3 retries: {e}", file=sys.stderr)
            time.sleep(2 ** (attempt + 1))
    return []


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--batch", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    all_rows = fetch_rows()
    if args.limit:
        all_rows = all_rows[: args.limit]
    known = load_known_pinyin()
    done = load_done()
    remaining = [(s, p) for s, p in all_rows if s not in done]
    print(f"Total: {len(all_rows)}, done: {len(done)}, remaining: {len(remaining)}")
    if not remaining:
        print("All rows already verified.")
        return
    if args.dry_run:
        print(f"[dry-run] would process {len(remaining)} rows in batches of {args.batch}")
        return

    batches = [remaining[i:i+args.batch] for i in range(0, len(remaining), args.batch)]
    print(f"Batches: {len(batches)}, workers: {args.workers}")

    total = 0
    blocked = 0
    fixed = 0
    lock = threading.Lock()
    t0 = time.time()
    with open(CHECKPOINT, "a") as ckpt:
        def run_batch(b):
            nonlocal total, blocked, fixed
            start = time.time()
            results = process_batch(b, known)
            with lock:
                for rec in results:
                    ckpt.write(json.dumps(rec, ensure_ascii=False) + "\n")
                ckpt.flush()
                total += len(results)
                if rec_ok := [r for r in results if r["v"] == "incorrect"]:
                    fixed += sum(1 for r in rec_ok if not r["blocked"])
                    blocked += sum(1 for r in rec_ok if r["blocked"])
            return len(results), time.time() - start

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(run_batch, b): i for i, b in enumerate(batches)}
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    n, el = future.result()
                    pct = total * 100 // max(1, len(remaining))
                    print(f"  batch {idx+1}/{len(batches)}: {n} rows {el:.1f}s [{pct}%] fixed={fixed} blocked={blocked}")
                except Exception as e:
                    print(f"  batch {idx+1} error: {e}", file=sys.stderr)
    print(f"\nDone: {total} rows in {(time.time()-t0)/60:.1f} min; fixed={fixed} blocked={blocked}")


if __name__ == "__main__":
    main()
