# Production loop

1. Pin dump URLs and sha256 in `data/sources.lock.json`.
2. `python -m umate_lexicon fetch` then `verify-sources`.
3. Ingest in lock order after gold: Unihan readings (kMandarin and
   kHanyuPinlu), variants (t2s), kTGH (8105), CC-CEDICT, THUOCL, official
   luna, essay, emoji, zhwiki titles / page / category, then Tencent light
   vocab and the d200 key top 1,000,000 lines. AOSP English is an emit
   sidecar, not a Chinese lemma. Luna/essay/emoji/tencent/wiki surfaces are
   simplified before overlay. Lock order puts both Tencent sources after
   wiki so overlay cannot steal wiki identity. Do not re-run a locked
   pipeline into an existing store: `domain_freq` values are summed on
   merge, so a second ingest doubles essay counts. Use a fresh `--store`.
4. Enrich polyphones. A closed-set character reading from gold, CC-CEDICT,
   Unihan, or kHanyuPinlu emits to `chars`. Luna-only readings stay
   `untrusted_reading` and are not emitted. Low-frequency composed guesses
   stay `review`.
5. Emit. Run `eval`. Gold readings and `data/gold/emit-probes.tsv` both
   fail the release. The probe file is not gold and must stay in
   `_GOLD_SKIP`.
6. Compile on the Mac Host used by uMate. Copy `table.bin` /
   `prism.bin` into the keyboard bundle. Never compile inside the
   extension. Sync is a separate confirmation; this factory does not
   push YAML into the keyboard tree by itself.
7. Emit shape: hot `umate_hans` (chars, base, corrections, emoji,
   hot_tail) and cold `umate_hans_cold` (every emitable pack). Which
   cold packs the keyboard actually compiles is a uMate schema choice.

`pipeline --fixtures` is the unit-test path. Unlocked `pipeline` is the
full ingest gate and must not substitute fixtures when a dump is missing.

Share-alike (CC-CEDICT, Wikimedia) has no recorded legal decision for the
commercial binary. Do not promote pure CC-CEDICT or pure wiki rows into
the hot table, and do not strip rows already emitted, until that decision
is written down. `NOTICE` still ships with the table.

Human time goes to the review queue and the polyphone closed set, not
to hand-editing million-line YAML.
