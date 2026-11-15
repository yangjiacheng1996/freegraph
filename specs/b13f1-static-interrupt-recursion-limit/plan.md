# Implementation Plan: B13F1 · 静态中断点 + `recursion_limit`

**Branch**: `b13f1-static-interrupt-recursion-limit` | **Date**: 2026-11-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/b13f1-static-interrupt-recursion-limit/spec.md`

---

## Summary

交付两项 **L2 运行期安全阀**：

1. **静态中断点**：`GraphSpec.interrupt_before` / `.interrupt_after` 在指定节点**前 / 后**
   挂起；挂起态复用 B10F1 的 **`InterruptResult`**（4 字段 · `interrupts == ()` · 结果键
   `"__interrupt__": ()`）⇒ **不新增结果类型 / 不另写挂起路径**。
2. **`recursion_limit`**：普通 dict / `RunConfig` 两种载体；默认 **10007**（硬编码 ·
   零环境变量）；按 **super-step 执行轮**计数（fan-out 轮计入）⇒ 超限抛
   **`GraphRecursionError`**（结构化属性 + 明确消息）。

**关键接缝**（spec Q14 / 裁定 14）：静态挂起用显式 **`suspension_kind`**
（`static_before` / `static_after`）标记 ⇒ `next` **可为空**（最后节点 after / 纯 fan-out
before）仍可恢复，且不被误判为 `no_pending_interrupt`。

**范围边界**：本 feature 是 **M1 收口**，只交付 L2；`compile()` / `invoke()` / 构建器属
**B7F2 / B7F3 / B6F1（M2）**。`graph_core.py` 的软断言**立即升级**，端到端真跑作为**具名承接
D-3** 延期到 B7F3（**EV-1**）。

---

## Technical Context

**Language/Version**: Python **>= 3.11**（开发 / CI 实测 CPython 3.11.16；上游差分用 3.12）

**Primary Dependencies**: **零第三方运行时依赖**（`dependencies = []`）；只依赖标准库；
`langgraph 1.2.11` **仅**以 PEP 735 依赖组出现在测试侧（`differential`）。

**Storage**: N/A —— 本 feature **不实现** checkpointer；只消费既有 `Checkpointer` 协议；
测试用 B10F1 的 `StubCheckpointer`；生产 saver 归 B14F1。

**Testing**: `pytest`（既有 1203 passed / 4 skipped 基线）；差分探针
`tests/differential/parity_probe.py`（上游缺席即 skip）。

**Target Platform**: 跨平台（Linux CI 主档 + Windows / CPython 3.11 兼容）；无 OS 特定逻辑。

**Project Type**: 库（图运行时内核 / library）。

**Performance Goals**:
- 静态断点判定 = 每轮 `O(标准任务数 + fan-out 任务数)` 的集合成员检查；
- `recursion_limit` 解析 = 入口一次，无热路径开销；
- **不得**因静态断点 / 上限检查引入额外线程、I/O、环境变量读取或网络。

**Constraints**:
- 零 `langsmith` / `langchain*` / `langgraph*` 运行时导入；
- 零环境变量、零出站、零文件 I/O；
- ARCH-1：L2 只依赖 L1；
- 不新增 L1 符号 / 契约条目 C1–C27 / 门禁编号 G1–G30；
- `harness/demo/target.py` **只读**；
- 新增代码行 / 分支覆盖率 **100%**；
- 既有冻结面**只增不删**（F-1…F-10）。

**Scale/Scope**: 680 行（实现 320 / 测试 360）· 3 人日（spec / 立项书 §5.2 的参考值）。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原则 / 门禁 | 判定 | 证据 / 落点 |
|---|---|---|
| **I 零 LangSmith / 零环境变量** | ✅ | 不读 `LANGGRAPH_DEFAULT_RECURSION_LIMIT`；10007 硬编码；无 `langsmith` |
| **II 内核纯净** | ✅ | 零 `langchain*` 导入；只依赖标准库 + L1 |
| **III 验收契约优先** | ✅ | `harness/demo/target.py` **零改动**；只改 `graph_core.py` 的软断言（F-6）与门面未就绪退出码 2 守卫（T102），以及 `README.md` 的软断言清单（F-7 / FR-032） |
| **IV 可诊断性** | ✅ | 静态挂起有明确结果键 / `suspension_kind`；递归错误结构化 |
| **V 人工验收** | ✅ | `harness/verification/B13F1/manual-verification.md`（五段式 + 来源覆盖） |
| **VI 规格驱动 / 判据级追溯** | ✅ | spec 32 FR / 24 SC；`tasks.md` 已按用户故事组织，每条 SC 挂判定任务 |
| **VII 契约 C1–C27** | ✅ | 不新增条目；静态断点 / `recursion_limit` 属 C17 运行期扩展 |
| **VIII 证据与术语纪律** | ✅ | 上游 1.2.11 + `路径:行号`；D-38…D-49 落差分探针 |
| **IX 许可证 / 商标** | ✅ | 无新依赖、无新第三方代码 |
| **X 署名头 / 文档合规** | ✅ | 新 `.py` 带署名头；contracts / quickstart 齐备 |
| **XI 上游优先 / 三态一致** | ✅ | P-01…P-20；DIFF → X-1/X-2/X-4/X-5/X-6/X-8，STRICTER → X-3/X-7，逐条对应（X-1 = P-12 / P-15；X-6 = P-20） |
| **XII 最优设计优先** | ✅ | 复用 `InterruptResult` / `GraphRecursionError`；不重复载体 |
| **v1.6.0 质量门禁分阶段** | ✅ | EV-1 具名承接 B7F3；不写永久红 CI |
| **v1.8.0 跨 feature 接线** | ✅ | H-1…H-8 / D-1…D-8 已写入 spec；tasks 已包含接线任务 **T106（待执行）**；**X-1 / X-2 / X-6 / X-8 追认**已落 **T103 / T114** |
| **ARCH-1 / ARCH-2** | ✅ | L2 → L1 合法；无 L2 → L3/L4/L5 |
| **G1–G30** | ✅ | 零新增门禁编号；既有门禁自动覆盖 |
| **冻结面** | ✅ | `GraphSpec` / `run_graph` / metadata / `fanout` 账本按 **F-1…F-10** 只增；**F-3 拆分 B11F1 的「`fanout` 不落盘」冻结面**（B11F1 `contracts/send-contract.md` §5.1 / `data-model.md` I-12 / `tasks.md` T019 / `plan.md` PR-8 / `research.md` DR-02·D-08 / `quickstart.md` DR-02 / `spec.md` D-3 同步修订 + 追认；`F-14` 仅顺序口径说明） |

**结论**：**无未登记的违规**。`GraphSpec` / `run_graph` 的签名变化是**兼容扩展**，但按
宪法 v1.8.0「破冻结面的三条」登记为 **F-1…F-10**，并在人工验证记录中追认。⚠️ **F-3 同时
拆分 B11F1 的「`fanout` 不落盘」冻结面**（`contracts/send-contract.md` §5.1 · `data-model.md`
I-12 · `tasks.md` T019 · `plan.md` PR-8 · `research.md` DR-02·D-08 · `quickstart.md` DR-02 ·
`spec.md` D-3）⇒ 该组文档 MUST 与 F-3 同 PR 修订，B11F1 的「不含」历史断言**拆分而不删**；
`spec.md` F-14 是**顺序口径**，只作「不受影响」说明，不是落盘修订对象。

---

## Project Structure

### Documentation (this feature)

```text
specs/b13f1-static-interrupt-recursion-limit/
├── plan.md              # 本文件（/speckit.plan 产出）
├── research.md          # Phase 0（上游实测 + 回归面 + 设计决策 + 遗留）
├── data-model.md        # Phase 1（实体 / 形状 / 校验 / 不变量）
├── quickstart.md        # Phase 1（可运行验证场景）
├── contracts/
│   ├── static-interrupt-contract.md   # 静态断点运行期契约
│   ├── recursion-limit-contract.md    # 递归上限契约
│   └── upstream-parity.md             # 上游对照 + 差分 + 偏离
├── spec.md              # 需求与判据的**唯一权威**
├── checklists/
│   └── requirements.md  # 规格质量清单（16/16）
└── tasks.md             # Phase 2（/speckit.tasks 已产出 · 按用户故事组织）
```

### Source Code (repository root)

```text
src/freegraph/
├── contracts/                    # L1（零改动）
│   ├── errors.py                 # GraphRecursionError（复用）
│   └── types.py                  # RunConfig.recursion_limit（已存在）
└── runtime/                      # L2（本 feature 的主战场）
    ├── __init__.py               # __all__ 仍 23 个（零新增导出）
    ├── superstep.py              # GraphSpec 字段 / 校验 / run_graph 解析 / 循环钩子 / metadata
    ├── _static.py                # 【新增 · 私有】静态断点常量 / 归一 / 匹配 / ack
    ├── _recursion.py             # 【新增 · 私有】默认值 / config 解析 / 上限校验
    └── _fanout.py                # fanout 账本编解码（只增函数）

