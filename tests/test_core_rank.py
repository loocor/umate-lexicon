from pathlib import Path

from umate_lexicon.emit.rime import emit_rime
from umate_lexicon.ingest.core import ingest_core
from umate_lexicon.layers import emit_weight
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore


def _char(surface: str, plain: str, *, tgh: bool, pinlu: int = 0, core: int = 1000) -> Lemma:
    flags = ["polyphone"]
    sources = [SourceRef("cedict", "cc-by-sa-cedict", "test")]
    domain: dict[str, int] = {"cedict": 1}
    if core:
        domain["core"] = core
    if tgh:
        flags.append("tgh")
        sources.append(SourceRef("chars", "standard-8105", "test"))
    if pinlu:
        flags.append("hanyu_pinlu")
        domain["hanyu_pinlu"] = pinlu
        sources.append(SourceRef("unihan", "unicode", "test"))
    return Lemma(
        surface=surface,
        pinyin_plain=plain,
        weight=1000,
        status="auto",
        flags=flags,
        domain_freq=domain,
        sources=sources,
    )


def test_shared_core_ranks_only_the_preferred_reading() -> None:
    primary = _char("和", "he", tgh=True, pinlu=9546)
    secondary = _char("和", "hu", tgh=False)
    siblings = [primary, secondary]
    # One column: the preferred reading keeps the shared core count; the
    # weaker reading drops it and falls back to its own cedict marker.
    assert emit_weight(primary, siblings) == 1000
    assert emit_weight(secondary, siblings) == 1
    assert emit_weight(secondary) == 1000

def test_demoted_reading_without_own_mass_falls_to_one() -> None:
    primary = _char("数", "shu", tgh=True)
    # A secondary whose only mass column is the shared core count.
    secondary = Lemma(
        surface="数",
        pinyin_plain="shuo",
        weight=5000,
        status="auto",
        flags=["polyphone"],
        domain_freq={"core": 1000},
        sources=[SourceRef("cedict", "cc-by-sa-cedict", "test")],
    )
    siblings = [primary, secondary]
    assert emit_weight(primary, siblings) == 1000
    # No stale weight fallback: the demoted reading must not keep 5000.
    assert emit_weight(secondary, siblings) == 1


def test_tied_readings_keep_the_surface_count() -> None:
    left = _char("行", "xing", tgh=False, pinlu=10)
    right = _char("行", "heng", tgh=False, pinlu=3)
    siblings = [left, right]
    # Equal reading evidence: the tie keeps the count on both sides.
    assert emit_weight(left, siblings) == 1000
    assert emit_weight(right, siblings) == 1000

def test_strictly_weaker_reading_falls_to_its_own_column() -> None:
    left = _char("行", "xing", tgh=True, pinlu=10)
    right = _char("行", "heng", tgh=False, pinlu=3)
    siblings = [left, right]
    assert emit_weight(left, siblings) == 1000
    assert emit_weight(right, siblings) == 3


def test_overlay_stamps_core_on_preferred_reading_only(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    store.upsert(_char("和", "he", tgh=True, pinlu=20, core=0))
    store.upsert(_char("和", "hu", tgh=False, core=0))
    core = tmp_path / "absorbed-core.tsv"
    core.write_text("和\t50\n", encoding="utf-8")
    ingest_core(store, core)
    preferred = store.get("和", "he")
    other = store.get("和", "hu")
    assert preferred is not None and preferred.domain_freq.get("core") == 50
    assert other is not None and "core" not in other.domain_freq
    store.close()


def test_gold_correction_does_not_steal_phrase_core() -> None:
    common = Lemma(
        surface="信息",
        pinyin_plain="xin xi",
        weight=89682,
        status="auto",
        domain_freq={"cedict": 1, "core": 269046},
        sources=[SourceRef("cedict", "cc-by-sa-cedict", "test"), SourceRef("umate-core", "lgpl-rime-essay", "test")],
    )
    correction = Lemma(
        surface="信息",
        pinyin_plain="zi xun",
        weight=89682,
        status="gold",
        flags=["gold", "correction"],
        domain_freq={"gold": 3000, "core": 269046},
        sources=[SourceRef("gold", "umate-gold", "test"), SourceRef("umate-core", "lgpl-rime-essay", "test")],
    )
    siblings = [common, correction]
    # Multi-character rows keep one column: core wins over gold for both,
    # so the correction never outranks the common reading via summing.
    assert emit_weight(common, siblings) == 269046
    assert emit_weight(correction, siblings) == 269046


def test_emit_writes_secondary_reading_below_primary(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    store.upsert(_char("说", "shuo", tgh=True, pinlu=80))
    store.upsert(_char("说", "shui", tgh=False, pinlu=2))
    out = tmp_path / "rime"
    emit_rime(store, out)
    text = (out / "umate_chars.dict.yaml").read_text(encoding="utf-8")
    weights = {}
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[0] == "说":
            weights[parts[1]] = int(parts[2])
    assert weights["shuo"] == 1000
    assert weights["shui"] == 2
    store.close()
