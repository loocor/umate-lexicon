from __future__ import annotations

import re

from umate_lexicon.lemma import Lemma

_HAN = re.compile(r"[\u4e00-\u9fff]")

CORE_LAYERS = ("chars", "base")
PACK_LAYERS = (
    "phrases",
    "ext",
    "names",
    "places",
    "brands",
    "orgs",
    "events",
    "mixed",
    "bulk",
    "corrections",
)
COVERAGE_SOURCE_IDS = frozenset({"wiki", "tencent"})
COVERAGE_FREQ_DOMAINS = frozenset({"wiki", "tencent"})

# Whole packs that ride the every-key hot table unconditionally.
HOT_STRUCTURAL_LAYERS = ("chars", "base", "corrections", "emoji")
# Long-tail packs whose rows ride hot only through the weight projection.
HOT_PROJECTED_LAYERS = (
    "phrases",
    "ext",
    "names",
    "places",
    "brands",
    "orgs",
    "events",
    "mixed",
    "bulk",
)
# Essay-scale floor, same family as PHRASE_HOT_FREQ / BASE_AUTO_FREQ.
# 2026-09-19: 1000 -> 450. Dry-run showed the 350-499 band has negligible
# same-length collision degradation (exclusive rate 70% vs 67% at 500) and
# the essay 2-char fragment guard below absorbs the real cross-length
# interference.
HOT_WEIGHT_FLOOR = 450
# Essay collocation n-grams strictly below this weight that are exactly 2
# han chars are sentence fragments (e.g. 地笑 from 傻傻地笑), not dictionary
# words. They must not enter the hot projection because they steal the
# syllable pair from char-by-char composition and break sentence ranking.
# Non-essay 2-char words (cedict/luna/thuocl/tencent real words) are
# unaffected.
HOT_TWO_CHAR_ESSAY_FLOOR = 500
# Layers that never ride the every-key hot table.
COLD_ONLY_LAYERS = ("wiki_tail",)
# Product policy (2026-09-18): the wiki-only long tail is paused; tencent
# light coverage rides bulk instead. Flip to True to re-enable the
# cold-only wiki tail pack.
WIKI_TAIL_ENABLED = False
# Cold weight for wiki-only typed entries (person / place / org / work)
# routed into their named packs. Intentionally below HOT_WEIGHT_FLOOR so
# they ride the cold fallback table only: findable by long-code lookup,
# never competing with essay-ranked hot candidates. The 694k untyped
# wiki-only rows stay in wiki_tail (disabled) and are not emitted.
# 2026-09-19 policy.
WIKI_COLD_WEIGHT = 100
# 2026-09-19: page_len notability tiers for wiki-only entries.
# Generated from zhwiki-20260901-page.sql.gz into
# data/sources/wiki_page_weights.tsv. Entries at or above the hot floor
# enter the hot projection; the rest stay cold with elevated or base
# weight.
WIKI_PAGE_WEIGHT_TIERS: tuple[tuple[int, int], ...] = (
    (30000, 1000),
    (10000, 600),
    (5000, 450),
    (2000, 150),
    (0, 100),
)
_wiki_page_weights: dict[str, int] | None = None
_polyphone_chars: frozenset[str] | None = None
_TRUSTED_CHAR_SOURCES = frozenset({"gold", "cedict", "unihan"})


def _load_wiki_page_weights() -> dict[str, int]:
    global _wiki_page_weights
    if _wiki_page_weights is not None:
        return _wiki_page_weights
    from umate_lexicon.paths import data_dir

    path = data_dir() / "sources" / "wiki_page_weights.tsv"
    weights: dict[str, int] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                try:
                    weights[parts[0]] = int(parts[2])
                except ValueError:
                    pass
    _wiki_page_weights = weights
    return weights



def polyphone_chars() -> frozenset[str]:
    """Closed-set characters from gold/polyphones.tsv. Not a layer."""
    global _polyphone_chars
    if _polyphone_chars is not None:
        return _polyphone_chars
    from umate_lexicon.paths import data_dir

    path = data_dir() / "gold" / "polyphones.tsv"
    chars: list[str] = []
    if path.is_file():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            chars.append(line.split("\t")[0])
    _polyphone_chars = frozenset(chars)
    return _polyphone_chars


