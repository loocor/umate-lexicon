from __future__ import annotations

"""Rank resolution: the only writer of the store `rank` column.

Policy v1 ("v1-absorb") freezes the pre-absorption emit semantics: the
strongest measured domain column wins (core corpus first), with the
single-char sibling rule. Emit reads `rank` instead of recomputing from
domain_freq, so ranking strategy changes become versioned store
migrations instead of per-emit behavior. Future policy versions bump
POLICY_VERSION and re-run resolve; domain_freq stays untouched evidence.
"""

from collections import defaultdict

from umate_lexicon import layers as _layers
from umate_lexicon.store import LemmaStore

POLICY_VERSION = "v1-absorb"
_META_KEY = "policy_version"


def resolve_store(store: LemmaStore) -> dict[str, int | str]:
    """Compute and bake `rank` for every lemma, then stamp policy_version."""
    siblings: dict[str, list] = defaultdict(list)
    lemmas = store.all_lemmas()
    for lemma in lemmas:
        siblings[lemma.surface].append(lemma)
    rows: list[tuple[int, str, str]] = []
    for lemma in lemmas:
        rank = _layers._emit_ranking_freq(lemma, siblings.get(lemma.surface))
        rows.append((rank, lemma.surface, lemma.pinyin_plain))
    with store.deferred_commit():
        store.set_ranks(rows)
        store.set_meta(_META_KEY, POLICY_VERSION)
    return {"resolved": len(rows), "policy_version": POLICY_VERSION}


def ensure_resolved(store: LemmaStore) -> bool:
    """Resolve once if the store has no policy stamp. Returns True if it ran."""
    if store.get_meta(_META_KEY) is not None:
        return False
    resolve_store(store)
    return True
