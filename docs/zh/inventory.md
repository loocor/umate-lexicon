# 词库盘点（2026-09-16，t2s 全量 emit 后）

本地 `lemmas.sqlite` 和 `dist/rime/*.dict.yaml` **不入库**。YAML 不是真相；发版看金标、lock 和本盘点。

结论先说：**还远没到「不用再堆源」**。这一轮把繁简折叠和官方 luna / essay / emoji 跑通了，得到一份能编译的简体底盘。覆盖和排序都还不够支撑「中英混输、手感追上雾凇」——差的是许可清楚的当代频次源、专名源和分层纪律，不是再手写一包残词。

## 规模（locked pipeline，eval 0 failure）

| 项 | 数量 | 说明 |
| --- | ---: | --- |
| lemmas | 393105 | 主键 `(词, 无调拼音)`，多音字拆行 |
| 独特表面 | 383930 |  |
| 发出行合计 | 378468 | 不含空的 events / corrections |
| dropped | 14638 | 多半是未闭合的多音字，不进 YAML |
| gold | 11 | 只锁读音和少数产品词，不是词库主体 |

发出分层（`dist/rime`）：

| 层 | 行数 | 角色 |
| --- | ---: | --- |
| chars | 27318 | 核心字表。来源主要是 Unihan，**稀有扩展区偏多**，不是 8105 通用规范汉字 |
| base | 167765 | 2–3 字，日常主体 |
| ext | 54665 | 4 字 |
| orgs | 42725 | 分类噪声大，THUOCL industry 桶混了不少普通词 |
| bulk | 36019 | 更长或未归层 |
| places | 35190 | 地名 + 误伤（如「开源」来自 THUOCL 地名表） |
| names | 11336 | 人名，历史名人好于当代名人 |
| emoji | 2483 | 触发词表；默认 schema **不** 挂 pack |
| brands | 828 | 几乎没有拉丁品牌 |
| mixed | 138 | 中英夹杂极少 |
| events | 0 | 空 |
| corrections | 0 | 空 |

权重公式仍是 `round(100 * log1p(domain_freq 合计))`。essay 叠上之后，「的」1539、「银行」1054、「微信」1040；金标但 essay 没有的「大模型」只有 691。

## 源与许可

lemma_sources 计数（一条 lemma 可挂多个源）：

| 源 | 许可 | 约 |
| --- | --- | ---: |
| essay | LGPL-3.0（官方 rime-essay） | 281220 |
| cedict | CC BY-SA | 121950 |
| thuocl | MIT | 98182 |
| luna | LGPL-3.0（官方 rime-luna-pinyin） | 48777 |
| unihan | Unicode | 44413 |
| emoji | LGPL-3.0（官方 rime-emoji） | 2483 |
| gold | umate-gold | 11 |
| tencent | CC BY 3.0 | **0**（适配器有，lock 未钉；官方 tar.gz 仍是 22KB HTML） |

THUOCL 已进：IT / 动物 / 财经 / 汽车 / 成语 / 地名 / 食物 / 法律 / 历史名人 / 医学 / 诗词。这是领域补丁，不是当代互联网总表。

LGPL 官方包已经在 VoiMate 键盘里用过，**不**要求输入法开源。禁止的是 GPL-3.0-only 的 rime-ice 成品表。

## 分域：有什么、缺什么

### 中文核心

常用字词在。essay 把书面频次抬起来了，「的 / 你好 / 银行 / 一个 / 可以」都像能打的词。

但 luna 繁体读音经**字级** t2s 叠到简体表面后，会留下多余读音，essay 还按表面给所有读音加同一频次：

- `我` 同时有 `wo` 和 `e`（后者权重同样百万级）
- `什么` 同时有 `shen me` 和 `she me`
- `和` 有 `han`（review）

这是读音合并策略问题，再堆词表解决不了。

chars 层 2.7 万，含大量扩展 A/B 生僻字（约 2.1 万条表面不在 CJK 基本区）。手机核心字表应该先钉 **8105**，而不是把 Unihan kMandarin 整表塞进 chars。

### 英文

**本工厂几乎不做英文。** 非汉字表面大约 40 条 ASCII，金标只有 `umate`。

键盘现在用的是 VoiMate 里那份 AOSP 英文表：约 **125923** 行、≥4 字母 unigram。`python` / `apple` / `name` / `iphone` 在；`ChatGPT` / `OpenAI` / `GitHub` / `llm` / `rag` / `mcp` / `gpu` 不在。短拉丁进不了这份 AOSP，是排序策略，不是缺汉字。

中英混输要的 mixed / 品牌拉丁，当前 emit 只有 138 + 828，远远不够。

### 人名

names 1.1 万。THUOCL 历史名人 + CEDICT：李白、孔子、秦始皇、曹雪芹、鲁迅、孙中山都在，权重可用。

当代：马云 / 马化腾在；雷军被打成 industry；刘强东缺失；马斯克只有 CEDICT weight=1。缺一份许可清楚的当代人名 / 维基标题源。

