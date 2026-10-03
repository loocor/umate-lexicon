#!/usr/bin/env python3
"""Calibrate our dictionary ranking against Wanxiang relative positions.

Compares the relative rank of entries within each toneless pinyin group
between our dist/rime output and Wanxiang (zi + jichu) dictionaries.
Reports divergences (TOP-1 mismatches, large rank shifts) without
copying Wanxiang weights into the repo.

Usage:
    python scripts/wanxiang_calibration.py \
        --dist dist/rime \
        --wanxiang-zi /path/to/wanxiang_zi.dict.yaml \
        [--wanxiang-jichu /path/to/wanxiang_jichu.dict.yaml] \
        [--top N] [--report PATH]
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

# Tone-marked pinyin -> toneless
_TONE_MAP = str.maketrans("āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ", "aaaaeeeeiiiioooouuuuvvvv")


def strip_tones(pinyin: str) -> str:
    """Remove tone marks from a pinyin string (single or multi-syllable)."""
    return pinyin.translate(_TONE_MAP).strip().lower()


def parse_wanxiang(path: Path) -> dict[str, list[tuple[str, int]]]:
    """Parse a Wanxiang dict.yaml; return {toneless_pinyin: [(surface, weight)]}."""
    groups: dict[str, list[tuple[str, int]]] = defaultdict(list)
    in_data = False
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line == "...":
            in_data = True
            continue
        if not in_data or not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        surface, pinyin, weight = parts[0], parts[1], int(parts[2])
        key = strip_tones(pinyin)
        groups[key].append((surface, weight))
    for key in groups:
        groups[key].sort(key=lambda x: -x[1])
    return groups


def parse_dist(path: Path) -> dict[str, list[tuple[str, int]]]:
    """Parse our dist/rime dict.yaml files; return {toneless_pinyin: [(surface, weight)]}."""
    groups: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for file_path in sorted(path.glob("*.dict.yaml")):
        in_data = False
        for line in file_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line == "...":
                in_data = True
                continue
            if not in_data or not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            surface, pinyin, weight = parts[0], parts[1], int(parts[2])
            key = strip_tones(pinyin)
            groups[key].append((surface, weight))
    for key in groups:
        groups[key].sort(key=lambda x: -x[1])
    return groups


def relative_rank(lst: list[tuple[str, int]], surface: str) -> int | None:
    """1-based rank of surface within lst (already sorted by weight desc)."""
    for i, (s, _) in enumerate(lst):
        if s == surface:
            return i + 1
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path("dist/rime"))
    parser.add_argument("--wanxiang-zi", type=Path, required=True)
    parser.add_argument("--wanxiang-jichu", type=Path)
    parser.add_argument("--top", type=int, default=200, help="Report divergences within top N positions")
    parser.add_argument("--report", type=Path, help="Write markdown report to this path (default: stdout)")
    args = parser.parse_args()

    # Load Wanxiang (merge zi + jichu if both provided)
    wx_groups = parse_wanxiang(args.wanxiang_zi)
    wx_entry_count = sum(len(v) for v in wx_groups.values())
    if args.wanxiang_jichu:
        jichu = parse_wanxiang(args.wanxiang_jichu)
        for key, entries in jichu.items():
            wx_groups[key].extend(entries)
        # re-sort after merge
        for key in wx_groups:
            wx_groups[key].sort(key=lambda x: -x[1])
        wx_entry_count += sum(len(v) for v in jichu.values())

    our_groups = parse_dist(args.dist)
    our_entry_count = sum(len(v) for v in our_groups.values())

    print(f"Wanxiang entries: {wx_entry_count}, pinyin groups: {len(wx_groups)}")
    print(f"Our dist entries: {our_entry_count}, pinyin groups: {len(our_groups)}")

    # Find shared pinyin groups (at least 2 entries on both sides)
    shared_keys = sorted(
        key for key in wx_groups
        if key in our_groups and len(wx_groups[key]) >= 2 and len(our_groups[key]) >= 2
    )
    print(f"Shared pinyin groups (>=2 entries both sides): {len(shared_keys)}")

    # Compare TOP-1 within each shared group
    top1_match = 0
    top1_mismatch = 0
    top1_mismatch_list: list[tuple[str, str, str, int, int]] = []  # (pinyin, our_top1, wx_top1, our_grp_size, wx_grp_size)

    # Rank shift analysis for single chars
    single_char_shifts: list[tuple[str, str, int | None, int | None]] = []  # (char, pinyin, our_rank, wx_rank)

    for key in shared_keys:
        our_entries = our_groups[key]
        wx_entries = wx_groups[key]
        our_top1 = our_entries[0][0]
        wx_top1 = wx_entries[0][0]
        if our_top1 == wx_top1:
            top1_match += 1
        else:
            top1_mismatch += 1
            top1_mismatch_list.append((key, our_top1, wx_top1, len(our_entries), len(wx_entries)))

        # Track single-char rank positions
        if len(key.split()) == 1:
            for surface in {s for s, _ in our_entries} | {s for s, _ in wx_entries}:
                if len(surface) == 1:
                    our_r = relative_rank(our_entries, surface)
                    wx_r = relative_rank(wx_entries, surface)
                    if our_r is not None and wx_r is not None and our_r != wx_r:
                        single_char_shifts.append((surface, key, our_r, wx_r))

    # Sort mismatches by Wanxiang group size (larger groups = more competitive)
    top1_mismatch_list.sort(key=lambda x: -min(x[4], 100))

    lines: list[str] = []
    lines.append("# Wanxiang Calibration Report")
    lines.append("")
    lines.append(f"- Wanxiang entries: {wx_entry_count} ({len(wx_groups)} pinyin groups)")
    lines.append(f"- Our dist entries: {our_entry_count} ({len(our_groups)} pinyin groups)")
    lines.append(f"- Shared pinyin groups (>=2 both sides): {len(shared_keys)}")
    lines.append(f"- TOP-1 match: {top1_match} ({top1_match*100//max(1,len(shared_keys))}%)")
    lines.append(f"- TOP-1 mismatch: {top1_mismatch}")
    lines.append("")

    if top1_mismatch_list:
        lines.append(f"## TOP-1 divergences (top {args.top})")
        lines.append("")
        lines.append("| pinyin | ours | wanxiang | our group | wx group |")
        lines.append("|--------|------|----------|-----------|----------|")
        for key, ours, wxs, on, wn in top1_mismatch_list[: args.top]:
            lines.append(f"| {key} | {ours} | {wxs} | {on} | {wn} |")
        lines.append("")

    # Single-char rank inversions where direction differs
    inversions = [
        (s, p, orr, wxr)
        for s, p, orr, wxr in single_char_shifts
        if (orr or 0) < (wxr or 0)
    ]
    inversions.sort(key=lambda x: -((x[3] or 0) - (x[2] or 0)))
    lines.append(f"## Single-char inversions (ours ranks higher than Wanxiang): {len(inversions)}")
    lines.append("")
    if inversions:
        lines.append("| char | pinyin | our rank | wx rank | shift |")
        lines.append("|------|--------|----------|---------|-------|")
        for s, p, orr, wxr in inversions[: args.top]:
            shift = (wxr or 0) - (orr or 0)
            lines.append(f"| {s} | {p} | {orr} | {wxr} | +{shift} |")
        lines.append("")

    under_ranks = [
        (s, p, orr, wxr)
        for s, p, orr, wxr in single_char_shifts
        if (orr or 0) > (wxr or 0)
    ]
    under_ranks.sort(key=lambda x: -((x[2] or 0) - (x[3] or 0)))
    lines.append(f"## Single-char under-ranks (ours ranks lower than Wanxiang): {len(under_ranks)}")
    lines.append("")
    if under_ranks:
        lines.append("| char | pinyin | our rank | wx rank | shift |")
        lines.append("|------|--------|----------|---------|-------|")
        for s, p, orr, wxr in under_ranks[: args.top]:
            shift = (orr or 0) - (wxr or 0)
            lines.append(f"| {s} | {p} | {orr} | {wxr} | +{shift} |")
        lines.append("")

    report = "\n".join(lines)
    if args.report:
        args.report.write_text(report, encoding="utf-8")
        print(f"Report written to {args.report}")
    else:
        print(report)


if __name__ == "__main__":
    main()
