"""Read Google/gensim word2vec dumps and emit a vocab-only word list.

The factory stores coverage surfaces, not embedding vectors. This reader
understands the binary format (`vocab dim` header, then word + float32
payload) and the older text / tar.gz dumps. It does not depend on gensim.
"""

from __future__ import annotations

import gzip
import tarfile
from collections.abc import Iterator
from pathlib import Path

_MAX_DIM = 8192


def write_vocab(source: Path, output: Path) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w", encoding="utf-8") as handle:
        for surface in iter_vocab_surfaces(source):
            handle.write(surface + "\n")
            count += 1
    return count


def iter_vocab_surfaces(path: Path) -> Iterator[str]:
    name = path.name.lower()
    if name.endswith(".tar.gz") or name.endswith(".tgz"):
        yield from _iter_archive(path)
        return
    if name.endswith(".gz"):
        with gzip.open(path, "rb") as handle:
            yield from _iter_text_lines(handle)
        return
    if _is_word2vec_binary(path):
        with path.open("rb") as handle:
            yield from _iter_binary(handle)
        return
    with path.open("rb") as handle:
        yield from _iter_text_lines(handle)


def _iter_archive(path: Path) -> Iterator[str]:
    with tarfile.open(path, "r:gz") as archive:
        members = [item for item in archive.getmembers() if item.isfile()]
        if not members:
            raise ValueError(f"no files in {path}")
        member = sorted(members, key=lambda item: item.size, reverse=True)[0]
        handle = archive.extractfile(member)
        if handle is None:
            raise ValueError(f"cannot extract {member.name}")
        header = handle.readline()
        rest = handle.read(64)
        handle.seek(0)
        if _header_then_binary(header, rest):
            yield from _iter_binary(handle)
            return
        yield from _iter_text_lines(handle)


def _is_word2vec_binary(path: Path) -> bool:
    if path.name.lower().endswith(".bin"):
        return True
    with path.open("rb") as handle:
        header = handle.readline()
        sample = handle.read(64)
    return _header_then_binary(header, sample)


def _header_then_binary(header: bytes, sample: bytes) -> bool:
    parsed = _parse_header(header)
    if parsed is None:
        return False
    space = sample.find(b" ")
    if space < 0:
        return False
    payload = sample[space + 1 : space + 1 + min(8, parsed[1] * 4)]
    if len(payload) < 4:
        return False
    return any(byte < 9 or 13 < byte < 32 or byte > 126 for byte in payload)


def _parse_header(raw: bytes) -> tuple[int, int] | None:
    try:
        text = raw.decode("ascii").strip()
    except UnicodeDecodeError:
        return None
    parts = text.split()
    if len(parts) != 2:
        return None
    try:
        vocab_size = int(parts[0])
        dim = int(parts[1])
    except ValueError:
        return None
    if vocab_size <= 0 or dim <= 0 or dim > _MAX_DIM:
        return None
    return vocab_size, dim


def _iter_binary(handle) -> Iterator[str]:
    header = handle.readline()
    parsed = _parse_header(header)
    if parsed is None:
        raise ValueError(f"invalid word2vec header: {header!r}")
    vocab_size, dim = parsed
    vector_bytes = dim * 4
    for _ in range(vocab_size):
        word_bytes = bytearray()
        while True:
            ch = handle.read(1)
            if not ch:
                raise ValueError("truncated word2vec binary while reading a word")
            if ch == b" ":
                break
            if ch != b"\n":
                word_bytes.extend(ch)
        skipped = handle.read(vector_bytes)
        if len(skipped) != vector_bytes:
            raise ValueError("truncated word2vec binary while skipping a vector")
        word = word_bytes.decode("utf-8", errors="replace")
        if word:
            yield word


def _iter_text_lines(handle) -> Iterator[str]:
    for raw in handle:
        line = raw.decode("utf-8", errors="replace").strip()
        if not line or line.startswith("#"):
            continue
        surface = line.split()[0]
        if surface:
            yield surface
