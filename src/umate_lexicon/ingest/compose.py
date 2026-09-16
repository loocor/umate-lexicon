from __future__ import annotations

import re

from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore

_HAN_ONLY = re.compile(r"^[\u4e00-\u9fff]+$")
TRUSTED_SOURCE_IDS = frozenset({"gold", "cedict", "unihan", "chars", "tgh"})


def is_han_only(surface: str) -> bool:
    return bool(surface) and _HAN_ONLY.fullmatch(surface) is not None


def is_trusted_reading(lemma: Lemma) -> bool:
    if lemma.status == "rejected":
        return False
    if lemma.status == "gold" or "gold" in lemma.flags:
        return True
    return any(ref.source_id in TRUSTED_SOURCE_IDS for ref in lemma.sources)


def compose_pinyin(store: LemmaStore, surface: str) -> str | None:
    syllables: list[str] = []
    for char in surface:
        lemmas = store.readings_for(char)
        trusted = [item for item in lemmas if is_trusted_reading(item)]
        plains = _unique_plain(trusted if trusted else lemmas)
        if len(plains) != 1:
            return None
        syllables.append(plains[0])
    if not syllables:
        return None
    return " ".join(syllables)


def overlay_domain_freq(
    store: LemmaStore,
    surface: str,
    *,
    domain: str,
    freq: int,
    source_id: str,
    license_id: str,
    locator: str,
) -> int:
    existing = [item for item in store.readings_for(surface) if item.status != "rejected"]
    if not existing:
        return 0
    trusted = [item for item in existing if is_trusted_reading(item)]
    targets = trusted if trusted else existing
    count = 0
    for lemma in targets:
        store.upsert(
            Lemma(
                surface=lemma.surface,
                pinyin_plain=lemma.pinyin_plain,
                weight=freq,
                status="auto",
                domain_freq={domain: freq},
                sources=[SourceRef(source_id, license_id, locator)],
            )
        )
        count += 1
    return count


def _unique_plain(lemmas: list[Lemma]) -> list[str]:
    plains: list[str] = []
    for lemma in lemmas:
        if lemma.status == "rejected":
            continue
        if lemma.pinyin_plain not in plains:
            plains.append(lemma.pinyin_plain)
    return plains
