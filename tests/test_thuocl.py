from pathlib import Path

from umate_lexicon.ingest.chars import ingest_chars
from umate_lexicon.ingest.thuocl import ingest_thuocl
from umate_lexicon.store import LemmaStore


def test_parses_tab_frequency_with_spaces(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    chars = tmp_path / "chars.tsv"
    chars.write_text("你\tni\t1\n好\thao\t1\n", encoding="utf-8")
    ingest_chars(store, chars)
    thuocl = tmp_path / "THUOCL_IT.txt"
    thuocl.write_text("你好 \t 128\n", encoding="utf-8")
    count = ingest_thuocl(store, thuocl)
    assert count == 1
    lemma = store.get("你好", "ni hao")
    assert lemma is not None
    assert lemma.domain_freq["thuocl"] == 128
    store.close()
