#!/usr/bin/env python3
"""Evaluate corpus text against the emitted Rime dictionaries.

Checks two things for each Chinese word (>=2 chars) found by jieba:
1. Coverage: does the word exist in any emitted dictionary?
2. Ranking: if present, is it the TOP-1 candidate for its pinyin?

Usage:
    PYTHONPATH=src python3 scripts/eval_corpus.py [--dist PATH] [--corpus-dir PATH]
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Add src to path if running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def parse_dict_yamls(dist_dir: Path) -> dict[str, list[tuple[int, str]]]:
    """Parse all dict.yaml files; return {pinyin: [(weight, surface), ...]}."""
    pinyin_map: dict[str, list[tuple[int, str]]] = defaultdict(list)
    all_surfaces: set[str] = set()
    for path in sorted(dist_dir.glob("*.dict.yaml")):
        in_data = False
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line == "...":
                in_data = True
                continue
            if not in_data or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                surface, pinyin, weight = parts[0], parts[1], int(parts[2])
                pinyin_map[pinyin].append((weight, surface))
                all_surfaces.add(surface)
    for pinyin in pinyin_map:
        pinyin_map[pinyin].sort(key=lambda x: -x[0])
    return pinyin_map, all_surfaces


def segment_text(text: str) -> list[str]:
    """Segment Chinese text with jieba; return Chinese words >=2 chars."""
    import jieba
    words = jieba.cut(text)
    return [w for w in words if len(w) >= 2 and re.fullmatch(r"[\u4e00-\u9fff]+", w)]


def get_pinyin(surface: str) -> str:
    """Get plain pinyin (no tones, space-separated) for a Chinese word."""
    try:
        from pypinyin import lazy_pinyin
        return " ".join(lazy_pinyin(surface))
    except ImportError:
        return ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path("dist/rime"))
    parser.add_argument("--corpus-dir", type=Path, default=Path("data/eval/corpus"))
    args = parser.parse_args()

    pinyin_map, all_surfaces = parse_dict_yamls(args.dist)
    print(f"Loaded {sum(len(v) for v in pinyin_map.values())} entries from {args.dist}")
    print(f"Unique pinyin keys: {len(pinyin_map)}")

    # Load corpus
    corpus_dir = args.corpus_dir
    corpus_texts: dict[str, str] = {}
    for path in sorted(corpus_dir.glob("*.txt")):
        corpus_texts[path.stem] = path.read_text(encoding="utf-8")
    print(f"Loaded {len(corpus_texts)} corpus files from {corpus_dir}")

    # Evaluate
    total_words = 0
    coverage_gaps: list[tuple[str, str]] = []  # (word, corpus)
    ranking_gaps: list[tuple[str, str, str, int]] = []  # (word, corpus, top1, word_weight)
    word_freq = Counter()

    for corpus_name, text in corpus_texts.items():
        words = segment_text(text)
        for word in words:
            total_words += 1
            word_freq[word] += 1
            if word not in all_surfaces:
                coverage_gaps.append((word, corpus_name))
                continue
            pinyin = get_pinyin(word)
            if not pinyin or pinyin not in pinyin_map:
                continue
            candidates = pinyin_map[pinyin]
            if not candidates:
                continue
            top1 = candidates[0][1]
            word_weight = None
            for w, s in candidates:
                if s == word:
                    word_weight = w
                    break
            if word_weight is not None and top1 != word:
                ranking_gaps.append((word, corpus_name, top1, word_weight))

    # Deduplicate and report
    unique_coverage = sorted(set(coverage_gaps))
    unique_ranking = sorted(set(ranking_gaps))

    print(f"\n{'='*60}")
    print(f"Total segmented words: {total_words}")
    print(f"Unique words: {len(word_freq)}")
    print(f"Coverage gaps (word not in any dict): {len(unique_coverage)}")
    print(f"Ranking gaps (word present but not TOP-1): {len(unique_ranking)}")
    print(f"{'='*60}")

    if unique_coverage:
        print(f"\n--- Coverage gaps ({len(unique_coverage)} unique) ---")
        gap_freq = Counter(w for w, _ in unique_coverage)
        for word, count in gap_freq.most_common(50):
            corpus = next(c for w, c in unique_coverage if w == word)
            print(f"  {word}  (freq={count}, from={corpus})")

    if unique_ranking:
        print(f"\n--- Ranking gaps ({len(unique_ranking)} unique) ---")
        rank_freq = Counter(w for w, _, _, _ in unique_ranking)
        for word, count in rank_freq.most_common(50):
            detail = next((c, t, wt) for w, c, t, wt in unique_ranking if w == word)
            corpus, top1, weight = detail
            print(f"  {word}  (freq={count}) TOP-1={top1} word_weight={weight} from={corpus}")

    # Most frequent words that passed (for sanity check)
    passed = [w for w in word_freq if w not in {c for c, _ in unique_coverage} and w not in {r for r, _, _, _ in unique_ranking}]
    print(f"\n--- Top 30 passed words (sanity check) ---")
    for w in sorted(passed, key=lambda x: -word_freq[x])[:30]:
        print(f"  {w} (freq={word_freq[w]})")


if __name__ == "__main__":
    main()
