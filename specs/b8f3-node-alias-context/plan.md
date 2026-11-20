# Implementation Plan: B8F3 · `context` 独立通道 + `RunConfig` 运行期接线（alias 已移除）

**Branch**: `b8f3-node-alias-context`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`
⇒ 无 `before_plan` 钩子；既有 feature 同样在 `main` 上开发）
| **Date**: 2026-11-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/b8f3-node-alias-context/spec.md`

**Feature ID**: `B8F3`（M2 图定义与对外 API · **第 22 个** · 前置：**B7F3**；
承接 **B7F3 / B8F1 / B8F2 / B1F1 / B2F1**；本 feature 完成后 **M2 收口**）

> **范围提醒（2026-11-20 发起者拍板）**：C25 节点别名**正式作废**（不是「v1 暂不实现」的注记）；
> 编号**保留为历史墓碑、不复用**；C26/C27 **不重编号**；**active 契约清单 = C1–C24 + C26–C27**。
> 本 feature 只交付 `context` 独立通道（C21）与 `RunConfig` 运行期接线（C22）。
> alias 移除的跨 feature 修订属 **T-2…T-7 / R-1…R-7**，与本 feature 的实现同批交付。
> 宪法版本：**1.16.0（MINOR）**；changelog 必须同批更新。

---

## Summary

交付 freegraph 的**运行期上下文独立通道**：

| 交付物 | 语义 | 关键规则 |
|---|---|---|
| **`context` 来源** | `RunConfig.context`（C22）是唯一来源 | `invoke` / `stream` 共用 `resolve_config()`；**不新增** `context=` 关键字 |
| **运行期载体** | L2 私有 run-scoped `ContextVar` | 新私有模块 `_context.py`；`run_graph` 与 `StreamSession` 在运行入口绑定 / 复原 |
| **节点视图** | 标准节点入参 `state.context` | `context is None` ⇒ 精确 `dict`；非 `None` ⇒ 带只读 `.context` 的 `dict` 子类（映射内容仍可变） |
| **状态隔离** | `context` 不进状态 | 不进 channels / 归约 / `invoke` 终态 / `values` 载荷 / checkpoint |
| **路由隔离** | fresh 视图无 context | 路由第二参 `config` 可携带 `RunConfig.context`（原始 config） |
| **`Send` 边界** | `Send.arg` 为 `dict` 时同样包装 | 非 `dict` 的 `Send.arg` 原样传递，不承诺 `.context` |
| **alias 移除** | `add_node` 无 `alias`、`_NodeRecord` 无 `alias` | `add_node(..., alias=...)` ⇒ `TypeError`；C25 正式作废、编号保留不复用 |
| **契约修订** | C25 / B6F1 / B2F2 / B22F1 / B7F2 / B8F2 / 验收脚本 | C25 正式作废（active = C1–C24 + C26–C27；编号不复用）；历史文字保留；代码 / 签名 / 测试按「彻底移除」处理 |
| **差分场景** | D-137…D-144 | SAME 5 / DIFF 2 / STRICTER 1；上游缺席即 skip |
| **人工门禁** | `harness/verification/B8F3/manual-verification.md` | context / RunConfig / alias 移除实测 + T-1…T-7 追认 |

**技术方案（关键落点）**：

