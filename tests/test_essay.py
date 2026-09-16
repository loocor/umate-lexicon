from pathlib import Path

from umate_lexicon.ingest.chars import ingest_chars
from umate_lexicon.ingest.essay import ingest_essay
from umate_lexicon.ingest.gold import ingest_gold
from umate_lexicon.ingest.luna import ingest_luna
from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore


def test_essay_overlays_existing_and_does_not_invent_pinyin(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    ingest_gold(store, data_dir() / "gold" / "product-terms.tsv")
    ingest_chars(store, data_dir() / "fixtures" / "chars.tsv")
    ingest_luna(store, data_dir() / "fixtures" / "luna.dict.yaml")
    count = ingest_essay(store, data_dir() / "fixtures" / "essay.txt")
    assert count >= 1
    weixin = store.get("微信", "wei xin")
    assert weixin is not None
    assert weixin.status == "gold"
    assert weixin.domain_freq["essay"] == 31877
    bank = store.get("銀行", "yin hang")
    assert bank is not None
    assert bank.domain_freq["essay"] == 36856
    store.close()
