# umate-lexicon

uMate 的 **词库工厂**：许可清楚的公开素材进去，版本化的 Lemma 库在中间，Rime 能消化的分层码表出来。

本仓库为了本地一起推进，放在 VoiMate 工作树目录下，但 **仍是独立 git 仓库**，不是键盘仓库里的包或 submodule。路径：`/Volumes/External/GitHub/VoiMate/Lexicon`。VoiMate 继续做产品（键盘、语音账本、Host）。这里只生产中文词数据。

## 原委

Rime 引擎我们继续用。真正头疼的是词。

VoiMate 已经把 librime 嵌进 iOS 键盘，挂的是官方明月拼音 + 八股文 essay。引擎经典、本地、许可干净。数据偏书面、当代词薄，个人学习几乎没接上。键盘里现场编译词典还会把扩展进程打到 jetsam 上限，所以词库只能 Host 预编译、键盘 mmap。

社区里「打着像 2026 年输入法」的方案（雾凇、万象）赢在词，不在 C++。雾凇仓库整体是 **GPL-3.0-only**。拷它的 schema、Lua、精修 `cn_dicts`，会把产品拖进 GPL。它的 *分层想法*（字表 / base / ext / 大覆盖、先 import 的权重生效、中英混输）可以学。实现必须对着 **上游 dump**：Unihan、CC-CEDICT、THUOCL、腾讯词向量词表、维基，并且每条词留下处。

官方 Rime 已经给过发射契约：`*.dict.yaml`、`import_tables`、librime 1.6 起的 `translator/packs`。雾凇是这份契约的一份手修产品。我们做的是工厂。

YAML 不是真相。真相是 Lemma：主键 `(词, 无调拼音)`。多音字拆开计数。大词表不允许「有词无码」除非能证明每个字都是单音。

## 「至少达到雾凇」指什么

- **结构：** 不少于冰的层，再加上 pack 化、出处、多音闭集、评测门。
- **规模：** 覆盖率和首选质量，不是去追 `tencent.dict.yaml` 的行数。
- **不是：** fork 雾凇，也不是把爬虫当主语料。

清洁室规则见 [CLEANROOM.md](CLEANROOM.md)。

## 流水线

```text
钉死的 dump
  → ingest（打许可、清洁室门）
  → lemma store
  → enrich（多音闭集、分类）
  → verify（规则 + 金标 + 可选 LLM 检查器）
  → emit 分层 dict.yaml + packs
  → Host 编译 table.bin / prism.bin
  → eval 不过不发版
```

LLM 只做分类和注音抽检，结构化 JSON，不准发明词条。金标测试拥有拼音：重庆不是 `zhong qing`。

全量原料由 `data/sources.lock.json` 钉死。先 `python -m umate_lexicon fetch`，再 `pipeline`（不要 `--fixtures`）。哈希不对就失败，不会改用 fixture。

官方明月词表、八股文频次、rime-emoji 可以吸收（LGPL，不是雾凇）。排序靠 essay 叠到已有 lemma 上；腾讯词向量只做覆盖，现钉两层：ModelScope **light 高频子集**（`tencent-light`）和 Hugging Face 固定 revision 的 Tencent AI Lab d200 v0.2.0 key 表（`tencent-d200-key-top1m`）。d200 key 表原文 12,287,936 行，当前只按原顺序流式取前 1,000,000 行，不下载 6.14 GB 向量本体。不要抄雾凇的 `tencent.dict.yaml`。tencent-only 的 unique compose 只进 bulk，不进默认 SKU；`domain_freq.tencent=1` 是覆盖占位，不改 essay 排序。light 吸收实测见 [docs/zh/tencent-light-absorb-2026-09-16.md](docs/zh/tencent-light-absorb-2026-09-16.md)。ModelScope 卡片上的 Apache-2.0 是包装许可；上游词表内容按腾讯 AI Lab CC BY 3.0 署名，HF 镜像本身没有单独声明许可。emoji 只作为可选 pack / OpenCC 映射发出，默认 schema 不挂上。

字级繁简折叠、8105、维基标题、拉丁品牌金标已经进 locked pipeline。维基补了同日 `page`/`categorylinks` 做重定向排重和类型记账；wiki-only 仍只进 bulk，条目长度不当词频。覆盖盘点见 [docs/zh/inventory.md](docs/zh/inventory.md)。CI 继续走 fixture；本地 `fetch` 会拉约 111MB 的 light `.bin` 和约 118MB 的 d200 GBK key 表。


## 和 VoiMate 的边界

键盘默认包：核心 + ext + 人名/品牌瘦包。大覆盖和时效 pack 可卸。Voice Ledger 仍是权威账本；确认过的句子以后可以 *投射* 成个人 pack，ASR 不能直接改 Rime User DB。
