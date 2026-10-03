"""Apply curated absolute ranks from data/voimate/rank-curation.tsv.

Format: surface<TAB>pinyin_plain<TAB>rank<TAB>reason. For entries the
source corpora undervalue but product verification depends on (e.g.
the biangbiang noodle signature phrase). Runs last so curated values
win over calibration.
"""

from __future__ import annotations

from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore


def apply_rank_curation(store: LemmaStore) -> dict[str, int]:
    conn = store._conn
    path = data_dir() / "voimate" / "rank-curation.tsv"
    stats = {"rank_curated": 0}
    if not path.is_file():
        return stats
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        surface, pinyin, rank = parts[0].strip(), parts[1].strip(), int(parts[2])
        conn.execute(
            "UPDATE lemmas SET rank=?, weight=? WHERE surface=? AND pinyin_plain=?",
            (rank, rank, surface, pinyin),
        )
        stats["rank_curated"] += 1
    return stats
