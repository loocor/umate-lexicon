"""Canonical category taxonomy for the lemma store.

Every ingest source maps its native category labels onto this single
vocabulary; downstream logic (pack routing, calibration, filters)
reads only canonical values. Source identity stays in domain_freq and
the sources table purely as lineage.

Entity types split into two groups:

- Named-entity types route into dedicated packs (names/places/orgs/
  ext/brands/events): person, place, org, work, brand, event.
- Domain-vocabulary types describe what kind of word it is but never
  route into a named-entity pack: food, medical, law, tech, finance,
  vehicle, animal, idiom, literary. They layer by measured rank like
  ordinary vocabulary.
"""

from __future__ import annotations

from pathlib import Path

CANONICAL_ENTITY_TYPES = frozenset({
    # named entities (pack-routed)
    "person", "place", "org", "work", "brand", "event",
    # domain vocabulary (rank-layered, never pack-routed)
    "food", "medical", "law", "tech", "finance", "vehicle",
    "animal", "idiom", "literary",
    # functional marks (not semantic categories)
    "emoji", "symbol", "correction",
})

# THUOCL sub-list file name fragment -> canonical entity type.
# Sub-list identity also lands in domain_freq as "thuocl-<sublist>"
# via the ingest domain parameter, so lineage survives independently.
THUOCL_SUBLIST_TYPES = {
    "food": "food",
    "diming": "place",
    "lishimingren": "person",
    "medical": "medical",
    "law": "law",
    "caijing": "finance",
    "car": "vehicle",
    "animal": "animal",
    "chengyu": "idiom",
    "poem": "literary",
    "it": "tech",
}

# Rank floors for thuocl-only rows, per canonical type. THUOCL
# inclusion is itself evidence of a real domain word; everyday-typed
# domains (food, idioms, vehicles, tech) earn the hot floor, while
# professional/long-tail domains stay cold but findable.
CANONICAL_RANK_FLOORS = {
    "food": 450, "idiom": 450, "vehicle": 450, "tech": 450,
    "medical": 200, "law": 200, "finance": 200,
    "animal": 150, "literary": 150,
    "place": 100, "person": 100,
}


def thuocl_entity_type(path_name: str) -> str | None:
    """Canonical type for a THUOCL sub-list file name, else None."""
    lowered = path_name.lower()
    for fragment, canonical in THUOCL_SUBLIST_TYPES.items():
        if fragment in lowered:
            return canonical
    return None


def thuocl_categories(path_name: str) -> list[str]:
    """Category tag list for a THUOCL sub-list file name."""
    entity = thuocl_entity_type(path_name)
    return [entity] if entity else []

# Domain-vocabulary types describe what kind of word it is and outrank
# named-entity types when one word lands in several THUOCL sub-lists
# (e.g. 肉夹馍 in both diming and food: the food label is the semantic
# truth; the diming hit is upstream noise). Within a group the largest
# measured sublist column wins.
_NAMED_ENTITY_TYPES = frozenset({"person", "place", "org", "work", "brand", "event"})
_DOMAIN_VOCAB_TYPES = frozenset({
    "food", "medical", "law", "tech", "finance", "vehicle", "animal",
    "idiom", "literary",
})


def entity_type_from_domains(domain_freq: dict[str, int]) -> str | None:
    """Canonical type re-derived from per-sublist THUOCL lineage.

    Merge keeps the first ingest label, so a broad named-entity hit that
    ingested earlier can shadow a later, more precise domain label. This
    re-derivation reads only domain_freq evidence, so it stays stable
    regardless of ingest order.
    """
    domain_types: dict[str, list[tuple[int, str]]] = {}
    for domain, count in domain_freq.items():
        if not domain.startswith("thuocl-") or count <= 0:
            continue
        entity = thuocl_entity_type(domain)
        if entity:
            domain_types.setdefault(entity, []).append((int(count), domain))
    if not domain_types:
        return None
    domain_hits = [e for e in domain_types if e in _DOMAIN_VOCAB_TYPES]
    if domain_hits:
        return max(
            domain_hits,
            key=lambda e: max(count for count, _ in domain_types[e]),
        )
    entity_hits = [e for e in domain_types if e in _NAMED_ENTITY_TYPES]
    if entity_hits:
        return max(
            entity_hits,
            key=lambda e: max(count for count, _ in domain_types[e]),
        )
    return None
