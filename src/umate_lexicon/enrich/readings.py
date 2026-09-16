from __future__ import annotations

from collections import defaultdict

from umate_lexicon.ingest.compose import is_trusted_reading
from umate_lexicon.store import LemmaStore

_MASS_DOMAINS = ("essay", "tencent", "thuocl")


def apply_reading_merge(store: LemmaStore) -> int:
    grouped: dict[str, list] = defaultdict(list)
    for lemma in store.all_lemmas():
        grouped[lemma.surface].append(lemma)
    marked = 0
    for lemmas in grouped.values():
        if len(lemmas) < 2:
            continue
        trusted = [item for item in lemmas if is_trusted_reading(item)]
        if not trusted:
            continue
        trusted_py = {item.pinyin_plain for item in trusted}
        for lemma in lemmas:
            if lemma.pinyin_plain in trusted_py:
                continue
            flags = list(lemma.flags)
            if "untrusted_reading" not in flags:
                flags.append("untrusted_reading")
            lemma.flags = flags
            freq = dict(lemma.domain_freq)
            for domain in _MASS_DOMAINS:
                freq.pop(domain, None)
            lemma.domain_freq = freq
            store.save(lemma)
            marked += 1
    return marked
