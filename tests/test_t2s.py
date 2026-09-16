from pathlib import Path

from umate_lexicon.ingest.chars import ingest_chars
from umate_lexicon.ingest.essay import ingest_essay
from umate_lexicon.ingest.gold import ingest_gold
from umate_lexicon.ingest.luna import ingest_luna
from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore
from umate_lexicon.t2s import load_unihan_simplified, make_simplifier


def test_unihan_map_folds_yin_hang() -> None:
    table = load_unihan_simplified(data_dir() / "fixtures" / "unihan-variants.txt")
    simplify = make_simplifier(table)
    assert simplify("銀行") == "银行"
    assert simplify("微信") == "微信"


def test_essay_overlays_simplified_bank(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    simplify = make_simplifier(load_unihan_simplified(data_dir() / "fixtures" / "unihan-variants.txt"))
    ingest_gold(store, data_dir() / "gold" / "readings.tsv")
    ingest_chars(store, data_dir() / "fixtures" / "chars.tsv")
    ingest_luna(store, data_dir() / "fixtures" / "luna.dict.yaml", simplify=simplify)
    ingest_essay(store, data_dir() / "fixtures" / "essay.txt", simplify=simplify)
    bank = store.get("银行", "yin hang")
    assert bank is not None
    assert bank.status == "gold"
    assert bank.domain_freq["essay"] == 36856
    assert store.get("銀行", "yin hang") is None
    store.close()
