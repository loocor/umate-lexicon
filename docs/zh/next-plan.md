# 授权跑道（2026-09-23）

这是已确认的操作边界，不是新的产品决定。排序实验、新数据源、同步键盘都不在这张单里。

## 可以做

- 文档、盘点、测试、探针。
- 复审通过后的 merge commit。已于 `b0c5785` 合进 `main` 并 push。
- 闭集单字里，store 已有 gold / CC-CEDICT / Unihan / kHanyuPinlu 读音、但被单字门滤掉的，补进 `chars`。不改权重公式，不猜没有可信来源的读音。

## 不可以做

- 新 pin 数据源。
- 改 `HOT_WEIGHT_FLOOR`。
- 把纯 wiki / 纯 CC-CEDICT 再抬进热表。
- 从现有发射里剥离 share-alike 行。
- 为了四条已能全拼打出的词去抬词重。
- 同步 VoiMate、Host 编译、装机、发版。

## 已做的排序修正（2026-10-01 干跑，落地待确认）

分域记账：发射权重取最强单一频次列（essay 优先，其次 hanyu_pinlu / chars /
gold / thuocl* / luna / cedict），不同量纲不求和。THUOCL 的 df 本身是
百万级（版权 thuocl=13,204,281 vs essay=42,144），旧求和让 THUOCL 词压过
essay 全表。单字 essay 计数没有拼音，只让首选读音保留；次读音保留自己的
实测列，不回退旧 weight。多字词不动，避免 gold correction 抢走常用读音。
store 不回写；干净重灌时 essay 只盖首选读音。

干跑实测（现有 store 重发射，1,428,27 热投影行不变号）：328,533 行中
111,455 行权重变化，其中 87,612 行是 ±3 以内的标记尘埃；热投影缩 4,589 行
（全部仍在对应冷包，无覆盖丢失）；同码 TOP-1 翻转 992 / 233,158（抽样为
净改善：`e` 首位 `哦→额`、`zhu de` 首位 `朱德→住的`、`xie dai` 首位
`携带`）。19 条闭集次读音落地权重 1–3。`青团`（essay 468）被 2 字 essay
碎片闸（<500）挡在热投影外，属 P1 调优候选，本轮不动。

## Share-alike 冻结

CC-BY-SA（CC-CEDICT、中文维基）可否进入商业包，**没有记录过的法律结论**。当前是冻结，不是批准。

- 不把纯 CEDICT / 纯 wiki 再抬进热表。
- 也不在另一次确认前把它们从已经发出的表里剥掉。
- `NOTICE` 继续随表走。上架前仍要人做法务判断。

`02edd7b` 已经把有类型的 wiki-only 放进对应 pack，冷权重 100；`page_len` 分层达到热表门槛的未分类型条目会进 bulk，并因此进入 `umate_hot_tail`。这是已合并、且键盘 YAML 已经对齐的行为，本跑道不回滚，也不再扩大。

## 探针

`data/gold/emit-probes.tsv` 只做判定，不进 gold。`eval` 会跑它。回退就停。

四条用户缺口仍只分诊：偷偷 / 多少是 `present-shipped`，连着 / 出门是 `present-ranked-low`。不入库。

## 停下条件

多音丢失读音补完、发射 diff 和探针结果写清之后停。下一步若要做，必须另一次确认：排序实验、新词频源、share-alike 剥离或正式接受、同步键盘。

## 不要做的事

不 ingest rime-ice、rime-frost、melt_eng、商业细胞词库。LLM 不造词。ASR 热词、Snippets、IME 用户词库不并库。空闲联想仍是键盘静态表。octagram 实验不吸进本仓库。
