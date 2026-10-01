# 真实数据验证体系：第一轮评测报告

## 日期

2026-10-01

## 语料

三篇知乎真实文章，覆盖不同域：

| 文件 | 域 | 大小 |
|------|-----|------|
| `data/eval/corpus/zhihu_dishwasher.txt` | 科普/生活（洗碗机玻璃白雾） | 8.4 KB |
| `data/eval/corpus/zhihu_cooking.txt` | 日常生活（猪肝烹饪） | 9.5 KB |
| `data/eval/corpus/zhihu_vim.txt` | 技术/编程（vim 编辑器） | 3.6 KB |

## 评测方法

`scripts/eval_corpus.py`：
1. jieba 分词提取中文词（≥2 字）
2. 覆盖检查：该词是否存在于任何 `dist/rime/*.dict.yaml`
3. 排序检查：该词的拼音对应的 TOP-1 是否为该词

## T2S 修复前后对比

| 指标 | 修复前 | 修复后 | 变化 |
|------|--------|--------|------|
| 词典总行数 | 884,206 | 873,971 | -10,235（去重） |
| 覆盖缺口 | 137 | 135 | -2 |
| 排序缺口 | 208 | 195 | -13 |

### T2S 修复详情

OpenCC `t2s` 在 emit 层强制转换，一次性转换 **20,207 条**繁体条目。

典型修复案例：
- `乾淨 gan jing w=35647` → `干净 gan jing w=35646`（TOP-1 修复 ✅）
- `週期 zhou qi w=48690` → `周期`（TOP-1 修复 ✅）
- `一週 yi zhou w=46299` → `一周`（TOP-1 修复 ✅）
- `兇手 xiong shou w=18081` → `凶手`（TOP-1 修复 ✅）
- `上週 shang zhou w=12312` → `上周`（TOP-1 修复 ✅）

## 剩余问题分类

### 排序缺口（195 条）

**子类 A：同音词频次校准**（需要 P0 验证改善）
- `清洗` 输给 `清晰`（w 23,943 vs 目标更低）
- `高效` 输给 `高校`（w 32,376）
- `侵蚀` 输给 `寝室`（w 4,338）

**子类 B：低权重同音词排序噪声**（TOP-1 和目标词都是 w=1 或极低）
- `上周` TOP-1=`商周` w=1
- `家里` TOP-1=`佳丽` w=1
- 这些说明频次源对这两个词都没有高权重数据

**子类 C：量词/数词+名词组合**
- `一只` 输给 `一直`（w 43,221 vs 更低）
- `一片` 输给 `一篇`（w 30,156）
- 这些是正常排序（`一直` 确实更常见），但在烹饪语境下应该选 `一只`

### 覆盖缺口（135 条）

**子类 A：真实日常域词汇**（值得补入）
- `宽油` `滑油` `炙锅` `底味` `发柴` `上浆`（烹饪域）
- `洗碗粉` `软水盐` `丝瓜络`（生活域）

**子类 B：jieba 过度分词的假阳性**（不需要修）
- `油少` `一激` `先滑出` `发柴` 等 3+ 字短语碎片

## 与 VoiMate 主项目的连接

修复后需要：
1. 同步 `dist/rime/` → `Extensions/uMateKeyboard/RimeSharedData.bundle/`
2. 在实际键盘上下文验证 TOP-1 修复效果

## 下一步

1. P0 + T2S 合 main → 重新 emit → 同步 bundle
2. 重跑评测确认排序改善幅度
3. 扩充评测语料（增加到 500+ 句）
4. octagram 上下文评测（需要 librime probe）

## 2026-10-01 知乎热榜语料扩充（9 篇）

语料从 4 篇扩到 9 篇，新增五个知乎热榜问答主题（永动机、程序员 AI、
机械硬盘、升职加薪、老派过节）。分词 9680 次，唯一词 3751 个。

- 覆盖：244 个 OOV 词，全部落在 `segmentation` 桶——单字层无缺口，
  多数是 jieba 分词伪影（如"水一""版卖"）。少量真实词组缺口中 8 个
  高价值词（共沸剂、不摆烂、跑通、底味、糊锅、划散、发柴、任前）
  已记入 `data/gold/daily-gaps.tsv`，供后续 phrase-curation 通道补录。
- 排序：560 个缺口，主体是高频词同音竞争（工作 54 次、这个 50、
  月球 49、玻璃 44）。逐词调频无法安全修复这类竞争（"知识/只是"、
  "任务/人物"取决于上下文），结构性出路是 octagram 上下文模型；
  词频 override 层只适合处理无歧义词对，作为权宜手段。
- 工具：新增 `scripts/triage_coverage.py`，基于 lemma store 对 OOV
  词做 missing/segmentation 分诊，保证只有真实缺口进入台账。

## 2026-10-01 第二轮：13 篇语料 + phrase-curation 通道

语料扩到 13 篇（新增 Mate 90 数码、番茄小说文娱、胖东来零售、炖肉
烹饪）。分词 14638 次，唯一词 5044 个。dist 从 875761 涨到 1461667
条（locked pipeline 全量重建，opencc t2s 生效）。

- phrase-curation 通道落地：`data/voimate/phrase-curation.tsv` +
  `ingest_phrase_curation()`（Tier-A weight 6000、固定 rank 1），
  首批 21 词覆盖台账 8 词与本轮新增 13 词（漫剧、变柴、血沫、微沸、
  软乎、七八分、没熟、沿锅边、闷味、抢味、典藏版、钉子户、炖牛肉）。
  覆盖缺口 431 → 308（-28.5%），全部仍为 segmentation 桶分词伪影
  或超长数字表达。
- 繁体回归发现与修复：无 opencc 环境跑 locked pipeline 时 t2s
  import-guard 静默降级 identity，乾淨(weight 11882, essay 域 47528)
  抢走干净 TOP-1。重建必须带 opencc；已在 test_corpus_eval 既有
  断言下复测通过（127 passed）。
- 排序缺口 850 → 919：dist 规模近翻倍后同音竞争面扩大，主体仍是
  上下文依赖词对，octagram 是结构性出路（P3 调研继续）。

### bundle 同步契约（2026-10-01 事故教训）

`RimeSharedData.bundle` 是共享领土：Lexicon 只拥有根目录的
`umate_*.dict.yaml`、`aosp_en.*`、`en_us_unigrams.tsv` 等数据文件；
schema、`build/`、`umate-zh-hans.gram`、`lua/`、`opencc/`、
`default.yaml` 等由 VoiMate 侧拥有。同步必须用 `rsync -a`（禁止
`--delete`），否则会删掉 VoiMate 侧 66 个 tracked 文件（本次已从
git 完整恢复，.gram 25,183,276 B 字节级核对一致）。