tests/
├── runtime/
│   ├── test_static_interrupt.py          # 【新增】before / after / resume / 最终节点 / 优先级
│   ├── test_static_interrupt_fanout.py   # 【新增】fan-out × 静态断点
│   ├── test_recursion_limit.py           # 【新增】载体 / 默认 / 校验 / 计数 / 错误
│   ├── test_graph_spec_static.py         # 【新增】V-22…V-26
│   ├── test_interrupt_checkpoint.py      # 【扩展】suspension_kind / static_ack / fanout 往返
│   ├── test_interrupt_resume.py          # 【零改动】动态断言不改；静态恢复由 test_static_interrupt.py 覆盖
│   └── test_send_fanout.py               # 【零改动】动态断言不改；静态 × fan-out 由 test_static_interrupt_fanout.py 覆盖
├── differential/
│   └── parity_probe.py                   # 【扩展】D-38…D-49
└── gates/                                # 零改动（既有门禁自动覆盖）

harness/
├── demo/
│   ├── graph_core.py                     # 【改】soft → check + GraphRecursionError（F-6）
│   └── README.md                         # 【改】删除 recursion_limit 软断言行（F-7）
└── verification/
    └── B13F1/manual-verification.md      # 【新增】五段式 + 来源覆盖 + EV-1
