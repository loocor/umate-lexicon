"""Post-resolve store shaping: LLM triage, notability, reading fixes,
THUOCL rank calibration, and curated ranks.

Runs after resolve_store (which writes the rank column) and before
emit, so every layer/pack decision sees the final status, flags, and
rank values. Each step is deterministic given its static input files
under data/eval/ and data/voimate/, so a full pipeline rebuild
reproduces the hand-applied store state without re-running any LLM.
"""

from __future__ import annotations

from umate_lexicon.store import LemmaStore
from umate_lexicon.postprocess.llm_triage import apply_llm_triage
from umate_lexicon.postprocess.wiki_notability import apply_wiki_notability
from umate_lexicon.postprocess.reading_fix import apply_reading_fix
from umate_lexicon.postprocess.thuocl_calibration import calibrate_thuocl_rank
from umate_lexicon.postprocess.rank_curation import apply_rank_curation


def run_postprocess(store: LemmaStore) -> dict[str, int]:
    stats: dict[str, int] = {}
    with store.deferred_commit():
        stats.update(apply_llm_triage(store))
        stats.update(apply_wiki_notability(store))
        stats.update(apply_reading_fix(store))
        stats.update(calibrate_thuocl_rank(store))
        stats.update(apply_rank_curation(store))
    return stats
