from umate_lexicon.enrich.category import classify
from umate_lexicon.layers import assign_layer
from umate_lexicon.lemma import Lemma, SourceRef


def test_two_char_diming_without_suffix_is_not_place() -> None:
    lemma = classify(
        Lemma(surface="开源", pinyin_plain="kai yuan", status="auto", entity_type="place", categories=["place"])
    )
    assert lemma.entity_type != "place"
    assert assign_layer(lemma) == "base"


def test_gold_city_keeps_place() -> None:
    lemma = classify(
        Lemma(
            surface="上海",
            pinyin_plain="shang hai",
            status="gold",
            flags=["gold"],
            entity_type="place",
            categories=["place"],
        )
    )
    assert lemma.entity_type == "place"
    assert assign_layer(lemma) == "places"


def test_latin_brand_still_default_sku() -> None:
    lemma = Lemma(surface="iPhone", pinyin_plain="iphone", status="gold", entity_type="brand", flags=["gold"])
    assert assign_layer(lemma) == "brands"


def test_cross_strait_alias_goes_to_corrections() -> None:
    lemma = Lemma(
        surface="出租车",
        pinyin_plain="ji cheng che",
        status="gold",
        flags=["gold", "correction"],
        entity_type="correction",
        sources=[SourceRef("gold", "umate-gold", "corrections.tsv")],
    )
    assert assign_layer(lemma) == "corrections"


def test_wiki_only_bigrams_go_to_bulk() -> None:
    lemma = Lemma(
        surface="开心",
        pinyin_plain="kai xin",
        status="auto",
        sources=[SourceRef("wiki", "cc-by-sa-wikimedia", "wiki")],
    )
    assert assign_layer(lemma) == "bulk"


def test_gold_five_char_term_stays_in_ext() -> None:
    lemma = Lemma(
        surface="大语言模型",
        pinyin_plain="da yu yan mo xing",
        status="gold",
        flags=["gold"],
    )
    assert assign_layer(lemma) == "ext"


def test_wiki_only_false_place_stays_bulk() -> None:
    lemma = Lemma(
        surface="一剑镇神州",
        pinyin_plain="yi jian zhen shen zhou",
        status="auto",
        entity_type="place",
        categories=["place"],
        sources=[SourceRef("wiki", "cc-by-sa-wikimedia", "wiki")],
    )
    assert assign_layer(lemma) == "bulk"


def test_wiki_only_town_stays_bulk() -> None:
    lemma = Lemma(
        surface="一亩泉镇",
        pinyin_plain="yi mu quan zhen",
        status="auto",
        entity_type="place",
        categories=["place"],
        sources=[SourceRef("wiki", "cc-by-sa-wikimedia", "wiki")],
    )
    assert assign_layer(lemma) == "bulk"