| 环节 | 落点 |
|---|---|
| 运行期上下文载体 | **新增** `src/freegraph/runtime/_context.py`（私有 · `__all__ = []`）· `ContextVar[Any]` + `bind_context()` / `get_context()` |
| 节点视图 | `_context.py` 的 `_ContextState(dict)`（只读 `.context`）+ `with_context(view)` / `with_context_arg(arg)` |
| 节点入参 | `superstep.py:784-800` 的 `_node_input`：`read_channels(...)` 后按需包装 |
| fan-out 入参 | `superstep.py:1328-1340`：`Send.arg` 为 `dict` 时按需包装；非 `dict` 原样 |
| invoke 绑定 | `superstep.py:2244` 的 `run_graph`：在 `bind_run(table)` 外层/同层绑定 `bind_context(run_config.context)` |
| stream 绑定 | `runtime/_stream.py:74-118` 的 `StreamSession.__enter__`：`bind_context(run_config.context)`；`__exit__` 复原 |
| RunConfig | **零改动**（`contracts/types.py:180-260` 九字段已含 `context`） |
| alias 移除（builder） | `_stategraph.py:83-89`（`_NodeRecord` 去掉 `alias`）· `:834-890`（`add_node` 去掉 `alias`） |
| alias 移除（文档） | `README.md:114` · `src/freegraph/contracts/graph.py:152` · `harness/demo/*` · 相关 specs |
| 零新增公开面 | `freegraph.runtime.__all__` 仍 **23**；L1 / L3 符号集不变；无新依赖 |

**零新增**：运行时依赖 · 公开 L2 符号 · 错误类型 · 新公开关键字。
**破冻结面**：T-1（C4 注记）+ T-2…T-7（C25 移除 / B6F1 / B2F2 / B22F1 / 验收脚本 / alias 交接注记）
⇒ 并入**唯一一次**追认。

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（`requires-python = ">=3.11"`）；
允许 `contextvars` / `dataclasses` / `collections.abc` / `typing`。
**MUST NOT** 使用 3.12+ 的 `TypeAliasType` / `override` / `TypeIs` / PEP 695 `type`。

**Primary Dependencies**: **运行时零第三方依赖**（`dependencies = []`）。
开发期：`pytest`（既有 `dev`）· 差分：`langgraph==1.2.11`（既有 `differential` 组）。
`pyproject.toml` **零改动** ⇒ G3 / G21 / G22 / G23 恒绿。

**Storage**: N/A（`context` **不持久化**；checkpoint 归 B14F1）。
**Testing**: pytest —— `tests/facade/`（公开 `invoke` / `stream` / `RunConfig` 行为）·
`tests/runtime/`（L2 `_node_input` / contextvar / 路由视图 / fan-out 边界）·
`tests/differential/parity_probe.py`（D-137…D-144）·
`tests/runtime/test_acceptance_script.py`（验收脚本真跑）。

**Target Platform**: Linux / macOS / Windows · CPython 3.11+ · 零出站。
**Project Type**: library（发行名 = 导入名 = `freegraph`）。

**Performance Goals**: **N/A（不设墙钟预算）** —— context 绑定 / 视图包装均为 O(1)；
不引入 I/O / 网络 / 线程。MUST NOT 用耗时做断言（CI 假红）。

**Constraints**（主要来自 spec 的 MUST 条目）：

| 约束 | spec 条目 |
|---|---|
| 只依赖标准库；MUST NOT import `langchain*` / `langgraph*` / `langsmith` | FR-017 |
| 零出站 / 零环境变量 / 导入无副作用 | FR-017 · SC-008 |
| `context` 只来自 `RunConfig.context`；不新增 `invoke/stream(context=...)` | FR-002 · SC-001 |
| `context` 不进状态 / 归约 / `invoke` 终态 / `values` 载荷 / checkpoint | FR-003 · SC-001 |
| 节点经 `getattr(state, "context", None)` 读到同一对象 | FR-004 · SC-001 |
| `context is None` ⇒ 精确 `dict`；非 `None` ⇒ 带只读 `.context` 的 `dict` 子类（映射内容仍可变） | FR-005 · SC-006 |
| 路由 fresh 视图无 context；第二参 `config` 可携带 `RunConfig.context` | FR-006 · SC-005 |
| `context` 不塞 `configurable`、不从 `configurable["context"]` 读取 | FR-007 · SC-003 |
| `invoke` / `stream` 同一套解析；不跨运行泄漏 | FR-008 |
| 不实现 `context_schema`；不持久化 `context` | FR-009 |
| 独立 run-scoped 私有载体；不改 `run_graph` / `run_super_step` / `run_super_steps` / `_stream_tick` 签名；零新增公开 L2 入口 | FR-010 |
| `add_node` 无 `alias`；`_NodeRecord` / `_BuilderSpec` 无 `alias` | FR-011 / FR-012 · SC-004 |
| C25 正式作废；active = C1–C24 + C26–C27；stream / 图导出 / `PregelTask.name` 只用内部节点名 | FR-013 / FR-014 · SC-004 |
| C25 用例 / README / 测试移除；C21 软断言升级为硬断言 | FR-015 / FR-020 · SC-009 / SC-010 |
| C4 / C6 / C8 / C11 不破坏；无 context 时 `type(state) is dict` 逐字不变 | FR-019 · SC-006 |
| 契约修订按 T-2…T-7；C25 正式作废、编号不复用 | FR-022 · SC-012 |
| 差分 D-137…D-144 · 上游缺席即 skip | SC-007 |
| 新源文件署名头 + docstring 首语句 | 宪法原则 X · G30 |
| 人工验证五段式 + 追认文字 | 宪法原则 V · SC-011 |