```

**Structure Decision**：沿用仓库既有的单包分层：
- `_static.py` / `_recursion.py` 落在 **L2 目录条目** `src/freegraph/runtime/` 内
  ⇒ **层注册表零改动**（**MUST NOT** 为它们单独立条目 —— 会造成 L2 → L2 横向依赖误判）；
- 新增模块**私有**（`__all__` 恒空）⇒ `freegraph.runtime.__all__` 仍 **23** 个符号；
- 门面 / L1 / 构建器 / `compile()` **零改动**。

---

## Implementation Strategy

> **顺序原则**：先冻结「形状 / 校验」（无行为），再接「行为」（before / after），
> 再接「恢复 / 持久化」，最后接「验收 / 差分 / 文档」。
> 每个阶段结束都跑 `pytest -q`；**MUST NOT** 让基线变红。
> ⚠️ **Phase A–E 是工作流分组**；`tasks.md` 按用户故事（US1–US8）组织，二者不是同一套 Phase 编号。

### Phase A · 骨架与校验（无行为）

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| A1 | 新建 `_static.py`：`STATIC_BEFORE` / `STATIC_AFTER`、`normalize_static_points`、`static_hit`、`static_allowed` | `runtime/_static.py` | 纯函数 · 无 I/O |
| A2 | `GraphSpec` 增两个 keyword-only 字段；`_validate_graph_spec` **调用** `normalize_static_points` 完成归一 / 校验（**单一入口**）；先校验节点表再展开 `"*"` / V-25；frozen dataclass 用 **`object.__setattr__`** 写回归一后的 `tuple` | `runtime/superstep.py` / `runtime/_static.py` | V-22…V-25 · FR-029 |
| A3 | `run_super_step` / `run_super_steps` 入口 V-26 拒绝 | `runtime/superstep.py` | 签名不变 |
| A4 | 新建 `test_graph_spec_static.py` | `tests/runtime/` | V-22…V-26 全覆盖 + 防御性拷贝（FR-029） |

### Phase B · `recursion_limit`（独立可验收）

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| B1 | 新建 `_recursion.py`：`DEFAULT_RECURSION_LIMIT` / `resolve_config` / `resolve_limit` / `validate_limit` | `runtime/_recursion.py` | 纯函数 |
| B2 | `run_graph` 的 `config` 注解放宽 + 解析 + 传 effective limit | `runtime/superstep.py` | FR-010 / FR-012 |
| B3 | `GraphRecursionError` 使用 effective limit | `runtime/superstep.py` | SC-003 / SC-013 |
| B4 | 新建 `test_recursion_limit.py` | `tests/runtime/` | 载体重载 / 默认 / 校验 / 计数 / fan-out |

### Phase C · 静态 before / after（核心行为）

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| C1 | `_run_graph_loop` 增 before 检查（递归检查后、`_run_round` 前；**不移动**循环顶部 `steps += 1`；before 结果的 `steps` 按 `steps - 1` 计） | `runtime/superstep.py` | SC-001 / SC-007 |
| C2 | after 检查（`state.step += 1` 后）+ `next` 计算 | `runtime/superstep.py` | SC-002 |
| C3 | 静态挂起构造 `InterruptResult`（空载荷 · 正确 `executed` / `steps`） | `runtime/superstep.py` | SC-001 / SC-002 / SC-006 |
| C4 | `_static.py` 的 ack 检查接入 **before 与 after 两处**（after 的 `static_allowed` 与 before 同款，MUST NOT 只接 before） | `runtime/superstep.py` | SC-011 |
| C5 | 新建 `test_static_interrupt.py` | `tests/runtime/` | before / after / final / priority |

### Phase D · 检查点 / 恢复 / fan-out

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| D1 | `to_checkpoint` / `from_checkpoint` 增 `fanout` 键（缺省 `{}`） | `runtime/superstep.py` / `_fanout.py` | F-3 / SC-009 |
| D2 | `_suspend_metadata` / `_write_suspend` 增 `suspension_kind` / `static_ack` / `next` | `runtime/superstep.py` | F-9 / SC-011 |
| D3 | `_first_graph` / `_resume_graph` 静态恢复分支（**早于 `per_node` 映射** · `next` 可空 · 忽略 resume 值）；**两条入口（`input=None` / `Command(resume=...)`）MUST 都把 `static_ack` 传给 `_run_graph_loop`** | `runtime/superstep.py` | SC-011 / SC-012 |
| D4 | **仅当本次运行为静态恢复**且最终返回 `SuperStepResult` ⇒ 写完成快照清标记（D-08 / F-10）；**普通（非静态）完成 MUST NOT 调用该路径** | `runtime/superstep.py` | SC-011 · F-10 |
| D5 | `fanout` 账本编解码 + 缺键宽容 + **`_restore_scheduler` 回填 `state.fanout`** | `runtime/_fanout.py` / `runtime/superstep.py` | SC-009 |
| D6 | 扩展 `test_interrupt_checkpoint.py` / 新建 `test_static_interrupt_fanout.py` | `tests/runtime/` | SC-009 / SC-011 / SC-012 |

### Phase E · 验收 / 差分 / 文档

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| E1 | `graph_core.py`：`soft → check` + `GraphRecursionError` + 精确 except；**M1 门面未就绪守卫（退出码 2，不判 FAIL）** | `harness/demo/graph_core.py` | F-6 / SC-005 |
| E2 | `README.md` 删除 `recursion_limit` 软断言行 | `harness/demo/README.md` | F-7 |
| E3 | `parity_probe.py` 追加 **D-38…D-49** | `tests/differential/` | SC-022 |
| E4 | 新增 `harness/verification/B13F1/manual-verification.md`（五段式 + 来源覆盖 + EV-1） | `harness/verification/` | SC-021 |
| E5 | 全量回归 + 覆盖率 + `graph_core` 退出码 2 复核 | 全仓 | SC-023 / SC-024 |

---

## Design Decisions（摘要 · 详见 research §3 / data-model）

| # | 决策 | 选定 |
|---|---|---|
| **D-01** | 静态字段形状 | `GraphSpec` 两个 keyword-only 字段 · 缺省 `()`；裸 `"*"` 展开为**可执行**节点（排除 `__start__` / `__end__`） |
| **D-02** | 静态校验 | V-22…V-25 **单一入口**（`_validate_graph_spec` → `normalize_static_points`）· 裸 `"*"` 展开（仅可执行节点） · `["*"]` 非法 · 裸空串/裸哨兵 ⇒ TypeError、序列元素空串 ⇒ ValueError |
| **D-03** | 低层入口 | V-26 显式拒绝 |
| **D-04** | before 判定 | 递归检查后、`_run_round` 前；**不移动**循环顶部 `steps += 1`；`InterruptResult.steps = steps - 1`；整轮不执行 |
| **D-05** | after 判定 | 写合并、`state.step += 1` 后 |
| **D-06** | metadata | `suspension_kind` / `static_ack`（同时镜像进 `scheduler`） |
| **D-07** | 恢复 | `input=None` / `Command(resume=...)` 都接受；静态标记不抛 `no_pending_interrupt`；**两条入口都 MUST 传 `static_ack`**（否则静态 before 恢复首轮立即重挂）；空 `StateDict` 视为无新输入 |
| **D-08** | 完成清标记 | 静态恢复完成 ⇒ 写完成快照（`suspension_kind=None` / `static_ack=None` / `next=()` / `fanout={}`）· 登记为 **F-10**（一次性完成写；每轮末快照仍归 B14F1） |
| **D-09** | ack | 通道版本水位；无新写入不重复触发 |
| **D-10** | 上限解析 | dict / `RunConfig` **互斥二选一** > `max_steps` > 10007；不新增关键字 |
| **D-11** | fanout 账本 | `to_checkpoint` 增 `fanout` 键；`from_checkpoint` 缺键宽容；**`_restore_scheduler` 回填 `state.fanout`** |
| **D-12** | 上限校验 | **非 `None` 值**的 `bool` / 浮点 / 非 int ⇒ `TypeError`；`<1` ⇒ `ValueError`；`None` 视为未提供（落回下一层） |
| **D-13** | 模块落位 | `_static.py` / `_recursion.py` 私有；`_fanout.py` 增编解码 |
| **D-14** | graph_core | 立即升级；端到端延期 B7F3（EV-1） |

---

## Freeze Surface Revisions（F-1…F-10 · 只增不删）

| # | 冻结面 | 处置 |
|---|---|---|
| **F-1** | `GraphSpec` 构造签名 | 只增两个 keyword-only 字段 |
| **F-2** | `GraphSpec` 校验表 | 只增 V-22…V-25 **的调用点**（`_validate_graph_spec` → `normalize_static_points` 单一入口；不重复校验） |
| **F-3** | `SchedulerState` 检查点账本 | 只增 `fanout` 键（缺省 `{}`） |
| **F-4** | `run_graph` 签名 | `config` 注解放宽；**不新增**关键字；目标契约 `interrupt-resume-contract.md` §2 同步 |
| **F-5** | 恢复路径 `no_pending_interrupt` | 拆分：静态标记时继续 |
| **F-6** | `graph_core.py` | `soft` → `check` + 精确异常 |
| **F-7** | `README.md` 软断言清单 | 删除 `recursion_limit` 行 |
| **F-8** | B7F1 低层入口说明 | 只增「非空静态字段 ⇒ 显式拒绝」 |
| **F-9** | 检查点 metadata | 只增 `suspension_kind` / `static_ack`（MUST 镜像进 `scheduler`；既有键不变） |
| **F-10** | 静态恢复完成快照 | 只增一次性完成写（`next=()` / `interrupts=()` / `tasks=()` / `suspension_kind=None` / `static_ack=None` / `fanout={}`）；**不是**每轮末快照（后者仍归 B14F1） |

> 追认文字落 `harness/verification/B13F1/manual-verification.md`；
> **未追认前 MUST NOT 合入**（宪法 v1.8.0 的破冻结面三条）。
> ⚠️ 追认范围不止 **F-1…F-10**：`spec.md` 的 **X-1 / X-2 / X-6 / X-8** 也明确要求追认
> （承接方分别为 B7F3 / B7F2 / B7F1 契约 F-8 / B14F1–B16F1），tasks **T103 / T114** 必须覆盖。

---

## Downstream Wiring（D-1…D-8 · 只接线）

| # | 承接方 | 动作 | 落点 |
|---|---|---|---|
| **D-1** | B7F2 | `compile(interrupt_before=, interrupt_after=)` 填 `GraphSpec`；接受形态与上游一致（裸 `"*"` / `list[str]`） | `harness/features/B7F2_compile编译.md` |
| **D-2** | B7F2 | 编译期失败信号与 `GraphSpec` 构造期逐字同款；裸 `"*"` = All | 同 D-1 |
| **D-3** | B7F3 | `invoke(input, config)` 透传 dict 的 `recursion_limit`；不包装 `GraphRecursionError`；`graph_core` 硬断言真跑通过 | `harness/features/B7F3_invoke返回完整状态.md` |
| **D-4** | B7F3 | 静态挂起返回 `as_result_dict()`（含 `__interrupt__: ()`）；恢复接受 `None` / `Command(resume=...)` | 同 D-3 |
| **D-5** | B14F1 | 持久化 `suspension_kind` / `static_ack` / `fanout`；不要求动态中断载荷；**F-10 的完成快照是 B13F1 的一次性写**，B14F1 的每轮末快照 MUST NOT 与之冲突 / 重复 | `harness/features/B14F1_Checkpointer协议与MemorySaver.md` |
| **D-6** | B15F1 / B16F1 | 历史 / 时间旅行表示「静态挂起 + `suspension_kind` / `static_ack` + 空 next」；不假设 `next` 非空 | 对应提示词初稿的 `## 下游承接` |
| **D-7** | B6F1 | 构建器不得丢弃 / 改名静态断点配置 | `harness/features/B6F1_StateGraph构建器.md` |
| **D-8** | B24F1 | 兼容矩阵记录 `compile` 关键字与 `recursion_limit` 载体；零新增行 | `harness/features/B24F1_打包分发与兼容矩阵.md` |

