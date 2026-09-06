from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore


@dataclass(frozen=True)
class EvalFailure:
    surface: str
    expected_pinyin: str
    actual: tuple[str, ...]
    reason: str


def load_eval_sentences(path: Path | None = None) -> list[tuple[str, str, str]]:
    target = path or data_dir() / "gold" / "eval-sentences.tsv"
    rows: list[tuple[str, str, str]] = []
    for raw in target.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        rows.append((parts[0], parts[1], parts[2].replace("ü", "v")))
    return rows


def evaluate_store(store: LemmaStore, path: Path | None = None) -> list[EvalFailure]:
    failures: list[EvalFailure] = []
    for _typed, surface, expected in load_eval_sentences(path):
        lemmas = store.readings_for(surface)
        plains = tuple(item.pinyin_plain for item in lemmas if item.status != "rejected")
        if expected not in plains:
            failures.append(
                EvalFailure(
                    surface=surface,
                    expected_pinyin=expected,
                    actual=plains,
                    reason="missing_reading",
                )
            )
            continue
        wrong = [item for item in lemmas if item.pinyin_plain != expected and "gold" in item.flags]
        if wrong:
            failures.append(
                EvalFailure(
                    surface=surface,
                    expected_pinyin=expected,
                    actual=plains,
                    reason="conflicting_gold",
                )
            )
    return failures
