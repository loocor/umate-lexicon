from pathlib import Path

from umate_lexicon.ingest.chars import ingest_chars
from umate_lexicon.ingest.compose import is_trusted_reading
from umate_lexicon.ingest.essay import ingest_essay
from umate_lexicon.ingest.luna import ingest_luna
from umate_lexicon.layers import assign_layer
from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore


def test_essay_overlays_trusted_reading_only(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    ingest_chars(store, data_dir() / "fixtures" / "chars.tsv")
    ingest_luna(store, data_dir() / "fixtures" / "luna.dict.yaml")
    ingest_essay(store, data_dir() / "fixtures" / "essay.txt")
    wo = store.get("我", "wo")
    leftover = store.get("我", "e")
    assert wo is not None
    assert wo.domain_freq.get("essay") == 100
    assert leftover is not None
    assert "essay" not in leftover.domain_freq
    assert is_trusted_reading(wo)
    assert not is_trusted_reading(leftover)
    store.close()
