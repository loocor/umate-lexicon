from pathlib import Path

from umate_lexicon.emit.rime import emit_rime
from umate_lexicon.ingest.curation import (
    curated_weight,
    ingest_english_emoji_curation,
    ingest_pinyin_emoji_curation,
)
from umate_lexicon.layers import EMOJI_TAIL_WEIGHT, emit_weight
from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore


def test_curated_pinyin_rows_carry_tier_a_weights(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    count = ingest_pinyin_emoji_curation(store, data_dir() / "voimate" / "pinyin-emoji-curation.tsv")
    assert count >= 1
    first = store.get("👌", "hao")
    assert first is not None
    assert "curated" in first.flags
    assert emit_weight(first) == 6000
    second = store.get("👍", "hao")
    assert second is not None
    assert emit_weight(second) == 3600
    assert curated_weight(4) == 1296


def test_curated_english_word_and_emoji_rows_use_letter_codes(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    count = ingest_english_emoji_curation(store, data_dir() / "voimate" / "english-emoji-curation.tsv")
    assert count >= 1
    word = store.get("ok", "o k")
    assert word is not None
    assert emit_weight(word) == 6000
    emoji = store.get("👌", "o k")
    assert emoji is not None
    assert emit_weight(emoji) == curated_weight(3)
    spelled = store.get("Okay", "o k a y")
    assert spelled is not None
    # Single-letter codes never carry curated rows.
    assert store.get("❤️", "a") is None


def test_official_emoji_rides_the_tail_floor(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    count = ingest_pinyin_emoji_curation(store, data_dir() / "voimate" / "pinyin-emoji-curation.tsv")
    assert count >= 1
    out = tmp_path / "rime"
    counts = emit_rime(store, out)
    assert counts.get("emoji", 0) >= 1
    rows = {
        (parts[0], parts[1]): int(parts[2])
        for parts in (
            line.split("\t")
            for line in (out / "umate_emoji.dict.yaml").read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#") and line != "..." and "\t" in line
        )
        if len(parts) == 3
    }
    assert rows[("👌", "hao")] == 6000
    assert all(weight >= EMOJI_TAIL_WEIGHT for weight in rows.values())
