from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from dataclasses import dataclass

from umate_lexicon.lemma import Lemma, SourceRef


@dataclass(frozen=True)
class WikiPage:
    page_id: int
    namespace: int
    title: str
    is_redirect: bool


@dataclass(frozen=True)
class WikiLinkTarget:
    lt_id: int
    namespace: int
    title: str

SCHEMA = """
CREATE TABLE IF NOT EXISTS lemmas (
    surface TEXT NOT NULL,
    pinyin_plain TEXT NOT NULL,
    pinyin_toned TEXT,
    weight INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    script TEXT NOT NULL DEFAULT 'hans',
    categories TEXT NOT NULL DEFAULT '[]',
    flags TEXT NOT NULL DEFAULT '[]',
    entity_type TEXT,
    domain_freq TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (surface, pinyin_plain)
);
CREATE TABLE IF NOT EXISTS lemma_sources (
    surface TEXT NOT NULL,
    pinyin_plain TEXT NOT NULL,
    source_id TEXT NOT NULL,
    license TEXT NOT NULL,
    locator TEXT NOT NULL,
    PRIMARY KEY (surface, pinyin_plain, source_id)
);
CREATE TABLE IF NOT EXISTS wiki_pages (
    page_id INTEGER PRIMARY KEY,
    namespace INTEGER NOT NULL,
    title TEXT NOT NULL,
    is_redirect INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS wiki_pages_title ON wiki_pages(title);
CREATE TABLE IF NOT EXISTS wiki_linktargets (
    lt_id INTEGER PRIMARY KEY,
    namespace INTEGER NOT NULL,
    title TEXT NOT NULL
);
"""


class LemmaStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._autocommit = True

    def close(self) -> None:
        self._conn.close()

    def save(self, lemma: Lemma) -> None:
        """Write `lemma` as-is. Use for enrich/verify. Ingest should call upsert."""
        self._write(lemma)

    def upsert(self, lemma: Lemma) -> None:
        existing = self.get(lemma.surface, lemma.pinyin_plain)
        merged = existing.merge(lemma) if existing else lemma
        self._write(merged)

    def _write(self, merged: Lemma) -> None:
        self._conn.execute(
            """
            INSERT INTO lemmas (
                surface, pinyin_plain, pinyin_toned, weight, status, script,
                categories, flags, entity_type, domain_freq
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(surface, pinyin_plain) DO UPDATE SET
                pinyin_toned = excluded.pinyin_toned,
                weight = excluded.weight,
                status = excluded.status,
                script = excluded.script,
                categories = excluded.categories,
                flags = excluded.flags,
                entity_type = excluded.entity_type,
                domain_freq = excluded.domain_freq
            """,
            (
                merged.surface,
                merged.pinyin_plain,
                merged.pinyin_toned,
                merged.weight,
                merged.status,
                merged.script,
                json.dumps(merged.categories, ensure_ascii=False),
                json.dumps(merged.flags, ensure_ascii=False),
                merged.entity_type,
                json.dumps(merged.domain_freq, ensure_ascii=False),
            ),
        )
        for ref in merged.sources:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO lemma_sources (
                    surface, pinyin_plain, source_id, license, locator
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (merged.surface, merged.pinyin_plain, ref.source_id, ref.license, ref.locator),
            )
        if self._autocommit:
            self._conn.commit()

    @contextmanager
    def deferred_commit(self) -> Iterator[None]:
        previous = self._autocommit
        self._autocommit = False
        try:
            yield
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        finally:
            self._autocommit = previous

    def get(self, surface: str, pinyin_plain: str) -> Lemma | None:
        row = self._conn.execute(
            "SELECT * FROM lemmas WHERE surface = ? AND pinyin_plain = ?",
            (surface, pinyin_plain),
        ).fetchone()
        if row is None:
            return None
        return self._lemma_from_row(row)

    def readings_for(self, surface: str) -> list[Lemma]:
        rows = self._conn.execute(
            "SELECT * FROM lemmas WHERE surface = ?",
            (surface,),
        ).fetchall()
        return [self._lemma_from_row(row) for row in rows]

    def char_plain(self, char: str) -> list[str]:
        return [lemma.pinyin_plain for lemma in self.readings_for(char) if len(char) == 1]

    def all_lemmas(self) -> list[Lemma]:
        sources = self._sources_by_key()
        rows = self._conn.execute("SELECT * FROM lemmas ORDER BY surface, pinyin_plain").fetchall()
        return [self._lemma_from_row(row, sources.get((row["surface"], row["pinyin_plain"]), [])) for row in rows]

    def _sources_by_key(self) -> dict[tuple[str, str], list[SourceRef]]:
        mapping: dict[tuple[str, str], list[SourceRef]] = {}
        rows = self._conn.execute(
            "SELECT surface, pinyin_plain, source_id, license, locator FROM lemma_sources"
        ).fetchall()
        for item in rows:
            key = (item["surface"], item["pinyin_plain"])
            mapping.setdefault(key, []).append(
                SourceRef(source_id=item["source_id"], license=item["license"], locator=item["locator"])
            )
        return mapping

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM lemmas").fetchone()
        return int(row["n"])

    def surfaces(self) -> set[str]:
        rows = self._conn.execute("SELECT DISTINCT surface FROM lemmas").fetchall()
        return {row[0] for row in rows}

    def iter_lemmas(self) -> Iterator[Lemma]:
        sources = self._sources_by_key()
        rows = self._conn.execute("SELECT * FROM lemmas")
        for row in rows:
            yield self._lemma_from_row(row, sources.get((row["surface"], row["pinyin_plain"]), []))

    def iter_wiki_only_guessed(self) -> Iterator[Lemma]:
        rows = self._conn.execute(
            """
            SELECT * FROM lemmas l
            WHERE l.entity_type IN ('place', 'org')
              AND EXISTS (
                SELECT 1 FROM lemma_sources s
                WHERE s.surface = l.surface
                  AND s.pinyin_plain = l.pinyin_plain
                  AND s.source_id = 'wiki'
              )
              AND NOT EXISTS (
                SELECT 1 FROM lemma_sources s
                WHERE s.surface = l.surface
                  AND s.pinyin_plain = l.pinyin_plain
                  AND s.source_id != 'wiki'
              )
            """
        )
        for row in rows:
            yield self._lemma_from_row(row)

    def iter_flagged(self, flag: str) -> Iterator[Lemma]:
        rows = self._conn.execute(
            "SELECT * FROM lemmas WHERE flags LIKE ?",
            (f"%{flag}%",),
        )
        for row in rows:
            lemma = self._lemma_from_row(row)
            if flag in lemma.flags:
                yield lemma

    def reset_wiki_pages(self) -> None:
        self._conn.execute("DELETE FROM wiki_pages")
        if self._autocommit:
            self._conn.commit()

    def add_wiki_pages(self, rows: list[tuple[int, int, str, int]]) -> None:
        self._conn.executemany(
            """
            INSERT OR REPLACE INTO wiki_pages (page_id, namespace, title, is_redirect)
            VALUES (?, ?, ?, ?)
            """,
            rows,
        )
        if self._autocommit:
            self._conn.commit()

    def get_wiki_page(self, page_id: int) -> WikiPage | None:
        row = self._conn.execute(
            "SELECT page_id, namespace, title, is_redirect FROM wiki_pages WHERE page_id = ?",
            (page_id,),
        ).fetchone()
        if row is None:
            return None
        return WikiPage(
            page_id=int(row["page_id"]),
            namespace=int(row["namespace"]),
            title=row["title"],
            is_redirect=bool(row["is_redirect"]),
        )

    def reset_wiki_linktargets(self) -> None:
        self._conn.execute("DELETE FROM wiki_linktargets")
        if self._autocommit:
            self._conn.commit()

    def add_wiki_linktargets(self, rows: list[tuple[int, int, str]]) -> None:
        self._conn.executemany(
            """
            INSERT OR REPLACE INTO wiki_linktargets (lt_id, namespace, title)
            VALUES (?, ?, ?)
            """,
            rows,
        )
        if self._autocommit:
            self._conn.commit()

    def get_wiki_linktarget(self, lt_id: int) -> WikiLinkTarget | None:
        row = self._conn.execute(
            "SELECT lt_id, namespace, title FROM wiki_linktargets WHERE lt_id = ?",
            (lt_id,),
        ).fetchone()
        if row is None:
            return None
        return WikiLinkTarget(
            lt_id=int(row["lt_id"]),
            namespace=int(row["namespace"]),
            title=row["title"],
        )

    def _lemma_from_row(self, row: sqlite3.Row, sources: list[SourceRef] | None = None) -> Lemma:
        if sources is None:
            sources = [
                SourceRef(source_id=item["source_id"], license=item["license"], locator=item["locator"])
                for item in self._conn.execute(
                    "SELECT source_id, license, locator FROM lemma_sources WHERE surface = ? AND pinyin_plain = ?",
                    (row["surface"], row["pinyin_plain"]),
                )
            ]
        return Lemma(
            surface=row["surface"],
            pinyin_plain=row["pinyin_plain"],
            pinyin_toned=row["pinyin_toned"],
            weight=row["weight"],
            status=row["status"],
            script=row["script"],
            categories=json.loads(row["categories"]),
            flags=json.loads(row["flags"]),
            entity_type=row["entity_type"],
            domain_freq=json.loads(row["domain_freq"]),
            sources=sources,
        )
