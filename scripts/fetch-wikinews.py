#!/usr/bin/env python3
"""Fetch zh.wikinews.org main-namespace articles as a dated TSV snapshot.

Output: /Volumes/Backup/tmp/umate-wikinews-corpus/wikinews-<date>-pages.tsv
One article per line: `title<TAB>body`. Wikitext is stripped to plain
text and converted to Simplified Chinese with OpenCC t2s at fetch time,
so downstream consumers (jieba segmentation, .gram training) see the
same script as the emitted dictionaries. The raw snapshot stays on the
scratch volume and is never committed; the Lexicon lock pins its hash.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

API = "https://zh.wikinews.org/w/api.php"
UA = "umate-lexicon/0.1 (contact: loocor@users.noreply.github.com)"
BATCH = 20
THROTTLE = 0.8
MIN_BODY_CHARS = 200
DEFAULT_OUT = Path("/Volumes/Backup/tmp/umate-wikinews-corpus")

TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
REF = re.compile(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", re.DOTALL)
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
WIKILINK = re.compile(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]")
TAG = re.compile(r"<[^>]+>")
URL = re.compile(r"https?://\S+")
EXTRA = re.compile(r"[ \t]+")
REDIRECT = re.compile(r"^#\s*(?:REDIRECT|重定向|重新導向)", re.IGNORECASE)


def api(params: dict) -> dict:
    import subprocess
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        r = subprocess.run(
            ["curl", "-sf", "--retry", "3", "--retry-all-errors",
             "--max-time", "120", "-A", UA, url],
            capture_output=True,
        )
        if r.returncode == 0:
            try:
                return json.loads(r.stdout)
            except json.JSONDecodeError:
                pass
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"api failed after retries: {url[:100]}")


def clean_wikitext(raw: str, opencc) -> str:
    text = REDIRECT.sub("", raw.strip()) if REDIRECT.match(raw) else raw
    if REDIRECT.match(raw):
        return ""
    text = REF.sub(" ", text)
    text = COMMENT.sub(" ", text)
    for _ in range(4):
        text = TEMPLATE.sub(" ", text)
    text = WIKILINK.sub(r"\1", text)
    text = TAG.sub(" ", text)
    text = URL.sub(" ", text)
    text = text.replace("&nbsp;", " ")
    text = opencc.convert(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--date", default=datetime.now().strftime("%Y%m%d"))
    args = parser.parse_args()
    from opencc import OpenCC  # opencc-python-reimplemented
    opencc = OpenCC("t2s")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / f"wikinews-{args.date}-pages.tsv"

    # 1. all titles as (pageid, title) pairs, cached for resumable runs
    titles_cache = args.out_dir / "titles.jsonl"
    if titles_cache.is_file():
        titles = [
            (int(line.split("\t", 1)[0]), line.split("\t", 1)[1].rstrip("\n"))
            for line in titles_cache.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        print(f"titles_cached={len(titles)}", flush=True)
    else:
        titles = []
        cont = None
        while True:
            p: dict = {"action": "query", "list": "allpages", "aplimit": "500",
                       "format": "json", "formatversion": "2"}
            if cont:
                p["apcontinue"] = cont
            d = api(p)
            for page in d.get("query", {}).get("allpages", []):
                titles.append((page["pageid"], page["title"]))
            cont = d.get("continue", {}).get("apcontinue")
            if not cont:
                break
            time.sleep(THROTTLE)
        with titles_cache.open("w", encoding="utf-8") as cf:
            for pid, title in titles:
                cf.write(f"{pid}\t{title}\n")
        print(f"titles={len(titles)}", flush=True)

    # 2. batched revisions, resumable via done_ids.txt
    done_ids_path = args.out_dir / "done_ids.txt"
    done_ids: set[int] = set()
    if done_ids_path.is_file():
        done_ids = {
            int(line) for line in done_ids_path.read_text().splitlines() if line.strip()
        }
        print(f"resuming, done={len(done_ids)}", flush=True)
    kept = sum(1 for _ in out.open(encoding="utf-8")) if out.is_file() else 0
    skipped = 0
    skipped_fh = (args.out_dir / "skipped.tsv").open("a", encoding="utf-8")
    done_fh = done_ids_path.open("a", encoding="utf-8")
    with out.open("a", encoding="utf-8") as fh:
        pending = [(pid, title) for pid, title in titles if pid not in done_ids]
        print(f"pending={len(pending)}", flush=True)
        for i in range(0, len(pending), BATCH):
            chunk = pending[i : i + BATCH]
            ids = "|".join(str(pid) for pid, _ in chunk)
            d = api({"action": "query", "prop": "revisions", "rvprop": "content",
                     "rvslots": "main", "pageids": ids,
                     "format": "json", "formatversion": "2"})
            title_by_id = {pid: title for pid, title in chunk}
            for page in d.get("query", {}).get("pages", []):
                pid = page["pageid"]
                revs = page.get("revisions") or []
                raw = (revs[0].get("slots", {}).get("main", {}).get("content", "")
                       if revs else "")
                body = clean_wikitext(raw, opencc)
                if len(body) < MIN_BODY_CHARS:
                    skipped += 1
                    skipped_fh.write(
                        f"{pid}\t{len(raw)}\t{len(body)}\t"
                        f"{title_by_id[pid][:40]}\n"
                    )
                else:
                    title = opencc.convert(title_by_id[pid]).strip()
                    fh.write(f"{title}\t{body}\n")
                    kept += 1
                done_fh.write(f"{pid}\n")
            done_fh.flush()
            skipped_fh.flush()
            print(f"progress {i + BATCH}/{len(pending)} kept={kept} skipped={skipped}",
                  flush=True)
            time.sleep(THROTTLE)
    skipped_fh.close()
    done_fh.close()
    print(f"done kept={kept} skipped={skipped} out={out}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