> **无 NEEDS CLARIFICATION**：`context` 的上游形态（`context=` + `Runtime.context`）已实测；
> freegraph 的 `RunConfig.context` / `state.context` 是已登记的 **X-1**；alias 已由用户
> 2026-11-20 明确移除。所有未知点均已在 spec 的 Clarifications / Assumptions 收敛。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| 原则 I（零 LangSmith / 零出站 / 零环境变量） | FR-017 · G24 / G26 / G27 / G4 | 通过 |
| 原则 II（零 LangChain · 状态语义等价） | 零新增依赖 · C4 / C6 / C8 / C11 · P-01…P-11 · D-137…D-144 | 通过 |
| 原则 III（验收契约优先 · `target.py` 只读） | `target.py` **零改动**；验收走 `graph_core.py` / `acceptance.py` | 通过 |
| 原则 IV（可诊断性 · 可视化不阻断） | `context` 不进入事件 / 状态；既有 stream / graph export 零影响 | 通过 |
| 原则 V（人工验收） | `harness/verification/B8F3/manual-verification.md` + T-1…T-7 追认 | 通过（计划交付） |
| 原则 VI（规格驱动 · 判据级覆盖） | spec FR-001…FR-022 / SC-001…SC-012 · tasks 追溯 | 通过（plan/tasks 落地） |
| 原则 VII（职责边界 · C21 / C22 / C25） | C21 / C22 接线；C25 **正式作废**（active 清单 C1–C24 + C26–C27；编号不复用）；宪法 **1.16.0 MINOR + changelog**（T-2） | 通过（T-2 已前移到 Setup；宪法 1.16.0 + changelog） |
| 原则 VIII（证据与术语） | `research.md` E-01…E-05 + 上游 `路径:行号`；无推测 | 通过 |
| 原则 IX（许可证 / 商标） | 零新增依赖 ⇒ `THIRD_PARTY_NOTICES` 零变更 | 通过 |
| 原则 X（署名头 / 文档） | 新私有模块带署名头；README / API 矩阵同步 | 通过 |
| 原则 XI（上游优先） | `context` 形态登记 X-1；alias 移除与上游「无 alias」一致；alias 传参失败信号 STRICTER（X-3） | 通过 |
| 原则 XII（最优设计 / 零重复载体） | 单一 `ContextVar` 载体 + 单一 `_ContextState` 视图；不把 context 塞进 channels / configurable | 通过 |
| 立项书 ARCH-1（L3 只依赖 L1 / L2） | `_context.py` 属 L2 私有；L3 只经既有公开入口消费 | 通过 |
| 运行时基线（3.11 · typing 上限） | Technical Context 逐项 ≤ 3.11 · G9 | 通过 |
| 依赖白名单 / 黑名单 | 零新增运行时依赖 | 通过 |
| 跨 feature 承接（v1.8.0） | H-1…H-5；W-1…W-4 撤回；D-1…D-4 | 通过（**T-1…T-7**） |
| 质量门禁 3 / 4 / 5 | C4 回归保持；`target.py` 不可达（PNG 属 B23F1）；人工验证记录 | 通过 |
| 发布门禁 | 不接入（B24F1）；新增代码在 `src/` · 零依赖 | 通过 |

