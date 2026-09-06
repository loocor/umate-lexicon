from pathlib import Path

from umate_lexicon.eval.gold import evaluate_store
from umate_lexicon.pipeline import run_fixture_pipeline
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
    bank = store.get("银行", "yin hang")
    assert bank is not None
    walk = store.get("行走", "xing zou")
    assert walk is not None
    store.close()


def test_thuocl_composes_unique_chars(tmp_path: Path) -> None:
    store_path = tmp_path / "lemmas.sqlite"
    run_fixture_pipeline(store_path=store_path, out_dir=tmp_path / "rime")
    store = LemmaStore(store_path)
    lemma = store.get("文件备份", "wen jian bei fen")
    assert lemma is not None
    store.close()
