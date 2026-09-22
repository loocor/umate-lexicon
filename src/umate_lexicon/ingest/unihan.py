from __future__ import annotations

import re
from pathlib import Path

from umate_lexicon.ingest.io import read_ingest_text
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore
from umate_lexicon.t2s import SimplifyFn

_LINE = re.compile(r"^U\+([0-9A-F]+)\tkMandarin\t(.+)$")
_PINLU_LINE = re.compile(r"^U\+([0-9A-F]+)\tkHanyuPinlu\t(.+)$")
_PINLU_TOKEN = re.compile(r"^([^()]+)\((\d+)\)$")


def ingest_unihan(
    store: LemmaStore,
    path: Path,
    locator: str | None = None,
    simplify: SimplifyFn | None = None,
) -> int:
    text = read_ingest_text(path)
    count = 0
    source = locator or str(path)
    for raw in text.splitlines():
        stripped = raw.strip()
        surface, readings = _kmandarin_row(stripped)
        if surface is not None:
            for reading in readings:
                plain = _kmandarin_to_plain(reading.lower())
                if not plain:
                    continue
                store.upsert(
                    Lemma(
                        surface=surface,
                        pinyin_plain=plain,
                        pinyin_toned=reading if _has_tone_mark(reading) else None,
                        weight=1,
                        status="auto",
                        domain_freq={"unihan": 1},
                        sources=[SourceRef("unihan", "unicode", source)],
                    )
                )
                count += 1
            continue
        surface, pinlu = _pinlu_row(stripped)
        if surface is None:
            continue
        for token in pinlu:
            match = _PINLU_TOKEN.match(token)
            if match is None:
                continue
            reading = match.group(1).strip()
            freq = int(match.group(2))
            plain = _kmandarin_to_plain(reading.lower())
            if not plain:
                continue
            # kHanyuPinlu covers traditional code points too; a
            # simplified target only emits the simplified glyph itself.
            if simplify is not None and simplify(surface) != surface:
                continue
            store.upsert(
                Lemma(
                    surface=surface,
                    pinyin_plain=plain,
                    pinyin_toned=reading if _has_tone_mark(reading) else None,
                    weight=max(1, freq),
                    status="auto",
                    domain_freq={"hanyu_pinlu": freq},
                    flags=["hanyu_pinlu"],
                    sources=[SourceRef("unihan", "unicode", source)],
                )
            )
            count += 1
    return count


def _kmandarin_row(line: str) -> tuple[str | None, list[str]]:
    match = _LINE.match(line)
    if match is None:
        return None, []
    surface = chr(int(match.group(1), 16))
    readings = [item.strip().lower() for item in match.group(2).split() if item.strip()]
    return surface, readings


def _pinlu_row(line: str) -> tuple[str | None, list[str]]:
    match = _PINLU_LINE.match(line)
    if match is None:
        return None, []
    surface = chr(int(match.group(1), 16))
    tokens = [item.strip() for item in match.group(2).split() if item.strip()]
    return surface, tokens


def _has_tone_mark(text: str) -> bool:
    return any(ch in text for ch in "āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ")


def _kmandarin_to_plain(reading: str) -> str:
    table = str.maketrans(
        {
            "ā": "a",
            "á": "a",
            "ǎ": "a",
            "à": "a",
            "ē": "e",
            "é": "e",
            "ě": "e",
            "è": "e",
            "ī": "i",
            "í": "i",
            "ǐ": "i",
            "ì": "i",
            "ō": "o",
            "ó": "o",
            "ǒ": "o",
            "ò": "o",
            "ū": "u",
            "ú": "u",
            "ǔ": "u",
            "ù": "u",
            "ǖ": "v",
            "ǘ": "v",
            "ǚ": "v",
            "ǜ": "v",
            "ü": "v",
        }
    )
    return reading.translate(table)
