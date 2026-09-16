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
| `tencent` | embedding vocab (first column) | `cc-by-3.0-tencent` | unique compose, fixture only |

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

Essay is the ranking source (`domain_freq.essay`). Luna is coverage plus
official readings. Ingest folds Traditional surfaces to Hans with Unihan
`kSimplifiedVariant` (`ingest: t2s`, lock id `unihan-variants`) so essay
`銀行` overlays `银行`. Frequency overlay and compose prefer trusted
readings (gold / cedict / unihan / chars). Leftover luna-only readings
are flagged `untrusted_reading` and are not emitted.

Tencent AI Lab embeddings are **coverage**, not frequency. The historic
tar.gz URL currently returns a 22KB HTML page, not the 6GB+ corpus. Do
not invent a hash. Adapter + `scripts/extract-tencent-vocab.py` are
ready; pin only after a real vocab file is downloaded and sha256'd.
Do not copy rime-ice `tencent.dict.yaml`.

Share-alike (CC-CEDICT, Wikipedia titles) is tagged, never silently
folded into a default keyboard SKU.

Fetch full dumps into `data/sources/downloads/`. Do not commit them.
Do not fetch rime-ice.
