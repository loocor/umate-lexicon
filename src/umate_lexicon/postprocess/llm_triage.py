"""Apply archived LLM triage verdicts to the store.

Inputs (static script checkpoints under data/eval/):
- llm-classify-review.jsonl: verdicts for review-tier rows (rank>=500)
- llm-classify-tencent.jsonl + llm-classify-tencent-magpie.jsonl:
  tencent-only auto rows, 4-char via dual-model agreement, 2/3-char
  via magpie alone (mimo never covered those lengths)

Actions mirror the hand-applied round of 2026-10-03:
- review real-word    -> auto
- review fragment     -> rejected + llm_fragment
- review variant-dup  -> rejected + llm_variant_dup
- tencent fragment    -> rejected + llm_fragment (auto rows only)
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
        key = rec.get("w") or rec.get("s")
        if key:
            out[key] = rec
    return out


def apply_llm_triage(store: LemmaStore) -> dict[str, int]:
    conn = store._conn
    llm_dir = data_dir() / "eval"

    review = _load(llm_dir / "llm-classify-review.jsonl")
    mimo = _load(llm_dir / "llm-classify-tencent.jsonl")
    magpie = _load(llm_dir / "llm-classify-tencent-magpie.jsonl")

    stats = {"review_promoted": 0, "review_rejected_fragment": 0,
             "review_rejected_variant": 0, "tencent_rejected": 0}

    # Review tier: promote real-word, reject fragment/variant-dup.
    for surface, rec in review.items():
        verdict = rec.get("v")
        row = conn.execute(
            "SELECT status, flags FROM lemmas WHERE surface=?", (surface,)
        ).fetchone()
        if row is None or row["status"] != "review":
            continue
        flags = json.loads(row["flags"] or "[]")
        if verdict == "real-word":
            conn.execute("UPDATE lemmas SET status='auto' WHERE surface=?", (surface,))
            stats["review_promoted"] += 1
        elif verdict == "fragment":
            if "llm_fragment" not in flags:
                flags.append("llm_fragment")
            conn.execute(
                "UPDATE lemmas SET status='rejected', flags=? WHERE surface=?",
                (json.dumps(flags, ensure_ascii=False), surface),
            )
            stats["review_rejected_fragment"] += 1
        elif verdict == "variant-dup":
            if "llm_variant_dup" not in flags:
                flags.append("llm_variant_dup")
            conn.execute(
                "UPDATE lemmas SET status='rejected', flags=? WHERE surface=?",
                (json.dumps(flags, ensure_ascii=False), surface),
            )
            stats["review_rejected_variant"] += 1

    # Tencent tier: 4-char needs dual agreement; 2/3-char magpie alone.
    targets: list[str] = [
        w for w, r in mimo.items()
        if r.get("c") == "fragment" and len(w) == 4
        and w in magpie and magpie[w].get("c") == "fragment"
    ]
    targets += [
        w for w, r in magpie.items()
        if r.get("c") == "fragment" and len(w) in (2, 3)
    ]
    for surface in targets:
        row = conn.execute(
            "SELECT status, flags FROM lemmas WHERE surface=? AND LENGTH(surface) BETWEEN 2 AND 4",
            (surface,),
        ).fetchone()
        if row is None or row["status"] != "auto":
            continue
        flags = json.loads(row["flags"] or "[]")
        if "llm_fragment" not in flags:
            flags.append("llm_fragment")
        conn.execute(
            "UPDATE lemmas SET status='rejected', flags=? WHERE surface=? AND status='auto'",
            (json.dumps(flags, ensure_ascii=False), surface),
        )
        stats["tencent_rejected"] += 1

    return stats
