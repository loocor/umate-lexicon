#!/usr/bin/env python3
"""Magpie deepseek relay for tencent LLM classification (Plan A).

Phase 1: process words not yet handled by the mimo checkpoint.
Phase 2 (--recheck): re-verify mimo-fragment rows via magpie; output is
written to a separate checkpoint so the merge step can override.

Usage:
    python scripts/llm_classify_tencent_magpie.py [--workers 4] [--batch 100] [--recheck] [--dry-run]
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
MIMO_CHECKPOINT = Path("data/eval/llm-classify-tencent.jsonl")
CHECKPOINT = Path("data/eval/llm-classify-tencent-magpie.jsonl")
CATEGORIES = {"real-word", "domain-term", "proper-noun", "fragment"}

PROMPT = (
    "你是中文输入法词库审核员。判断每个词是否是用户会主动输入的独立词汇。\n"
    "类别：real-word(独立词汇) / domain-term(领域术语) / proper-noun(专名) / fragment(碎片截断)\n"
    '每词输出一行 JSON：{"w":"词","c":"类别","d":"简述"}\n'
    "不要输出其他内容。词语：\n"
)


def fetch_words(min_len: int, max_len: int) -> list[str]:
    db = sqlite3.connect("data/store/lemmas.sqlite")
    rows = db.execute(
        """
        SELECT surface FROM lemmas
        WHERE domain_freq LIKE '%tencent%'
        AND json_extract(domain_freq, '$.tencent') = 1
        AND (json_extract(domain_freq, '$.core') IS NULL OR json_extract(domain_freq, '$.core') = 0)
        AND status = 'auto'
        AND LENGTH(surface) >= ? AND LENGTH(surface) <= ?
        ORDER BY surface
        """,
        (min_len, max_len),
    ).fetchall()
    return [r[0] for r in rows]


def load_jsonl(path: Path) -> dict[str, dict]:
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                try:
                    rec = json.loads(line)
                    out[rec["w"]] = rec
                except (json.JSONDecodeError, KeyError):
                    pass
    return out


def strip_fences(text: str) -> str:
    text = text.strip()
    m = re.match(r"^```(?:json)?\s*\n(.*?)\n```\s*$", text, re.DOTALL)
    return m.group(1).strip() if m else text


def call_llm(batch: list[str]) -> str:
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT + "\n".join(batch)}],
        "temperature": 0.1,
        "max_tokens": 16384,
    }).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"] or ""


def parse_results(content: str) -> list[dict]:
    results = []
    for line in strip_fences(content).split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            if rec.get("c") in CATEGORIES:
                results.append({"w": rec["w"], "c": rec["c"], "d": rec.get("d", "")})
        except json.JSONDecodeError:
            pass
    return results


def process_batch(batch: list[str]) -> list[dict]:
    for attempt in range(3):
        try:
            content = call_llm(batch)
            results = parse_results(content)
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
    parser.add_argument("--min-len", type=int, default=4)
    parser.add_argument("--max-len", type=int, default=4)
    parser.add_argument("--recheck", action="store_true",
                        help="re-verify mimo=fragment rows instead of new words")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    all_words = fetch_words(args.min_len, args.max_len)
    mimo = load_jsonl(MIMO_CHECKPOINT)
    mine = load_jsonl(CHECKPOINT)

    if args.recheck:
        targets = [r["w"] for r in mimo.values() if r["c"] == "fragment"]
        print(f"Recheck: mimo fragment rows: {len(targets)}")
    else:
        targets = [w for w in all_words if w not in mimo and w not in mine]
        print(f"Total: {len(all_words)}, mimo done: {len(mimo)}, magpie done: {len(mine)}, remaining: {len(targets)}")

    if args.dry_run:
        print(f"[dry-run] would process {len(targets)} words")
        return
    if not targets:
        print("Nothing to do.")
        return

    batches = [targets[i:i+args.batch] for i in range(0, len(targets), args.batch)]
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
            non_frag = sum(1 for r in results if r["c"] != "fragment")
            return len(results), non_frag, time.time() - start

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(run_batch, b): i for i, b in enumerate(batches)}
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    n, kept, el = future.result()
                    pct = total * 100 // max(1, len(targets))
                    print(f"  batch {idx+1}/{len(batches)}: {n} words ({kept} non-fragment) {el:.1f}s [{pct}%]")
                except Exception as e:
                    print(f"  batch {idx+1} error: {e}", file=sys.stderr)
    print(f"\nDone: {total} words in {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
