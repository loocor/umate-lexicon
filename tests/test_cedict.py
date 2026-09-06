from pathlib import Path

from umate_lexicon.ingest.cedict import ingest_cedict
from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore


def test_ingests_simplified_with_plain_pinyin(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    count = ingest_cedict(store, data_dir() / "fixtures" / "cedict.txt")
    assert count >= 4
    lemma = store.get("重庆", "chong qing")
    assert lemma is not None
    assert lemma.status == "auto"
    store.close()
