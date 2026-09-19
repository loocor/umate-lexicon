from pathlib import Path

from umate_lexicon.emit.rime import emit_rime
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore


def test_emit_writes_packs(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    store.upsert(
        Lemma(
            surface="你",
            pinyin_plain="ni",
            weight=10,
            status="auto",
            sources=[SourceRef("chars", "standard-chars", "test")],
        )
    )
    store.upsert(
        Lemma(
            surface="你好",
            pinyin_plain="ni hao",
            weight=10,
            status="gold",
            sources=[SourceRef("gold", "umate-gold", "test")],
        )
    )
    store.upsert(
        Lemma(
            surface="一会儿",
            pinyin_plain="yi hui r",
            weight=5000,
            status="auto",
            domain_freq={"essay": 5000},
            sources=[SourceRef("essay", "lgpl-rime-essay", "test")],
        )
    )
    out = tmp_path / "rime"
    counts = emit_rime(store, out)
    assert counts["chars"] == 1
    assert counts["base"] == 2
    assert counts["codes_sanitized"] >= 1
    body = (out / "umate_base.dict.yaml").read_text(encoding="utf-8")
    assert "一会儿\tyi huir\t" in body
    schema = (out / "umate_hans.schema.yaml").read_text(encoding="utf-8")
    assert "translator/packs" in schema or "packs:" in schema
    assert "aosp_en" in schema
    assert "umate_en" not in schema
    assert (out / "aosp_en.dict.yaml").is_file()
    assert (out / "en_us_unigrams.tsv").is_file()
    store.close()


def test_wiki_only_titles_go_to_cold_tail(tmp_path: Path, monkeypatch) -> None:
    from umate_lexicon import layers

    monkeypatch.setattr(layers, "WIKI_TAIL_ENABLED", True)
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    store.upsert(
        Lemma(
            surface="秦虹街道",
            pinyin_plain="qin hong jie dao",
            status="auto",
            sources=[SourceRef("wiki", "cc-by-sa-wikimedia", "test")],
        )
    )
    store.upsert(
        Lemma(
            surface="一线城市",
            pinyin_plain="yi xian cheng shi",
            status="auto",
            sources=[
                SourceRef("wiki", "cc-by-sa-wikimedia", "test"),
                SourceRef("tencent", "cc-by-3.0-tencent", "test"),
            ],
        )
    )
    out = tmp_path / "rime"
    counts = emit_rime(store, out)
    assert counts.get("bulk", 0) == 1
    assert counts.get("wiki_tail", 0) == 1
    body = (out / "umate_bulk.dict.yaml").read_text(encoding="utf-8")
    assert "一线城市" in body
    assert "秦虹街道" not in body
    tail = (out / "umate_wiki_tail.dict.yaml").read_text(encoding="utf-8")
    assert "秦虹街道\tqin hong jie dao\t1" in tail
    hot = (out / "umate_hans.dict.yaml").read_text(encoding="utf-8")
    assert "- umate_hot_tail" in hot
    assert "umate_wiki_tail" not in hot
    cold = (out / "umate_hans_cold.dict.yaml").read_text(encoding="utf-8")
    assert "- umate_wiki_tail" in cold
    assert "- umate_hot_tail" not in cold
    store.close()


def test_hot_tail_is_a_weight_projection(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    store.upsert(
        Lemma(
            surface="人工智能大会",
            pinyin_plain="ren gong zhi neng da hui",
            status="auto",
            domain_freq={"essay": 2000},
            sources=[SourceRef("essay", "lgpl-rime-essay", "test")],
        )
    )
    store.upsert(
        Lemma(
            surface="大会论文",
            pinyin_plain="da hui lun wen",
            status="auto",
            domain_freq={"essay": 100},
            sources=[SourceRef("essay", "lgpl-rime-essay", "test")],
        )
    )
    out = tmp_path / "rime"
    emit_rime(store, out)
    hot_tail = (out / "umate_hot_tail.dict.yaml").read_text(encoding="utf-8")
    assert "人工智能大会\t" in hot_tail
    assert "大会论文" not in hot_tail
    ext = (out / "umate_ext.dict.yaml").read_text(encoding="utf-8")
    assert "大会论文\t" in ext
    cold = (out / "umate_hans_cold.dict.yaml").read_text(encoding="utf-8")
    assert "- umate_ext" in cold
    store.close()


def test_emitted_weight_is_the_raw_ranking_frequency(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    store.upsert(
        Lemma(
            surface="粉色",
            pinyin_plain="fen se",
            status="auto",
            domain_freq={"essay": 1584, "cedict": 1},
            sources=[SourceRef("essay", "lgpl-rime-essay", "essay.txt")],
        )
    )
    out = tmp_path / "rime"
    emit_rime(store, out)
    body = (out / "umate_base.dict.yaml").read_text(encoding="utf-8")
    assert "粉色\tfen se\t1585" in body
    store.close()


def test_wiki_tail_paused_by_default(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    store.upsert(
        Lemma(
            surface="秦虹街道",
            pinyin_plain="qin hong jie dao",
            status="auto",
            sources=[SourceRef("wiki", "cc-by-sa-wikimedia", "test")],
        )
    )
    out = tmp_path / "rime"
    counts = emit_rime(store, out)
    assert "wiki_tail" not in counts
    assert not (out / "umate_wiki_tail.dict.yaml").exists()
    cold = (out / "umate_hans_cold.dict.yaml").read_text(encoding="utf-8")
    assert "umate_wiki_tail" not in cold
    assert (out / "umate_hot_tail.dict.yaml").exists()
    store.close()
