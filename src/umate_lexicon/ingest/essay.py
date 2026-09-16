from __future__ import annotations

from pathlib import Path

from umate_lexicon.ingest.compose import compose_pinyin, overlay_domain_freq
from umate_lexicon.ingest.io import read_ingest_text
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore

LICENSE_ID = "lgpl-rime-essay"


def ingest_essay(store: LemmaStore, path: Path, locator: str | None = None) -> int:
    text = read_ingest_text(path)
    count = 0
    source = locator or f"essay:{path.name}"
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        surface = parts[0].strip()
        freq_s = parts[1].strip() if len(parts) > 1 else ""
        freq = int(freq_s) if freq_s.isdigit() else 1
        if not surface:
            continue
        overlaid = overlay_domain_freq(
            store,
            surface,
            domain="essay",
            freq=freq,
            source_id="essay",
            license_id=LICENSE_ID,
            locator=source,
        )
        if overlaid:
            count += overlaid
            continue
        if len(surface) < 2:
            continue
        pinyin = compose_pinyin(store, surface)
        if pinyin is None:
            continue
        store.upsert(
            Lemma(
                surface=surface,
                pinyin_plain=pinyin,
                weight=freq,
                status="auto",
                domain_freq={"essay": freq},
                sources=[SourceRef("essay", LICENSE_ID, source)],
            )
        )
        count += 1
    return count
