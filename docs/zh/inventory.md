# 词库盘点（2026-09-16）

本地 `lemmas.sqlite`（不入库）约 24 万条，来自 Unihan + CC-CEDICT + THUOCL。
YAML 不是真相；发版看金标和 lock。

## 这一轮补遗

写进 `data/gold/product-terms.tsv`（`umate-gold`，不是叠 `umate.dict.yaml`）：

- 缺词：`大模型`、`提示词`、`多模态`、`向量库`、`umate`
- 已有但权重只有 1、需要权威读音：`微信`、`抖音`
- 纯拉丁金标进 `brands`，才能进默认 SKU（core+ext+names+brands）
- 不把 `llm` / `rag` / `mcp` 塞进中文表：三个字母进不了 AOSP（≥4），那是 VoiMate 排序策略，不是缺汉字

## 仓库里已经有、但权重弱

`智能体`、`上下文`、`幻觉`、`微调`、`对齐`、`人工智能`、`小红书` 都在，多半是 CEDICT 的 weight=1。
要追上雾凇手感，下一步是许可清楚的频次源（腾讯词向量词表一类），不是再手写一份 210 词补丁。

## 还没做

- 吸收官方 luna / essay（合法源，不是 rime-ice）
- 通用规范汉字 8105 字表（locked pipeline 目前靠 Unihan）
- `events` / `corrections` pack 仍空
- 不要把 `dist/rime` 接到键盘；Host 编译后才 mmap
- 不要把 A–Z 音节行交给当前 luna_pinyin