### 专名 / 品牌 / 机构

互联网常用词参差：

- 有且 essay 能抬：微信、抖音、微博、淘宝、支付宝、腾讯、华为、百度、小红书、快手、知乎
- 有但几乎没频次：哔哩哔哩、字节跳动、拼多多、短视频（CEDICT=1）
- 缺：美团、得物、闲鱼、视频号、腾讯会议
- 拉丁品牌缺：iPhone、iPad、GitHub、ChatGPT、OpenAI、NVIDIA

「苹果」被 THUOCL 食物表打到百万频次，entity=industry，会污染品牌义。

orgs 4.2 万看起来很大，很多是 THUOCL 文件名映射成 industry，不是真机构。

### Emoji

发出 2483 条触发 + `opencc/emoji_word.txt` 旁路。默认 schema 不挂 `umate_emoji`，键盘也不要自己开 OpenCC。

「哈哈」在汉字表里很重，官方映射是 😄+VS；「笑哭」「好的」「ok」作为触发还不在。要加触发就写 gold / 独立 emoji 源，不要再叠 210 条杂补丁。

### 现代网络 / IT / AI

IT 汉语基本词大多在（编程、数据库、服务器、云计算、微服务、区块链、芯片），权重靠 essay/THUOCL。

明显缺口：

- 缺词：大语言模型、提示工程、向量数据库、检索增强、云原生、预训练
- 在但弱：智能体（CEDICT=1）、生成式
- 拉丁开发词：本表故意不收 `llm`/`rag`/`mcp`；`Python`/`GPU`/`ChatGPT` 也不在本工厂

金标目前只有：大模型、提示词、多模态、向量库、微信、抖音、umate。这是补遗，不是 AI 词表。

### 地名

省市和常见世界城市作为**词**大多能打出来（北京、重庆、昆明、新疆、香港、纽约、新加坡）。分层不稳定：北京/广州进 places，上海/深圳/重庆进 base，珠江被标成 industry。

「开源」进 places：THUOCL 地名表里有这个表面，和「open source」撞车。分类要用白名单/金标压，不能指望文件名。

还没有行政区划层级、乡镇、POI。Wikimedia / 官方区划是下一类源，不是再手写几个市名。

### 历史

成语、诗词、历史名人够「能打」，偏书面。THUOCL 诗词/成语是文学覆盖，不是当代口语。events 层全空，没有「朝代 / 战役 / 节日」独立包。

## 这一轮已经做完

- Unihan `kSimplifiedVariant` 字级 t2s；luna / essay / emoji / tencent 表面折到简体
- `银行` gold + essay 36856 → 发出权重 1054；`銀行` 不再占一行
- `微信` gold + essay 31877 → 1040
- 官方 luna / essay / rime-emoji 进 lock（LGPL，不是雾凇）
- `make inventory` 可对当前 store 复盘

## 还没做、而且应该做的源（按杠杆）

1. **真实腾讯词向量词表**（CC BY 3.0）：当代覆盖 + 非书面频次。现在是最大缺口。禁止编造哈希，禁止抄雾凇 `tencent.dict.yaml`。
2. **Wikimedia 标题**（CC BY-SA）：人名、机构、作品、现代专名。Share-alike 要打标，默认 SKU 要想清楚。
3. **通用规范汉字 8105**：替换 Unihan 生僻字当核心字表。
4. **拉丁 / 混输品牌表**：iPhone、GitHub、ChatGPT 这一档；短缩写仍走键盘策略，不塞进中文 gold。
5. **events / corrections**：现在是空文件头。
6. **读音合并**：字级 t2s 之后，luna 多余读音不要再吃 essay 整表面频次。
7. **分类纪律**：THUOCL 文件名 ≠ 实体类型；「开源」「苹果」「上海」要金标或规则压层。

短语级 OpenCC（`什麼`→`什么` 连带读音）可以后做。用户词库、教育键盘是产品侧，不进工厂补丁包。

## 明确不要

- 不要把 `dist/rime` 接到键盘；Host 编译 `table.bin` 后才 mmap
- 不要开键盘 OpenCC；emoji pack 先不进 `translator/packs`
- 不要把 A–Z 音节行交给当前 QWERTY `luna_pinyin`
- 不要 fork 雾凇 / 万象，不要搜狗细胞词库
- 不要为了几个样例再叠 `umate.dict.yaml` 式零散补丁

## 怎样才算「可以少堆源」

不是行数追上雾凇的 tencent 表。最低限度：

- 8105 字表进核心，生僻扩展字退出 chars
- 腾讯词表或同等许可的当代频次真正 ingest
- 维基标题补专名，金标压住撞车和多音
- mixed/brands 能打常见拉丁产品名
- events/corrections 不再是空包
- eval 从 8 句金标扩成「首选命中」集

在那之前，继续收集是对的；但收集必须进 lock 的上游 dump，不要再拆成一堆残缺小文件。
