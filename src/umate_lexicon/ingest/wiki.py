from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

from umate_lexicon.ingest.compose import compose_pinyin, is_han_only
from umate_lexicon.ingest.io import read_ingest_text
from umate_lexicon.ingest.mysql_dump import iter_mysql_table_rows
from umate_lexicon.layers import is_wiki_only
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.store import LemmaStore
from umate_lexicon.t2s import SimplifyFn

LICENSE_ID = "cc-by-sa-wikimedia"
NS_CATEGORY = 14
_SKIP_MARKERS = ("列表", "消歧义", "维基", "Wikipedia", "Category:")
_HAN = re.compile(r"[\u4e00-\u9fff]")
_GUESSED_TYPES = frozenset({"place", "org"})
_ENTITY_PRIORITY = {"person": 4, "work": 3, "org": 2, "place": 1}
_PERSON_ENDINGS = ("年出生", "年逝世", "人物")
_WORK_ENDINGS = ("电影", "电视剧", "小说", "歌曲", "专辑", "漫画")
_ORG_MARKERS = ("公司", "大学", "学校", "学院", "医院", "协会")
_PLACE_MARKERS = ("行政区划", "乡镇", "街道办事处", "聚居地")
_TYPED = frozenset({"person", "place", "org", "work"})


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
        store.upsert(
            Lemma(
                surface=surface,
                pinyin_plain=pinyin,
                weight=1,
                status="auto",
                domain_freq={"wiki": 1},
                sources=[SourceRef("wiki", LICENSE_ID, source)],
            )
        )
        seen.add(surface)
        count += 1
    return count


def ingest_wiki_page(
    store: LemmaStore,
    path: Path,
    locator: str | None = None,
    simplify: SimplifyFn | None = None,
) -> int:
    del locator
    clear_wiki_only_guessed_types(store)
    surfaces = store.surfaces()
    store.reset_wiki_pages()
    rejected = 0
    batch: list[tuple[int, int, str, int]] = []
    for row in iter_mysql_table_rows(path, "page"):
        namespace = int(row["page_namespace"] or 0)
        if namespace != 0:
            continue
        title = _surface_from_title(row["page_title"], simplify)
        if title is None or title not in surfaces:
            continue
        is_redirect = int(row["page_is_redirect"] or 0)
        batch.append((int(row["page_id"]), namespace, title, is_redirect))
        if len(batch) >= 5000:
            store.add_wiki_pages(batch)
            batch.clear()
        if is_redirect:
            rejected += _reject_wiki_only_redirect(store, title)
    if batch:
        store.add_wiki_pages(batch)
    return rejected


def ingest_wiki_linktarget(
    store: LemmaStore,
    path: Path,
    locator: str | None = None,
    simplify: SimplifyFn | None = None,
) -> int:
    del locator, simplify
    store.reset_wiki_linktargets()
    count = 0
    batch: list[tuple[int, int, str]] = []
    for row in iter_mysql_table_rows(path, "linktarget"):
        namespace = int(row["lt_namespace"] or 0)
        if namespace != NS_CATEGORY:
            continue
        title = str(row["lt_title"] or "")
        if not title:
            continue
        batch.append((int(row["lt_id"]), namespace, title))
        count += 1
        if len(batch) >= 5000:
            store.add_wiki_linktargets(batch)
            batch.clear()
    if batch:
        store.add_wiki_linktargets(batch)
    return count


def ingest_wiki_category(
    store: LemmaStore,
    path: Path,
    locator: str | None = None,
    simplify: SimplifyFn | None = None,
) -> int:
    del locator, simplify
    clear_wiki_category_overlay(store)
    count = 0
    for row in iter_mysql_table_rows(path, "categorylinks"):
        cl_type = row.get("cl_type")
        if cl_type not in {None, "page"}:
            continue
        category = _category_title(store, row)
        if category is None:
            continue
        entity = entity_from_category(category)
        if entity is None:
            continue
        page = store.get_wiki_page(int(row["cl_from"]))
        if page is None or page.is_redirect:
            continue
        count += _overlay_wiki_entity(store, page.title, entity)
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


def clear_wiki_only_guessed_types(store: LemmaStore) -> int:
    count = 0
    for lemma in store.iter_wiki_only_guessed():
        if "wiki_category" in lemma.flags:
            continue
        lemma.entity_type = None
        lemma.categories = [item for item in lemma.categories if item not in _GUESSED_TYPES]
        store.save(lemma)
        count += 1
    return count


def entity_from_category(title: str) -> str | None:
    text = title.replace("_", "")
    if any(marker in text for marker in _SKIP_MARKERS) or "作品" in text:
        return None
    if text.endswith(_PERSON_ENDINGS):
        return "person"
    if text.endswith(_WORK_ENDINGS):
        return "work"
    if any(marker in text for marker in _ORG_MARKERS):
        return "org"
    if any(marker in text for marker in _PLACE_MARKERS):
        return "place"
    return None


def clear_wiki_category_overlay(store: LemmaStore) -> int:
    count = 0
    for lemma in store.iter_flagged("wiki_category"):
        lemma.entity_type = None
        lemma.categories = [item for item in lemma.categories if item not in _TYPED]
        lemma.flags = [item for item in lemma.flags if item != "wiki_category"]
        store.save(lemma)
        count += 1
    return count


def _surface_from_title(raw: object, simplify: SimplifyFn | None) -> str | None:
    if raw is None:
        return None
    title = str(raw).replace("_", "")
    if not title:
        return None
    if simplify is not None:
        title = simplify(title)
    return title


def _reject_wiki_only_redirect(store: LemmaStore, title: str) -> int:
    count = 0
    for lemma in store.readings_for(title):
        if lemma.status == "rejected" or not is_wiki_only(lemma):
            continue
        flags = list(lemma.flags)
        if "wiki_redirect" not in flags:
            flags.append("wiki_redirect")
        lemma.status = "rejected"
        lemma.flags = flags
        store.save(lemma)
        count += 1
    return count


def _category_title(store: LemmaStore, row: dict[str, object]) -> str | None:
    if "cl_to" in row and row["cl_to"] not in {None, ""}:
        return str(row["cl_to"])
    target_id = row.get("cl_target_id")
    if target_id is None:
        return None
    target = store.get_wiki_linktarget(int(target_id))
    if target is None or target.namespace != NS_CATEGORY:
        return None
    return target.title


def _overlay_wiki_entity(store: LemmaStore, title: str, entity: str) -> int:
    count = 0
    incoming = _ENTITY_PRIORITY[entity]
    for lemma in store.readings_for(title):
        if lemma.status in {"rejected", "gold"} or not is_wiki_only(lemma):
            continue
        current = _ENTITY_PRIORITY.get(lemma.entity_type or "", 0)
        if current >= incoming:
            continue
        categories = list(lemma.categories)
        if entity not in categories:
            categories.append(entity)
        flags = list(lemma.flags)
        if "wiki_category" not in flags:
            flags.append("wiki_category")
        lemma.entity_type = entity
        lemma.categories = categories
        lemma.flags = flags
        store.save(lemma)
        count += 1
    return count