---

## Risks & Mitigations

| # | 风险 | 影响 | 缓解 |
|---|---|---|---|
| **R-1** | 静态 before 与 fan-out 的「整轮不执行」被误实现为「只跳过目标」 | 同轮其它任务被执行 ⇒ 违反上游 / spec | 用 `_static_hit` 在 `_run_round` **之前**判定；测试覆盖「同轮标准 + fan-out」 |
| **R-2** | `next` 为空时被误判为 `no_pending_interrupt` | 最后节点 after / 纯 fan-out before 无法恢复 | `suspension_kind` + `static_ack`；测试覆盖两种空 `next` |
| **R-3** | 旧快照的 `suspension_kind` 未清 | 后续 `input=None` 重复执行静态 before | D-08 完成快照；测试覆盖「恢复完成后再次 `input=None`」 |
| **R-4** | fan-out 账本编码破坏 JSON 往返 | 既有 `test_interrupt_checkpoint` 变红 | `fanout` 缺省 `{}`；测试用 JSON 兼容 `arg`；非 JSON 登记 DR-01 / B14F1 |
| **R-5** | `bool` / 浮点上限被误接受 | 与 spec X-7 不符 | `type(value) is not int` + 专项测试 |
| **R-6** | `config` dict 归一丢失 `thread_id` | checkpointer 取不到会话 | 用 `RunConfig.from_dict(..., ignore_unknown=True)`；测试覆盖 `configurable.thread_id` |
| **R-7** | 静态断点在低层入口被静默忽略 | 用户误以为生效 | V-26 显式拒绝；测试覆盖两个入口 |
| **R-8** | `graph_core` 硬断言端到端不可跑 | A3 判据争议 | 立即升级 + L2 等价硬测试；M1 门面未就绪 ⇒ **退出码 2**（不判 FAIL）；EV-1 具名承接 B7F3 |
| **R-9** | 新增私有模块被误判为 L2 → L2 横向依赖 | G25 变红 | 落在 `runtime/` 目录条目内；**MUST NOT** 单独立注册表条目 |
| **R-10** | 覆盖率不足 | SC-023 失败 | 私有纯函数集中测试；`coverage --fail-under=100` 覆盖**全部变更源码**（`_static.py` / `_recursion.py` / `_fanout.py` 新函数 + `superstep.py` 新增分支） |
| **R-11** | 完成快照与 B14F1 每轮末快照重复 / 冲突 | 双写 / 旧标记未清 | **F-10** 明确为一次性完成写且**仅静态恢复**触发；**D-5** 约定 B14F1 不得重复；测试覆盖「完成后再次 `input=None`」+ **「普通（非静态）完成不写静态完成快照」反向用例** |

