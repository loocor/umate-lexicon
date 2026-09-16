from __future__ import annotations

import re

from umate_lexicon.layers import han_len, is_wiki_only
from umate_lexicon.lemma import Lemma

_PLACE_SUFFIX = re.compile(r"(市|县|区|镇|乡|村|州|省|盟|旗)$")
_ORG_SUFFIX = re.compile(r"(公司|集团|大学|学院|医院|银行|协会|委员会)$")
_LATIN = re.compile(r"[A-Za-z]")
_HAN = re.compile(r"[\u4e00-\u9fff]")


def _has_extra_suffix(surface: str, pattern: re.Pattern[str]) -> bool:
    match = pattern.search(surface)
    return match is not None and match.start() > 0


def classify(lemma: Lemma) -> Lemma:
    flags = list(lemma.flags)
    categories = list(lemma.categories)
    entity = lemma.entity_type
    if _LATIN.search(lemma.surface) and _HAN.search(lemma.surface):
        if "mixed_latin" not in flags:
            flags.append("mixed_latin")
        if "brand" not in categories:
            categories.append("brand")
        entity = entity or "brand"
    if is_wiki_only(lemma):
        lemma.flags = flags
        lemma.categories = categories
        lemma.entity_type = entity
        return lemma
    if _has_extra_suffix(lemma.surface, _PLACE_SUFFIX):
        if "place" not in categories:
            categories.append("place")
        entity = entity or "place"
    if _has_extra_suffix(lemma.surface, _ORG_SUFFIX):
        if "org" not in categories:
            categories.append("org")
        entity = entity or "org"
    if (
        entity == "place"
        and "gold" not in flags
        and han_len(lemma.surface) <= 3
        and not _has_extra_suffix(lemma.surface, _PLACE_SUFFIX)
    ):
        entity = None
        categories = [item for item in categories if item != "place"]
    lemma.flags = flags
    lemma.categories = categories
    lemma.entity_type = entity
    return lemma
