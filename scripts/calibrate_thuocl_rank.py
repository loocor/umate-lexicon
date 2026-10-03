#!/usr/bin/env python3
"""Calibrate THUOCL-only ranks via within-sublist percentile mapping.

THUOCL raw counts are document-level on an incompatible scale with the
core 1e8 contract, so thuocl-only rows fall into cold bulk with rank
near zero. This script maps each word's within-sublist percentile onto
the tiered scale already used by the wiki page weights:

    p>=95 -> 1000, p>=85 -> 600, p>=70 -> 450, p>=50 -> 200, else 100

Only rows whose domain_freq has no stronger measured domain
(modern_freq/core/hanyu_pinlu/chars/gold) are touched.

Usage:
    python scripts/calibrate_thuocl_rank.py [--dry-run]
"""

from __future__ import annotations

import argparse
import glob
import json
import sqlite3
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from umate_lexicon.layers import COVERAGE_FREQ_DOMAINS, RANK_DOMAIN_PRECEDENCE  # noqa: E402

HOT_FLOOR = 450

STRONG_DOMAINS = {"modern_freq", "core", "hanyu_pinlu", "chars", "gold"}
TIERS = [(95, 1000), (85, 600), (70, 450), (50, 200), (0, 100)]
from umate_lexicon.taxonomy import CANONICAL_RANK_FLOORS, thuocl_entity_type  # noqa: E402


def load_sublists() -> dict[str, dict[str, int]]:
    sublists: dict[str, dict[str, int]] = {}
    for path in sorted(glob.glob("data/sources/downloads/THUOCL_*.txt")):
        name = Path(path).stem.replace("THUOCL_", "").lower()
        freqs: dict[str, int] = {}
        for line in open(path):
            parts = line.strip().split("\t")
            if parts and parts[0] and not parts[0].startswith("#"):
                surface = parts[0].strip()
                freq = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
                freqs[surface] = freq
        if freqs:
            sublists[name] = freqs
    return sublists


def percentile_rank(freqs: dict[str, int], surface: str) -> float:
    """Percentile of this word's freq within its sublist (0-100)."""
    target = freqs[surface]
    values = sorted(freqs.values())
    below = sum(1 for v in values if v < target)
    return below * 100 / max(1, len(values) - 1)


def tier_for(pct: float) -> int:
    for threshold, weight in TIERS:
        if pct >= threshold:
            return weight
    return TIERS[-1][1]



def _rank_source(domains: dict) -> str | None:
    """Which domain wins the rank column under resolve precedence."""
    ledger = {
        k: int(v) for k, v in domains.items()
        if k not in COVERAGE_FREQ_DOMAINS and k != "curation_rank" and int(v) > 0
    }
    if not ledger:
        return None
    for domain in RANK_DOMAIN_PRECEDENCE:
        if ledger.get(domain):
            return domain
    for domain in ledger:
        if domain.startswith("thuocl"):
            return domain
    return max(ledger, key=lambda k: ledger[k])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sublists = load_sublists()
    db = sqlite3.connect("data/store/lemmas.sqlite")

    # word -> (sublist, percentile, tier)
    plan: dict[str, tuple[str, float, int]] = {}
    for name, freqs in sublists.items():
        for surface in freqs:
            pct = percentile_rank(freqs, surface)
            floor = CANONICAL_RANK_FLOORS.get(thuocl_entity_type(f"THUOCL_{name}.txt") or "", 100)
            tier = max(tier_for(pct), floor)
            if surface not in plan or tier > plan[surface][2]:
                plan[surface] = (name, pct, tier)

    rows = db.execute("SELECT surface, domain_freq, rank FROM lemmas").fetchall()
    updated = 0
    tier_stats: dict[int, int] = {}
    skipped_strong = 0
    for row in rows:
        surface = row[0]
        if surface not in plan:
            continue
        domains = json.loads(row[1] or "{}")
        if _rank_source(domains) != "thuocl":
            skipped_strong += 1
            continue
        current = row[2] or 0
        if current >= HOT_FLOOR:
            skipped_strong += 1
            continue
        tier = plan[surface][2]
        updated += 1
        tier_stats[tier] = tier_stats.get(tier, 0) + 1
        if not args.dry_run:
            db.execute(
                "UPDATE lemmas SET rank=?, weight=? WHERE surface=?",
                (tier, tier, surface),
            )
    print(f"would update: {updated}")
    print(f"skipped (stronger domain present): {skipped_strong}")
    print(f"tier distribution of updates: {dict(sorted(tier_stats.items(), reverse=True))}")
    hot_gain = sum(n for t, n in tier_stats.items() if t >= 450)
    print(f"rows entering hot projection (>=450): {hot_gain}")
    if not args.dry_run:
        db.commit()
        print("committed")
    else:
        print("[dry-run] no changes written")


if __name__ == "__main__":
    main()
