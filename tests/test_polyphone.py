from pathlib import Path

from umate_lexicon.enrich.polyphone import apply_polyphone_flags
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


def test_composed_polyphone_goes_to_review(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    store.upsert(
        Lemma(
            surface="重庆",
            pinyin_plain="zhong qing",
            status="auto",
            sources=[SourceRef("thuocl", "mit-thuocl", "x")],
        )
    )
    apply_polyphone_flags(store, frozenset({"重"}))
    lemma = store.get("重庆", "zhong qing")
    assert lemma is not None
    assert lemma.status == "review"
    store.close()
