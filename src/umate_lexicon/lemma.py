from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


ALLOWED_STATUS = frozenset({"gold", "auto", "review", "rejected"})


@dataclass(frozen=True)
class SourceRef:
    source_id: str
    license: str
    locator: str


@dataclass
class Lemma:
    surface: str
    pinyin_plain: str
    pinyin_toned: str | None = None
    weight: int = 0
    status: str = "auto"
    script: str = "hans"
    categories: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    entity_type: str | None = None
    domain_freq: dict[str, int] = field(default_factory=dict)
    sources: list[SourceRef] = field(default_factory=list)

    def key(self) -> tuple[str, str]:
        return (self.surface, self.pinyin_plain)

    def merge(self, other: Lemma) -> Lemma:
        if self.key() != other.key():
            raise ValueError("cannot merge lemmas with different keys")
        status = _stronger_status(self.status, other.status)
        categories = _unique(self.categories + other.categories)
        flags = _unique(self.flags + other.flags)
        sources = _unique_sources(self.sources + other.sources)
        domain = dict(self.domain_freq)
        for name, count in other.domain_freq.items():
            domain[name] = domain.get(name, 0) + count
        toned = self.pinyin_toned or other.pinyin_toned
        entity = self.entity_type or other.entity_type
        return Lemma(
            surface=self.surface,
            pinyin_plain=self.pinyin_plain,
            pinyin_toned=toned,
            weight=max(self.weight, other.weight),
            status=status,
            script=self.script,
            categories=categories,
            flags=flags,
            entity_type=entity,
            domain_freq=domain,
            sources=sources,
        )


def _stronger_status(a: str, b: str) -> str:
    rank = {"rejected": 0, "review": 1, "auto": 2, "gold": 3}
    if a not in rank or b not in rank:
        raise ValueError(f"unknown status: {a!r} {b!r}")
    # rejected always wins: a blocked source must not be laundered
    if a == "rejected" or b == "rejected":
        return "rejected"
    return a if rank[a] >= rank[b] else b


def _unique(values: Iterable[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen


def _unique_sources(values: Iterable[SourceRef]) -> list[SourceRef]:
    seen: list[SourceRef] = []
    keys: set[tuple[str, str, str]] = set()
    for ref in values:
        key = (ref.source_id, ref.license, ref.locator)
        if key in keys:
            continue
        keys.add(key)
        seen.append(ref)
    return seen
