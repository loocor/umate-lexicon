from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from umate_lexicon.ingest.io import read_ingest_text
from umate_lexicon.ingest.tencent import (
    OVERLAY,
    SKIP_COMPOSE,
    SKIP_EMPTY,
    SKIP_LENGTH_1,
    SKIP_LENGTH_GT4,
    SKIP_NON_HAN,
    UPSERT,
    classify_tencent_surface,
    parse_tencent_line,
)
from umate_lexicon.layers import COVERAGE_SOURCE_IDS, assign_layer, is_coverage_only
from umate_lexicon.store import LemmaStore

SimplifyFn = Callable[[str], str]

PRESENT_PROBES = ("微信", "人工智能", "银行卡")
ABSENT_PROBES = ("元宇宙", "新冠病毒", "yyds")


@dataclass
class TencentAbsorbStats:
    surfaces: int = 0
    overlaid_surfaces: int = 0
    overlaid_curated_surfaces: int = 0
    wiki_overlap_surfaces: int = 0
    upserted_surfaces: int = 0
    skipped_non_han_without_gold: int = 0
    skipped_length_1: int = 0
    skipped_length_gt4: int = 0
    skipped_compose: int = 0
    skipped_empty: int = 0
    overlaid_surface_set: set[str] = field(default_factory=set)
    overlaid_curated_surface_set: set[str] = field(default_factory=set)
    wiki_overlap_surface_set: set[str] = field(default_factory=set)
    upserted_surface_set: set[str] = field(default_factory=set)
    tencent_lemmas: int = 0
    tencent_only_lemmas: int = 0
    layers_touched: dict[str, int] = field(default_factory=dict)
    tencent_only_layers: dict[str, int] = field(default_factory=dict)
    tencent_freq_values: dict[int, int] = field(default_factory=dict)
    vectors_in_store: int = 0
    probes_present: dict[str, bool] = field(default_factory=dict)
    probes_absent: dict[str, bool] = field(default_factory=dict)


def measure_tencent_absorb(
    store: LemmaStore,
    path: Path,
    simplify: SimplifyFn | None = None,
) -> TencentAbsorbStats:
    stats = TencentAbsorbStats()
    seen: set[str] = set()
    for raw in read_ingest_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parsed = parse_tencent_line(line)
        if parsed is None:
            continue
        surface, _freq = parsed
        if simplify is not None:
            surface = simplify(surface)
        if surface in seen:
            continue
        seen.add(surface)
        stats.surfaces += 1
        lemmas = [item for item in store.readings_for(surface) if item.status != "rejected"]
        tencent_lemmas = [
            item for item in lemmas if any(ref.source_id == "tencent" for ref in item.sources)
        ]
        if tencent_lemmas:
            source_ids = {
                ref.source_id for item in tencent_lemmas for ref in item.sources
            }
            if source_ids == {"tencent"}:
                stats.upserted_surfaces += 1
                stats.upserted_surface_set.add(surface)
            elif source_ids <= COVERAGE_SOURCE_IDS:
                stats.wiki_overlap_surfaces += 1
                stats.wiki_overlap_surface_set.add(surface)
                stats.overlaid_surfaces += 1
                stats.overlaid_surface_set.add(surface)
            else:
                stats.overlaid_curated_surfaces += 1
                stats.overlaid_curated_surface_set.add(surface)
                stats.overlaid_surfaces += 1
                stats.overlaid_surface_set.add(surface)
            continue
        action = classify_tencent_surface(store, surface)
        if action == SKIP_NON_HAN:
            stats.skipped_non_han_without_gold += 1
        elif action == SKIP_LENGTH_1:
            stats.skipped_length_1 += 1
        elif action == SKIP_LENGTH_GT4:
            stats.skipped_length_gt4 += 1
        elif action == SKIP_COMPOSE:
            stats.skipped_compose += 1
        elif action == SKIP_EMPTY:
            stats.skipped_empty += 1
        elif action in {OVERLAY, UPSERT}:
            # Gate says absorb, but store has no tencent stamp — count as compose miss.
            stats.skipped_compose += 1
    layers: Counter[str] = Counter()
    only_layers: Counter[str] = Counter()
    freqs: Counter[int] = Counter()
    for lemma in store.all_lemmas():
        if "tencent" not in {ref.source_id for ref in lemma.sources}:
            continue
        stats.tencent_lemmas += 1
        freq = lemma.domain_freq.get("tencent")
        if freq is not None:
            freqs[freq] += 1
        layer = assign_layer(lemma) or "dropped"
        layers[layer] += 1
        if is_coverage_only(lemma) and {ref.source_id for ref in lemma.sources} == {"tencent"}:
            stats.tencent_only_lemmas += 1
            only_layers[layer] += 1
        for value in lemma.domain_freq.values():
            if isinstance(value, str) or (isinstance(value, float) and not float(value).is_integer()):
                stats.vectors_in_store += 1
    stats.layers_touched = dict(layers)
    stats.tencent_only_layers = dict(only_layers)
    stats.tencent_freq_values = {int(key): count for key, count in freqs.items()}
    stats.probes_present = {name: _surface_present(store, name) for name in PRESENT_PROBES}
    stats.probes_absent = {name: not _surface_present(store, name) for name in ABSENT_PROBES}
    return stats


def _surface_present(store: LemmaStore, surface: str) -> bool:
    return any(item.status != "rejected" for item in store.readings_for(surface))


def render_tencent_absorb(stats: TencentAbsorbStats) -> str:
    lines = [
        f"surfaces\t{stats.surfaces}",
        f"overlaid_surfaces\t{stats.overlaid_surfaces}",
        f"overlaid_curated_surfaces\t{stats.overlaid_curated_surfaces}",
        f"wiki_overlap_surfaces\t{stats.wiki_overlap_surfaces}",
        f"upserted_surfaces\t{stats.upserted_surfaces}",
        f"skipped_non_han_without_gold\t{stats.skipped_non_han_without_gold}",
        f"skipped_length_1\t{stats.skipped_length_1}",
        f"skipped_length_gt4\t{stats.skipped_length_gt4}",
        f"skipped_compose\t{stats.skipped_compose}",
        f"tencent_lemmas\t{stats.tencent_lemmas}",
        f"tencent_only_lemmas\t{stats.tencent_only_lemmas}",
        "layer_touched\tcount",
    ]
    for key, value in sorted(stats.layers_touched.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"{key}\t{value}")
    lines.append("tencent_only_layer\tcount")
    for key, value in sorted(stats.tencent_only_layers.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"{key}\t{value}")
    lines.append("tencent_freq\tcount")
    for key, value in sorted(stats.tencent_freq_values.items()):
        lines.append(f"{key}\t{value}")
    lines.append(f"vectors_in_store\t{stats.vectors_in_store}")
    lines.append("probe\tsurface\texpected\tok")
    for surface, present in stats.probes_present.items():
        lines.append(f"present\t{surface}\tyes\t{'yes' if present else 'no'}")
    for surface, absent in stats.probes_absent.items():
        lines.append(f"absent\t{surface}\tno\t{'yes' if absent else 'no'}")
    return "\n".join(lines) + "\n"
