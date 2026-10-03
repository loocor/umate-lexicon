#!/usr/bin/env python3
"""Apply untrusted_reading LLM fixes to the lemma store.

From llm-verify-reading.jsonl:
  incorrect (post-validated)  -> update pinyin_plain, drop
                                 'untrusted_reading', add 'llm_reading_fix'
  correct / variant           -> keep flag (reading confirmed or alternate)
  blocked                     -> untouched, stay for Unihan verification

Usage:
    python scripts/apply_reading_fix.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

CHECKPOINT = Path("data/eval/llm-verify-reading.jsonl")


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
    fixed, kept, blocked, skipped = 0, 0, 0, 0
    merges = []
    for surface, rec in recs.items():
        if rec.get("blocked"):
            blocked += 1
            continue
        if rec["v"] != "incorrect":
            kept += 1
            continue
        row = db.execute(
            "SELECT status, flags, pinyin_plain, weight, domain_freq FROM lemmas WHERE surface=?",
            (surface,),
        ).fetchone()
        if row is None:
            skipped += 1
            continue
        if "untrusted_reading" not in (row["flags"] or ""):
            skipped += 1
            continue
        flags = json.loads(row["flags"] or "[]")
        flags = [f for f in flags if f != "untrusted_reading"]
        if "llm_reading_fix" not in flags:
            flags.append("llm_reading_fix")
        corrected = rec["c"].strip().lower()
        if corrected == row["pinyin_plain"]:
            # already in sync; just swap flag
            fixed += 1
            if not args.dry_run:
                db.execute(
                    "UPDATE lemmas SET flags=? WHERE surface=? AND pinyin_plain=?",
                    (json.dumps(flags, ensure_ascii=False), surface, row["pinyin_plain"]),
                )
            continue
        clash = db.execute(
            "SELECT 1 FROM lemmas WHERE surface=? AND pinyin_plain=?",
            (surface, corrected),
        ).fetchone()
        if clash is not None:
            merges.append((surface, row["pinyin_plain"], corrected))
            if not args.dry_run:
                old_flags = json.loads(row["flags"] or "[]")
                tgt = db.execute(
                    "SELECT flags, weight, domain_freq FROM lemmas WHERE surface=? AND pinyin_plain=?",
                    (surface, corrected),
                ).fetchone()
                tgt_flags = json.loads(tgt["flags"] or "[]")
                merged_flags = sorted(set(tgt_flags) | (set(old_flags) - {"untrusted_reading"}) | {"llm_reading_fix"})
                old_df_raw = db.execute(
                    "SELECT domain_freq FROM lemmas WHERE surface=? AND pinyin_plain=?",
                    (surface, row["pinyin_plain"]),
                ).fetchone()[0] or "{}"
                old_df = json.loads(old_df_raw)
                tgt_df = json.loads(tgt["domain_freq"] or "{}")
                for k, v in old_df.items():
                    tgt_df[k] = max(tgt_df.get(k, 0), v)
                db.execute(
                    "UPDATE lemmas SET flags=?, domain_freq=? WHERE surface=? AND pinyin_plain=?",
                    (json.dumps(merged_flags, ensure_ascii=False), json.dumps(tgt_df, ensure_ascii=False), surface, corrected),
                )
                db.execute(
                    "DELETE FROM lemmas WHERE surface=? AND pinyin_plain=?",
                    (surface, row["pinyin_plain"]),
                )
            continue
        fixed += 1
        if not args.dry_run:
            db.execute(
                "UPDATE lemmas SET pinyin_plain=?, pinyin_toned=NULL, flags=? WHERE surface=? AND pinyin_plain=?",
                (corrected, json.dumps(flags, ensure_ascii=False), surface, row["pinyin_plain"]),
            )
    print(f"fixed (pinyin updated, flag swapped): {fixed}")
    print(f"primary-key merges (old row removed, target merged): {len(merges)}")
    for s, old, new in merges[:10]:
        print(f"  {s}: {old} -> {new}")
    print(f"kept (correct/variant, flag preserved): {kept}")
    print(f"blocked (untouched): {blocked}")
    print(f"skipped (missing or flag already cleared): {skipped}")
    if not args.dry_run:
        db.commit()
        print("committed")
    else:
        print("[dry-run] no changes written")


if __name__ == "__main__":
    main()
