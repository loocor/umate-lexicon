"""Apply archived LLM reading verdicts for untrusted_reading rows.

incorrect verdicts (pre-validated against per-char known readings)
update pinyin_plain; primary-key clashes merge into the existing row
(flags unioned, domain_freq max-merged, old row removed). correct and
variant verdicts keep the untrusted_reading flag; blocked rows stay
untouched for the separate Unihan verification pass.
"""

from __future__ import annotations

import json
from pathlib import Path

from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore


def _load(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("s"):
            out[rec["s"]] = rec
    return out


def apply_reading_fix(store: LemmaStore) -> dict[str, int]:
    conn = store._conn
    recs = _load(data_dir() / "eval" / "llm-verify-reading.jsonl")
    stats = {"reading_fixed": 0, "reading_merged": 0}

    for surface, rec in recs.items():
        if rec.get("blocked") or rec.get("v") != "incorrect":
            continue
        row = conn.execute(
            "SELECT status, flags, pinyin_plain, weight, domain_freq FROM lemmas WHERE surface=?",
            (surface,),
        ).fetchone()
        if row is None or "untrusted_reading" not in (row["flags"] or ""):
            continue
        corrected = (rec.get("c") or "").strip().lower()
        if not corrected:
            continue
        flags = json.loads(row["flags"] or "[]")
        flags = [f for f in flags if f != "untrusted_reading"]
        if "llm_reading_fix" not in flags:
            flags.append("llm_reading_fix")
        flags_json = json.dumps(flags, ensure_ascii=False)

        if corrected == row["pinyin_plain"]:
            conn.execute(
                "UPDATE lemmas SET flags=? WHERE surface=? AND pinyin_plain=?",
                (flags_json, surface, row["pinyin_plain"]),
            )
            stats["reading_fixed"] += 1
            continue
        clash = conn.execute(
            "SELECT flags, domain_freq FROM lemmas WHERE surface=? AND pinyin_plain=?",
            (surface, corrected),
        ).fetchone()
        if clash is not None:
            tgt_flags = json.loads(clash["flags"] or "[]")
            merged = sorted(set(tgt_flags) | (set(flags) - {"llm_reading_fix"}))
            merged.append("llm_reading_fix")
            old_df = json.loads(row["domain_freq"] or "{}")
            tgt_df = json.loads(clash["domain_freq"] or "{}")
            for key, value in old_df.items():
                tgt_df[key] = max(tgt_df.get(key, 0), value)
            conn.execute(
                "UPDATE lemmas SET flags=?, domain_freq=? WHERE surface=? AND pinyin_plain=?",
                (json.dumps(merged, ensure_ascii=False), json.dumps(tgt_df, ensure_ascii=False),
                 surface, corrected),
            )
            conn.execute(
                "DELETE FROM lemmas WHERE surface=? AND pinyin_plain=?",
                (surface, row["pinyin_plain"]),
            )
            stats["reading_merged"] += 1
            continue
        conn.execute(
            "UPDATE lemmas SET pinyin_plain=?, pinyin_toned=NULL, flags=? WHERE surface=? AND pinyin_plain=?",
            (corrected, flags_json, surface, row["pinyin_plain"]),
        )
        stats["reading_fixed"] += 1

    return stats
