from umate_lexicon.enrich.category import classify
from umate_lexicon.layers import assign_layer
from umate_lexicon.lemma import Lemma


def test_bank_word_is_not_an_org() -> None:
    lemma = classify(Lemma(surface="银行", pinyin_plain="yin hang", status="gold"))
    assert lemma.entity_type != "org"
    assert "org" not in lemma.categories


def test_named_bank_is_org() -> None:
    lemma = classify(Lemma(surface="中国银行", pinyin_plain="zhong guo yin hang", status="auto"))
    assert lemma.entity_type == "org"


def test_gold_latin_brand_ships_in_default_sku() -> None:
    lemma = Lemma(surface="umate", pinyin_plain="umate", status="gold")
    assert assign_layer(lemma) == "brands"
