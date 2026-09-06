from __future__ import annotations

import argparse
from pathlib import Path

from umate_lexicon.emit.rime import emit_rime
from umate_lexicon.eval.gold import evaluate_store
from umate_lexicon.ingest.cedict import ingest_cedict
from umate_lexicon.ingest.chars import ingest_chars
from umate_lexicon.ingest.gold import ingest_gold
from umate_lexicon.ingest.thuocl import ingest_thuocl
from umate_lexicon.ingest.unihan import ingest_unihan
from umate_lexicon.paths import default_store_path
from umate_lexicon.pipeline import run_fixture_pipeline
from umate_lexicon.store import LemmaStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umate-lexicon")
    parser.add_argument("--store", type=Path, default=None)
    sub = parser.add_subparsers(dest="cmd", required=True)

    pipe = sub.add_parser("pipeline", help="run the fixture factory end to end")
    pipe.add_argument("--fixtures", action="store_true")
    pipe.add_argument("--out", type=Path, default=None)

    ingest = sub.add_parser("ingest")
    ingest.add_argument("kind", choices=["cedict", "thuocl", "chars", "unihan", "gold"])
    ingest.add_argument("path", type=Path)

    emit = sub.add_parser("emit")
    emit.add_argument("--out", type=Path, required=True)

    sub.add_parser("eval")
    sub.add_parser("status")

    args = parser.parse_args(argv)
    store_path = args.store or default_store_path()

    if args.cmd == "pipeline":
        stats = run_fixture_pipeline(store_path=store_path, out_dir=args.out)
        for key, value in stats.items():
            print(f"{key}\t{value}")
        return 0

    store = LemmaStore(store_path)
    if args.cmd == "ingest":
        count = {
            "cedict": ingest_cedict,
            "thuocl": ingest_thuocl,
            "chars": ingest_chars,
            "unihan": ingest_unihan,
            "gold": ingest_gold,
        }[args.kind](store, args.path)
        print(count)
        store.close()
        return 0
    if args.cmd == "emit":
        counts = emit_rime(store, args.out)
        for key, value in counts.items():
            print(f"{key}\t{value}")
        store.close()
        return 0
    if args.cmd == "eval":
        failures = evaluate_store(store)
        store.close()
        if failures:
            for item in failures:
                print(f"{item.surface}\t{item.expected_pinyin}\t{item.reason}\t{item.actual}")
            return 1
        print("ok")
        return 0
    if args.cmd == "status":
        print(store.count())
        store.close()
        return 0
    store.close()
    return 2
