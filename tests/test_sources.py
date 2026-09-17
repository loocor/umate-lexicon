import gzip
import hashlib
import json
import struct
from pathlib import Path

import pytest

from umate_lexicon.fetch import fetch_locked_sources
from umate_lexicon.pipeline import run_locked_pipeline
from umate_lexicon.sources import SourceLockError, load_lock, sha256_file, verify_ingest_file
from umate_lexicon.store import LemmaStore


def _write(path: Path, body: str) -> str:
    path.write_text(body, encoding="utf-8")
    return sha256_file(path)


def _lock(downloads: Path, sources: list[dict]) -> Path:
    lock_path = downloads / "sources.lock.json"
    lock_path.write_text(json.dumps({"version": 1, "sources": sources}), encoding="utf-8")
    return lock_path


def test_repo_lock_version_and_kinds() -> None:
    lock = load_lock()
    assert lock.version == 1
    kinds = {source.ingest for source in lock.sources}
    assert {
        "unihan",
        "t2s",
        "tgh",
        "cedict",
        "thuocl",
        "luna",
        "essay",
        "emoji",
        "wiki",
        "wiki_page",
        "wiki_linktarget",
        "wiki_category",
        "tencent",
    } <= kinds
    assert "rime-ice" not in kinds
    assert any(source.id == "unihan" for source in lock.sources)
    assert any(source.id == "cedict" for source in lock.sources)
    tencent = next(source for source in lock.sources if source.id == "tencent-light")
    assert tencent.ingest == "tencent"
    assert tencent.license == "cc-by-3.0-tencent"
    assert tencent.sha256 == "5515923c7e67cdc7eb42996546e0bad273c8452f3bfad6db0794e51c848d151b"
    assert tencent.filename == "light_Tencent_AILab_ChineseEmbedding.bin"
    assert "modelscope.cn" in tencent.url
    assert tencent.url.endswith("light_Tencent_AILab_ChineseEmbedding.bin")
    assert tencent.homepage is not None
    assert "tencent" in tencent.homepage.lower() or "ailab" in tencent.homepage.lower()
    assert tencent.extract is not None
    assert tencent.extract.kind == "word2vec-vocab"
    assert tencent.extract.output == "tencent-light-vocab.txt"
    ids = [source.id for source in lock.sources]
    assert ids.index("tencent-light") > ids.index("zhwiki-categorylinks")


def test_hash_mismatch_is_hard_failure(tmp_path: Path) -> None:
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    digest = _write(downloads / "cedict.txt", "你好 你好 [ni3 hao3] /hello/\n")
    lock_path = _lock(
        tmp_path,
        [
            {
                "id": "cedict",
                "license": "cc-by-sa-cedict",
                "url": "https://example.invalid/cedict.txt",
                "sha256": digest,
                "filename": "cedict.txt",
                "ingest": "cedict",
            }
        ],
    )
    (downloads / "cedict.txt").write_text("tampered\n", encoding="utf-8")
    lock = load_lock(lock_path)
    with pytest.raises(SourceLockError, match="hash mismatch"):
        verify_ingest_file(lock.sources[0], downloads)


def test_missing_dump_is_hard_failure(tmp_path: Path) -> None:
    lock_path = _lock(
        tmp_path,
        [
            {
                "id": "unihan",
                "license": "unicode",
                "url": "https://example.invalid/unihan.txt",
                "sha256": "0" * 64,
                "filename": "unihan.txt",
                "ingest": "unihan",
            }
        ],
    )
    lock = load_lock(lock_path)
    with pytest.raises(SourceLockError, match="missing pinned dump"):
        verify_ingest_file(lock.sources[0], tmp_path / "downloads")


def test_gpl_and_agpl_licenses_are_blocked(tmp_path: Path) -> None:
    for license_id in (
        "gpl-3.0-only",
        "AGPL-3.0-or-later",
        "gplv3",
        "GNU GPL v3",
        "GNU General Public License v3.0",
        "GNU Affero General Public License v3.0",
        "Affero GPL",
    ):
        lock_path = _lock(
            tmp_path,
            [
                {
                    "id": "blocked",
                    "license": license_id,
                    "url": "https://example.invalid/blocked.txt",
                    "sha256": "0" * 64,
                    "filename": "blocked.txt",
                    "ingest": "cedict",
                }
            ],
        )
        with pytest.raises(SourceLockError, match="blocked GPL/AGPL license"):
            load_lock(lock_path)


