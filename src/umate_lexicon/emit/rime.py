from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import shutil

from umate_lexicon.emit.aosp_en import emit_aosp_en
from umate_lexicon.ingest.emoji import emoji_opencc_sidecar
from umate_lexicon import layers as _layers
from umate_lexicon.layers import (
    COLD_ONLY_LAYERS,
    HOT_PROJECTED_LAYERS,
    HOT_STRUCTURAL_LAYERS,
    is_hot_projected,
    PACK_LAYERS,
    assign_layer,
    emit_weight,
)
from umate_lexicon.lemma import Lemma
from umate_lexicon.pinyin import sanitize_emit_code
from umate_lexicon.t2s import SimplifyFn
from umate_lexicon.store import LemmaStore

LATIN_SYLLABLES = [(ch, ch) for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
DIGIT_SYLLABLES = [
    ("0", "ling"),
    ("1", "yi"),
    ("1", "yao"),
    ("2", "er"),
    ("3", "san"),
    ("4", "si"),
    ("5", "wu"),
    ("6", "liu"),
    ("7", "qi"),
    ("8", "ba"),
    ("9", "jiu"),
]


_opencc_t2s: SimplifyFn | None = None
_opencc_loaded = False


def _load_opencc_t2s() -> SimplifyFn:
    """Load OpenCC t2s converter once; return identity on import failure."""
    global _opencc_t2s, _opencc_loaded
    if _opencc_loaded:
        return _opencc_t2s if _opencc_t2s is not None else (lambda s: s)
    _opencc_loaded = True
    try:
        from opencc import OpenCC
        cc = OpenCC("t2s")
        _opencc_t2s = cc.convert
    except ImportError:
        pass
    return _opencc_t2s if _opencc_t2s is not None else (lambda s: s)


def default_ranking_overrides_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "voimate" / "ranking-overrides.tsv"


def load_ranking_overrides(path: Path | None = None) -> dict[tuple[str, str], str]:
    """Map (surface, pinyin_plain) -> reason. Missing file => empty."""
    src = path if path is not None else default_ranking_overrides_path()
    rows: dict[tuple[str, str], str] = {}
    if not src.is_file():
        return rows
    for raw in src.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        surface, pinyin = parts[0].strip(), parts[1].strip()
        if surface and pinyin:
            rows[(surface, pinyin)] = parts[2].strip() if len(parts) > 2 else ""
    return rows


def apply_ranking_overrides(
    weights: dict[tuple[str, str], int],
    overrides: dict[tuple[str, str], str],
) -> int:
    """Raise each override just above the current same-pinyin peak. Returns applied count."""
    if not overrides:
        return 0
    by_py: dict[str, list[tuple[int, str]]] = {}
    for (surface, pinyin), weight in weights.items():
        by_py.setdefault(pinyin, []).append((weight, surface))
    applied = 0
    for (surface, pinyin), _reason in overrides.items():
        if (surface, pinyin) not in weights:
            continue
        group = by_py.get(pinyin) or []
        if not group:
            continue
        peak = max(weight for weight, _ in group)
        tied = [name for weight, name in group if weight == peak]
        current = weights[(surface, pinyin)]
        if current < peak or (current == peak and (len(tied) > 1 or tied != [surface])):
            weights[(surface, pinyin)] = peak + 1
            applied += 1
    return applied


def emit_rime(
    store: LemmaStore,
    out_dir: Path,
    version: str = "0.1.0",
    *,
    ranking_overrides: Path | None = None,
) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    to_simplified = _load_opencc_t2s()
    siblings: dict[str, list[Lemma]] = defaultdict(list)
    buckets: dict[str, list[Lemma]] = defaultdict(list)
    t2s_converted = 0
    deduped = 0
    best_by_key: dict[tuple[str, str], Lemma] = {}
    for raw_lemma in store.all_lemmas():
        fixed_surface = to_simplified(raw_lemma.surface)
        if fixed_surface != raw_lemma.surface:
            t2s_converted += 1
            lemma = Lemma(
                surface=fixed_surface,
                pinyin_plain=raw_lemma.pinyin_plain,
                pinyin_toned=raw_lemma.pinyin_toned,
                weight=raw_lemma.weight,
                status=raw_lemma.status,
                script=raw_lemma.script,
                categories=list(raw_lemma.categories),
                flags=list(raw_lemma.flags),
                entity_type=raw_lemma.entity_type,
                domain_freq=dict(raw_lemma.domain_freq),
                sources=list(raw_lemma.sources),
            )
        else:
            lemma = raw_lemma
        key = lemma.key()
        existing = best_by_key.get(key)
        if existing is not None:
            deduped += 1
            if lemma.weight > existing.weight:
                best_by_key[key] = lemma
            continue
        best_by_key[key] = lemma
    for lemma in best_by_key.values():
        siblings[lemma.surface].append(lemma)
        layer = assign_layer(lemma)
        if layer is None:
            continue
        buckets[layer].append(lemma)

    sanitized = 0
    dropped = 0
    for name, items in list(buckets.items()):
        cleaned: list[Lemma] = []
        for lemma in items:
            code = sanitize_emit_code(lemma.pinyin_plain)
            if code is None:
                dropped += 1
                continue
            if code != lemma.pinyin_plain:
                sanitized += 1
                lemma = Lemma(
                    surface=lemma.surface,
                    pinyin_plain=code,
                    pinyin_toned=lemma.pinyin_toned,
                    weight=lemma.weight,
                    status=lemma.status,
                    script=lemma.script,
                    categories=list(lemma.categories),
                    flags=list(lemma.flags),
                    entity_type=lemma.entity_type,
                    domain_freq=dict(lemma.domain_freq),
                    sources=list(lemma.sources),
                )
            cleaned.append(lemma)
        buckets[name] = cleaned

    counts = {name: len(items) for name, items in buckets.items()}
    counts["t2s_converted"] = t2s_converted
    counts["deduped"] = deduped
    counts["codes_sanitized"] = sanitized
    counts["codes_dropped"] = dropped
    weight_cache: dict[tuple[str, str], int] = {}
    for items in buckets.values():
        for lemma in items:
            key = (lemma.surface, lemma.pinyin_plain)
            if key not in weight_cache:
                weight_cache[key] = emit_weight(lemma, siblings.get(lemma.surface))
    override_path = ranking_overrides
    if override_path is None:
        default_path = default_ranking_overrides_path()
        override_path = default_path if default_path.is_file() else None
    applied = 0
    boosted: set[tuple[str, str]] = set()
    if override_path is not None:
        loaded = load_ranking_overrides(override_path)
        before = dict(weight_cache)
        applied = apply_ranking_overrides(weight_cache, loaded)
        boosted = {key for key, value in weight_cache.items() if before.get(key) != value}
    counts["ranking_overrides"] = applied
    _write_table(out_dir / "umate_chars.dict.yaml", "umate_chars", version, buckets.get("chars", []), siblings, weight_cache)
    _write_table(out_dir / "umate_base.dict.yaml", "umate_base", version, buckets.get("base", []), siblings, weight_cache)
    for pack in PACK_LAYERS:
        _write_table(
            out_dir / f"umate_{pack}.dict.yaml",
            f"umate_{pack}",
            version,
            buckets.get(pack, []),
            siblings,
            weight_cache,
        )
    _write_table(out_dir / "umate_emoji.dict.yaml", "umate_emoji", version, buckets.get("emoji", []), siblings, weight_cache)
    hot_tail = []
    for pack in HOT_PROJECTED_LAYERS:
        for lemma in buckets.get(pack, []):
            key = (lemma.surface, lemma.pinyin_plain)
            if key in boosted:
                if weight_cache[key] >= _layers.HOT_WEIGHT_FLOOR:
                    hot_tail.append(lemma)
            elif is_hot_projected(lemma, siblings.get(lemma.surface)):
                hot_tail.append(lemma)
    counts["hot_tail"] = len(hot_tail)
    _write_table(out_dir / "umate_hot_tail.dict.yaml", "umate_hot_tail", version, hot_tail, siblings, weight_cache)
    cold_only_enabled = COLD_ONLY_LAYERS if _layers.WIKI_TAIL_ENABLED else ()
    for layer in COLD_ONLY_LAYERS:
        stale = out_dir / f"umate_{layer}.dict.yaml"
        if not _layers.WIKI_TAIL_ENABLED and stale.exists():
            stale.unlink()
    if _layers.WIKI_TAIL_ENABLED:
        cold_only = [lemma for layer in cold_only_enabled for lemma in buckets.get(layer, [])]
        counts["wiki_tail"] = len(cold_only)
        for layer in cold_only_enabled:
            _write_table(
                out_dir / f"umate_{layer}.dict.yaml",
                f"umate_{layer}",
                version,
                buckets.get(layer, []),
                siblings,
            )
    _write_core(out_dir / "umate_hans.dict.yaml", version)
    _write_cold_core(out_dir / "umate_hans_cold.dict.yaml", version)
    _write_schema(out_dir / "umate_hans.schema.yaml")
    _write_emoji_opencc(out_dir, store)
    # AOSP artifacts must exist before NOTICE: the notice lists them by
    # filename, and a fresh emit dir has no files from a previous run.
    aosp_csv = _resolve_aosp_wordlist()
    if aosp_csv is not None:
        counts.update(emit_aosp_en(aosp_csv, out_dir))
    _write_notice(out_dir / "NOTICE", store)
    return counts


def _resolve_aosp_wordlist() -> Path | None:
    """Prefer pinned download extract, then downloads CSV, then fixture."""
    from umate_lexicon.paths import data_dir
    from umate_lexicon.sources import default_downloads_dir

    downloads = default_downloads_dir()
    for name in (
        "aosp_en_US_wordlist.csv",
        "en_US_wordlist.combined.csv",
    ):
        path = downloads / name
        if path.is_file():
            return path
    fixture = data_dir() / "fixtures" / "aosp_en_wordlist.csv"
    if fixture.is_file():
        return fixture
    return None


def _write_core(path: Path, version: str) -> None:
    lines = [
        "# Rime dictionary",
        "# encoding: utf-8",
        "# Generated by umate-lexicon. Do not hand-edit.",
        "# Hot every-key table: structural packs plus the weight projection",
        "# pack. Full fallback lives in umate_hans_cold.",
        "---",
        "name: umate_hans",
        f'version: "{version}"',
        "sort: by_weight",
        "use_preset_vocabulary: false",
        "import_tables:",
        "  - umate_chars",
        "  - umate_base",
        "  - umate_corrections",
        "  - umate_emoji",
        "  - umate_hot_tail",
        "...",
        "",
    ]
    for text, code in LATIN_SYLLABLES:
        lines.append(f"{text}\t{code}")
    for text, code in DIGIT_SYLLABLES:
        lines.append(f"{text}\t{code}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_cold_core(path: Path, version: str) -> None:
    packs = [
        "umate_chars",
        "umate_base",
        *(f"umate_{layer}" for layer in PACK_LAYERS),
        "umate_emoji",
        *(f"umate_{layer}" for layer in COLD_ONLY_LAYERS if _layers.WIKI_TAIL_ENABLED),
    ]
    lines = [
        "# Rime dictionary",
        "# encoding: utf-8",
        "# Generated by umate-lexicon. Do not hand-edit.",
        "# Cold full-fallback table: every emitable pack, drawer-only.",
        "---",
        "name: umate_hans_cold",
        f'version: "{version}"',
        "sort: by_weight",
        "use_preset_vocabulary: false",
        "import_tables:",
    ]
    lines.extend(f"  - {pack}" for pack in packs)
    lines.extend(["...", ""])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_table(
    path: Path,
    name: str,
    version: str,
    lemmas: list[Lemma],
    siblings: dict[str, list[Lemma]] | None = None,
    weights: dict[tuple[str, str], int] | None = None,
) -> None:
    lines = [
        "# Rime dictionary",
        "# encoding: utf-8",
        "# Generated by umate-lexicon. Do not hand-edit.",
        "---",
        f"name: {name}",
        f'version: "{version}"',
        "sort: by_weight",
        "use_preset_vocabulary: false",
        "columns:",
        "  - text",
        "  - code",
        "  - weight",
        "...",
        "",
    ]
    def weight_of(item: Lemma) -> int:
        if weights is not None:
            cached = weights.get((item.surface, item.pinyin_plain))
            if cached is not None:
                return cached
        group = None if siblings is None else siblings.get(item.surface)
        return emit_weight(item, group)

    ordered = sorted(lemmas, key=lambda item: (-weight_of(item), item.surface, item.pinyin_plain))
    for lemma in ordered:
        lines.append(f"{lemma.surface}\t{lemma.pinyin_plain}\t{weight_of(lemma)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_schema(path: Path) -> None:
    packs = "\n".join(f"    - umate_{name}" for name in PACK_LAYERS)
    path.write_text(
        f"""# Rime schema
# encoding: utf-8
# Generated by umate-lexicon. Wire this from uMate; do not copy rime-ice.

schema:
  schema_id: umate_hans
  name: uMate Hans
  version: "0.1.0"

engine:
  translators:
    - script_translator
    - table_translator@aosp_en

translator:
  dictionary: umate_hans
  packs:
{packs}
  enable_user_dict: false
""",
        encoding="utf-8",
    )


def _write_emoji_opencc(out_dir: Path, store: LemmaStore) -> None:
    sidecar = emoji_opencc_sidecar(store)
    if not sidecar.is_file():
        return
    dest_dir = out_dir / "opencc"
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(sidecar, dest_dir / "emoji_word.txt")
    (dest_dir / "NOTICE").write_text(
        "emoji_word.txt is generated from official rime/rime-emoji "
        "(LGPL-3.0). Do not enable simplifier@emoji_suggestion in the "
        "uMate keyboard schema unless that pack is explicitly selected.\n",
        encoding="utf-8",
    )


def _write_notice(path: Path, store: LemmaStore) -> None:
    licenses: dict[str, int] = defaultdict(int)
    for lemma in store.all_lemmas():
        for ref in lemma.sources:
            licenses[f"{ref.source_id} ({ref.license})"] += 1
    body = ["umate-lexicon emit NOTICE", ""]
    for key, count in sorted(licenses.items()):
        body.append(f"{key}: {count} lemmas")
    if (path.parent / "opencc" / "emoji_word.txt").is_file():
        body.append("emoji (lgpl-rime-emoji): opencc/emoji_word.txt")
    if (path.parent / "aosp_en.dict.yaml").is_file():
        body.append("aosp_en (apache-2.0-aosp-latinime): aosp_en.dict.yaml")
        body.append("en_us_unigrams (apache-2.0-aosp-latinime): en_us_unigrams.tsv")
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
