# octagram grammar A/B 报告 2026-10-01

## 目的

回答 merge criteria 的量化问题：当前 `umate-zh-hans.gram`（25.2 MB）对真实语料导出的排序缺口用例是否有可测量增量，有无回退。

## 用例

| 来源 | 数量 | 说明 |
|---|---|---|
| `data/eval/rounds/grammar-probe-cases.tsv` | 232 | freq≥2 排序缺口导出，pypinyin 标注，soft=1 |
| 探针内置 hard cases | 10 | 设计稿/长句等基础回归 |
| 探针内置 grammar-sensitive | 2 | 柴火句（词表覆盖类） |
| 探针内置 context cases | 2 | commit 前缀后次词选择 |
| 合计 | 246 | |

## 方法

- bundle：on = 现行 `RimeSharedData.bundle`（含 `.gram` + `grammar:` 块）；off = `rsync -a` 同拷后删 `.gram` 并剥除 12 处 schema 的 `grammar:` 块；user dirs 全新空目录。
- 探针：`Scripts/umate_grammar_probe.c`，`RIME_PROBE_CASES` 读 TSV。
- librime：本地源码构建 `librime.a`（1.16.1 arm64，`BUILD_MERGED_PLUGINS=ON`，lua/octagram 符号在 `.a` 中确认）。
- 附加对照：污染测试（`.gram` 替换为 200 字节随机数据）。

## 结果

### 第一轮：普通 `-lrime` 静态链接 —— 无效实验

on / off / 污染 `.gram` 三者输出完全一致（0 翻转，0 差异）。

原因：静态库链接器不拉入无外部引用的注册目标文件。`nm` 显示探针二进制 octagram 符号数 = 0，模块从未注册，grammar 组件不存在。污染测试无反应是"没加载"的证据，不是"加载了没用"。

**教训：静态链接 librime 探针必须 `-Wl,-force_load,<librime.a>`，并以 `nm <binary> | grep -c octagram ≥ 1` 作为链接验收条件。**

### 第二轮：`-Wl,-force_load` 重链 —— 有效实验

| 指标 | on（gram） | off（无 gram） |
|---|---|---|
| PASS（246 case） | 20 | 18 |
| TSV 排序缺口（232） | 9 PASS / 223 FAIL | 9 PASS / 223 FAIL |
| 修复（off FAIL → on PASS） | **2** | — |
| 回退（off PASS → on FAIL） | **0** | — |

修复的 2 条均为上下文条件 case：

- `ctx-kitchen-shenghuo`：commit "到厨房" 后，shenghuo → 生火（off 侧为 生活）
- `ctx-firewood-shenghuo`：commit "柴火" 后，shenghuo → 生火（off 侧为 生活）

223 条 TSV 排序缺口（全部 got 非空，属词级同音排序）0 翻转：grammar 对该类缺口无增量。

内置 `firewood-sentence` 两侧同为 FAIL（"抱着一捆"未收录）：缺口性质是词表覆盖，与 grammar 正交——印证分域记账的必要性。

## 结论

1. octagram 增量真实但范围窄：支持"上下文条件下的次词排序改善"，不支持"无上下文首候选同音排序改善"。
2. 223 条排序缺口的改善通道是 phrase-curation 词级权重（phrase-curation 主循环），不是 `.gram`。
3. 对照 `Docs/specs/2026-10-01-octagram-merge-criteria.md`：本轮补齐"真实语料排序用例 + 无回退"维度；成本与真机维度以 2026-09-19 experiment-1 wrapup 实测为准（RSS +14.8 MB、ctx 查询 0.2 ms、QWERTY 1.8 ms、iPhone-JA 实机无性能/稳定性问题）。

## 复现

```sh
# link (force_load mandatory)
c++ Scripts/umate_grammar_probe.c \
  -I/Volumes/Backup/tmp/umate-librime-1.16.1/src \
  -Wl,-force_load,/Volumes/Backup/tmp/umate-librime-1.16.1/build-macos-arm64/lib/librime.a \
  -L/Volumes/Backup/tmp/umate-librime-prefix/lib \
  -lleveldb -lmarisa -lopencc -lyaml-cpp -lpthread -lz \
  -o /Volumes/Backup/tmp/umate-gram-ab/umate_grammar_probe_fl

# run
RIME_PROBE_CASES=data/eval/rounds/grammar-probe-cases.tsv \
  /Volumes/Backup/tmp/umate-gram-ab/umate_grammar_probe_fl \
  /Volumes/Backup/tmp/umate-gram-ab/{on,off} \
  /Volumes/Backup/tmp/umate-gram-ab/users/{on,off}
```

## 遗留

- 探针 C 改动在 VoiMate 侧单独 tooling commit。
- force_load 验收条件建议写入后续探针文档/脚本。

## Merge criteria 对照（2026-10-01，数据为 force_load 轮）

| 标准 | 状态 | 证据 |
|---|---|---|
| 1 Effect | 过 | +2 ctx PASS、0 回退；翻转归因（厨房/柴火 × 生火搭配）成立，n-gram 计数核对未做 |
| 2 Cost | 过（一处临界） | 依据 2026-09-19 experiment-1 wrapup 实测：RSS +14.8 MB（≤15 MB 锚线）、ctx 查询 ~0.2 ms、QWERTY ~1.8 ms（≤2 ms 暖查询）、iPhone-JA 实机验证；唯一残留：gram 25,183,276 B 超 24 MB 锚线约 0.07%，瘦身或锚线修订二选一 |
| 3 Licensing | v1 已完成 | .gram v1 训练语料 = Wikimedia zhwiki/wikivoyage dumps，GFDL+CC BY-SA 3.0 双许可取 CC 分支（2026-10-01 verdict 登记 SOURCES.md，与 wiki 词库通道同级）；bundle NOTICE 署名已补（9613973f）。essay.txt 非 .gram 语料（rime 词频表，lgpl-rime-essay 通道 NOTICE 已有）。v2 新语料须逐源登记 verdict |
| 4 Swappability | 过 | off 侧仅数据文件删除即可回退，引擎/ schema 无需改动 |
| 5 Closure | 过 | 本报告 + experiment-1 wrapup 均在 |

清理条件：1/2/3/4 均未触发（主套件有净收益、非 gold-anchor、非 neural-LM、本轮可复现）。

**判定：merge criteria 五条全部满足——效果（+2 ctx、0 回退）、成本（wrapup 实测达标，唯一残留 gram 超 24 MB 锚线 0.07%）、许可（插件 BSD-3-Clause 2026-09-19 更正；v1 语料 CC BY-SA 3.0 分支 verdict + NOTICE 署名 2026-10-01 落地）、可替换（纯数据文件 swap）、闭环（experiment-1 wrapup + 本报告）。.gram 正式保留在主 bundle（`3c2291d5`），不再是"测试性质待定"。下一步按序：① gram 瘦身过线或修订锚线措辞 ② n-gram 归因核对 ③ v2 训练语料（维基新闻 CC BY 4.0 等商用清洁源）逐源登记后重建。本判定修正 2026-10-01 初版"标准 2 未覆盖"的结论——当时漏查了 experiment-1 wrapup 的已测数据。**
