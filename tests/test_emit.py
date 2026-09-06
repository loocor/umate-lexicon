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
    store.close()
