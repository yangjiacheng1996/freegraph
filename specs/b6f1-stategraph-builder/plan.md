> **2026-11-20 后续修订（C25 正式作废）**：`add_node` 不再接受 `alias`，`_NodeRecord` 不再含 `alias`。本计划中 alias 记录文字保留为历史。
> 差分场景 **D-74** 已迁移到 **B8F3 D-142**，`parity_probe.py` 不再承载；本计划中的 `D-50…D-74` 为历史范围。

# Implementation Plan: B6F1 · `StateGraph` 构建器

**Branch**: `b6f1-stategraph-builder` | **Date**: 2026-11-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/b6f1-stategraph-builder/spec.md`
（含 2026-11-15 澄清轮：Q10 内部接口载体 · Q11 路由通道位置 · Q12 更严失败信号）

> **本 plan 的唯一权威输入 = `spec.md`**。本 plan 只承接 spec；若两者不一致，以 spec 为准并回修本 plan。
> 本 feature **不破**任何既有冻结面（spec「破冻结面的回溯修订清单」为空）。

---

## Summary

交付 `StateGraph` 构建器：用户用**同名同签名**的 API 声明状态 schema、节点、静态边与条件边，
构建器完成**登记 + 构建期校验**，产出供 B7F2 消费的私有内部规格 `_BuilderSpec`。

**核心判据**：`harness/demo/target.py:142-155` 的建图代码原样可执行；`path_map` 的 list / dict
两形态各一例通过；边指向不存在节点、重复节点名、缺少入口等错误在构建期被显式指出；
`add_edge` 可链式；构建器**不执行**任何用户函数。

**技术路线**：

| 关注点 | 落法 |
|---|---|
| **公开 API** | `StateGraph` 的构造签名与 4 个核心方法签名**逐字不变**（B2F2 快照）；`validate()` 只补实现、不改签名 |
| **登记载体** | `_nodes` / `_edges` / `_conditional_edges` / `_branch_names` 全部为私有属性；构造期只初始化空容器 |
| **节点** | `_NodeRecord(name, action, defer, metadata)`（**C25 作废后无 alias**）；支持 `add_node(fn)` 单 callable 形态；取名 `__name__` → 类型名（普通 callable 的 `.name` 不参与） |
| **静态边** | 单源键 `str`、多源键 `tuple[str, ...]`；按源聚合、目标保序去重、相同边幂等；非法 `start_key` / `end_key` ⇒ `TypeError` |
| **条件边** | `_ConditionalEdgeDraft` 记录源 / 路由函数 / 归一化 `path_map` / 分支名；list → dict、dict 浅拷贝、`None` 按上游 `Literal[...]` 返回注解推断；分支名 `__name__`（`.name` 不参与）；`None` 推断不到 ⇒ `targets=()` / `route_channels=()` |
| **内部规格** | 私有 `_build_spec() -> _BuilderSpec`；`channels` / `nodes` / `edges` 与 B7F1 的 `GraphSpec` / `NodeSpec` 同构；`conditional_edges` 为 `_ConditionalEdgeSpec` 元组（含 `branch`） |
| **路由通道** | 每个静态非 `END` 目标一个 `EphemeralValue("branch:to:<target>", Any, guard=False)`，直接放进 `_BuilderSpec.channels` |
| **校验** | 立即层（节点重复 / 保留名 / 边源合法性 / `path_map` 类型 / 同名分支）+ 构建期末层（schema → 源 → 入口 → 目标 → 空节点表）；只用 `ValueError` / `TypeError`（schema 用 B4F1 `InvalidSchemaError`）；空节点表登记 X-5 |
| **不执行** | 节点函数、路由函数、归约器一律只持有、不调用；不实现 `compile()` / `invoke()` / `stream()` |
| **不越界** | **C25 已正式作废（alias 不再接受）** · `defer=True` 屏障不做（B7F4 X-03）· 静态断点关键字仍属 `compile()`（B7F2）· 其余上游同款构建方法保持显式未实现 |
| **可验证出口** | 新增 facade 构建器测试 + 差分构建探针 D-50…D-74 + `harness/verification/B6F1/acceptance.py` + 五段式人工验证 |

**范围边界**：本 feature 是 **M2 第 1 个 feature**，只交付「建图」环节。`target.py` 的端到端
运行仍需 **B7F2（compile）+ B7F3（invoke）+ B8F1（路由）+ B22F1 / B23F1（图导出）** 齐备；
本 feature **MUST NOT** 用任何方式声称 `target.py` 已跑通。

---

## Technical Context

**Language/Version**: Python **>= 3.11**（typing 构件上限 = 3.11；禁用 `TypeAliasType` /
`override` / `ReadOnly` / `TypeIs` / PEP 695 `type` 语句）。本 feature 只使用标准库
`typing` / `collections.abc` / `dataclasses`。

**Primary Dependencies**: **零第三方运行时依赖**（`dependencies = []`）⇒ 不新增依赖；
`langgraph 1.2.11` 只作为开发 / 测试侧差分依赖。

**Storage**: N/A。本 feature 无持久化、无文件 I/O、无网络。

**Testing**: `pytest`（既有基线 + 新增 facade 构建器测试）· 差分探针
`tests/differential/parity_probe.py`（上游缺席即 skip）。

**Target Platform**: Linux / macOS / Windows（纯同步，无 POSIX-only 依赖）。

**Project Type**: library（图运行时内核 / 图定义层）。

**Performance Goals**:
- 构建期只在 `add_*` / `validate()` / `_build_spec()` 做线性登记与校验；
- 不引入热路径开销；`_build_spec()` 不缓存、不重复解析用户函数；
- 本 feature 无运行期性能判据（不执行任何节点）。

**Constraints**:
- 零 `langsmith` / `langchain*` / `langgraph*` 运行时 import；
- 零环境变量、零出站、零文件 I/O；
- ARCH-1：L3 只依赖 L1 / L2；MUST NOT 反向 import；
- `freegraph.graph` 仍恰 7 个导出符号；`StateGraph` 公开方法签名快照逐字节不变；
- 不新增 L1 符号 / 契约条目（active = C1–C24 + C26–C27；C25 已作废） / 门禁编号 G1–G30；
- `harness/demo/target.py` 只读；
- 新增源码 / 测试行覆盖率达到仓库既有门禁要求。

**Scale/Scope**: 立项书 §5.2 = **1,320 行**（实现约 700 / 测试约 620）· **3 人日**。
实际规模以 `/speckit.tasks` 的任务条数为准；本 feature 不单方面改上位文档数字。

**改动面**：

| # | 文件 | 动作 | 说明 |
|---|---|---|---|
| 1 | `src/freegraph/_stategraph.py` | **改** | 4 个核心方法 + `validate()` + 私有 `_BuilderSpec` / `_NodeRecord` / `_ConditionalEdgeSpec` / `_build_spec()` |
| 2 | `src/freegraph/graph.py` | **改（docstring only）** | 更新「四个方法仍是桩」的过时说明；导出面不变 |
| 3 | `README.md` | **改（事实性措辞）** | `StateGraph` 行的「构建器行为待 B6F1 / B7F2 交付」改为「构建器已交付（B6F1）；compile 待 B7F2」 |
| 4 | `tests/facade/test_facade.py` | **改** | 把 `TestNotWired` 收窄到 `compile()` / 其余未交付方法；删除「四个方法都未接线」的过时断言 |
| 5 | `tests/facade/test_stategraph_builder.py` | **新增** | 目标脚本建图 / list+dict `path_map` / 链式 / `_build_spec` / 不执行用户函数 |
| 6 | `tests/facade/test_stategraph_validation.py` | **新增** | 立即层 + 构建期末层错误；消息可定位；异常类型 |
| 7 | `tests/facade/test_stategraph_spec.py` | **新增** | `_BuilderSpec` → `GraphSpec` 适配 / 快照独立性 / 顺序 |
| 8 | `tests/facade/_builder_support.py` | **新增** | 测试夹具 / 结构等价比较 / schema 与节点替身 |
| 9 | `tests/differential/parity_probe.py` | **改** | 新增 builder-only 场景模型与 D-50…D-74，并接入 `run_all()` |
| 10 | `tests/differential/test_parity_probe.py` | **改** | 新增 builder 场景的 pytest 包装 |
| 11 | `harness/verification/B6F1/acceptance.py` | **新增** | 一键验收（建图 + 校验 + 快照 + 差分等） |
| 12 | `harness/verification/B6F1/manual-verification.md` | **新增** | 五段式 + 来源覆盖 + EV-1 门禁偏离登记 |
| 13 | `harness/verification/README.md` | **改（记录表）** | 「当前已有记录」表补 B6F1 |

**不改动**：`src/freegraph/runtime/**`（B7F1 / B4F1 / B5F1 冻结面）· `src/freegraph/contracts/**` ·
`src/freegraph/graph.py` 的导出面 · `tests/facade/test_api_snapshot.py`（签名不变）·
`tests/gates/**` · `harness/demo/target.py` · `harness/demo/graph_core.py`（compile 仍为桩）。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原则 / 门禁 | 判定 | 证据 / 落点 |
|---|---|---|
| **I 零 LangSmith / 零环境变量** | 通过 | 零 `langsmith`；零环境变量读取；无出站 |
| **II 内核纯净** | 通过 | 零 `langchain*` 导入；只依赖标准库 + L1 / L2 |
| **III 验收契约优先** | 通过 | `target.py` 零改动；第 142–155 行建图代码原样可执行；不声称端到端跑通 |
| **IV 可诊断性** | 通过 | 构建期错误消息点名节点 / 源 / 分支 / 目标 / `entrypoint`；私有快照字段可读 |
| **V 人工验收** | 通过 | `harness/verification/B6F1/manual-verification.md`（五段式 + EV-1） |
| **VI 规格驱动 / 判据级追溯** | 通过 | spec 21 FR / 15 SC；tasks 每条 SC 挂可执行判据，并以 T050 建立双向追溯 |
| **VII 契约 C1–C24 + C26–C27** | 通过 | 不新增 L1 符号 / 契约条目；复用 C1 / C5 / C7 / C9 / C10；C25 已正式作废 |
| **VIII 证据与术语纪律** | 通过 | 上游 `langgraph 1.2.11` + `路径:行号` + 实测 E-01…E-24；术语与 spec 一致 |
| **IX 许可证 / 商标** | 通过 | 零新增依赖、零新增第三方代码 |
| **X 署名头 / 文档合规** | 通过 | 新测试 / 验收脚本带署名头；README 兼容矩阵 `StateGraph` 行事实性更新 |
| **XI 上游优先 / 三态一致** | 通过 | P-01…P-14 + P-02b / P-02c / P-03b / P-03c / P-04b / P-04c / P-04d / P-06b / P-06c / P-07b / P-07c / P-13b；D-50…D-74；DIFF → X-1 / X-3 / X-6 / X-7，STRICTER → X-2 / X-4 / X-5；P-13 的行为面限非 defer；H-2 的校验范围限 V-1 / V-2 / V-3（B9F1 的 `__parent__` 保留名检查 / V-16 归 B7F2）；`validate(interrupt)` 与上游同款；逐条对应 |
| **XII 最优设计优先** | 通过 | 复用 B4F1 / B5F1 / B7F1 既有载体；不新增第三套图规格；私有快照是形态最优（X-3 · Q10 发起者确认），而不是公开 API |
| **ARCH-1 / ARCH-2** | 通过 | L3 → L1 / L2 合法；L1 / L2 不反向 import L3；顶层包仍惰性 |
| **G1–G30** | 通过 | 零新增门禁编号；既有门禁自动覆盖 |
| **冻结面** | 通过 | 公开 API 快照不变；B7F1 / B4F1 / B5F1 签名与语义不变；本 feature 无破冻结面 |

### 质量门禁的分阶段登记（EV-1）

> 宪法 v1.6.0「质量门禁的分阶段落地与发起者追认」的窄口径适用：本 feature 按里程碑
> **只交付建图**，因此部分门禁项**物理不可达成**。判据不放大、不伪装通过。

| # | 被偏离的门禁部分 | 不可达成根因 | 承接方 / 里程碑 | 本 feature 的替代判据 |
|---|---|---|---|---|
| **EV-1a** | 门禁 3 的「`target.py` 原样可跑」 | 需要 `compile()` / `invoke()` / 路由 / 图导出，分别属 B7F2 / B7F3 / B8F1 / B22F1 / B23F1 | B7F2 / B7F3 / B8F1 / B22F1 / B23F1（M2 六项齐备）· 最终双跑 B25F1（M4） | B6F1 只判 `target.py:142-155` 建图段原样可执行；`G29` 断言 `target.py` diff 为空；**G22「场景②」的运行期断言不在本 feature 执行，由 B7F3 点亮（H-7 · 裁定 11）** |
| **EV-1b** | 门禁 4 的「fake 模型跑通验收基线一轮」 | 无 `invoke()`，图不可执行 | B25F1（M4） | 本 feature 以 L3 构建器单测 + 差分构建探针替代；不写永久红 CI |
| **EV-1c** | 门禁 5 + 原则 V 的「真实模型一轮」 | 无 `invoke()`，无法跑真实模型轮 | B25F1（M4） | 人工验证记录照常五段式；真实模型轮具名承接 B25F1 |

**追认要求**：EV-1a / EV-1b / EV-1c 合并为**一次**发起者追认，文字落
`harness/verification/B6F1/manual-verification.md`；未追认前 MUST NOT 合入。
红线（依赖 / 许可证 / 商标 / 零出站）**不适用**本条，照常执行。

---

## Project Structure

### Documentation (this feature)

```text
specs/b6f1-stategraph-builder/
├── plan.md              # 本文件
├── research.md          # Phase 0（上游取证 + 设计决策）
├── data-model.md        # Phase 1（实体 / 形状 / 校验 / 不变量）
├── quickstart.md        # Phase 1（可运行验证指南）
├── contracts/
│   ├── builder-contract.md   # 构建器内部规格的唯一权威
│   └── upstream-parity.md    # 上游对照 + 差分 + 偏离取证底稿
├── spec.md              # 需求与判据的唯一权威
├── checklists/
│   └── requirements.md  # 规格质量清单（16/16）
└── tasks.md             # Phase 2（/speckit.tasks 产出）
```

### Source Code (repository root)

```text
src/freegraph/
├── _stategraph.py                # 本 feature 主战场（L3）
├── graph.py                      # 门面（仅 docstring 更新；导出面不变）
├── contracts/                    # L1（零改动）
└── runtime/
    ├── __init__.py               # L2 导出面（零改动）
    ├── schema.py                 # parse_state_schema（复用）
    ├── mapping.py                # build_channels（复用）
    ├── channel.py                # EphemeralValue（复用）
    └── superstep.py              # GraphSpec / NodeSpec（复用）

tests/
├── facade/
│   ├── test_facade.py            # 改：收窄未接线断言
│   ├── test_stategraph_builder.py
│   ├── test_stategraph_validation.py
│   ├── test_stategraph_spec.py
│   └── _builder_support.py
├── differential/
│   ├── parity_probe.py           # 改：builder-only 场景
│   └── test_parity_probe.py      # 改：builder 场景包装
└── gates/                        # 零改动（既有门禁自动覆盖）

harness/verification/B6F1/
├── acceptance.py                 # 新增：一键验收
└── manual-verification.md        # 新增：五段式 + EV-1
```

**Structure Decision**：沿用仓库既有的单包分层。`StateGraph` 实现体保持在
`src/freegraph/_stategraph.py`（层注册表已有条目），**不新增源文件**；私有快照类型也放在同一
模块内，避免新增层注册表条目或 L3 内部横向依赖。测试沿用 `tests/facade/`（通过公开门面
`freegraph.graph` 取 `StateGraph`），差分测试沿用 `tests/differential/`。

---

## Implementation Strategy

> 顺序原则：先完成注册与归一化（无 schema 解析），再做 snapshot + 校验，最后接测试 /
> 差分 / 验收 / 文档。每个阶段结束跑 `pytest -q`，MUST NOT 让基线变红。

### Phase A · 构建器骨架与节点登记

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| A1 | `__init__` 增加私有空容器 `_nodes` / `_edges` / `_conditional_edges` / `_branch_names`；只保存 `_schema` 参数并初始化空容器，忽略其余构造参数，不解析 schema；`vars(graph)` 的 key 集合恰为 `{"_schema", "_nodes", "_edges", "_conditional_edges", "_branch_names"}` | `_stategraph.py` | FR-001 |
| A2 | 新建 `_NodeRecord`；实现 `add_node` 的 str / 单 callable 形态、`__name__` → 类型名取名（`.name` 不参与）、重复 / 保留名 / 保留字符 / `action` 形态校验 | `_stategraph.py` | FR-002 / FR-005 / FR-010 / FR-011 |
| A3 | `defer` / `metadata` 原样记录；`metadata` 做浅拷贝；`alias` 已随 C25 作废；不调用用户函数 | `_stategraph.py` | FR-002 / FR-009 / FR-018 |
| A4 | **T032a**：与 A1–A3 / T008–T010 同批更新 `tests/facade/test_facade.py`：收窄 `TestNotWired`、更新 `vars(graph)` 断言；Phase A 结束 MUST 保持 `pytest -q` 绿 | `tests/facade/test_facade.py` | SC-010 |

### Phase B · 静态边与条件边登记

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| B1 | 实现 `add_edge`：单源 `str` / 多源 `list` / `tuple`；`END`/`START` 立即校验；`start_key` / `end_key` 非法类型 ⇒ `TypeError`；多源源与目标立即校验；按源聚合、目标保序去重、相同边幂等；返回 `Self` | `_stategraph.py` | FR-003 / FR-005 |
| B2 | 实现 `add_conditional_edges`：source / path / `path_map` 类型校验；list → dict；dict 浅拷贝；`None` 的 `Literal[...]` 推断；分支名 `__name__`（`.name` 不参与）；同名分支立即失败；返回 `Self` | `_stategraph.py` | FR-004 / FR-018 |
| B3 | 新建内部 `_ConditionalEdgeDraft`（source / path / path_map / branch_name） | `_stategraph.py` | FR-004 |

### Phase C · 快照与构建期校验

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| C1 | 实现 `_build_spec` 的校验顺序：schema 解析 → **源存在性** → **入口**（静态边 source == START 或条件边 source == START）→ **目标存在性** → **空节点表**（X-5）；失败不修改构建器状态。B6F1 的校验与 L2 `GraphSpec` 构造校验语义一致（**仅限 V-1 / V-2 / V-3**）；**B9F1 FR-005 的 `__parent__` 保留名检查**与 **V-16**（多源目标为 `END` / 目标数 ≠ 1）由 B7F2 构造 `GraphSpec` 时最终失败 | `_stategraph.py` | FR-006 / FR-017 / FR-019 |
| C2 | 构建 `channels` 的**状态通道基表**：B4F1 `parse_state_schema` + B5F1 `build_channels`；路由通道由 US2（T018）追加（`branch:to:<target>`、`EphemeralValue(Any, guard=False)`、排除 `END`、同目标只建一次；`defer=True` 目标也用 `EphemeralValue`，上游 `LastValueAfterFinish` 差异登记 X-7，由 B7F4 X-03 在 defer 落地时一并处理） | `_stategraph.py` | FR-007 / FR-020 |
| C3 | 构建 `nodes`：每个节点一个 `NodeSpec(subscribes=全部状态通道, run=action)`；顺序 = `add_node` 登记顺序 | `_stategraph.py` | FR-007 / FR-016 |
| C4 | 构建 `edges` / `node_records` / `conditional_edges`；`conditional_edges` 的 `branch` 取自 `_ConditionalEdgeDraft.branch_name`；`targets` 含 `END`，`route_channels` 不含 `END`（由 US2 填充）；`path_map=None` 且推断不到 ⇒ `targets=()` / `route_channels=()`、保留 `None`；每次返回新副本（含新通道实例） | `_stategraph.py` | FR-007 / FR-016 / FR-018 |
| C5 | 实现 `validate(interrupt=None) -> Self`：调用 `_build_spec()`，成功返回 `self`；`interrupt` 按上游校验节点存在性（未知节点 ⇒ `ValueError`） | `_stategraph.py` | FR-019 / FR-021 |

### Phase D · 测试与差分

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| D1 | 新建 `_builder_support.py`：schema / 节点替身 / 结构等价比较 / 调用计数器 | `tests/facade/` | SC-005 / SC-007 / SC-011 |
| D2 | 新建 `test_stategraph_builder.py`：target 建图段、list/dict `path_map`、链式、单 callable、别名 / defer / metadata 记录、`_build_spec` | `tests/facade/` | SC-001 / SC-002 / SC-004 / SC-005 / SC-014 |
| D2b | 新建 `test_stategraph_spec.py`：`_BuilderSpec` → `GraphSpec` 适配、快照独立性、顺序与结构等价 | `tests/facade/` | SC-005 / SC-011 |
| D3 | 新建 `test_stategraph_validation.py`：3 类核心错误（未知目标用例带有效入口）+ schema / 空节点表 / 条件边源与目标 / 多源 / 保留字符 / `path_map` 非法类型 / 非法 `start_key` / 普通 callable `.name` 不参与取名 | `tests/facade/` | SC-003 / SC-012 |
| D4 | **T032b**：为 `tests/facade/test_facade.py` 增加静态断点透传断言（`compile` 签名含 `interrupt_before` / `interrupt_after`；构建器无同名公开字段；`validate(interrupt=["nope"])` ⇒ `ValueError`）；`TestNotWired` 的收窄已在 A4 完成 | `tests/facade/` | SC-010 / SC-013 |
| D5 | 扩展 `parity_probe.py`：新增 builder-only 场景模型 + D-50…D-74（场景名含 `builder` 前缀），并接入 `run_all()` 使 `diff_parity.py -k builder` 可跑；`test_parity_probe.py` 新增包装测试；核对并复用 `research.md` 已登记的 E-18…E-24（不重复新增） | `tests/differential/` | SC-006 |
| D6 | 新增**宪法签名**兼容测试（只比较方法名 + 必填位置参数 / 顺序 + 返回语义；**MUST NOT** 比较完整 keyword-only 集合、默认值或注解；C25 已作废（alias 不再是关键字）；缺席 skip；附 `state.py:line`）（T046） | `tests/facade/test_stategraph_builder.py` | SC-006 |
| D7 | 新增最小图测试（2 节点 + START / END 边，T047）；条件边 START 入口测试由 T020 覆盖 | `tests/facade/test_stategraph_builder.py` / `tests/facade/test_stategraph_validation.py` | SC-015 / SC-003 |

### Phase E · 验收 / 文档

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| E1 | 新增 `harness/verification/B6F1/acceptance.py`：建图 / list+dict / 链式 / 错误 / 快照 / 不执行用户函数 | `harness/verification/B6F1/` | SC-001…SC-015 |
| E2 | 更新 `README.md` 的 `StateGraph` 行事实性措辞；`src/freegraph/graph.py` 与 `_stategraph.py` 的模块 / 类 / **方法级** docstring 同步；未交付方法的 `NotImplementedError` 消息改为「本版本不交付 · 另行立项」（MUST NOT 继续写「由 B6F1 交付」） | `README.md` / `src/freegraph/` | SC-010 / 门禁 G19 |
| E3 | 新增 `manual-verification.md`：五段式 + 来源覆盖 + EV-1 追认 | `harness/verification/B6F1/` | 原则 V |
| E4 | 全量回归 + 覆盖率 + 门禁（G17 / G18 / G19 / G21 / G24 / G25 / G26 / G27 / G29 / G30）；**MUST 在 D6 / D7（T046 / T047）之后执行** | 全仓 | SC-008 / SC-009 / SC-010 |
| E5 | 下游提示词初稿接线：B7F2 / B8F1 / B8F3 / B7F3 各追加一条 B6F1 → 目标承接（只接线；B7F3 承接 G22 场景②）（T039–T041 / T048） | `harness/features/` | D-1 / D-2 / D-3 / H-7 |
| E6 | 更新 `harness/verification/README.md` 的「当前已有记录」表（T049） | `harness/verification/README.md` | 原则 V |

---

## Design Decisions（摘要 · 详见 research.md）

| # | 决策 | 选定 |
|---|---|---|
| **DD-01** | schema 解析时机 | 构造期只保存 schema 参数并初始化空私有容器；`validate()` / `_build_spec()` 才解析 |
| **DD-02** | 节点登记 | `_NodeRecord`；支持 `add_node(fn)`；取名 `__name__` → 类型名（`.name` 不参与）；重复 / 保留名 / 保留字符立即失败 |
| **DD-03** | 静态边聚合 | 单源 `str`、多源 `tuple`；目标保序去重；相同边幂等；非法 `start_key` ⇒ `TypeError`（与上游同族 · SAME）；非法 `end_key` ⇒ `TypeError`（更严 · X-2） |
| **DD-04** | 条件边归一化 | list → dict；dict 浅拷贝；`None` 按 `Literal[...]` 推断；分支名 `__name__`（`.name` 不参与；lambda / 无名 ⇒ `condition`）；同名分支立即失败；非法元素 / value ⇒ `TypeError`；`None` 推断不到 ⇒ `targets=()` / `route_channels=()` |
| **DD-05** | 构建期校验顺序 | schema → 源存在性 → 入口（静态或条件边 source == START）→ 目标存在性 → 空节点表（X-5）；**B9F1 的 `__parent__` 保留名检查 / V-16 不在本层校验**，由 B7F2 构造 `GraphSpec` 时最终失败 |
| **DD-06** | 内部快照 | 私有 `_build_spec() -> _BuilderSpec`；每次新副本（新通道实例 / 新 `NodeSpec` / 新映射 / 元组）；通道按类型 / 归约器 / key 做结构等价；B7F2 消费时把 `conditional_edges` 机械翻译为纯内建类型 `dict[str, tuple[dict[str, Any], ...]]`（形状以 spec D-2 为准；`branch` 取自 `_ConditionalEdgeSpec.branch`），并把完整 `_BuilderSpec`（至少 `node_records`）保留在 `CompiledGraph` 私有字段供 B8F3 使用 |
| **DD-07** | 路由通道 | `EphemeralValue("branch:to:<target>", Any, guard=False)`；放 `channels`；`END` 不建；`defer=True` 目标也统一用 `EphemeralValue`（上游 `LastValueAfterFinish` 差异登记 X-7，由 B7F4 X-03 在 defer 落地时一并处理） |
| **DD-08** | `targets` 与 `route_channels` | `targets` 含 `END`；`route_channels` 不含 `END` |
| **DD-09** | 节点订阅集 | `NodeSpec.subscribes` = 全部状态通道；上游窄 `input_schema` 推断明确 Out of Scope |
| **DD-10** | 用户函数 | 全部只持有、不调用；不检查返回注解 |
| **DD-11** | 静态断点 | 构建器侧零动作（不新增字段、不拦截、不改名、不丢弃）；`validate(interrupt=...)` 按上游校验节点存在性；`compile()` 的 `interrupt_before` / `interrupt_after` 与正向透传归 B7F2 |
| **DD-12** | 其余构建方法 | `add_sequence` / `set_*` / `set_node_defaults` 保持显式 `NotImplementedError` |
| **DD-13** | 差分探针 | 在 `parity_probe.py` 内新增 builder-only 场景模型（D-50…D-74），不改既有 runtime 场景 |
| **DD-14** | facade 测试 | 收窄 `TestNotWired`，不删除公开签名快照断言；新增签名 parity / 最小图测试 |
| **DD-15** | 文档 | README 与 verification README 只做事实性更新；API 快照不变 |

---

## Risks & Mitigations

| # | 风险 | 影响 | 缓解 |
|---|---|---|---|
| **R-1** | 建图 API 参数名 / 位置与上游偏差 | `target.py` 建图段失败 | 逐项对照 P-01…P-14；差分 D-50…D-74；签名快照不变；T046 只比较必填位置参数 / 顺序 / 返回语义 |
| **R-2** | `path_map` 归一化与上游不一致 | list / dict 行为漂移 | 直接复制 `_branch.py:96-114` 的归一化与 `Literal` 推断；差分 D-51 / D-56 / D-60 / D-64；`None` 推断不到时 `targets=()` / `route_channels=()` 并保留 `None`（FR-007 ④） |
| **R-3** | 构建期校验过严 / 过松或顺序偏离 | 合法图被拒、错误优先级与上游不一致 | 按 spec 两层校验；构建期末顺序 = 源 → 入口 → 目标 → 空节点表；`validate()` / `_build_spec()` 复用同一 routine；差分 D-71 锁定顺序 |
| **R-4** | `_BuilderSpec` 被调用方修改后污染后续快照 | B7F2 看到不一致规格 | 每次返回新副本；测试两次快照独立性 |
| **R-5** | 路由通道与用户 schema key 同名 | 覆盖用户状态通道 | 复制上游 `state.py:1525-1530` 的覆盖行为；在 research 登记为已知边界 |
| **R-6** | `GraphSpec` 不接受 `END` 目标 / 多源 V-16 形态 / `__parent__` 保留名 | B7F2 直接消费快照时失败 | 快照保留 `END` 与多源目标；D-1 明确 B7F2 只过滤**单源** `END`，多源 **V-16 形态**（`END` / 目标数 ≠ 1）与 `__parent__` **B9F1 保留名检查**由 B7F2 最终失败 |
| **R-7** | 现有 facade 测试断言「四个方法未接线」与 `vars(graph) == {"_schema"}` | B6F1 后基线变红 | **Phase A4（T032a）** 与 T008–T010 同批收窄/更新测试：只保留 `compile()` / 其余未交付方法，`vars(graph)` 改为含私有登记容器的精确集合；在 spec「既有测试口径更新」节登记 |
| **R-8** | 公开 API 快照被内部类型污染 | G15 / G16 / G19 红 | 所有新增类型 / 方法以下划线开头；快照文件零改动 |
| **R-9** | 构建期误调用用户函数 | 副作用 / 测试红 | 用户函数只存入 `_NodeRecord` / `_ConditionalEdgeDraft`；不调用、不检查返回注解 |
| **R-10** | 门禁 3 / 4 / 5 在本 feature 物理不可达成 | 永久红 CI | EV-1a / EV-1b / EV-1c 具名承接 B7F2 / B7F3 / B8F1 / B22F1 / B23F1 / B25F1；人工验证记录追认；不写永久红断言 |

---

## Test & Verification Strategy

| 层 | 内容 | 判据 |
|---|---|---|
| **L3 单元 / facade** | target 建图段、list/dict `path_map`、链式、单 callable、别名记录、`_build_spec` 形状、签名 parity、最小图 | SC-001 / SC-002 / SC-004 / SC-005 / SC-006 / SC-014 / SC-015 |
| **构建期错误** | 重复节点、未知边端点、缺入口、条件边源 / 目标、schema、空节点表（X-5）、保留字符、非法 `start_key`、`path_map` 类型、普通 callable `.name` 不参与取名、条件边 START 入口、多源 END | SC-003 / SC-012 |
| **纯净性** | 用户函数 / 路由函数 / 归约器调用计数 == 0；无 I/O / env | SC-007 / SC-008 |
| **差分** | D-50…D-74（上游缺席 skip） | SC-006 |
| **契约门禁** | `target.py` diff 为空（G29）；公开 API 快照不变；L3 依赖合法 | SC-009 / SC-010 |
| **验收脚本** | `harness/verification/B6F1/acceptance.py` | SC-001…SC-015 |
| **人工** | 五段式 + 来源覆盖 + EV-1 追认 | 原则 V |

> `compile()` / `invoke()` 的端到端真跑不在本 feature 范围；由 **B7F2 / B7F3 / B25F1**
> 按 spec 的下游承接 D-1 与 EV-1 收口。本 feature **MUST NOT** 写永久红 CI。

---

## Downstream Wiring（spec D-1…D-3 · 只接线）

| # | 承接方 | 动作 | 落点 | 接线状态 |
|---|---|---|---|---|
| **D-1** | B7F2 | `compile()` MUST 消费 `_build_spec()`；**仅过滤单源 `END` 目标**后构造 `GraphSpec`（多源 **V-16 形态**：`END` / 目标数 ≠ 1 原样保留给 V-16；`__parent__` 由 B9F1 保留名检查失败）；**保留 `_BuilderSpec.conditional_edges`，并机械翻译为纯内建类型 `dict[str, tuple[dict[str, Any], ...]]`（内层 key / value 逐字为 `{"branch": str, "path": Callable, "path_map": dict[Hashable, str] \| None, "targets": tuple[str, ...], "route_channels": tuple[str, ...]}`，`branch` 取自 `_ConditionalEdgeSpec.branch`）存放在 `CompiledGraph` 私有字段（如 `_conditional_edges`）**；并保留**完整 `_BuilderSpec`（至少 `node_records`）**供 B8F3；B7F2 阶段不填 `GraphSpec.conditional_edges`；不重新解析 schema / 不重造节点边 | `harness/features/B7F2_compile编译.md` 的 `## 下游承接` 块 | 待接线（tasks 中落一条最小改动） |
| **D-2** | B8F1 | 把 B7F2 保留的 plain mapping 填入 `GraphSpec.conditional_edges` 并承接 V-8 放宽；之后只消费 L2 的 `GraphSpec.conditional_edges` 与 `branch:to:<target>` 路由通道；**MUST NOT import `_stategraph` / `_ConditionalEdgeSpec`**；不重新归一化 `path_map`；`path_map=None` MUST 原样保留并走动态求值 | `harness/features/B8F1_条件边路由与fresh读.md` 的 `## 下游承接` 块 | 待接线（tasks 中落一条最小改动） |
| **D-3** | B8F3 | **已撤回（C25 正式作废）**：B8F3 不再读取 `_NodeRecord.alias`；不要求用户重新声明 | `harness/features/B8F3_节点别名与context通道.md` 的 `## 下游承接` 块 | 历史 |

> spec 已冻结上述接口；目标提示词初稿尚未逐字写入 B6F1 → 目标的承接条目 ⇒ 本 feature 的
> tasks MUST 包含三条「只接线 · 逐条最小改动」任务；**MUST NOT** 越界实现下游行为。
> **H-7** 另需向 `harness/features/B7F3_invoke返回完整状态.md` 追加「G22 场景② 最小图运行期
> 断言」承接（只接线；本 feature 不执行运行期断言）。

---

## Post-Design Constitution Re-Check（Phase 1 后）

| 复核项 | 结果 |
|---|---|
| **原则 XI 判定顺序** | 每个设计点先查上游；P-01…P-14 + P-02b / P-02c / P-03b / P-03c / P-04b / P-04c / P-04d / P-06b / P-06c / P-07b / P-07c / P-13b 全部带版本 + `路径:行号`；P-03 / P-05 / P-14 等行为断言有 E-18…E-24 实测；失败信号分叉仅 X-2 / X-4 / X-5 / X-6 / X-7 且已登记；`validate(interrupt)` 与上游同款 |
| **三态标注一致性** | DIFF → P-02b / P-06c / P-11 / P-13b ⇒ X-1 / X-6 / X-3 / X-7；STRICTER → P-03b / P-04b / P-04c / P-06b / P-07c / P-10 / P-14 ⇒ X-2 / X-4 / X-5；SAME → P-01 / P-02 / P-02c / P-03 / P-03c / P-04 / P-04d / P-05 / P-06 / P-07 / P-07b / P-08 / P-09（顺序）/ P-12 / P-13（非 defer）；无孤行 / 漏行 |
| **层纪律** | `_stategraph.py` 属 L3，只 import L1 / L2；runtime 不反向 import L3 |
| **导出面** | `freegraph.graph` 仍 7 个；`StateGraph` 公开签名快照逐字节不变；新增类型全私有 |
| **冻结面** | B7F1 / B4F1 / B5F1 零改动；本 feature 无破冻结面 |
| **可判定性** | 21 FR / 15 SC 均可由自动化测试或人工记录判定；D-50…D-74 判词齐备；tasks 双向追溯（T050） |
| **永久红** | EV-1a / EV-1b / EV-1c 具名承接 B7F2 / B7F3 / B8F1 / B22F1 / B23F1 / B25F1；`graph_core.py` 仍退出码 2（不判 FAIL） |
| **零出站 / 零 env** | 无新依赖 / I/O / 网络；标准库 + L1 / L2 |

---

## Complexity Tracking

> 无未登记的宪法违规。EV-1a / EV-1b / EV-1c 属宪法 v1.6.0 的**门禁分阶段**，已具名承接
> B7F2 / B7F3 / B8F1 / B22F1 / B23F1 / B25F1；本 feature 的判据未放宽。
> X-6 属必须自研区（非 callable Runnable 的零依赖边界）；X-1（alias 增量）随 C25 正式作废。
> X-3 属原则 XII 的**形态优化**（Q10 发起者确认 · 上游锚点见 P-11）；
> X-2 / X-4 / X-5 属更严失败信号，均已登记；X-7 属已知不支持（defer 路由通道，承接 B7F4 X-03）；X-2 / X-4 已获 Q12 发起者确认。

| 复杂度来源 | 为什么需要 | 更简单的替代为何被拒 |
|---|---|---|
| 私有 `_BuilderSpec` / `_build_spec()` | L3 构建器与 L2 运行时物理分层；B7F2 需要唯一冻结接口 | 直接让 B7F2 读构建器私有属性会形成隐式契约，且无法保证顺序 / 副本 / 校验一致性 |
| 路由通道在构建器内创建 | spec FR-007 / FR-020 要求；B8F1 只做求值 | 让 B8F1 建通道会把「声明层」职责下推，违反分层 |
| 两层校验 | spec FR-006 要求早失败，同时保持上游单源边前向引用形态 | 全部立即校验会拒绝合法的「先边后节点」写法；全部推迟到 compile 会违反早失败需求 |
