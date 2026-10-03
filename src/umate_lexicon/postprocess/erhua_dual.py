"""Derive the missing erhua spelling for 儿-final words.

Users type 儿化 words either as independent syllables (一会儿 -> yi hui
er) or with the fused erhua r (yi hui r). The store historically kept
only one spelling per word, so the other input path dead-ends with an
orphan r (or an orphan er). This step mirrors the reading to the other
spelling with identical evidence; it derives no new surfaces and no new
pinyin content beyond the two conventional spellings of the same word.
"""

from __future__ import annotations

from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore

_FLAG = "erhua_dual"


def _mirror(pinyin_plain: str) -> str | None:
    if pinyin_plain.endswith(" r"):
        return pinyin_plain[:-2] + " er"
    if pinyin_plain.endswith(" er"):
        return pinyin_plain[:-3] + " r"
    return None


def apply_erhua_dual(store: LemmaStore) -> dict[str, int]:
    added = 0
    rows = store.all_lemmas()
    for lemma in rows:
        if not lemma.surface.endswith("儿") or lemma.status == "rejected":
            continue
        if "erhua_dual" in lemma.flags:
            continue
        mirrored = _mirror(lemma.pinyin_plain)
        if mirrored is None:
            continue
        if store.get(lemma.surface, mirrored) is not None:
            continue
        store.upsert(
            Lemma(
                surface=lemma.surface,
                pinyin_plain=mirrored,
                pinyin_toned=lemma.pinyin_toned,
                weight=lemma.weight,
                status=lemma.status,
                script=lemma.script,
                categories=list(lemma.categories),
                flags=[*lemma.flags, _FLAG],
                entity_type=lemma.entity_type,
                domain_freq=dict(lemma.domain_freq),
                sources=[
                    SourceRef(ref.source_id, ref.license, ref.locator)
                    for ref in lemma.sources
                ],
                rank=lemma.rank,
            )
        )
        added += 1
    return {"erhua_dual_added": added}
