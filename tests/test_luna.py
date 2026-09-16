from pathlib import Path

from umate_lexicon.ingest.luna import ingest_luna
from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore


def test_ingests_spaced_pinyin_and_skips_bopomofo(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    count = ingest_luna(store, data_dir() / "fixtures" / "luna.dict.yaml")
    assert count >= 3
    hello = store.get("你好", "ni hao")
    assert hello is not None
    assert hello.script == "hant"
    assert hello.domain_freq["luna"] == 1
    assert hello.sources[0].license == "lgpl-rime-luna"
    assert store.get("ㄓ", "zhi") is None
    zao = store.get("繰", "zao")
    assert zao is not None
    assert zao.domain_freq["luna"] == 1
    store.close()
