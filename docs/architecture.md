# Architecture

The factory is a compiler with a durable IR.

```text
sources/downloads     gitignored dumps, hashed
data/fixtures         tiny original samples for tests
data/gold             readings, polyphones, eval sentences
        │
        ▼
   ingest adapters    cedict / thuocl / chars / unihan / luna / essay / emoji / tencent
        │             clean-room gate first
        ▼
   SQLite store       lemmas + lemma_sources
        │
        ▼
   enrich             compose pinyin, polyphone flags, categories
        │
        ▼
   verify             rules, gold, optional LLM
        │
        ▼
   emit               dist/rime/*.dict.yaml
        │
        ▼
   eval               gold pairs must exist with the right pinyin
```

## Lemma

Primary key: `(surface, pinyin_plain)`.

`pinyin_plain` uses Rime syllable spelling (`v` for ü). Toned forms are
metadata for QA, not the lookup key.

Status:

- `gold` — locked by `data/gold/readings.tsv`
- `auto` — produced by a trusted adapter (CC-CEDICT with numbered pinyin)
- `review` — polyphonic or composed without a gold reading
- `rejected` — failed rules (NSFW markers, empty surface, blocked source)

## Layers

| Layer | Predicate | Rime role |
| --- | --- | --- |
| chars | one Han character | core `import_tables` |
| base | 2–3 Han chars, status gold/auto | core |
| ext | 4 Han chars, curated | pack |
| names / places / brands / orgs / events | `entity_type` | packs |
| bulk | auto, no `polyphone` flag | pack |
| corrections | `correction` flag | pack |
| mixed | `mixed_latin` flag | pack or secondary translator |

Duplicate `(surface, pinyin)` across layers is legal; emit writes a lemma
to the first matching layer only.

## Weight

Raw counts live in `domain_freq`. Emitted weight is
`round(100 * log1p(total))` so files stay short, same idea as large
community tables without copying them.
