from pathlib import Path

from umate_lexicon.enrich.polyphone import apply_polyphone_flags
from umate_lexicon.layers import assign_layer
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore


def test_cedict_polyphone_stays_auto(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    store.upsert(
        Lemma(
            surface="重庆",
            pinyin_plain="chong qing",
            status="auto",
            sources=[SourceRef("cedict", "cc-by-sa-cedict", "x")],
        )
    )
    apply_polyphone_flags(store, frozenset({"重"}))
    lemma = store.get("重庆", "chong qing")
    assert lemma is not None
    assert lemma.status == "auto"
    assert "polyphone" in lemma.flags
    store.close()


def test_low_freq_composed_polyphone_goes_to_review(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    store.upsert(
        Lemma(
            surface="重庆",
            pinyin_plain="zhong qing",
            status="auto",
            weight=10,
            domain_freq={"thuocl": 10},
            sources=[SourceRef("thuocl", "mit-thuocl", "x")],
        )
    )
    apply_polyphone_flags(store, frozenset({"重"}))
    lemma = store.get("重庆", "zhong qing")
    assert lemma is not None
    assert lemma.status == "review"
    store.close()


def test_high_freq_aspect_bigram_stays_auto_and_emits(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    store.upsert(
        Lemma(
            surface="拿着",
            pinyin_plain="na zhe",
            status="auto",
            weight=16449,
            domain_freq={"essay": 16449},
            sources=[SourceRef("essay", "lgpl-rime-essay", "essay.txt")],
        )
    )
    apply_polyphone_flags(store, frozenset({"着"}))
    lemma = store.get("拿着", "na zhe")
    assert lemma is not None
    assert lemma.status == "auto"
    assert "polyphone" in lemma.flags
    assert assign_layer(lemma) == "base"
    store.close()


def test_prior_review_high_freq_reopens_to_auto(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    store.upsert(
        Lemma(
            surface="带着",
            pinyin_plain="dai zhe",
            status="review",
            weight=29478,
            domain_freq={"essay": 29478},
            flags=["polyphone"],
            sources=[SourceRef("essay", "lgpl-rime-essay", "essay.txt")],
        )
    )
    apply_polyphone_flags(store, frozenset({"着"}))
    lemma = store.get("带着", "dai zhe")
    assert lemma is not None
    assert lemma.status == "auto"
    assert assign_layer(lemma) == "base"
    store.close()


def test_review_short_lemma_can_emit_via_freq_gate() -> None:
    lemma = Lemma(
        surface="看着",
        pinyin_plain="kan zhe",
        status="review",
        domain_freq={"essay": 32548},
        flags=["polyphone"],
        sources=[SourceRef("essay", "lgpl-rime-essay", "essay.txt")],
    )
    assert assign_layer(lemma) == "base"
