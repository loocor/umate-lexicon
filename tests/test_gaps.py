from pathlib import Path

from umate_lexicon.gaps import (
    char_floor,
    classify_ledger,
    classify_surface,
    load_gap_ledger,
    render_gaps,
)
from umate_lexicon.lemma import Lemma
from umate_lexicon.store import LemmaStore


def _store(tmp_path: Path) -> LemmaStore:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    with store.deferred_commit():
        store.upsert(
            Lemma(
                surface="出",
                pinyin_plain="chu",
                status="auto",
                domain_freq={"essay": 57216},
            )
        )
        store.upsert(
            Lemma(
                surface="门",
                pinyin_plain="men",
                status="auto",
                domain_freq={"essay": 15697},
            )
        )
    return store


def test_absent_surface_without_characters_is_missing(tmp_path: Path) -> None:
    store = _store(tmp_path)
    finding = classify_surface(store, "龘靐")
    assert finding.bucket == "missing"
    store.close()


def test_composable_absent_surface_is_segmentation(tmp_path: Path) -> None:
    store = _store(tmp_path)
    finding = classify_surface(store, "出门门")
    assert finding.bucket == "segmentation"
    assert finding.readings == ()
    store.close()


def test_filtered_when_no_layer_survives(tmp_path: Path) -> None:
    store = _store(tmp_path)
    # Short high-freq review lemmas may now emit; keep a long low-freq
    # polyphone review case as the still-filtered inventory bucket.
    store.upsert(
        Lemma(
            surface="中书省试案",
            pinyin_plain="zhong shu sheng shi an",
            status="review",
            flags=["polyphone"],
            domain_freq={"essay": 408},
        )
    )
    finding = classify_surface(store, "中书省试案")
    assert finding.bucket == "present-filtered"
    assert "status=review" in finding.detail
    assert "flags=polyphone" in finding.detail
    store.close()


def test_pack_only_surface_is_not_shipped(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert(
        Lemma(
            surface="昆明",
            pinyin_plain="kun ming",
            status="auto",
            entity_type="place",
            domain_freq={"essay": 900},
        )
    )
    finding = classify_surface(store, "昆明")
    assert finding.bucket == "present-not-shipped"
    assert "places" in finding.detail
    store.close()


def test_phrase_below_character_floor_is_ranked_low(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert(
        Lemma(surface="出门", pinyin_plain="chu men", status="auto", domain_freq={"essay": 12251})
    )
    assert char_floor(store, "出门", "chu men") == 15697
    finding = classify_surface(store, "出门")
    assert finding.bucket == "present-ranked-low"
    assert "below character floor 15697" in finding.detail
    store.close()


def test_phrase_above_character_floor_is_shipped(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert(
        Lemma(surface="出门", pinyin_plain="chu men", status="auto", domain_freq={"essay": 99999})
    )
    finding = classify_surface(store, "出门")
    assert finding.bucket == "present-shipped"
    assert finding.layers == ("base",)
    store.close()


def test_char_floor_is_unknown_when_syllables_do_not_line_up(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert char_floor(store, "出门", "chu") is None
    store.close()


def test_ledger_skips_header_and_comments(tmp_path: Path) -> None:
    ledger = tmp_path / "daily-gaps.tsv"
    ledger.write_text(
        "surface\torigin\treported\tnote\n"
        "# a comment\n"
        "\n"
        "连着\tuser\t2026-09-17\tcannot type it\n",
        encoding="utf-8",
    )
    rows = load_gap_ledger(ledger)
    assert [row.surface for row in rows] == ["连着"]
    assert rows[0].origin == "user"
    assert rows[0].note == "cannot type it"


def test_report_renders_bucket_counts(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert(
        Lemma(surface="出门", pinyin_plain="chu men", status="auto", domain_freq={"essay": 12251})
    )
    ledger = tmp_path / "daily-gaps.tsv"
    ledger.write_text("surface\torigin\treported\tnote\n出门\tuser\t2026-09-17\t\n", encoding="utf-8")
    text = render_gaps(classify_ledger(store, ledger))
    assert "present-ranked-low" in text
    assert "present-ranked-low\t1" in text
    store.close()
