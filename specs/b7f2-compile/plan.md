# Implementation Plan: B7F2 · `compile()` → `CompiledGraph`

**Branch**: `b7f2-compile` | **Date**: 2026-11-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/b7f2-compile/spec.md`
（含 2026-11-16 澄清轮：13 条设计裁定 + 5 条上游自查补记 S-1…S-5 + 1 条用户裁定
「`store=` 发恰好 1 条 warning」= 裁定 14）

> **本 plan 的唯一权威输入 = `spec.md`**。本 plan 只承接 spec；若两者不一致，以 spec 为准并回修本 plan。
> 本 feature **不破**任何既有公开契约面（spec「破冻结面的回溯修订清单」只有 2 处**测试口径**更新
> + 1 处**已登记的实现落点修正**，见 R-1 / R-2 / R-3 / DD-02）。

---

## Summary

交付 `compile()`：把 B6F1 构建器产出的 `_BuilderSpec` **适配**为 L2 的 `GraphSpec`
（节点任务规格 + 触发依赖 + 通道表含路由通道），并把**条件边分支规格**与**可插拔能力注入项**
挂到一个满足 L1 `CompiledGraph` 协议的**编译产物**上；编译期完成**静态校验**（14 项 MUST 查 /
7 项 MUST NOT 查），未就绪的能力面 6 方法抛显式 `NotImplementedError`。

**核心判据**（spec §6 A1–A3 · SC-001 / SC-002 / SC-003）：

1. `compile()` **无参可调用**，返回非空编译产物；
2. `compile(checkpointer=None, store=None)` **不抛** `TypeError`；
3. 编译期 3 类错误（边目标不存在 / 条件边源不存在 / 条件边目标不存在）各一例被捕获。

**技术路线**：

| 关注点 | 落法 |
|---|---|
| **公开 API** | `StateGraph.compile` 签名**逐字不变**（B2F2 快照）；`freegraph.graph` 仍恰 7 个导出符号 |
| **产物落点** | 实现类 `CompiledGraph` 与构建器**同模块** `src/freegraph/_stategraph.py`（L3 **单文件**注册条目 ⇒ 见 DD-02 / R-11） |
| **产物持有** | 私有：`_spec`（`GraphSpec`）/ `_builder_spec`（完整 `_BuilderSpec`）/ `_conditional_edges`（plain mapping）· 公开：`checkpointer` / `store` / `cache` / `debug` / `name` / `transformers` / `interrupt_before_nodes` / `interrupt_after_nodes`（注入项同款见 E-31；`transformers` 命名见 **X-12**） |
| **图规格适配** | `parse_state_schema` + `build_channels` 已在 `_build_spec()` 内完成 ⇒ 本层**只做 END 过滤 + 组装**；**MUST NOT** 重解析 schema / 重造节点边表 / 另立第三套形态 |
| **`END` 过滤** | 只过滤**单源键**（`str`）的 `END` 目标；过滤后目标元组为空的源键**整体移除**；多源键原样保留 ⇒ 交 `GraphSpec` **V-16** 失败（B6F1 D-1） |
| **校验** | 构造 `GraphSpec` **即**校验（V-1 / V-2 / V-3 / V-14 / V-16 / V-22…V-25）+ 构建器 `_build_spec()` 的构建期末校验 ⇒ 全部落在 `compile()` 调用点；**不**做可达性 / 环 / 路由返回值检查 |
| **静态断点** | `compile` 入口只做**容器形态门**（`None` / `str` / `list`；`str` 原样透传；其余 ⇒ `TypeError` V-22 家族）；元素级与裸字符串失败信号由 `GraphSpec` 归一函数**逐字**产出（B13F1 D-1 / D-2） |
| **注入项** | 全部**接受 + 记录**，不做类型校验；`store=` 非 `None` ⇒ **恰好 1 条** `warnings.warn`（裁定 14）；其余只记录 + 文档写明 |
| **条件边** | `_BuilderSpec.conditional_edges` → `dict[str, tuple[dict[str, Any], ...]]`（B6F1 D-2 形状逐字）；`GraphSpec.conditional_edges` **恒空**（填了即 V-8 失败） |
| **能力面** | 6 方法**全部存在**；本 feature **全部**抛内置 `NotImplementedError`（消息点名 B7F3 / B8F2 / B22F1 / B15F1×2 / B16F1） |
| **多次编译** | 每次 `_build_spec()` 取新快照 ⇒ 产物彼此独立；不设 `compiled` 标志、不发「已编译后改图」提示（B6F1 裁定） |
| **可验证出口** | facade 编译测试 + 差分 `D-75…D-91` + `harness/verification/B7F2/acceptance.py` + 五段式人工验证 |

**范围边界**：本 feature 是 **MVP 六项最小交付集的第 2 项**，只交付「编译」环节。
`target.py` 端到端仍需 **B7F3（invoke）+ B8F1（路由）+ B22F1 / B23F1（图导出）**；
本 feature **MUST NOT** 声称 `target.py` 已跑通。

---

## Technical Context

**Language/Version**: Python **>= 3.11**（仓库既有口径；禁用 `TypeAliasType` / `override` /
`ReadOnly` / `TypeIs` / PEP 695 `type` 语句）。本 feature 只使用标准库
`typing` / `collections.abc` / `dataclasses` / `warnings`。

**Primary Dependencies**: **零第三方运行时依赖**（`dependencies = []`）⇒ 不新增依赖；
`langgraph 1.2.11` 只作为开发 / 测试侧差分依赖（上游缺席即 `skip`）。

**Storage**: N/A。无持久化、无文件 I/O、无网络。（`checkpointer` / `store` 只**持有**不**使用**。）

**Testing**: `pytest`（既有基线 + 新增 `tests/facade/test_compiled_graph.py` 等）· 差分探针
`tests/differential/parity_probe.py`（新增 compile-only 场景 `D-75…D-91`）· 一键验收
`harness/verification/B7F2/acceptance.py`。

**Target Platform**: Linux / macOS / Windows（纯同步，无 POSIX-only 依赖）。

**Project Type**: library（图运行时内核 · 图定义层 L3）。

**Performance Goals**:
- 编译期只做**线性**适配（节点 / 边 / 通道 / 条件边各一遍）+ 一次 `GraphSpec` 构造校验；
- 不引入热路径开销；不在 `compile()` 内做任何 schema 重解析；
- 本 feature 无运行期性能判据（不执行任何节点）。

**Constraints**:
- 零 `langsmith` / `langchain*` / `langgraph*` 运行时 import；零环境变量；零出站 / 零文件 I/O；
- **ARCH-1**：L3 只依赖 L1 / L2；**L3 内部禁止横向 import**（G25 同层规则 · L2–L5 禁同层）
  ⇒ 编译产物**必须**与构建器同模块（DD-02 / R-11）；
- `freegraph.graph` 仍恰 7 个导出符号；`StateGraph` 公开签名快照**逐字节不变**；
- 不新增 L1 符号 / 契约条目（active = C1–C24 + C26–C27；C25 已作废） / 门禁编号 G1–G30；
- `harness/demo/target.py` **只读**；
- 新源码 / 测试带署名头（G5 / G19 / G30）。

**Scale/Scope**: 立项书 §5.2 = **1,200 行**（实现约 640 / 测试约 560）· **3 人日**。
实际规模以 `/speckit.tasks` 的任务条数为准；本 feature 不单方面改上位文档数字。

**改动面**：

| # | 文件 | 动作 | 说明 |
|---|---|---|---|
| 1 | `src/freegraph/_stategraph.py` | **改（主体）** | 实现 `compile()`；新增 `CompiledGraph` 类（L3 私有；**L1 协议导入改为别名 `CompiledGraphProtocol`** 以避免同名影子化）；END 过滤 / `GraphSpec` 组装 / 条件边 plain mapping / 静态断点容器门 / 注入项记录与 `store` 告警 |
| 2 | `src/freegraph/graph.py` | **改（docstring only）** | 更新「`compile()` 仍抛 `NotImplementedError`（归 B7F2）」的过时说明；**导出面不变** |
| 3 | `README.md` | **改（事实性措辞）** | `StateGraph` 行的「`compile` 待 B7F2」改为「`compile` 已交付（B7F2）；`invoke` 待 B7F3」；`Store` 行补「v1 不支持（`compile(store=...)` 只接受并警告）」 |
| 4 | `tests/facade/test_facade.py` | **改（拆分不删）** | `TestNotWired` 拆为「compile 已接线」+「其余 5 个构建方法仍未交付」；`vars(graph)` 断言保留（compile 不改构建器状态）；**把 4 处 compile 桩断言替换为反面断言（不删除）**：`test_not_wired_compile_reports_b7f2` / `test_not_wired_compile_does_not_return_an_executable` / `test_not_wired_methods_produce_no_real_semantics` / `test_not_wired_method_raises_not_implemented[compile]` |
| 5 | `tests/facade/_gatesupport.py` | **零改动** | 本 feature **不新增源文件** ⇒ `FACADE_MODULES` / `SIGNED_SOURCE_FILES` 无需同步 |
| 6 | `tests/facade/test_compiled_graph.py` | **新增** | 产物能力面 / 注入项可读 / `store` 警告 / 快照独立 / 私有字段冻结名 / 不执行用户函数 |
| 7 | `tests/facade/test_compile_validation.py` | **新增** | 编译期 14 项检查清单逐项 + 7 项不检查项的反向断言（尤其动态路由编译成功） |
| 8 | `tests/facade/test_compile_interrupt.py` | **新增** | 静态断点 6 种形态 + 失败信号逐字同款 + `"*"` 展开 + 编译期可达性 |
| 9 | `tests/facade/_compiled_support.py` | **新增** | 编译测试共享夹具（复用 `_builder_support` 的 schema / 节点替身 / `CallCounter`） |
| 10 | `tests/differential/parity_probe.py` | **改** | 新增 compile-only 场景模型 + `D-75…D-91`，接入 `run_all()` |
| 11 | `tests/differential/test_parity_probe.py` | **改** | 新增 compile 场景的 pytest 包装 |
| 12 | `harness/demo/graph_core.py` | **改（A3 先跑 + 探 `invoke`）** | `main()`：`compile()` 可用即**先跑 A3（`case_build_and_compile`）**；随后探 `invoke()` —— 未就绪（B7F3）⇒ **A3 通过之后**以**退出码 2** 结束；`invoke` 也就绪 ⇒ 正常跑全部用例。**MUST NOT** 改用「产物具备 6 方法能力面 ⇒ 视为已就绪」（会打红 rc==2 硬断言） |
| 13 | `harness/demo/README.md` | **改（事实性）** | 软 / 硬断言清单同步（`compile` 不再是未接线桩） |
| 14 | `harness/verification/B7F2/acceptance.py` | **新增** | 一键验收（A1–A3 + 校验清单 + 注入项 + 幂等） |
| 15 | `harness/verification/B7F2/manual-verification.md` | **新增** | 五段式 + 来源覆盖 + EV-1 承接 |
| 16 | `harness/verification/README.md` | **改（记录表）** | 「当前已有记录」表补 B7F2 |
| 17 | `harness/features/{B7F3,B8F1,B8F3,B14F1,B22F1}_*.md` | **改（只接线）** | 各追加一条 **B7F2 → 目标** 的下游承接 |

**不改动**：`src/freegraph/runtime/**`（B7F1 / B4F1 / B5F1 / B10F1 / B13F1 冻结面）·
`src/freegraph/contracts/**`（L1 冻结面 · `CompiledGraph` 协议零改动）·
`src/freegraph/graph.py` 的导出面 · `tests/facade/test_api_snapshot.py` ·
`tests/contracts/**` · `tests/gates/**` · `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md`
（**不新增源文件 ⇒ 零改动**）· `harness/demo/target.py`（只读基准）。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原则 / 门禁 | 判定 | 证据 / 落点 |
|---|---|---|
| **I 零 LangSmith / 零环境变量** | 通过 | 零 `langsmith`；零环境变量读取（`debug` 缺省硬编码 `False` · X-9）；无出站 |
| **II 内核纯净** | 通过 | 零 `langchain*` 导入；只依赖标准库 + L1 / L2 |
| **III 验收契约优先** | 通过 | `target.py` 零改动；`compile()` 无参可调用（C10）；**不**声称端到端跑通（`invoke` 归 B7F3） |
| **IV 可诊断性** | 通过 | 编译期错误消息点名节点 / 源 / 分支 / 目标 / `entrypoint`；`store=` 的「未生效」当场可见（裁定 14）；未就绪方法消息点名归属 feature |
| **V 人工验收** | 通过 | `harness/verification/B7F2/manual-verification.md`（五段式 + EV-1 承接） |
| **VI 规格驱动 / 判据级追溯** | 通过 | spec 25 FR / 16 SC；tasks 每条 SC 挂**可执行判据**并建立双向追溯 |
| **VII 契约 C1–C24 + C26–C27** | 通过 | 不新增 L1 符号 / 契约条目；复用 C10 / C11 / C12 / C13 / C19 / C20；`store=` 的 v1 无实现**文档写明**（原则 VII） |
| **VIII 证据与术语纪律** | 通过 | 上游 `langgraph 1.2.11` + `路径:行号` + 本 plan 的实测 E-25…E-55；术语与 spec 一致 |
| **IX 许可证 / 商标** | 通过 | 零新增依赖、零新增第三方代码 |
| **X 署名头 / 文档合规** | 通过 | 新测试 / 验收脚本带署名头；README 与 demo README 只做**事实性**更新 |
| **XI 上游优先 / 三态一致** | 通过 | spec P-01…P-18 + P-03b / P-03c / P-05b / P-05c / P-17b；差分 `D-75…D-91`；DIFF → X-1 / X-3…X-10 / **X-12**（`transformers` 命名），STRICTER → X-2；**新增 P-03d / X-11**（断点对外形态，见 DD-14）；对照表与偏离登记逐条一致 |
| **XII 最优设计优先** | 通过 | 复用 `GraphSpec` / `NodeSpec` / `EphemeralValue` / `_BuilderSpec`；不新增第三套形态；断点单一载体（`GraphSpec` 归一值） |
| **ARCH-1 / ARCH-2** | 通过 | L3 → L1 / L2 合法；**L3 内部无横向 import**（单文件 · DD-02）；L1 / L2 不反向 import L3；顶层包仍惰性 |
| **G1–G30** | 通过 | 零新增门禁编号；既有门禁自动覆盖；**不新增源文件** ⇒ 层注册表零改动 |
| **冻结面** | 通过 | 公开 API 快照不变；B7F1 / B4F1 / B5F1 / B13F1 签名与语义不变；仅 2 处**测试口径**更新（spec 已登记） |

### 质量门禁的分阶段登记（EV-1 · 承接 B6F1 · 只接线）

> 宪法 v1.6.0「质量门禁的分阶段落地与发起者追认」的窄口径适用：本 feature 只交付**编译**，
> `invoke()` 尚未交付 ⇒ 部分门禁项**物理不可达成**。判据不放大、不伪装通过。

| # | 被偏离的门禁部分 | 不可达成根因 | 承接方 / 里程碑 | 本 feature 的替代判据 |
|---|---|---|---|---|
| **EV-1a** | 门禁 3 的「`target.py` 原样可跑」 | 需要 `invoke()` / 路由 / 图导出（B7F3 / B8F1 / B22F1 / B23F1） | **B7F3 / B8F1 / B22F1 / B23F1**（M2）· 双跑 **B25F1**（M4） | 本 feature 只判 `compile()` 侧：A1–A3 + 校验清单 + 注入项；`G29` 断言 `target.py` diff 为空；**G22「场景②」的运行期断言仍由 B7F3 点亮（B3F1 裁定 22 · H-6）** |
| **EV-1b** | 门禁 4 的「fake 模型跑通验收基线一轮」 | 无 `invoke()`，图不可执行 | **B25F1**（M4） | 以 facade 编译测试 + 差分编译探针替代；不写永久红 CI |
| **EV-1c** | 门禁 5 + 原则 V 的「真实模型一轮」 | 无 `invoke()`，无法跑真实模型轮 | **B25F1**（M4） | 人工验证记录照常五段式；真实模型轮具名承接 B25F1 |

**追认要求**：EV-1a / EV-1b / EV-1c 合并为**一次**发起者追认，文字落
`harness/verification/B7F2/manual-verification.md`；未追认前 MUST NOT 合入。
红线（依赖 / 许可证 / 商标 / 零出站）**不适用**本条，照常执行。

---

## Project Structure

### Documentation (this feature)

```text
specs/b7f2-compile/
├── plan.md              # 本文件
├── research.md          # Phase 0（上游实测 E-25…E-55 + 设计决策 DR-1…DR-16）
├── data-model.md        # Phase 1（产物实体 / 注入项 / plain mapping / 校验 CV / 顺序）
├── quickstart.md        # Phase 1（可运行验证指南）
├── contracts/
│   ├── compile-contract.md    # 编译产物与 compile() 的唯一权威契约
│   └── upstream-parity.md     # 上游对照 + 差分 + 偏离取证底稿（P-xx / D-xx / X-xx）
├── spec.md              # 需求与判据的唯一权威
├── checklists/
│   └── requirements.md  # 规格质量清单（16/16）
└── tasks.md             # Phase 2（/speckit.tasks 产出）
```

### Source Code (repository root)

```text
src/freegraph/
├── _stategraph.py                # 本 feature 主战场（L3 · 构建器 + CompiledGraph 同模块）
├── graph.py                      # 门面（仅 docstring 更新；导出面不变）
├── contracts/                    # L1（零改动 · CompiledGraph 协议不动）
└── runtime/
    ├── __init__.py               # L2 导出面（零改动）
    ├── superstep.py              # GraphSpec / NodeSpec / SchedulerState（复用）
    ├── _static.py                # normalize_static_points（复用 · 唯一断点形态判定）
    ├── schema.py / mapping.py    # parse_state_schema / build_channels（经 _build_spec 复用）
    └── channel.py                # Channel / EphemeralValue（复用）

tests/
├── facade/
│   ├── test_facade.py            # 改：TestNotWired 拆分
│   ├── test_compiled_graph.py    # 新增：能力面 / 注入项 / 快照 / 冻结字段名
│   ├── test_compile_validation.py# 新增：检查清单 14 项 + 不检查项 7 项
│   ├── test_compile_interrupt.py # 新增：静态断点 6 形态 + 逐字同款
│   ├── _compiled_support.py      # 新增：夹具
│   └── _builder_support.py       # 复用（schema / 节点替身 / CallCounter）
├── differential/
│   ├── parity_probe.py           # 改：compile-only 场景 D-75…D-91
│   └── test_parity_probe.py      # 改：compile 场景包装
└── gates/                        # 零改动（既有门禁自动覆盖）

harness/
├── demo/
│   ├── graph_core.py             # 改：_facade_ready() 改为探 invoke（退出码 2 保持）
│   ├── README.md                 # 改：软/硬断言清单事实性同步
│   └── target.py                 # 只读（零改动）
└── verification/B7F2/
    ├── acceptance.py             # 新增：一键验收
    └── manual-verification.md    # 新增：五段式 + EV-1
```

**Structure Decision**：沿用仓库既有的单包分层。**编译产物与构建器同属 L3 的同一个文件
`src/freegraph/_stategraph.py`** —— 因为层注册表（`specs/b3f1-scaffold-ci-gates/contracts/
layer-registry.md`）把 `src/freegraph/_stategraph.py` 登记为**文件级 L3 条目**，而 G25 对
**L2–L5 的同层横向 import 一律判违规** ⇒ 若把 `CompiledGraph` 放进新文件
`src/freegraph/_compiled.py`，`_stategraph.py` 导入它就会构成 **L3 → L3** 违规
（除非改冻结的层注册表）。⇒ 选择**单文件**：零层注册表改动、零门禁扫描面缺口、
零既有条目层归属变更（原则 XII：形态取最优且代价最小）。详见 DD-02 / R-11。

---

## Implementation Strategy

> 顺序原则：先做**适配与产物**（无行为），再做**校验清单**，最后接测试 / 差分 / 验收 / 文档。
> 每个阶段结束跑 `pytest -q`，MUST NOT 让基线变红。

### Phase A · 产物骨架与注入项

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| A1 | 新增 `CompiledGraph` 类（L3 私有）：`__init__` 收 `spec` / `builder_spec` / `conditional_edges` / 注入项 / 归一断点；**仅** `_spec` / `_builder_spec` / `_conditional_edges` 落私有字段，注入项与归一断点**只**落 8 个公开实例属性（不另存私有副本 ⇒ `vars(compiled)` 恰 11 键）；公开属性 `checkpointer` / `store` / `cache` / `debug` / `name` / `transformers` / `interrupt_before_nodes` / `interrupt_after_nodes`（值 = 记录值 / `GraphSpec` 归一后的元组） | `_stategraph.py` | FR-002 / FR-010 · SC-002 / SC-015 |
| A2 | 实现 6 个能力面方法，签名逐字对齐 L1 协议（`invoke(input, config=None)` / `stream(input, config=None, *, stream_mode="values")` / `get_graph(*, xray=False)` / `get_state(config)` / `get_state_history(config)` / `update_state(config, values, as_node=None)`），全部抛 `NotImplementedError` 并**点名归属 feature** | `_stategraph.py` | FR-011 · SC-004 / SC-008 |
| A3 | `CompiledGraph` 带**私有**标记（模块内 `_` 前缀类名之外，类型不进 `freegraph.graph` 导出面；`__all__` 不动） | `_stategraph.py` | FR-017 · SC-013 |

> ⚠️ **2026-11-20 · B8F2 回溯修订注记（T-3 · 只补注记 · 原 A2 描述不改写）**：
> 自 **B8F2** 起，A2 的 `stream(input, config=None, *, stream_mode="values")` 已由
> `NotImplementedError` 改为**真实交付**；签名默认值改为 **`stream_mode=None`（解析为
> `"updates"`）**、`config` 放宽为 `RunConfig | Mapping[str, Any] | None`。原 A2 描述保留为
> **历史事实**；现行权威见 `contracts/compile-contract.md` §2.4 的注记与
> `specs/b8f2-stream-modes/contracts/stream-contract.md`。

### Phase B · `compile()` 入口与图规格适配

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| B1 | `compile()` 调 `self._build_spec()`（**唯一**入口 · 不重解析 schema） | `_stategraph.py` | FR-008 · SC-009 |
| B2 | 边表适配：**仅**过滤单源键（`str`）的 `END` 目标；过滤后目标元组为空 ⇒ 移除该源键；多源键（`tuple`）**原样**透传 | `_stategraph.py` | FR-007 · SC-008 |
| B3 | 构造 `GraphSpec(channels=<_BuilderSpec.channels 的**新映射**>, nodes=..., edges=..., interrupt_before=..., interrupt_after=...)` ⇒ **构造期**完成 V-1 / V-2 / V-3 / V-14 / V-16 / V-22…V-25 校验；`conditional_edges` **不传**（恒空） | `_stategraph.py` | FR-003 / FR-004 / FR-005 · SC-006 |
| B4 | 静态断点**容器形态门**：`None` → `()`；`str` / `list` **原样**交 `GraphSpec`（元素级失败信号逐字同款）；其它（含 `tuple` / `set` / 数值）⇒ `TypeError`（V-22 家族，消息带字段名与类型） | `_stategraph.py` | FR-013 / FR-014 · SC-007 |
| B5 | 条件边 plain mapping：`dict[str, tuple[dict[str, Any], ...]]`，内层 5 键逐字（`branch` / `path` / `path_map` / `targets` / `route_channels`），顺序 = 登记顺序，`branch` 取自 `_ConditionalEdgeSpec.branch` | `_stategraph.py` | FR-009 · SC-010 |
| B6 | 注入项记录：全部接受、不做类型校验；`store is not None` ⇒ `warnings.warn(..., stacklevel=2)` **恰好 1 条**（点名「v1 不支持 `Store`」）；`store is None` 不警告 | `_stategraph.py` | FR-016 · 裁定 14 · SC-015 |
| B7 | 返回 `CompiledGraph` 实例（**每次新对象** · 每个产物私有状态互不共享） | `_stategraph.py` | FR-019 · SC-012 |

### Phase C · 校验清单与边界

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| C1 | 核对 FR-005 的 **C-01…C-14** 逐项落点（schema → 构建器源/入口/目标/空表 → `GraphSpec` V-1/V-2/V-3/V-14/V-16 → 入口层 C-11 → `GraphSpec` 归一 C-12 → 构建器 C-13/C-14）；**失败必须发生在 `compile()` 调用点**（⚠️ **C-13 例外**：由 `add_conditional_edges` 立即层抛出，早于 `compile()`；**C-07 / C-08 为防御性检查**，以正向用例覆盖） | `_stategraph.py` | FR-005 · SC-003 / SC-006 |
| C2 | 核对 FR-006 的 **N-01…N-07** 均**未**被误检（尤其 `path_map=None` 的动态路由必须编译成功；不检查 checkpointer / store 的类型） | `_stategraph.py` + 测试 | FR-006 · SC-006 |
| C3 | 异常类型面：只用内置 `ValueError` / `TypeError`（schema 沿用 B4F1 `InvalidSchemaError`；未就绪用 `NotImplementedError`）⇒ 零新增异常类型 | `_stategraph.py` | FR-018 · SC-003 |
| C4 | 顺序与确定性：通道 key 顺序 = schema 声明顺序 + 路由通道（首次出现顺序）；节点 / 边 / 条件边顺序 = 登记顺序；两次 `compile()` 结构等价 | `_stategraph.py` | FR-021 · SC-009 / SC-012 |

### Phase D · 测试与差分

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| D1 | `TestNotWired` **拆分**：① 新增 `TestCompileIsWired`（`compile()` 返回产物、6 方法存在、不再抛 `NotImplementedError`）；② 保留 `vars(graph)` 精确集合断言（compile **不改**构建器状态）；③ 新增「其余 5 个构建方法仍抛 `NotImplementedError`（消息「本版本不交付」）」；④ **将「compile 不返回可执行产物」替换为反面断言（不删除）**；⑤ `NOT_WIRED_PATTERN` 收窄 / 移除（仅此一处引用） | `tests/facade/test_facade.py` | SC-004 / SC-013 |
| D2 | 新增 `test_compiled_graph.py`：A1–A3 判据 / 产物非空 / 6 方法 / 注入项可读（`is` 同一对象）/ `store` 警告恰好 1 条 / `store=None` 零警告 / 私有字段名冻结 / 构建器后续变更不影响产物 / 两次编译独立 / 通道零残留 | `tests/facade/` | SC-001 / SC-002 / SC-004 / SC-011 / SC-012 / SC-015 |
| D3 | 新增 `test_compile_validation.py`：14 项检查逐项（正向 + 反例）；7 项不检查项的反向断言（动态路由编译成功、非法 checkpointer 不报错、无可达性检查等）；**3 类核心错误**各一例且消息点名 | `tests/facade/` | SC-003 / SC-006 / SC-008 |
| D4 | 新增 `test_compile_interrupt.py`：`None` / `"*"` / `["a"]` / `("a",)` / `"a"` / `["nope"]` 六形态；`"*"` 展开为全部可执行节点；元素级失败消息与 `GraphSpec` 构造期**逐字**一致（直接比较两条消息字符串） | `tests/facade/` | SC-005 / SC-007 |
| D5 | 扩展 `parity_probe.py`：新增 compile-only 场景模型（`CompileScenario`：失败则比 `exc_type`；成功则比归一化摘要 `(方法面, 注入项身份, store 警告条数, 断点元组)`），落 `D-75…D-91` 并接入 `run_all()`；`test_parity_probe.py` 加包装 | `tests/differential/` | SC-016 |
| D6 | 纯净性测试：编译期节点 / 路由 / 归约器调用计数 == 0；无 I/O；`socket` 夹具断言 freegraph 出站 == 0 | `tests/facade/` | SC-005 |
| D7 | 既有测试守护：`test_facade.py::TestAcceptanceScriptsCanImportTheFacade` 仍绿（`graph_core` 退出码 2 保持）；`test_api_snapshot.py` 逐字节不变 | `tests/` | SC-013 / SC-014 |

> **与 `tasks.md` 的阶段映射**：本 plan 的 Phase A→任务 T005–T006 · B→T007–T011 ·
> C→T022–T026（校验清单测试）· D→T014–T039 + T040–T041 · E→T042–T054（含 T043b）。
> `tasks.md` 的 Phase 1–9 是 speckit 的标准分组（按用户故事），
> **以 `tasks.md` 的执行顺序为准**；本 plan 的 A–E 只描述**技术分层**。

### Phase E · 验收 / 文档 / 接线

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| E1 | `main()` 改为「**先跑 A3**（`case_build_and_compile`：compile 无参 + `checkpointer=`/`store=` 关键字）**再探 `invoke()`**」：① compile 仍不可用 ⇒ rc **2**；② compile 可用、`invoke` 未就绪 ⇒ **A3 通过后** rc **2**（打印 `[环境未就绪]`）；③ 两者都就绪 ⇒ 正常跑。**MUST NOT** 用「6 方法能力面」当就绪判据 | `harness/demo/graph_core.py` | SC-001 / SC-002 / SC-014 |
| E2 | `harness/demo/README.md` 软 / 硬断言清单事实性同步（`compile` 已接线；`invoke` 仍待 B7F3） | `harness/demo/README.md` | 原则 X |
| E3 | 新增 `harness/verification/B7F2/acceptance.py`：A1–A3 / 校验清单 / 注入项 / 幂等 / 零副作用 | `harness/verification/B7F2/` | SC-001…SC-015 |
| E4 | 新增 `manual-verification.md`（五段式 + 来源覆盖 + EV-1 承接 + X-9/X-11/X-12 追认文字） | `harness/verification/B7F2/` | 原则 V |
| E5 | `harness/verification/README.md` 记录表补 B7F2 | `harness/verification/README.md` | 原则 V |
| E6 | 下游提示词初稿**只接线**：`B7F3`（D-1）/ `B8F1`（D-2）/ `B8F3`（D-3）/ `B14F1`（D-4）/ `B22F1`（D-5）各追加一条 | `harness/features/` | D-1…D-5 |
| E7 | 全量回归 + 门禁（G1–G30 中受影响的 G14 / G17 / G19 / G20 / G25 / G26 / G27 / G29 / G30）；MUST 在 D1–D7 之后执行 | 全仓 | SC-005 / SC-013 / SC-014 |

> **注**：T053 的门禁清单 MUST 与 E7 逐项对齐（含 `gate_G14`）。

---

## Design Decisions（摘要 · 详见 research.md）

| # | 决策 | 选定 |
|---|---|---|
| **DD-01** | 编译产物落点 | `src/freegraph/_stategraph.py`（L3 单文件）· 类名 `CompiledGraph` · 不继承 L1 协议 · 不进门面导出面 · **L1 协议以别名导入**（`from .contracts import CompiledGraph as CompiledGraphProtocol`）以避免同名影子化 |
| **DD-02** | 为何不新建 `_compiled.py` | 层注册表把 `_stategraph.py` 登记为**文件级 L3** 条目；G25 禁 **L3→L3** 同层横向 import ⇒ 新文件会**强制**改冻结的层注册表（或产生违规）⇒ 单文件是代价最小且不改冻结面的形态（原则 XII） |
| **DD-03** | `compile()` 签名 | 逐字沿用 B2F2 快照（`checkpointer` 位置参数 + 6 个 keyword-only + `cache` / `transformers`） |
| **DD-04** | 图规格适配 | 复用 `_build_spec()` 产物：`channels` **新映射**（同一批模板对象）· `nodes` 原样 · `edges` 过滤单源 `END` · `conditional_edges` **不填** |
| **DD-05** | `END` 过滤细则 | 仅 `str` 键；过滤后空目标元组 ⇒ 移除源键；`tuple` 键原样交给 V-16 |
| **DD-06** | 编译期校验 | 全部委托 `GraphSpec.__post_init__`（V-1 / V-2 / V-3 / V-14 / V-16 / V-22…V-25）+ 构建器 `_build_spec()` 的构建期末校验 ⇒ 单一真源、零重复实现 |
| **DD-07** | 静态断点容器门 | 入口层只判**容器形态**（`None` / `str` / `list` 之外 ⇒ `TypeError`）；元素级交给 `normalize_static_points`（逐字同款） |
| **DD-08** | 注入项 | 接受 + 记录 + **不校验类型**；`store` 非 `None` ⇒ 1 条 `warnings.warn(stacklevel=2)`；其余不警告 |
| **DD-09** | 能力面 | 6 方法**全部**抛 `NotImplementedError`（消息点名归属 feature）· 签名逐字对齐 L1 协议 |
| **DD-10** | 快照与幂等 | 每次 `compile()` 调 `_build_spec()` 取新快照 ⇒ 产物独立；不设 `compiled` 标志、不发改图提示 |
| **DD-11** | 通道规格 | 产物持**模板**（`GraphSpec.channels`）；编译期**零写入**；`_builder_spec.channels` 与 `_spec.channels` 是**两个独立映射** |
| **DD-12** | 条件边载体 | plain mapping `dict[str, tuple[dict[str, Any], ...]]`（B6F1 D-2 形状逐字）存私有字段 `_conditional_edges` |
| **DD-13** | 私有字段名冻结 | `_spec` / `_builder_spec` / `_conditional_edges` 三个名字是**跨 feature 接口**（B8F1 / B8F3 / B22F1 按名读取） |
| **DD-14** | 断点对外形态 | 公开属性 `interrupt_before_nodes` / `interrupt_after_nodes` 暴露**归一后的保序元组**（`"*"` 已展开、`None` → `()`）⇒ 与上游「保留 `"*"` 原值」（E-47）/「`None` → `[]`」**形态不同**（语义等价）⇒ 登记 **P-03d / X-11** |
| **DD-15** | `graph_core.py` 守卫 | **先跑 A3 再探 `invoke`** ⇒ A3 判据（SC-001/SC-002）真跑通过，且 `invoke` 未就绪时仍在 A3 之后以退出码 **2** 结束 ⇒ 既有 rc==2 硬断言零改动 |
| **DD-16** | 差分探针 | 新增 `CompileScenario`（编译成败 + 异常类型 + 归一化摘要），不改既有 runtime / builder 场景 |
| **DD-17** | 既有测试口径 | `TestNotWired` **拆分不删**（spec 已登记）· `NOT_WIRED_PATTERN` 收窄 · `vars(graph)` 断言保留 |
| **DD-18** | 文档 | README / demo README 只做事实性更新；API 快照与兼容矩阵符号面不变 |

---

## Risks & Mitigations

| # | 风险 | 影响 | 缓解 |
|---|---|---|---|
| **R-1** | 编译产物独立成文件 ⇒ **G25 L3→L3 违规** | 门禁红 / 迫使改冻结的层注册表 | **DD-02**：与构建器同模块；tasks 中显式禁止新建 L3 文件 |
| **R-2** | `compile()` 后 `graph_core.py` 退出码从 2 变 1 | `tests/runtime/test_acceptance_script.py` 与 `TestAcceptanceScriptsCanImportTheFacade` 变红 | **DD-15 / E1**：**先跑 A3 再探 `invoke`** ⇒ A3 真跑通过、退出码保持 2；E7 全量回归验证。⚠️ 若把守卫改成「6 方法齐备即就绪」⇒ 必然 rc=1 打红既有断言 |
| **R-3** | `TestNotWired` / `NOT_WIRED_PATTERN` 与「compile 不返回产物」断言过时 | 基线变红 | **DD-17 / D1**：拆分不删（spec「破冻结面」节已登记）；同 PR 内更新 |
| **R-4** | 静态断点元素级失败信号与 `GraphSpec` 构造期**不一致**（消息漂移） | 违反 B13F1 D-2「逐字同款」 | **DD-07**：入口层**只**判容器形态（`str` 原样透传），元素级与裸字符串 100% 委托 `normalize_static_points`；D4 用**字符串相等**断言 |
| **R-5** | 误把 `tuple` / `set` 放行给 `GraphSpec` | B13F1 D-1 的「tuple 只在 compile 入口拒绝」失效 | 入口层显式白名单（`None` / `str` / `list`）；D4 覆盖 `tuple` / `set` / 数值 |
| **R-6** | 编译期校验过严（可达性 / 环 / 路由返回值） | 合法图被拒（提示词 §10 的「误伤」） | spec FR-006 的 7 项不检查项逐条落测试；`path_map=None` 必须编译成功（D3） |
| **R-7** | 校验过松（把错误推迟到 `invoke()`） | 违反「编译期是最后的机会」 | C-01…C-14 逐项测试；失败必须在 `compile()` 调用点（D3 用 `pytest.raises` 包住 `compile()`） |
| **R-8** | `store=` 警告噪音（每次编译都喊） | 用户反感 / 测试噪音 | 只在 `store is not None` 时**恰好 1 条**；`store=None` / 其它关键字零警告（D2 计数断言） |
| **R-9** | 编译产物污染构建器快照（共享 `channels` 映射） | B8F1 运行期增补内部通道会改写 `_builder_spec` | `_spec.channels` 用**新映射**（同一批模板对象）；DD-11 + D2 断言两映射独立 |
| **R-10** | 公开属性面与上游不一致（多 / 少） | 兼容性面漂移 | 公开 8 项（7 项见 E-31；`transformers` 命名见 **X-12**）· 内部规格私有（X-10）· D6 边界断言（`nodes` / `channels` / `builder` 不公开） |
| **R-11** | 把 `CompiledGraph` 误写进 `graph.py` 门面 | G14（门面零实现体）红 | 只在 `_stategraph.py` 实现；`graph.py` 仅 docstring 更新 |
| **R-12** | `interrupt_before_nodes` 暴露原值 vs 归一值不一致 | 与上游形态差异未登记 | **DD-14**：暴露归一值 + 登记 **P-03d / X-11**；D4 断言 `"*"` 已展开 |
| **R-13** | 差分探针把「上游 fail / freegraph ok」误判 | 判词与实际不符 | `CompileScenario` 复用既有 `_run_builder` 的判词口径（SAME 比 kind + 摘要；STRICTER 必须有 note 且方向合法；DIFF 必须有 note） |
| **R-14** | EV-1 门禁项在本 feature 仍物理不可达成 | 永久红 CI | EV-1a/b/c 沿用 B6F1 的具名承接（B7F3 / B8F1 / B22F1 / B23F1 / B25F1）；人工验证记录追认 |

---

## Test & Verification Strategy

| 层 | 内容 | 判据 |
|---|---|---|
| **L3 facade / 产物** | A1–A3 · 产物非空 · 6 方法 · 注入项可读 · 快照独立 · 零状态残留 · 冻结字段名 | SC-001 / SC-002 / SC-004 / SC-010 / SC-011 / SC-012 / SC-015 |
| **编译期校验** | C-01…C-14 逐项（正反例）· 3 类核心错误消息点名 · 失败在 `compile()` 调用点 | SC-003 / SC-006 / SC-008 |
| **不检查项（反向）** | 动态路由 `path_map=None` 编译成功 · 非法 checkpointer 不报错 · 不检查可达性 / 环 / 返回值 | SC-006 |
| **静态断点** | 6 形态 · `"*"` 展开 · 元素级消息与 `GraphSpec` **逐字**一致 · 编译期可达性 | SC-005 / SC-007 |
| **纯净性** | 用户函数调用计数 == 0 · 零 env · 零出站 · 零 I/O | SC-005 |
| **差分** | `D-75…D-91`（上游缺席 `skip`）· 判词与对照表一致 | SC-016 |
| **契约门禁** | `target.py` diff 为空（G29）· 公开 API 快照逐字节不变 · G25 层方向 · G20 署名头 | SC-013 / SC-014 |
| **验收脚本** | `harness/verification/B7F2/acceptance.py` · `graph_core.py` A3 组 | SC-001 / SC-002 / SC-014 |
| **人工** | 五段式 + 来源覆盖 + EV-1 承接 | 原则 V |

> `invoke()` 的端到端真跑**不在**本 feature 范围；由 **B7F3 / B25F1** 按 spec 的下游承接
> D-1 与 EV-1 收口。本 feature **MUST NOT** 写永久红 CI。

---

## Downstream Wiring（spec D-1…D-5 · 只接线）

| # | 承接方 | 动作 | 落点 | 接线状态 |
|---|---|---|---|---|
| **D-1** | B7F3 | `invoke()` MUST 驱动 L2 `run_graph(spec, input, *, checkpointer=..., config=...)` 并把结果归一成完整状态字典；每次 `invoke` MUST **新建**通道实例（多会话隔离的另一半）；MUST NOT 另写执行路径 | `harness/features/B7F3_invoke返回完整状态.md` 的 `## 下游承接` 块 | 待接线（tasks 落一条最小改动） |
| **D-2** | B8F1 | MUST 从 `compiled._conditional_edges` 读取并填入 `GraphSpec.conditional_edges`（承接 V-8 放宽）；**路由求值只消费 L2 的 `GraphSpec.conditional_edges`**；**MUST NOT** import `freegraph._stategraph` / `_ConditionalEdgeSpec`；不重新归一化 `path_map`；沿用 `branch:to:<target>` | `harness/features/B8F1_条件边路由与fresh读.md` | 待接线 |
| **D-3** | B8F3 | **已撤回（C25 正式作废）**：B8F3 不再读取 `_NodeRecord.alias`；不要求用户重新声明 | `harness/features/B8F3_节点别名与context通道.md` | 历史 |
| **D-4** | B14F1 | MUST 补上上游同款的 **checkpointer 编译期类型校验**（上游 `ensure_valid_checkpointer` ⇒ `TypeError` · E-29）；校验口径由 B14F1 冻结 | `harness/features/B14F1_Checkpointer协议与MemorySaver.md` | 待接线 |
| **D-5** | B22F1 | `get_graph(*, xray=False)` MUST 从 `_spec`（节点 / 边 / 通道）与 `_conditional_edges` 导出结构；MUST NOT 重新解析构建器状态 | `harness/features/B22F1_get_graph与draw_mermaid.md` | 待接线 |

> spec 已冻结上述接口；目标提示词初稿尚未逐字写入 B7F2 → 目标的承接条目 ⇒ 本 feature 的
> tasks MUST 包含五条「只接线 · 逐条最小改动」任务；**MUST NOT** 越界实现下游行为。

---

## Post-Design Constitution Re-Check（Phase 1 后）

| 复核项 | 结果 |
|---|---|
| **原则 XI 判定顺序** | P-01…P-18 + P-03b / P-03c / P-03d / P-05b / P-05c / P-17b 全部带版本 + `路径:行号`；行为断言有本 plan 的实测 **E-25…E-55** 支撑；失败信号分叉仅 X-2；X-11（形态）/ X-12（命名）属可见形态差异，其余 DIFF 均为分层接缝 / 定位边界 / 能力未就绪且已登记 |
| **三态标注一致性** | DIFF → P-03 / P-09 / P-10 / P-11 / P-12 / P-13 / P-14 / P-17b / P-03c（内部规格）/ P-03c（`transformers` 命名）/ P-03d ⇒ X-1 / X-3 / X-4 / X-6 / X-7 / X-5 / X-8 / X-9 / X-10 / **X-12** / X-11；STRICTER → P-05b ⇒ X-2；SAME → 其余；无孤行 / 漏行 |
| **层纪律** | L3 单文件；L3 → L1 / L2 合法；无 L3 → L3 |
| **导出面** | `freegraph.graph` 仍 7 个；`StateGraph` 公开签名快照逐字节不变；`CompiledGraph` 不进快照 |
| **冻结面** | B7F1 / B4F1 / B5F1 / B13F1 零改动；仅 2 处测试口径更新（spec 已登记） |
| **可判定性** | 25 FR / 16 SC 均可由自动化测试或人工记录判定；`D-75…D-91` 判词齐备 |
| **永久红** | EV-1a/b/c 具名承接 B7F3 / B8F1 / B22F1 / B23F1 / B25F1；`graph_core.py` 仍退出码 2 |
| **零出站 / 零 env** | 零新依赖 / I/O / 网络；`warnings` 为本地输出（非出站） |

---

## Complexity Tracking

> 无未登记的宪法违规。EV-1a / EV-1b / EV-1c 属宪法 v1.6.0 的**门禁分阶段**，已具名承接
> B7F3 / B8F1 / B22F1 / B23F1 / B25F1；判据未放宽。
> X-1 / X-6 / X-7 / X-8 / X-10 属**分层接缝**（原则 XII 的层次对应）；
> X-3 / X-4 属**定位边界 / 能力未就绪**；X-5 属 B6F1 已裁定的范围边界；X-9 属零环境变量红线；
> X-11 属**同语义单载体**（原则 XII）；X-12 属**命名形态**（`transformers` 与上游
> `stream_transformers` 不同名）；X-2 属更严失败信号。全部已登记且与对照表标注一致。

| 复杂度来源 | 为什么需要 | 更简单的替代为何被拒 |
|---|---|---|
| 编译产物与构建器同模块（约 +250 行） | 层注册表冻结 + G25 禁 L3→L3 | 新建 `_compiled.py` 要么改冻结的层注册表，要么引入 L3→L3 违规 |
| 入口层「容器形态门」与 `GraphSpec` 归一**双段**判定 | B13F1 D-1（tuple 只在入口拒绝）+ D-2（元素级逐字同款） | 单段委托无法拒绝 tuple（`GraphSpec` 接受 `Sequence`）；单段自判会与 `GraphSpec` 消息漂移 |
| 条件边 plain mapping（而非直接填 `GraphSpec.conditional_edges`） | B7F1 的 `conditional_edges` 非空即 V-8 失败；V-8 放宽归 B8F1 | 直接填会让 B7F2 的 `compile()` 自身失败 |
| 8 个公开只读属性 | 注入项同款见 E-31（`transformers` 命名见 **X-12**）⇒ 用户可观察注入项 | 全私有会让「记录生效」不可验证（SC-002 / SC-015 失去用户可观察口径） |
