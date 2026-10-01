"""Round-report regression guards.

Threshold rails only: they fail when a rebuild silently worsens the
small-corpus eval numbers or the exported probe-case file, and they
never pin specific word lists.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
DIST = REPO_ROOT / "dist" / "rime"
CORPUS_DIR = REPO_ROOT / "data" / "eval" / "corpus"
ROUNDS_DIR = REPO_ROOT / "data" / "eval" / "rounds"
CASES_TSV = ROUNDS_DIR / "grammar-probe-cases.tsv"

sys.path.insert(0, str(SCRIPTS))

from eval_corpus import get_pinyin, parse_dict_yamls, segment_text  # noqa: E402


def _latest_metrics() -> dict:
    path = ROUNDS_DIR / "latest.json"
    if not path.is_file():
        pytest.skip("data/eval/rounds/latest.json missing")
    return json.loads(path.read_text(encoding="utf-8"))


def _subset_gaps(name: str) -> tuple[int, int, int]:
    """Coverage/ranking gaps (unique-word) and token count for one file."""
    pinyin_map, all_surfaces = parse_dict_yamls(DIST)
    text = (CORPUS_DIR / f"{name}.txt").read_text(encoding="utf-8")
    words = segment_text(text)
    cov = rank = 0
    for word in set(words):
        if word not in all_surfaces:
            cov += 1
            continue
        pinyin = get_pinyin(word)
        if not pinyin or pinyin not in pinyin_map:
            continue
        candidates = pinyin_map[pinyin]
        if candidates and candidates[0][1] != word:
            rank += 1
    return cov, rank, len(words)


class TestSmallCorpusGuard:
    def test_smallest_subset_gaps_do_not_regress(self) -> None:
        if not DIST.exists():
            pytest.skip("dist/rime not present; run emit first")
        latest = _latest_metrics()
        per_source = latest["metrics"] and latest.get("per_source") or {}
        candidates = [
            (v["words"], k) for k, v in per_source.items() if v.get("words")
        ]
        if not candidates:
            pytest.skip("latest.json has no per_source baseline")
        candidates.sort()
        name = candidates[0][1]
        base = per_source[name]
        cov, rank, unique = _subset_gaps(name)
        assert unique == base["words"], (
            f"{name} corpus changed ({base['words']} -> {unique} unique words); "
            "append new files instead of rewriting old ones"
        )
        assert cov <= max(base["coverage_gaps"] + 5, base["coverage_gaps"] * 2), (
            f"{name} coverage gaps regressed: {base['coverage_gaps']} -> {cov}"
        )
        assert rank <= max(base["ranking_gaps"] + 8, base["ranking_gaps"] * 2), (
            f"{name} ranking gaps regressed: {base['ranking_gaps']} -> {rank}"
        )


class TestProbeCaseFileStable:
    def test_cases_tsv_shape(self) -> None:
        if not CASES_TSV.is_file():
            pytest.skip("grammar-probe-cases.tsv not exported yet")
        labels: set[str] = set()
        rows = 0
        for line in CASES_TSV.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split("\t")
            assert len(parts) == 4, f"expected 4 TSV columns, got {len(parts)}"
            pinyin, expected, label, soft = parts
            assert pinyin and expected and label
            assert soft in {"0", "1"}
            assert label not in labels, f"duplicate label {label}"
            labels.add(label)
            rows += 1
        assert rows >= 200, f"probe case set shrunk to {rows} rows"


CTX_TSV = ROUNDS_DIR / "grammar-probe-ctx-cases.tsv"


class TestCtxCaseFile:
    def test_ctx_cases_shape_and_wikinews_domain(self) -> None:
        if not CTX_TSV.is_file():
            pytest.skip("grammar-probe-ctx-cases.tsv not exported yet")
        labels: set[str] = set()
        rows = 0
        domains: set[str] = set()
        for line in CTX_TSV.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split("\t")
            assert len(parts) >= 6, f"expected 6+ TSV columns, got {len(parts)}"
            prefix, probe, expected, label, soft, domain = parts[:6]
            assert prefix and probe and expected and label
            assert soft in {"0", "1"}
            assert domain == "wikinews"
            assert label not in labels, f"duplicate label {label}"
            labels.add(label)
            domains.add(domain)
            rows += 1
        assert rows >= 30, f"wikinews ctx case set shrunk to {rows} rows"
        assert domains == {"wikinews"}
