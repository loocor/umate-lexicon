from __future__ import annotations

from pathlib import Path

from umate_lexicon.ingest.io import read_ingest_text
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore


def ingest_chars(store: LemmaStore, path: Path, license_id: str = "standard-chars") -> int:
    text = read_ingest_text(path)
    count = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        surface, pinyin = parts[0], parts[1].strip().lower().replace("ü", "v")
        weight = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
        if len(surface) != 1 or not pinyin:
            continue
        store.upsert(
            Lemma(
                surface=surface,
                pinyin_plain=pinyin,
                weight=weight,
                status="auto",
                domain_freq={"chars": weight},
                sources=[SourceRef("chars", license_id, str(path))],
            )
        )
        count += 1
    return count
