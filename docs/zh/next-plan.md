# 授权跑道（2026-09-23）

这是已确认的操作边界，不是新的产品决定。排序实验、新数据源、同步键盘都不在这张单里。

## 可以做

- 文档、盘点、测试、探针。
- 复审通过后的 merge commit。已于 `b0c5785` 合进 `main` 并 push。
- 闭集单字里，store 已有 gold / CC-CEDICT / Unihan / kHanyuPinlu 读音、但被单字门滤掉的，补进 `chars`。不改权重公式，不猜没有可信来源的读音。

## 不可以做

- 新 pin 数据源。
- 改 `HOT_WEIGHT_FLOOR` 或权重公式。
- 把纯 wiki / 纯 CC-CEDICT 再抬进热表。
- 从现有发射里剥离 share-alike 行。
- 同步 VoiMate、Host 编译、装机、发版。

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
