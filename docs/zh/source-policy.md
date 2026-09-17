# 来源准入策略

这份文档管的是**什么素材可以进 Lemma 库**，是可执行的操作规则。
`CLEANROOM.md` 管的是**哪些配方树绝对不能抄**；本文管的是哪些来源可以
pin、怎么记录。英文原件在 [`docs/source-policy.md`](../source-policy.md)。

机器可读的清单位于 [`data/sources.lock.json`](../../data/sources.lock.json)。
每次 `verify-sources` 和 locked `pipeline` 都会走过
`umate_lexicon.sources` 里的这道门。

## 准入门槛

同时满足以下条件，来源才可以被 pin：

1. 有明确、公开的许可声明；或者属于政府 / 标准机构发布、有明确
   公共使用条款的材料。
2. 许可字符串**原样**记录在 lock 条目里。
3. 许可不是任何写法的 GPL / AGPL。
4. 产物是稳定可哈希的文件（带日期的 dump，或锁到某个 commit），
   不是会自己变的滚动页面。
5. 内容是公开发布的批量素材 —— 不收用户语料，不收私密内容，不收
   需要登录才能看的内容。

## 硬性排除

- **GPL / AGPL，任何变体。** `gpl-*`、`gplv2`、`gplv3`、`agpl-*`、
  `GPL-3.0-only` 等等，一律在 lock 解析阶段直接失败。这是产品决策：
  发出的码表会嵌进商业 App，所以 copyleft 的**源码**许可完全不碰。
  检查实现在 `is_blocked_license()`，按**子串**匹配，所以全称写法
（`GNU GPL v3`、`Affero GPL`、`GNU General Public License v3.0`）
  一并拦下。LGPL 是**故意放行**的 —— 官方 Rime luna / essay / emoji
  就是 LGPL；`LGPL-3.0` 和 `Lesser General Public License` 不受
  GPL 匹配影响。
- 配方树：`iDvel/rime-ice`、`rime-wanxiang`、`melt_eng`，以及任何
  社区 schema / Lua / OpenCC 树。见 `CLEANROOM.md`。
- 商业输入法 cell 词库：搜狗 / QQ / 百度 `.scel` 导出。
- 需要登录、需要付费、或站点条款明确禁止抓取的内容。
- 不允许再分发、或在目标市场有法律限制的内容。
- 任何个人信息：私信、带身份标识的评论历史、通讯录、转写文本、
  用户自己输入产生的语料。

## 隐私

来源只取公开发布的批量 dump。流水线不摄入任何可以定位到个人的内容，
也不摄入用户自己产出的材料。若候选来源里混着公开文本和用户生成内容，
要么把 ingest 限制在公开部分，要么整条来源作废。

## robots.txt 与站点条款

优先用官方 dump / 导出，而不是抓 HTML。当来源没有 dump、只能走 HTTP 时：

- 先看 `robots.txt` 和站点条款，并把结论记录下来；
- 用稳定 UA、低频抓取；
- 不做任何认证，也不绕过封锁；
- 条款不清楚的，在问题解决前一律当作**未准入**。

lock 里保留 `homepage`，就是为了以后能回头复查许可和条款。

## 许可记录

每条 lock 条目记录：

| 字段 | 含义 |
| --- | --- |
| `id` | 稳定来源 id，落成 `lemma_sources.source_id` |
| `license` | 许可字符串，原样，例如 `cc-by-sa-cedict` |
| `homepage` | 复查许可和条款的入口 |
| `url` | 精确的 pin 产物 URL |
| `sha256` | 内容哈希；对不上直接硬失败 |
| `filename` / `extract` | 产物文件名与解包方式 |

逐条词目的来源落在 `lemma_sources` 表里；emit 会在每个输出目录写一份
`NOTICE`，列出每个 source id、许可和行数。

## 同样方式共享（Share-alike）

CC BY-SA 来源（CC-CEDICT、维基标题）按词目标记，并写进 `NOTICE`。
share-alike 和纯覆盖类素材留在 `bulk` 层，不会悄悄并进默认键盘 SKU。
要改这一点，需要一条**有记录的决定**，而不是去改 emitter。

## 新增一个来源

1. 确认许可和条款，把结论记下来。
2. pin 带日期的 dump 或某个 commit；算出 sha256。
3. 加 lock 条目：`license`、`homepage`、`url`、`sha256`、
   `filename`、`ingest`。
4. 跑 `verify-sources` 和 locked `pipeline`。没有许可的来源进不了库，
   locked 路径也不允许回退到 fixtures。
