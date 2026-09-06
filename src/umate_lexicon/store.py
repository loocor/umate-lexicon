from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from umate_lexicon.lemma import Lemma, SourceRef

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
"""


class LemmaStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)

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
        self._conn.commit()

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
        rows = self._conn.execute("SELECT * FROM lemmas ORDER BY surface, pinyin_plain").fetchall()
        return [self._lemma_from_row(row) for row in rows]

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM lemmas").fetchone()
        return int(row["n"])

    def _lemma_from_row(self, row: sqlite3.Row) -> Lemma:
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
