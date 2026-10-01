"""Regression tests for the emit-layer T2S conversion.

Verify that common Simplified Chinese words map correctly from Traditional,
and that the emit-layer OpenCC loader is properly wired.
"""

from __future__ import annotations

import pytest


class TestOpenCCT2S:
    """Verify the OpenCC converter used in emit_rime maps Traditional to Simplified."""

    @pytest.fixture
    def opencc_t2s(self):
        try:
            from opencc import OpenCC
        except ImportError:
            pytest.skip("opencc-python-reimplemented not installed")
        return OpenCC("t2s").convert

    def test_t2s_converts_common_traditional_chars(self, opencc_t2s) -> None:
        cases = {
            "乾": "干",
            "兇": "凶",
            "週": "周",
            "淨": "净",
            "餘": "余",
            "麵": "面",
            "裡": "里",
            "乾淨": "干净",
            "週期": "周期",
            "一週": "一周",
            "兇手": "凶手",
        }
        for trad, simp in cases.items():
            assert opencc_t2s(trad) == simp, f"{trad} -> {opencc_t2s(trad)}, expected {simp}"

    def test_t2s_preserves_already_simplified(self, opencc_t2s) -> None:
        simplified = ["干净", "周期", "一周", "凶手", "上周", "玻璃", "猪肝", "洗碗机"]
        for s in simplified:
            assert opencc_t2s(s) == s, f"should be idempotent: {s}"

    def test_t2s_preserves_proper_nouns_with_qian(self, opencc_t2s) -> None:
        assert opencc_t2s("乾隆") == "乾隆"
        assert opencc_t2s("乾坤") == "乾坤"


class TestEmitT2SIntegration:
    def test_opencc_loader_returns_callable(self) -> None:
        from umate_lexicon.emit.rime import _load_opencc_t2s
        fn = _load_opencc_t2s()
        assert callable(fn)
        try:
            from opencc import OpenCC
            assert fn("乾淨") == "干净"
        except ImportError:
            assert fn("乾淨") == "乾淨"
