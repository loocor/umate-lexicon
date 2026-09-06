# Clean-room policy

This repository is a lexicon **compiler**. It is not a fork of rime-ice,
rime-wanxiang, melt_eng, or any commercial IME dictionary.

## Allowed

- Reading public documentation and analyzing *ideas*: layering (chars /
  base / ext / bulk), Rime `import_tables`, `translator/packs`,
  `(surface, pinyin)` as a key, log-compressed weights.
- Ingesting **upstream dumps under their own licenses**: Unihan,
  CC-CEDICT, THUOCL, Tencent embedding word lists (CC BY 3.0), Wikimedia
  dumps, the Table of General Standard Chinese Characters.
- Independently authored gold readings, eval sentences, and schema files.
- Comparing **behavior** on a public typing test set (first-candidate
  hit rate) against other products.

## Forbidden

- Copying files, patches, Lua, schema, OpenCC recipes, or curated
  `*.dict.yaml` bodies from `iDvel/rime-ice` (GPL-3.0-only).
- Using rime-ice / rime-wanxiang trees as ingest input, even to
  "take only the good words".
- Ingesting Sogou/QQ/Baidu cell dictionaries or other commercial IME
  exports.
- Scraping sites that prohibit crawling, or logged-in content.

The ingest path refuses files whose path or content matches known
third-party recipe markers. See `umate_lexicon.cleanroom`.

## Why this exists

uMate embeds librime (BSD-3-Clause) as a Chinese text engine. Official
luna_pinyin + essay is too literary for 2026 mobile input. Community
recipes that feel modern are GPL-encumbered or mixed. This factory
rebuilds scale and structure from licensed sources so the keyboard can
mmap Host-compiled `table.bin` files without taking GPL into the app.
