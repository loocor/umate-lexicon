#!/usr/bin/env python3
"""Wrap MOT v1.11 VOA Mandarin articles into a mediawiki xml.bz2.

The tarball is training-feed only (not lemma ingest). This helper:
  * reads `article/*.json` from `cmn_voachinese.tgz`
  * keeps content_type=article with predicted_language=cmn
  * OpenCC t2s so collocations match the zh-hans dictionary
  * recent-first CJK cap (default 10_000_000) so extract() cannot
    spend its per-file 30M budget on MOT alone
  * emits the <page>/<text> shape train_grammar.extract parses

Usage:
  wrap_mot_voa.py --tarball cmn_voachinese.tgz --out pages.xml.bz2
  wrap_mot_voa.py --t2s-xml in.xml.bz2 --out out.xml.bz2
"""
from __future__ import annotations

import argparse
import bz2
import gzip
import json
import re
import tarfile
from pathlib import Path
from xml.sax.saxutils import escape

CJK_RUN = re.compile(r"[\u3400-\u9fff]+")


def _opencc_t2s():
    from opencc import OpenCC  # opencc-python-reimplemented

    return OpenCC("t2s")


def _cjk_len(text: str) -> int:
    return sum(len(m) for m in CJK_RUN.findall(text))


def _article_text(obj: dict) -> str:
    title = (obj.get("title") or "").strip()
    paras = obj.get("paragraphs") or []
    if isinstance(paras, str):
        body = paras
    else:
        body = "\n".join(p.strip() for p in paras if isinstance(p, str) and p.strip())
    if title and body:
        return title + "\n" + body
    return title or body


def _write_page(out, title: str, body: str) -> None:
    out.write(
        "<page>\n"
        f"  <title>{escape(title)}</title>\n"
        "  <revision>\n"
        f"    <text>{escape(body)}</text>\n"
        "  </revision>\n"
        "</page>\n"
    )


def t2s_xml(src: Path, dst: Path) -> dict:
    opencc = _opencc_t2s()
    pages = 0
    with bz2.open(src, "rt", encoding="utf-8") as fh, bz2.open(
        dst, "wt", encoding="utf-8"
    ) as out:
        for line in fh:
            out.write(opencc.convert(line))
            if "<page>" in line:
                pages += 1
    return {"pages": pages, "out": str(dst)}


def wrap_tarball(tarball: Path, dst: Path, cap: int) -> dict:
    opencc = _opencc_t2s()
    skipped = {"not_article": 0, "lang": 0, "empty": 0, "json": 0}
    articles: list[tuple[str, str, str]] = []
    total_cjk = 0
    kept_all = 0
    with tarfile.open(tarball, "r:gz") as tf:
        for member in tf:
            name = member.name
            if member.isdir() or "/article/" not in name:
                continue
            if not (name.endswith(".json") or name.endswith(".json.gz")):
                continue
            extracted = tf.extractfile(member)
            if extracted is None:
                continue
            raw = extracted.read()
            if name.endswith(".gz") or raw[:2] == b"\x1f\x8b":
                try:
                    raw = gzip.decompress(raw)
                except OSError:
                    skipped["json"] += 1
                    continue
            try:
                obj = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                skipped["json"] += 1
                continue
            if (obj.get("content_type") or "article") != "article":
                skipped["not_article"] += 1
                continue
            lang = obj.get("predicted_language") or ""
            if lang and lang != "cmn":
                skipped["lang"] += 1
                continue
            text = _article_text(obj)
            text = opencc.convert(text)
            title = opencc.convert((obj.get("title") or "").strip()) or "untitled"
            if _cjk_len(text) < 40:
                skipped["empty"] += 1
                continue
            published = obj.get("time_published") or ""
            articles.append((published, title, text))
            kept_all += 1
            total_cjk += _cjk_len(text)

    articles.sort(key=lambda row: row[0], reverse=True)
    picked = []
    picked_cjk = 0
    for published, title, text in articles:
        n = _cjk_len(text)
        if picked_cjk + n > cap and picked:
            break
        picked.append((published, title, text))
        picked_cjk += n
        if picked_cjk >= cap:
            break

    with bz2.open(dst, "wt", encoding="utf-8") as out:
        out.write("<mediawiki>\n")
        for _, title, text in picked:
            _write_page(out, title, text)
        out.write("</mediawiki>\n")

    newest = picked[0][0] if picked else ""
    oldest = picked[-1][0] if picked else ""
    return {
        "source": str(tarball),
        "out": str(dst),
        "kept_articles_all": kept_all,
        "total_cjk_all": total_cjk,
        "skipped": skipped,
        "picked": len(picked),
        "picked_cjk": picked_cjk,
        "cap": cap,
        "newest": newest,
        "oldest": oldest,
        "t2s": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tarball", type=Path)
    parser.add_argument("--t2s-xml", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cap", type=int, default=10_000_000)
    parser.add_argument("--stats", type=Path)
    args = parser.parse_args()
    if bool(args.tarball) == bool(args.t2s_xml):
        parser.error("exactly one of --tarball or --t2s-xml is required")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.t2s_xml:
        stats = t2s_xml(args.t2s_xml, args.out)
    else:
        stats = wrap_tarball(args.tarball, args.out, args.cap)
    if args.stats:
        args.stats.write_text(
            __import__("json").dumps(stats, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
