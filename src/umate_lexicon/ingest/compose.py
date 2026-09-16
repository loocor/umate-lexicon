from __future__ import annotations

import re

from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore

_HAN_ONLY = re.compile(r"^[\u4e00-\u9fff]+$")


def is_han_only(surface: str) -> bool:
    return bool(surface) and _HAN_ONLY.fullmatch(surface) is not None


def compose_pinyin(store: LemmaStore, surface: str) -> str | None:
    syllables: list[str] = []
    for char in surface:
        readings = store.char_plain(char)
        if len(readings) != 1:
            return None
        syllables.append(readings[0])
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
    existing = store.readings_for(surface)
    if not existing:
        return 0
    count = 0
    for lemma in existing:
        if lemma.status == "rejected":
            continue
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
