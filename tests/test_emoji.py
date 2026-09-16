from pathlib import Path

from umate_lexicon.emit.rime import emit_rime
from umate_lexicon.ingest.chars import ingest_chars
from umate_lexicon.ingest.emoji import ingest_emoji, parse_emoji_word_line
from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore


def test_parses_opencc_word_line() -> None:
    assert parse_emoji_word_line("哈哈\t哈哈 😂") == ("哈哈", ["😂"])
    assert parse_emoji_word_line("WIFI\tWIFI 🛜") == ("WIFI", ["🛜"])


def test_composable_triggers_become_emoji_lemmas(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    ingest_chars(store, data_dir() / "fixtures" / "chars.tsv")
    count = ingest_emoji(store, data_dir() / "fixtures" / "emoji_word.txt")
    assert count >= 1
    laugh = store.get("😂", "ha ha")
    assert laugh is not None
    assert laugh.entity_type == "emoji"
    assert store.get("🛜", "wifi") is None
    sidecar = (tmp_path / "emoji_word.txt").read_text(encoding="utf-8")
    assert "WIFI\tWIFI 🛜" in sidecar
    out = tmp_path / "rime"
    counts = emit_rime(store, out)
    assert counts.get("emoji", 0) >= 1
    schema = (out / "umate_hans.schema.yaml").read_text(encoding="utf-8")
    assert "umate_emoji" not in schema
    assert (out / "opencc" / "emoji_word.txt").exists()
    store.close()
