from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

from umate_lexicon.ingest.compose import compose_pinyin, is_han_only
from umate_lexicon.ingest.io import read_ingest_text
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore
from umate_lexicon.t2s import SimplifyFn

LICENSE_ID = "cc-by-sa-wikimedia"
_SKIP_MARKERS = ("列表", "消歧义", "维基", "Wikipedia", "Category:")
_PLACE_SUFFIX = re.compile(r"(市|县|区|镇|乡|村|州|省|盟|旗)$")
_ORG_SUFFIX = re.compile(r"(公司|集团|大学|学院|医院|银行|协会|委员会)$")
_HAN = re.compile(r"[\u4e00-\u9fff]")


def ingest_wiki(
    store: LemmaStore,
    path: Path,
    locator: str | None = None,
    simplify: SimplifyFn | None = None,
) -> int:
    text = read_ingest_text(path)
    source = locator or f"wiki:{path.name}"
    seen = {lemma.surface for lemma in store.all_lemmas()}
    count = 0
    for raw in text.splitlines():
        surface = normalize_wiki_title(raw, simplify=simplify)
        if surface is None or surface in seen:
            continue
        pinyin = compose_pinyin(store, surface)
        if pinyin is None:
            continue
        entity, categories = _entity_for(surface)
        store.upsert(
            Lemma(
                surface=surface,
                pinyin_plain=pinyin,
                weight=1,
                status="auto",
                categories=categories,
                entity_type=entity,
                domain_freq={"wiki": 1},
                sources=[SourceRef("wiki", LICENSE_ID, source)],
            )
        )
        seen.add(surface)
        count += 1
    return count


def normalize_wiki_title(raw: str, simplify: SimplifyFn | None = None) -> str | None:
    line = unquote(raw.strip())
    if not line or line.startswith("#"):
        return None
    if "\t" in line:
        line = line.split("\t")[-1].strip()
    if any(marker in line for marker in _SKIP_MARKERS):
        return None
    if "(" in line or "（" in line:
        return None
    line = line.replace("_", "")
    if not line:
        return None
    if simplify is not None:
        line = simplify(line)
    if not is_han_only(line):
        return None
    n = len(_HAN.findall(line))
    if n < 2 or n > 8:
        return None
    return line


def _entity_for(surface: str) -> tuple[str | None, list[str]]:
    if _PLACE_SUFFIX.search(surface) and _PLACE_SUFFIX.search(surface).start() > 0:
        return "place", ["place"]
    if _ORG_SUFFIX.search(surface) and _ORG_SUFFIX.search(surface).start() > 0:
        return "org", ["org"]
    return None, []
