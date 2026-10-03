#!/usr/bin/env python3
"""Apply review-tier LLM triage to the lemma store.

From llm-classify-review.jsonl:
  real-word    -> status='auto' (user picked promote)
  fragment     -> status='rejected' + flag 'llm_fragment'
  variant-dup  -> status='rejected' + flag 'llm_variant_dup'

Usage:
    python scripts/apply_review_triage.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

CHECKPOINT = Path("data/eval/llm-classify-review.jsonl")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    recs = {}
    for line in CHECKPOINT.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            recs[r["s"]] = r
    print(f"checkpoint rows: {len(recs)}")

    db = sqlite3.connect("data/store/lemmas.sqlite")
    db.row_factory = sqlite3.Row
    promote, reject_frag, reject_dup, skipped = 0, 0, 0, 0
    for surface, rec in recs.items():
        row = db.execute(
            "SELECT status, flags FROM lemmas WHERE surface=?", (surface,)
        ).fetchone()
        if row is None or row["status"] != "review":
            skipped += 1
            continue
        verdict = rec["v"]
        flags = json.loads(row["flags"] or "[]")
        if verdict == "real-word":
            promote += 1
            if not args.dry_run:
                db.execute("UPDATE lemmas SET status='auto' WHERE surface=?", (surface,))
        elif verdict == "fragment":
            reject_frag += 1
            if "llm_fragment" not in flags:
                flags.append("llm_fragment")
            if not args.dry_run:
                db.execute(
                    "UPDATE lemmas SET status='rejected', flags=? WHERE surface=?",
                    (json.dumps(flags, ensure_ascii=False), surface),
                )
        elif verdict == "variant-dup":
            reject_dup += 1
            if "llm_variant_dup" not in flags:
                flags.append("llm_variant_dup")
            if not args.dry_run:
                db.execute(
                    "UPDATE lemmas SET status='rejected', flags=? WHERE surface=?",
                    (json.dumps(flags, ensure_ascii=False), surface),
                )
    print(f"promote to auto: {promote}")
    print(f"reject fragment: {reject_frag}")
    print(f"reject variant-dup: {reject_dup}")
    print(f"skipped (not review status): {skipped}")
    if not args.dry_run:
        db.commit()
        print("committed")
    else:
        print("[dry-run] no changes written")


if __name__ == "__main__":
    main()
