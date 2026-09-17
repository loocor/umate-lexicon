from __future__ import annotations

import argparse
from pathlib import Path

from umate_lexicon.emit.rime import emit_rime
from umate_lexicon.eval.gold import evaluate_store
from umate_lexicon.fetch import fetch_locked_sources
from umate_lexicon.gaps import classify_ledger, render_gaps
from umate_lexicon.ingest.cedict import ingest_cedict
from umate_lexicon.ingest.chars import ingest_chars
from umate_lexicon.ingest.emoji import ingest_emoji
from umate_lexicon.ingest.essay import ingest_essay
from umate_lexicon.ingest.gold import ingest_gold
from umate_lexicon.ingest.luna import ingest_luna
from umate_lexicon.ingest.tencent import ingest_tencent
from umate_lexicon.ingest.tgh import ingest_tgh
from umate_lexicon.ingest.thuocl import ingest_thuocl
from umate_lexicon.ingest.unihan import ingest_unihan
from umate_lexicon.ingest.wiki import (
    ingest_wiki,
    ingest_wiki_category,
    ingest_wiki_linktarget,
    ingest_wiki_page,
)
from umate_lexicon.eval.tencent_absorb import measure_tencent_absorb, render_tencent_absorb
from umate_lexicon.inventory import render_summary, summarize_store
from umate_lexicon.paths import default_store_path
from umate_lexicon.pipeline import run_fixture_pipeline, run_locked_pipeline
from umate_lexicon.sources import default_downloads_dir, load_lock, verify_ingest_file
from umate_lexicon.store import LemmaStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="umate-lexicon")
    parser.add_argument("--store", type=Path, default=None)
    sub = parser.add_subparsers(dest="cmd", required=True)

    pipe = sub.add_parser("pipeline", help="run the factory end to end")
    pipe.add_argument(
        "--fixtures",
        action="store_true",
        help="use short original samples instead of pinned dumps",
    )
    pipe.add_argument("--out", type=Path, default=None)

    ingest = sub.add_parser("ingest")
    ingest.add_argument("kind", choices=["cedict", "thuocl", "chars", "unihan", "tgh", "gold", "luna", "essay", "emoji", "tencent", "wiki", "wiki_page", "wiki_linktarget", "wiki_category"])
    ingest.add_argument("path", type=Path)

    emit = sub.add_parser("emit")
    emit.add_argument("--out", type=Path, required=True)

    aosp = sub.add_parser("emit-aosp", help="emit aosp_en.dict.yaml + en_us_unigrams.tsv")
    aosp.add_argument("--csv", type=Path, required=True, help="AOSP LatinIME wordlist CSV")
    aosp.add_argument("--out", type=Path, required=True)
    aosp.add_argument("--min-length", type=int, default=4)
    aosp.add_argument("--unigram-limit", type=int, default=20_000)
    aosp.add_argument("--snapshot-note", default="snapshot from Lexicon emit")

    sub.add_parser("eval")
    sub.add_parser("status")
    sub.add_parser("fetch", help="download and extract pinned dumps")
    sub.add_parser("verify-sources", help="check pinned dumps without ingesting")
    sub.add_parser("inventory", help="summarize lemma coverage")
    absorb = sub.add_parser("tencent-absorb", help="measure tencent-light absorb against the store")
    absorb.add_argument("vocab", type=Path, help="extracted tencent-light-vocab.txt")

    gaps = sub.add_parser("gaps", help="classify reported word gaps against the store")
    gaps.add_argument("--file", type=Path, default=None, help="gap ledger TSV (default data/gold/daily-gaps.tsv)")

    args = parser.parse_args(argv)
    store_path = args.store or default_store_path()

    if args.cmd == "pipeline":
        if args.fixtures:
            stats = run_fixture_pipeline(store_path=store_path, out_dir=args.out)
        else:
            stats = run_locked_pipeline(store_path=store_path, out_dir=args.out)
        for key, value in stats.items():
            print(f"{key}\t{value}")
        return 0

    if args.cmd == "fetch":
        results = fetch_locked_sources()
        for key, value in results.items():
            print(f"{key}\t{value}")
        return 0

    if args.cmd == "verify-sources":
        lock = load_lock()
        dest = default_downloads_dir()
        for source in lock.sources:
            path = verify_ingest_file(source, dest)
            print(f"{source.id}\t{path}")
        return 0

    if args.cmd == "emit-aosp":
        from umate_lexicon.emit.aosp_en import emit_aosp_en

        counts = emit_aosp_en(
            args.csv,
            args.out,
            min_length=args.min_length,
            unigram_limit=args.unigram_limit,
            snapshot_note=args.snapshot_note,
        )
        for key, value in counts.items():
            print(f"{key}\t{value}")
        return 0

    store = LemmaStore(store_path)
    if args.cmd == "ingest":
        count = {
            "cedict": ingest_cedict,
            "thuocl": ingest_thuocl,
            "chars": ingest_chars,
            "unihan": ingest_unihan,
            "tgh": ingest_tgh,
            "gold": ingest_gold,
            "luna": ingest_luna,
            "essay": ingest_essay,
            "emoji": ingest_emoji,
            "tencent": ingest_tencent,
            "wiki": ingest_wiki,
            "wiki_page": ingest_wiki_page,
            "wiki_linktarget": ingest_wiki_linktarget,
            "wiki_category": ingest_wiki_category,
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

    if args.cmd == "inventory":
        summary = summarize_store(store)
        print(render_summary(summary), end="")
        store.close()
        return 0
    if args.cmd == "gaps":
        print(render_gaps(classify_ledger(store, args.file)), end="")
        store.close()
        return 0
    if args.cmd == "tencent-absorb":
        stats = measure_tencent_absorb(store, args.vocab)
        print(render_tencent_absorb(stats), end="")
        store.close()
        return 0
    if args.cmd == "status":
        print(store.count())
        store.close()
        return 0
    store.close()
    return 2
