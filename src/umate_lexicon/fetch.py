from __future__ import annotations

import gzip
import shutil
import urllib.request
import zipfile
from pathlib import Path

from umate_lexicon.cleanroom import assert_ingest_allowed
from umate_lexicon.sources import (
    PinnedSource,
    SourceLock,
    SourceLockError,
    default_downloads_dir,
    load_lock,
    sha256_file,
    verify_artifact,
)

USER_AGENT = "umate-lexicon/0.1 (+https://github.com/loocor/umate-lexicon)"


def fetch_locked_sources(
    lock: SourceLock | None = None,
    downloads_dir: Path | None = None,
) -> dict[str, str]:
    source_lock = lock or load_lock()
    dest = downloads_dir or default_downloads_dir()
    dest.mkdir(parents=True, exist_ok=True)
    results: dict[str, str] = {}
    for source in source_lock.sources:
        results[source.id] = fetch_one(source, dest)
    return results


def fetch_one(source: PinnedSource, downloads_dir: Path) -> str:
    artifact = source.artifact_path(downloads_dir)
    if artifact.is_file() and sha256_file(artifact) == source.sha256:
        status = "cached"
    else:
        _download(source.url, artifact)
        digest = sha256_file(artifact)
        if digest != source.sha256:
            raise SourceLockError(
                f"hash mismatch after download for {source.id}: "
                f"expected {source.sha256}, got {digest}"
            )
        status = "downloaded"
    verify_artifact(source, downloads_dir)
    ingest_path = _extract(source, downloads_dir)
    preview = ingest_path.read_text(encoding="utf-8-sig", errors="replace")[:4000]
    assert_ingest_allowed(ingest_path, preview)
    return status


def _download(url: str, dest: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    partial = dest.with_name(dest.name + ".partial")
    try:
        with urllib.request.urlopen(request) as response, partial.open("wb") as handle:
            shutil.copyfileobj(response, handle)
        partial.replace(dest)
    except Exception:
        if partial.exists():
            partial.unlink()
        raise


def _extract(source: PinnedSource, downloads_dir: Path) -> Path:
    ingest_path = source.ingest_path(downloads_dir)
    if source.extract is None:
        return ingest_path
    artifact = source.artifact_path(downloads_dir)
    if source.extract.kind == "gzip":
        with gzip.open(artifact, "rb") as src, ingest_path.open("wb") as out:
            shutil.copyfileobj(src, out)
        return ingest_path
    if source.extract.kind == "zip":
        member = source.extract.member
        if member is None:
            raise SourceLockError(f"zip extract missing member for {source.id}")
        with zipfile.ZipFile(artifact) as archive:
            if member not in archive.namelist():
                raise SourceLockError(
                    f"zip member {member!r} not in {artifact.name} for {source.id}"
                )
            ingest_path.write_bytes(archive.read(member))
        return ingest_path
    raise SourceLockError(f"unknown extract kind {source.extract.kind!r} for {source.id}")