---

## Test & Verification Strategy

| 层 | 内容 | 判据 |
|---|---|---|
| **纯 L2 单元** | `_static.py` 归一 / 匹配 / ack；`_recursion.py` 解析 / 校验；`GraphSpec` V-22…V-26 + 防御性拷贝 | SC-014 / SC-015 / SC-023 |
| **L2 图级** | before / after / final / fan-out / resume / priority | SC-001…SC-012 |
| **检查点** | `suspension_kind` / `static_ack` / `fanout` 往返；完成清标记 | SC-009 / SC-011 / SC-012 |
| **差分** | D-38…D-49（上游缺席 skip） | SC-022 |
| **验收脚本** | `graph_core.py` 软断言升级；L2 等价硬测试 | SC-005 |
| **回归** | 既有 1203 + 新增全绿；`target.py` 零改动；变更范围仅限预期文件 | SC-015 / SC-016 / SC-020 / SC-024 |
| **人工** | 五段式 + 来源覆盖 + EV-1 | SC-021 |

> ⚠️ **SC-006 的 `invoke` 部分不在本 feature 的 L2 测试范围**：`invoke(input, {...})` 的
> dict 载体透传、不包装 `GraphRecursionError`、无显式关键字等对外判据由 **B7F3（M2）**
> 按**下游承接 D-3** 收口；B13F1 只判 `run_graph` 的载体与优先级。

