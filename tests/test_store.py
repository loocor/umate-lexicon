from pathlib import Path

from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore


def test_merge_keeps_gold_and_sources(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    store.upsert(
        Lemma(
            surface="重庆",
            pinyin_plain="chong qing",
            status="gold",
            sources=[SourceRef("gold", "umate-gold", "a")],
        )
    )
    store.upsert(
        Lemma(
            surface="重庆",
            pinyin_plain="chong qing",
            status="auto",
            sources=[SourceRef("cedict", "cc-by-sa-cedict", "b")],
        )
    )
    lemma = store.get("重庆", "chong qing")
    assert lemma is not None
    assert lemma.status == "gold"
    assert {ref.source_id for ref in lemma.sources} == {"gold", "cedict"}
    store.close()
