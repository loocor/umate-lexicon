"""Locked-store probes. These fail the release; they do not add lemmas."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from umate_lexicon.gaps import classify_surface
from umate_lexicon.layers import assign_layer, emit_weight, is_hot_member
from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore


@dataclass(frozen=True)
class ProbeFailure:
    check: str
    surface: str
    detail: str


def load_probes(path: Path | None = None) -> list[tuple[str, str, str, str, str]]:
    target = path or data_dir() / "gold" / "emit-probes.tsv"
    rows: list[tuple[str, str, str, str, str]] = []
    for raw in target.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        while len(parts) < 5:
            parts.append("")
        rows.append((parts[0], parts[1], parts[2], parts[3], parts[4]))
    return rows


def evaluate_probes(
    store: LemmaStore,
    path: Path | None = None,
    emit_dir: Path | None = None,
) -> list[ProbeFailure]:
    failures: list[ProbeFailure] = []
    chars_text = ""
    if emit_dir is not None:
        chars_path = emit_dir / "umate_chars.dict.yaml"
        if not chars_path.is_file():
            return [ProbeFailure("emit", "", f"missing {chars_path}")]
        chars_text = chars_path.read_text(encoding="utf-8")
    for check, surface, pinyin, expect, expect2 in load_probes(path):
        lemma = store.get(surface, pinyin) if pinyin else None
        if check == "reading":
            if lemma is None or lemma.status == "rejected":
                failures.append(ProbeFailure(check, surface, f"missing {pinyin}"))
            continue
        if check == "layer":
            if lemma is None:
                failures.append(ProbeFailure(check, surface, f"missing {pinyin}"))
                continue
            actual = assign_layer(lemma)
            if actual != expect:
                failures.append(ProbeFailure(check, surface, f"{pinyin} layer {actual} != {expect}"))
            elif emit_dir is not None and expect == "chars" and f"\n{surface}\t{pinyin}\t" not in chars_text:
                failures.append(ProbeFailure(check, surface, f"{pinyin} not in umate_chars"))
            continue
        if check == "hot":
            if lemma is None:
                failures.append(ProbeFailure(check, surface, f"missing {pinyin}"))
                continue
            hot = is_hot_member(lemma)
            if expect == "yes" and not hot:
                failures.append(ProbeFailure(check, surface, f"{pinyin} not hot"))
            if expect == "no" and hot:
                failures.append(ProbeFailure(check, surface, f"{pinyin} unexpectedly hot"))
            continue
        if check == "weight_gt":
            left = store.get(surface, pinyin)
            right = store.get(expect, expect2)
            if left is None or right is None:
                failures.append(ProbeFailure(check, surface, f"missing pair {pinyin} / {expect} {expect2}"))
                continue
            if emit_weight(left) <= emit_weight(right):
                failures.append(
                    ProbeFailure(
                        check,
                        surface,
                        f"{pinyin} {emit_weight(left)} <= {expect} {expect2} {emit_weight(right)}",
                    )
                )
            continue
        if check == "gap":
            finding = classify_surface(store, surface)
            if finding.bucket != expect:
                failures.append(ProbeFailure(check, surface, f"{finding.bucket} != {expect}"))
            continue
        if check == "not_emitted":
            if lemma is not None and assign_layer(lemma) is not None:
                failures.append(ProbeFailure(check, surface, f"{pinyin} layer {assign_layer(lemma)}"))
            elif emit_dir is not None and f"\n{surface}\t{pinyin}\t" in chars_text:
                failures.append(ProbeFailure(check, surface, f"{pinyin} present in umate_chars"))
            continue
        failures.append(ProbeFailure(check, surface, "unknown check"))
    return failures
