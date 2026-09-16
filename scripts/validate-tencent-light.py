#!/usr/bin/env python3
"""Run the largest locked subset this machine can verify, then measure tencent-light absorb.

Does not invent hashes. Sources that fail verify are skipped and reported.
Validates light coverage fusion only; the official ~8M dump stays out of scope.
"""

from __future__ import annotations

from pathlib import Path

from umate_lexicon.eval.tencent_absorb import measure_tencent_absorb, render_tencent_absorb
from umate_lexicon.pipeline import run_locked_pipeline
from umate_lexicon.sources import (
    SourceLockError,
    default_downloads_dir,
    default_lock_path,
    load_lock,
    verify_ingest_file,
)
from umate_lexicon.store import LemmaStore


def main() -> int:
    lock = load_lock(default_lock_path())
    dest = default_downloads_dir()
    skip: set[str] = set()
    ready: list[str] = []
    for source in lock.sources:
        try:
            verify_ingest_file(source, dest)
        except SourceLockError as exc:
            print(f"skip\t{source.id}\t{exc}")
            skip.add(source.id)
        else:
            ready.append(source.id)
            print(f"ready\t{source.id}")
    store_path = Path("data/store/lemmas.sqlite")
    out_dir = Path("dist/rime")
    if store_path.exists():
        store_path.unlink()
    stats = run_locked_pipeline(
        store_path=store_path,
        out_dir=out_dir,
        skip_ids=skip,
    )
    print("pipeline")
    for key, value in stats.items():
        print(f"{key}\t{value}")
    vocab = dest / "tencent-light-vocab.txt"
    store = LemmaStore(store_path)
    report = measure_tencent_absorb(store, vocab)
    store.close()
    print("tencent-absorb")
    print(render_tencent_absorb(report), end="")
    print(f"ran_sources\t{','.join(ready)}")
    print(f"skipped_sources\t{','.join(sorted(skip)) if skip else '-'}")
    print("scope\tlight coverage fusion only; official ~8M dump out of scope")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
