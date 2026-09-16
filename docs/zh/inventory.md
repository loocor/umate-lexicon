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

## 这一轮吸收

- 官方 luna / essay / rime-emoji 已进适配器和 lock（LGPL，不是 rime-ice）
- essay 给已有词叠频次：`微信` 31877，`的` 4822928。这是重排，不是再手写补丁
- luna 词表是繁体；精确表面才能叠 essay，所以 `銀行` 暂时不会改写 `银行`
- emoji 发出 `umate_emoji.dict.yaml` + `opencc/emoji_word.txt`，默认 schema **不** 挂 pack，键盘也不要自行打开 OpenCC
- 腾讯词向量：适配器和抽词脚本已有。官方 tar.gz 目前是 22KB HTML，未钉 lock，禁止编造哈希，禁止抄雾凇 `tencent.dict.yaml`

## 还没做

- 繁简折叠（t2s ingest），让 essay 的 `銀行` 能抬升 `银行`
- 钉一份真实的腾讯词表 dump
- 通用规范汉字 8105 字表（locked pipeline 目前靠 Unihan）
- `events` / `corrections` pack 仍空
- 不要把 `dist/rime` 接到键盘；Host 编译后才 mmap
- 不要把 A–Z 音节行交给当前 luna_pinyin
