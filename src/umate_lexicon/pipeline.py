from __future__ import annotations

from pathlib import Path

from umate_lexicon.emit.rime import emit_rime
from umate_lexicon.enrich.category import classify
from umate_lexicon.enrich.polyphone import apply_polyphone_flags
from umate_lexicon.eval.gold import evaluate_store
from umate_lexicon.ingest.cedict import ingest_cedict
from umate_lexicon.ingest.chars import ingest_chars
from umate_lexicon.ingest.gold import ingest_gold
from umate_lexicon.ingest.thuocl import ingest_thuocl
from umate_lexicon.ingest.unihan import ingest_unihan
from umate_lexicon.paths import data_dir, default_store_path
from umate_lexicon.store import LemmaStore
from umate_lexicon.verify.rules import apply_rules


def run_fixture_pipeline(
    store_path: Path | None = None,
    out_dir: Path | None = None,
) -> dict[str, int]:
    root = data_dir()
    store = LemmaStore(store_path or default_store_path())
    stats = {
        "gold": ingest_gold(store, root / "gold" / "readings.tsv"),
        "chars": ingest_chars(store, root / "fixtures" / "chars.tsv"),
        "unihan": ingest_unihan(store, root / "fixtures" / "unihan.txt"),
        "cedict": ingest_cedict(store, root / "fixtures" / "cedict.txt"),
        "thuocl": ingest_thuocl(store, root / "fixtures" / "thuocl.txt"),
    }
    for lemma in store.all_lemmas():
        store.save(classify(lemma))
    stats["polyphone"] = apply_polyphone_flags(store)
    stats["rejected"] = apply_rules(store)
    emit_dir = out_dir or (Path(__file__).resolve().parents[2] / "dist" / "rime")
    stats.update({f"emit_{k}": v for k, v in emit_rime(store, emit_dir).items()})
    stats["lemmas"] = store.count()
    failures = evaluate_store(store)
    stats["eval_failures"] = len(failures)
    store.close()
    if failures:
        details = "; ".join(
            f"{item.surface} expected {item.expected_pinyin} got {item.actual}" for item in failures
        )
        raise SystemExit(f"eval failed: {details}")
    return stats
