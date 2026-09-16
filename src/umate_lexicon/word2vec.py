from __future__ import annotations

from collections.abc import BinaryIO, Iterator
from pathlib import Path

FLOAT32_BYTES = 4


def iter_word2vec_vocab(source: Path | BinaryIO) -> Iterator[str]:
    """Yield words from a gensim-compatible word2vec binary.

    Layout: ASCII header ``vocab_size dim\\n``, then each entry is word
    bytes until a space, followed by ``float32 * dim``. Vectors are
    discarded; this factory only needs the vocabulary.
    """
    if isinstance(source, Path):
        with source.open("rb") as handle:
            yield from _iter_word2vec_handle(handle)
        return
    yield from _iter_word2vec_handle(source)


def extract_word2vec_vocab(source: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as out:
        for word in iter_word2vec_vocab(source):
            out.write(word + "\n")
    return dest


def _iter_word2vec_handle(handle: BinaryIO) -> Iterator[str]:
    header = handle.readline()
    if not header:
        raise ValueError("empty word2vec header")
    parts = header.decode("utf-8", errors="replace").split()
    if len(parts) != 2 or not all(part.lstrip("-").isdigit() for part in parts):
        raise ValueError(f"bad word2vec header: {header!r}")
    vocab_size = int(parts[0])
    dim = int(parts[1])
    if vocab_size < 0 or dim <= 0:
        raise ValueError(f"bad word2vec shape: vocab_size={vocab_size} dim={dim}")
    vector_bytes = dim * FLOAT32_BYTES
    for _ in range(vocab_size):
        word = _read_word2vec_word(handle)
        payload = handle.read(vector_bytes)
        if len(payload) != vector_bytes:
            raise ValueError("truncated word2vec vector")
        if word:
            yield word


def _read_word2vec_word(handle: BinaryIO) -> str:
    chunks: list[bytes] = []
    while True:
        ch = handle.read(1)
        if ch == b"":
            raise ValueError("unexpected EOF in word2vec word")
        if ch == b" ":
            break
        if ch != b"\n":
            chunks.append(ch)
    return b"".join(chunks).decode("utf-8", errors="replace")
