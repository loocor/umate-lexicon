from pathlib import Path

from umate_lexicon.ingest.chars import ingest_chars
from umate_lexicon.ingest.wikinews import ingest_wikinews, segment_words
from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore


def test_segment_words_counts_han_bigrams_and_up() -> None:
    freq = segment_words("香港政府向每个电力账户发放电费补贴，参赛家庭平均减少用电量。")
    assert freq, "jieba must yield at least one word"
    assert freq.get("每个") == 1
    assert all(len(w) >= 2 for w in freq)
    assert all(not w.isascii() for w in freq)
    assert all("\u4e00" <= ch <= "\u9fff" for w in freq for ch in w)


def test_ingest_wikinews_adds_missing_words_only(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    ingest_chars(store, data_dir() / "fixtures" / "chars.tsv")
    fixture = data_dir() / "fixtures" / "wikinews-pages.tsv"
    added = ingest_wikinews(store, fixture, locator="wikinews-20261001-pages.tsv")
    assert added >= 1
    # a news-domain word missing from chars gets the wikinews source id
    found = [
        lemma
        for lemma in store.all_lemmas()
        if "wikinews" in lemma.sources[0].license
    ]
    assert found, "no lemma recorded under cc-by-4.0-wikinews"
    for lemma in found:
        assert lemma.sources[0].license == "cc-by-4.0-wikinews"
        assert lemma.domain_freq.get("wikinews", 0) >= 2
        assert lemma.surface not in (), lemma.surface
    before = {lemma.surface for lemma in store.all_lemmas()}
    again = ingest_wikinews(store, fixture)
    after = {lemma.surface for lemma in store.all_lemmas()}
    assert again == 0 and before == after, "re-ingest must be idempotent"
    store.close()


def test_ingest_wikinews_skips_low_freq_words(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    ingest_chars(store, data_dir() / "fixtures" / "chars.tsv")
    one_off = tmp_path / "one-off.tsv"
    # every char is covered by the chars fixture, but "我们" occurs once
    one_off.write_text(
        "测试标题\t我们在测试设备上完成文件备份。\n",
        encoding="utf-8",
    )
    assert ingest_wikinews(store, one_off) == 0
    store.close()
