#!/usr/bin/env python3
"""Apply notability filter to wiki-only person/place/org rows (Plan A).

Rows with flags='["wiki_category"]', status='auto', entity_type in
(person, place, org), and domain_freq='{"wiki": 1}' are rejected when
their wiki page policy_weight is below 450 (or missing from the weight
table). work rows and multi-source rows are untouched.

Usage:
    python scripts/apply_wiki_notability.py [--dry-run]
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
        SELECT surface, flags FROM lemmas
        WHERE flags='["wiki_category"]' AND status='auto'
        AND entity_type IN ('person','place','org')
        AND domain_freq='{"wiki": 1}'
    """).fetchall()
    print(f"candidates: {len(rows)}")

    rejected, kept, missing = 0, 0, 0
    for row in rows:
        surface = row["surface"]
        pw = weights.get(surface)
        if pw is None:
            missing += 1
            pw = 0
        if pw >= HOT_FLOOR:
            kept += 1
            continue
        if args.dry_run:
            rejected += 1
            continue
        flags = json.loads(row["flags"] or "[]")
        if "wiki_low_notable" not in flags:
            flags.append("wiki_low_notable")
        db.execute(
            "UPDATE lemmas SET status='rejected', flags=? WHERE surface=? AND status='auto'",
            (json.dumps(flags, ensure_ascii=False), surface),
        )
        rejected += 1

    print(f"kept (pw>={HOT_FLOOR}): {kept}")
    print(f"missing from weight table (treated as pw=0): {missing}")
    print(f"rejected: {rejected}")
    if not args.dry_run:
        db.commit()
        print("committed")
    else:
        print("[dry-run] no changes written")


if __name__ == "__main__":
    main()
