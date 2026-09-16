from pathlib import Path

from umate_lexicon.ingest.chars import ingest_chars
from umate_lexicon.ingest.tgh import ingest_tgh
from umate_lexicon.layers import assign_layer
from umate_lexicon.lemma import Lemma
from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore


def test_tgh_marks_standard_chars(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    ingest_chars(store, data_dir() / "fixtures" / "chars.tsv")
    count = ingest_tgh(store, data_dir() / "fixtures" / "unihan-tgh.txt")
    assert count >= 1
    ni = store.get("你", "ni")
    assert ni is not None
    assert "tgh" in ni.flags
    store.close()


def test_unihan_only_char_is_not_core() -> None:
    lemma = Lemma(
        surface="㐀",
        pinyin_plain="qiu",
        status="auto",
        sources=[],
    )
    assert assign_layer(lemma) is None
