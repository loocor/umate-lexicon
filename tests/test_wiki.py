from pathlib import Path

from umate_lexicon.ingest.chars import ingest_chars
from umate_lexicon.ingest.wiki import ingest_wiki, normalize_wiki_title
from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore


def test_normalize_skips_lists_and_keeps_han() -> None:
    assert normalize_wiki_title("开心") == "开心"
    assert normalize_wiki_title("List_of_planets") is None
    assert normalize_wiki_title("北京_(消歧义)") is None


def test_wiki_adds_composable_missing_title(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    ingest_chars(store, data_dir() / "fixtures" / "chars.tsv")
    count = ingest_wiki(store, data_dir() / "fixtures" / "wiki-titles.txt")
    assert count >= 1
    happy = store.get("开心", "kai xin")
    assert happy is not None
    store.close()
