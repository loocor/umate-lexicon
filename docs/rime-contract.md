# Rime emit contract

Target: librime 1.16 dictionary source format.

A dict file is a YAML header between `---` and `...`, then tab-separated
rows: `text`, `code`, `weight`.

```yaml
# Rime dictionary
# encoding: utf-8
---
name: umate_hans
version: "0.1.0"
sort: by_weight
use_preset_vocabulary: false
import_tables:
  - umate_chars
  - umate_base
...
```

Packs (librime ≥ 1.6) are extra `*.table.bin` files sharing the core
prism syllable table. Schema:

```yaml
translator:
  dictionary: umate_hans
  packs:
    - umate_ext
    - umate_names
    - umate_places
    - umate_brands
    - umate_orgs
    - umate_events
    - umate_bulk
    - umate_corrections
```

This repo emits **source YAML**. Binary compilation is a Host job in
VoiMate (`table.bin`, `prism.bin`, `reverse.bin`). The keyboard extension
must not run `start_maintenance`.

Alphabet digits belong in the core dict body. `A`–`Z` syllable rows are
emitted here for a *future* mixed-input schema only. VoiMate QWERTY
`luna_pinyin` must not import those rows yet: Shift-letter still starts
Chinese composing. The English table identity is `aosp_en`, not a
handmade `umate_en` patch.

## Optional emoji pack

`umate_emoji.dict.yaml` is emitted when composable Han triggers exist
(`哈哈` → `ha ha` → 😂). `opencc/emoji_word.txt` is copied beside it.
Neither is listed in `translator/packs` and VoiMate must not enable
`simplifier@emoji_suggestion` until that SKU is explicitly chosen.
The mapping comes from official `rime/rime-emoji` (LGPL-3.0), not from
rime-ice OpenCC recipes.
