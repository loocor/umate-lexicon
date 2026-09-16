from pathlib import Path

from umate_lexicon.ingest.chars import ingest_chars
from umate_lexicon.ingest.gold import ingest_gold
from umate_lexicon.ingest.tencent import ingest_tencent, parse_tencent_line
from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore


def test_parses_freq_and_embedding_lines() -> None:
    assert parse_tencent_line("微信\t100") == ("微信", 100)
    assert parse_tencent_line("人工智能 0.12 -0.03 0.44") == ("人工智能", 1)
    assert parse_tencent_line("xyz") == ("xyz", 1)


def test_covers_unique_han_and_overlays_gold_latin(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    ingest_gold(store, data_dir() / "gold" / "product-terms.tsv")
    ingest_chars(store, data_dir() / "fixtures" / "chars.tsv")
    count = ingest_tencent(store, data_dir() / "fixtures" / "tencent.txt")
    assert count >= 2
    weixin = store.get("微信", "wei xin")
    assert weixin is not None
    assert weixin.domain_freq["tencent"] == 100
    ai = store.get("人工智能", "ren gong zhi neng")
    assert ai is not None
    assert ai.domain_freq["tencent"] == 1
    assert store.get("的", "de") is None or "tencent" not in (store.get("的", "de").domain_freq)
    vector = store.get("向量数据库", "xiang liang shu ju ku")
    assert vector is not None
    assert vector.status == "gold"
    assert vector.domain_freq["tencent"] == 3
    brand = store.get("umate", "umate")
    assert brand is not None
    assert brand.domain_freq["tencent"] == 8
    store.close()
