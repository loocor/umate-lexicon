"""Ingest Wikinews (zh.wikinews.org) article text as vocabulary.

Input is a dated TSV snapshot produced by scripts/fetch-wikinews.py:
one article per line, `title<TAB>body` (Simplified Chinese, cleaned).
Words are segmented with jieba; only missing composable surfaces are
added, so this channel extends coverage without touching weights.
"""
from __future__ import annotations

from pathlib import Path

from umate_lexicon.ingest.compose import compose_pinyin, is_han_only
from umate_lexicon.ingest.io import read_ingest_text
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore

MIN_WORD_LEN = 2
MIN_FREQ = 2


def _segment() -> "list[str]":
    try:
        import jieba
    except ImportError as exc:  # pragma: no cover - environment error
        raise RuntimeError(
            "ingest_wikinews requires jieba (uv run --with jieba ...)"
        ) from exc
    jieba.setLogLevel(60)
    return jieba


def segment_words(text: str) -> dict[str, int]:
    """Chinese words (>=2 han chars) with occurrence counts in one body."""
    jieba = _segment()
    freq: dict[str, int] = {}
    for word in jieba.cut(text):
        word = word.strip()
        if len(word) < MIN_WORD_LEN or not is_han_only(word):
            continue
        freq[word] = freq.get(word, 0) + 1
    return freq


def ingest_wikinews(store: LemmaStore, path: Path, locator: str | None = None) -> int:
    text = read_ingest_text(path)
    source = locator or f"wikinews:{path.name}"
    known = {lemma.surface for lemma in store.all_lemmas()}
    corpus_freq: dict[str, int] = {}
    for raw in text.splitlines():
        if not raw.strip() or raw.startswith("#"):
            continue
        parts = raw.split("\t", 1)
        body = parts[1] if len(parts) > 1 else parts[0]
        for word, n in segment_words(body).items():
            corpus_freq[word] = corpus_freq.get(word, 0) + n
    count = 0
    for surface in sorted(corpus_freq):
        if surface in known:
            continue
        if corpus_freq[surface] < MIN_FREQ:
            continue
        pinyin = compose_pinyin(store, surface)
        if pinyin is None:
            continue
        store.upsert(
            Lemma(
                surface=surface,
                pinyin_plain=pinyin,
                weight=corpus_freq[surface],
                status="auto",
                domain_freq={"wikinews": corpus_freq[surface]},
                sources=[SourceRef("wikinews", "cc-by-4.0-wikinews", source)],
            )
        )
        count += 1
    return count
