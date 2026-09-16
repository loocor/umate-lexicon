from __future__ import annotations

from pathlib import Path

from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore


def apply_overrides(store: LemmaStore, path: Path | None = None) -> int:
    target = path or data_dir() / "gold" / "layer-overrides.tsv"
    if not target.is_file():
        return 0
    count = 0
    for raw in target.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if not parts or not parts[0].strip():
            continue
        surface = parts[0].strip()
        entity_raw = parts[1].strip() if len(parts) > 1 else ""
        cats_raw = parts[2].strip() if len(parts) > 2 else ""
        lemmas = store.readings_for(surface)
        if not lemmas:
            continue
        for lemma in lemmas:
            if entity_raw == "-":
                lemma.entity_type = None
            elif entity_raw:
                lemma.entity_type = entity_raw
            if cats_raw == "-":
                lemma.categories = [item for item in lemma.categories if item not in {"place", "industry", "org", "brand"}]
            elif cats_raw:
                merged = list(lemma.categories)
                for item in cats_raw.split(","):
                    item = item.strip()
                    if item and item not in merged:
                        merged.append(item)
                lemma.categories = merged
            store.save(lemma)
            count += 1
    return count