def _trusted_char_reading(lemma: Lemma) -> bool:
    """Gold, CC-CEDICT, Unihan, or kHanyuPinlu. Luna-only stays untrusted."""
    if "hanyu_pinlu" in lemma.flags:
        return True
    return any(ref.source_id in _TRUSTED_CHAR_SOURCES for ref in lemma.sources)


def wiki_page_weight(surface: str) -> int | None:
    """Policy weight for a wiki title, or None if the title is absent."""
    return _load_wiki_page_weights().get(surface)


# Essay 4+ grams at or above this ranking_freq ride the hot phrase pack so
# long common phrases participate in every-key sentence ranking.
PHRASE_HOT_FREQ = 1000
# Auto 2–3 char lemmas need luna or this essay-scale floor to stay in hot base;
# weaker CEDICT/essay noise (涡核 / 沃德) demotes to cold bulk.
BASE_AUTO_FREQ = 1000
BASE_CEDICT_FREQ = 500


def han_len(surface: str) -> int:
    return len(_HAN.findall(surface))


def is_wiki_only(lemma: Lemma) -> bool:
    return {ref.source_id for ref in lemma.sources} == {"wiki"}


def is_coverage_only(lemma: Lemma) -> bool:
    ids = {ref.source_id for ref in lemma.sources}
    return bool(ids) and ids <= COVERAGE_SOURCE_IDS


def ranking_freq(lemma: Lemma) -> int:
    ranked = sum(
        count for domain, count in lemma.domain_freq.items() if domain not in COVERAGE_FREQ_DOMAINS
    )
    if ranked:
        return ranked
    return lemma.weight


def emit_weight(lemma: Lemma) -> int:
    """Value for the Rime `weight` column.

    librime stores this column as `log(weight)` at compile time
    (`dict_compiler.cc`) and subtracts `log(1e8)` at query time, so the
    column is a raw frequency on a 1e8 scale -- the same scale rime-essay
    counts already use. Compressing it here would flatten the distribution
    and let a rare entry compete with a common one.

    Wiki-only typed entries (person / place / org / work) carry a flat
    cold weight: enough to surface in the cold fallback table, never
    enough to enter the hot projection or outrank essay-ranked entries.
    """
    w = max(1, ranking_freq(lemma))
    if w <= 1 and is_wiki_only(lemma):
        page_w = wiki_page_weight(lemma.surface)
        if page_w is not None:
            return max(page_w, WIKI_COLD_WEIGHT)
        if _wiki_typed_pack(lemma) is not None:
            return WIKI_COLD_WEIGHT
    return w


def _wiki_typed_pack(lemma: Lemma) -> str | None:
    """Pack for wiki-only entries with a known entity_type, else None."""
    if lemma.entity_type == "person" or "person" in lemma.categories:
        return "names"
    if lemma.entity_type == "place" or "place" in lemma.categories:
        return "places"
    if lemma.entity_type in {"org", "industry"} or "org" in lemma.categories:
        return "orgs"
    if lemma.entity_type == "work" or "work" in lemma.categories:
        return "ext"
    return None


