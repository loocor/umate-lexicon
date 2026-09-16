from __future__ import annotations

import re
from pathlib import Path

from umate_lexicon.ingest.io import read_ingest_text
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore

_LINE = re.compile(r"^U\+([0-9A-F]+)\tkMandarin\t(.+)$")


def ingest_unihan(store: LemmaStore, path: Path, locator: str | None = None) -> int:
    text = read_ingest_text(path)
    count = 0
    source = locator or str(path)
    for raw in text.splitlines():
        match = _LINE.match(raw.strip())
        if match is None:
            continue
        surface = chr(int(match.group(1), 16))
        readings = [item.strip().lower() for item in match.group(2).split() if item.strip()]
        for reading in readings:
            plain = _kmandarin_to_plain(reading.lower())
            if not plain:
                continue
            store.upsert(
                Lemma(
                    surface=surface,
                    pinyin_plain=plain,
                    pinyin_toned=reading if _has_tone_mark(reading) else None,
                    weight=1,
                    status="auto",
                    domain_freq={"unihan": 1},
                    sources=[SourceRef("unihan", "unicode", source)],
                )
            )
            count += 1
    return count


def _has_tone_mark(text: str) -> bool:
    return any(ch in text for ch in "āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ")


def _kmandarin_to_plain(reading: str) -> str:
    table = str.maketrans(
        {
            "ā": "a",
            "á": "a",
            "ǎ": "a",
            "à": "a",
            "ē": "e",
            "é": "e",
            "ě": "e",
            "è": "e",
            "ī": "i",
            "í": "i",
            "ǐ": "i",
            "ì": "i",
            "ō": "o",
            "ó": "o",
            "ǒ": "o",
            "ò": "o",
            "ū": "u",
            "ú": "u",
            "ǔ": "u",
            "ù": "u",
            "ǖ": "v",
            "ǘ": "v",
            "ǚ": "v",
            "ǜ": "v",
            "ü": "v",
        }
    )
    return reading.translate(table)
