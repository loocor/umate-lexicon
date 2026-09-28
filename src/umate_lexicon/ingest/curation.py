from __future__ import annotations

from pathlib import Path

from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore

SOURCE_ID = "voimate-curation"
LICENSE_ID = "voimate-curation"

PINYIN_HOT_BASE = 6000
PINYIN_HOT_DECAY = 0.6


def curated_weight(rank: int) -> int:
    """Tier A weight for the rank-th curated emoji of one trigger (1-based)."""
    return round(PINYIN_HOT_BASE * (PINYIN_HOT_DECAY ** max(0, rank - 1)))


def _row(sound: str, surface: str, rank: int, locator: str) -> Lemma:
    return Lemma(
        surface=surface,
        pinyin_plain=sound,
        weight=curated_weight(rank),
        status="auto",
        categories=["emoji"],
        flags=["emoji", "curated"],
        entity_type="emoji",
        domain_freq={"emoji-curation": 1, "curation_rank": max(1, rank)},
        sources=[SourceRef(SOURCE_ID, LICENSE_ID, locator)],
    )


def ingest_pinyin_emoji_curation(store: LemmaStore, path: Path) -> int:
    """Curated pinyin → emoji rows. Tier A: engine-visible, weight-decayed.

    Keys are tone-less pinyin codes already, so no compose step: the code
    is exactly what a Chinese composition spells.
    """
    count = 0
    for raw in read_rows(path):
        key, emojis = raw
        for rank, emoji in enumerate(emojis, start=1):
            store.upsert(_row(key, emoji, rank, f"{SOURCE_ID}:pinyin:{key}"))
            count += 1
    return count


def ingest_english_emoji_curation(store: LemmaStore, path: Path) -> int:
    """Curated English trigger words → word + emoji rows, per-letter codes.

    `ok` becomes code `o k`; `okay` becomes `o k a y`. Single-letter keys
    are skipped: one letter is always a live pinyin syllable and must not
    carry an emoji association.
    """
    count = 0
    for raw in read_rows(path):
        key, emojis = raw
        letters = [ch for ch in key.lower() if ch.isascii() and ch.isalpha()]
        if len(letters) < 2 or letters != list(key.lower()):
            continue
        code = " ".join(letters)
        rows: list[tuple[str, int]] = [(key, 1)]
        capitalized = key.capitalize()
        if capitalized != key:
            rows.append((capitalized, 2))
        for rank, emoji in enumerate(emojis, start=3):
            rows.append((emoji, rank))
        for surface, rank in rows:
            store.upsert(_row(code, surface, rank, f"{SOURCE_ID}:english:{key}"))
            count += 1
    return count


def read_rows(path: Path) -> list[tuple[str, list[str]]]:
    rows: list[tuple[str, list[str]]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        key = parts[0].strip().lower()
        emojis = [
            token.strip() for token in parts[1].split("|") if token.strip()
        ]
        if key and emojis:
            rows.append((key, emojis))
    return rows