def assign_layer(lemma: Lemma) -> str | None:
    if lemma.status == "rejected":
        return None
    if "untrusted_reading" in lemma.flags:
        return None
    if "emoji" in lemma.flags or lemma.entity_type == "emoji" or "emoji" in lemma.categories:
        return "emoji"
    if "correction" in lemma.flags:
        return "corrections"
    if is_wiki_only(lemma):
        # 2026-09-19: wiki-only entries with a known entity_type ride the
        # corresponding named pack at cold weight, so long-code lookup can
        # find them. Untyped wiki-only rows with a page_len weight at or
        # above the hot floor ride bulk (long-tail catch-all); the rest
        # stay in wiki_tail (disabled by default) as coverage evidence.
        typed = _wiki_typed_pack(lemma)
        if typed is not None:
            return typed
        page_w = wiki_page_weight(lemma.surface)
        if page_w is not None and page_w >= HOT_WEIGHT_FLOOR:
            return "bulk"
        return "wiki_tail" if WIKI_TAIL_ENABLED else None
    if is_coverage_only(lemma):
        return "bulk"
    if lemma.entity_type == "person" or "person" in lemma.categories:
        return "names"
    if lemma.entity_type == "place" or "place" in lemma.categories:
        return "places"
    if lemma.entity_type == "brand" or "brand" in lemma.categories or "mixed_latin" in lemma.flags:
        if "mixed_latin" in lemma.flags:
            return "mixed"
        return "brands"
    if lemma.entity_type in {"org", "industry"} or "org" in lemma.categories:
        return "orgs"
    if lemma.entity_type == "event" or "event" in lemma.categories:
        return "events"
    n = han_len(lemma.surface)
    if n == 0:
        if lemma.status == "gold":
            return "brands"
        return None
    if n == 1:
        if (
            lemma.status == "gold"
            or "tgh" in lemma.flags
            or "hanyu_pinlu" in lemma.flags
            or any(ref.source_id == "chars" for ref in lemma.sources)
            or (lemma.surface in polyphone_chars() and _trusted_char_reading(lemma))
        ):
            return "chars"
        return None
    if n in {2, 3} and lemma.status == "gold":
        return "base"
    # review is scrutiny, not a hard emit ban — high-freq short lemmas share
    # the auto short-layer gate (带着 / 拿着 and similar aspect bigrams).
    if n in {2, 3} and lemma.status in {"auto", "review"}:
        return _auto_short_layer(lemma, n)
    rf = ranking_freq(lemma)
    if n >= 4 and (lemma.status == "gold" or rf >= PHRASE_HOT_FREQ):
        return "phrases"
    if n == 4:
        return "ext"
    if "polyphone" in lemma.flags and lemma.status not in {"gold", "auto"}:
        return None
    return "bulk"


def _auto_short_layer(lemma: Lemma, n: int) -> str:
    rf = ranking_freq(lemma)
    source_ids = {ref.source_id for ref in lemma.sources}
    if "luna" in source_ids or rf >= BASE_AUTO_FREQ:
        return "base"
    if "cedict" in source_ids and rf >= BASE_CEDICT_FREQ:
        return "base"
    if n == 3 and rf >= BASE_CEDICT_FREQ:
        return "base"
    # Explicit weak mass signal (essay/cedict/thuocl below floor) → cold bulk.
    # Lemmas with no mass freq keep prior hot-base behavior.
    if rf > 0 and source_ids & {"essay", "cedict", "thuocl"}:
        return "bulk"
    return "base"


def _is_essay_two_char_fragment(lemma: Lemma) -> bool:
    """Essay-only 2-char collocation fragment below the fragment floor."""
    if len(lemma.surface) != 2:
        return False
    if emit_weight(lemma) >= HOT_TWO_CHAR_ESSAY_FLOOR:
        return False
    return any(ref.source_id == "essay" for ref in lemma.sources)


def is_hot_projected(lemma: Lemma) -> bool:
    """Weight-projection predicate for long-tail packs, with the essay
    2-char fragment guard."""
    return emit_weight(lemma) >= HOT_WEIGHT_FLOOR and not _is_essay_two_char_fragment(lemma)


def is_hot_member(lemma: Lemma) -> bool:
    """Whether the lemma rides the every-key hot table.

    Structural layers (chars/base/corrections/emoji) ride hot wholesale.
    Every other emitable layer is a pure weight projection at or above
    HOT_WEIGHT_FLOOR, so long-tail frequency -- not category membership --
    decides hot presence. Cold-only layers never ride hot.
    """
    layer = assign_layer(lemma)
    if layer is None or layer in COLD_ONLY_LAYERS:
        return False
    if layer in HOT_STRUCTURAL_LAYERS:
        return True
    return is_hot_projected(lemma)
