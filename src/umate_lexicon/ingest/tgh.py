from __future__ import annotations

import re
from pathlib import Path

from umate_lexicon.ingest.io import read_ingest_text
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore

_LINE = re.compile(r"^U\+([0-9A-F]+)\tkTGH\t(.+)$")
LICENSE_ID = "unicode"


def ingest_tgh(store: LemmaStore, path: Path, locator: str | None = None) -> int:
    """Mark 通用规范汉字表 (8105) characters using Unihan kTGH."""
    text = read_ingest_text(path)
    source = locator or f"tgh:{path.name}"
    count = 0
    for raw in text.splitlines():
        match = _LINE.match(raw.strip())
        if match is None:
            continue
        surface = chr(int(match.group(1), 16))
        readings = store.readings_for(surface)
        if not readings:
            continue
        for lemma in readings:
            if lemma.status == "rejected":
                continue
            flags = list(lemma.flags)
            if "tgh" not in flags:
                flags.append("tgh")
            store.upsert(
                Lemma(
                    surface=lemma.surface,
                    pinyin_plain=lemma.pinyin_plain,
                    flags=flags,
                    sources=[SourceRef("tgh", LICENSE_ID, source)],
                )
            )
            count += 1
    return count
