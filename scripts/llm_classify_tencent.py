#!/usr/bin/env python3
"""LLM classification of tencent-only words via mimo-flash.

Classifies 4-char auto-status tencent-only words as real-word, domain-term,
proper-noun, or fragment. Results stored as JSONL checkpoints for
resumability. 4 concurrent workers, 100 words per batch.

Usage:
    python scripts/llm_classify_tencent.py [--workers 4] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

API = "http://127.0.0.1:3721/v1/chat/completions"
KEY = "Pr8D242A9OnnTp6ExTJ3d2qgnhYPobcE"
MODEL = "mimo-v2.6-flash"
BATCH_SIZE = 100
CHECKPOINT = Path("data/eval/llm-classify-tencent.jsonl")
CATEGORIES = {"real-word", "domain-term", "proper-noun", "fragment"}


def fetch_words(min_len: int, max_len: int) -> list[str]:
    """Get tencent-only auto words from store."""
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


def load_done() -> set[str]:
    """Load already-classified words from checkpoint."""
    done = set()
    if CHECKPOINT.exists():
        for line in CHECKPOINT.read_text().splitlines():
            if line.strip():
                try:
                    rec = json.loads(line)
                    done.add(rec["w"])
                except (json.JSONDecodeError, KeyError):
                    pass
    return done


def call_llm(batch: list[str]) -> str:
    """Send a batch to mimo-flash and return raw content."""
    nl = "\n"
    word_list = nl.join(batch)
    prompt = (
        "你是中文输入法词库审核员。判断每个词是否是用户会主动输入的独立词汇。\n"
        "类别：real-word(独立词汇) / domain-term(领域术语) / proper-noun(专名) / fragment(碎片截断)\n"
        '每词输出一行 JSON：{"w":"词","c":"类别","d":"简述"}\n'
        "不要输出其他内容。词语：\n" + word_list
    )
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 16384,
    }).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"] or ""


def parse_results(content: str) -> list[dict]:
    """Parse JSONL lines from LLM output."""
    results = []
    for line in content.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            w = rec.get("w", "")
            c = rec.get("c", "")
            if c not in CATEGORIES:
                continue
            results.append({"w": w, "c": c, "d": rec.get("d", "")})
        except json.JSONDecodeError:
            pass
    return results


def process_batch(batch: list[str]) -> list[dict]:
    """Call LLM and parse results, with retry."""
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
    parser.add_argument("--min-len", type=int, default=4)
    parser.add_argument("--max-len", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--batch", type=int, default=BATCH_SIZE)
    args = parser.parse_args()

    all_words = fetch_words(args.min_len, args.max_len)
    if args.limit:
        all_words = all_words[: args.limit]
    done = load_done()
    remaining = [w for w in all_words if w not in done]
    import random
    random.shuffle(remaining)
    print(f"Total: {len(all_words)}, done: {len(done)}, remaining: {len(remaining)}")

    if not remaining:
        print("All words already classified.")
        return

    if args.dry_run:
        print(f"[dry-run] would process {len(remaining)} words in {len(remaining)//BATCH_SIZE} batches with {args.workers} workers")
        return

    batch_size = args.batch or BATCH_SIZE
    batches = [remaining[i:i+batch_size] for i in range(0, len(remaining), batch_size)]
    print(f"Batches: {len(batches)}, workers: {args.workers}")

    total_processed = 0
    total_time = time.time()
    checkpoint_lock = __import__("threading").Lock()

    with open(CHECKPOINT, "a") as ckpt:
        def run_batch(batch):
            nonlocal total_processed
            start = time.time()
            results = process_batch(batch)
            elapsed = time.time() - start
            with checkpoint_lock:
                for rec in results:
                    ckpt.write(json.dumps(rec, ensure_ascii=False) + "\n")
                ckpt.flush()
                total_processed += len(results)
            done_names = sum(1 for r in results if r["c"] != "fragment")
            return len(results), elapsed, done_names

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(run_batch, b): i for i, b in enumerate(batches)}
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    count, elapsed, kept = future.result()
                    # count already tracked inside run_batch
                    pct = total_processed * 100 // max(1, len(remaining))
                    print(f"  batch {idx+1}/{len(batches)}: {count} words ({kept} non-fragment), {elapsed:.1f}s [{pct}%]")
                except Exception as e:
                    print(f"  batch {idx+1} error: {e}", file=sys.stderr)

    wall = time.time() - total_time
    print(f"\nDone: {total_processed} words in {wall/3600:.1f}h")


if __name__ == "__main__":
    main()
