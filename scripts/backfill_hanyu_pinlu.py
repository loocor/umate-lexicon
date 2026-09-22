"""One-off backfill: ingest kHanyuPinlu readings into the existing store.

The locked pipeline re-ingests everything; this script adds only the
kHanyuPinlu pass (authoritative Pinlu frequency readings, the source of
polyphone secondary readings such as 长/chang) on top of the current
lemmas.sqlite, then re-emits the Rime tables. Safe to re-run: upsert
merges, and the simplify filter keeps traditional code points out.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from umate_lexicon.emit.rime import emit_rime
from umate_lexicon.ingest.unihan import ingest_unihan
from umate_lexicon.paths import data_dir, default_store_path
from umate_lexicon.sources import load_lock, verify_ingest_file
from umate_lexicon.store import LemmaStore
from umate_lexicon.t2s import load_unihan_simplified, make_simplifier


def main() -> int:
    root = data_dir()
    store_path = default_store_path()
    if not store_path.is_file():
        print(f"store missing: {store_path}")
        return 1

    lock = load_lock()
    unihan_sources = [s for s in lock.sources if s.ingest == "unihan"]
    if not unihan_sources:
        print("no unihan source in lock")
        return 1
    source = unihan_sources[0]
    downloads = root / "sources" / "downloads"
    path = verify_ingest_file(source, downloads)
    print(f"ingesting kHanyuPinlu from {path.name}")

    simplify_table = None
    for candidate in lock.sources:
        if candidate.ingest == "t2s":
            simplify_table = load_unihan_simplified(
                verify_ingest_file(candidate, downloads)
            )
            break
    simplify = make_simplifier(simplify_table)

    store = LemmaStore(store_path)
    locator = f"{source.id}:{source.filename}"
    count = ingest_unihan(store, path, locator=locator, simplify=simplify)
    print(f"ingested rows (mandarin + pinlu pass): {count}")

    version = "0.1.0"
    stats = emit_rime(store, root.parent / "dist" / "rime", version=version)
    print(f"emit stats: {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