---

## Post-Design Constitution Re-Check（Phase 1 后）

| 复核项 | 结果 |
|---|---|
| **原则 XI 判定顺序** | 每个设计点先查上游 ⇒ 静态 before/after、空载荷、恢复、fan-out、`"*"`、默认 10007 **全部照抄**；仅 X-1…X-8 刻意分叉并登记 ✅ |
| **三态标注一致性** | P-01…P-20 的 SAME / STRICTER / DIFF 与 X-1…X-8 逐条对应：DIFF → X-1/X-2/X-4/X-5/X-6/X-8；STRICTER → X-3/X-7；无孤行 / 漏行 ✅ |
| **层纪律** | `_static.py` / `_recursion.py` 在 L2 目录条目内；L2 → L1 合法；零 L2 → L3/L4/L5 ✅ |
| **导出面** | `runtime.__all__` 仍 23；L1 仍 21；门面仍 7 ✅ |
| **冻结面** | F-1…F-10 全部「只增不删」；无既有测试变红（C-01…C-12）✅ |
| **可判定性** | 32 FR / 24 SC 全部可判定（自动化 + 人工验证记录）；D-38…D-49 判词齐备 ✅ |
| **永久红** | EV-1 具名承接 B7F3；M1 门面未就绪 ⇒ graph_core 退出码 2（不判 FAIL）；MUST NOT 写永久红 CI ✅ |
| **零出站 / 零 env** | 默认值硬编码；无新依赖 / I/O / 网络 ✅ |

