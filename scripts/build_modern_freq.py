#!/usr/bin/env python3
"""Build modern_freq v1: rank-calibrated core-scale values for single chars.

Uses hanyu_pinlu's relative ordering mapped onto the core frequency scale
via rank-to-rank quantile matching. The result is stored as a `modern_freq`
domain in the ledger. Multi-char words are NOT covered: tencent vocab has
no usable frequency counts (88% are placeholder 1), only a coarse
"appeared at least N times" signal.

Usage:
    PYTHONPATH=src python scripts/build_modern_freq.py [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from umate_lexicon.store import LemmaStore  # noqa: E402


def build_char_modern_freq(
    chars: list[tuple[str, str, int, int]],
) -> list[tuple[str, str, int]]:
    """Rank-to-rank quantile mapping: pinlu order → core scale.

    Args:
        chars: (surface, pinyin, core_value, pinlu_value) sorted by pinlu desc.
    Returns:
        (surface, pinyin, modern_freq) where modern_freq is on core scale.
    """
    if not chars:
        return []
    core_values = sorted((c for _, _, c, _ in chars), reverse=True)
    results = []
    for i, (surface, pinyin, _core, _pinlu) in enumerate(chars):
        mapped = core_values[i] if i < len(core_values) else 0
        results.append((surface, pinyin, mapped))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--store", type=Path, default=Path("data/store/lemmas.sqlite"))
    args = parser.parse_args()

    store = LemmaStore(args.store)

    char_rows = []
    for lemma in store.all_lemmas():
        if len(lemma.surface) != 1:
            continue
        core = int(lemma.domain_freq.get("core") or 0)
        pinlu = int(lemma.domain_freq.get("hanyu_pinlu") or 0)
        if core > 0 and pinlu > 0:
            char_rows.append((lemma.surface, lemma.pinyin_plain, core, pinlu))

    char_rows.sort(key=lambda x: -x[3])
    print(f"Single chars with both core+pinlu: {len(char_rows)}")

    calibrated = build_char_modern_freq(char_rows)

    print("\n--- Largest rank corrections (pinlu order vs old core) ---")
    cal_map = {(s, p): v for s, p, v in calibrated}
    changes = []
    for surface, pinyin, old_core, pinlu in char_rows:
        new_val = cal_map.get((surface, pinyin), old_core)
        if abs(new_val - old_core) / max(1, old_core) > 0.5:
            changes.append((surface, pinyin, old_core, new_val, pinlu))
    changes.sort(key=lambda x: -abs(x[3] - x[2]))
    for s, p, old, new, pl in changes[:15]:
        direction = "up" if new > old else "down"
        print(f"  {s} {p}: core={old:>10} -> modern_freq={new:>10} {direction} (pinlu={pl})")

    qun = cal_map.get(("群", "qun"))
    qun2 = cal_map.get(("裙", "qun"))
    print(f"\n群(qun): {qun}")
    print(f"裙(qun): {qun2}")
    ok = "YES" if qun and qun2 and qun > qun2 else "NO"
    print(f"群 > 裙: {ok}")

    if args.dry_run:
        print("\n(dry run, no store writes)")
        return

    updated = 0
    with store.deferred_commit():
        for lemma in store.all_lemmas():
            key = (lemma.surface, lemma.pinyin_plain)
            if key in cal_map:
                lemma.domain_freq["modern_freq"] = cal_map[key]
                store.save(lemma)
                updated += 1
    print(f"\nWrote modern_freq for {updated} lemmas.")


if __name__ == "__main__":
    main()
