from pathlib import Path

from umate_lexicon.enrich.category import classify
from umate_lexicon.ingest.chars import ingest_chars
from umate_lexicon.ingest.wiki import (
    entity_from_category,
    ingest_wiki,
    ingest_wiki_category,
    ingest_wiki_linktarget,
    ingest_wiki_page,
    normalize_wiki_title,
)
from umate_lexicon.layers import assign_layer
from umate_lexicon.lemma import Lemma, SourceRef
from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore


def test_normalize_skips_lists_and_keeps_han() -> None:
    assert normalize_wiki_title("开心") == "开心"
    assert normalize_wiki_title("List_of_planets") is None
    assert normalize_wiki_title("北京_(消歧义)") is None


def test_wiki_adds_composable_missing_title(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    ingest_chars(store, data_dir() / "fixtures" / "chars.tsv")
    count = ingest_wiki(store, data_dir() / "fixtures" / "wiki-titles.txt")
    assert count >= 1
    happy = store.get("开心", "kai xin")
    assert happy is not None
    company = store.get("美团公司", "mei tuan gong si")
    assert company is not None
    assert company.entity_type is None
    store.close()


def test_wiki_only_redirect_is_rejected(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    store.upsert(
        Lemma(
            surface="测试别名",
            pinyin_plain="ce shi bie ming",
            status="auto",
            sources=[SourceRef("wiki", "cc-by-sa-wikimedia", "wiki")],
        )
    )
    store.upsert(
        Lemma(
            surface="文件备份",
            pinyin_plain="wen jian bei fen",
            status="auto",
            sources=[
                SourceRef("thuocl", "mit-thuocl", "thuocl"),
                SourceRef("wiki", "cc-by-sa-wikimedia", "wiki"),
            ],
        )
    )
    rejected = ingest_wiki_page(store, data_dir() / "fixtures" / "wiki-page.sql")
    assert rejected == 1
    alias = store.get("测试别名", "ce shi bie ming")
    assert alias is not None
    assert alias.status == "rejected"
    assert "wiki_redirect" in alias.flags
    assert assign_layer(alias) is None
    mixed = store.get("文件备份", "wen jian bei fen")
    assert mixed is not None
    assert mixed.status == "auto"
    store.close()


def test_wiki_category_types_are_not_emitted(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    store.upsert(
        Lemma(
            surface="美团公司",
            pinyin_plain="mei tuan gong si",
            status="auto",
            entity_type="org",
            categories=["org"],
            sources=[SourceRef("wiki", "cc-by-sa-wikimedia", "wiki")],
        )
    )
    store.upsert(
        Lemma(
            surface="开心",
            pinyin_plain="kai xin",
            status="auto",
            sources=[SourceRef("wiki", "cc-by-sa-wikimedia", "wiki")],
        )
    )
    ingest_wiki_page(store, data_dir() / "fixtures" / "wiki-page.sql")
    ingest_wiki_linktarget(store, data_dir() / "fixtures" / "wiki-linktarget.sql")
    typed = ingest_wiki_category(store, data_dir() / "fixtures" / "wiki-categorylinks.sql")
    assert typed >= 1
    company = store.get("美团公司", "mei tuan gong si")
    assert company is not None
    assert company.entity_type == "org"
    assert "wiki_category" in company.flags
    # 2026-09-19: wiki-only typed entries ride the corresponding pack
    assert assign_layer(company) == "orgs"
    happy = store.get("开心", "kai xin")
    assert happy is not None
    assert happy.entity_type == "person"
    assert assign_layer(happy) == "names"
    store.close()


def test_cl_to_category_dump_without_linktarget(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    store.upsert(
        Lemma(
            surface="李白",
            pinyin_plain="li bai",
            status="auto",
            sources=[SourceRef("wiki", "cc-by-sa-wikimedia", "wiki")],
        )
    )
    store.add_wiki_pages([(9, 0, "李白", 0)])
    path = tmp_path / "categorylinks.sql"
    path.write_text(
        """
CREATE TABLE `categorylinks` (
  `cl_from` int,
  `cl_to` varbinary(255),
  `cl_type` enum('page','subcat','file')
);
INSERT INTO `categorylinks` VALUES (9,'2020年出生','page');
""",
        encoding="utf-8",
    )
    assert ingest_wiki_category(store, path) == 1
    lemma = store.get("李白", "li bai")
    assert lemma is not None
    assert lemma.entity_type == "person"
    # 2026-09-19: wiki-only typed lemmas ride the corresponding pack.
    assert assign_layer(lemma) == "names"
    store.close()


def test_classify_does_not_suffix_wiki_only() -> None:
    lemma = classify(
        Lemma(
            surface="一亩泉镇",
            pinyin_plain="yi mu quan zhen",
            status="auto",
            sources=[SourceRef("wiki", "cc-by-sa-wikimedia", "wiki")],
        )
    )
    assert lemma.entity_type is None
    assert "place" not in lemma.categories


def test_category_markers_are_conservative() -> None:
    assert entity_from_category("2020年出生") == "person"
    assert entity_from_category("中国公司") == "org"
    assert entity_from_category("河北省乡镇") == "place"
    assert entity_from_category("日本电影") == "work"
    assert entity_from_category("某某作品") is None
    assert entity_from_category("科") is None
