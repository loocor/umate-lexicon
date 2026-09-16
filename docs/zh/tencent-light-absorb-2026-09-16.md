# tencent-light 吸收验证（2026-09-16 / 2026-09-17）

只验证 ModelScope **light** 高频子集的覆盖融合，不是官方约 800 万全量 dump。
官方下载地址仍返回 HTML，本轮没有编造全量 hash，也没有改 pin。

Pin 未动：`tencent-light` →
`https://modelscope.cn/models/lili666/text2vec-word2vec-tencent-chinese/resolve/master/light_Tencent_AILab_ChineseEmbedding.bin`
，sha256 `5515923c7e67cdc7eb42996546e0bad273c8452f3bfad6db0794e51c848d151b`。
`word2vec-vocab` 抽出 `tencent-light-vocab.txt`。bin 和 vocab 都 gitignore，不入库。

Lock 顺序：`tencent-light` 在全部 zhwiki dump **之后**。Tencent 只 overlay 已有 lemma，不能抢 wiki 身份。

## 2026-09-17 全量 locked 复验

在 `origin/main` + 本 PR head 的隔离 worktree 中运行：

```sh
PYTHONPATH=src .venv/bin/python scripts/validate-tencent-light.py
```

本轮 23 个 pinned artifact 全部 hash 匹配，包含 CC-CEDICT；`ran_sources` 没有跳过项。
`eval_failures=0`，pipeline 得到 `lemmas=1327824`，`tencent-light` ingest action 计数为 `91981`。
pipeline 的 action 计数与下表按表面去重的 absorb 计数口径不同，两个数字都要保留，不能互相替代。

### 词表本身（抽词后、ingest 前）

| 项 | 数量 |
| --- | ---: |
| light 表面（词表行） | **143613** |
| 去重可解析表面（absorb 计数） | **143607** |
| 文件 | 111MB `.bin` → 1.1MB vocab |

### 吸收数字（2026-09-17 全量 pipeline 后）

| 项 | 数量 | 说明 |
| --- | ---: | --- |
| 总表面 | **143607** | 去重后的可解析 light 行 |
| overlay 到已有 curated lemma | **71760** | essay / cedict / thuocl / gold / luna / unihan 等 |
| wiki±tencent 覆盖重叠 | **1208** | 仅 coverage 源；仍是 bulk。wiki 先写入，tencent 后盖章 |
| unique compose 新写入 | **16681** | tencent-only |
| 跳过：非汉无金标 | **22509** |  |
| 跳过：长度 1 | **14052** |  |
| 跳过：长度 >4 且无 overlay | **685** |  |
| 跳过：compose 失败 | **16712** |  |

`71760 + 1208 = 72968` 条 overlay 表面；再加 unique compose 和四类 skip，合计为 `143607`。

tencent 碰过的 lemma：

| 项 | 数量 |
| --- | ---: |
| 带 tencent 源的 lemma | **90926** |
| 其中 tencent-only | **16698**（分层全是 **bulk**） |
| store 里的向量/非整频次 | **0** |

分层（`assign_layer`，统计带 tencent 源的 lemma；不是全库总层表）：

| layer | 数量 |
| --- | ---: |
| base | 51572 |
| bulk | 18171 |
| ext | 10834 |
| orgs | 3976 |
| dropped | 3398 |
| places | 2157 |
| names | 727 |
| brands | 60 |
| events | 21 |
| corrections | 10 |

`dropped` 是 overlay 到不发词的 lemma（`untrusted_reading` / 无资格单字等），不是 tencent-only 漏进默认 SKU。tencent-only `16698` 全部 bulk。

`domain_freq.tencent` 取值：

| 值 | lemma 数 |
| ---: | ---: |
| 1 | 89872 |
| 2 | 1053 |
| 3 | 1 |

占位频次，不是 essay 权值。值为 2/3 来自繁简折叠或多次 overlay，不是向量。

### 点检

点检按 **light 词表成员关系**判断，不按最终 store 是否存在判断。`元宇宙` 和 `新冠病毒` 可以来自 CEDICT / essay，因此会出现在 store，但不会带 tencent 源；`yyds` 不在 light 词表，也没有有效 store lemma。

| 表面 | light 词表 | store 里 |
| --- | --- | --- |
| 微信 | 有 | 有（tencent-stamped；gold / cedict / essay） |
| 人工智能 | 有 | 有（tencent-stamped；cedict / essay） |
| 银行卡 | 有 | 有（tencent-stamped；cedict / luna / essay） |
| 元宇宙 | 无 | 有（cedict / essay，无 tencent stamp） |
| 新冠病毒 | 无 | 有（cedict / essay，无 tencent stamp） |
| yyds | 无 | 无有效 lemma |

## 融合纪律（本轮修补）

粗混的口子已经堵上，不是把 vocab 拼进 emit：

1. **闸门：** 非汉且无金标 / 单字 / 超 4 字且不能 overlay / unique compose 失败 → 丢弃。
2. **覆盖：** 已有 lemma 只盖 `domain_freq.tencent=1`，不发明 essay 级权值。
3. **排序：** `emit_weight` 不计 `tencent` / `wiki` 占位，essay 仍是排序源。
4. **分层：** tencent-only（以及 wiki±tencent 的 coverage-only）一律 **bulk**，不进默认 SKU 的 base/ext。
5. **分类：** coverage-only 不再被 `银行` 等后缀抬进 orgs/places。
6. **繁简：** ingest 走 Unihan t2s，`銀行` 叠到 `银行`。
7. **向量：** extract 只留第一列，store 不收 embedding。

## 2026-09-16 partial run（历史）

最初一轮遇到 CC-CEDICT 滚动文件 hash mismatch，按纪律跳过 CEDICT，且对应的 wiki 基线早于当前 `main` 的 redirect/classification 收敛。旧结果（`lemmas=1989553`、`tencent-light ingest=106034`、curated overlay `79009`、wiki overlap `1629`、unique compose `22065`、tencent-only `22091`）只保留作历史追踪，不能和上表直接比较或相加。

## 范围外

- 官方约 800 万全量 dump
- 键盘 / VoiMate 接线
- 抄雾凇 `tencent.dict.yaml`
- 把 light vocab 直接拼进默认 SKU

CC-CEDICT 是滚动 URL；它今天 hash 匹配，但未来漂移时 `scripts/validate-tencent-light.py` 会跳过并记录，不会重写 pin 或回退 fixture。
