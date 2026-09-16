from __future__ import annotations

from pathlib import Path

from collections import Counter
from collections.abc import Iterator

from umate_lexicon.ingest.compose import compose_pinyin, is_han_only, overlay_domain_freq
from umate_lexicon.ingest.io import read_ingest_text
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore
from umate_lexicon.t2s import SimplifyFn

LICENSE_ID = "cc-by-3.0-tencent"

# Coverage gates. Tencent is presence-only; essay keeps ranking.
DROP_EMPTY = "drop_empty"
DROP_NON_HAN = "drop_non_han"
DROP_SINGLE_CHAR = "drop_single_char"
DROP_TOO_LONG = "drop_too_long"
DROP_NO_UNIQUE_PINYIN = "drop_no_unique_pinyin"
OVERLAY_GOLD_NON_HAN = "overlay_gold_non_han"
OVERLAY_EXISTING = "overlay_existing"
ACCEPT_NEW = "accept_new"


def classify_tencent_surface(store: LemmaStore, surface: str) -> str:
    """Return the factory gate for one Tencent vocab surface."""
    if not surface:
        return DROP_EMPTY
    if not is_han_only(surface):
        existing = store.readings_for(surface)
        if any(item.status == "gold" for item in existing):
            return OVERLAY_GOLD_NON_HAN
        return DROP_NON_HAN
    if len(surface) == 1:
        return DROP_SINGLE_CHAR
    existing = [item for item in store.readings_for(surface) if item.status != "rejected"]
    if existing:
        return OVERLAY_EXISTING
    if len(surface) > 4:
        return DROP_TOO_LONG
    if compose_pinyin(store, surface) is None:
        return DROP_NO_UNIQUE_PINYIN
    return ACCEPT_NEW


def ingest_tencent(
    store: LemmaStore,
    path: Path,
    locator: str | None = None,
    simplify: SimplifyFn | None = None,
) -> int:
    text = read_ingest_text(path)
    count = 0
    source = locator or f"tencent:{path.name}"
    for raw in text.splitlines():
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
        if action in {DROP_EMPTY, DROP_NON_HAN, DROP_SINGLE_CHAR, DROP_TOO_LONG, DROP_NO_UNIQUE_PINYIN}:
            continue
        if action in {OVERLAY_GOLD_NON_HAN, OVERLAY_EXISTING}:
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


def iter_tencent_classifications(
    store: LemmaStore,
    path: Path,
    simplify: SimplifyFn | None = None,
) -> Iterator[tuple[str, str]]:
    """Yield (surface, gate) for each non-comment vocab line without writing."""
    text = read_ingest_text(path)
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parsed = parse_tencent_line(line)
        if parsed is None:
            yield "", DROP_EMPTY
            continue
        surface, _freq = parsed
        if simplify is not None:
            surface = simplify(surface)
        yield surface, classify_tencent_surface(store, surface)


def summarize_tencent_gates(
    store: LemmaStore,
    path: Path,
    simplify: SimplifyFn | None = None,
    sample_limit: int = 8,
) -> dict[str, object]:
    counts: Counter[str] = Counter()
    samples: dict[str, list[str]] = {}
    for surface, action in iter_tencent_classifications(store, path, simplify=simplify):
        counts[action] += 1
        bucket = samples.setdefault(action, [])
        if surface and len(bucket) < sample_limit:
            bucket.append(surface)
    kept = counts[OVERLAY_GOLD_NON_HAN] + counts[OVERLAY_EXISTING] + counts[ACCEPT_NEW]
    dropped = sum(counts.values()) - kept
    return {
        "raw_lines": sum(counts.values()),
        "kept": kept,
        "dropped": dropped,
        "overlap": counts[OVERLAY_EXISTING] + counts[OVERLAY_GOLD_NON_HAN],
        "new_coverage": counts[ACCEPT_NEW],
        "gates": dict(counts),
        "samples": samples,
    }


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