### 登记项 G-1（**唯一一次追认** · T-1…T-7 共用）

**依据**：宪法 v1.8.0「破冻结面的三条」——① 回溯修订（契约 + spec + 冻结断言，
**保留历史 / 拆分而不删**）② 上游对照表写明「上游有 ⇒ freegraph 原先缺」或
「上游无 ⇒ 自研区」③ 发起者追认（落 `harness/verification/B8F3/manual-verification.md`，
**未追认前 MUST NOT 合入**）⇒ 追认次数每 feature **≤ 1 次**。

| # | 冻结面 | 处置 | 追认 |
|---|---|---|---|
| **T-1** | B5F2 / B7F1 的 C4「节点入参是普通 `dict`」 | **只补注记**：无 context ⇒ 精确 `dict`；有 context ⇒ 带只读 `.context` 的 `dict` 子类，映射内容仍可变、映射语义不变 | 并入 G-1 |
| **T-2** | C25（节点别名）· Q8 active 清单 / 宪法 / 立项书 §5.2 / §5.3 / §9.2 / 宪法 changelog | **正式移除**：C25 从 active 清单移除、编号保留不复用；C26/C27 不重编号；宪法 1.16.0 + changelog；立项书 B8F3 行改为 C21/C22；未来 alias 使用新编号（如 C28） | 并入 G-1 |
| **T-3** | B6F1 `add_node(alias=)` / `_NodeRecord.alias` | **移除**：参数 / 字段 / 测试 / 合同同步 | 并入 G-1 |
| **T-4** | B2F2 门面 `add_node(..., alias=None)` / 兼容矩阵 | **移除**：签名 / 矩阵 / research / checklist 同步 | 并入 G-1 |
| **T-5** | B22F1「别名归 B8F3 / v1 不解析」注记 | **只补注记**：别名已移除；图导出 `name == id` 不变 | 并入 G-1 |
| **T-6** | 验收脚本 / README / 测试的 C25 用例 | **移除**：`case_node_alias` / C25 软断言行 / 相关断言 | 并入 G-1 |
| **T-7** | B6F1 / B7F2 / B8F2 的 alias 交接注记 | **撤回 / 收缩**：B8F2 D-1 收缩为「只用内部节点名」 | 并入 G-1 |

---

## Project Structure

### Documentation (this feature)

```text
specs/b8f3-node-alias-context/
├── plan.md                         # 本文件
├── spec.md                         # 权威 spec（alias 已移除）
├── research.md                     # Phase 0：决策 + 上游实测 + 代码锚点
├── data-model.md                   # Phase 1：实体 / 不变量 / 生命周期
├── quickstart.md                   # Phase 1：可执行验证指南
├── contracts/
│   ├── context-channel-contract.md # C21 / C22 运行期接线契约
│   ├── alias-removal-contract.md   # alias 移除的签名 / 字段 / 失败信号
│   └── upstream-parity.md          # P / E / D / X / T 对照
├── checklists/requirements.md      # 规格质量清单
└── tasks.md                        # Phase 2 输出（/speckit.tasks 生成，本命令不创建）
```

### Source Code (repository root)

