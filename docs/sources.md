# Source adapters

Pinned dumps live in [`sources.lock.json`](../data/sources.lock.json).
Fetch with `python -m umate_lexicon fetch` or `scripts/fetch-sources.sh`.
The ingest gate (`verify-sources` / locked `pipeline`) refuses missing
files and hash mismatches. It does not fall back to fixtures.

Scope note: this file is the lemma-store adapter contract. Evaluation
and training corpora (round eval files, `.gram` training feeds) are
registered separately in `data/eval/corpus/SOURCES.md`; admission
policy lives in `source-policy.md`.

| Adapter | Input | License to record | Pinyin |
| --- | --- | --- | --- |
| `chars` | `surface<TAB>pinyin<TAB>weight` | `standard-8105` or `unihan` | required |
| `cedict` | CC-CEDICT `cedict_ts.u8` | `cc-by-sa-cedict` | numbered, converted |
| `thuocl` | THUOCL `word<TAB>df` | `mit-thuocl` | composed from char table |
| `unihan` | Unihan `kMandarin` lines | `unicode` | from kMandarin |
| `gold` | `data/gold/readings.tsv` | `umate-gold` | authoritative |
| `luna` | official `luna_pinyin.dict.yaml` | `lgpl-rime-luna` | spaced plain pinyin |
| `core` | absorbed `data/voimate/absorbed-core.tsv` (rime-essay derived) | `lgpl-rime-essay` | overlay / unique compose |
| `emoji` | official `opencc/emoji_word.txt` | `lgpl-rime-emoji` | compose trigger, optional pack |
| `tgh` | Unihan `kTGH` lines | `unicode` | flags 8105 chars |
| `wiki` | zhwiki ns0 titles | `cc-by-sa-wikimedia` | unique compose, bulk |
| `wiki_page` | zhwiki `page` SQL | `cc-by-sa-wikimedia` | reject wiki-only redirects |
| `wiki_linktarget` | zhwiki `linktarget` SQL | `cc-by-sa-wikimedia` | category titles |
| `wiki_category` | zhwiki `categorylinks` SQL | `cc-by-sa-wikimedia` | type overlay, still bulk |
| `tencent` | embedding vocab (first column) | `cc-by-3.0-tencent` | unique compose, coverage only, bulk if tencent-only |
| `wikinews` | dated article TSV `title<TAB>body` | `cc-by-4.0-wikinews` | unique compose, missing surfaces only, coverage only, bulk if wikinews-only |

Current pins:

- Unihan 17.0.0 zip from unicode.org
- CC-CEDICT gzip from MDBG (rolling file; bump the lock when it changes)
- THUOCL `data/*.txt` at git commit `a30ce79d895d01ab5132a5c74c29703ff7efb4cc`
- Official Rime `rime-luna-pinyin` `luna_pinyin.dict.yaml` at
  `56b934b099dfbeab842320f13aa8b461a6ab3e42`
- Absorbed core: `rime-essay` `essay.txt` at
  `e9b1a374a6ea015fca5bdd04318924b4483ac35a`, frozen once as
  `data/voimate/absorbed-core.tsv` (upstream re-reviewed periodically)
- Official Rime `rime-emoji` `opencc/emoji_word.txt` at
  `d1dbb424124fc50452a179300c7f287dbcc0db64`
- Unihan `kTGH` from the same 17.0.0 zip (`unihan-tgh`)
- Chinese Wikipedia ns0 titles `zhwiki-20260901-all-titles-in-ns0.gz`
- Wikipedia `page` / `categorylinks` / `linktarget` dumps, same date, for
  redirect 排重 and entity typing. Wiki-only lemmas stay in bulk even
  when typed. Do not copy `page_len` or edit counts into `domain_freq`.
- Tencent AI Lab embedding **light** subset via ModelScope
  `lili666/text2vec-word2vec-tencent-chinese`
  (`light_Tencent_AILab_ChineseEmbedding.bin`, lock id `tencent-light`).
- Tencent AI Lab d200 v0.2.0 key list via a pinned Hugging Face revision
  (`26b432a69cca98e291a76b6e8e8890f3527b67b5`, lock id
  `tencent-d200-key-top1m`). The mirror declares no separate license;
  attribution follows the upstream CC BY 3.0 Tencent AI Lab vocabulary.
  The key list has 12,287,936 lines. The lock transcodes its first
  1,000,000 lines from CP936 to UTF-8 and does not download the 6.14 GB
  vector payload. Do not copy rime-ice `tencent.dict.yaml`.

The absorbed core corpus is the ranking source (`domain_freq.core`,
resolved once into `lemmas.rank`, policy `v1-absorb`). Luna is coverage
plus official readings. Ingest folds Traditional surfaces to Hans with
Unihan `kSimplifiedVariant` (`ingest: t2s`, lock id `unihan-variants`)
so core `銀行` overlays `银行`. Frequency overlay and compose prefer trusted
readings (gold / cedict / unihan / chars). Leftover luna-only readings
are flagged `untrusted_reading` and are not emitted.

Tencent AI Lab embeddings are **coverage**, not frequency. The ModelScope
binary and the d200 key list have no counts; ingest treats vocab lines as
`freq=1` / unique compose and never invents core-like weights. Overlay
stamps `domain_freq.tencent=1` on existing lemmas; emit ranking ignores
that placeholder so core stays the sort key. Tencent-only unique-compose
lemmas stay in **bulk** (not base/ext). Lock order puts both Tencent sources
after the wiki dumps so overlay cannot steal wiki identity. Fetch downloads
the ModelScope resolve URL (CDN `auth_key` redirects are ephemeral; the
resolve URL plus content sha256 are the pin) and the pinned Hugging Face
revision. `extract.kind = word2vec-vocab` writes a first-column word list
only — vectors never enter the store. `extract.kind = transcode` converts
the d200 CP936 key list to UTF-8 and `max_lines` bounds the slice while
streaming. `scripts/extract-tencent-vocab.py` reads Google/gensim binary as
well as text / tar.gz. CI stays on fixtures; do not commit the raw bins or
derived vocab. ModelScope card Apache-2.0 is packaging; the Hugging Face
mirror declares no separate license. Vocabulary attribution remains
CC BY 3.0 Tencent AI Lab.

Wikinews article text (`wikinews-pages`, CC BY 4.0) is **coverage**, not
frequency. The dated TSV from `scripts/fetch-wikinews.py` is ingested last
and only inserts surfaces missing from every earlier channel, so it cannot
steal identity or ranking from core / luna / wiki / tencent. Wikinews-only
lemmas stay in **bulk**; `domain_freq.wikinews` is excluded from
`ranking_freq`. Re-fetching is a new dated file plus a lock hash bump.

Share-alike (CC-CEDICT, Wikipedia titles) is tagged, never silently
folded into a default keyboard SKU.

Fetch full dumps into `data/sources/downloads/`. Do not commit them.
Do not fetch rime-ice.
