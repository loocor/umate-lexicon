# Source adapters

Pinned dumps live in [`sources.lock.json`](../data/sources.lock.json).
Fetch with `python -m umate_lexicon fetch` or `scripts/fetch-sources.sh`.
The ingest gate (`verify-sources` / locked `pipeline`) refuses missing
files and hash mismatches. It does not fall back to fixtures.

| Adapter | Input | License to record | Pinyin |
| --- | --- | --- | --- |
| `chars` | `surface<TAB>pinyin<TAB>weight` | `standard-8105` or `unihan` | required |
| `cedict` | CC-CEDICT `cedict_ts.u8` | `cc-by-sa-cedict` | numbered, converted |
| `thuocl` | THUOCL `word<TAB>df` | `mit-thuocl` | composed from char table |
| `unihan` | Unihan `kMandarin` lines | `unicode` | from kMandarin |
| `gold` | `data/gold/readings.tsv` | `umate-gold` | authoritative |
| `luna` | official `luna_pinyin.dict.yaml` | `lgpl-rime-luna` | spaced plain pinyin |
| `essay` | official `essay.txt` frequency | `lgpl-rime-essay` | overlay / unique compose |
| `emoji` | official `opencc/emoji_word.txt` | `lgpl-rime-emoji` | compose trigger, optional pack |
| `tgh` | Unihan `kTGH` lines | `unicode` | flags 8105 chars |
| `wiki` | zhwiki ns0 titles | `cc-by-sa-wikimedia` | unique compose, bulk |
| `wiki_page` | zhwiki `page` SQL | `cc-by-sa-wikimedia` | reject wiki-only redirects |
| `wiki_linktarget` | zhwiki `linktarget` SQL | `cc-by-sa-wikimedia` | category titles |
| `wiki_category` | zhwiki `categorylinks` SQL | `cc-by-sa-wikimedia` | type overlay, still bulk |
| `tencent` | embedding vocab (first column) | `cc-by-3.0-tencent` | unique compose, coverage only |

Current pins:

- Unihan 17.0.0 zip from unicode.org
- CC-CEDICT gzip from MDBG (rolling file; bump the lock when it changes)
- THUOCL `data/*.txt` at git commit `a30ce79d895d01ab5132a5c74c29703ff7efb4cc`
- Official Rime `rime-luna-pinyin` `luna_pinyin.dict.yaml` at
  `56b934b099dfbeab842320f13aa8b461a6ab3e42`
- Official Rime `rime-essay` `essay.txt` at
  `e9b1a374a6ea015fca5bdd04318924b4483ac35a`
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
  Official full dump (~8M words / multi-GB) is still unavailable; those
  URLs return HTML. This is not that dump. Do not copy rime-ice
  `tencent.dict.yaml`.

Essay is the ranking source (`domain_freq.essay`). Luna is coverage plus
official readings. Ingest folds Traditional surfaces to Hans with Unihan
`kSimplifiedVariant` (`ingest: t2s`, lock id `unihan-variants`) so essay
`銀行` overlays `银行`. Frequency overlay and compose prefer trusted
readings (gold / cedict / unihan / chars). Leftover luna-only readings
are flagged `untrusted_reading` and are not emitted.

Tencent AI Lab embeddings are **coverage**, not frequency. The binary
has no counts; ingest treats vocab lines as `freq=1` / unique compose
and never invents essay-like weights. Fetch downloads the ModelScope
resolve URL (CDN `auth_key` redirects are ephemeral; the resolve URL
plus content sha256 are the pin). `extract.kind = word2vec-vocab`
writes a first-column word list only — vectors never enter the store.
`scripts/extract-tencent-vocab.py` reads Google/gensim binary as well
as text / tar.gz. CI stays on fixtures; do not commit the ~111MB bin
or the derived vocab. ModelScope card Apache-2.0 is packaging;
vocabulary attribution remains CC BY 3.0 Tencent AI Lab.

Fusion is careful, not a dump into default `base`:

- Overlay `domain_freq.tencent` on lemmas that already exist (gold /
  essay / cedict / thuocl / luna / wiki). That does not change layer
  for trusted daily sources.
- Tencent-only lemmas (2–4 Han, unique compose) may be tracked, but
  `assign_layer` sends **coverage-only** (`tencent`, `wiki`, or both)
  to `bulk`. They must not enter default `base` or curated `ext`.
- Suffix classifiers do not promote coverage-only terms into
  places/orgs. Tencent is not a promoting source for wiki redirects.
- Lock order puts `tencent-light` after the wiki dumps so overlay
  cannot steal wiki identity.

Share-alike (CC-CEDICT, Wikipedia titles) is tagged, never silently
folded into a default keyboard SKU.

Fetch full dumps into `data/sources/downloads/`. Do not commit them.
Do not fetch rime-ice.