@pytest.mark.parametrize("license_id", ["lgpl-rime-essay", "LGPL-3.0", "Lesser General Public License"])
def test_lgpl_is_not_treated_as_gpl(tmp_path: Path, license_id: str) -> None:
    lock_path = _lock(
        tmp_path,
        [
            {
                "id": "essay",
                "license": license_id,
                "url": "https://example.invalid/essay.txt",
                "sha256": "0" * 64,
                "filename": "essay.txt",
                "ingest": "essay",
            }
        ],
    )
    lock = load_lock(lock_path)
    assert lock.sources[0].license == license_id


def test_unknown_ingest_kind_rejected(tmp_path: Path) -> None:
    lock_path = _lock(
        tmp_path,
        [
            {
                "id": "ice",
                "license": "gpl",
                "url": "https://example.invalid/ice.txt",
                "sha256": "0" * 64,
                "filename": "ice.txt",
                "ingest": "rime-ice",
            }
        ],
    )
    with pytest.raises(SourceLockError, match="unknown ingest kind"):
        load_lock(lock_path)


def test_fetch_extracts_gzip_and_verifies(tmp_path: Path) -> None:
    raw = "# CC-CEDICT sample\n你好 你好 [ni3 hao3] /hello/\n"
    gz_path = tmp_path / "cedict.txt.gz"
    gz_path.write_bytes(gzip.compress(raw.encode("utf-8")))
    digest = sha256_file(gz_path)
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    (downloads / "cedict.txt.gz").write_bytes(gz_path.read_bytes())
    lock_path = _lock(
        tmp_path,
        [
            {
                "id": "cedict",
                "license": "cc-by-sa-cedict",
                "url": "https://example.invalid/cedict.txt.gz",
                "sha256": digest,
                "filename": "cedict.txt.gz",
                "ingest": "cedict",
                "extract": {"kind": "gzip", "output": "cedict_ts.u8"},
            }
        ],
    )
    lock = load_lock(lock_path)
    results = fetch_locked_sources(lock=lock, downloads_dir=downloads)
    assert results["cedict"] == "cached"
    extracted = downloads / "cedict_ts.u8"
    assert extracted.read_text(encoding="utf-8") == raw


def _write_word2vec_binary(path: Path, items: list[tuple[str, list[float]]]) -> None:
    dim = len(items[0][1])
    with path.open("wb") as handle:
        handle.write(f"{len(items)} {dim}\n".encode("ascii"))
        for word, vector in items:
            handle.write(word.encode("utf-8") + b" ")
            handle.write(struct.pack("<" + "f" * dim, *vector))
            handle.write(b"\n")


def test_fetch_extracts_word2vec_vocab_without_vectors(tmp_path: Path) -> None:
    artifact = tmp_path / "downloads" / "light.bin"
    artifact.parent.mkdir()
    _write_word2vec_binary(
        artifact,
        [("微信", [0.12, -0.03]), ("人工智能", [1.0, 2.0]), ("银行卡", [0.0, 0.5])],
    )
    digest = sha256_file(artifact)
    lock_path = _lock(
        tmp_path,
        [
            {
                "id": "tencent-light",
                "license": "cc-by-3.0-tencent",
                "homepage": "https://ai.tencent.com/ailab/nlp/en/embedding.html",
                "url": "https://example.invalid/light.bin",
                "sha256": digest,
                "filename": "light.bin",
                "ingest": "tencent",
                "extract": {"kind": "word2vec-vocab", "output": "tencent-light-vocab.txt"},
            }
        ],
    )
    lock = load_lock(lock_path)
    results = fetch_locked_sources(lock=lock, downloads_dir=artifact.parent)
    assert results["tencent-light"] == "cached"
    vocab = (artifact.parent / "tencent-light-vocab.txt").read_text(encoding="utf-8")
    assert vocab.splitlines() == ["微信", "人工智能", "银行卡"]
    assert "0.12" not in vocab
    assert "143613" not in vocab


