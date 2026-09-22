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
umate_hans.dict.yaml          hot every-key: chars + base + corrections + emoji + hot_tail
umate_hans_cold.dict.yaml     full fallback; drawer-only
umate_hot_tail                long-tail packs at or above the hot weight floor
umate_mixed                   mixed Latin phrases already emitted
aosp_en.dict.yaml             English Rime table (AOSP LatinIME, Apache-2.0)
en_us_unigrams.tsv            Swift EnglishLexicon truncation, including short function words
```

The keyboard schema is `umate_pinyin*`, owned by uMate. This factory does
not compile binaries and does not decide which cold packs the extension
mmap. See [docs/rime-contract.md](docs/rime-contract.md).

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
8105, zhwiki titles, and authored brand/event packs are in. Wikipedia page/category dumps now reject wiki-only redirects and type inventory. Typed wiki-only rows join their named pack at a cold weight; untyped rows enter bulk only when the page-length tier meets the hot floor. That split is frozen: do not promote more pure wiki or pure CC-CEDICT into the hot table, and do not strip rows already emitted, until a legal decision is recorded. See docs/zh/next-plan.md. Tencent coverage has two pinned layers: the ModelScope light high-frequency subset (`tencent-light`) and the Tencent AI Lab d200 v0.2.0 key list from a pinned Hugging Face revision (`tencent-d200-key-top1m`). The full key list contains 12,287,936 lines; the lock ingests the first 1,000,000 lines in source order as a bounded high-frequency slice and never downloads the 6.14 GB vector payload. Do not copy rime-ice `tencent.dict.yaml`. Tencent-only unique-compose lemmas stay in bulk; `domain_freq.tencent=1` is a coverage placeholder and does not change essay ranking. Measured light absorb: [docs/zh/tencent-light-absorb-2026-09-16.md](docs/zh/tencent-light-absorb-2026-09-16.md). CI stays on fixtures; a locked fetch downloads the local Tencent artifacts.

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
