#!/usr/bin/env python3
"""Stream Tencent embedding vocabulary into a one-word-per-line file.

Accepts the official text / tar.gz / gz dumps and gensim-compatible
word2vec binaries (``light_Tencent_AILab_ChineseEmbedding.bin``).
This factory only needs the word list (coverage), not the vectors.
Do not copy rime-ice tencent.dict.yaml.
"""

from __future__ import annotations

import argparse
import gzip
import sys
import tarfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from umate_lexicon.word2vec import iter_word2vec_vocab  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument(
        "--binary",
        action="store_true",
        help="force gensim word2vec binary parsing regardless of suffix",
    )
    args = parser.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as out:
        for surface in iter_tencent_surfaces(args.source, binary=args.binary):
            out.write(surface + "\n")
    return 0


def iter_tencent_surfaces(path: Path, binary: bool = False):
    name = path.name.lower()
    if name.endswith(".tar.gz") or name.endswith(".tgz"):
        with tarfile.open(path, "r:gz") as archive:
            members = [item for item in archive.getmembers() if item.isfile()]
            if not members:
                raise SystemExit(f"no files in {path}")
            member = sorted(members, key=lambda item: item.size, reverse=True)[0]
            handle = archive.extractfile(member)
            if handle is None:
                raise SystemExit(f"cannot extract {member.name}")
            if binary or _is_word2vec_bin_name(member.name):
                yield from iter_word2vec_vocab(handle)
            else:
                yield from _iter_lines(handle)
            return
    if binary or _is_word2vec_bin_name(name):
        if name.endswith(".gz"):
            with gzip.open(path, "rb") as handle:
                yield from iter_word2vec_vocab(handle)
            return
        yield from iter_word2vec_vocab(path)
        return
    if name.endswith(".gz"):
        with gzip.open(path, "rb") as handle:
            yield from _iter_lines(handle)
        return
    with path.open("rb") as handle:
        yield from _iter_lines(handle)


def _is_word2vec_bin_name(name: str) -> bool:
    lowered = name.lower()
    return lowered.endswith(".bin") or lowered.endswith(".bin.gz")


def _iter_lines(handle):
    for raw in handle:
        line = raw.decode("utf-8", errors="replace").strip()
        if not line or line.startswith("#"):
            continue
        surface = line.split()[0]
        if surface:
            yield surface


if __name__ == "__main__":
    sys.exit(main())