```text
src/freegraph/
├── _stategraph.py                  # 移除 _NodeRecord.alias / add_node(alias=)
├── graph.py                        # 门面导出；无签名改动
├── contracts/
│   ├── types.py                    # RunConfig 九字段（零改动）
│   ├── graph.py                    # Node 文档去掉 C25 引用
│   └── protocols.py                # 无签名改动
├── runtime/
│   ├── _context.py                 # 新增：ContextVar + _ContextState + bind/get
│   ├── _stream.py                  # StreamSession 绑定 / 复原 context
│   ├── superstep.py                # _node_input 包装；run_graph 绑定；fan-out 边界
│   ├── _stream_context.py          # 既有流式上下文；不改
│   └── __init__.py                 # 公开 23 符号不变
└── ...

tests/
├── facade/
│   ├── test_context_channel.py     # 新增：公开 invoke / stream / RunConfig
│   ├── test_stategraph_builder.py  # 改：alias 移除 / TypeError / 无 alias 字段
│   └── ...
├── runtime/
│   ├── test_context_channel.py     # 新增：L2 _node_input / route / fan-out / C4
│   ├── test_acceptance_script.py   # 改：README 不再保留 C25；C21 硬断言
│   ├── test_context_manual_record_guard.py # 新增：人工记录守卫（T039）
│   └── ...
├── contracts/
│   ├── test_graph.py               # Node.name 是展示名，不是 C25 别名（不变）
│   └── test_c25_retirement.py      # 新增：C25 正式作废守卫（T038）
└── differential/
    └── parity_probe.py             # 移除 D-74 alias；新增 D-137…D-144

harness/
├── demo/
│   ├── graph_core.py               # 删 case_node_alias；C21 soft -> check
│   ├── README.md                   # 删 C25 软断言行 / A10；更新覆盖 C1–C24
│   └── acceptance.py               # 更新 core 覆盖描述
└── verification/
    └── B8F3/manual-verification.md # 新增：实测 + 零出站 + T-1…T-7 追认

README.md                           # 删 StateGraph 行的 alias / C25
```

**Structure Decision**：单项目库（`src/` + `tests/` + `harness/`）；L3 → L2 → L1 方向不变；
`_context.py` 是 **L2 私有模块**（`__all__ = []`），不进入 `freegraph.runtime.__all__`；
无新子包 / 无新公开模块。

---

## Complexity Tracking

| 复杂度 | 为什么需要 | 更简单的替代为什么被拒绝 |
|---|---|---|
| 新增 L2 私有 `_context.py` | `context` 必须同时服务 `invoke` 与 `stream`，且不能进入状态 / `RunConfig.configurable` | 复用 `_stream_context.py`（流式专用）⇒ invoke 不经过它；复用 `configurable` ⇒ 违反 C21 / 拖回 `langchain-core` |
| 新增 `_ContextState(dict)` | 提示词已冻结 `getattr(state, "context", None)`，同时 C4 要求无 context 时精确 `dict` | 把 `context` 放进状态字典 ⇒ 破坏 schema / 归约 / C4；把 state 换成非 dict 包装 ⇒ 破坏 C4 |
| `Send.arg` 的 dict / 非 dict 边界 | `Send.arg` 是任意对象；只有 dict 能安全附加 `.context` | 包装所有对象 ⇒ 改变用户对象类型 / 身份；完全不包装 ⇒ dict 形态的 fan-out 失去 context |
| C25 移除的跨 feature 修订（T-2…T-7） | 用户明确判断 alias 无真实收益，要求彻底移除；保留 no-op 会误导 | 保留 no-op 关键字 ⇒ 用户以为可用；保留 alias 语义 ⇒ 继续维护无收益的命名空间 |

---

## Phase 0: Outline & Research

**输出**：[research.md](./research.md)

已解决的关键未知点（无 `NEEDS CLARIFICATION`）：

