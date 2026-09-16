from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from umate_lexicon.ingest.io import read_ingest_text

_LINE = re.compile(r"^U\+([0-9A-F]+)\tkSimplifiedVariant\t(.+)$")
_CODE = re.compile(r"U\+([0-9A-F]+)")

SimplifyFn = Callable[[str], str]


def identity(surface: str) -> str:
    return surface


def load_unihan_simplified(path: Path) -> dict[str, str]:
    text = read_ingest_text(path)
    table: dict[str, str] = {}
    for raw in text.splitlines():
        match = _LINE.match(raw.strip())
        if match is None:
            continue
        traditional = chr(int(match.group(1), 16))
        variants = _CODE.findall(match.group(2))
        if not variants:
            continue
        simplified = chr(int(variants[0], 16))
        if traditional != simplified:
            table[traditional] = simplified
    return table


def make_simplifier(table: dict[str, str] | None) -> SimplifyFn:
    mapping = table or {}
    if not mapping:
        return identity

    def simplify(surface: str) -> str:
        return "".join(mapping.get(char, char) for char in surface)

    return simplify
