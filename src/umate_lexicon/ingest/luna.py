from __future__ import annotations

import re
from pathlib import Path

from umate_lexicon.ingest.io import read_ingest_text
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.pinyin import looks_like_pinyin, normalize_plain_pinyin
from umate_lexicon.store import LemmaStore

_BOPOMOFO = re.compile(r"[\u3100-\u312f\u31a0-\u31bf]")
_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
LICENSE_ID = "lgpl-rime-luna"


def ingest_luna(store: LemmaStore, path: Path, locator: str | None = None) -> int:
    text = read_ingest_text(path)
    body = _body_after_header(text)
    count = 0
    source = locator or f"luna:{path.name}"
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        surface = parts[0].strip()
        code = normalize_plain_pinyin(parts[1])
        if not _surface_ok(surface) or not looks_like_pinyin(code):
            continue
        if len(surface) != len(code.split()):
            continue
        weight = 1
        if len(parts) >= 3 and parts[2].strip().isdigit():
            parsed = int(parts[2].strip())
            if parsed > 0:
                weight = parsed
        store.upsert(
            Lemma(
                surface=surface,
                pinyin_plain=code,
                weight=weight,
                status="auto",
                script="hant",
                domain_freq={"luna": weight},
                sources=[SourceRef("luna", LICENSE_ID, source)],
            )
        )
        count += 1
    return count


def _body_after_header(text: str) -> str:
    marker = "\n..."
    index = text.find(marker)
    if index == -1:
        if text.startswith("..."):
            return text[3:]
        return ""
    return text[index + len(marker) :]


def _surface_ok(surface: str) -> bool:
    if not surface or _BOPOMOFO.search(surface):
        return False
    return _CJK.search(surface) is not None
