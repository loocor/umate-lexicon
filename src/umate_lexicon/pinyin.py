from __future__ import annotations

import re

_TONE_VOWELS = {
    "a": "āáǎàa",
    "e": "ēéěèe",
    "i": "īíǐìi",
    "o": "ōóǒòo",
    "u": "ūúǔùu",
    "ü": "ǖǘǚǜü",
    "v": "ǖǘǚǜv",
}

_NUMBERED = re.compile(r"^([a-z:üv]+)([1-5])$", re.IGNORECASE)
_SYLLABLE_SPLIT = re.compile(r"\s+")


def normalize_cedict_syllable(raw: str) -> str:
    text = raw.strip().lower().replace("u:", "v")
    return text


def numbered_to_plain(numbered: str) -> str:
    parts = [_strip_tone_number(normalize_cedict_syllable(part)) for part in _SYLLABLE_SPLIT.split(numbered.strip()) if part]
    return " ".join(parts)


def numbered_to_toned(numbered: str) -> str:
    parts = [_apply_tone_number(normalize_cedict_syllable(part)) for part in _SYLLABLE_SPLIT.split(numbered.strip()) if part]
    return " ".join(parts)


def _strip_tone_number(syllable: str) -> str:
    match = _NUMBERED.match(syllable)
    if not match:
        return syllable.rstrip("12345")
    body = match.group(1).replace("ü", "v")
    return body


def _apply_tone_number(syllable: str) -> str:
    match = _NUMBERED.match(syllable)
    if not match:
        return syllable
    body, tone_s = match.group(1), match.group(2)
    tone = int(tone_s)
    if tone == 5:
        return body.replace("v", "ü")
    return _mark_tone(body, tone)


def _mark_tone(body: str, tone: int) -> str:
    lower = body.replace("v", "ü")
    # Standard placement: a/e, then ou, else last vowel.
    if "a" in lower:
        return _replace_vowel(lower, "a", tone)
    if "e" in lower:
        return _replace_vowel(lower, "e", tone)
    if "ou" in lower:
        return _replace_vowel(lower, "o", tone)
    for index in range(len(lower) - 1, -1, -1):
        ch = lower[index]
        if ch in _TONE_VOWELS:
            return lower[:index] + _TONE_VOWELS[ch][tone - 1] + lower[index + 1 :]
    return lower


def _replace_vowel(body: str, vowel: str, tone: int) -> str:
    index = body.index(vowel)
    return body[:index] + _TONE_VOWELS[vowel][tone - 1] + body[index + 1 :]


def parse_cedict_pinyin_field(field: str) -> tuple[str, str]:
    """Return (plain, toned) from a CEDICT [ni3 hao3] body without brackets."""
    numbered = field.strip()
    return numbered_to_plain(numbered), numbered_to_toned(numbered)
