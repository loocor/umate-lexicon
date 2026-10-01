#!/usr/bin/env python3
"""Run one corpus evaluation round, record the delta, export probe cases.

One command per round: measure coverage/ranking gaps of data/eval/corpus
against dist/rime, compare with the previous snapshot in
data/eval/rounds/latest.json, write a Markdown report under
data/eval/rounds/, refresh latest.json, and export homophone competitor
pairs as candidate octagram grammar-probe cases (TSV for the VoiMate
umate_grammar_probe A/B suite).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_corpus import get_pinyin, parse_dict_yamls, segment_text  # noqa: E402

METRIC_ROWS = [
    ("coverage_gaps", "覆盖缺口（unique）"),
    ("ranking_gaps", "排序缺口（unique）"),
    ("coverage_gap_rate_per_1k", "覆盖缺口率 / 千词"),
    ("ranking_gap_rate_per_1k", "排序缺口率 / 千词"),
    ("dist_entries", "dist 条目数"),
    ("total_words", "分词总数"),
    ("unique_words", "唯一词数"),
]


def collect(dist: Path, corpus_dir: Path) -> dict:
    pinyin_map, all_surfaces = parse_dict_yamls(dist)
    total_words = 0
    word_freq: Counter[str] = Counter()
    cov_src: dict[str, set[str]] = defaultdict(set)
    rank_src: dict[str, set[str]] = defaultdict(set)
    rank_detail: dict[str, dict] = {}
    per_source: dict[str, dict] = {}

    for path in sorted(corpus_dir.glob("*.txt")):
        words = segment_text(path.read_text(encoding="utf-8"))
        total_words += len(words)
        word_freq.update(words)
        stem = path.stem
        per_source[stem] = {"words": len(words), "coverage_gaps": 0, "ranking_gaps": 0}
        for word in set(words):
            if word not in all_surfaces:
                cov_src[word].add(stem)
                per_source[stem]["coverage_gaps"] += 1
                continue
            pinyin = get_pinyin(word)
            if not pinyin or pinyin not in pinyin_map:
                continue
            candidates = pinyin_map[pinyin]
            if not candidates:
                continue
            top1 = candidates[0][1]
            if top1 == word:
                continue
            rank_src[word].add(stem)
            per_source[stem]["ranking_gaps"] += 1
            weight = next((w for w, s in candidates if s == word), None)
            cur = rank_detail.get(word)
            if cur is None or (weight or 0) > (cur["weight"] or 0):
                rank_detail[word] = {
                    "pinyin": pinyin,
                    "expected": word,
                    "top1": top1,
                    "weight": weight,
                }

    cov_top = [
        {"word": w, "freq": word_freq[w], "sources": sorted(cov_src[w])}
        for w in sorted(cov_src, key=lambda x: -word_freq[x])[:20]
    ]
    rank_top = [
        {
            "word": w,
            "freq": word_freq[w],
            "pinyin": rank_detail[w]["pinyin"],
            "top1": rank_detail[w]["top1"],
            "sources": sorted(rank_src[w]),
        }
        for w in sorted(rank_src, key=lambda x: -word_freq[x])[:20]
    ]
    metrics = {
        "dist_entries": sum(len(v) for v in pinyin_map.values()),
        "pinyin_keys": len(pinyin_map),
        "corpus_files": len(per_source),
        "total_words": total_words,
        "unique_words": len(word_freq),
        "coverage_gaps": len(cov_src),
        "ranking_gaps": len(rank_src),
        "coverage_gap_rate_per_1k": round(len(cov_src) / total_words * 1000, 2),
        "ranking_gap_rate_per_1k": round(len(rank_src) / total_words * 1000, 2),
    }
    return {
        "metrics": metrics,
        "per_source": per_source,
        "cov_top": cov_top,
        "rank_top": rank_top,
        "rank_detail": rank_detail,
        "word_freq": word_freq,
        "rank_src": rank_src,
    }


def fmt_delta(current, previous) -> str:
    delta = current - previous
    return f"{delta:+}" if isinstance(delta, float) else f"{delta:+d}"


def write_report(
    rounds_dir: Path,
    label: str,
    result: dict,
    prev: dict | None,
) -> Path:
    rounds_dir.mkdir(parents=True, exist_ok=True)
    metrics = result["metrics"]
    lines = [
        f"# 语料轮报告 {label}",
        "",
        f"生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
        "",
    ]
    if prev:
        pm = prev["metrics"]
        lines += ["| 指标 | 上轮 | 本轮 | Δ |", "|---|---|---|---|"]
        for key, cn in METRIC_ROWS:
            cur, old = metrics[key], pm.get(key, 0)
            lines.append(f"| {cn} | {old} | {cur} | {fmt_delta(cur, old)} |")
        note = prev.get("note")
        if note:
            lines += ["", f"上轮备注：{note}"]
    else:
        lines += ["（首轮，无上轮对照）", ""]
        lines += ["| 指标 | 本轮 |", "|---|---|"]
        for key, cn in METRIC_ROWS:
            lines.append(f"| {cn} | {metrics[key]} |")
    lines += ["", "## 覆盖缺口 Top20", ""]
    for item in result["cov_top"]:
        lines.append(
            f"- {item['word']}（freq={item['freq']}, from={','.join(item['sources'])}）"
        )
    lines += ["", "## 排序缺口 Top20（同音竞争）", ""]
    for item in result["rank_top"]:
        lines.append(
            f"- {item['word']} ← TOP-1 {item['top1']}"
            f"（pinyin={item['pinyin']}, freq={item['freq']},"
            f" from={','.join(item['sources'])}）"
        )
    lines += ["", "## 分源统计", "", "| 语料 | 分词 | 覆盖缺口 | 排序缺口 |", "|---|---|---|---|"]
    for stem, info in result["per_source"].items():
        lines.append(
            f"| {stem} | {info['words']} | {info['coverage_gaps']} | {info['ranking_gaps']} |"
        )
    out = rounds_dir / f"{label}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def export_cases(result: dict, cases_path: Path) -> int:
    rows = []
    freq = result["word_freq"]
    for word, detail in result["rank_detail"].items():
        rows.append(
            (
                detail["pinyin"],
                word,
                detail["top1"],
                detail["weight"] or 0,
                freq[word],
                ",".join(sorted(result["rank_src"][word])),
            )
        )
    rows.sort(key=lambda r: -r[4])
    cases_path.parent.mkdir(parents=True, exist_ok=True)
    with cases_path.open("w", encoding="utf-8") as fh:
        fh.write("pinyin\texpected\tcurrent_top1\tweight\tfreq\tsources\n")
        for pinyin, expected, top1, weight, f, sources in rows:
            fh.write(f"{pinyin}\t{expected}\t{top1}\t{weight}\t{f}\t{sources}\n")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path("dist/rime"))
    parser.add_argument("--corpus-dir", type=Path, default=Path("data/eval/corpus"))
    parser.add_argument("--rounds-dir", type=Path, default=Path("data/eval/rounds"))
    parser.add_argument("--cases", type=Path, default=Path("data/eval/probe-cases.tsv"))
    parser.add_argument("--label", default=None, help="override round label")
    args = parser.parse_args()

    result = collect(args.dist, args.corpus_dir)
    latest = args.rounds_dir / "latest.json"
    prev = json.loads(latest.read_text(encoding="utf-8")) if latest.is_file() else None
    index = (prev or {}).get("index", 0) + 1
    label = args.label or f"{datetime.now():%Y-%m-%d}-r{index}"

    report = write_report(args.rounds_dir, label, result, prev)
    n_cases = export_cases(result, args.cases)

    snapshot = {
        "round": label,
        "index": index,
        "metrics": result["metrics"],
        "per_source": result["per_source"],
    }
    latest.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"round {label}: report={report} cases={n_cases} -> {args.cases}")
    for key, _ in METRIC_ROWS:
        prev_v = (prev or {}).get("metrics", {}).get(key)
        cur_v = result["metrics"][key]
        suffix = f" (prev {prev_v})" if prev_v is not None else ""
        print(f"  {key}: {cur_v}{suffix}")


if __name__ == "__main__":
    main()
