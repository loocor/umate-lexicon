# 词库盘点（2026-09-16，覆盖推进后）

本地 `lemmas.sqlite` 和 `dist/rime/*.dict.yaml` **不入库**。YAML 不是真相；发版看金标、lock 和本盘点。

结论：**五件事推了四件半。** 8105、维基标题、拉丁品牌、读音合并/分层纪律、events/corrections 已经进工厂。腾讯词向量官方 URL 仍是 22KB HTML，**没有编造哈希，没有抄雾凇**，适配器继续待命。还没接到键盘。

## 规模（locked pipeline，eval 0 failure）

| 项 | 数量 | 说明 |
| --- | ---: | --- |
| lemmas | **1311126** | 上次 t2s 后 39 万 |
| 独特表面 | 1301130 |  |
| wiki 新词 | 844275 | 只进 bulk（默认 SKU 不带） |
| dropped | 99124 | 未闭合多音 + 未信任读音不发射 |
| gold | 182 | 读音、产品、地名、节日、品牌、纠正 |

发出分层：

| 层 | 行数 | 角色 |
| --- | ---: | --- |
| chars | 7877 | **8105 纪律**：Unihan kTGH 打标，生僻扩展字不再进核心字表（上次 27318） |
| base | 220353 | 2–3 字，essay/cedict/thuocl/gold |
| ext | 79592 | 4 字 + 金标长词（大语言模型等） |
| bulk | 775811 | 维基标题为主，full SKU |
| places | 60562 | 金标省市 + 带地名后缀 |
| orgs | 51843 |  |
| names | 11336 |  |
| emoji | 3585 | 默认 schema 仍不挂 pack |
| brands | 873 | 含 iPhone/ChatGPT/GitHub 等拉丁金标 |
| mixed | 138 |  |
| events | 22 | 春节等，不再空包 |
| corrections | 10 | 两岸别称码，不再空包 |

## 五件事对照

1. **腾讯词向量**：未钉 lock。`ai.tencent.com` 两个历史 tar.gz 都返回 22KB HTML。禁止编造哈希。ingest 仍可 overlay 已有词、收 2–4 字新词。
2. **Wikimedia 标题**：钉 `zhwiki-20260901-all-titles-in-ns0.gz`（sha256 `7af018a9…`）。只收 2–8 字纯汉字、能唯一注音的新表面。**仅 wiki 来源的 2–4 字进 bulk**，不进默认 core/ext。
3. **8105**：Unihan `kTGH`（`unihan-tgh`）。发出 chars **7877**（部分规范字没有 kMandarin，无法单独成行）。生僻扩展 A/B 不再进 chars。
4. **拉丁/混输品牌**：`data/gold/latin-brands.tsv`。iPhone、ChatGPT、GitHub、Python、OpenAI 等在 brands。短缩写 `llm`/`rag`/`mcp`/`GPU` 仍不进中文表。
5. **读音合并 + 分层 + events/corrections**
   - essay 只叠到受信任读音（gold/cedict/unihan/chars）。`我/e` 不再吃 119 万 essay，flag `untrusted_reading`，不发射。
   - 2–3 字 THUOCL 地名无后缀且非 gold → 不当 place。`开源`、`苹果` 回 base；`上海` 金标 places。
   - events 22、corrections 10。

## 分域

- **中文核心**：常用词仍在，chars 从 2.7 万收到约 8 千。`银行` 1054，`的` 1539。
- **英文**：工厂仍几乎不做英文。拉丁品牌约 45 条金标。键盘 AOSP ~12.6 万未动。`llm`/`rag`/`mcp` 仍不收。
- **人名**：历史名人可用。马斯克仍弱（CEDICT=1）。维基人名在 bulk，默认 SKU 看不见。
- **专名/品牌**：美团/得物/闲鱼/视频号已金标。哔哩哔哩、字节跳动仍几乎没频次。
- **Emoji**：笑哭、好的已金标汉字；官方 emoji pack 仍不挂 schema。
- **IT/AI**：大语言模型、提示工程、向量数据库、检索增强、云原生、预训练已金标。智能体仍弱。
- **地名**：金标省市进 places。开源不再占 places。
- **历史**：events 只覆盖节日，不是朝代/战役包。

## 还缺、而且应该继续收集

1. **真实腾讯词表 dump**（官方复活或可核验镜像）。没有它，当代口语频次仍靠 essay。
2. 维基标题没有类型：人物/作品大量在 bulk，默认打不出来。下一步是 Wikidata 类型，不是再手写人名。
3. 8105 里缺 kMandarin 的约两百字，要用 通用规范汉字表 正文或 kTGHZ2013 补读音。
4. 用户词库 / 教育键盘仍是产品侧。
5. 不要为了样例再拆补丁文件。金标按用途各一份：`product-terms` / `latin-brands` / `places` / `events` / `corrections` / `layer-overrides`。

## 明确不要

- 不要把 `dist/rime` 接到键盘；Host 编译后才 mmap
- 不要把 bulk（维基）放进默认 SKU
- 不要开键盘 OpenCC
- 不要 fork 雾凇，不要给腾讯编哈希
