# Rime emit contract

Target: librime 1.16 dictionary source format.

A dict file is a YAML header between `---` and `...`, then tab-separated
rows: `text`, `code`, `weight`.

The hot table `umate_hans` imports `umate_chars`, `umate_base`,
`umate_corrections`, and `umate_hot_tail`.
`use_preset_vocabulary` stays `false`. `umate_hans_cold` imports every
emitable pack and is the drawer fallback, not the every-key table.
`umate_hot_tail` is the weight projection of the long-tail packs.

uMate wires schema ids `umate_pinyin`, `umate_pinyin_t9`, and
`umate_pinyin_14key` onto dictionary `umate_hans`. This factory emits
the dictionary sources. It does not own those schema ids.

Packs (librime ≥ 1.6) are extra `*.table.bin` files sharing the core
prism syllable table. The generated `umate_hans.schema.yaml` lists the
pack names for wiring; the keyboard schema is the product shell.

This repo emits **source YAML**. Binary compilation is a Host job in
VoiMate (`table.bin`, `prism.bin`, `reverse.bin`). The keyboard extension
must not run `start_maintenance`.

Alphabet digits belong in the core dict body. `A`–`Z` syllable rows are
emitted here for a *future* mixed-input schema only. VoiMate QWERTY
must not import those rows yet: Shift-letter still starts Chinese
composing.

Emit codes are sanitized in this factory (`sanitize_emit_code`): a–z /
digits / spaces only, erhua attached (`hui r` → `huir`), and lone
letters other than `a`/`o`/`e` collapsed or dropped. VoiMate must not
rewrite lemma rows on ingest.

The English table identity is `aosp_en` (Apache-2.0 AOSP LatinIME),
emitted beside the Chinese packs as `aosp_en.dict.yaml` plus
`en_us_unigrams.tsv` for the Swift EnglishLexicon truncation. It is not
a handmade `umate_en` patch. Chinese every-key paths may omit the Rime
`table_translator@aosp_en` wiring; ownership of the wordlist still
lives here.

## Emoji candidate channel

`umate_emoji.dict.yaml` is a standalone emoji candidate source, emitted
when composable Han triggers exist (`哈哈` → `ha ha` → 😂). The hot
`umate_hans` table never imports it, so an emoji weight can never take a
Chinese word slot by force (for example `qun`: 👗 must not outrank
群 / 裙). The table stays inside `umate_hans_cold` for the drawer
fallback, so emoji reachability survives without inline competition.
Weights inside `umate_emoji` rank emoji against emoji only; they never
compete with Chinese words.

`opencc/emoji_word.txt` is copied beside it. Neither is listed in
`translator/packs` and VoiMate must not enable
`simplifier@emoji_suggestion` until that SKU is explicitly chosen.

Host policy owns exposure: `off` (no emoji candidates), `inline` (at
most one emoji slot, never above the top Chinese words), or drawer-only
(default through `umate_hans_cold`). A dedicated emoji translator wired
from `umate_emoji` is the Host-side mechanism; this factory emits the
source table only.
The mapping comes from official `rime/rime-emoji` (LGPL-3.0), not from
rime-ice OpenCC recipes.
