# 授权跑道（2026-09-23）

这是已确认的操作边界，不是新的产品决定。

2026-10-01 另一次确认：ranking r1（emit 提权表）已授权落地；词库 YAML 可用官方 `Scripts/sync-lexicon-rime-to-bundle.sh` 同步键盘，仍不改引擎线程未提交文件，rsync 禁止 `--delete`。新数据源 / `HOT_WEIGHT_FLOOR` / 纯 wiki-CEDICT 抬热表仍冻结。

## 本轮（codex/lexicon-coverage-ranking，2026-10-03）

沿用 2026-10-01 目标模式：知乎 13 篇只当传感器；只修类 A；不改 `HOT_WEIGHT_FLOOR`；
不把知乎写进 lemma / .gram。

覆盖：TGH 单字先于 THUOCL industry/org 落 `chars`（鸮/鸰等），并把 TGH 扩展区
1 字纳入同一扇门（㑇 等 273 字）。呒/呣 的 `ḿ` 清洗仍不动。

排序：类 A 的繁简失重改为发射继承，不再靠继续加提权表。
简体 `ranking_freq <= 1` 才继承折叠来的繁体列，max 不求和；已有实测列不吸收。
知乎-13 覆盖仍 274，排序 861→848。类 C 未翻。提权表保留作近 tie 安全网。
覆盖短语：`肝片`、`共沸` 仍走 phrase-curation。锅气 / 钾碱 仍是 rejected wiki_redirect，不洗白。
键盘同步 / Host 编译仍另走。

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
- Host 编译、装机、发版（词库 YAML 同步见文首 2026-10-01 确认）。

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

CC-BY-SA（CC-CEDICT、中文维基）**作为热表权重来源**可否进入商业包，**没有记录过的法律结论**。当前是冻结，不是批准。

层面区分（2026-10-01）：本节冻结的是**词库发射权重**（纯 CEDICT/wiki 抬进热表）；**.gram 训练语料**属另一层面，其 CC BY-SA verdict 已按 training-feed 纪律单独记录在 `data/eval/corpus/SOURCES.md`（zhwiki/wikivoyage dumps，GFDL+CC BY-SA 3.0 取 CC 分支，NOTICE 署名已补），两条线互不扩大、互不回滚。

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

## 生僻字 curation（2026-10-03）

新增 `data/voimate/rare-char-curation.tsv`（surface→拼音，ingest 走
`ingest_rare_char_curation`，层判定进 `chars`，权重走 curated 档）。首批只有
`𰻝 biang`（U+30EDD）。

判定依据（本机实测，非推断）：

- **字体**：CoreText `CTFontGetGlyphsForCharacters` 在活动苹方 SC 上对
  𰻝/𰻞 返回 True；磁盘 AssetsV2 里的 PingFang.ttc 是陈旧副本，不能作为
  字体判定依据。SIP 变体 𱿗 (U+31FD7)、𲁓 (U+32053) 无系统字形（会落
  LastResort），不收录。
- **OpenCC 折叠**：官方 t2s 把 𰻞 (U+30EDE) 规范化到 𰻝，与 淨→净 同一
  机制；emit 只出 𰻝。测试环境无 opencc 时 t2s 降级恒等，写测试时不得
  假设两个 glyph 同时出货。
- **脏数据**：cedict 用 □ (U+25A1) 顶替无法编码的字（□|biang、□|biu、
  □|ging），ingest 已加占位符闸，存量三行已置 rejected。

`han_len` 已扩展（同日）：`_HAN` 覆盖 Ext A / BMP / 兼容区 / Ext B-H，
`𰻝𰻝面` 正确数成 3 字、进 bulk。全库 246 万条新旧层模拟：仅约 1,200 条
含扩展区汉字的真实词组从 None/base/bulk 归位（None→base 610、None→bulk
460、base/bulk→ext 186、bulk→base 27、base→phrases 3、ext→bulk 9）；
5 条 review+polyphone 五字变体词被收严为不发射，符合政策。chars/names/
places 热表零变动。