def test_locked_pipeline_uses_verified_dumps(tmp_path: Path) -> None:
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    unihan = "U+4F60\tkMandarin\tNǏ\nU+597D\tkMandarin\tHǍO\n"
    cedict = "你好 你好 [ni3 hao3] /hello/\n重慶 重庆 [chong2 qing4] /Chongqing/\n"
    thuocl = "你好\t9\n"
    sources = [
        {
            "id": "unihan",
            "license": "unicode",
            "url": "https://example.invalid/unihan.txt",
            "sha256": _write(downloads / "unihan.txt", unihan),
            "filename": "unihan.txt",
            "ingest": "unihan",
        },
        {
            "id": "cedict",
            "license": "cc-by-sa-cedict",
            "url": "https://example.invalid/cedict.txt",
            "sha256": _write(downloads / "cedict.txt", cedict),
            "filename": "cedict.txt",
            "ingest": "cedict",
        },
        {
            "id": "thuocl-it",
            "license": "mit-thuocl",
            "url": "https://example.invalid/THUOCL_IT.txt",
            "sha256": _write(downloads / "THUOCL_IT.txt", thuocl),
            "filename": "THUOCL_IT.txt",
            "ingest": "thuocl",
        },
        {
            "id": "luna",
            "license": "lgpl-rime-luna",
            "url": "https://example.invalid/luna.dict.yaml",
            "sha256": _write(
                downloads / "luna.dict.yaml",
                "---\nname: luna_pinyin\n...\n\n你好\tni hao\n",
            ),
            "filename": "luna.dict.yaml",
            "ingest": "luna",
        },
        {
            "id": "essay",
            "license": "lgpl-rime-essay",
            "url": "https://example.invalid/essay.txt",
            "sha256": _write(downloads / "essay.txt", "你好\t9\n"),
            "filename": "essay.txt",
            "ingest": "essay",
        },
        {
            "id": "emoji",
            "license": "lgpl-rime-emoji",
            "url": "https://example.invalid/emoji_word.txt",
            "sha256": _write(downloads / "emoji_word.txt", "哈哈\t哈哈 😂\n"),
            "filename": "emoji_word.txt",
            "ingest": "emoji",
        },
    ]
    lock_path = _lock(tmp_path, sources)
    stats = run_locked_pipeline(
        store_path=tmp_path / "lemmas.sqlite",
        out_dir=tmp_path / "rime",
        lock_path=lock_path,
        downloads_dir=downloads,
    )
    assert stats["eval_failures"] == 0
    assert stats["cedict"] >= 1
    store = LemmaStore(tmp_path / "lemmas.sqlite")
    hello = store.get("你好", "ni hao")
    assert hello is not None
    store.close()


def test_locked_pipeline_can_skip_unverified_source(tmp_path: Path) -> None:
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    unihan = "U+4F60\tkMandarin\tNǏ\nU+597D\tkMandarin\tHǍO\n"
    cedict = "你好 你好 [ni3 hao3] /hello/\n重慶 重庆 [chong2 qing4] /Chongqing/\n"
    sources = [
        {
            "id": "unihan",
            "license": "unicode",
            "url": "https://example.invalid/unihan.txt",
            "sha256": _write(downloads / "unihan.txt", unihan),
            "filename": "unihan.txt",
            "ingest": "unihan",
        },
        {
            "id": "cedict",
            "license": "cc-by-sa-cedict",
            "url": "https://example.invalid/cedict.txt",
            "sha256": _write(downloads / "cedict.txt", cedict),
            "filename": "cedict.txt",
            "ingest": "cedict",
        },
        {
            "id": "emoji",
            "license": "lgpl-rime-emoji",
            "url": "https://example.invalid/emoji_word.txt",
            "sha256": "cd" * 32,
            "filename": "emoji_word.txt",
            "ingest": "emoji",
        },
    ]
    lock_path = _lock(tmp_path, sources)
    stats = run_locked_pipeline(
        store_path=tmp_path / "lemmas.sqlite",
        out_dir=tmp_path / "rime",
        lock_path=lock_path,
        downloads_dir=downloads,
        skip_ids={"emoji"},
    )
    assert stats["eval_failures"] == 0
    assert stats["skipped_emoji"] == 0
    assert "emoji" not in stats
    assert stats["cedict"] >= 1