| # | 未知点 | 决策 |
|---|---|---|
| 1 | `context` 的运行期载体 | 新 L2 私有 `ContextVar`（`_context.py`）；`run_graph` / `StreamSession` 绑定 |
| 2 | 节点如何读到 context | 标准节点入参包装为带只读 `.context` 的 `dict` 子类；`context is None` 时保持精确 `dict` |
| 3 | 路由是否能看到 context | fresh 状态视图不能；第二参 `config` 可携带 `RunConfig.context` |
| 4 | `Send.arg` 的 context | `dict` ⇒ 包装；非 `dict` ⇒ 原样（v1 边界） |
| 5 | alias 移除后的失败信号 | `add_node(alias=...)` ⇒ `TypeError`；不静默忽略 |
| 6 | C25 历史文字 | 保留 + 注记「正式作废、编号不复用」；不删除历史 |
| 7 | 是否新增公开面 | 否；`runtime.__all__` 23 不变；无新依赖 |
| 8 | 测试策略 | facade + runtime + differential + demo/acceptance + manual |

**上游实测**：E-01（alias 静默忽略）· E-02（`Runtime.context`）· E-03（updates 内部名）·
E-04（图导出内部名）· E-05（路由视图无 context）。详见 [research.md](./research.md) §2。

---

## Phase 1: Design & Contracts

