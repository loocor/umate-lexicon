from pathlib import Path

from umate_lexicon.ingest.chars import ingest_chars
from umate_lexicon.ingest.compose import compose_pinyin
from umate_lexicon.ingest.essay import ingest_essay
from umate_lexicon.ingest.gold import ingest_gold
from umate_lexicon.ingest.luna import ingest_luna
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore


def test_compose_prefers_tgh_reading_for_polyphone_phrases(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    store.upsert(
        Lemma(
            surface="和",
            pinyin_plain="he",
            weight=1000,
            status="auto",
            flags=["tgh", "polyphone"],
            sources=[SourceRef("chars", "umate-chars", "test")],
        )
    )
    store.upsert(
        Lemma(
            surface="和",
            pinyin_plain="huo",
            weight=1000,
            status="auto",
            flags=["polyphone"],
            sources=[SourceRef("cedict", "cc-cedict", "test")],
        )
    )
    store.upsert(
        Lemma(
            surface="我",
            pinyin_plain="wo",
            weight=1000,
            status="auto",
            flags=["tgh"],
            sources=[SourceRef("chars", "umate-chars", "test")],
        )
    )
    assert compose_pinyin(store, "我和") == "wo he"
    store.close()


def test_essay_bakes_polyphone_skeleton_phrases(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    fixture = data_dir() / "fixtures"
    ingest_gold(store, data_dir() / "gold" / "readings.tsv")
    ingest_chars(store, fixture / "chars.tsv")
    ingest_luna(store, fixture / "luna.dict.yaml")
    essay = tmp_path / "essay.txt"
    essay.write_text("我和\t12742\n我的\t158176\n", encoding="utf-8")
    # Seed polyphone chars the way production does (multiple plains + tgh).
    store.upsert(
        Lemma(
            surface="和",
            pinyin_plain="he",
            weight=665031,
            status="auto",
            flags=["tgh", "polyphone"],
            domain_freq={"essay": 665031},
            sources=[SourceRef("chars", "umate-chars", "test")],
        )
    )
    store.upsert(
        Lemma(
            surface="和",
            pinyin_plain="huo",
            weight=665031,
            status="auto",
            flags=["polyphone"],
            domain_freq={"essay": 665031},
            sources=[SourceRef("cedict", "cc-cedict", "test")],
        )
    )
    store.upsert(
        Lemma(
            surface="的",
            pinyin_plain="de",
            weight=4822928,
            status="auto",
            flags=["tgh", "polyphone"],
            domain_freq={"essay": 4822928},
            sources=[SourceRef("chars", "umate-chars", "test")],
        )
    )
    store.upsert(
        Lemma(
            surface="的",
            pinyin_plain="di",
            weight=4822928,
            status="auto",
            flags=["polyphone"],
            domain_freq={"essay": 4822928},
            sources=[SourceRef("cedict", "cc-cedict", "test")],
        )
    )
    store.upsert(
        Lemma(
            surface="我",
            pinyin_plain="wo",
            weight=1191912,
            status="auto",
            flags=["tgh"],
            domain_freq={"essay": 1191912},
            sources=[SourceRef("chars", "umate-chars", "test")],
        )
    )
    count = ingest_essay(store, essay)
    assert count >= 2
    assert store.get("我和", "wo he") is not None
    assert store.get("我的", "wo de") is not None
    store.close()
