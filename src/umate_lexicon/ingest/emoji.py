from __future__ import annotations

from pathlib import Path

from umate_lexicon.ingest.compose import compose_pinyin, is_han_only
from umate_lexicon.ingest.io import read_ingest_text
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore

LICENSE_ID = "lgpl-rime-emoji"


def emoji_opencc_sidecar(store: LemmaStore) -> Path:
    return store.path.with_name("emoji_word.txt")


def ingest_emoji(store: LemmaStore, path: Path, locator: str | None = None) -> int:
    text = read_ingest_text(path)
    source = locator or f"emoji:{path.name}"
    mappings: list[tuple[str, list[str]]] = []
    count = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parsed = parse_emoji_word_line(line)
        if parsed is None:
            continue
        trigger, emojis = parsed
        mappings.append((trigger, emojis))
        pinyin = compose_pinyin(store, trigger) if is_han_only(trigger) else None
        if pinyin is None:
            continue
        for emoji in emojis:
            store.upsert(
                Lemma(
                    surface=emoji,
                    pinyin_plain=pinyin,
                    weight=1,
                    status="auto",
                    categories=["emoji"],
                    flags=["emoji"],
                    entity_type="emoji",
                    domain_freq={"emoji": 1},
                    sources=[SourceRef("emoji", LICENSE_ID, f"emoji:{trigger}")],
                )
            )
            count += 1
    _write_opencc_sidecar(store, mappings, source)
    return count


def parse_emoji_word_line(line: str) -> tuple[str, list[str]] | None:
    parts = line.split("\t")
    if len(parts) < 2:
        return None
    trigger = parts[0].strip()
    values = parts[1].split()
    if not trigger:
        return None
    emojis = [token for token in values if token != trigger]
    if not emojis:
        return None
    return trigger, emojis


def _write_opencc_sidecar(
    store: LemmaStore,
    mappings: list[tuple[str, list[str]]],
    source: str,
) -> None:
    del source
    lines = [f"{trigger}\t{trigger} {' '.join(emojis)}" for trigger, emojis in mappings]
    emoji_opencc_sidecar(store).write_text("\n".join(lines) + "\n", encoding="utf-8")
