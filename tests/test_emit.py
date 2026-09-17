from pathlib import Path

from umate_lexicon.emit.rime import emit_rime
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore


def test_emit_writes_packs(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    store.upsert(
        Lemma(
            surface="你",
            pinyin_plain="ni",
            weight=10,
            status="auto",
            sources=[SourceRef("chars", "standard-chars", "test")],
        )
    )
    store.upsert(
        Lemma(
            surface="你好",
            pinyin_plain="ni hao",
            weight=10,
            status="gold",
            sources=[SourceRef("gold", "umate-gold", "test")],
        )
    )
    out = tmp_path / "rime"
    counts = emit_rime(store, out)
    assert counts["chars"] == 1
    assert counts["base"] == 1
    schema = (out / "umate_hans.schema.yaml").read_text(encoding="utf-8")
    assert "translator/packs" in schema or "packs:" in schema
    assert "aosp_en" in schema
    assert "umate_en" not in schema
    store.close()


def test_wiki_only_titles_are_not_emitted(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    store.upsert(
        Lemma(
            surface="秦虹街道",
            pinyin_plain="qin hong jie dao",
            status="auto",
            sources=[SourceRef("wiki", "cc-by-sa-wikimedia", "test")],
        )
    )
    store.upsert(
        Lemma(
            surface="一线城市",
            pinyin_plain="yi xian cheng shi",
            status="auto",
            sources=[
                SourceRef("wiki", "cc-by-sa-wikimedia", "test"),
                SourceRef("tencent", "cc-by-3.0-tencent", "test"),
            ],
        )
    )
    out = tmp_path / "rime"
    counts = emit_rime(store, out)
    assert counts.get("bulk", 0) == 1
    body = (out / "umate_bulk.dict.yaml").read_text(encoding="utf-8")
    assert "一线城市" in body
    assert "秦虹街道" not in body
    store.close()
