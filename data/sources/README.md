# Source downloads

Hashed dumps belong in `downloads/` (gitignored). Fetch them from the
pins in `../sources.lock.json`:

```sh
python -m umate_lexicon fetch
```

Expected artifacts after fetch:

- CC-CEDICT `cedict_ts.u8`
- THUOCL `THUOCL_*.txt`
- Unihan `Unihan_Readings.txt`

Do not place rime-ice, rime-wanxiang, or commercial `.scel` files here.
The ingest gate will refuse them.
