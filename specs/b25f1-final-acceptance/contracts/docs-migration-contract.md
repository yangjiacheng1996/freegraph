# Contract: 迁移说明 + 最终 README

**Feature**: B25F1 · **Date**: 2026-11-25
**Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md)

> 锁定 FR-009 / FR-010 / SC-005：迁移说明三类、**Y-01**、README 结构、`COMPAT.md` 绝对链接、
> 「不复制完整矩阵」。

---

## 1. 迁移说明

**文件**：`harness/proposals/更名与迁移说明.md`（在既有 §1–§6 之后新增 v1 迁移章节）。

### 1.1 三类分组（MUST）

#### A. 同名直接可用

| 上游 | freegraph | 说明 |
|---|---|---|
| `from langgraph.graph import StateGraph, START, END` | `from freegraph.graph import StateGraph, START, END` | 只换包名 |
| `StateGraph(schema)` | 同签名 | — |
| `add_node(name, fn)` | 同签名 | — |
| `add_edge(src, dst)` | 同签名（含多源汇合边） | — |
| `add_conditional_edges(src, path_fn, path_map)` | 同签名（list / dict / `None`） | — |
| `compile()` | 同签名（支持 `checkpointer=` / `tracer=` / interrupt 关键字） | — |
| `invoke(input, config)` | 同签名 | 返回完整状态 |

#### B. 同名但行为有差异

| 项 | 上游 | freegraph | 编号 |
|---|---|---|---|
| `Command.goto` 缺省 | `()` | `None` | **Y-01** |
| `get_state` 无快照 | 空 `StateSnapshot` | `None` | Y-02 |
| `Send` 可变性 | 可变 | 不可变 | Y-03 |
| `draw_mermaid_png()` | 真实渲染 | v1 固定占位 PNG | B23F1 |
| `Command` 非法目标 / 非 dict `update` | 静默忽略 | 显式失败（更严） | X-06 |
| `update_state` | 支持 `task_id` / `values=None, as_node=END` | v1 不支持（能力边界） | — |

#### C. 需改写 / 不属 freegraph 范围

| 项 | 处置 |
|---|---|
| `init_chat_model(...)` | `langchain` 层；freegraph 不替代 |
| `@tool` / `tool.name` / `tool.invoke` | `langchain` 层；freegraph 鸭子类型承载 |
| `ToolMessage(...)` / `HumanMessage(...)` | `langchain.messages`；freegraph 原样流转 |
| `display(Image(...))` | IPython；脚本自身 |
| `Store` | 契约已冻结、v1 不实现（v2） |
| Postgres / 子图 / async / 完整 Studio | v2 范围 |

### 1.2 Y-01 的 v1 行为提示（MUST）

迁移说明 MUST 明确写：

> freegraph 的 `Command().goto` 是 `None`，上游是 `()`。若你的代码依赖 `goto == ()`
> 或对 `goto` 做真值判断，请改为 `is None` / 显式检查。运行时对齐归 v2 独立契约修订。

### 1.3 `COMPAT.md` 指针

- 逐符号细节 MUST 指向 `COMPAT.md`；
- **MUST NOT** 在迁移说明里复制完整矩阵；
- 链接 MUST 为绝对 URL 或仓库内相对链接（迁移说明在仓库内，可用相对链接）。

---

## 2. 最终 README

**文件**：`README.md`

### 2.1 必需章节（MUST）

| 章节 | 内容 |
|---|---|
| **快速上手** | `pip install freegraph`；最小图；`invoke`；`[otlp]` 安装；fake / 真实轮验收入口 |
| **三条对外承诺** | 零账号（含零 license key）/ 零出站 / 零第三方运行时依赖 |
| **能力处置表** | 能力 → freegraph 处置（沿用 B24F1 的 5 列 / 8 行 + as-of 日期） |
| **独立实现声明** | 独立实现、非 LangChain Inc. 产品；不构成 affiliation |
| **兼容矩阵指针** | 指向 `COMPAT.md` 的**绝对链接** |

### 2.2 `COMPAT.md` 绝对链接（MUST）

```text
https://github.com/yangjiacheng1996/freegraph/blob/main/COMPAT.md
```

**MUST NOT**：

- 使用相对路径（PyPI 落地页会 404）；
- 在 README 维护第二份完整逐符号矩阵；
- 复制 `COMPAT.md` 的机读段。

### 2.3 中文为主 + 英文关键段落

- 中文为主；
- 英文覆盖：独立实现声明、三条承诺、安装与 `[otlp]`、能力摘要、`COMPAT.md` 链接；
- **MUST NOT** 要求逐节全译。

### 2.4 徽标 / 商标

- **MUST NOT** 使用 LangChain / LangGraph / LangSmith 的 logo / 品牌色 / 官方文案；
- 纯文字名称（互操作说明）允许，但 MUST 与 affiliation 声明配套。

### 2.5 状态说明

- MUST 与当前已交付能力一致；
- **MUST NOT** 出现「内核尚未实现」「没有任何图运行时能力」「请勿当作可用替代品」等过时断言；
- MAY 保留「占位版本」的客观描述。

---

## 3. `harness/demo/README.md`

MUST 更新：

- 「尚缺的验收脚本：可诊断性（M3）」⇒ 改为「`diagnostics.py` 已交付」；
- 执行顺序加入 `diagnostics` 与 `target(fake)`；
- 双跑说明：fake 轮（CI）/ 真实轮（人工）的入口；
- 目标态：`harness/demo/acceptance.py` 编排四组（含 diagnostics）；
- **MUST NOT** 修改 `target.py` 的描述为「可改」。

---

## 4. 文档守卫

| 检查 | 入口 |
|---|---|
| 迁移说明存在三类 + Y-01 | 人工复核 + `tests/runtime/test_b25f1_manual_record_guard.py` |
| README 有绝对 `COMPAT.md` 链接 | `tests/contracts/test_b24f1_docs.py`（沿用） |
| README 无完整矩阵 | B24F1 的 G8 / G19 / G29 判据（沿用） |
| README 三条承诺 / 独立实现声明 | B24F1 的 docs guard（沿用） |
| demo README 标记 diagnostics | `tests/runtime/test_b25f1_diagnostics.py` / 人工复核 |

---

## 5. 失败示例

```text
[FAIL] 迁移说明缺 Y-01 的 v1 行为提示
[FAIL] README 含完整逐符号矩阵（应只保留 COMPAT.md 指针）
[FAIL] README 的 COMPAT.md 链接是相对路径
[FAIL] 迁移说明把 langchain 层写成 freegraph 能力
```
