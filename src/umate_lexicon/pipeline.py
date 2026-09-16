from __future__ import annotations

from pathlib import Path

from umate_lexicon.emit.rime import emit_rime
from umate_lexicon.enrich.category import classify
from umate_lexicon.enrich.polyphone import apply_polyphone_flags
from umate_lexicon.eval.gold import evaluate_store
from umate_lexicon.ingest.cedict import ingest_cedict
from umate_lexicon.ingest.chars import ingest_chars
from umate_lexicon.ingest.emoji import ingest_emoji
from umate_lexicon.ingest.essay import ingest_essay
from umate_lexicon.ingest.gold import ingest_gold
from umate_lexicon.ingest.luna import ingest_luna
from umate_lexicon.ingest.tencent import ingest_tencent
from umate_lexicon.ingest.thuocl import ingest_thuocl
from umate_lexicon.ingest.unihan import ingest_unihan
from umate_lexicon.paths import data_dir, default_store_path
from umate_lexicon.sources import (
    PinnedSource,
    SourceLockError,
    default_downloads_dir,
    load_lock,
    verify_ingest_file,
)
from umate_lexicon.store import LemmaStore
from umate_lexicon.verify.rules import apply_rules


def run_fixture_pipeline(
    store_path: Path | None = None,
    out_dir: Path | None = None,
) -> dict[str, int]:
    root = data_dir()
    store = LemmaStore(store_path or default_store_path())
    with store.deferred_commit():
        stats = {
            "gold": _ingest_authored_gold(store),
            "chars": ingest_chars(store, root / "fixtures" / "chars.tsv"),
            "unihan": ingest_unihan(store, root / "fixtures" / "unihan.txt"),
            "cedict": ingest_cedict(store, root / "fixtures" / "cedict.txt"),
            "thuocl": ingest_thuocl(store, root / "fixtures" / "thuocl.txt"),
            "luna": ingest_luna(store, root / "fixtures" / "luna.dict.yaml"),
            "essay": ingest_essay(store, root / "fixtures" / "essay.txt"),
            "emoji": ingest_emoji(store, root / "fixtures" / "emoji_word.txt"),
            "tencent": ingest_tencent(store, root / "fixtures" / "tencent.txt"),
        }
    return _finish(store, stats, out_dir)


def run_locked_pipeline(
    store_path: Path | None = None,
    out_dir: Path | None = None,
    lock_path: Path | None = None,
    downloads_dir: Path | None = None,
) -> dict[str, int]:
    lock = load_lock(lock_path)
    dest = downloads_dir or default_downloads_dir()
    ready = {source.id: verify_ingest_file(source, dest) for source in lock.sources}
    store = LemmaStore(store_path or default_store_path())
    stats: dict[str, int] = {}
    with store.deferred_commit():
        stats["gold"] = _ingest_authored_gold(store)
        for source in lock.sources:
            stats[source.id] = _ingest_pinned(store, source, ready[source.id])
    return _finish(store, stats, out_dir)


def _ingest_authored_gold(store: LemmaStore) -> int:
    gold_dir = data_dir() / "gold"
    count = ingest_gold(store, gold_dir / "readings.tsv")
    product = gold_dir / "product-terms.tsv"
    if product.is_file():
        count += ingest_gold(store, product)
    return count


def _ingest_pinned(store: LemmaStore, source: PinnedSource, path: Path) -> int:
    locator = f"{source.id}:{source.filename}"
    if source.ingest == "unihan":
        return ingest_unihan(store, path, locator=locator)
    if source.ingest == "cedict":
        return ingest_cedict(store, path, locator=locator)
    if source.ingest == "thuocl":
        return ingest_thuocl(store, path, locator=locator)
    if source.ingest == "luna":
        return ingest_luna(store, path, locator=locator)
    if source.ingest == "essay":
        return ingest_essay(store, path, locator=locator)
    if source.ingest == "emoji":
        return ingest_emoji(store, path, locator=locator)
    if source.ingest == "tencent":
        return ingest_tencent(store, path, locator=locator)
    raise SourceLockError(f"unknown ingest kind {source.ingest!r} for {source.id}")


def _finish(store: LemmaStore, stats: dict[str, int], out_dir: Path | None) -> dict[str, int]:
    with store.deferred_commit():
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
