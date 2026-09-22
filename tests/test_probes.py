from pathlib import Path

from umate_lexicon.eval.probes import evaluate_probes
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore


def test_probe_weight_and_gap(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    store.upsert(
        Lemma(
            surface="了",
            pinyin_plain="le",
            status="auto",
            flags=["tgh"],
            domain_freq={"essay": 100},
            sources=[SourceRef("chars", "standard-8105", "x")],
        )
    )
    store.upsert(
        Lemma(
            surface="了",
            pinyin_plain="liao",
            status="auto",
            flags=["tgh"],
            domain_freq={"essay": 10},
            sources=[SourceRef("chars", "standard-8105", "x")],
        )
    )
    probe = tmp_path / "probes.tsv"
    probe.write_text(
        "weight_gt\t了\tle\t了\tliao\nlayer\t了\tle\tchars\t\nnot_emitted\t了\tliao\t\t\n",
        encoding="utf-8",
    )
    failures = evaluate_probes(store, probe)
    assert [item.check for item in failures] == ["not_emitted"]
    store.close()
