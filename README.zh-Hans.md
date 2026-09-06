# umate-lexicon

uMate 的 **词库工厂**：许可清楚的公开素材进去，版本化的 Lemma 库在中间，Rime 能消化的分层码表出来。

本仓库是 **VoiMate 的兄弟项目**，不是键盘仓库里的一个包。VoiMate 继续做产品（键盘、语音账本、Host）。这里只生产中文词数据。

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

## 和 VoiMate 的边界

键盘默认包：核心 + ext + 人名/品牌瘦包。大覆盖和时效 pack 可卸。Voice Ledger 仍是权威账本；确认过的句子以后可以 *投射* 成个人 pack，ASR 不能直接改 Rime User DB。
