from __future__ import annotations

from umate_lexicon.store import LemmaStore

_BLOCKED_SUBSTRINGS = ("http://", "https://", "www.")


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
    return rejected
