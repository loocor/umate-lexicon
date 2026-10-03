#!/usr/bin/env python3
"""Second-pass atomicity verdict for long real-word entries.

Input: data/eval/llm-classify-review.jsonl rows with v=real-word and a
surface of 5+ hanzi. Classifies each as:

- atomic: fixed expression, saying, term, or a proper name whose full
  form is the conventional unique string (多年媳妇熬成婆)
- composable: a mechanical concatenation of shorter common words or
  name parts that users reach by typing the pieces in sequence
  (吉林省公安厅 = 吉林省 + 公安厅)

Checkpoint JSONL for resumability. Application policy lives in the
postprocess triage step, not here.

Usage:
    python scripts/llm_classify_atomicity.py [--workers 6] [--batch 150] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

API = "http://127.0.0.1:3425/v1/chat/completions"
KEY = "magpie"
MODEL = "workbuddy/deepseek-v4.1-flash"
REVIEW_CHECKPOINT = Path("data/eval/llm-classify-review.jsonl")
CHECKPOINT = Path("data/eval/llm-classify-atomicity.jsonl")
CATEGORIES = {"atomic", "composable"}

SYSTEM = (
    "You are a Chinese IME lexicon curator. For each numbered multi-character "
    "Chinese entry, decide whether it deserves to exist as ONE dictionary entry:\n"
    "- atomic: a fixed saying/idiom/proverb, a technical term, or a proper name "
    "whose full form is the conventional unique string; decomposing it loses the "
    "meaning or the standard form (e.g. 多年媳妇熬成婆)\n"
    "- composable: a mechanical concatenation of shorter common words or name "
    "parts; a user typing this string would naturally type the shorter pieces in "
    "sequence instead (e.g. 吉林省公安厅 = 吉林省+公安厅, 吉隆坡城中城公园 = "
    "吉隆坡+城中城+公园)\n"
    "Rule of thumb: if shorter existing words chained together reach the same "
    "string and the full form is not a single fixed conventional name, it is "
    "composable.\n"
    'Reply ONLY with JSON lines: {"n":<number>,"v":"atomic|composable","d":"<10-20 char reason>"}\n'
    "No markdown fences, no extra text."
)


def load_review_real_words() -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for line in REVIEW_CHECKPOINT.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        surface = rec.get("s") or ""
        if rec.get("v") != "real-word":
            continue
        if len(surface) < 5 or surface in seen:
            continue
        seen.add(surface)
        out.append(surface)
    return out


def load_done() -> set[str]:
    done: set[str] = set()
    if CHECKPOINT.exists():
        for line in CHECKPOINT.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    done.add(json.loads(line)["s"])
                except (json.JSONDecodeError, KeyError):
                    pass
    return done


def strip_fences(text: str) -> str:
    text = text.strip()
    m = re.match(r"^```(?:json)?\s*\n(.*?)\n```\s*$", text, re.DOTALL)
    return m.group(1).strip() if m else text


def call_llm(batch: list[tuple[int, str]]) -> str:
    lines = "\n".join(f"{n}. {s}" for n, s in batch)
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


def parse_results(content: str, batch: list[tuple[int, str]]) -> list[dict]:
    n_to_surface = dict(batch)
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
            results.append({"s": n_to_surface[n], "v": v, "d": rec.get("d", "")})
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue
    return results


def process_batch(batch: list[tuple[int, str]]) -> list[dict]:
    for attempt in range(3):
        try:
            content = call_llm(batch)
            results = parse_results(content, batch)
            if results:
                return results
        except Exception as e:
            if attempt == 2:
                print(f"  batch failed after 3 retries: {e}", flush=True)
            time.sleep(2 ** (attempt + 1))
    return []


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--batch", type=int, default=150)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    all_rows = load_review_real_words()
    if args.limit:
        all_rows = all_rows[: args.limit]
    done = load_done()
    remaining = [(n, s) for n, s in enumerate(all_rows) if s not in done]
    print(f"Total real-word long rows: {len(all_rows)}, done: {len(done)}, remaining: {len(remaining)}")
    if not remaining:
        print("All rows already classified.")
        return
    if args.dry_run:
        print(f"[dry-run] would process {len(remaining)} rows")
        return

    batches = [remaining[i:i+args.batch] for i in range(0, len(remaining), args.batch)]
    print(f"Batches: {len(batches)}, workers: {args.workers}")

    total = 0
    lock = threading.Lock()
    t0 = time.time()
    with open(CHECKPOINT, "a") as ckpt:
        def run_batch(b):
            nonlocal total
            results = process_batch(b)
            with lock:
                if results:
                    for rec in results:
                        ckpt.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    ckpt.flush()
                    total += len(results)
                    done_n = total
                else:
                    done_n = total
                rate = done_n / max(time.time() - t0, 1) * 60
                print(f"progress {done_n} rows, {rate:.0f} rows/min", flush=True)

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(run_batch, batches))
    print(f"Done: {total} verdicts in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