**输出**：[data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

### 1. 数据模型

- `RunConfig`：九字段不变；`context` 是唯一来源。
- `_ContextState(dict)`：只读 `.context`；映射内容 == 稀疏状态；不出现 `"context"` 键。
- `_CONTEXT`：L2 私有 `ContextVar[Any]`，默认 `None`。
- `_NodeRecord`：去掉 `alias`；保留 `name` / `action` / `defer` / `metadata` / `destinations`。
- `add_node`：去掉 keyword-only `alias`；其余参数不变。
- `Node.name`：图展示字段，**不是** C25 别名；保持现状。

### 2. 契约

| 契约 | 内容 |
|---|---|
| [context-channel-contract.md](./contracts/context-channel-contract.md) | 来源 / 节点视图 / 路由 / invoke / stream / 生命周期 / 禁止行为 |
| [alias-removal-contract.md](./contracts/alias-removal-contract.md) | `add_node` 签名 / `_NodeRecord` 字段 / 失败信号 / 不变量 / 受影响面 |
| [upstream-parity.md](./contracts/upstream-parity.md) | P-01…P-11 / E-01…E-05 / D-137…D-144 / X-1…X-3 / T-1…T-7 |

### 3. Quickstart

[quickstart.md](./quickstart.md) 提供：定向 pytest、全量 pytest、demo / acceptance、
差分场景、人工验证、零出站检查、alias 移除检查。

---

## Work Breakdown（供 `/speckit.tasks` 拆解）

> 本命令不创建 `tasks.md`；以下分组是任务拆解的输入。

### Phase A：契约修订（T-1…T-7 / R-1…R-7）

- A0：**正式修订宪法 1.16.0（MINOR）+ constitution-changelog v1.16.0 + `harness/prompts/init_constitution.md` 同步**：C25 从 active 清单移除、编号不复用、C26/C27 不重编号。
- A1：Q8 active 清单 + C25 墓碑；立项书 §5.2 B8F3 行 / §5.3 C25 行 / §9.2 graph_core / 架构图同步。
- A2：B6F1 契约 / data-model / spec 去掉 `alias`；撤回 D-3。
- A3：B2F2 门面 / 兼容矩阵 / research / checklist 去掉 `alias`。
- A4：B22F1 图导出注记去掉「别名归 B8F3」；保持 `name == id`。
- A5：B7F2 / B8F2 的 alias 交接注记撤回 / 收缩。
- A6：README / demo / acceptance / 测试的 C25 引用清理。

### Phase B：alias 移除（代码）

- B1：`_NodeRecord` 去掉 `alias`；`add_node` 去掉 `alias`。
- B2：确认 `add_node(alias=...)` 抛 `TypeError`，失败不修改构建器状态。
- B3：`contracts/graph.py` 的 `Node` 文档去掉 C25 引用（保留 `Node.name` 展示语义）。
- B4：更新 `tests/facade/test_stategraph_builder.py`（alias 移除 / 其余记录不变）。
- B5：移除 `tests/differential/parity_probe.py` 的 D-74 alias 场景。
- B6：`harness/demo/graph_core.py` / README / `acceptance.py` / `test_acceptance_script.py`
  清理 C25；C21 软断言升级为硬断言。

### Phase C：context 载体与节点视图

- C1：新增 `runtime/_context.py`（`ContextVar` / `bind_context` / `get_context` / `_ContextState` / `with_context` / `with_context_arg`）。
- C2：`_node_input` 包装标准节点入参。
- C3：`_run_round` 包装 `dict` 形态的 `Send.arg`；非 `dict` 原样。
- C4：`run_graph` 绑定 / 复原 context（invoke 路径）。
- C5：`StreamSession` 绑定 / 复原 context（stream 路径）。
- C6：确认路由 fresh 视图不包装；第二参 `config` 仍为原始 config。

### Phase D：context 测试

- D1：`tests/facade/test_context_channel.py`：invoke / stream / RunConfig / 无 `context=` 关键字。
- D2：`tests/runtime/test_context_channel.py`：`_node_input` / C4 / route / fan-out / 生命周期。
- D3：C4 回归：无 context ⇒ `type(state) is dict`；有 context ⇒ `isinstance` + 映射相等。
- D4：`tests/differential/parity_probe.py` 新增 D-137…D-144。
- D5：确认既有 `tests/runtime/test_conditional_edges.py:918`（路由视图无 context）保持绿。

### Phase E：验收 / 文档 / 人工门禁

- E1：`harness/demo/graph_core.py` C21 `soft(...)` ⇒ `check(...)` / `eq(...)`。
- E2：`harness/demo/acceptance.py` core 套件真跑通过。
- E3：`harness/verification/B8F3/manual-verification.md`（五段式 + 实测输出 + 零出站 + T-1…T-7 追认）。
- E4：README 兼容矩阵 / demo README 覆盖描述同步。
- E5：全量 pytest + 依赖门禁 + 零出站门禁。

---

## Pre-registered Red List（实施时逐条核对）

> 预登记依据 = 代码 / 文档 grep 实测；实施后 MUST 逐条归因，**MUST NOT** 只凭本表追认。

| # | 位置 | 预期变化 | 处置 |
|---|---|---|---|
| RD-01 | `tests/facade/test_stategraph_builder.py:61-77` | `record.alias` / `add_node(alias=)` | 改为 `TypeError` + 无 `alias` 字段；`defer` / `metadata` / 单 callable 断言保留 |
| RD-02 | `tests/differential/parity_probe.py:4139-4162,4220` | D-74 alias 场景 | 移除；D-142 在新 context 组覆盖「alias 传参 ⇒ TypeError」 |
| RD-03 | `tests/runtime/test_acceptance_script.py:59-65` | README「保留 C25」+ `当前一处` 断言 | 改为「C25 已移除」并同步 `当前一处`；新增 C21 硬断言检查 |
| RD-04 | `harness/demo/README.md:25,70,83` | C1–C25 / C25 软断言 / A10 行 | 改为 C1–C24；删除 C25 / A10 行；更新「软断言」段 |
| RD-05 | `harness/demo/acceptance.py:70` | `C1–C25` 描述 | 改为 `C1–C24` |
| RD-06 | `harness/demo/graph_core.py:31,563-602,660` | alias 头注释 / `case_node_alias` / `main` 注册 | 删除；C21 段改为硬断言 |
| RD-07 | `README.md:114` | `add_node(... alias=None ...)` / C25 | 删除 alias / C25；其余兼容矩阵不变 |
| RD-08 | `src/freegraph/contracts/graph.py:152` | `Node` 文档「C13 / C25」 | 改为 C13；注明 `Node.name` 是展示名，不是 C25 别名 |
| RD-09 | `tests/runtime/test_superstep_contract.py:204-227` | I-1 `type(state) is dict` | **保持绿**（无 context 时精确 dict） |
| RD-10 | `tests/runtime/test_conditional_edges.py:918` | 路由视图无 context | **保持绿**（不包装 route view） |
| RD-11 | `tests/contracts/test_types.py:350,364` | `RunConfig.context` | **保持绿**（字段零改动） |
| RD-12 | `harness/demo/graph_core.py` C21 段 | `soft(...)` | 改 `check(...)` / `eq(...)`；C21 真绿 |

**MUST NOT 变红**：`harness/demo/target.py`（只读基准）· `tests/differential/test_differential.py`
（B5F2 线性替身）· C4 / C6 / C8 / C11 既有回归 · `freegraph.runtime.__all__` 23 符号。

---

## Risks & Mitigations

| 风险 | 缓解 |
|---|---|
| `dict` 子类改变节点入参的 `type`，误伤 `type(state) is dict` 断言 | 仅在 `context is not None` 时包装；无 context 保持精确 `dict`；新增 C4 回归双断言 |
| `context` 泄漏到状态 / `values` / invoke 终态 | 只在 `_node_input` 包装视图；`_full_state` / channels / reducers 零改动；测试断言键集 |
| `context` 跨运行泄漏（contextvar 未复原） | `bind_context` 用 token + `finally` 复原；`run_graph` / `StreamSession` 两侧测试连续两次运行 |
| `Send.arg` 非 dict 无法附加 `.context` | 明确 v1 边界：只对 `dict` 包装；非 dict 原样；差分 / 单测覆盖 |
| alias 移除波及大量测试 / 文档 | 先做 T-2…T-7 文档修订，再改代码；按 RD-01…RD-12 逐条归因；不删除历史事实。C25 采用**墓碑式移除**：编号保留不复用、C26/C27 不重编号，避免改写已发布事实。 |
| 路由第二参 `config` 与 fresh 视图混淆 | 契约写死：fresh 视图无 context；第二参是原始 config；测试分别断言 |
| 契约修订未追认就合入 | T-1…T-7 追认文字落 `harness/verification/B8F3/manual-verification.md`；CI/人工门禁 |

---

## Baseline

- **测试收集（2026-11-20）**：`1742 tests collected`（`pytest --collect-only -q`）。
- **实施前 MUST**：记录 `pytest -q` 的真实 passed / skipped / failed / 耗时；实施后逐条归因
  RD-01…RD-12。**MUST NOT** 以本 plan 的收集数替代真实绿基线。

---

## Phase 1 Re-check（设计后）

| 宪法条款 | 复检结果 |
|---|---|
| I / II（零依赖 / 零出站） | `_context.py` 只用 `contextvars` / `collections.abc` / `typing`；零新增依赖 |
| III（target.py 只读） | 零改动 |
| IV（可诊断性） | context 不进入 stream 事件 / 图导出；既有诊断面零回归 |
| V（人工验收） | manual-verification 计划已列 |
| VI（规格驱动） | 本 plan + data-model + contracts + quickstart 与 spec FR/SC 一一对应 |
| VII（C21 / C22 / C25） | C21 / C22 接线；C25 **正式作废**（active = C1–C24 + C26–C27；编号不复用）+ 宪法 1.16.0 + changelog（T-2） |
| VIII（证据） | research 的 E-01…E-05 与上游 `路径:行号` 可复核 |
| IX / X（许可证 / 署名） | 零新增依赖；新文件带署名头 |
| XI（上游优先） | context 形态 X-1；alias 移除与上游无 alias 一致；alias 传参 STRICTER X-3 |
| XII（最优设计） | 单一 contextvar + 单一视图；不重复载体 |
| ARCH-1 | L3 → L2 → L1；`_context.py` 私有 |
| 冻结面 | T-1…T-7 已登记，唯一一次追认 |
