from __future__ import annotations

import math
import re

from umate_lexicon.lemma import Lemma

_HAN = re.compile(r"[\u4e00-\u9fff]")

CORE_LAYERS = ("chars", "base")
PACK_LAYERS = (
    "ext",
    "names",
    "places",
    "brands",
    "orgs",
    "events",
    "mixed",
    "bulk",
    "corrections",
)


def han_len(surface: str) -> int:
    return len(_HAN.findall(surface))


def emit_weight(lemma: Lemma) -> int:
    total = sum(lemma.domain_freq.values()) or lemma.weight
    return max(1, int(round(100 * math.log1p(total))))


def assign_layer(lemma: Lemma) -> str | None:
    if lemma.status == "rejected":
        return None
    if "correction" in lemma.flags:
        return "corrections"
    if lemma.entity_type == "person" or "person" in lemma.categories:
        return "names"
    if lemma.entity_type == "place" or "place" in lemma.categories:
        return "places"
    if lemma.entity_type == "brand" or "brand" in lemma.categories or "mixed_latin" in lemma.flags:
        if "mixed_latin" in lemma.flags:
            return "mixed"
        return "brands"
    if lemma.entity_type in {"org", "industry"} or "org" in lemma.categories:
        return "orgs"
    if lemma.entity_type == "event" or "event" in lemma.categories:
        return "events"
    n = han_len(lemma.surface)
    if n == 1:
        return "chars"
    if n in {2, 3} and lemma.status in {"gold", "auto"}:
        return "base"
    if n == 4:
        return "ext"
    if "polyphone" in lemma.flags and lemma.status != "gold":
        return None
    return "bulk"
