# Tencent light pin validation

Scratch-store dry-run of the pinned light Word2Vec vocabulary.
This is **not** a dictionary merge and does **not** refresh
[zh/inventory.md](zh/inventory.md) lemma totals.

Commands:

```sh
PYTHONPATH=src python3 -m umate_lexicon fetch \
  --id unihan --id unihan-variants --id unihan-tgh \
  --id thuocl-it --id thuocl-animal --id thuocl-caijing --id thuocl-car \
  --id thuocl-chengyu --id thuocl-diming --id thuocl-food --id thuocl-law \
  --id thuocl-lishimingren --id thuocl-medical --id thuocl-poem \
  --id luna --id essay --id emoji --id tencent
PYTHONPATH=src python3 -m umate_lexicon verify-sources --id tencent
PYTHONPATH=src python3 scripts/report-tencent-fusion.py \
  --store /tmp/tencent-fusion.sqlite -o /tmp/tencent-fusion.json
```

Wiki dumps were not fetched. CEDICT was skipped: the rolling MDBG
file no longer matches the lock (`expected 70fee391…`,
`got 6da40a5a…`). Do not invent a replacement hash here.

## Fetch / extract

| Field | Value |
| --- | --- |
| artifact | `light_Tencent_AILab_ChineseEmbedding.bin` |
| bytes | 116021049 |
| sha256 | `5515923c7e67cdc7eb42996546e0bad273c8452f3bfad6db0794e51c848d151b` |
| header | vocab_size=143613, dim=200 |
| extracted lines | 143613 (`tencent-vocab.txt`) |
| unique surfaces | 143612 (one duplicate line) |

Vectors were discarded. Factory ingest sees the word list only.

## Raw vocab shape (before factory gates)

| Bucket | Count | Examples |
| --- | ---: | --- |
| ASCII alphabetic | 17526 | chapter, the, data, unit |
| Mixed han + other | 1204 | 2015年, 3个, 10年 |
| Any digit | 4707 | 1, 2017, 2. |

Leading embedding tokens include punctuation: `,` `“` `”` `.` `~`.

## Fusion against gold + Unihan + THUOCL + luna + essay + emoji

Base store before Tencent: **582447** lemmas.

| Gate | Count | Meaning | Samples |
| --- | ---: | --- | --- |
| `overlay_existing` | 80208 | already in store; add `domain_freq.tencent` | 我们, 可以, 微信, 抖音 |
| `accept_new` | 25285 | 2–4 han chars with unique composed pinyin | 游戏, 如果你, 吃饭, 周末 |
| `drop_non_han` | 23009 | punctuation / ASCII / mixed / digits | `,`, `“`, chapter, 2015年 |
| `drop_single_char` | 13558 | han length 1; char table already owns these | 的, 了, 是, 在 |
| `drop_no_unique_pinyin` | 1063 | no single trusted char reading | 都会, 适合, 都不 |
| `drop_too_long` | 490 | han length > 4 and not already present | 新闻发布会, 房地产市场 |
| kept (overlay + new) | 105493 | would enter as coverage |  |
| dropped | 38120 |  |  |

`ingest_tencent` returned **105975** (higher than 105493 because
`overlay_domain_freq` can stamp more than one reading per surface).
Store grew **25266** lemmas to **607713**. That is the classified
`accept_new` set after upsert; it is not a naive 143613-line union.

## Spot checks

| Surface | Gate | After ingest |
| --- | --- | --- |
| 微信 | `overlay_existing` | gold + essay 31877 + tencent 1 |
| 抖音 | `overlay_existing` | gold + essay 8777 + tencent 1 |
| 人工智能 | `overlay_existing` | essay 12457 + tencent 1 |
| 游戏 | `accept_new` | tencent 1 only (new coverage) |
| 的 | `drop_single_char` | no tencent stamp; essay 4822928 stays |

Essay remains the ranking source. Tencent is a presence flag of 1.

## What this did not do

- No write to `data/store/` or `dist/rime/`
- No rime-ice / wanxiang / melt_eng ingest
- No wiki dumps
- No CEDICT (stale lock)
- No runtime vectors
- Inventory totals in `docs/zh/inventory.md` were not refreshed
