from __future__ import annotations

from umate_lexicon.layers import han_len, ranking_freq
from umate_lexicon.store import LemmaStore

_BLOCKED_SUBSTRINGS = ("http://", "https://", "www.")
# Essay-only invented n-grams below this floor are usually segmentation
# artifacts (可以骂) that poison sentence DP without helping coverage.
_ESSAY_ONLY_MIN_FREQ = 200


def apply_rules(store: LemmaStore) -> int:
    rejected = 0
    for lemma in store.all_lemmas():
        if not lemma.surface.strip() or not lemma.pinyin_plain.strip():
            lemma.status = "rejected"
            store.save(lemma)
            rejected += 1
            continue
        if any(marker in lemma.surface.lower() for marker in _BLOCKED_SUBSTRINGS):
            lemma.status = "rejected"
            store.save(lemma)
            rejected += 1
            continue
        source_ids = {ref.source_id for ref in lemma.sources}
        if (
            source_ids == {"essay"}
            and han_len(lemma.surface) >= 3
            and ranking_freq(lemma) < _ESSAY_ONLY_MIN_FREQ
            and lemma.status != "gold"
        ):
            lemma.status = "rejected"
            store.save(lemma)
            rejected += 1
    return rejected
