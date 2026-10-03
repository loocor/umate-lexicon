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

## 轮次流程固化与遗留子目标（2026-10-01 决策）

杯水车薪问题的定位：语料轮是传感器不是修理厂——它负责发现系统性
缺口，批量修复走数据源/管道层，单条 curated 修复只做高价值个案。
为此固化三件工具：

- `scripts/round_report.py`：一轮一条命令，产出 `data/eval/rounds/`
  的 delta 报告（含缺口率/千词、分源统计），并维护 `latest.json`
  快照；同口径系列自 r2 起（唯一词口径）。
- `data/eval/corpus/SOURCES.md`：语料源登记表，区分 eval-only 与
  training-feed，采集纪律（只追加不改写、未登记不入库）。
- `data/eval/probe-cases.tsv`：排序缺口导出的同音竞争用例
  （pinyin/expected/current_top1/weight/freq/sources），供 VoiMate
  `umate_grammar_probe` 扩充 octagram A/B case 集。

原 goal 三段子目标中，harness 已完成；剩余两项转入常规轮次，
不再使用 goal 预算推进：

1. octagram 上下文评测：用例已在 `probe-cases.tsv`（r2 导出 849 条），
   探针执行与格式对齐在 VoiMate 侧完成。
2. 评测纳入回归测试：待 probe case 集稳定后，把小语料子集的
   eval_corpus 断言收进 pytest（阈值护栏，不锁死具体词表）。

r2 同口径确认效果：覆盖缺口 431→308（-28.5%），排序缺口率 58.07→
62.78/千词（口径=对，dist 近翻倍竞争面扩大，主体仍为上下文依赖，
octagram 是结构性出路）。

## octagram grammar A/B（2026-10-01 追加）

232 条 freq≥2 排序缺口用例 + 14 内置/上下文 case，on（25.2MB .gram）/off（剥 grammar 块）双 bundle 对比。结果：上下文条件 case 修复 2（shenghuo→生火 ×2）、回退 0；232 条词级同音排序用例 0 翻转。结论：octagram 增量真实但限于上下文条件次词排序；词级排序缺口（223 条）走 phrase-curation，与 .gram 正交。方法学教训：静态链接 librime 探针必须 `-Wl,-force_load` 并以 `nm | grep octagram ≥ 1` 验收，否则模块静默失效（首轮无效实验已记录）。criteria 五条对照判定：全部满足（成本维度依据 2026-09-19 experiment-1 wrapup 实测：RSS +14.8 MB、ctx 0.2 ms、QWERTY 1.8 ms、iPhone-JA 实机验证；唯一残留 gram 超 24 MB 锚线 0.07%），.gram 正式保留在主 bundle。详见 `data/eval/rounds/2026-10-01-grammar-ab.md`。

## octagram grammar v2（2026-10-01 追加）

维基新闻 10,074 篇（8.7M 字符，CC BY 4.0）+ zhwiki 重下混合重训。A/B：246 case 与现役 v1 完全打平（20 PASS、0 回退、ctx 保持）；成本大幅优化：bundle 24→8.1MB（-66%）、RSS -7.6MB、延迟持平。判定 v2 换包，v1 备份可回滚。域内增量（台风/地震类搭配 542 行）已入 gram 但现用例集不覆盖，后续补 wikinews 域 ctx case。详见 data/eval/rounds/2026-10-01-grammar-v2.md。

## octagram 域内 ctx（wikinews）与 v3 扩充决策（2026-10-01 追加）

从 wikinews TSV 按 v2 高分搭配人工核验 40 条上下文选词 case（`domain=wikinews`），
用 v1 备份 gram 与现役 v2 复测：v1 22 PASS / v2 35 PASS，**增益 13、回退 0**。
典型翻转：橙色预警、台风吹袭、飓风过境、洪水暴涨。两侧同 FAIL 5 条为台风专名
或无上下文也打不赢的同音（纪录/记录），不是回退。

判定：新闻域搭配增益可测且方向正确，octagram **GO 扩语料重训 v3**（不停留 v2）。
v3 训练循环要求先 pin MOT/VOA Mandarin（公有领域新闻，CC BY 4.0 汇集）或等价
清洁源，把混合 CJK 做到 20M+，再走完整 A/B + criteria。wikinews 滚动采集常态化
为新 dated TSV + lock hash bump。Newsdata.io / CC-News 因底层稿件版权不入训。
评测面：`data/eval/rounds/grammar-probe-ctx-cases.tsv`；报告：
`data/eval/rounds/2026-10-01-grammar-wikinews-ctx.md`。

词库：`COVERAGE_SOURCE_IDS` 纳入 wikinews，只补缺失表面，落层 bulk。

## octagram grammar v3（2026-10-01 追加）

已 pin MOT v1.11 VOA Mandarin（tarball sha256 `c60b30efa8…`，t2s xml
`81fb504d…`，7,203 篇 / 10.0M CJK）并与 v2 的 zhwiki+wikinews 混合重训，
合计 **27.9M CJK**，gram 8.1→13.2 MB。A/B vs 现役 v2（286 case，
`nm | grep octagram` = 7）：wikinews ctx 35→31 PASS，**增益 0 / 回退 4**
（伤亡→上网、事件→时间 ×2、中断→终端）；232 条词级排序仍 0 翻转；
builtin `shenghuo` 保持 PASS。scored 核对：`方中断` 92919→89090 被
min_value=90000 裁掉，短尾巴被 MOT 稀释。

