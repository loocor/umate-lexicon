from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from umate_lexicon.layers import CORE_LAYERS, assign_layer, han_len, ranking_freq
from umate_lexicon.lemma import Lemma
from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore

# Buckets, in the order a report should print them. The first four mean the
# lemma cannot reach a candidate list; `present-shipped` means it can.
BUCKETS = (
    "missing",
    "segmentation",
    "present-filtered",
    "present-not-shipped",
    "present-ranked-low",
    "present-shipped",
)


@dataclass(frozen=True)
class GapReport:
    surface: str
    origin: str
    reported: str
    note: str


@dataclass(frozen=True)
class GapFinding:
    surface: str
    bucket: str
    detail: str
    readings: tuple[str, ...]
    layers: tuple[str, ...]


def default_gap_ledger() -> Path:
    return data_dir() / "gold" / "daily-gaps.tsv"


def load_gap_ledger(path: Path | None = None) -> list[GapReport]:
    target = path or default_gap_ledger()
    rows: list[GapReport] = []
    for raw in target.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        surface = parts[0].strip()
        if not surface or surface == "surface":
            continue
        rows.append(
            GapReport(
                surface=surface,
                origin=parts[1].strip() if len(parts) > 1 else "",
                reported=parts[2].strip() if len(parts) > 2 else "",
                note=parts[3].strip() if len(parts) > 3 else "",
            )
        )
    return rows


def char_floor(store: LemmaStore, surface: str, pinyin_plain: str) -> int | None:
    """Weakest ranking frequency among the characters that spell `surface`.

    A phrase whose own ranking frequency sits below this floor carries less
    evidence than the rarest character it is built from, so the engine has no
    reason to prefer the phrase over typing the characters one by one. Returns
    None when the syllables do not line up, which means the floor is unknown.
    """
    characters = list(surface)
    syllables = pinyin_plain.split()
    if len(characters) != len(syllables) or not characters:
        return None
    floors: list[int] = []
    for character, syllable in zip(characters, syllables):
        matches = [
            lemma
            for lemma in store.readings_for(character)
            if lemma.pinyin_plain == syllable and lemma.status != "rejected"
        ]
        if not matches:
            return None
        floors.append(max(ranking_freq(lemma) for lemma in matches))
    return min(floors)


def _is_composable(store: LemmaStore, surface: str) -> bool:
    characters = list(surface)
    if len(characters) < 2:
        return False
    return all(store.char_plain(character) for character in characters)


def _best_core(rows: list[tuple[str, Lemma]]) -> tuple[str, Lemma] | None:
    core = [item for item in rows if item[0] in CORE_LAYERS]
    if not core:
        return None
    return max(core, key=lambda item: ranking_freq(item[1]))


def classify_surface(store: LemmaStore, surface: str) -> GapFinding:
    lemmas = store.readings_for(surface)
    if not lemmas:
        if _is_composable(store, surface):
            return GapFinding(
                surface=surface,
                bucket="segmentation",
                detail="no phrase entry; every character has its own reading",
                readings=(),
                layers=(),
            )
        return GapFinding(
            surface=surface,
            bucket="missing",
            detail="no lemma and not composable from single characters",
            readings=(),
            layers=(),
        )

    layered = [(assign_layer(lemma), lemma) for lemma in lemmas]
    live = [(layer, lemma) for layer, lemma in layered if layer is not None]
    readings = tuple(sorted({lemma.pinyin_plain for lemma in lemmas}))
    layers = tuple(sorted({layer for layer, _ in live}))
    if not live:
        statuses = ",".join(sorted({lemma.status for lemma in lemmas}))
        flags = sorted({flag for lemma in lemmas for flag in lemma.flags})
        detail = f"status={statuses}"
        if flags:
            detail += f" flags={','.join(flags)}"
        return GapFinding(surface, "present-filtered", detail, readings, layers)

    best = _best_core(live)
    if best is None:
        return GapFinding(
            surface=surface,
            bucket="present-not-shipped",
            detail=f"only optional packs: {','.join(layers)}",
            readings=readings,
            layers=layers,
        )

    _layer, lemma = best
    floor = char_floor(store, lemma.surface, lemma.pinyin_plain)
    freq = ranking_freq(lemma)
    if han_len(lemma.surface) >= 2 and floor is not None and freq < floor:
        return GapFinding(
            surface=surface,
            bucket="present-ranked-low",
            detail=f"rank={freq} below character floor {floor}",
            readings=readings,
            layers=layers,
        )
    return GapFinding(
        surface=surface,
        bucket="present-shipped",
        detail=f"layer={_layer} rank={freq}"
        + (f"" if floor is None else f" floor={floor}"),
        readings=readings,
        layers=layers,
    )


def classify_ledger(store: LemmaStore, path: Path | None = None) -> list[tuple[GapReport, GapFinding]]:
    return [(row, classify_surface(store, row.surface)) for row in load_gap_ledger(path)]


def render_gaps(results: list[tuple[GapReport, GapFinding]]) -> str:
    counts: dict[str, int] = {bucket: 0 for bucket in BUCKETS}
    lines = [f"{'surface':<8} {'bucket':<20} {'readings':<24} detail"]
    for row, finding in results:
        counts[finding.bucket] = counts.get(finding.bucket, 0) + 1
        readings = " ".join(finding.readings) or "-"
        lines.append(
            f"{finding.surface:<8} {finding.bucket:<20} {readings:<24} {finding.detail}"
        )
        if row.note:
            lines.append(f"{'':<8} {'':<20} {'':<24} note: {row.note}")
    lines.append("")
    for bucket in BUCKETS:
        lines.append(f"{bucket}\t{counts.get(bucket, 0)}")
    return "\n".join(lines) + "\n"
