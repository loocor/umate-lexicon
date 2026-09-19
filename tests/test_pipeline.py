from pathlib import Path

from umate_lexicon.eval.gold import evaluate_store
from umate_lexicon.layers import assign_layer
from umate_lexicon.pipeline import _ingest_authored_gold, run_fixture_pipeline
from umate_lexicon.store import LemmaStore


def test_fixture_pipeline_passes_gold(tmp_path: Path) -> None:
    store_path = tmp_path / "lemmas.sqlite"
    out_dir = tmp_path / "rime"
    stats = run_fixture_pipeline(store_path=store_path, out_dir=out_dir)
    assert stats["eval_failures"] == 0
    assert stats["lemmas"] >= 4
    store = LemmaStore(store_path)
    assert evaluate_store(store) == []
    chongqing = store.get("重庆", "chong qing")
    assert chongqing is not None
    assert chongqing.status == "gold"
    assert (out_dir / "umate_hans.dict.yaml").exists()
    core = (out_dir / "umate_hans.dict.yaml").read_text(encoding="utf-8")
    assert "import_tables:" in core
    assert "umate_chars" in core
    assert "- umate_hot_tail" in core
    assert "umate_wiki_tail" not in core
    cold_core = (out_dir / "umate_hans_cold.dict.yaml").read_text(encoding="utf-8")
    assert "umate_wiki_tail" not in cold_core
    assert "- umate_hot_tail" not in cold_core
    assert (out_dir / "umate_hot_tail.dict.yaml").exists()
    bank = store.get("银行", "yin hang")
    assert bank is not None
    assert bank.domain_freq.get("essay") == 36856
    assert store.get("銀行", "yin hang") is None
    walk = store.get("行走", "xing zou")
    assert walk is not None
    model = store.get("大模型", "da mo xing")
    assert model is not None
    assert model.status == "gold"
    brand = store.get("umate", "umate")
    assert brand is not None
    assert brand.status == "gold"
    weixin = store.get("微信", "wei xin")
    assert weixin is not None
    assert weixin.status == "gold"
    assert weixin.domain_freq.get("essay") == 31877
    assert weixin.domain_freq.get("tencent") == 100
    assert assign_layer(weixin) == "base"
    ai = store.get("人工智能", "ren gong zhi neng")
    assert ai is not None
    assert {ref.source_id for ref in ai.sources} == {"tencent"}
    assert ai.domain_freq["tencent"] == 1
    assert assign_layer(ai) == "bulk"
    laugh = store.get("😂", "ha ha")
    assert laugh is not None
    assert (out_dir / "opencc" / "emoji_word.txt").exists()
    schema = (out_dir / "umate_hans.schema.yaml").read_text(encoding="utf-8")
    assert "umate_emoji" not in schema
    store.close()


def test_thuocl_composes_unique_chars(tmp_path: Path) -> None:
    store_path = tmp_path / "lemmas.sqlite"
    run_fixture_pipeline(store_path=store_path, out_dir=tmp_path / "rime")
    store = LemmaStore(store_path)
    lemma = store.get("文件备份", "wen jian bei fen")
    assert lemma is not None
    store.close()


def test_daily_gap_ledger_is_not_ingested_as_gold(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    _ingest_authored_gold(store)
    assert store.get("surface", "origin") is None
    assert store.get("偷偷", "user") is None
    store.close()
