from __future__ import annotations

from pathlib import Path

from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore


def load_polyphones(path: Path | None = None) -> frozenset[str]:
    target = path or data_dir() / "gold" / "polyphones.tsv"
    chars: list[str] = []
    for raw in target.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        chars.append(line.split("\t")[0])
    return frozenset(chars)


def apply_polyphone_flags(store: LemmaStore, polyphones: frozenset[str] | None = None) -> int:
    closed = polyphones if polyphones is not None else load_polyphones()
    marked = 0
    for lemma in store.all_lemmas():
        if not any(ch in closed for ch in lemma.surface):
            continue
        flags = list(lemma.flags)
        if "polyphone" not in flags:
            flags.append("polyphone")
        lemma.flags = flags
        trusted = lemma.status == "gold" or any(
            ref.source_id in {"gold", "cedict"} for ref in lemma.sources
        )
        if not trusted and lemma.status != "rejected":
            lemma.status = "review"
        store.save(lemma)
        marked += 1
    return marked
