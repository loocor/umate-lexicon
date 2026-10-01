#!/usr/bin/env python3
"""Export wikinews-domain context probe cases from scored octagram bigrams.

Reads the dated Wikinews TSV, v2 scored collocation table, and emitted
Rime tables. Emits candidate ctx cases (commit prefix word, then type
the next word's pinyin) for manual review. Does not invent lemmas.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_corpus import get_pinyin, parse_dict_yamls  # noqa: E402

HAN = re.compile(r"^[\u4e00-\u9fff]+$")
DOMAIN_KEYWORDS = (
    "台风",
    "飓风",
    "气旋",
    "地震",
    "余震",
    "海啸",
    "暴雨",
    "洪水",
    "洪灾",
    "泥石流",
    "山体滑坡",
    "塌方",
    "沙尘",
    "雾霾",
    "降温",
    "高温",
    "寒潮",
    "暴雪",
    "火灾",
    "爆炸",
    "事故",
    "空难",
    "沉船",
    "撞车",
    "伤亡",
    "疏散",
    "预警",
    "登陆",
    "震中",
    "震感",
    "气象",
    "天气",
)
MAX_WORD = 4


def compact_pinyin(surface: str) -> str:
    spaced = get_pinyin(surface)
    return spaced.replace(" ", "") if spaced else ""


def load_scores(path: Path) -> dict[str, int]:
    scores: dict[str, int] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or "\t" not in line:
                continue
            key, _, raw = line.partition("\t")
            try:
                scores[key] = int(raw)
            except ValueError:
                continue
    return scores


def pair_score(scores: dict[str, int], left: str, right: str) -> int:
    word_key = right[:MAX_WORD]
    best = 0
    tail = left[-MAX_WORD:]
    for k in range(1, min(MAX_WORD, len(tail)) + 1):
        key = tail[-k:] + word_key
        best = max(best, scores.get(key, 0))
    return best


def domain_hits(text: str) -> list[str]:
    return [kw for kw in DOMAIN_KEYWORDS if kw in text]


def iter_articles(path: Path):
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            title, _, body = line.partition("\t")
            yield title, body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wikinews",
        type=Path,
        default=Path("data/sources/downloads/wikinews-20261001-pages.tsv"),
    )
    parser.add_argument(
        "--scored",
        type=Path,
        default=Path("/Volumes/Backup/tmp/umate-octagram-work/scored-final.tsv"),
    )
    parser.add_argument("--dist", type=Path, default=Path("dist/rime"))
    parser.add_argument("--min-score", type=int, default=90000)
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    import jieba

    jieba.setLogLevel(60)
    print("loading dicts...", flush=True)
    pinyin_map, all_surfaces = parse_dict_yamls(args.dist)
    print(f"surfaces={len(all_surfaces)} pinyin_keys={len(pinyin_map)}", flush=True)
    print("loading scores...", flush=True)
    scores = load_scores(args.scored)
    print(f"scored_keys={len(scores)}", flush=True)

    seen_pairs: set[tuple[str, str]] = set()
    candidates: list[dict] = []

    for title, body in iter_articles(args.wikinews):
        article = f"{title} {body}"
        hits = domain_hits(article)
        if not hits:
            continue
        # Sentence-ish chunks keep the collocation local.
        chunks = re.split(r"[。！？；!?;\n]", article)
        for chunk in chunks:
            chunk_hits = domain_hits(chunk) or hits
            words = [w for w in jieba.cut(chunk) if HAN.fullmatch(w) and 2 <= len(w) <= 4]
            if len(words) < 2:
                continue
            for left, right in zip(words, words[1:]):
                pair = (left, right)
                if pair in seen_pairs:
                    continue
                if left not in all_surfaces or right not in all_surfaces:
                    continue
                if not (set(chunk_hits) & {left, right} or any(kw in left + right for kw in DOMAIN_KEYWORDS)):
                    continue
                score = pair_score(scores, left, right)
                if score < args.min_score:
                    continue
                left_py = compact_pinyin(left)
                right_py = compact_pinyin(right)
                if not left_py or not right_py:
                    continue
                left_key = get_pinyin(left)
                right_key = get_pinyin(right)
                left_cands = pinyin_map.get(left_key) or []
                right_cands = pinyin_map.get(right_key) or []
                if not left_cands or not right_cands:
                    continue
                left_top = left_cands[0][1]
                right_top = right_cands[0][1]
                if left_top != left:
                    continue  # space-commit would not produce the intended context
                discriminative = right_top != right
                if len(right_cands) < 2:
                    continue
                seen_pairs.add(pair)
                snippet = chunk.strip()
                if len(snippet) > 80:
                    snippet = snippet[:80] + "…"
                candidates.append(
                    {
                        "score": score,
                        "left": left,
                        "right": right,
                        "left_py": left_py,
                        "right_py": right_py,
                        "right_top": right_top,
                        "discriminative": int(discriminative),
                        "domains": ",".join(chunk_hits[:4]),
                        "title": title[:40],
                        "snippet": snippet.replace("\t", " "),
                    }
                )

    candidates.sort(key=lambda row: (-row["discriminative"], -row["score"], row["left"], row["right"]))
    # Spread across right-hand words so 登陆 does not eat the whole set.
    picked: list[dict] = []
    per_right: dict[str, int] = defaultdict(int)
    per_domain: dict[str, int] = defaultdict(int)
    for row in candidates:
        if len(picked) >= args.limit:
            break
        if per_right[row["right"]] >= 3:
            continue
        primary = row["domains"].split(",")[0] if row["domains"] else "other"
        if per_domain[primary] >= 12:
            continue
        per_right[row["right"]] += 1
        per_domain[primary] += 1
        picked.append(row)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        fh.write(
            "prefix_pinyin\tprobe_pinyin\texpected\tlabel\tsoft\tdomain\t"
            "score\tdiscriminative\tright_top\tprefix\tevidence\n"
        )
        for i, row in enumerate(picked, 1):
            label = f"ctx-wikinews-{i:03d}-{row['left']}-{row['right']}"
            fh.write(
                f"{row['left_py']}\t{row['right_py']}\t{row['right']}\t{label}\t1\t"
                f"wikinews\t{row['score']}\t{row['discriminative']}\t{row['right_top']}\t"
                f"{row['left']}\t{row['snippet']}\n"
            )
    disc = sum(r["discriminative"] for r in picked)
    print(f"wrote {len(picked)} candidates ({disc} discriminative) -> {args.out}")
    print(f"pool={len(candidates)} unique_pairs={len(seen_pairs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
