# Production loop

1. Pin dump URLs and sha256 in `data/sources.lock.json`.
2. `python -m umate_lexicon fetch` then `verify-sources`.
3. Ingest in lock order after gold: Unihan readings (kMandarin and
   kHanyuPinlu), variants (t2s), kTGH (8105), CC-CEDICT, THUOCL, official
   luna, absorbed core, emoji, zhwiki titles / page / category, then Tencent light
   vocab and the d200 key top 1,000,000 lines, then Wikinews pages last
   (missing surfaces only). AOSP English is an emit
   sidecar, not a Chinese lemma. Luna/core/emoji/tencent/wiki surfaces are
   simplified before overlay. Lock order puts both Tencent sources after
   wiki so overlay cannot steal wiki identity. Do not re-run a locked
   pipeline into an existing store: `domain_freq` values are summed on
   merge, so a second ingest doubles core counts. Use a fresh `--store`.
4. Enrich polyphones. A closed-set character reading from gold, CC-CEDICT,
   Unihan, or kHanyuPinlu emits to `chars`. Luna-only readings stay
   `untrusted_reading` and are not emitted. Low-frequency composed guesses
   stay `review`.
5. Emit. Run `eval`. Gold readings and `data/gold/emit-probes.tsv` both
   fail the release. The probe file is not gold and must stay in
   `_GOLD_SKIP`. OpenCC t2s folds traditional *words* at emit time; it
   must not replace a TGH/gold/chars 1-gram or keep the heavier
   traditional lemma when that would drop the chars gate (羣/群, 喫/吃).
   A TGH/gold/kHanyuPinlu/chars-source 1-gram, including TGH Extension
   A-F, stays in `chars` even when THUOCL tagged it as industry/org
   (鸮/鸰). Unihan-only Extension A stays out. A floor simplified row
   (ranking frequency <= 1) may inherit the folded traditional ranking
   column (乾淨 core -> 干净). A native row that already has a measured
   column keeps it (群 does not absorb 羣).
6. Compile on the Mac Host used by uMate. Copy `table.bin` /
   `prism.bin` into the keyboard bundle. Never compile inside the
   extension. Sync is a separate confirmation; this factory does not
   push YAML into the keyboard tree by itself.
7. Emit shape: hot `umate_hans` (chars, base, corrections, hot_tail)
   and cold `umate_hans_cold` (every emitable pack). Emoji is a
   standalone `umate_emoji` channel, never merged into the hot table.
   Which cold packs the keyboard actually compiles is a uMate schema
   choice.

`pipeline --fixtures` is the unit-test path. Unlocked `pipeline` is the
full ingest gate and must not substitute fixtures when a dump is missing.

Share-alike (CC-CEDICT, Wikimedia) has no recorded legal decision for the
commercial binary. Do not promote pure CC-CEDICT or pure wiki rows into
the hot table, and do not strip rows already emitted, until that decision
is written down. `NOTICE` still ships with the table.

Human time goes to the review queue and the polyphone closed set, not
to hand-editing million-line YAML.

## Essay absorption record (2026-10-03)

The `rime/rime-essay` word list was absorbed once into this repo as the
self-owned snapshot `data/voimate/absorbed-core.tsv` (derived from
`essay.txt` @ `e9b1a374a6ea015fca5bdd04318924b4483ac35a`, sha256
`a6f8409c...4151cea`, LGPL-3.0). Data provenance in the store is
`umate-core` (domain `core`); the ranking column is resolved once into
`lemmas.rank` + `store_meta.policy_version = v1-absorb` by
`scripts/absorb_essay_migration.py`. No pipeline stage reads the essay
identity anymore; attribution lives in `NOTICE` and this record.

Upstream review cadence: check `rime/rime-essay` every 3-6 months for
word-list corrections worth re-absorbing; re-absorption is a deliberate
versioned migration, never an automatic fetch.

Acceptance: post-migration emit is byte-identical on every `*.dict.yaml`
(NOTICE only renames `essay` -> `umate-core`, same 440148 lemmas).

## OpenCC toolchain pin (2026-10-03)

Emit t2s conversion must use the official `opencc` package
(`uv run --with opencc -- ...`). The `opencc-python-reimplemented`
package produces different variant-folding output on 132 base chars
(谿→溪, 舖→铺, etc.). The current `dist/rime` output was refreshed with
the official implementation; do not mix implementations between builds.

## Modern-freq v2 record (2026-10-03)

`modern_freq` v1 covers 2,837 single chars with both core + hanyu_pinlu
measurements. Values are rank-calibrated onto the core scale via
rank-to-rank quantile mapping (`scripts/build_modern_freq.py`). Policy
version is `v2-modern-freq`; the column has top precedence in
`RANK_DOMAIN_PRECEDENCE`. This fixes 群(14689) > 裙(663) and promotes 一
to rank 2, matching natural Chinese frequency intuition.

Multi-char words are NOT covered: tencent vocab has no usable frequency
counts (88% are placeholder 1), only a coarse "appeared >= N times"
signal. Word-level modern_freq requires a new corpus source (pending
user decision).
