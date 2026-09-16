# Production loop

1. Pin dump URLs and sha256 in `data/sources.lock.json`.
2. `python -m umate_lexicon fetch` then `verify-sources`.
3. Ingest in lock order after gold: Unihan, CC-CEDICT, THUOCL, official luna, essay, emoji.
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
