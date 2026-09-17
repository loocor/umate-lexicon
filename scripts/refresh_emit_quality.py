#!/usr/bin/env python3
"""Refresh store lemmas that quality fixes need, then re-emit Rime packs.

Does not re-ingest wiki/tencent (hours). Re-applies authored gold, essay
compose (polyphone bake), enrich/rules, and emit_weight (raw ranking_freq).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from umate_lexicon.emit.rime import emit_rime
from umate_lexicon.enrich.category import classify
from umate_lexicon.enrich.overrides import apply_overrides
from umate_lexicon.enrich.polyphone import apply_polyphone_flags
from umate_lexicon.enrich.readings import apply_reading_merge
from umate_lexicon.eval.gold import evaluate_store
from umate_lexicon.ingest.essay import ingest_essay
from umate_lexicon.ingest.gold import ingest_gold
from umate_lexicon.paths import data_dir, default_store_path
from umate_lexicon.sources import default_downloads_dir, load_lock, verify_ingest_file
from umate_lexicon.store import LemmaStore
from umate_lexicon.t2s import load_unihan_simplified, make_simplifier
from umate_lexicon.verify.rules import apply_rules


def main() -> int:
    store = LemmaStore(default_store_path())
    gold_dir = data_dir() / "gold"
    lock = load_lock()
    downloads = default_downloads_dir()
    simplify = make_simplifier(None)
    for source in lock.sources:
        if source.ingest == "t2s":
            simplify = make_simplifier(load_unihan_simplified(verify_ingest_file(source, downloads)))
            break

    with store.deferred_commit():
        gold_n = 0
        for name in ("readings.tsv", "product-terms.tsv", "corrections.tsv", "latin-brands.tsv", "places.tsv", "events.tsv"):
            path = gold_dir / name
            if path.is_file():
                gold_n += ingest_gold(store, path)
        essay_source = next(s for s in lock.sources if s.id == "essay")
        essay_path = verify_ingest_file(essay_source, downloads)
        essay_n = ingest_essay(store, essay_path, locator=f"essay:{essay_source.filename}", simplify=simplify)
        for lemma in store.all_lemmas():
            store.save(classify(lemma))
        overrides = apply_overrides(store)
        reading_merge = apply_reading_merge(store)
        polyphone = apply_polyphone_flags(store)
        rejected = apply_rules(store)

    out = ROOT / "dist" / "rime"
    emit_counts = emit_rime(store, out)
    failures = evaluate_store(store)
    store.close()
    print(
        f"refresh gold={gold_n} essay={essay_n} overrides={overrides} "
        f"reading_merge={reading_merge} polyphone={polyphone} rejected={rejected} "
        f"emit={emit_counts} eval_failures={len(failures)}"
    )
    if failures:
        for item in failures:
            print(f"  FAIL {item.surface} expected {item.expected_pinyin} got {item.actual} ({item.reason})")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
