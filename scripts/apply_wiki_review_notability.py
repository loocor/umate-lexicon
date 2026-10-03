#!/usr/bin/env python3
"""Apply notability filter to wiki_category review-tier rows.

Same rule as the auto-tier filter (apply_wiki_notability.py), but for
status='review' rows, and promote instead of keep:
  work                     -> status='auto' (films/books user cares about)
  person/place/org pw>=450 -> status='auto'
  person/place/org pw<450  -> status='rejected' + flag 'wiki_low_notable'

Usage:
    python scripts/apply_wiki_review_notability.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from umate_lexicon.layers import _load_wiki_page_weights  # noqa: E402

HOT_FLOOR = 450


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    weights = _load_wiki_page_weights()
    db = sqlite3.connect("data/store/lemmas.sqlite")
    db.row_factory = sqlite3.Row

    rows = db.execute("""
        SELECT surface, entity_type, flags FROM lemmas
        WHERE flags LIKE '%wiki_category%' AND status='review'
    """).fetchall()
    print(f"review-tier wiki_category rows: {len(rows)}")

    promote, reject, skipped = 0, 0, 0
    for row in rows:
        surface = row["surface"]
        etype = row["entity_type"]
        if etype == "work":
            promote += 1
            if not args.dry_run:
                db.execute("UPDATE lemmas SET status='auto' WHERE surface=?", (surface,))
            continue
        if etype not in ("person", "place", "org"):
            skipped += 1
            continue
        pw = weights.get(surface) or 0
        if pw >= HOT_FLOOR:
            promote += 1
            if not args.dry_run:
                db.execute("UPDATE lemmas SET status='auto' WHERE surface=?", (surface,))
        else:
            reject += 1
            flags = json.loads(row["flags"] or "[]")
            if "wiki_low_notable" not in flags:
                flags.append("wiki_low_notable")
            if not args.dry_run:
                db.execute(
                    "UPDATE lemmas SET status='rejected', flags=? WHERE surface=?",
                    (json.dumps(flags, ensure_ascii=False), surface),
                )
    print(f"promote to auto: {promote}")
    print(f"reject low-notable: {reject}")
    print(f"skipped (other entity types): {skipped}")
    if not args.dry_run:
        db.commit()
        print("committed")
    else:
        print("[dry-run] no changes written")


if __name__ == "__main__":
    main()
