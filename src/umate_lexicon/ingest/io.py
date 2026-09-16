from __future__ import annotations

from pathlib import Path

from umate_lexicon.cleanroom import assert_ingest_allowed


def read_ingest_text(path: Path, limit: int = 4000) -> str:
    data = path.read_text(encoding="utf-8-sig")
    assert_ingest_allowed(path, data[:limit])
    return data
