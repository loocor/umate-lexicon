# 词库盘点（2026-09-16，wiki 分类排重后）

本地 `lemmas.sqlite` 和 `dist/rime/*.dict.yaml` **不入库**。YAML 不是真相；发版看金标、lock 和本盘点。

这一轮数字仍是 **wiki 分类排重后、腾讯 light 词表尚未跑进本盘点**。标题表没有拼音、没有收录时间、没有编辑次数；那些字段也不适合当输入法词频。分类和排重改走同一日期的 `page` / `linktarget` / `categorylinks` dump。

腾讯侧：官方 6GB dump URL 仍返回约 22KB HTML，**不要编哈希**。已在 `sources.lock.json` 钉死 ModelScope / Hugging Face 的 light Word2Vec 词表（`light_Tencent_AILab_ChineseEmbedding.bin`，143613×200），只抽词、不当词频，不抄雾凇 `tencent.dict.yaml`。本盘点数字还未叠加这次 ingest。

## 规模（locked dumps overlay，eval 0 failure）

| 项 | 数量 | 说明 |
| --- | ---: | --- |
| lemmas | **1311126** | 条数没变，状态变了 |
| 独特表面 | 1301130 |  |
| wiki-only | 844275 | 仍全部 **bulk**，默认 SKU 不带 |
| wiki-only 重定向 | **378018** | `status=rejected`，`wiki_redirect` |
| wiki-only 未类型 | 693749 | 含已拒绝重定向 |
| dropped | 442718 | 重定向 + 未闭合多音 + 未信任读音 |

发出分层：

| 层 | 行数 | 角色 |
| --- | ---: | --- |
| chars | 7877 | 8105 纪律未改 |
| base | 220353 | 2–3 字，essay/cedict/thuocl/gold |
| ext | 79592 | 4 字 + 金标长词 |
| bulk | **480869** | 维基非重定向为主；上次 775811 |
| places | **20721** | 金标省市 + THUOCL 等地名；上次 60562 是后缀误伤 |
| orgs | 43032 | 后缀泄漏已从 wiki-only 拿掉 |
| names | 11336 | 维基人物仍在 bulk，不进默认 names |
| emoji | 3585 | 默认 schema 仍不挂 pack |
| brands | 873 |  |
| mixed | 138 |  |
| events | 22 |  |
| corrections | 10 |  |

wiki-only 库存类型（**不改变发射层**，只记账）：

| entity | 数量 |
| --- | ---: |
| none | 693749 |
| person | 104527 |
| place | 26586 |
| org | 12190 |
| work | 7223 |

例：`一剑镇神州` 不再当地名；`一亩泉镇` 标 place 但仍是 bulk；`上海` 金标仍在 places。

## 维基 meta 能不能当词频？

不能。

| dump | 有什么 | 输入法词频？ |
| --- | --- | --- |
| `all-titles-in-ns0` | 只有标题 | 否 |
| `page` | `page_is_redirect`、`page_len`、`page_touched` | `page_len` 是条目字节，不是「的/了」。**禁止**写入 `domain_freq` |
| `categorylinks` + `linktarget` | 分类 | 类型，不是口语频次 |
| stub-meta-history（8GB，未拉） | 可算创建时间和编辑次数 | 百科热度 ≠ 口语。未用 |
| Wikidata P1721 拼音 | 极少 | 不够用 |

拼音：中文维基标题表没有拼音。条目 infobox 要 3.3GB XML；Wiktionary `{{zh-pron}}` 是另一份 dump。本轮继续 **unique compose**，不爬正文。

## 这一轮做了什么

1. **分层纪律：** wiki-only 一律 bulk。后缀 `镇/州/旗/公司` 不再把维基标题抬进 places/orgs。
2. **排重：** ns0 重定向且仅有 wiki 来源 → rejected。有 essay/cedict/thuocl 的词不杀。
3. **分类：** 保守类别标记（`年出生`/`年逝世`/`人物`，电影/电视剧等 ending，公司/大学，行政区划/乡镇）。不用裸 `作品`、不用 `科/属/种`。
4. **钉死** 20260901：`page` / `linktarget` / `categorylinks`，sha256 是下载后算的，没有编造。

## 明确还没做

1. 腾讯官方大 dump 仍是 HTML，未钉。light 词表已钉且做过 fetch/抽词/融合干跑（见 [../tencent-validation.md](../tencent-validation.md)）。**本盘点表没重跑**（跳过 wiki；CEDICT 是滚动文件，现网哈希已变，未编新哈希）。
2. 不把 bulk 放进默认 SKU。
3. 不把维基人物/作品用 pageviews 抬出 bulk。
4. 不接键盘，不抄雾凇。
5. 不把 word2vec 向量送进运行时；工厂只要词表。
