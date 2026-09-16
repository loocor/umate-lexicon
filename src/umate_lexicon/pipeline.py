from __future__ import annotations

from pathlib import Path

from umate_lexicon.emit.rime import emit_rime
from umate_lexicon.enrich.category import classify
from umate_lexicon.enrich.overrides import apply_overrides
from umate_lexicon.enrich.polyphone import apply_polyphone_flags
from umate_lexicon.enrich.readings import apply_reading_merge
from umate_lexicon.eval.gold import evaluate_store
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
from umate_lexicon.ingest.wiki import ingest_wiki
from umate_lexicon.paths import data_dir, default_store_path
from umate_lexicon.sources import (
    PinnedSource,
    SourceLockError,
    default_downloads_dir,
    load_lock,
    verify_ingest_file,
)
from umate_lexicon.store import LemmaStore
from umate_lexicon.t2s import SimplifyFn, load_unihan_simplified, make_simplifier
from umate_lexicon.verify.rules import apply_rules

_GOLD_SKIP = frozenset({"polyphones.tsv", "eval-sentences.tsv", "layer-overrides.tsv"})


def run_fixture_pipeline(
    store_path: Path | None = None,
    out_dir: Path | None = None,
) -> dict[str, int]:
    root = data_dir()
    store = LemmaStore(store_path or default_store_path())
    simplify = make_simplifier(load_unihan_simplified(root / "fixtures" / "unihan-variants.txt"))
    with store.deferred_commit():
        stats = {
            "gold": _ingest_authored_gold(store),
            "chars": ingest_chars(store, root / "fixtures" / "chars.tsv"),
            "unihan": ingest_unihan(store, root / "fixtures" / "unihan.txt"),
            "tgh": ingest_tgh(store, root / "fixtures" / "unihan-tgh.txt"),
            "cedict": ingest_cedict(store, root / "fixtures" / "cedict.txt"),
            "thuocl": ingest_thuocl(store, root / "fixtures" / "thuocl.txt"),
            "luna": ingest_luna(store, root / "fixtures" / "luna.dict.yaml", simplify=simplify),
            "essay": ingest_essay(store, root / "fixtures" / "essay.txt", simplify=simplify),
            "emoji": ingest_emoji(store, root / "fixtures" / "emoji_word.txt", simplify=simplify),
            "tencent": ingest_tencent(store, root / "fixtures" / "tencent.txt", simplify=simplify),
            "wiki": ingest_wiki(store, root / "fixtures" / "wiki-titles.txt", simplify=simplify),
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
    simplify = _simplifier_from_lock(lock.sources, ready)
    stats: dict[str, int] = {}
    with store.deferred_commit():
        stats["gold"] = _ingest_authored_gold(store)
        for source in lock.sources:
            stats[source.id] = _ingest_pinned(store, source, ready[source.id], simplify=simplify)
    return _finish(store, stats, out_dir)


def _ingest_authored_gold(store: LemmaStore) -> int:
    gold_dir = data_dir() / "gold"
    count = 0
    ordered: list[Path] = []
    readings = gold_dir / "readings.tsv"
    if readings.is_file():
        ordered.append(readings)
    for path in sorted(gold_dir.glob("*.tsv")):
        if path.name in _GOLD_SKIP or path in ordered:
            continue
        ordered.append(path)
    for path in ordered:
        count += ingest_gold(store, path)
    return count


def _simplifier_from_lock(sources: tuple[PinnedSource, ...], ready: dict[str, Path]) -> SimplifyFn:
    for source in sources:
        if source.ingest == "t2s":
            return make_simplifier(load_unihan_simplified(ready[source.id]))
    return make_simplifier(None)


def _ingest_pinned(
    store: LemmaStore,
    source: PinnedSource,
    path: Path,
    simplify: SimplifyFn | None = None,
) -> int:
    locator = f"{source.id}:{source.filename}"
    if source.ingest == "unihan":
        return ingest_unihan(store, path, locator=locator)
    if source.ingest == "t2s":
        return len(load_unihan_simplified(path))
    if source.ingest == "tgh":
        return ingest_tgh(store, path, locator=locator)
    if source.ingest == "cedict":
        return ingest_cedict(store, path, locator=locator)
    if source.ingest == "thuocl":
        return ingest_thuocl(store, path, locator=locator)
    if source.ingest == "luna":
        return ingest_luna(store, path, locator=locator, simplify=simplify)
    if source.ingest == "essay":
        return ingest_essay(store, path, locator=locator, simplify=simplify)
    if source.ingest == "emoji":
        return ingest_emoji(store, path, locator=locator, simplify=simplify)
    if source.ingest == "tencent":
        return ingest_tencent(store, path, locator=locator, simplify=simplify)
    if source.ingest == "wiki":
        return ingest_wiki(store, path, locator=locator, simplify=simplify)
    raise SourceLockError(f"unknown ingest kind {source.ingest!r} for {source.id}")


def _finish(store: LemmaStore, stats: dict[str, int], out_dir: Path | None) -> dict[str, int]:
    with store.deferred_commit():
        for lemma in store.all_lemmas():
            store.save(classify(lemma))
        stats["overrides"] = apply_overrides(store)
        stats["reading_merge"] = apply_reading_merge(store)
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
