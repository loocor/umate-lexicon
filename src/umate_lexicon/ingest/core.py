from __future__ import annotations

from pathlib import Path

from umate_lexicon.ingest.compose import compose_pinyin, overlay_domain_freq
from umate_lexicon.ingest.io import read_ingest_text
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore
from umate_lexicon.t2s import SimplifyFn
from umate_lexicon.sources import sha256_file

# Attribution stays: the absorbed word list derives from rime-essay (LGPL-3.0).
LICENSE_ID = "lgpl-rime-essay"


def absorbed_core_path() -> Path:
    from umate_lexicon.paths import data_dir

    return data_dir() / "voimate" / "absorbed-core.tsv"


def verify_absorbed_core() -> Path:
    """Integrity-check the in-repo absorbed snapshot against its pinned hash."""
    path = absorbed_core_path()
    expected = path.with_suffix(".sha256").read_text(encoding="utf-8").strip()
    digest = sha256_file(path)
    if digest != expected:
        raise ValueError(
            f"absorbed-core.tsv hash mismatch: expected {expected}, got {digest}"
        )
    return path


def ingest_core(
    store: LemmaStore,
    path: Path,
    locator: str | None = None,
    simplify: SimplifyFn | None = None,
) -> int:
    text = read_ingest_text(path)
    count = 0
    source = locator or f"absorbed:{path.name}"
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        surface = parts[0].strip()
        if simplify is not None:
            surface = simplify(surface)
        freq_s = parts[1].strip() if len(parts) > 1 else ""
        freq = int(freq_s) if freq_s.isdigit() else 1
        if not surface:
            continue
        overlaid = overlay_domain_freq(
            store,
            surface,
            domain="core",
            freq=freq,
            source_id="umate-core",
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
                domain_freq={"core": freq},
                sources=[SourceRef("umate-core", LICENSE_ID, source)],
            )
        )
        count += 1
    return count
