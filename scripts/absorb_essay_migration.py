#!/usr/bin/env python3
"""One-time essay absorption migration (2026-10-03, codex/essay-absorption).

Renames the already-absorbed rime-essay data in the canonical store
(domain `essay` -> `core`, source id `essay` -> `umate-core`, locator
re-stamped), then resolves `rank` + `policy_version` under policy v1
(status-quo column precedence). Word content and weights are unchanged;
this is a provenance rename plus a rank freeze.

Back up data/store/lemmas.sqlite before running. Idempotent on an
already-migrated store: the renames no-op and resolve re-stamps.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from umate_lexicon.paths import default_store_path
from umate_lexicon.resolve import resolve_store
from umate_lexicon.store import LemmaStore


def main() -> int:
    store = LemmaStore(default_store_path())
    conn = store._conn
    with store.deferred_commit():
        renamed_domains = 0
        for surface, pinyin, payload in conn.execute(
            'SELECT surface, pinyin_plain, domain_freq FROM lemmas WHERE domain_freq LIKE \'%"essay"%\''
        ).fetchall():
            data = json.loads(payload)
            if "essay" in data:
                data["core"] = data.pop("essay")
                conn.execute(
                    "UPDATE lemmas SET domain_freq = ? WHERE surface = ? AND pinyin_plain = ?",
                    (json.dumps(data, ensure_ascii=False), surface, pinyin),
                )
                renamed_domains += 1
        renamed_sources = conn.execute(
            "UPDATE lemma_sources SET source_id = 'umate-core' WHERE source_id = 'essay'"
        ).rowcount
        conn.execute(
            "UPDATE lemma_sources SET locator = 'absorbed:absorbed-core.tsv' "
            "WHERE source_id = 'umate-core' AND locator LIKE 'essay:%'"
        )
    stats = resolve_store(store)
    residue = conn.execute(
        'SELECT COUNT(*) FROM lemmas WHERE domain_freq LIKE \'%"essay"%\''
    ).fetchone()[0]
    nulls = conn.execute("SELECT COUNT(*) FROM lemmas WHERE rank IS NULL").fetchone()[0]
    store.close()
    print(
        f"absorbed migration: domains_renamed={renamed_domains} "
        f"sources_renamed={renamed_sources} resolved={stats['resolved']} "
        f"policy={stats['policy_version']} essay_residue={residue} rank_nulls={nulls}"
    )
    if residue or nulls:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
