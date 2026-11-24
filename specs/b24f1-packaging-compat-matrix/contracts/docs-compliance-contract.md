# Contract: README · `THIRD_PARTY_NOTICES` · 商标与双语

**Feature**: B24F1 · **Date**: 2026-11-24 · **Spec**: [../spec.md](../spec.md)

---

## 1. README 结构（目标顺序）

```text
# freegraph
> 状态说明（与当前已交付能力一致；保留「占位版本」客观描述）
> 独立实现、非 LangChain Inc. 产品
> 三条承诺（零账号（含零 license key） / 零出站 / 零第三方运行时依赖）
（英文关键段落：独立实现声明 / 承诺 / 安装 / 能力摘要）

## 依赖面
## 开发与验收
## 可观测属性（B18F1）
## OTLP 导出（B21F1 · 可选 [otlp]）  ← MUST 保留 OpenLIT / Langfuse / Phoenix 三后端（并列 · 无默认推荐）
## 能力 → freegraph 处置          ← 立项书 §3.2 定稿表体
## API 兼容矩阵                   ← 指针：唯一权威在 COMPAT.md（绝对 GitHub URL）
```

- `## 能力 → freegraph 处置` MUST 在 README 可见，**逐字复刻**立项书 §3.2 的
  **5 列**（`能力 | Developer $0 | Plus $39/seat/月 | Enterprise | freegraph v1`）与 **8 行**，
  并附 `as-of 2026-11-01`（以官方定价页为准）；**MUST NOT** 压缩为 3 列、删减行或简写表头。
- `## OTLP 导出` MUST 保留三后端示例（**OpenLIT / Langfuse / Phoenix**），三者**并列、
  无默认推荐**；MUST NOT 写「官方推荐 / 默认后端」。
- `## API 兼容矩阵` MUST **只是指针**：说明唯一权威在 `COMPAT.md` + **绝对 GitHub URL**
  （`https://github.com/yangjiacheng1996/freegraph/blob/main/COMPAT.md`）；**不得**含完整符号表
  （机读取行数为 0）。
- README MUST NOT 维护第二份完整矩阵。
- README 的公开面计数 MUST 为 **manifest 驱动**（当前契约层 **22** ∪ 门面 **8**，去重后 **27**）；
  MUST NOT 保留「契约层 18 / 20 / 21 个」「门面 7 个」等旧计数；MUST NOT 保留「31 个 feature / 93 人日」
  （改为立项书口径 **32 / 96**）。

---

## 2. 顶部状态说明

**必须删除的过时断言**：

- 「内核尚未实现」；
- 「没有任何图运行时能力」；
- 「请勿当作可用替代品」/「请勿用于生产」（**任何语境均不得保留**；发布基线不应再出现该句）。

**允许保留**：

- 「v0.0.x 是占位版本（name-reservation placeholder）」的**客观历史**；
- 「PyPI 发行名已锁定」的事实；
- 指向立项书 / 实现路线的说明。

**MUST**：状态说明与当前已交付能力一致（本 feature 是发行前置，不得首屏自述「不可用」）。

---

## 3. 三条对外承诺

| 承诺 | README 必须表达 |
|---|---|
| **零账号** | 无需 LangSmith 账号 / API key / license key |
| **零出站** | freegraph 自身不主动出站；不阻断用户代码出网 |
| **零第三方运行时依赖** | 基础安装不装任何第三方包；site-packages 只有 freegraph |

（**2026-11-24 拍板**：第三条 = **零第三方运行时依赖**；「零 license key」并入
**零账号**维度（无需账号 / API key / license key），**不单列为第四条**。）

---

## 4. 双语口径

- **中文为主**：正文、能力表、安装说明以中文为主。
  **判定口径**：除英文关键段落外，其余章节说明文字 MUST 为中文；英文关键段落 MUST 以
  **显式子标题 / 标注**呈现（或集中于独立英文摘要段），**MUST NOT** 以「英文散落在各节」冒充覆盖。
  **可执行判定**：所有 `##` 级章节标题 MUST 为中文；唯一例外是显式的
  `## English` / `## English Summary` 段（或带 `[English]` 标注的段落）。
  非英文段内 MUST NOT 出现连续 3 段以上纯英文正文；英文段 MUST 覆盖
  独立实现声明 / 三条承诺 / 安装与 `[otlp]` / 能力处置摘要 / `COMPAT.md` 链接。
  该结构由 `tests/contracts/test_b24f1_docs.py` 断言（作为「中文为主」的可执行判据）。
- **英文覆盖关键段落**（MUST 至少）：
  1. 独立实现 / non-affiliation 声明；
  2. 三条承诺；
  3. 安装与 `[otlp]`；
  4. 能力处置摘要；
  5. 指向 `COMPAT.md` 的链接。
- **不要求**逐节全译；MUST NOT 因此判失败。
- README MUST 含「**兼容意图为互操作，不构成 affiliation**」（可与独立实现声明同段；
  `COMPAT.md` 机读段另有一份，二者不互斥）。

---

## 5. 商标 / 品牌资产（原则 IX）

### 5.1 禁止

