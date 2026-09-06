from pathlib import Path

import pytest

from umate_lexicon.cleanroom import CleanRoomError, assert_ingest_allowed


def test_blocks_rime_ice_path(tmp_path: Path) -> None:
    path = tmp_path / "vendor" / "rime-ice" / "cn_dicts" / "base.dict.yaml"
    with pytest.raises(CleanRoomError):
        assert_ingest_allowed(path, "hello")


def test_blocks_ice_banner(tmp_path: Path) -> None:
    path = tmp_path / "innocent.dict.yaml"
    with pytest.raises(CleanRoomError):
        assert_ingest_allowed(path, "# 雾凇拼音词库")


def test_allows_cedict_sample(tmp_path: Path) -> None:
    path = tmp_path / "cedict.txt"
    assert_ingest_allowed(path, "你好 你好 [ni3 hao3] /hello/")
