# 评测语料源登记

语料分两种用途，任何新文件入库前必须在此登记：

- **eval-only**：仅用于本仓库内部评测对比，不对外分发。
- **training-feed**：作为 `.gram` / 词频统计的训练输入，会形成分发
  衍生物，许可必须商用清洁（评审结论与日期标注在行内）。

分工边界：本表只管**评测/训练语料**；词库 ingest 的 adapter 合同在
`docs/sources.md`，来源准入策略在 `docs/source-policy.md`（中文版
`docs/zh/source-policy.md`）。一处来源只登记一次，其他文档用指针。

| 文件模式 | 来源 | 用途 | 许可 | 采集方式 | 状态 |
|---|---|---|---|---|---|
| `zhihu_<topic>.txt` | 知乎热榜问答正文 | eval-only | 用户内容默认许可含 NC 变体；进入训练前需逐篇评审 | 内部浏览器 AX 提取 | 活跃（13 篇） |
| `wikinews_<yyyymmdd>-pages.tsv` | 中文维基新闻 zh.wikinews.org | training-feed（.gram v2 已消费）+ 词库 adapter | CC BY 4.0（站方版权页 2026-10-01 核对；署名即可、允许商用；.gram NOTICE 附署名） | `scripts/fetch-wikinews.py`（MediaWiki API，断点续传，t2s 后落盘） | 已采数（2026-10-01 批次：ns0 全量 20,736 篇，kept 10,074 / 8.7M 字符；skip 诊断见 data/eval/rounds/2026-10-01-grammar-v2.md） |
| `gongbao_<yyyymmdd>.txt` | 国务院公报 gov.cn/gongbao | training-feed 候选（有条件） | 著作权法第五条第(一)项：法规与行政性质文件不受保护；公报内讲话、解读类仍受保护，须按篇过滤 | 逐期抓取 | 待逐篇过滤规则复核 |

## 采集纪律

- 每轮只追加新文件，不改写旧文件，保证轮次指标可比。
- 文件名即来源标识；未登记的文件不得进入 corpus 目录。
- `.gram` v2 训练启动前，training-feed 清单必须全部带许可结论。
| `wikimedia_dumps_*.xml.bz2`（zhwiki pages-articles shard p1p187712、wikivoyage dump） | Wikimedia dumps（dumps.wikimedia.org） | training-feed（.gram v1 已消费；raw dump 不入库、不入 bundle，仅衍生统计分发） | GFDL + CC BY-SA 3.0 双许可，按 CC BY-SA 3.0 分支分发衍生 .gram；与词库 wiki 通道（cc-by-sa-wikimedia，已在 bundle）同级先例；条件：分发物 NOTICE 附署名（2026-10-01 verdict，依据 dumps.wikimedia.org/legal.html 与 Wikipedia:Licensing update） | `Scripts/experiments/octagram-grammar/fetch_corpus.sh` 直连下载 | .gram v1 已消费；NOTICE 署名 2026-10-01 补齐 |
## 2026-10-01 扩充源评审（.gram v3 候选）

域内 ctx A/B 已证明 wikinews 搭配增益可测（+13 / 0 回退），v3 走扩新闻语料而不是
再堆百科。下列来源只在本表登记评审结论；**未 pin sha256 的不得进入 train.sh**。

| 文件模式 | 来源 | 用途 | 许可 | 采集方式 | 状态 |
|---|---|---|---|---|---|
| `mot-cmn-voa-*.jsonl`（拟定） | MOT v1.11 Mandarin / Voice of America | training-feed 候选（.gram v3） | VOA 雇员作品公有领域（17 U.S.C. § 105）；MOT 汇集声明 CC BY 4.0（arxiv:2201.05609，bltlab/mot） | GitHub Release 按语言 tarball，只取 `cmn` | 评审通过、**尚未 pin**；下一循环下载、hash、NOTICE 署名后才能训 |
| `newsdata-io-*` | Newsdata.io free datasets | 不采用 | 数据集包 CC BY 4.0，但条款写明底层文章仍归原出版社 | — | **否决**：不能把出版社稿件洗进商用 .gram |
| `cc-news-*` / INFINI-NEWS | Common Crawl 新闻聚合 | 不采用 | 原站版权 | — | **否决** |

wikinews 滚动：API 只读后仍可 dump；每轮新文件 `wikinews-<yyyymmdd>-pages.tsv`，
bump `data/sources.lock.json` hash，禁止改写旧快照。

