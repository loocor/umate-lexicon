from __future__ import annotations

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
COVERAGE_SOURCE_IDS = frozenset({"wiki", "tencent"})
COVERAGE_FREQ_DOMAINS = frozenset({"wiki", "tencent"})


def han_len(surface: str) -> int:
    return len(_HAN.findall(surface))


def is_wiki_only(lemma: Lemma) -> bool:
    return {ref.source_id for ref in lemma.sources} == {"wiki"}


def is_coverage_only(lemma: Lemma) -> bool:
    ids = {ref.source_id for ref in lemma.sources}
    return bool(ids) and ids <= COVERAGE_SOURCE_IDS


def ranking_freq(lemma: Lemma) -> int:
    ranked = sum(
        count for domain, count in lemma.domain_freq.items() if domain not in COVERAGE_FREQ_DOMAINS
    )
    if ranked:
        return ranked
    return lemma.weight


def emit_weight(lemma: Lemma) -> int:
    """Value for the Rime `weight` column.

    librime stores this column as `log(weight)` at compile time
    (`dict_compiler.cc`) and subtracts `log(1e8)` at query time, so the
    column is a raw frequency on a 1e8 scale -- the same scale rime-essay
    counts already use. Compressing it here would flatten the distribution
    and let a rare entry compete with a common one.
    """
    return max(1, ranking_freq(lemma))


def assign_layer(lemma: Lemma) -> str | None:
    if lemma.status == "rejected":
        return None
    if "untrusted_reading" in lemma.flags:
        return None
    if "emoji" in lemma.flags or lemma.entity_type == "emoji" or "emoji" in lemma.categories:
        return "emoji"
    if "correction" in lemma.flags:
        return "corrections"
    if is_wiki_only(lemma):
        # Wikipedia titles are encyclopedia entries, not typing vocabulary.
        # Measured on the locked store: 465k wiki-only rows, none of them
        # carry any essay frequency, and no product probe word depends on
        # one. They stay in the store as coverage evidence but must never
        # reach a candidate list.
        return None
    if is_coverage_only(lemma):
        return "bulk"
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
    if n == 0:
        if lemma.status == "gold":
            return "brands"
        return None
    if n == 1:
        if lemma.status == "gold" or "tgh" in lemma.flags or any(ref.source_id == "chars" for ref in lemma.sources):
            return "chars"
        return None
    if n in {2, 3} and lemma.status in {"gold", "auto"}:
        return "base"
    if lemma.status == "gold" and n >= 4:
        return "ext"
    if n == 4:
        return "ext"
    if "polyphone" in lemma.flags and lemma.status != "gold":
        return None
    return "bulk"
