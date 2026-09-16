#!/usr/bin/env python3
"""Classify the pinned light Tencent vocab against a non-wiki locked store.

Does not emit into dist/rime and does not treat Tencent as frequency.
Wiki dumps are skipped so this validation does not pull multi-GB files.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from umate_lexicon.fetch import fetch_one
from umate_lexicon.ingest.compose import is_han_only
from umate_lexicon.ingest.tencent import (
    ACCEPT_NEW,
    OVERLAY_EXISTING,
    ingest_tencent,
    summarize_tencent_gates,
)
from umate_lexicon.pipeline import _ingest_authored_gold, _ingest_pinned, _simplifier_from_lock
from umate_lexicon.sources import (
    SourceLockError,
    default_downloads_dir,
    load_lock,
    sha256_file,
    verify_artifact,
    verify_ingest_file,
)
from umate_lexicon.store import LemmaStore
from umate_lexicon.word2vec import read_word2vec_header

WIKI_INGEST = frozenset({"wiki", "wiki_page", "wiki_linktarget", "wiki_category"})
SPOT_KEEP = ("微信", "抖音", "人工智能")
SPOT_FILTER = ("的",)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="fetch missing non-wiki pins first")
    parser.add_argument("--downloads", type=Path, default=None)
    parser.add_argument("--store", type=Path, required=True, help="temporary sqlite path")
    parser.add_argument("-o", "--output", type=Path, default=None)
    args = parser.parse_args(argv)

    lock = load_lock()
    downloads = args.downloads or default_downloads_dir()
    selected = tuple(source for source in lock.sources if source.ingest not in WIKI_INGEST)
    tencent = next(source for source in selected if source.id == "tencent")
    skipped: dict[str, str] = {}
    ready: dict[str, Path] = {}
    for source in selected:
        if args.fetch:
            try:
                fetch_one(source, downloads)
            except SourceLockError as exc:
                if source.id == "tencent":
                    raise
                skipped[source.id] = str(exc)
                continue
        try:
            ready[source.id] = verify_ingest_file(source, downloads)
        except SourceLockError as exc:
            if source.id == "tencent":
                raise
            skipped[source.id] = str(exc)

    artifact = verify_artifact(tencent, downloads)
    vocab = ready[tencent.id]
    digest = sha256_file(artifact)
    vocab_size, dim = read_word2vec_header(artifact)
    raw_lines = [line for line in vocab.read_text(encoding="utf-8").splitlines() if line.strip()]
    raw_shape = {
        "lines": len(raw_lines),
        "unique": len(set(raw_lines)),
        "ascii_alpha": sum(1 for word in raw_lines if word.isascii() and word.isalpha()),
        "mixed_han": sum(
            1
            for word in raw_lines
            if any("\u4e00" <= char <= "\u9fff" for char in word) and not is_han_only(word)
        ),
        "has_digit": sum(1 for word in raw_lines if any(char.isdigit() for char in word)),
    }

    store = LemmaStore(args.store)
    base = tuple(source for source in selected if source.id != "tencent" and source.id in ready)
    simplify = _simplifier_from_lock(tuple(source for source in selected if source.id in ready), ready)
    with store.deferred_commit():
        gold = _ingest_authored_gold(store)
        base_stats = {source.id: _ingest_pinned(store, source, ready[source.id], simplify=simplify) for source in base}
    lemmas_before = store.count()
    summary = summarize_tencent_gates(store, vocab, simplify=simplify, sample_limit=8)
    probes = {}
    for surface in (*SPOT_KEEP, *SPOT_FILTER):
        probes[surface] = next(
            (action for item, action in _probe(store, vocab, simplify) if item == surface),
            "absent_from_vocab",
        )
    with store.deferred_commit():
        ingested = ingest_tencent(store, vocab, locator=f"{tencent.id}:{tencent.filename}", simplify=simplify)
    lemmas_after = store.count()
    after: dict[str, list[dict[str, object]]] = {}
    for surface in (*SPOT_KEEP, *SPOT_FILTER, "游戏"):
        after[surface] = [
            {
                "pinyin": item.pinyin_plain,
                "status": item.status,
                "domain_freq": dict(item.domain_freq),
                "sources": [ref.source_id for ref in item.sources],
            }
            for item in store.readings_for(surface)
        ]
    store.close()

    report = {
        "artifact": {
            "id": tencent.id,
            "filename": tencent.filename,
            "bytes": artifact.stat().st_size,
            "sha256": digest,
            "sha256_expected": tencent.sha256,
            "hash_ok": digest == tencent.sha256,
            "header_vocab_size": vocab_size,
            "header_dim": dim,
            "extracted": str(vocab),
            "extracted_lines": raw_shape["lines"],
            "raw_shape": raw_shape,
        },
        "base": {
            "gold": gold,
            "ingest": base_stats,
            "skipped": skipped,
            "lemmas_before_tencent": lemmas_before,
        },
        "fusion": summary,
        "ingest_tencent_count": ingested,
        "lemmas_after_tencent": lemmas_after,
        "new_store_lemmas": lemmas_after - lemmas_before,
        "probes": probes,
        "after_ingest": after,
        "notes": [
            "Tencent is coverage only; essay remains the frequency source.",
            "Vectors discarded; ingest uses the extracted word list.",
            "Wiki dumps were not fetched or ingested.",
            "This store is a validation scratch path, not a dictionary merge.",
        ],
    }
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    if not report["artifact"]["hash_ok"]:
        return 1
    if probes.get("微信") not in {OVERLAY_EXISTING, ACCEPT_NEW} or probes.get("的") != "drop_single_char":
        return 1
    return 0


def _probe(store, vocab, simplify):
    from umate_lexicon.ingest.tencent import iter_tencent_classifications

    wanted = set(SPOT_KEEP) | set(SPOT_FILTER)
    for surface, action in iter_tencent_classifications(store, vocab, simplify=simplify):
        if surface in wanted:
            yield surface, action
            wanted.discard(surface)
            if not wanted:
                return


if __name__ == "__main__":
    sys.exit(main())
