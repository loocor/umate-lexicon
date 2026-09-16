from __future__ import annotations

from pathlib import Path

from umate_lexicon.ingest.io import read_ingest_text
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore


def ingest_thuocl(store: LemmaStore, path: Path, domain: str = "thuocl", locator: str | None = None) -> int:
    text = read_ingest_text(path)
    count = 0
    source = locator or str(path)
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        surface = parts[0].strip()
        freq = parts[1].strip() if len(parts) > 1 else ""
        df = int(freq) if freq.isdigit() else 1
        pinyin = compose_pinyin(store, surface)
        if pinyin is None:
            continue
        store.upsert(
            Lemma(
                surface=surface,
                pinyin_plain=pinyin,
                weight=df,
                status="auto",
                categories=_categories_from_name(path.name),
                entity_type=_entity_from_name(path.name),
                domain_freq={domain: df},
                sources=[SourceRef("thuocl", "mit-thuocl", source)],
            )
        )
        count += 1
    return count


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


def _categories_from_name(name: str) -> list[str]:
    lowered = name.lower()
    mapping = {
        "it": "industry",
        "diming": "place",
        "lishimingren": "person",
        "medical": "industry",
        "law": "industry",
        "caijing": "industry",
        "car": "brand",
        "food": "industry",
        "animal": "industry",
        "chengyu": "idiom",
        "poem": "literary",
    }
    for key, value in mapping.items():
        if key in lowered:
            return [value]
    return []


def _entity_from_name(name: str) -> str | None:
    cats = _categories_from_name(name)
    return cats[0] if cats else None
