"""Calibrate THUOCL-only ranks via within-sublist percentile mapping.

THUOCL document counts sit on an incompatible scale with the core 1e8
contract. Map each word's within-sublist percentile onto the tiered
scale used by the wiki page weights, touching only rows without a
stronger measured domain (modern_freq/core/hanyu_pinlu/chars/gold).
"""

from __future__ import annotations

import json
from pathlib import Path

from umate_lexicon.layers import COVERAGE_FREQ_DOMAINS, RANK_DOMAIN_PRECEDENCE
from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore

HOT_FLOOR = 450
TIERS = [(95, 1000), (85, 600), (70, 450), (50, 200), (0, 100)]
# Sublist endorsement floors: THUOCL inclusion is itself evidence the
# entry is a real domain word. Food/chengyu/car names are typed in
# everyday scenarios (ordering, vehicles) so they enter the hot
# projection; professional terminology stays cold but findable.
SUBLIST_FLOORS = {
    "food": 450, "chengyu": 450, "car": 450, "it": 450,
    "medical": 200, "law": 200, "caijing": 200,
    "animal": 150, "poem": 150,
    "diming": 100, "lishimingren": 100,
}


def _load_sublists() -> dict[str, dict[str, int]]:
    sublists: dict[str, dict[str, int]] = {}
    downloads = data_dir() / "sources" / "downloads"
    if not downloads.is_dir():
        return sublists
    for path in sorted(downloads.glob("THUOCL_*.txt")):
        freqs: dict[str, int] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split("\t")
            if parts and parts[0] and not parts[0].startswith("#"):
                surface = parts[0].strip()
                freq = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
                freqs[surface] = freq
        if freqs:
            sublists[path.stem.replace("THUOCL_", "").lower()] = freqs
    return sublists


def _tier_for(freqs: dict[str, int], surface: str, floor: int) -> int:
    values = sorted(freqs.values())
    below = sum(1 for v in values if v < freqs[surface])
    pct = below * 100 / max(1, len(values) - 1)
    tier = TIERS[-1][1]
    for threshold, weight in TIERS:
        if pct >= threshold:
            tier = weight
            break
    return max(tier, floor)


def calibrate_thuocl_rank(store: LemmaStore) -> dict[str, int]:
    conn = store._conn
    sublists = _load_sublists()
    from umate_lexicon.taxonomy import CANONICAL_RANK_FLOORS, thuocl_entity_type

    plan: dict[str, int] = {}
    for name, freqs in sublists.items():
        floor = CANONICAL_RANK_FLOORS.get(
            thuocl_entity_type(f"THUOCL_{name}.txt") or "", 100
        )
        for surface in freqs:
            tier = _tier_for(freqs, surface, floor)
            if surface not in plan or tier > plan[surface]:
                plan[surface] = tier

    stats = {"thuocl_calibrated": 0}
    rows = conn.execute("SELECT surface, domain_freq, rank FROM lemmas").fetchall()
    for row in rows:
        surface = row["surface"]
        if surface not in plan:
            continue
        domains = json.loads(row["domain_freq"] or "{}")
        if _rank_source(domains) != "thuocl":
            continue
        # High-frequency thuocl rows (周期 at 77769) are already correct
        # on the raw scale; only rows crushed below the hot floor move.
        current = row["rank"] or 0
        if current >= HOT_FLOOR:
            continue
        tier = plan[surface]
        conn.execute(
            "UPDATE lemmas SET rank=?, weight=? WHERE surface=?",
            (tier, tier, surface),
        )
        stats["thuocl_calibrated"] += 1
    return stats


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
