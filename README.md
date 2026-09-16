# umate-lexicon

A **lexicon factory** for [uMate](https://github.com): licensed public
corpora in, a versioned lemma store in the middle, Rime-digestible
layered dictionaries out.

This repository is nested under the VoiMate working tree for local
work, but remains an **independent git repo**, not a VoiMate package
or submodule. Canonical path: `/Volumes/External/GitHub/VoiMate/Lexicon`.
VoiMate remains the product (keyboard, voice ledger, Host). This repo
produces the Chinese word data the keyboard will eventually mmap.

## Why this repo exists

Rime is the right engine. The bottleneck is data.

uMate already embeds librime and a small official luna_pinyin + essay
bundle. That stack is classic, local, and license-clean. It is also
dated: literary weights, thin modern coverage, and almost no personal
accumulation on the keyboard. Community recipes that *feel* like a 2026
IME (rime-ice / 雾凇, wanxiang / 万象) got there by years of dictionary
work, not by a better C++ core.

We will not vendor those recipes:

- rime-ice is **GPL-3.0-only**. Copying its schema, Lua, or curated
  `cn_dicts` would pull the product under GPL.
- Its interesting *ideas* (character table, base, ext, bulk coverage,
  mixed Latin, first-import wins) are not copyrightable. We re-implement
  them against **upstream dumps** (Unihan, CC-CEDICT, THUOCL, Tencent
  embedding vocabulary, Wikimedia), with provenance on every lemma.
- Official Rime already defined the file contract we emit:
  `*.dict.yaml`, `import_tables`, and `translator/packs`
  (librime ≥ 1.6). Ice is one productization of that contract. This
  factory is another.

The factory is designed like a compiler, not like a pile of YAML:

```text
pinned dumps
  → ingest (license stamp, clean-room gate)
  → lemma store  (surface, pinyin) primary key
  → enrich (polyphone closed set, categories)
  → verify (rules + gold + optional LLM checker)
  → emit layered dict.yaml + packs
  → Host compiles table.bin / prism.bin
  → eval gate (must not regress gold readings)
```

YAML is an **object dump**, not the source of truth.

## What "at least 雾凇" means here

- **Structure:** at least ice's layers, plus packs, provenance, a
  polyphone closed set, and an eval gate. Bulk coverage must not rely on
  Rime guessing pinyin for polyphonic words.
- **Scale:** coverage and first-candidate quality, not line count of
  `tencent.dict.yaml`.
- **Not:** a fork, a re-licensed ice tree, or a web crawler as the
  primary corpus.

## Clean room

See [CLEANROOM.md](CLEANROOM.md). Ingest refuses rime-ice paths and
markers. Do not use ice or wanxiang files as raw material. Comparing
typing-test *behavior* is allowed.

## Pipeline

```text
umate_hans.dict.yaml          core: chars + 2–3 char base + A–Z/digits
translator/packs:
  umate_ext                   4-char and curated extra
  umate_names                 people
  umate_places                admin divisions / POI
  umate_brands                brands / products
  umate_orgs                  orgs / industries
  umate_events                dated events (droppable)
  umate_bulk                  large coverage, no unresolved polyphones
  umate_corrections           common typos / wrong pinyin
secondary translators:
  aosp_en                     English (AOSP table identity)
  umate_cn_en                 mixed phrases
```

Keyboard default SKU: core + ext + names/brands. Bulk and events stay
optional so the iOS Keyboard Extension can mmap without compiling.

## Quick start

Python 3.12+. No required third-party packages for the core factory.

```sh
cd Lexicon
PYTHONPATH=src python -m pytest
PYTHONPATH=src python -m umate_lexicon pipeline --fixtures
```

Fixtures ship in `data/fixtures/` (short original samples, not community
recipes). Full dumps are pinned in `data/sources.lock.json` and fetched
into `data/sources/downloads/` (gitignored). Hash mismatch is a hard
failure. Never fetch rime-ice.

```sh
PYTHONPATH=src python -m umate_lexicon fetch
PYTHONPATH=src python -m umate_lexicon verify-sources
PYTHONPATH=src python -m umate_lexicon pipeline
```

`eval` fails the build if gold pairs such as 重庆/`chong qing`,
银行/`yin hang`, 行走/`xing zou` are missing or wrong.

Coverage after a locked emit is recorded in [docs/zh/inventory.md](docs/zh/inventory.md).
8105, zhwiki titles, and authored brand/event packs are in. Wikipedia page/category dumps now reject wiki-only redirects and type inventory; wiki-only stays bulk. Tencent coverage is the ModelScope **light** high-frequency subset (`tencent-light`), not the official ~8M dump. Official Tencent download URLs still return HTML; do not copy rime-ice `tencent.dict.yaml`. Tencent-only unique-compose lemmas stay in bulk; `domain_freq.tencent=1` is a coverage placeholder and does not change essay ranking. Measured absorb: [docs/zh/tencent-light-absorb-2026-09-16.md](docs/zh/tencent-light-absorb-2026-09-16.md). CI stays on fixtures; a locked fetch downloads the ~111MB `.bin` locally. This work validates **light coverage fusion only**; the ~8M full dump stays out of scope.

## LLM role

Large language models may classify categories or flag likely-wrong
readings through `umate_lexicon.verify.llm`. They must return structured
JSON. They must not invent lemmas. Gold tests own pinyin.

## License

- **Code:** Apache-2.0 (see [LICENSE](LICENSE)).
- **Data:** per lemma, recorded in the store and [NOTICE](NOTICE).
  Share-alike sources need an explicit product decision before they
  enter a default keyboard table.

## Relationship to VoiMate

VoiMate consumes emitted `table.bin` / `prism.bin` produced on a Mac
Host. This repo does not call `start_maintenance` inside a keyboard
extension. Voice Ledger remains a separate ledger; confirmed transcripts
may later *project* into a personal pack, never the other way around.