判定：Effect 不满足零回退，**停留 v2，不换包**。MOT 许可清洁且 pin 有效，
但 10M 近端 VOA 不能当作 Wikinews 搭配增益。v3 gram 留 Backup 作实验物，
未 rsync 键盘。详见 `data/eval/rounds/2026-10-01-grammar-v3.md`。

## ranking r1：目标模式 + 6 条 emit 提权（2026-10-01）

无上下文 TOP-1 定为通用书面语，知乎 13 篇只当传感器。通道是 emit
写时把指定表面抬到同音峰 +1，不改 essay、不改 `HOT_WEIGHT_FLOOR`。

`data/voimate/ranking-overrides.tsv` 首批 6 条，热表 TOP-1 全部翻转：

| 拼音 | 原 TOP-1 | 现 TOP-1 |
|---|---|---|
| fu gai | 复盖 14118 | 覆盖 14119（进 hot_tail） |
| ji hua | 计画 = 计划 45520 | 计划 45521 |
| fu gou | 扶沟 578 | 复购 579 |
| man dun | 曼顿 757 | 慢炖 758（进 hot_tail） |
| xian zhu | 先主 652 | 显著 653（进 hot_tail） |
| ke ni | 可你 831 | 可逆 832 |

类 C（任务/人物、老师/老实）未全局翻转。`python -m umate_lexicon eval`
探针 ok。`tests/test_ranking_overrides.py` + emit/eval-regression 绿。

知乎-13 传感器（`2026-10-01-ranking-r1`，语料未改写）：覆盖缺口 307→277
（-30，本轮 OpenCC t2s 重建把繁体表面并进简体）；排序缺口 849→850（+1，
6 条不在这 13 篇的排序缺口里，+1 是同音竞争面噪声，低于回归轨 +8）。
dist 条目 1,461,667→1,480,994（含 hot_tail 投影重复计数）。

判定：r1 结构修复成立，词库可同步键盘。不把知乎/VOA 写进 lemma 或 .gram。

## coverage + ranking r2（2026-10-03）

知乎 13 篇传感器未改写。覆盖 277→274（-3：肝片 / 共沸进 phrase-curation，外加 TGH 单字回 `chars`）。
排序 850→861（+11）：OpenCC 折叠后「本地简体行优先」把繁体 essay 质量留在被丢的繁体行上，
一批常用词只剩 weight 1（干净 / 游客 / 游戏 / 周末…）。本轮用 emit 提权表修了类 A 共 15 条
（下锅 + t2s 簇），任务/人物等类 C 未动。

TGH：`chars` 7960→8243。THUOCL industry 抢走的 鸮/鸰等回到单字表；273 个扩展区
规范字（㑇 等）因 `han_len` 只认 BMP 而从未发出，现已进 `chars`。呒/呣 仍被 `ḿ`
清洗丢掉。锅气 / 钾碱 仍是 rejected wiki_redirect，不洗白。

结构性下一步（未做）：折叠时把繁体 essay 质量叠到留下的简体行，而不是继续加提权表。
键盘同步 / Host 编译仍另走。详见 `data/eval/rounds/2026-10-03-coverage-ranking-r2.md`。

## t2s 质量继承（2026-10-03）

观点：这一刀只补类 A 的繁简失重。排序缺口留在 848 不是失败，类 C 不翻。

证据：`inherit_folded_ranking` 在发射时生效。简体行 `ranking_freq <= 1` 才用 max（不求和）继承被 OpenCC 折掉的繁体 ranking 列。已有实测列的不动。rejected / curated 不继承。重发射：`t2s_inherited=2441`，`ranking_overrides=9`（21 条提权里 12 条继承后已是唯一 TOP-1，不再抬）。`chars=8243`，`base=97015`，`hot_tail=156212`。

抽查：干净 11882、上周 4104、凶手 6027、一周 15433、干脆 8386、干燥 4588、游客 6116、周末 12071、游戏 190700、旅游 12438、炖煮 643、炖锅 524、下锅 987、吃饭 31690 均为该拼音 TOP-1。游行 3697 / 游园 1431 仍靠提权压过有幸 / 有缘各 1。群仍 1000，不吸收羣，且低于裙 1526。任务/人物、升职/升值、酒精/究竟、汇报/回报未翻。

知乎-13（语料未改写，`2026-10-03-t2s-inherit`）：覆盖缺口 274→274；排序缺口 861→848（相对 r1 的 850 为 -2）。`python -m umate_lexicon eval` 为 ok。`tests/test_emit.py`、`test_ranking_overrides.py`、`test_tgh.py`、`test_corpus_eval.py` 绿。

weight≤1 的排序缺口仍有 132。高频项多为分词碎片，或评测拼音和词库读音不一致：这儿在 `zher` 3652，看似在 `kan si` 14215，传感器却用 `zhe er` / `kan shi` 去对。碱性 weight 1 对践行 1234 先观察。OpenCC 把鹼性折成碱性，但不折硷性（硷性 1027 仍单独在库）。即使把这列并过去，也仍低于践行，不值得为它加提权。不给自转/自传、猪肝/主干、潮汐/抄袭加提权。

多来源折叠只在凌蒙初上丢掉更高的一列（436→17），不在这 13 篇里，本轮不改合并顺序。

键盘同步 / Host 编译仍另走。详见 `data/eval/rounds/2026-10-03-t2s-inherit.md`。
