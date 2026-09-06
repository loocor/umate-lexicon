from __future__ import annotations

import re
from pathlib import Path

from umate_lexicon.ingest.io import read_ingest_text
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.pinyin import parse_cedict_pinyin_field
from umate_lexicon.store import LemmaStore

_LINE = re.compile(
    r"^(?P<trad>\S+)\s+(?P<simp>\S+)\s+\[(?P<pinyin>[^\]]+)\]\s+/(?P<gloss>.*)/$"
)


def ingest_cedict(store: LemmaStore, path: Path, locator: str | None = None) -> int:
    text = read_ingest_text(path)
    count = 0
    source = locator or str(path)
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _LINE.match(line)
        if match is None:
            continue
        surface = match.group("simp")
        plain, toned = parse_cedict_pinyin_field(match.group("pinyin"))
        if not surface or not plain:
            continue
        store.upsert(
            Lemma(
                surface=surface,
                pinyin_plain=plain,
                pinyin_toned=toned,
                weight=1,
                status="auto",
                domain_freq={"cedict": 1},
                sources=[SourceRef("cedict", "cc-by-sa-cedict", source)],
            )
        )
        count += 1
    return count
