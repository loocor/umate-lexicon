#!/usr/bin/env python3
"""Stream the first column from a Tencent embedding dump into a vocab file.

The official vector file is multi-gigabyte. This factory only needs the
word list (coverage), not the vectors, and does not pin a dump until a
real artifact is hashed. Do not copy rime-ice tencent.dict.yaml.
"""

from __future__ import annotations

import argparse
import gzip
import sys
import tarfile
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as out:
        for surface in _iter_surfaces(args.source):
            out.write(surface + "\n")
    return 0


def _iter_surfaces(path: Path):
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
            yield from _iter_lines(handle)
            return
    if name.endswith(".gz"):
        with gzip.open(path, "rb") as handle:
            yield from _iter_lines(handle)
        return
    with path.open("rb") as handle:
        yield from _iter_lines(handle)


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
