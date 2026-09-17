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
        plain = preferred_plain(store.readings_for(char))
        if plain is None:
            return None
        syllables.append(plain)
    if not syllables:
        return None
    return " ".join(syllables)


def preferred_plain(lemmas: list[Lemma]) -> str | None:
    """Pick one plain reading for phrase baking.

    Polyphones often carry several trusted plains (和 he/hu/huo). Dropping the
    whole phrase made skeleton bigrams like 我和 / 我的 disappear from the
    store. Prefer TGH / gold, then denser trusted evidence, then weight.
    """
    usable = [
        item
        for item in lemmas
        if item.status != "rejected" and "untrusted_reading" not in item.flags
    ]
    trusted = [item for item in usable if is_trusted_reading(item)]
    pool = trusted if trusted else usable
    plains = _unique_plain(pool)
    if len(plains) == 1:
        return plains[0]
    if not plains:
        return None
    best_by_plain: dict[str, Lemma] = {}
    for lemma in pool:
        current = best_by_plain.get(lemma.pinyin_plain)
        if current is None or _reading_score(lemma) > _reading_score(current):
            best_by_plain[lemma.pinyin_plain] = lemma
    return max(best_by_plain.values(), key=_reading_score).pinyin_plain


def _reading_score(lemma: Lemma) -> tuple[int, int, int, int]:
    trusted_sources = sum(1 for ref in lemma.sources if ref.source_id in TRUSTED_SOURCE_IDS)
    return (
        1 if "tgh" in lemma.flags else 0,
        1 if lemma.status == "gold" or "gold" in lemma.flags else 0,
        trusted_sources,
        int(lemma.weight),
    )


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
