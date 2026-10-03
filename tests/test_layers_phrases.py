from umate_lexicon.layers import assign_layer
from umate_lexicon.lemma import Lemma, SourceRef


def test_high_freq_four_char_core_goes_to_phrases() -> None:
    coldish = Lemma(
        surface="四面楚歌",
        pinyin_plain="si mian chu ge",
        status="auto",
        domain_freq={"core": 800},
        weight=800,
        sources=[SourceRef("umate-core", "lgpl-rime-essay", "essay")],
    )
    # Below hot phrase threshold → cold ext for 4-char.
    assert assign_layer(coldish) == "ext"

    hot = Lemma(
        surface="以下几个方面",
        pinyin_plain="yi xia ji ge fang mian",
        status="auto",
        domain_freq={"core": 1527},
        weight=1527,
        sources=[SourceRef("umate-core", "lgpl-rime-essay", "essay")],
    )
    assert assign_layer(hot) == "phrases"


def test_gold_long_term_goes_to_phrases() -> None:
    lemma = Lemma(
        surface="大语言模型",
        pinyin_plain="da yu yan mo xing",
        status="gold",
        flags=["gold"],
    )
    assert assign_layer(lemma) == "phrases"


def test_weak_auto_bigram_demotes_to_bulk() -> None:
    lemma = Lemma(
        surface="涡核",
        pinyin_plain="wo he",
        status="auto",
        domain_freq={"core": 243, "cedict": 1},
        weight=243,
        sources=[
            SourceRef("cedict", "cc-cedict", "test"),
            SourceRef("umate-core", "lgpl-rime-essay", "essay"),
        ],
    )
    assert assign_layer(lemma) == "bulk"


def test_strong_core_bigram_stays_base() -> None:
    lemma = Lemma(
        surface="马上",
        pinyin_plain="ma shang",
        status="auto",
        domain_freq={"core": 18883, "cedict": 1},
        weight=18883,
        sources=[
            SourceRef("cedict", "cc-cedict", "test"),
            SourceRef("umate-core", "lgpl-rime-essay", "essay"),
        ],
    )
    assert assign_layer(lemma) == "base"


def test_wikinews_only_short_lemma_is_bulk() -> None:
    from umate_lexicon.layers import is_coverage_only

    lemma = Lemma(
        surface="震央",
        pinyin_plain="zhen yang",
        status="auto",
        domain_freq={"wikinews": 12},
        weight=12,
        sources=[SourceRef("wikinews", "cc-by-4.0-wikinews", "wikinews-pages")],
    )
    assert is_coverage_only(lemma)
    assert assign_layer(lemma) == "bulk"
