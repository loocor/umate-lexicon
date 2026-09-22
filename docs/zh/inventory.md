# 词库盘点（2026-09-23）

这份盘点替换 2026-09-16 的 1,311,126。数字来自当前 `data/store/lemmas.sqlite` 上的 `assign_layer`，不是干净重灌。干净 locked pipeline 另写到 `/tmp/lexicon-locked-rebuild`，因为对已有 store 再 ingest 会把 `domain_freq` 加一遍。那次重灌若还在跑，不能拿来和本表对账。

本地 `lemmas.sqlite`、`data/sources/downloads/`、`dist/` 不入库。

## 规模

| 项 | 数量 | 说明 |
| --- | ---: | --- |
| lemmas | 1,425,891 |  |
| 独特表面 | 1,415,890 |  |
| auto / rejected / review / gold | 889,272 / 487,435 / 48,999 / 185 |  |
| wiki-only | 842,019 | 其中发出 184,554，热表 59,786 |
| cedict-only | 10,970 | 全部 auto。冻结：不再抬进热表，也不剥 |
| tencent-only | 22,811 | 全部 bulk，`freq=1` |
| essay-only | 259,733 |  |

`review` 48,999 里，34,634 仍有发射层，14,365 被滤掉。滤掉的主要是 `untrusted_reading` 和没有可信读音的组合。闭集单字里，luna-only 的 29 条保持不发。

## 发射层

| 层 | 行数 | 角色 |
| --- | ---: | --- |
| dropped | 815,528 | rejected + 未信任读音 + 未放行 |
| base | 178,081 | 热表结构层 |
| bulk | 132,897 | 覆盖；热表只收权重 ≥ 450 的投影 |
| names | 115,425 | 含冷权重的 wiki 人物 |
| orgs | 55,323 |  |
| places | 47,849 |  |
| ext | 35,626 |  |
| phrases | 32,563 |  |
| chars | 7,971 | 含本轮补回的 19 条闭集读音 |
| emoji | 3,585 | 热表结构层；键盘 schema 另接 |
| brands | 873 |  |
| mixed | 138 |  |
| events | 22 |  |
| corrections | 10 |  |

`umate_chars.dict.yaml` 实际写出 7,965 行。另有 9 条 chars 层读音被 `sanitize_emit_code` 丢掉或改写：`儿/r`，以及 `呒/呣/嗯` 的鼻音声调码。本跑道不改清洗规则。

## 本轮多音补回

闭集 84 字里，19 条读音已有 CC-CEDICT，也有 essay/luna，但单字门原先只认 gold / tgh / kHanyuPinlu / chars 源，所以没发出。现已进 `chars`。权重没改，仍是 `ranking_freq`。其中几条次读音带着主读音的 essay 计数，所以权重很高，不是口语实测：

| 表面 | 拼音 | 发出权重 |
| --- | --- | ---: |
| 和 | hu | 1995095 |
| 说 | shui | 1021126 |
| 将 | qiang | 361278 |
| 行 | heng | 119731 |
| 车 | ju | 81081 |
| 区 | ou | 79185 |

其余 13 条在 5,076–64,207。这是读音补回，不是排序实验。次读音和主读音共享 essay 计数的问题留到下一次确认。

## Share-alike

没有记录过的法律结论。59,786 条 wiki-only 已经在热表投影里，这是 `02edd7b` 的既有行为。冻结：不再抬，也不剥。`NOTICE` 仍随表走。

## 探针

`eval` 0 failure。四条缺口：偷偷、多少是 `present-shipped`；连着、出门是 `present-ranked-low`。不进 gold。

## 明确还没做

1. 不改 `HOT_WEIGHT_FLOOR`，不改权重公式。
2. 不把纯 wiki / 纯 CC-CEDICT 再抬进热表。
3. 不同步键盘，不编译，不装机。
4. 腾讯全量约 800 万仍不可用。不拉向量。
5. 不 ingest rime-ice / rime-frost / melt_eng / 商业细胞词库。
