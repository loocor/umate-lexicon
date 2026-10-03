#!/usr/bin/env python3
"""LLM classification of visible review-tier rows via magpie deepseek flash.

Targets rows with status='review' AND rank>=500 (user-visible in candidate
tray). Classifies each as real-word, fragment, or variant-dup. Fragment and
variant-dup rows are later downgraded to rejected. Checkpoint JSONL for
resumability.

Usage:
    python scripts/llm_classify_review.py [--workers 4] [--batch 100] [--dry-run] [--limit N]
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
MODEL = "workbuddy/deepseek-v4.1-flash"
CHECKPOINT = Path("data/eval/llm-classify-review.jsonl")
CATEGORIES = {"real-word", "fragment", "variant-dup"}

SYSTEM = (
    "You are a Chinese IME lexicon reviewer. Given numbered Chinese entries "
    "(surface only, no pinyin), classify each as one of:\n"
    "- real-word: a genuine standalone Chinese word or phrase a user would type\n"
    "- fragment: an incomplete/partial string with no standalone lexical meaning "
    "(e.g. a truncated phrase, a concatenation that reads like filler)\n"
    "- variant-dup: a near-duplicate of another entry in this batch (same meaning, "
    "redundant form; e.g. repeated particles, trivial variants)\n"
    'Reply ONLY with JSON lines, one per entry: {"n":<number>,"v":"real-word|fragment|variant-dup","d":"<10-20 char reason>"}\n'
    "No markdown fences, no extra text."
)


def fetch_rows() -> list[tuple[str, str]]:
    db = sqlite3.connect("data/store/lemmas.sqlite")
    rows = db.execute(
        "SELECT surface, pinyin_plain FROM lemmas "
        "WHERE status='review' AND rank>=500 ORDER BY rank DESC"
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


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


def call_llm(batch: list[tuple[int, str, str]]) -> str:
    lines = "\n".join(f"{n}. {s} ({p})" for n, s, p in batch)
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
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"] or ""


def parse_results(content: str, batch: list[tuple[int, str, str]]) -> list[dict]:
    n_to_surface = {n: (s, p) for n, s, p in batch}
    results = []
    for line in strip_fences(content).split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            n = int(rec.get("n"))
            v = rec.get("v")
            if v not in CATEGORIES or n not in n_to_surface:
                continue
            s, p = n_to_surface[n]
            results.append({"s": s, "p": p, "v": v, "d": rec.get("d", "")})
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
    return results


def process_batch(batch: list[tuple[int, str, str]]) -> list[dict]:
    for attempt in range(3):
        try:
            content = call_llm(batch)
            results = parse_results(content, batch)
            if results:
                return results
        except Exception as e:
            if attempt == 2:
                print(f"  batch failed after 3 retries: {e}", file=sys.stderr)
            time.sleep(2 ** (attempt + 1))
    return []


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--batch", type=int, default=100)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    all_rows = fetch_rows()
    if args.limit:
        all_rows = all_rows[: args.limit]
    done = load_done()
    remaining = [(n, s, p) for n, (s, p) in enumerate(all_rows) if s not in done]
    print(f"Total: {len(all_rows)}, done: {len(done)}, remaining: {len(remaining)}")
    if not remaining:
        print("All rows already classified.")
        return
    if args.dry_run:
        print(f"[dry-run] would process {len(remaining)} rows")
        return

    batch_size = args.batch
    batches = [remaining[i:i+batch_size] for i in range(0, len(remaining), batch_size)]
    print(f"Batches: {len(batches)}, workers: {args.workers}")

    total = 0
    lock = threading.Lock()
    t0 = time.time()
    with open(CHECKPOINT, "a") as ckpt:
        def run_batch(b):
            nonlocal total
            start = time.time()
            results = process_batch(b)
            with lock:
                for rec in results:
                    ckpt.write(json.dumps(rec, ensure_ascii=False) + "\n")
                ckpt.flush()
                total += len(results)
            rejected = sum(1 for r in results if r["v"] != "real-word")
            return len(results), rejected, time.time() - start

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(run_batch, b): i for i, b in enumerate(batches)}
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    n, rej, el = future.result()
                    pct = total * 100 // max(1, len(remaining))
                    print(f"  batch {idx+1}/{len(batches)}: {n} rows ({rej} non-real-word) {el:.1f}s [{pct}%]")
                except Exception as e:
                    print(f"  batch {idx+1} error: {e}", file=sys.stderr)
    print(f"\nDone: {total} rows in {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
