"""Triage coverage gaps from the eval corpus against the lemma store.

Classifies each out-of-vocabulary word as `missing` (no lemma, not
composable) or `segmentation` (every character has its own reading), so
only true gaps reach the daily-gaps ledger. Read-only against the store.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from umate_lexicon.gaps import classify_surface  # noqa: E402
from umate_lexicon.store import LemmaStore  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", type=Path, default=Path("data/eval/corpus"))
    parser.add_argument("--store", type=Path, default=Path("data/store/lemmas.sqlite"))
    parser.add_argument("--missing-out", type=Path, default=Path("data/eval/missing-words.tsv"))
    args = parser.parse_args()

    from eval_corpus import segment_text

    store = LemmaStore(args.store)
    words: Counter[str] = Counter()
    for path in sorted(args.corpus_dir.glob("*.txt")):
        for word in segment_text(path.read_text(encoding="utf-8")):
            if len(word) >= 2:
                words[word] += 1

    buckets: Counter[str] = Counter()
    missing: list[str] = []
    for word, count in words.most_common():
        if store.readings_for(word):
            continue
        finding = classify_surface(store, word)
        buckets[finding.bucket] += 1
        if finding.bucket == "missing":
            missing.append(word)

    print(f"Unique OOV words: {sum(buckets.values())}")
    for bucket, count in buckets.most_common():
        print(f"  {bucket}: {count}")

    if missing:
        args.missing_out.parent.mkdir(parents=True, exist_ok=True)
        with args.missing_out.open("w", encoding="utf-8") as fh:
            fh.write("surface\tfreq\n")
            for word in missing:
                fh.write(f"{word}\t{words[word]}\n")
        print(f"Wrote {len(missing)} missing words to {args.missing_out}")


if __name__ == "__main__":
    main()
