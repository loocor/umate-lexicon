# Source adapters

| Adapter | Input | License to record | Pinyin |
| --- | --- | --- | --- |
| `chars` | `surface<TAB>pinyin<TAB>weight` | `standard-8105` or `unihan` | required |
| `cedict` | CC-CEDICT `cedict_ts.u8` | `cc-by-sa-cedict` | numbered, converted |
| `thuocl` | THUOCL `word<TAB>df` | `mit-thuocl` | composed from char table |
| `unihan` | Unihan `kMandarin` lines | `unicode` | from kMandarin |
| `gold` | `data/gold/readings.tsv` | `umate-gold` | authoritative |

Share-alike (CC-CEDICT, Wikipedia titles) is tagged, never silently
folded into a default keyboard SKU.

Fetch full dumps into `data/sources/downloads/`. Do not commit them.
Do not fetch rime-ice.
