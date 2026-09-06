# Production loop

1. Pin dump URLs and hashes in a future `sources.lock.json`.
2. Ingest in order: gold → chars/unihan → cedict → thuocl → categories.
3. Enrich polyphones; anything in the closed set without gold/cedict
   stays `review`.
4. Emit. Run `eval`. Fail the release if gold readings regress.
5. Compile on the Mac Host used by VoiMate. Copy `table.bin` /
   `prism.bin` into the keyboard bundle. Never compile inside the
   extension.
6. SKU: `default` (core+ext+names+brands) vs `full` (+bulk+events).

Human time goes to the review queue and the polyphone closed set, not
to hand-editing million-line YAML.
