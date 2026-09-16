from pathlib import Path

from umate_lexicon.enrich.category import classify
from umate_lexicon.eval.tencent_absorb import measure_tencent_absorb
from umate_lexicon.ingest.chars import ingest_chars
from umate_lexicon.ingest.essay import ingest_essay
from umate_lexicon.ingest.gold import ingest_gold
from umate_lexicon.ingest.tencent import ingest_tencent
from umate_lexicon.layers import assign_layer, emit_weight
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore
from umate_lexicon.t2s import load_unihan_simplified, make_simplifier


def test_tencent_only_bigram_stays_out_of_default_sku() -> None:
    lemma = Lemma(
        surface="词向量",
        pinyin_plain="ci xiang liang",
        status="auto",
        domain_freq={"tencent": 1},
        sources=[SourceRef("tencent", "cc-by-3.0-tencent", "tencent-light")],
    )
    assert assign_layer(lemma) == "bulk"


def test_tencent_only_four_char_stays_out_of_ext() -> None:
    lemma = Lemma(
        surface="词向量库",
        pinyin_plain="ci xiang liang ku",
        status="auto",
        domain_freq={"tencent": 1},
        sources=[SourceRef("tencent", "cc-by-3.0-tencent", "tencent-light")],
    )
    assert assign_layer(lemma) == "bulk"


def test_wiki_plus_tencent_coverage_stays_bulk() -> None:
    lemma = Lemma(
        surface="开心",
        pinyin_plain="kai xin",
        status="auto",
        domain_freq={"wiki": 1, "tencent": 1},
        sources=[
            SourceRef("wiki", "cc-by-sa-wikimedia", "wiki"),
            SourceRef("tencent", "cc-by-3.0-tencent", "tencent-light"),
        ],
    )
    assert assign_layer(lemma) == "bulk"


def test_tencent_overlay_keeps_base_and_essay_rank() -> None:
    essay_only = Lemma(
        surface="微信",
        pinyin_plain="wei xin",
        status="gold",
        domain_freq={"essay": 10},
        sources=[
            SourceRef("gold", "umate-gold", "product-terms.tsv"),
            SourceRef("essay", "lgpl-rime-essay", "essay.txt"),
        ],
    )
    overlaid = Lemma(
        surface="微信",
        pinyin_plain="wei xin",
        status="gold",
        domain_freq={"essay": 10, "tencent": 1},
        sources=essay_only.sources
        + [SourceRef("tencent", "cc-by-3.0-tencent", "tencent-light")],
    )
    assert assign_layer(overlaid) == "base"
    assert emit_weight(overlaid) == emit_weight(essay_only)


def test_tencent_placeholder_does_not_invent_rank() -> None:
    lemma = Lemma(
        surface="微信",
        pinyin_plain="wei xin",
        status="gold",
        weight=10,
        domain_freq={"essay": 10, "tencent": 1},
    )
    assert lemma.domain_freq["tencent"] == 1
    assert emit_weight(lemma) == emit_weight(
        Lemma(surface="微信", pinyin_plain="wei xin", status="gold", domain_freq={"essay": 10})
    )


def test_tencent_only_bank_suffix_is_not_promoted_to_orgs() -> None:
    lemma = classify(
        Lemma(
            surface="建设银行",
            pinyin_plain="jian she yin hang",
            status="auto",
            sources=[SourceRef("tencent", "cc-by-3.0-tencent", "tencent-light")],
        )
    )
    assert lemma.entity_type != "org"
    assert assign_layer(lemma) == "bulk"


def test_tencent_t2s_overlays_simplified_surface(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    simplify = make_simplifier(load_unihan_simplified(data_dir() / "fixtures" / "unihan-variants.txt"))
    ingest_gold(store, data_dir() / "gold" / "readings.tsv")
    ingest_chars(store, data_dir() / "fixtures" / "chars.tsv")
    ingest_essay(store, data_dir() / "fixtures" / "essay.txt", simplify=simplify)
    vocab = tmp_path / "tencent-light-vocab.txt"
    vocab.write_text("微信\n銀行\n", encoding="utf-8")
    count = ingest_tencent(store, vocab, simplify=simplify)
    assert count >= 2
    bank = store.get("银行", "yin hang")
    assert bank is not None
    assert bank.domain_freq["tencent"] == 1
    assert bank.domain_freq["essay"] == 36856
    assert store.get("銀行", "yin hang") is None
    store.close()


def test_measure_tencent_absorb_counts_gates(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    ingest_gold(store, data_dir() / "gold" / "product-terms.tsv")
    ingest_chars(store, data_dir() / "fixtures" / "chars.tsv")
    ingest_gold(store, data_dir() / "gold" / "readings.tsv")
    vocab = tmp_path / "tencent-light-vocab.txt"
    vocab.write_text(
        "\n".join(
            [
                "微信",
                "人工智能",
                "的",
                "xyz",
                "向量数据库",
                "超长覆盖词不该入库",
                "无读音词",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    ingest_tencent(store, vocab)
    stats = measure_tencent_absorb(store, vocab)
    assert stats.surfaces == 7
    assert stats.overlaid_surfaces >= 2
    assert "微信" in stats.overlaid_surface_set
    assert stats.skipped_non_han_without_gold >= 1
    assert stats.skipped_length_1 >= 1
    assert stats.skipped_length_gt4 >= 1
    weixin = store.get("微信", "wei xin")
    assert weixin is not None
    assert weixin.domain_freq["tencent"] == 1
    assert assign_layer(weixin) == "base"
    store.close()
