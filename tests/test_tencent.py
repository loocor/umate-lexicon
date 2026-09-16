import gzip
import importlib.util
import struct
import tarfile
from pathlib import Path

import pytest

from umate_lexicon.ingest.chars import ingest_chars
from umate_lexicon.ingest.gold import ingest_gold
from umate_lexicon.ingest.tencent import ingest_tencent, parse_tencent_line
from umate_lexicon.paths import data_dir
from umate_lexicon.store import LemmaStore
from umate_lexicon.word2vec import extract_word2vec_vocab, iter_word2vec_vocab


def _write_word2vec_bin(path: Path, words: list[str], dim: int = 2) -> Path:
    path.write_bytes(_word2vec_bytes(words, dim))
    return path


def _word2vec_bytes(words: list[str], dim: int = 2) -> bytes:
    payload = f"{len(words)} {dim}\n".encode("utf-8")
    zeros = struct.pack(f"<{dim}f", *([0.0] * dim))
    for word in words:
        payload += word.encode("utf-8") + b" " + zeros
    return payload


def _extract_script():
    path = Path(__file__).resolve().parents[1] / "scripts" / "extract-tencent-vocab.py"
    spec = importlib.util.spec_from_file_location("extract_tencent_vocab", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parses_freq_and_embedding_lines() -> None:
    assert parse_tencent_line("微信\t100") == ("微信", 100)
    assert parse_tencent_line("人工智能 0.12 -0.03 0.44") == ("人工智能", 1)
    assert parse_tencent_line("xyz") == ("xyz", 1)


def test_covers_unique_han_and_overlays_gold_latin(tmp_path: Path) -> None:
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    ingest_gold(store, data_dir() / "gold" / "product-terms.tsv")
    ingest_chars(store, data_dir() / "fixtures" / "chars.tsv")
    count = ingest_tencent(store, data_dir() / "fixtures" / "tencent.txt")
    assert count >= 2
    weixin = store.get("微信", "wei xin")
    assert weixin is not None
    assert weixin.domain_freq["tencent"] == 100
    ai = store.get("人工智能", "ren gong zhi neng")
    assert ai is not None
    assert ai.domain_freq["tencent"] == 1
    assert store.get("的", "de") is None or "tencent" not in (store.get("的", "de").domain_freq)
    vector = store.get("向量数据库", "xiang liang shu ju ku")
    assert vector is not None
    assert vector.status == "gold"
    assert vector.domain_freq["tencent"] == 3
    brand = store.get("umate", "umate")
    assert brand is not None
    assert brand.domain_freq["tencent"] == 8
    store.close()


def test_word2vec_binary_extracts_vocab_only(tmp_path: Path) -> None:
    words = ["的", "微信", "抖音", "人工智能"]
    bin_path = _write_word2vec_bin(tmp_path / "light.bin", words, dim=200)
    assert list(iter_word2vec_vocab(bin_path)) == words
    vocab = tmp_path / "tencent-vocab.txt"
    extract_word2vec_vocab(bin_path, vocab)
    assert vocab.read_text(encoding="utf-8").splitlines() == words


def test_word2vec_skips_newlines_between_entries(tmp_path: Path) -> None:
    zeros = struct.pack("<2f", 0.0, 0.0)
    path = tmp_path / "spaced.bin"
    path.write_bytes(b"2 2\nwei " + zeros + b"\nxin " + zeros)
    assert list(iter_word2vec_vocab(path)) == ["wei", "xin"]


def test_word2vec_binary_rejects_truncated_payload(tmp_path: Path) -> None:
    path = tmp_path / "truncated.bin"
    path.write_bytes(b"2 2\nwei " + struct.pack("<2f", 0.0, 0.0))
    with pytest.raises(ValueError, match="unexpected EOF|truncated"):
        list(iter_word2vec_vocab(path))


def test_word2vec_binary_rejects_html_header(tmp_path: Path) -> None:
    path = tmp_path / "official.html.bin"
    path.write_bytes(b"<!DOCTYPE html>\n<html>not a dump</html>\n")
    with pytest.raises(ValueError, match="bad word2vec header"):
        list(iter_word2vec_vocab(path))


def test_extract_script_reads_word2vec_and_text(tmp_path: Path) -> None:
    script = _extract_script()
    words = ["的", "微信", "抖音", "人工智能"]
    bin_path = _write_word2vec_bin(tmp_path / "light_Tencent_AILab_ChineseEmbedding.bin", words)
    out_bin = tmp_path / "from-bin.txt"
    assert script.main([str(bin_path), "-o", str(out_bin)]) == 0
    assert out_bin.read_text(encoding="utf-8").splitlines() == words

    text_path = tmp_path / "tencent.txt"
    text_path.write_text("微信\t100\n人工智能 0.1 0.2\n", encoding="utf-8")
    out_text = tmp_path / "from-text.txt"
    assert script.main([str(text_path), "-o", str(out_text)]) == 0
    assert out_text.read_text(encoding="utf-8").splitlines() == ["微信", "人工智能"]

    gz_path = tmp_path / "tencent.txt.gz"
    gz_path.write_bytes(gzip.compress("抖音\n".encode("utf-8")))
    out_gz = tmp_path / "from-gz.txt"
    assert script.main([str(gz_path), "-o", str(out_gz)]) == 0
    assert out_gz.read_text(encoding="utf-8").splitlines() == ["抖音"]

    tar_path = tmp_path / "tencent.tar.gz"
    with tarfile.open(tar_path, "w:gz") as archive:
        inner = tmp_path / "inner.bin"
        _write_word2vec_bin(inner, ["微信"])
        archive.add(inner, arcname="inner.bin")
    out_tar = tmp_path / "from-tar.txt"
    assert script.main([str(tar_path), "-o", str(out_tar)]) == 0
    assert out_tar.read_text(encoding="utf-8").splitlines() == ["微信"]

    raw_bin = _word2vec_bytes(["抖音"])
    bin_gz = tmp_path / "light.bin.gz"
    bin_gz.write_bytes(gzip.compress(raw_bin))
    out_bin_gz = tmp_path / "from-bin-gz.txt"
    assert script.main([str(bin_gz), "-o", str(out_bin_gz)]) == 0
    assert out_bin_gz.read_text(encoding="utf-8").splitlines() == ["抖音"]

    untitled = tmp_path / "no-suffix"
    untitled.write_bytes(raw_bin)
    out_forced = tmp_path / "from-forced.txt"
    assert script.main([str(untitled), "--binary", "-o", str(out_forced)]) == 0
    assert out_forced.read_text(encoding="utf-8").splitlines() == ["抖音"]


def test_word2vec_vocab_feeds_tencent_ingest(tmp_path: Path) -> None:
    bin_path = _write_word2vec_bin(tmp_path / "light.bin", ["微信", "人工智能"])
    vocab = tmp_path / "tencent-vocab.txt"
    extract_word2vec_vocab(bin_path, vocab)
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    ingest_gold(store, data_dir() / "gold" / "product-terms.tsv")
    ingest_chars(store, data_dir() / "fixtures" / "chars.tsv")
    count = ingest_tencent(store, vocab)
    assert count >= 2
    weixin = store.get("微信", "wei xin")
    assert weixin is not None
    assert weixin.domain_freq["tencent"] == 1
    ai = store.get("人工智能", "ren gong zhi neng")
    assert ai is not None
    assert ai.domain_freq["tencent"] == 1
    store.close()
