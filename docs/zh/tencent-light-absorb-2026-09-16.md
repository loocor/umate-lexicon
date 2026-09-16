# tencent-light 吸收验证（2026-09-16）

只验证 ModelScope **light** 高频子集的覆盖融合，不是官方约 800 万全量 dump。
官方下载地址仍返回 HTML，本轮没有编造全量 hash，也没有改 pin。

Pin 未动：`tencent-light` →
`https://modelscope.cn/models/lili666/text2vec-word2vec-tencent-chinese/resolve/master/light_Tencent_AILab_ChineseEmbedding.bin`
，sha256 `5515923c7e67cdc7eb42996546e0bad273c8452f3bfad6db0794e51c848d151b`。
`word2vec-vocab` 抽出 `tencent-light-vocab.txt`。bin 和 vocab 都 gitignore，不入库。

Lock 顺序：`tencent-light` 在全部 zhwiki dump **之后**。Tencent 只 overlay 已有 lemma，不能抢 wiki 身份。

## 词表本身（抽词后、ingest 前）

| 项 | 数量 |
| --- | ---: |
| light 表面（词表行） | **143613** |
| 去重可解析表面（absorb 计数） | **143607** |
| 文件 | 111MB `.bin` → 1.1MB vocab |

点检（词表行，不是 lemma）：

| 表面 | light 里 |
| --- | --- |
| 微信 | 有 |
| 人工智能 | 有 |
| 银行卡 | 有 |
| 元宇宙 | 无 |
| 新冠病毒 | 无 |
| yyds | 无 |

## 融合纪律（本轮修补）

粗混的口子已经堵上，不是把 vocab 拼进 emit：

1. **闸门：** 非汉且无金标 / 单字 / 超 4 字且不能 overlay / unique compose 失败 → 丢弃。
2. **覆盖：** 已有 lemma 只盖 `domain_freq.tencent=1`，不发明 essay 级权值。
3. **排序：** `emit_weight` 不计 `tencent` / `wiki` 占位，essay 仍是排序源。
4. **分层：** tencent-only（以及 wiki±tencent 的 coverage-only）一律 **bulk**，不进默认 SKU 的 base/ext。
5. **分类：** coverage-only 不再被 `银行` 等后缀抬进 orgs/places。
6. **繁简：** ingest 走 Unihan t2s，`銀行` 叠到 `银行`。
7. **向量：** extract 只留第一列，store 不收 embedding。

## Locked ingest 跑了什么

`scripts/validate-tencent-light.py` 于 2026-09-16 跑完。`run_locked_pipeline` 只吃 hash 对得上的 dump；对不上的跳过并记名，不回退 fixture，不改 lock。

本环境：

- `tencent-light` hash **ok**，已抽出 vocab（digest 与 #2 pin 一致）。
- CC-CEDICT 仍是滚动文件：期望
  `70fee391949cec73eaec73476e0b6058930439cb61f435579f90209a1bb70b26`，
  现网 `6da40a5a88e88a771545da065e7948ade659b9a7d632d90013472bf7fc18c648`。
  **未改 pin，未使用这份不匹配文件。** 因此 curated overlay **不含 cedict**。
- 对齐 lock 并参与 ingest 的源：Unihan（readings / variants / tgh）、全部 THUOCL、luna、essay、emoji、zhwiki-titles / page / linktarget / categorylinks、tencent-light。
- pipeline `eval_failures=0`，`lemmas=1989553`，`tencent-light` ingest 次数 `106034`。

## 吸收数字（pipeline 后实测）

| 项 | 数量 | 说明 |
| --- | ---: | --- |
| 总表面 | **143607** | 去重后的可解析 light 行 |
| overlay 到已有 curated lemma | **79009** | essay / thuocl / gold / luna / unihan 等；本轮无 cedict |
| wiki±tencent 覆盖重叠 | **1629** | 仅 coverage 源；仍是 bulk。wiki 先写入，tencent 后盖章 |
| unique compose 新写入 | **22065** | tencent-only |
| 跳过：非汉无金标 | **22509** |  |
| 跳过：长度 1 | **14052** |  |
| 跳过：长度 >4 且无 overlay | **431** |  |
| 跳过：compose 失败 | **3912** |  |

79009 + 1629 = 80638 条 overlay 表面；与 unique compose / 四类 skip 合计 143607。

tencent 碰过的 lemma：

| 项 | 数量 |
| --- | ---: |
| 带 tencent 源的 lemma | **104923** |
| 其中 tencent-only | **22091**（分层全是 **bulk**） |
| store 里的向量/非整频次 | **0** |

分层（`assign_layer`，含 overlay 到已有 curated 的条目）：

| layer | 数量 |
| --- | ---: |
| base | 47531 |
| bulk | 24007 |
| ext | 12932 |
| dropped | 11740 |
| orgs | 5354 |
| places | 2384 |
| names | 863 |
| brands | 81 |
| events | 21 |
| corrections | 10 |

`dropped` 是 overlay 到不发词的 lemma（`untrusted_reading` / 无资格单字等），不是 tencent-only 漏进默认 SKU。tencent-only 22091 全部 bulk。

`domain_freq.tencent` 取值：

| 值 | lemma 数 |
| ---: | ---: |
| 1 | 103814 |
| 2 | 1107 |
| 3 | 2 |

占位频次，不是 essay 权值。值为 2/3 来自繁简折叠或多次 overlay，不是向量。

点检（pipeline 后的 store，不是词表行）：

| 表面 | light 词表 | store 里 |
| --- | --- | --- |
| 微信 | 有 | 有 |
| 人工智能 | 有 | 有 |
| 银行卡 | 有 | 有 |
| 元宇宙 | 无 | 有（其他源，不是 light 写入） |
| 新冠病毒 | 无 | 有（其他源，不是 light 写入） |
| yyds | 无 | 无 |

## 范围外

- 官方约 800 万全量 dump
- 键盘 / VoiMate 接线
- 抄雾凇 `tencent.dict.yaml`
- 把 light vocab 直接拼进默认 SKU
- 本轮未吸收 CC-CEDICT（hash mismatch，已跳过）
