from __future__ import annotations

from pathlib import Path

from umate_lexicon.ingest.io import read_ingest_text
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore


def ingest_gold(store: LemmaStore, path: Path) -> int:
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
        toned = parts[2].strip() if len(parts) > 2 and parts[2].strip() else None
        store.upsert(
            Lemma(
                surface=surface,
                pinyin_plain=pinyin,
                pinyin_toned=toned,
                weight=1000,
                status="gold",
                flags=["gold"],
                domain_freq={"gold": 1000},
                sources=[SourceRef("gold", "umate-gold", str(path))],
            )
        )
        count += 1
    return count
