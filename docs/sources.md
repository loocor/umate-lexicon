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

Current pins:

- Unihan 17.0.0 zip from unicode.org
- CC-CEDICT gzip from MDBG (rolling file; bump the lock when it changes)
- THUOCL `data/*.txt` at git commit `a30ce79d895d01ab5132a5c74c29703ff7efb4cc`

Share-alike (CC-CEDICT, Wikipedia titles) is tagged, never silently
folded into a default keyboard SKU.

Fetch full dumps into `data/sources/downloads/`. Do not commit them.
Do not fetch rime-ice.
