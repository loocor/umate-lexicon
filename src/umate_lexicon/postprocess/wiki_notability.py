"""Wiki notability filter for person/place/org rows.

Auto tier: wiki-only rows below the page-weight hot floor (450) are
rejected with the wiki_low_notable flag. Review tier: work rows and
notable person/place/org rows are promoted to auto; the rest rejected.
Multi-source rows (any non-wiki measured domain) are never touched:
tencent/core coverage outranks the wiki page heuristic.
"""

from __future__ import annotations

import json

from umate_lexicon.layers import _load_wiki_page_weights
from umate_lexicon.store import LemmaStore

HOT_FLOOR = 450


def apply_wiki_notability(store: LemmaStore) -> dict[str, int]:
    conn = store._conn
    weights = _load_wiki_page_weights()
    stats = {"auto_rejected_low_notable": 0, "review_promoted": 0,
             "review_rejected_low_notable": 0}

    # Auto tier.
    rows = conn.execute(
        """
        SELECT surface, flags FROM lemmas
        WHERE flags='["wiki_category"]' AND status='auto'
        AND entity_type IN ('person','place','org')
        AND domain_freq='{"wiki": 1}'
        """
    ).fetchall()
    for row in rows:
        if (weights.get(row["surface"]) or 0) >= HOT_FLOOR:
            continue
        flags = json.loads(row["flags"] or "[]")
        if "wiki_low_notable" not in flags:
            flags.append("wiki_low_notable")
        conn.execute(
            "UPDATE lemmas SET status='rejected', flags=? WHERE surface=? AND status='auto'",
            (json.dumps(flags, ensure_ascii=False), row["surface"]),
        )
        stats["auto_rejected_low_notable"] += 1

    # Review tier.
    rows = conn.execute(
        """
        SELECT surface, entity_type, flags FROM lemmas
        WHERE flags LIKE '%wiki_category%' AND status='review'
        """
    ).fetchall()
    for row in rows:
        etype = row["entity_type"]
        if etype not in ("person", "place", "org", "work"):
            continue
        notable = etype == "work" or (weights.get(row["surface"]) or 0) >= HOT_FLOOR
        if notable:
            conn.execute("UPDATE lemmas SET status='auto' WHERE surface=?", (row["surface"],))
            stats["review_promoted"] += 1
        else:
            flags = json.loads(row["flags"] or "[]")
            if "wiki_low_notable" not in flags:
                flags.append("wiki_low_notable")
            conn.execute(
                "UPDATE lemmas SET status='rejected', flags=? WHERE surface=?",
                (json.dumps(flags, ensure_ascii=False), row["surface"]),
            )
            stats["review_rejected_low_notable"] += 1

    return stats
