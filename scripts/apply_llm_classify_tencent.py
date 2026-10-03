#!/usr/bin/env python3
"""Apply merged tencent LLM classification to the lemma store.

Two write-back modes:
  --source both    both mimo and magpie checkpoints must agree on 'fragment'
  --source magpie  magpie checkpoint alone decides (for 2/3-char ranges
                   mimo never covered)

Only rows currently status='auto' are touched; rejected rows get flag
'llm_fragment' for traceability.

Usage:
    python scripts/apply_llm_classify_tencent.py --min-len 4 --max-len 4 --source both [--dry-run]
    python scripts/apply_llm_classify_tencent.py --min-len 3 --max-len 3 --source magpie [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

MIMO = Path("data/eval/llm-classify-tencent.jsonl")
MAGPIE = Path("data/eval/llm-classify-tencent-magpie.jsonl")


def load(path: Path) -> dict[str, dict]:
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                try:
                    r = json.loads(line)
                    out[r["w"]] = r
                except (json.JSONDecodeError, KeyError):
                    pass
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-len", type=int, required=True)
    parser.add_argument("--max-len", type=int, required=True)
    parser.add_argument("--source", choices=["both", "magpie"], required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    mimo = load(MIMO) if args.source == "both" else {}
    magpie = load(MAGPIE)

    if args.source == "both":
        targets = [w for w, r in mimo.items() if r["c"] == "fragment" and w in magpie and magpie[w]["c"] == "fragment"]
    else:
        targets = [w for w, r in magpie.items() if r["c"] == "fragment"]
    print(f"mode={args.source}, len={args.min_len}-{args.max_len}, targets: {len(targets)}")

    db = sqlite3.connect("data/store/lemmas.sqlite")
    db.row_factory = sqlite3.Row
    confirm, skipped, changed = 0, 0, 0
    for w in targets:
        row = db.execute(
            f"SELECT surface, status, flags FROM lemmas WHERE surface=? AND LENGTH(surface) BETWEEN {args.min_len} AND {args.max_len}",
            (w,),
        ).fetchone()
        if row is None or row["status"] != "auto":
            skipped += 1
            continue
        flags = json.loads(row["flags"] or "[]")
        if "llm_fragment" not in flags:
            flags.append("llm_fragment")
        confirm += 1
        if not args.dry_run:
            db.execute(
                "UPDATE lemmas SET status='rejected', flags=? WHERE surface=? AND status='auto'",
                (json.dumps(flags, ensure_ascii=False), w),
            )
            changed += 1
    print(f"confirmed auto-status targets: {confirm}, skipped: {skipped}")
    if not args.dry_run:
        db.commit()
        print(f"updated rows: {changed}")
    else:
        print("[dry-run] no changes written")


if __name__ == "__main__":
    main()