- LangChain / LangSmith / langgraph / deepagents 的 **logo / 图标 / 品牌色 / 品牌视觉**；
- 官方 **"Approved copy"** 描述文案；
- 暗示官方身份 / 授权 / 合作关系的表述。

### 5.2 允许（nominative use）

- 纯文字提及上游产品名（`LangGraph` / `langgraph` 关键字与描述），用于说明**互操作目标**；
- 前提：README 的「独立实现、非 LangChain Inc. 产品」声明齐备；
- `pyproject.toml` 的 `keywords`（含 `langgraph`）与 `description` 允许保留（A-10）。

### 5.3 扫描

- G30 的第三方品牌资产扫描命中数 MUST 为 **0**；
- README / 文档 MUST 含「**独立实现、非 LangChain Inc. 产品**」。

---

## 6. `THIRD_PARTY_NOTICES` 结构

```text
# 第三方归属清单
## 1. 引入的第三方代码（复制 / 改编 / vendored）
## 2. 第三方运行时依赖
## 3. 互操作与 affiliation 声明
## 4. 维护规则
```

### 6.1 §1 必需条目

| 项目 | 来源 | 许可证 | 引入方式 | 版权保留 |
|---|---|---|---|---|
| `langgraph-checkpoint-sqlite` 的同步 `SqliteSaver` | `langgraph-checkpoint-sqlite 3.1.1`（LangChain, Inc.） | MIT | 改编（B15F1 `src/freegraph/persistence/sqlite.py`） | 清单 + 源文件署名头 |

> **术语清理（MUST）**：`THIRD_PARTY_NOTICES` §1 / §4 的旧 feature 编号 `F1P1` / `F24P1`
> MUST 替换为 `B1F1` / `B24F1`（历史说明可保留括注）；MUST NOT 让旧编号与现行 `B<n>F<m>` 命名混用。

### 6.2 §2 必需条目

- `[otlp]` 闭包逐包：`opentelemetry-api` · `opentelemetry-sdk` ·
  `opentelemetry-semantic-conventions` · `opentelemetry-exporter-otlp-proto-grpc` ·
  `opentelemetry-exporter-otlp-proto-common` · `opentelemetry-exporter-otlp-common` ·
  `opentelemetry-proto` · `googleapis-common-protos` · `grpcio` · `protobuf` · `typing-extensions`；
- `protobuf`：`3-Clause BSD License` → `BSD-3-Clause`（**仅此一包**的具名归一）；
- 基础安装：**无数据行**（零依赖）；
- v2 extras 的**计划说明**保留（不是 v1.0 发行依赖）；
- `langgraph==1.2.11`（differential）**不登记**（测试侧 · 不进发行包 · A-11）。

### 6.3 §3 affiliation

MUST 含：「兼容意图为互操作，不构成 affiliation」；并指向 `COMPAT.md`。

### 6.4 §4 维护规则

§4 的「新增公开符号 ⇒ 更新兼容矩阵」MUST 指向 **`COMPAT.md`**（README 仅指针），
**MUST NOT** 继续写成「更新 `README.md` 的兼容矩阵」。

---

## 7. 文档守卫（自动化）

| 测试 | 断言 |
|---|---|
| `test_b24f1_docs.py` | README 状态不含过时断言（含「请勿用于生产」）；含三条承诺；含能力表标题 + §3.2 关键行；含 **绝对 GitHub URL** 的 `COMPAT.md` 链接；OTLP 三后端（OpenLIT / Langfuse / Phoenix）且「无默认推荐」；英文关键段存在；无品牌资产 |
| `test_b24f1_notices.py` | `THIRD_PARTY_NOTICES` 存在；§1 含 `SqliteSaver` / MIT / LangChain, Inc.；§2 含 `[otlp]` 逐包 + `protobuf` 归一；基础依赖无数据行 |
| `test_b24f1_manual_record_guard.py` | `manual-verification.md` 存在；五段式齐备；正文非空；含 `B24F1 acceptance: PASS` / `pip freeze` / 纯度正负向退出码 / `COMPAT.md` **18 项与下游行核对** / G8-G19-G29 追认 / **质量门禁 5 偏离 + B25F1 承接追认** / **Y-01 / Y-02 / Y-03** 遗留项 / **B15F1 与 B16F1 人工验收证据（或链接）**；不含 `待填` |
| 既有 README 守卫 | 保留 `test_b16f1_doc_guard.py` / `test_invoke_purity.py` / `test_compiled_graph.py` / `test_b21f1_manual_record_guard.py` 所需字符串（或同步更新守卫） |
| G30 | 新增 `.py` 署名头 + 品牌资产扫描（既有） |

---

## 8. 不变量

- README 不复制完整矩阵（唯一权威在 `COMPAT.md`）。
- README 的 `COMPAT.md` 链接 MUST 为**绝对 GitHub URL**（COMPAT.md 不进发行包）。
- README 的 OTLP 段 MUST 保留三后端并列、无默认推荐（H-8③）。
- 纯文字产品名允许；品牌资产禁止。
- 三条承诺与独立实现声明中英齐备。
