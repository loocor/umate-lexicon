from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from umate_lexicon.lemma import Lemma

READING_SCHEMA = {
    "type": "object",
    "required": ["surface", "pinyin_plain", "confidence", "reason"],
    "properties": {
        "surface": {"type": "string"},
        "pinyin_plain": {"type": "string"},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
}


@dataclass(frozen=True)
class ReadingVerdict:
    surface: str
    pinyin_plain: str
    confidence: float
    reason: str


class ReadingChecker(Protocol):
    def check(self, lemma: Lemma) -> ReadingVerdict: ...


class NullChecker:
    """Default backend: do not call a model. Gold tests own pinyin."""

    def check(self, lemma: Lemma) -> ReadingVerdict:
        return ReadingVerdict(
            surface=lemma.surface,
            pinyin_plain=lemma.pinyin_plain,
            confidence=0.0,
            reason="llm disabled; gold/rules only",
        )
