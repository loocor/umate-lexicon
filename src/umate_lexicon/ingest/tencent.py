from __future__ import annotations

from pathlib import Path

from umate_lexicon.ingest.compose import compose_pinyin, is_han_only, overlay_domain_freq
from umate_lexicon.ingest.io import iter_ingest_text
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore
from umate_lexicon.t2s import SimplifyFn

LICENSE_ID = "cc-by-3.0-tencent"

OVERLAY = "overlay"
UPSERT = "upsert"
SKIP_EMPTY = "skip_empty"
SKIP_NON_HAN = "skip_non_han_without_gold"
SKIP_LENGTH_1 = "skip_length_1"
SKIP_LENGTH_GT4 = "skip_length_gt4"
SKIP_COMPOSE = "skip_compose"


def ingest_tencent(
    store: LemmaStore,
    path: Path,
    locator: str | None = None,
    simplify: SimplifyFn | None = None,
) -> int:
    count = 0
    source = locator or f"tencent:{path.name}"
    for raw in iter_ingest_text(path):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parsed = parse_tencent_line(line)
        if parsed is None:
            continue
        surface, freq = parsed
        if simplify is not None:
            surface = simplify(surface)
        action = classify_tencent_surface(store, surface)
        if action == OVERLAY:
            count += overlay_domain_freq(
                store,
                surface,
                domain="tencent",
                freq=freq,
                source_id="tencent",
                license_id=LICENSE_ID,
                locator=source,
            )
            continue
        if action != UPSERT:
            continue
        pinyin = compose_pinyin(store, surface)
        if pinyin is None:
            continue
        store.upsert(
            Lemma(
                surface=surface,
                pinyin_plain=pinyin,
                weight=freq,
                status="auto",
                domain_freq={"tencent": freq},
                sources=[SourceRef("tencent", LICENSE_ID, source)],
            )
        )
        count += 1
    return count


def classify_tencent_surface(store: LemmaStore, surface: str) -> str:
    if not surface:
        return SKIP_EMPTY
    if not is_han_only(surface):
        existing = store.readings_for(surface)
        if any(item.status == "gold" for item in existing):
            return OVERLAY
        return SKIP_NON_HAN
    if len(surface) == 1:
        return SKIP_LENGTH_1
    if any(item.status != "rejected" for item in store.readings_for(surface)):
        return OVERLAY
    if len(surface) > 4:
        return SKIP_LENGTH_GT4
    if compose_pinyin(store, surface) is None:
        return SKIP_COMPOSE
    return UPSERT


def parse_tencent_line(line: str) -> tuple[str, int] | None:
    parts = line.split()
    if not parts:
        return None
    surface = parts[0]
    rest = parts[1:]
    if len(rest) == 1 and rest[0].isdigit():
        return surface, int(rest[0])
    if rest and all(_is_float(token) for token in rest):
        return surface, 1
    if not rest:
        return surface, 1
    return surface, 1


def _is_float(token: str) -> bool:
    try:
        float(token)
    except ValueError:
        return False
    return True
