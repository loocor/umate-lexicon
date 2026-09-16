# Production loop

1. Pin dump URLs and sha256 in `data/sources.lock.json`.
2. `python -m umate_lexicon fetch` then `verify-sources`.
3. Ingest in lock order after gold: Unihan readings, variants (t2s), kTGH (8105), CC-CEDICT, THUOCL, official luna, essay, emoji, Tencent light vocab (`tencent-light`, coverage only), zhwiki titles. Luna/essay/emoji/tencent/wiki surfaces are simplified before overlay. Coverage-only lemmas (wiki and/or tencent, no curated source) emit to bulk, not default SKU. The Tencent pin is the ModelScope light subset, not the official ~8M dump. Measured light absorb: [docs/zh/tencent-light-absorb-2026-09-16.md](zh/tencent-light-absorb-2026-09-16.md).
4. Enrich polyphones; anything in the closed set without gold/cedict
   stays `review`.
5. Emit. Run `eval`. Fail the release if gold readings regress.
6. Compile on the Mac Host used by VoiMate. Copy `table.bin` /
   `prism.bin` into the keyboard bundle. Never compile inside the
   extension.
7. SKU: `default` (core+ext+names+brands) vs `full` (+bulk+events).

`pipeline --fixtures` is the unit-test path. Unlocked `pipeline` is the
full ingest gate and must not substitute fixtures when a dump is missing.

Human time goes to the review queue and the polyphone closed set, not
to hand-editing million-line YAML.
