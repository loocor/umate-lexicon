from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from umate_lexicon.cleanroom import assert_ingest_allowed


def read_ingest_text(path: Path, limit: int = 4000) -> str:
    data = path.read_text(encoding="utf-8-sig")
    assert_ingest_allowed(path, data[:limit])
    return data


def iter_ingest_text(path: Path, limit: int = 4000) -> Iterator[str]:
    with path.open("r", encoding="utf-8-sig") as handle:
        preview = handle.read(limit)
        assert_ingest_allowed(path, preview)
        handle.seek(0)
        yield from handle
