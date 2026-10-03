from pathlib import Path

from umate_lexicon.emit.rime import apply_ranking_overrides, emit_rime, load_ranking_overrides
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore


def _core(store: LemmaStore, surface: str, pinyin: str, freq: int) -> None:
    store.upsert(
        Lemma(
            surface=surface,
            pinyin_plain=pinyin,
            status="auto",
            domain_freq={"core": freq},
            sources=[SourceRef("umate-core", "lgpl-rime-essay", "test")],
        )
    )


def _cedict(store: LemmaStore, surface: str, pinyin: str) -> None:
    store.upsert(
        Lemma(
            surface=surface,
            pinyin_plain=pinyin,
            status="auto",
            domain_freq={"cedict": 1},
            sources=[SourceRef("cedict", "cc-by-sa-cedict", "test")],
        )
    )


def test_load_skips_comments(tmp_path: Path) -> None:
    path = tmp_path / "overrides.tsv"
    path.write_text("# surface\tpinyin\n覆盖\tfu gai\tnote\n", encoding="utf-8")
    rows = load_ranking_overrides(path)
    assert rows == {("覆盖", "fu gai"): "note"}


def test_apply_raises_just_above_peak() -> None:
    weights = {("复盖", "fu gai"): 14118, ("覆盖", "fu gai"): 1, ("其他", "qi ta"): 9}
    n = apply_ranking_overrides(weights, {("覆盖", "fu gai"): "variant"})
    assert n == 1
    assert weights[("覆盖", "fu gai")] == 14119
    assert weights[("复盖", "fu gai")] == 14118


def test_apply_breaks_tie() -> None:
    weights = {("计划", "ji hua"): 45520, ("计画", "ji hua"): 45520}
    n = apply_ranking_overrides(weights, {("计划", "ji hua"): "tie"})
    assert n == 1
    assert weights[("计划", "ji hua")] == 45521
    assert weights[("计画", "ji hua")] == 45520


def test_emit_override_beats_variant(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    _core(store, "复盖", "fu gai", 14118)
    _cedict(store, "覆盖", "fu gai")
    overrides = tmp_path / "overrides.tsv"
    overrides.write_text("覆盖\tfu gai\n", encoding="utf-8")
    out = tmp_path / "rime"
    counts = emit_rime(store, out, ranking_overrides=overrides)
    assert counts["ranking_overrides"] == 1
    rows: dict[str, tuple[str, int]] = {}
    for path in out.glob("umate_*.dict.yaml"):
        in_data = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() == "...":
                in_data = True
                continue
            if not in_data or not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                rows[parts[0]] = (parts[1], int(parts[2]))
    assert rows["覆盖"][1] == 14119
    assert rows["复盖"][1] == 14118
    store.close()


def test_emit_without_override_keeps_core(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    _core(store, "粉色", "fen se", 1584)
    empty = tmp_path / "empty.tsv"
    empty.write_text("# none\n", encoding="utf-8")
    out = tmp_path / "rime"
    emit_rime(store, out, ranking_overrides=empty)
    body = (out / "umate_base.dict.yaml").read_text(encoding="utf-8")
    assert "粉色\tfen se\t1584" in body
    store.close()
