# Architecture

The factory is a compiler with a durable IR.

```text
sources/downloads     gitignored dumps, hashed
data/fixtures         tiny original samples for tests
data/gold             readings, polyphones, eval sentences
        │
        ▼
   ingest adapters    cedict / thuocl / chars / unihan / t2s / tgh / luna / absorbed-core / emoji / tencent / wiki
        │             t2s folds luna/core/emoji/tencent/wiki to Hans; clean-room gate first
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
| bulk | tencent-only and other low-frequency but real word lists | pack |
| — | `wiki`-only lemmas | **not emitted** (coverage evidence only) |
| corrections | `correction` flag | pack |
| mixed | `mixed_latin` flag | pack or secondary translator |

Duplicate `(surface, pinyin)` across layers is legal; emit writes a lemma
to the first matching layer only.

## Weight

Raw counts live in `domain_freq`, one column per measuring instrument.
The emitted `weight` column is a single raw column, never a sum: the
strongest measured domain wins (`core` first, then `hanyu_pinlu`,
`chars`, `gold`, `thuocl*`, `luna`, `cedict`, `unihan`). A THUOCL
document count and a core 1e8-scale count are different rulers, not
addends -- summing them let THUOCL terms outrank common core-ranked
words. librime compiles the column as `log(weight)` and subtracts
`log(1e8)` when a candidate is built, so the column stays on the core
1e8 scale. Do not pre-compress it -- a log here is applied twice and
flattens the distribution until rare entries rival common ones.

Core corpus lines have no pinyin. For a single character, when the same core
count is stamped on more than one reading, emit keeps it on the preferred
reading only (TGH, gold, then trusted-source count, then weight). A
strictly weaker reading loses the shared column and keeps its own
measured domains; it never falls back to the stale store weight. Ties
keep the count. Multi-character rows are not rewritten this way: a gold
correction such as `信息/zi xun` must not steal the count from the
common reading. The store is not rewritten; a later clean ingest stamps
the preferred reading only for single characters.

Coverage placeholders (`domain_freq.tencent`, `domain_freq.wiki`) are
stored but excluded from ranking so core remains the sort key. Tencent
vocab lines are `freq=1`; vectors never enter the store.

## Gap triage

`data/gold/daily-gaps.tsv` is the running ledger of words users report as
untypeable. It is triage input only and must not be ingested as gold; the
locked pipeline excludes it. `python -m umate_lexicon gaps` classifies each
row against the store so a report turns into an action instead of a guess:

| Bucket | Meaning | Action |
| --- | --- | --- |
| `missing` | no lemma, and the characters are not all in `chars` | add a source or a gold reading |
| `segmentation` | no phrase entry, but every character has a reading | phrase is composed, not stored: check ranking, not coverage |
| `present-filtered` | rows exist but no layer survives emit | read `status` / `flags`, usually polyphone |
| `present-not-shipped` | survives only in an optional pack | decide pack membership, do not touch the store |
| `present-ranked-low` | in core, but rank is below `char_floor` | ranking work, not coverage work |
| `present-shipped` | in core, above the character floor | reported failure is UI, config, or segmentation |

`char_floor` is the weakest `ranking_freq` among the characters that spell
the phrase, matched per syllable. A phrase below that floor carries less
evidence than the rarest character inside it, so the engine has no reason
to prefer the phrase over typing the characters one at a time.
