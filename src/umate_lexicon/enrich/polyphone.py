from __future__ import annotations

from pathlib import Path

from umate_lexicon.layers import BASE_AUTO_FREQ, han_len, ranking_freq
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
    """Flag lemmas that contain a polyphone character.

    Review status means "needs scrutiny", not "do not emit". High-frequency
    multi-char lemmas (带着 / 拿着) keep or regain ``auto`` so sentence DP can
    see them; low-frequency composed guesses still drop to ``review``.
    """
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
        if trusted or lemma.status == "rejected":
            store.save(lemma)
            marked += 1
            continue
        # Containing a polyphone char is not enough to ban a stable phrase.
        if han_len(lemma.surface) >= 2 and ranking_freq(lemma) >= BASE_AUTO_FREQ:
            if lemma.status == "review":
                lemma.status = "auto"
            store.save(lemma)
            marked += 1
            continue
        if lemma.status != "rejected":
            lemma.status = "review"
        store.save(lemma)
        marked += 1
    return marked