---

## Complexity Tracking

> **无未登记的宪法违规需要额外复杂度**。F-3 对 B11F1「`fanout` 不落盘」冻结面的拆分是
> **静态挂起跨恢复保留 fan-out 现场的最小必要修订**（拆分而不删 · 已在 F-3 登记并由
> B11F1 文档同步追认），**不是**为便利破冻结面。
> 新增的私有模块（`_static.py` / `_recursion.py`）与 `_fanout.py` 的编解码是
> **最小必要拆分**：保持 `superstep.py` 可读、保持私有面不进导出 / 兼容矩阵；
> 不引入新框架、新依赖或新门禁。

---

## 任务组织（已产出 · `/speckit.tasks`）

`tasks.md` 已按**用户故事**组织（Setup / Foundational / US1–US8 / Polish），以满足
「每个故事可独立实现、独立测试」。本 plan 的 **Phase A–E 是工作流分组**（骨架 → 上限 →
静态行为 → 检查点/恢复 → 验收），不是 tasks 的 Phase 编号；实施时按 tasks 的任务 ID 顺序推进：

- 每条 **SC** 至少挂 1 条**能判定它**的任务（宪法 v1.11.0）；
- F-1…F-10 / D-1…D-8 / P-01…P-20 / D-38…D-49 逐一映射到任务；
- 人工验证记录与 **EV-1** 追认文字包含在最后阶段。
