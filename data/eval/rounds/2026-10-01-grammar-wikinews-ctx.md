# octagram 域内 ctx 评测与 v3 扩充决策 2026-10-01

## 目的

补齐 grammar v2 的评测盲区：wikinews 新闻域搭配增益是否可测、方向是否正确，
并据此决定是否把语料扩到 20M+ CJK 重训 v3。

## 评测面

从 `data/sources/downloads/wikinews-20261001-pages.tsv`（10,074 篇）与
v2 `scored-final.tsv` 高分域（台风 / 地震 / 天气 / 事故等）导出候选，
人工核验后保留 40 条上下文选词 case：

- 提交前词（prefix 必须是该拼音 TOP-1，保证空格上屏即上下文）
- 再输入次词拼音，期望次词（次词在无上下文词表里不是 TOP-1）
- 文件：`data/eval/rounds/grammar-probe-ctx-cases.tsv`（`domain=wikinews`）
- 同内容以 `#ctx` 行附录在 `grammar-probe-cases.tsv`，既有 ranking 探针会跳过 `#`

## 方法

- 现役 v2 gram：键盘 bundle `umate-zh-hans.gram`（8.1 MB，sha256 `1bd6f91c…`）
- v1 备份：`/Volumes/Backup/tmp/umate-gram-ab/v1-gram-backup`（24.0 MB）
- 两份 bundle 均 `rsync -a` 自现役 `RimeSharedData.bundle`，v1 仅替换 `.gram`
- 探针：Backup/tmp 侧 `umate_grammar_probe_ctx`（VoiMate `umate_grammar_probe.c` 的本地副本，
  增加 `RIME_PROBE_CTX_CASES`；**未改** VoiMate 引擎树）。`nm | grep octagram` = 7
- 空 user dir；builtin 12+2 回归与 40 条 wikinews ctx 一起跑

## 域内 A/B（40 条 wikinews ctx）

| 指标 | v1 | v2 |
|---|---|---|
| PASS | 22 | **35** |
| FAIL | 18 | 5 |
| v1 FAIL → v2 PASS | — | **13** |
| v1 PASS → v2 FAIL | — | **0** |

增益 13 条（v2 纠正的次词）：

| 上下文 | v1 | v2 |
|---|---|---|
| 洒水 + 降温 | 姜文 | 降温 |
| 橙红色 + 预警 | 语境 | 预警 |
| 橙色 + 预警 | 语境 | 预警 |
| 气象厅 + 录得 | 路德 | 录得 |
| 台风 + 吹袭 | 吹熄 | 吹袭 |
| 飓风 + 吹袭 | 吹熄 | 吹袭 |
| 台风 + 云系 | 云溪 | 云系 |
| 飓风 + 时速 | 世俗 | 时速 |
| 飓风 + 过境 | 郭靖 | 过境 |
| 气象局 + 因应 | 阴影 | 因应 |
| 塌方 + 中断 | 终端 | 中断 |
| 洪水 + 冲走 | 重奏 | 冲走 |
| 洪水 + 暴涨 | 保障 | 暴涨 |

两侧同 FAIL（5）：台风名「天鸽 / 巴威」（词表有、gram 无足够专名搭配）、
「撞车事件」仍选「时间」、「高温纪录 / 少雨」仍选「记录 / 少于」。
不是回退。

Builtin ctx `shenghuo` 两侧仍 PASS。`puppy-walk` 两侧同 FAIL（词表路径，与本评测面正交）。

## 判定

域内增益**可测且方向正确**（+13 / 0 回退）。v2 换包不仅是体积收益，新闻域搭配
对次词排序有真实增量。与 232 条知乎词级排序缺口 0 翻转仍然正交：本面测的是
句级搭配，不是无上下文 TOP-1。

## 扩充决策（GO，v3 训练循环另开）

**结论：octagram 应扩语料重训 v3，不停留在 v2。** 本轮不在未 pin 的新源上
直接开训，避免把未登记 verdict 的文本写进 `.gram`。

### 采纳

| 来源 | 许可 | 角色 | 状态 |
|---|---|---|---|
| zh.wikinews.org 滚动快照 | CC BY 4.0 | 已在 v2；常态化 = 按日/按月 `scripts/fetch-wikinews.py` 新文件 + lock hash bump | 2026-10-01 批次已 pin；站方只读不妨碍 dump |
| MOT / VOA Mandarin（`bltlab/mot` `cmn`） | VOA 文本公有领域（17 U.S.C. § 105）；MOT 汇集 CC BY 4.0 | v3 新闻增量，目标把混合语料做到 20M+ CJK | **下一循环 pin sha256 + NOTICE 署名后再训** |
| 国务院公报 | 著作权法第五条第(一)项（法规/行政性质文件） | 候选；讲话/解读须按篇剔除 | 仍待过滤规则，不进 v3 本轮 |

v2 混合量：zhwiki 12.06M + wikinews 5.80M CJK ≈ 17.86M。20M+ 差约 2.2M CJK，
MOT Mandarin（论文口径约 29 万篇）足够，且比再堆 zhwiki shard 更对准新闻域。

### 不采纳

- Newsdata.io「CC BY 4.0 数据集」：汇集条款写明底层稿件仍归原出版社 —— 不能当商用 `.gram` 训练文本。
- Common Crawl CC-News / INFINI-NEWS：同样是出版社版权聚合。
- 把 wikinews skip 的体育比分模板填回去：字符量升、搭配质量不升。
- 为凑 20M 再灌百科 shard：与本轮刚测到的**新闻域**增益正交。

### v3 入口条件（下一循环）

1. MOT `cmn`（或等价 VOA 中文）dated dump pin 进 training-feed，SOURCES.md 写 verdict。
2. `train.sh` 混合 zhwiki + wikinews-20261001 + 新源，CJK ≥ 20M。
3. 完整 A/B：本 40 条 wikinews ctx + 既有 246 case；要求 ctx 面不回退、体积/RSS/延迟仍过 criteria。
4. v2 gram 继续留作回滚。

## 词库搭车项

`COVERAGE_SOURCE_IDS` / `COVERAGE_FREQ_DOMAINS` 纳入 `wikinews`。理由：adapter
只补缺失表面、计数不是 essay 量纲；若不纳入，2–3 字 auto 会掉进 `base` 热表。
预期落层 **bulk**，与 tencent-only 相同。locked pipeline 全量吸收见同日结案记录。

## 词库 locked pipeline（同日）

首次真实 locked 吸收 wikinews（fixture 路径早已覆盖）。新鲜 store，opencc 在场。

| 项 | 值 |
|---|---|
| wikinews-pages 新增 lemma | 7885 |
| 与其它源混合 | 0（只补缺失表面） |
| wikinews-only 落层 | **bulk 7885 / 7885** |
| emit_t2s_converted | 25433 |
| eval_failures / probe_failures | 0 / 0 |
| lemmas | 2,462,722 |
| emit_bulk | 698,296 |

`COVERAGE_SOURCE_IDS` 纳入 wikinews 的理由成立：若未纳入，2–3 字 auto 会进 base 热表。
产物在 `/Volumes/Backup/tmp/umate-lexicon-locked-20261001/`，并已 rsync -a 回本仓库 `dist/rime/` 与 `data/store/lemmas.sqlite`（均 gitignore）。未同步 VoiMate bundle。

## 后续（v3 循环已关闭）

GO 已执行：见 `2026-10-01-grammar-v3.md`。MOT 已 pin 并混合重训到 27.9M CJK，
但相对 v2 **ctx 回退 4 / 增益 0**，判定停留 v2、不换包。
