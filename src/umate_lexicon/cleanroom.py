from __future__ import annotations

from pathlib import Path

BLOCKED_PATH_FRAGMENTS = (
    "rime-ice",
    "rime_ice",
    "idvel",
    "rime-wanxiang",
    "rime_wanxiang",
    "melt_eng",
)

BLOCKED_CONTENT_MARKERS = (
    "「霧凇拼音」",
    "雾凇拼音",
    "github.com/idvel/rime-ice",
    "github.com/amzxyz/rime-wanxiang",
)


class CleanRoomError(ValueError):
    pass


def assert_ingest_allowed(path: Path, preview: str = "") -> None:
    lowered_path = str(path).lower()
    for fragment in BLOCKED_PATH_FRAGMENTS:
        if fragment in lowered_path:
            raise CleanRoomError(f"blocked path fragment {fragment!r}: {path}")
    haystack = preview.lower()
    for marker in BLOCKED_CONTENT_MARKERS:
        if marker.lower() in haystack:
            raise CleanRoomError(f"blocked content marker {marker!r} in {path}")
