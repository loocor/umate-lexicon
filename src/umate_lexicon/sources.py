from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from umate_lexicon.paths import data_dir


class SourceLockError(ValueError):
    pass


# License ids are free text, so match substrings rather than a prefix:
# "GNU GPL v3", "Affero GPL" and the spelled-out names must all be caught.
_LGPL_HINTS = ("lgpl", "lessergeneralpubliclicense")
_AGPL_HINTS = ("agpl", "affero")
_GPL_HINTS = ("gpl", "generalpubliclicense")


def is_blocked_license(license_id: str) -> bool:
    compact = "".join(ch for ch in license_id.lower() if ch.isalnum())
    if any(hint in compact for hint in _LGPL_HINTS):
        return False
    if any(hint in compact for hint in _AGPL_HINTS):
        return True
    return any(hint in compact for hint in _GPL_HINTS)


@dataclass(frozen=True)
class ExtractSpec:
    kind: str
    output: str
    member: str | None = None
    input_encoding: str | None = None
    errors: str = "strict"
    max_lines: int | None = None


@dataclass(frozen=True)
class PinnedSource:
    id: str
    license: str
    url: str
    sha256: str
    filename: str
    ingest: str
    homepage: str | None = None
    extract: ExtractSpec | None = None

    def artifact_path(self, downloads_dir: Path) -> Path:
        return downloads_dir / self.filename

    def ingest_path(self, downloads_dir: Path) -> Path:
        if self.extract is None:
            return self.artifact_path(downloads_dir)
        return downloads_dir / self.extract.output


@dataclass(frozen=True)
class SourceLock:
    version: int
    sources: tuple[PinnedSource, ...]


ALLOWED_INGEST = frozenset({"unihan", "t2s", "tgh", "cedict", "thuocl", "luna", "essay", "emoji", "tencent", "wiki", "wiki_page", "wiki_linktarget", "wiki_category"})
ALLOWED_EXTRACT = frozenset({"gzip", "zip", "word2vec-vocab", "transcode"})


def default_lock_path() -> Path:
    return data_dir() / "sources.lock.json"


def default_downloads_dir() -> Path:
    return data_dir() / "sources" / "downloads"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def load_lock(path: Path | None = None) -> SourceLock:
    lock_path = path or default_lock_path()
    payload = json.loads(lock_path.read_text(encoding="utf-8"))
    version = payload.get("version")
    if version != 1:
        raise SourceLockError(f"unsupported lock version: {version!r} in {lock_path}")
    raw_sources = payload.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise SourceLockError(f"lock has no sources: {lock_path}")
    sources = tuple(_parse_source(item, lock_path) for item in raw_sources)
    return SourceLock(version=1, sources=sources)


def _parse_source(item: object, lock_path: Path) -> PinnedSource:
    if not isinstance(item, dict):
        raise SourceLockError(f"source entry is not an object in {lock_path}")
    required = ("id", "license", "url", "sha256", "filename", "ingest")
    missing = [key for key in required if key not in item]
    if missing:
        raise SourceLockError(f"source missing {missing} in {lock_path}")
    ingest = item["ingest"]
    if ingest not in ALLOWED_INGEST:
        raise SourceLockError(f"unknown ingest kind {ingest!r} in {lock_path}")
    license_id = str(item["license"])
    if is_blocked_license(license_id):
        raise SourceLockError(
            f"blocked GPL/AGPL license {license_id!r} for source {item['id']}"
        )
    extract_raw = item.get("extract")
    extract = None
    if extract_raw is not None:
        if not isinstance(extract_raw, dict):
            raise SourceLockError(f"extract is not an object for {item['id']}")
        kind = extract_raw.get("kind")
        output = extract_raw.get("output")
        if kind not in ALLOWED_EXTRACT:
            raise SourceLockError(f"unknown extract kind {kind!r} for {item['id']}")
        if not output:
            raise SourceLockError(f"extract.output required for {item['id']}")
        member = extract_raw.get("member")
        if kind == "zip" and not member:
            raise SourceLockError(f"extract.member required for zip source {item['id']}")
        input_encoding = extract_raw.get("input_encoding")
        if kind == "transcode" and not input_encoding:
            raise SourceLockError(f"extract.input_encoding required for transcode source {item['id']}")
        errors = str(extract_raw.get("errors", "strict"))
        if errors not in {"strict", "replace", "ignore"}:
            raise SourceLockError(f"unsupported extract.errors {errors!r} for {item['id']}")
        max_lines = extract_raw.get("max_lines")
        if max_lines is not None:
            if isinstance(max_lines, bool) or not isinstance(max_lines, int) or max_lines <= 0:
                raise SourceLockError(f"extract.max_lines must be a positive integer for {item['id']}")
        extract = ExtractSpec(
            kind=kind,
            output=str(output),
            member=None if member is None else str(member),
            input_encoding=None if input_encoding is None else str(input_encoding),
            errors=errors,
            max_lines=max_lines,
        )
    homepage = item.get("homepage")
    return PinnedSource(
        id=str(item["id"]),
        license=license_id,
        url=str(item["url"]),
        sha256=str(item["sha256"]).lower(),
        filename=str(item["filename"]),
        ingest=str(ingest),
        homepage=None if homepage is None else str(homepage),
        extract=extract,
    )


def verify_artifact(source: PinnedSource, downloads_dir: Path) -> Path:
    artifact = source.artifact_path(downloads_dir)
    if not artifact.is_file():
        raise SourceLockError(
            f"missing pinned dump {source.id}: {artifact} (run: python -m umate_lexicon fetch)"
        )
    digest = sha256_file(artifact)
    if digest != source.sha256:
        raise SourceLockError(
            f"hash mismatch for {source.id}: expected {source.sha256}, got {digest}"
        )
    return artifact


def verify_ingest_file(source: PinnedSource, downloads_dir: Path) -> Path:
    verify_artifact(source, downloads_dir)
    ingest_path = source.ingest_path(downloads_dir)
    if not ingest_path.is_file():
        raise SourceLockError(
            f"missing extracted dump {source.id}: {ingest_path} (run: python -m umate_lexicon fetch)"
        )
    return ingest_path

