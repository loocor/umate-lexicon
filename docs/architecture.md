# Architecture

The factory is a compiler with a durable IR.

```text
sources/downloads     gitignored dumps, hashed
data/fixtures         tiny original samples for tests
data/gold             readings, polyphones, eval sentences
        │
        ▼
   ingest adapters    cedict / thuocl / chars / unihan / t2s / tgh / luna / essay / emoji / tencent / wiki
        │             t2s folds luna/essay/emoji/tencent/wiki to Hans; clean-room gate first
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

Raw counts live in `domain_freq`. Emitted weight is
`round(100 * log1p(ranking))` so files stay short, same idea as large
community tables without copying them. Coverage placeholders
(`domain_freq.tencent`, `domain_freq.wiki`) are stored but excluded
from ranking so essay remains the sort key. Tencent vocab lines are
`freq=1`; vectors never enter the store.

## Gap triage

`data/gold/daily-gaps.tsv` is the running ledger of words users report as
untypeable. `python -m umate_lexicon gaps` classifies each row against the
store so a report turns into an action instead of a guess:

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
