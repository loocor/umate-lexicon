#!/usr/bin/env python3
"""Stream the first column from a Tencent embedding dump into a vocab file.

Accepts Google/gensim word2vec binary (`.bin`), text dumps, `.gz`, and
`.tar.gz`. The factory only needs the word list (coverage), not the
vectors. Do not copy rime-ice tencent.dict.yaml.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from umate_lexicon.word2vec import write_vocab  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args(argv)
    write_vocab(args.source, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
