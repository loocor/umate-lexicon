"""Quick corpus regression: verify key Simplified Chinese words are TOP-1."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST = REPO_ROOT / "dist" / "rime"

MUST_BE_TOP1 = [
    ("干净", "gan jing"),
    ("上周", "shang zhou"),
    ("凶手", "xiong shou"),
    ("周期", "zhou qi"),
    ("一周", "yi zhou"),
    ("干脆", "gan cui"),
    ("干燥", "gan zao"),
    ("周围", "zhou wei"),
]

# These Traditional entries must NOT appear as TOP-1 after the T2S fix.
MUST_NOT_BE_TOP1 = [
    ("乾淨", "gan jing"),
    ("上週", "shang zhou"),
    ("兇手", "xiong shou"),
    ("週期", "zhou qi"),
    ("一週", "yi zhou"),
    ("乾脆", "gan cui"),
]


class TestCorpusTop1:
    @pytest.fixture
    def pinyin_map(self):
        if not DIST.exists():
            pytest.skip("dist/rime not present; run emit first")
        pm = defaultdict(list)
        for path in sorted(DIST.glob("umate_*.dict.yaml")):
            in_data = False
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip() == "...":
                    in_data = True
                    continue
                if not in_data or line.startswith("#"):
                    continue
                parts = line.strip().split("\t")
                if len(parts) >= 3:
                    pm[parts[1]].append((int(parts[2]), parts[0]))
        for key in pm:
            pm[key].sort(key=lambda x: -x[0])
        return dict(pm)

    @pytest.mark.parametrize(("surface", "pinyin"), MUST_BE_TOP1)
    def test_must_be_top1(self, pinyin_map, surface, pinyin):
        assert pinyin in pinyin_map, f"pinyin {pinyin} not found"
        candidates = pinyin_map[pinyin]
        assert candidates, f"no candidates for {pinyin}"
        top1 = candidates[0][1]
        assert top1 == surface, f"TOP-1 for {pinyin} is {top1}, expected {surface}"

    @pytest.mark.parametrize(("surface", "pinyin"), MUST_NOT_BE_TOP1)
    def test_traditional_not_top1(self, pinyin_map, surface, pinyin):
        if pinyin not in pinyin_map:
            return
        candidates = pinyin_map[pinyin]
        for _, s in candidates:
            if s == surface:
                pytest.fail(f"Traditional {surface} still present for {pinyin}")
