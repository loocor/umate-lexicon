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
- Official luna `luna_pinyin.dict.yaml`
- Official essay `essay.txt`
- Official rime-emoji `emoji_word.txt`
- Tencent light Word2Vec `light_Tencent_AILab_ChineseEmbedding.bin`
  (extracted to `tencent-vocab.txt`; do not commit the `.bin`)

Do not place rime-ice, rime-wanxiang, or commercial `.scel` files here.
The ingest gate will refuse them.
