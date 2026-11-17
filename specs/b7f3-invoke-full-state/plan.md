# Implementation Plan: B7F3 · `invoke()` 返回完整状态 + `InvalidUpdateError`

**Branch**: `b7f3-invoke-full-state` | **Date**: 2026-11-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/b7f3-invoke-full-state/spec.md`
（含 2026-11-16 澄清轮：16 条设计裁定 + 2 条用户裁定（**Q1 = 选项 A**（无值 key 填 `None` + 只读快照禁令）
+ **Q2 = 选项 A**（L1 的 `config` 注解一并放宽））

> **本 plan 的唯一权威输入 = `spec.md`**。本 plan 只承接 spec；若两者不一致，以 spec 为准并回修本 plan。
> 本 feature 的破面 = **5 类**（**唯一事实源 = spec.md「Assumptions」的「破面全集 5 类」**）：
> ① L1 `invoke` 的 **`input`** 注解放宽 ② L1 `invoke` 的 **`config`** 注解放宽
> ③ L2 `run_graph` 的 **`max_concurrency` 读取点**（兼容扩展）
> ④ **G19**「既有契约层矩阵行逐字未改」判据（新增 `MATRIX_ROWS_UPDATABLE_BY_B7F3` 白名单 · 只放行 `CompiledGraph` 一行）
> ⑤ **四处**「invoke 未就绪」冻结断言的拆分替换
> ⇒ ⇒ **同属一次**登记 + 回溯修订 + 发起者追认 ⇒ 追认额度 **1 次**（≤ 1 次/feature）
> ⇒ ⇒ 见 spec「破冻结面的回溯修订清单」与本 plan 的 **R-1**。

---

## Summary

交付 freegraph 的**主对外执行入口** `invoke(input, config=None)`：驱动 L2 的 `run_graph` 把整张图
跑到终止，并把结果归一成**完整状态字典**（**schema 全部 key** · 无值者以 `None` 补齐 ·
挂起时额外含 `"__interrupt__"`）；节点返回未知 key 时以 `InvalidUpdateError` 显式失败。

**核心判据**（**提示词初稿 §6** 的 A1–A3（`harness/features/B7F3_invoke返回完整状态.md`）
· SC-001 / SC-002 / SC-003 / SC-004；⚠️ **勿与 `graph_core.py` 的用例组 A1–A10 混用**）：

1. 返回值的**键集 == schema 全部 key**（顺序一致）⇒ `messages` 与 `llm_calls` **均在**；
2. `messages` == **初始 + 全部新增**（**不是**增量）⇒ `llm_calls` == 实际调用轮数；
3. 未知 key ⇒ `InvalidUpdateError` 且消息**点名**违规 key；
4. **多源汇合（屏障）**：`add_edge([a, b], c)` ⇒ 屏障目标 `c` 的写入出现在**所有**源之后
   （**静态多源边** · **B7F4 已交付于 L2** ⇒ **物理可达** · **不依赖 B8F1** ⇒ ⇒ ⇒ **EV-3 已撤销**
   · SC-013 恢复**整条**判定）。

**技术路线**：

| 关注点 | 落法 |
|---|---|
| **公开 API** | `CompiledGraph.invoke(input, config=None)`（**桩原地替换**）· 门面导出面**仍恰 7 个符号** · `freegraph.graph` **零改动**（除 docstring 的事实性说明） |
| **L1 协议** | `CompiledGraph.invoke` 的 `input` 放宽为 `StateDict \| Command \| None`、**`config` 放宽为 `RunConfig \| Mapping[str, Any] \| None`**（**与 L2 的 `run_graph` 逐字同款**）⇒ **破 L1 冻结面**（**两处 · 同属一次**追认） |
| **执行路径** | 调 L2 的 `run_graph(spec, input, *, checkpointer=..., config=...)` ⇒ **零新增执行路径**（B7F2 的 D-1 授权）⇒ **零 `try/except`** ⇒ 失败信号**原样**传播 ⇒ ⇒ ⚠️ **门面 MUST NOT 传 `max_concurrency` 关键字**（**旋钮的读取点在 L2** · 关键字优先 · `config` 兜底 ⇒ 见 **DD-3 / DD-4** · 裁定 13）⇒ ⇒ ⇒ ⇒ ⇒ **2026-11-16 analyse 轮 · 第三轮回修（FND-A1）**：原写「`..., max_concurrency=...`」⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 与 DD-3 / DD-4 / 契约 **ES-01** / tasks **T010 / T026** 的「**恒不传**」直接冲突 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **已订正**（门面**零搬运逻辑**） |
| **完整状态** | **一个**模块级私有函数 `_full_state(spec, sparse)`：键集 = `spec.channels` **扣除** `isinstance(channel, EphemeralValue)` 的路由通道（**B7F1 FR-014 的冻结判定**）⇒ 值 = `sparse.get(key, None)` ⇒ ⇒ **单一实现点**（下游 **B8F2** MUST 复用） |
| **挂起** | 走 **B10F1 的唯一转成路径** `InterruptResult.as_result_dict()` ⇒ **再**补齐（`__interrupt__` 键**保留**）⇒ ⇒ **MUST NOT** 另写转成路径 |
| **`config`** | **原样**交给 L2（`resolve_config` 归一 · 未知键宽容忽略）⇒ ⇒ `recursion_limit` 由 L2 的 `resolve_limit` 决定优先级 |
| **`max_concurrency`** | ⚠️ **2026-11-16 clarify 轮 · 用户拍板（Q2 = B）**：旋钮的**读取点下沉到 L2** —— `run_graph` 在**关键字缺省时**回落到 `config.max_concurrency`（**关键字优先**）⇒ ⇒ **兼容扩展**（既有调用方零改动 · 失败顺序逐字不变）⇒ ⇒ **门面层零搬运逻辑** |
| **错误传播** | 节点真异常 / `InvalidUpdateError` / `GraphRecursionError` / `InterruptError` ⇒ **原类型 + 原消息** ⇒ 门面**零捕获** |
| **多会话隔离** | 每次调用**不传** `state=` ⇒ L2 自建调度状态 + **新建**通道实例 ⇒ 连续两次**不累积**、并发两次**不串扰** |
| **可验证出口** | facade 执行测试 + 差分 `D-92…D-102` + `harness/verification/B7F3/acceptance.py` + 五段式人工验证 + 门禁 G21–G30 |

**范围边界**：本 feature 是 **MVP 六项最小交付集的第 3 项**，只交付「**执行**」环节。
⚠️ **固定脚本的工具循环轮**（`messages` 长度 = 3 / `llm_calls == 2` / 工具结果 = 7）依赖
**B8F1（条件边路由）** ⇒ ⇒ **本 feature 物理不可达成** ⇒ ⇒ 登记为 **EV-2**（具名承接 B8F1）⇒ ⇒ ⚠️ **固定脚本的端到端轮**（`target.py` 跑通）同样**物理不可达成** ⇒ ⇒ 登记为 **EV-4**（具名承接 B8F1 / B22F1 / B23F1 / B25F1），
**判据不放宽**（详见 §Constitution Check 的分阶段登记）。

---

## Technical Context

**Language/Version**: Python **>= 3.11**（仓库既有口径；禁用 `TypeAliasType` / `override` /
`ReadOnly` / `TypeIs` / PEP 695 `type` 语句）。本 feature 只使用标准库
`typing` / `collections.abc` / `dataclasses`。

**Primary Dependencies**: **零第三方运行时依赖**（`dependencies = []`）⇒ 不新增依赖；
`langgraph==1.2.11` 只作为开发 / 测试侧差分依赖（上游缺席即 `skip`）。

**Storage**: N/A。无持久化、无文件 I/O、无网络。（`checkpointer` 只**持有**并**透传** ⇒ 落盘归 B14F1。）

**Testing**: `pytest`（既有基线 + 新增 `tests/facade/test_invoke_*.py`（**7 个用户故事 ⇒ 6 个测试文件** · US1 与 US2 共用 `test_invoke_full_state.py` ⇒ 两者**串行**））· 差分探针
`tests/differential/parity_probe.py`（新增 **`InvokeScenario`** 模型 + `D-92…D-102`）·
一键验收 `harness/verification/B7F3/acceptance.py`。
⚠️ **仓库无 ruff / mypy 配置**（`pyproject.toml` 无 `[tool.ruff]` / `[tool.mypy]` · CI 无 lint /
typecheck 步骤）⇒ 验证手段 = **pytest + 门禁脚本**（**不臆造 lint 命令**）。

**Target Platform**: Linux / macOS / Windows（纯同步，无 POSIX-only 依赖）。

**Project Type**: library（图运行时内核 · 门面 L3 → 执行内核 L2）。

**Performance Goals**:
- 一次 `invoke` 的额外开销 = **一次**通道表扫描（键集推导）+ **一次**结果字典构造（O(通道数)）；
- **不**在 `invoke` 内重解析 schema、**不**重建通道表、**不**复制状态值（**按引用**）⇒
  ⇒ 与上游同款（`langgraph/pregel/_io.py:19-20` 的「值按引用」）；
- 本 feature **无**新增运行期性能判据（不引入新的热路径）。

**Constraints**:
- 零 `langsmith` / `langchain*` / `langgraph*` 运行时 import；零环境变量；零出站 / 零文件 I/O；
- **ARCH-1**：L3 只依赖 L1 / L2；**L3 内部禁止横向 import**（G25 同层规则）⇒
  ⇒ **零新增源文件** ⇒ 层注册表**零改动**；
- `freegraph.graph` 仍恰 **7** 个导出符号；`freegraph.runtime.__all__` 仍恰 **23** 个符号
  （⇒ **零新增 L2 导出**）；
- `public-api-snapshot.txt`（G16 逐字节）**MUST NOT** 改（它只渲染门面导出面 · **不含** `invoke`）；
- 不新增 L1 符号 / 契约条目 C1–C27 / 门禁编号 G1–G30；
- `harness/demo/target.py` **只读**（G29 ① 的 diff 断言）；
- 新源码 / 测试带署名头（G5 / G19 / **G30** 全仓扫描）。

**Scale/Scope**: 立项书 §5.2 = **980 行**（实现 460 / 测试 520）· **3 人日**。
实际规模以 `/speckit.tasks` 的任务条数为准；本 feature 不单方面改上位文档数字（**依据 = 仓库既有惯例**（B7F2 同款措辞）＋ **立项口径属发起者批准**；⚠️ 宪法 v1.12.0 **并无**此 MUST ⇒ ⇒ 不假托宪法）。

**改动面**：

| # | 文件 | 动作 | 说明 |
|---|---|---|---|
| 1 | `src/freegraph/_stategraph.py` | **改（主体）** | ① 替换 `CompiledGraph.invoke` 的桩（`:259-261`）② 新增**模块级私有函数** `_full_state(spec, sparse)`（**单一实现点**）③ import 补 `run_graph` **+** `InterruptResult` **+** `SuperStepResult`（`EphemeralValue` 已在）**＋** `Command` / `RunConfig` / `StateDict`（`from .contracts import ...`）④ ⚠️ **MUST NOT** 再导入 `collections.abc.Mapping`（**`_stategraph.py:34` 已导入** ⇒ 重复导入 ⇒ lint 红 · **FND-M3**）⇒ ⇒ **零新增** L2 导出面（`freegraph.runtime.__all__` 仍 23 · 三者**已在** `__all__` 内） |
| 2 | `src/freegraph/contracts/protocols.py` | **改（破 L1 冻结面）** | `invoke` 签名（`:270-272`）：`input: StateDict \| Command \| None` + `config: RunConfig \| Mapping[str, Any] \| None = None`；docstring 表行（`:240` / `:263`）标注「**自 B7F3 起已交付 / 放宽**」　**＋ `:22` 的 import 补 `Mapping`**（⚠️ **2026-11-16 analyse 轮 · 第三轮回修 · 行号订正**：原写「`:26`」⇒ **`:26` 实为 `from .trace import Span`**（内部模块导入）⇒ **改它会误伤 import** ⇒ ⇒ **正确目标是 `:22`**（`from collections.abc import Iterator, Sequence`））（⚠️ **必要伴随改动 · FND-C1 · CRITICAL** ⇒ 该模块**无** `from __future__ import annotations` ⇒ 注解在**类体求值期**解析 ⇒ 缺 `Mapping` ⇒ `NameError` ⇒ **import 期抛出** ⇒ 全仓不可导入） |
| 3 | `specs/b2f1-contracts-protocols/contracts/public-api.md` | **改（回溯修订）** | `:82`（`CompiledGraph` 行）+ `:195`（C11 行）标注「自 B7F3 起放宽」⇒ ⚠️ **MUST NOT** 改 `public-api-snapshot.txt`（G16） |
| 4 | `README.md` | **改（事实性）** | 兼容矩阵 `StateGraph` / `CompiledGraph` 两行：`StateGraph` 行「`invoke` 待 B7F3」⇒「**已交付（B7F3）**」；`CompiledGraph` 行「**行为细节挂起** B7F3 / B8F2 / B15F1 / B16F1」⇒「**行为细节挂起** B8F2 / B15F1 / B16F1」（**只移除 B7F3**）；并补「**返回值是只读快照 · 不要原样回喂**」（SC-020）⇒ ⇒ ⚠️ **2026-11-16 analyse 轮第四轮 · C1 事实订正**：初版写「该两行**已在 G19 的可更新白名单**内」⇒ ⇒ **事实错误** ⇒ ⇒ `StateGraph` 属**门面层 7 符号** ⇒ **不**参与 G19 的逐字节比对 ⇒ ⇒ 而 `CompiledGraph` 属**契约层 21 符号**（`public-api.md` §0 的清单驱动口径 · 不硬编码个数） ⇒ ⇒ **受**该比对保护且**原不在任何白名单** ⇒ ⇒ ⇒ ⇒ ⇒ **必须**由本 feature 新增白名单（见改动面 §4′）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ |
| 4′ | `tests/facade/test_facade_gates.py` | **改（白名单 · 只放宽一处）** | ⚠️ **2026-11-16 analyse 轮第四轮 · C1 回修**：新增 `MATRIX_ROWS_UPDATABLE_BY_B7F3 = frozenset({"CompiledGraph"})` ⇒ ⇒ 比照 **B9F1 / B11F1 / B12F1** 的三处既有白名单写法 ⇒ ⇒ 「等价程度（第三列）MUST NOT **变差**」的护栏一并适用 ⇒ ⇒ ⇒ ⇒ ⇒ **其余契约层行仍逐字未改**（判据**只放宽一处**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **破冻结面 T-4**（登记在 spec 的破冻结面清单 · 并入那唯一一次追认）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ |
| 5 | `tests/facade/test_compiled_graph.py` | **改（拆分不删）** | `:73-86` 的 `"invoke": (({},), "B7F3")` 条目 ⇒ **替换为反面断言**（`invoke` MUST NOT 抛 `NotImplementedError`）；其余 5 个条目**逐字不动** |
| 6 | `tests/facade/test_facade.py` | **改（拆分不删）** | `:195-200`（`test_compile_reports_invoke_b7f3`）与 `:217-234` 的 `("invoke", ({},))` 条目 ⇒ **替换为反面断言**；`assert not hasattr(graph, "invoke")`（构建器侧）**保留** |
| 7 | `tests/runtime/test_acceptance_script.py` | **改（拆分不删）** | `:15-34` 的「`graph_core.py` 退出码 == 2」断言 ⇒ **替换**为「**脚本成功**」= `rc == 0`（⇒ 期望**绿**）；理由：该断言的**根因**（`invoke` 未就绪）已消失 ⇒ **拆分而不删**（保留 subprocess **机制**断言）⇒ ⇒ ⚠️ **判据只可更严**（2026-11-16 analyse 轮 · **S-17**）⇒ ⇒ ⇒ **MUST** 断言 `rc == 0`（**不是**「不再是 2」· **不是** `rc ∉ {2}` ⇒ 那会让真失败 rc==1 仍判绿）⇒ ⇒ ⇒ ⇒ **与 G29 判定 2 / T051 的「rc == 0」同款**；⇒ ⇒ ⚠️ **MUST NOT** 保留「`[环境未就绪]` 文本检查」（该文本**只在未就绪分支**打印 · `graph_core.py:585/596` ⇒ invoke 交付后**永不出现** ⇒ 与「退出码不再是 2」**互斥**） |
| 8 | `harness/demo/graph_core.py` | **改（分级 · 事实性）** | ⚠️ **就绪探针 `_invoke_ready()`（`:555-571`）MUST NOT 改**（它键在 `NotImplementedError` 上 ⇒ 自动切换）⇒ ⇒ **用例组 MUST 按「依赖是否已交付」重新分级** —— **逐条清单**：**保持硬断言**（依赖已交付）= **A3** 图构建与编译（探针**之前**已跑通）· A1 状态模型 / A2 稀疏状态 / A4 完整状态 / A7 并发与错误 / A8 递归上限；**降级为 `soft()` 并标注归属 feature**（依赖未交付）= **A5** 条件边与 fresh 读 ⇒ **B8F1** · **A6 的 C16 段**（`Command(update=)` 经条件边到达）⇒ **B8F1** · **A9 的 context 段**（context 独立通道）⇒ **B8F3** · **A10** 节点别名 ⇒ **B8F3**；⇒ ⇒ **A6 的 C17 段（中断与恢复 · `graph_core.py:357-405`）MUST 保持硬断言**（**挂起半边**：结果含 `__interrupt__` / 元素有 `.value` / `.id` / 载荷原样透出 ⇒ 依赖已交付 ⇒ 必绿）⇒ ⇒ ⇒ ⇒ 其**恢复半边**（`Command(resume=)`）沿用**仓库既有写法** = `soft()`（「恢复需 checkpointer 支持 —— 载体待 **B14F1** 锁定」）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 把该段**整体**降级；⇒ ⇒ ⚠️ **2026-11-16 analyse 轮 · 第三轮回修（FND-B2 · 清单补全）**：**A6 的 C17 段（中断与恢复 · `graph_core.py:357-405`）MUST 保持硬断言**（**挂起半边**：结果含 `__interrupt__` / 元素有 `.value` / `.id` / 载荷原样透出 ⇒ 依赖已交付 ⇒ 必绿）⇒ ⇒ ⇒ ⇒ 其**恢复半边**（`Command(resume=)`）沿用**仓库既有写法** = `soft()`（「恢复需 checkpointer 支持 —— 载体待 **B14F1** 锁定」）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **MUST NOT** 把该段**整体**降级；⇒ ⇒ **降级写法沿用** C17 恢复项「载体待 B14F1 锁定」的既有写法；⇒ ⇒ ⚠️ **2026-11-16 analyse 轮补记**：**A1 / A2 / A4 / A7 / A8 此前从未执行过**（长期被就绪探针挡住 ⇒ `graph_core.py` 以退出码 2 结束）⇒ ⇒ ⇒ ⇒ 它们的首次执行结果 MUST 由 **Phase 0′**（tasks **T011**）**实测登记** ⇒ ⇒ ⇒ ⇒ ⇒ **降级范围 MUST 以实测为据**（**MUST NOT** 顺手降级与本 feature 无关的红点）；⚠️ 另**修一处已红的陈旧断言**：`:509-512` 的 `not hasattr(cfg, "configurable")` 与**已冻结**的 `RunConfig`（**有** `configurable` 字段 · `types.py:215`）矛盾 ⇒ 改为 `cfg.configurable == {}`（**保留**判词原意「context 未被塞进 configurable」） |
| 9 | `harness/demo/agent_loop.py` | **改（分级 · 事实性）** | ⚠️ **2026-11-16 analyse 轮 · 降级范围扩为三个用例组**（原先只列 B1 ⇒ 遗漏 **B2 / B3**）—— **B1** 工具循环（`llm_calls == 2` / `len(messages) == 4` / 工具结果 = 7）· **B2** tool_call 形状（⚠️ 直接取 `msgs[1]` ⇒ **路由未交付时 `msgs` 长度为 1 ⇒ `IndexError`** ⇒ 被 `main()` 兜底捕获成失败）· **B3** 人工审批插入工具循环（`tools` 节点依赖路由才可达）⇒ ⇒ 三者**均依赖 B8F1 的条件边路由** ⇒ ⇒ **全部降级为 `soft()`** + 标注归属（**B8F1**）；⇒ ⇒ **B4**（`Command(update=)` · **静态边** ⇒ 依赖已交付）⇒ ⇒ **C11 完整状态的静态边断言保持硬断言**；⇒ ⇒ ⚠️ 降级范围 MUST 以 **Phase 0′** 的**实测红点**为依据（**MUST NOT** 只凭推理） |
| 10 | `harness/demo/README.md` | **改（事实性）** | 软 / 硬断言清单同步（`invoke` 已接线；新增的软断言逐条标注归属 feature） |
| 11 | `tests/facade/test_invoke_full_state.py` · `test_invoke_errors.py` · `test_invoke_config.py` · `test_invoke_interrupt.py` · `test_invoke_isolation.py` · `test_invoke_purity.py` | **新增**（**7 个用户故事 ⇒ 6 个文件** · US1 与 US2 共用 `test_invoke_full_state.py` ⇒ 两者**串行**；其余故事互不依赖、可并行 ⇒ 避免同文件冲突） | 完整状态 / 键集 / 补齐 / **路由通道排除（带 `path_map` 的条件边图 · **FND-H4**）** / 归约型类型空值 / 错误传播 / 多会话隔离 / `config` 双形态 / 递归上限 / 挂起 / 只读禁令（**契约 §6 的 I-01…I-14**） |
| 12 | `src/freegraph/runtime/superstep.py` | **改（L2 · 兼容扩展）** | ① `run_graph` 的 `max_concurrency` **读取点**：关键字缺省时回落到 `config.max_concurrency`（**关键字优先**）⇒ ⇒ **签名一字不动** · 关键字的校验**仍在 `resolve_config` 之前** ⇒ ⇒ ⇒ ② **config 兜底值的校验点** = `resolve_config` 之后、`_first_graph` 之前（FR-023 的失败顺序）⇒ ⇒ ⇒ ⇒ 回溯修订 B10F1 / B12F1 的契约行（破冻结面 **T-3**）⇒ ⇒ ⇒ ③ ⚠️ **承接编号订正**（2026-11-16 analyse 轮）：`:1947` 的 docstring 写「门面层再归一成 dict（B7F3 · 承接 **D-3**）」⇒ 那是 **B10F1 的 D-3**（与本 feature 的 D-3/D-4 **不同源**）⇒ ⇒ ⇒ ⇒ MUST 一并订正为正确编号（**文档性改动 · 不改行为**） |
| 13 | `specs/b10f1-interrupt-resume/contracts/interrupt-resume-contract.md` + `specs/b12f1-concurrency-errors/spec.md` | **改（回溯修订 · 拆分而不删）** | `run_graph` 的 `max_concurrency` 参数行 + **FR-017 / 裁定 18** 行 ⇒ 标注「自 B7F3 起：关键字优先 · config 兜底」 |
| 14 | `harness/scripts/gates/gate_G22_isolated_env.py` | **改（门禁 · 只接线）** | 新增 **③② 运行期（最小图）** 的步骤 6（建图 → 编译 → 执行 ⇒ 断言 `sys.modules` 无 langchain 家族 + 零出站）⇒ ⇒ **MUST NOT** 新增门禁编号 ⇒ ⇒ 其**反向用例 MUST 同步能失败** |
| 15 | `harness/scripts/gates/gate_G27_zero_egress.py` | **改（声明字符串）** | **观测面声明**从「当前观测面：测试套件执行期（**尚不含内核运行时 —— 运行期待 M2**）」改为「**已含内核运行时（M2 · B7F3 起）**」（B3F1 SC-006 ①：零出站断言**必须**附带观测面声明 ⇒ 声明过期 ⇒ 「零出站已被证明」会被误读） |
| 16 | `tests/facade/_invoke_support.py` | **新增** | 夹具（schema / 节点替身 / `CallCounter` / ✅ **自足桩 checkpointer**（**恢复路径的载体** · **S-22** · **仅供测试** · **MUST NOT** 进 `src/` · ⚠️ **2026-11-16 analyse 轮第五轮 · FND-N2 回修**：**方法集逐字按契约 §4 F-05 的 3 个方法**（`get_tuple` / `put` / `put_writes`）⇒ ⇒ **MUST NOT** 实现 `list` / `delete_thread` / `delete_for_runs` / `copy_thread` / `get_next_version` 这 5 个 **L2 恢复路径不调用**的协议方法 ⇒ ⇒ **MUST NOT** 以「等最小集」这类**开放表述**取舍） / **条件边图构造器**（**带 `path_map`**）· **并发 fan-out 图构造器**（`START→a` / `START→b` ⇒ **同一 super-step** ⇒ **SC-006 的「可观测并发度」判据载体** —— ⚠️ 串行图**恒不重叠** ⇒ 该断言会**恒假**）· ⚠️ **2026-11-16 analyse 轮第五轮 · FND-N5 补齐**：另需 **`build_two_node_graph()`**（`START→a→b→END` · US1 的载体）与 **`build_loop_graph()`**（自环 · `recursion_limit` 的载体）⇒ ⇒ ⇒ ⇒ ⇒ **五个构造器**与 tasks **T002** 的清单**逐项一致**）· **本 feature 用** ⇒ 承载「路由通道排除」断言（契约 **I-03** · **FND-H4**）⇒ ⇒ ⇒ ⚠️ **MUST NOT** 断言路由求值生效（**B8F1**）） |
| 17 | `tests/differential/parity_probe.py` | **改** | 新增 **`InvokeScenario`** 模型（`fg` / `up` 两个 callable + `verdict` + `note`）+ `D-92…D-102` + 接入 `run_all()` |
| 18 | `tests/differential/test_parity_probe.py` | **改** | 新增 `invoke` 场景的 pytest 包装 + **把新模型纳入** `test_the_verdict_vocabulary_is_closed` 的循环（否则新场景**逃逸**该检查） |
| 19 | `harness/verification/B7F3/acceptance.py` | **新增** | 一键验收（A1–A3 + 完整状态 + 失败信号 + 多会话隔离 + `config` 双形态） |
| 20 | `harness/verification/B7F3/manual-verification.md` | **新增** | 五段式 + **EV-1 / EV-2 承接**（**EV-3 已撤销**） + **破冻结面的发起者追认文字** |
| 21 | `harness/verification/README.md` | **改（记录表）** | 「当前已有记录」表补 B7F3 |
| 22 | `harness/features/B8F2_*.md` / `B8F1_*.md` / `B22F1_*.md` / `B23F1_*.md` / `B14F1_*.md` / `B15F1_*.md` / `B16F1_*.md` | **改（只接线）** | 各追加一条 **B7F3 → 目标** 的下游承接（**逐条最小改动**）—— **D-1…D-5 五条**（D-5 = `config` 注解放宽的归属边界 · 归 B8F2 / B15F1 / B16F1）|

**不改动**：`src/freegraph/runtime/**` 中除 `run_graph` 的 `max_concurrency` **读取点**（**兼容扩展** · 破冻结面 **T-3**）之外的一切（L2 冻结面 · B7F1 / B4F1 / B5F1 / B10F1 / B12F1 / B13F1）·
`src/freegraph/contracts/types.py`（`RunConfig` **零改动**）· `src/freegraph/graph.py` 的**导出面** ·
`tests/contracts/**` · `tests/gates/**` · `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md`
（**零新增源文件 ⇒ 零改动**）· `specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt`
（**G16 逐字节**）· `harness/demo/target.py`（只读基准）。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原则 / 门禁 | 判定 | 证据 / 落点 |
|---|---|---|
| **I 零 LangSmith / 零环境变量** | 通过 | 零 `langsmith`；**零环境变量读取**（`recursion_limit` 缺省**硬编码** `10007` · X-5）；无出站 |
| **II 内核纯净** | 通过 | 零 `langchain*` 导入；只依赖标准库 + L1 / L2；**零新增依赖** |
| **III 验收契约优先** | 通过 | `target.py` **零改动**（G29 ①）；`invoke` **同名同签名**（`input, config=None`）⇒ ⚠️ **不**声称固定脚本已端到端跑通（工具循环轮依赖 **B8F1** ⇒ **EV-2**） |
| **IV 可诊断性** | 通过 | 未知 key ⇒ `InvalidUpdateError` 且**点名违规 key**（`.invalid_keys` 结构化）；真异常**原类型 + 原消息**；`NotImplementedError` 消息点名归属 feature（其余 5 个方法不变） |
| **V 人工验收** | 通过 | `harness/verification/B7F3/manual-verification.md`（五段式 + **EV-1 / EV-2** 承接 + **追认文字**） |
| **VI 规格驱动 / 判据级追溯** | 通过 | spec **28 FR / 20 SC**；spec 的追溯表**双向无空缺**（本 plan 已复核）；tasks 每条 SC MUST 挂**可执行判据** |
| **VII 契约 C1–C27** | 通过 | **零新增** L1 符号 / 契约条目；复用 **C4 / C5 / C6 / C11**；L1 协议的两处**注解放宽**走「登记 + 回溯修订 + 追认」（**不**新增条目） |
| **VIII 证据与术语纪律** | 通过 | 上游 `langgraph 1.2.11` + `路径:行号` + 本 plan 的**实测 E-1…E-10**（`research.md` §1）；术语与 spec 一致（「完整状态」/「稀疏视图」/「只读快照」） |
| **IX 许可证 / 商标** | 通过 | 零新增依赖、零新增第三方代码 |
| **X 署名头 / 文档合规** | 通过 | 新测试 / 验收脚本带署名头（G5 / G19 / **G30** 全仓扫描）；README 与 demo README 只做**事实性**更新；**兼容矩阵**的两行改法 = **分两种**：⚠️ **2026-11-16 analyse 轮第五轮 · D1 回修**：初版写「`StateGraph` / `CompiledGraph` 两行**在 G19 的白名单内** ⇒ 可改」⇒ ⇒ **事实错误**（两行**都不在**任何白名单里）⇒ ⇒ ⇒ `StateGraph` 属**门面层 7 符号** ⇒ **不**参与 G19 的逐字节比对（契约层清单 = `public-api.md` §0 的 **21** 个符号 · 不含 `StateGraph`）⇒ ⇒ ⇒ ⇒ ⇒ **可改**；`CompiledGraph` **属契约层** ⇒ ⇒ **受**该比对保护且**原不在任何白名单** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **必须**落在本 feature 新增的 `MATRIX_ROWS_UPDATABLE_BY_B7F3` 白名单内（**只放行这一行** · 破冻结面 **T-4** · 落地任务 = **T053**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **等价程度（第三列）MUST NOT 变差**（`CompiledGraph` 保持 **部分等价**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ |
| **XI 上游优先 / 三态一致** | 通过 | spec P-01…**P-14**；差分 **D-92…D-102**；偏离 **X-1…X-6**（STRICTER 3 / DIFF 3）⇒ **每条偏离有对照表的对应行**（X-1↔P-03 · X-2↔P-04 · X-3↔P-05 · X-4↔P-07 · X-5↔P-09 · **X-6↔P-14**）⇒ ⇒ 三态标注**逐字一致** |
| **XII 最优设计优先** | 通过 | 复用 `run_graph` / `read_channels` / `as_result_dict` / `EphemeralValue` 判定；**零新增** L2 导出 / 零新增源文件 / 零新增能力面方法；「补齐」**单一实现点**（供 B8F2 复用） |
| **ARCH-1 / ARCH-2** | 通过 | L3 → L1 / L2 合法；**零新增源文件** ⇒ **无 L3 → L3**；L1 / L2 不反向 import L3；顶层包仍惰性（G1）；⚠️ **L2 的改动只在 L2 内部**（`run_graph` 读自己的 `config`）⇒ **不产生新的层间依赖** |
| **G1–G30** | 通过 | 零新增门禁编号；既有门禁自动覆盖；**零新增源文件** ⇒ 层注册表零改动；⚠️ **G16 逐字节** ⇒ **MUST NOT** 改 `public-api-snapshot.txt` |
| **冻结面** | ⚠️ **5 类破面（1 次追认）**（⚠️ **2026-11-16 analyse 轮第五轮订正 · FND-C8**：原写「3 处破面」且 plan 导语写「2 处」⇒ ⇒ 现与 spec 的「5 类」统一） | **唯一事实源 = spec.md「Assumptions」的「破面全集 5 类」**：① L1 `CompiledGraph.invoke` 的 **`input`** 注解放宽 ② L1 `CompiledGraph.invoke` 的 **`config`** 注解放宽（① ② 属**同一处契约面**）③ L2 `run_graph` 的 `max_concurrency` **读取点**（**兼容扩展** · 关键字优先 · config 兜底）④ ⚠️ **2026-11-16 analyse 轮第四轮 · C1 回修**：**G19** 的「既有契约层矩阵行逐字未改」判据（新增 `MATRIX_ROWS_UPDATABLE_BY_B7F3` 白名单 · **只放行 `CompiledGraph` 一行** ⇒ ⇒ **破冻结面 T-4**）⑤ **四处**「invoke 未就绪」冻结断言的拆分替换 ⇒ ⇒ ⇒ ⇒ ⇒ **五类同属一次**登记 + 回溯修订 + **发起者追认**（追认次数 **≤ 1**）⇒ ⇒ B7F2 的编译产物持有面**不破**（`vars()` 仍 11 键）⇒ ⇒ ⇒ 立项书 §5.2 的 B7F3 **层标注（L2）**与实际的 **L3** 归属不一致 ⇒ ⇒ **知情说明**（以层注册表 + G25 为准 · 本 feature **不**单方面改上位文档） |

### 质量门禁的分阶段登记（EV-1 / EV-2 / EV-4 · 承接 B13F1 / B10F1 · 只接线）

> 宪法 v1.6.0「质量门禁的分阶段落地与发起者追认」的窄口径适用：判据不放大、不伪装通过。

| # | 被偏离的门禁部分 | 不可达成根因 | 承接方 / 里程碑 | 本 feature 的替代判据 |
|---|---|---|---|---|
| **EV-1** | 门禁 3 的「`target.py` 原样可跑」 | 需 `get_graph` / `draw_mermaid_png`（**B22F1 / B23F1**）+ 条件边路由（**B8F1**）⇒ 脚本在 `invoke` **之前**就会中断 | **B22F1 / B23F1 / B8F1**（M2）· 双跑 **B25F1**（M4） | 本 feature 只判 `invoke` 侧：**A1–A3** + 完整状态 + 失败信号 + 多会话隔离 + `config` 双形态；**G29 ①** 的 diff 断言仍为**空** |
| **EV-2** | 门禁 4 / 5 的「**fake / 真实模型轮**跑通**工具循环**」（立项书 §9.2 的三个断言点：`messages` 长度 = 3 · `llm_calls == 2` · 工具结果 = 7） | 工具循环依赖 **条件边路由** ⇒ **B8F1** 未交付 ⇒ 本 feature **物理不可达成** | **B8F1**（M2）· 双跑 **B25F1**（M4） | `manual-verification.md` 照常**五段式**；**fake 轮**的**静态边**部分**真跑**并记录；**工具循环**部分**具名**承接 B8F1 ⇒ ⇒ ⇒ **判据不放宽**（B10F1 **D-8** 要求的「两轮实测输出」照常登记，工具循环段的缺口**如实写明**）⇒ ⇒ ⇒ ⚠️ **2026-11-16 analyse 轮 · 口径订正**：立项书 §9.2 写「`messages` 长度 = **3**」，而 `harness/demo/agent_loop.py` 实际断言 **4**（入参 + 助手 + 工具结果 + 助手）⇒ ⇒ ⇒ ⇒ ⇒ **本 feature 以脚本为准（4）**；立项书的数字修订属**发起者**职权（**上位文档不单方面改**）⇒ ⇒ ⇒ ⇒ ⇒ |

| **EV-4** | 门禁 4 / 5 的「**固定脚本（`target.py`）端到端轮**」（fake + 真实模型各跑一遍固定脚本并记录**逐字段一致**的最终状态） | 固定脚本的执行链需 **B8F1**（条件边路由 · 工具循环轮）+ **B22F1**（`get_graph`）+ **B23F1**（`draw_mermaid_png`）⇒ ⇒ 三者**均未交付** ⇒ ⇒ ⇒ **物理不可达成**（与 EV-1 同一根因的不同切面：EV-1 判「门禁 3 的原样可跑」，EV-4 判「门禁 4/5 的**固定脚本**双跑」） | **B8F1 / B22F1 / B23F1**（M2）· 双跑 **B25F1**（M4） | ① **「fake 模型轮」** = 猴补 `init_chat_model` + **本 feature 可跑的最小图**（**静态边**部分**真跑**）· ② **「真实模型轮」** = 真实模型 + **最小真实模型图**（1 个节点调用真实模型）⇒ ⇒ ⇒ **两轮的实测输出 MUST 记录**⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **判据不放宽**（SC-018 的两轮 MUST 有**非空**实测输出 · **MUST NOT** 写「符合预期」）⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **判据级覆盖**：SC-018 MUST 挂**可自动核验的文档守卫断言**（宪法原则 VI v1.11.0 + v1.13.0 的「人工门禁类 SC」条款）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **真实轮因环境不具备**（无凭据 / 无外网）而无法完成 ⇒ MUST 另登记为**环境偏离**（**MUST NOT** 用「未验证」替代） |

| ⚠️ **EV-3 · 已撤销**（2026-11-16 analyse 轮） | ~~SC-013 的「屏障」半边~~ | **原登记的根因判断有误**：屏障 = **静态多源边**（`add_edge([a, b], c)` · **B7F4 已交付于 L2** · `superstep.py:671/747/1000-1007`）⇒ ⇒ **不依赖 B8F1 的条件边路由** ⇒ ⇒ ⇒ 实测 `executed == ('a','b','c')` ⇒ ⇒ ⇒ ⇒ ⇒ **物理可达** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 违反宪法 v1.6.0「分阶段落地」的**窄口径**（适用范围两要件之「物理不可达成」不成立）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **撤销该登记** | ——（**不承接**） | **SC-013 恢复整条判定**（含屏障半边 · 比例 == **100%**）⇒ 差分 **D-102** 锁住（判词 **SAME**）⇒ ⇒ ⇒ ⇒ **判据不放宽** ⇒ ⇒ ⇒ ⇒ ⚠️ **条件边路由**（`add_conditional_edges` 的**求值**）仍属 **B8F1**（FR-026 · Out of Scope）—— 那是「**能力尚未交付**」，**不是**「物理不可达成」⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **不适用**本条 |

> ⚠️ **门禁 7 的可达性说明（2026-11-16 analyse 轮 · 第三轮回修 · 事实性澄清**）**（⚠️ **2026-11-16 analyse 轮第五轮 · FND-E1**：本块**原**整块重复两次 ⇒ ⇒ 删去单行版 · 保留多行完整版）**：门禁 7 的「API 兼容矩阵已更新」
> **在本 feature 可达** ⇒ ⇒ ⇒ **README 的「API 兼容矩阵」章节（`:79` 起 · 含「行为等价 / 部分等价 / 不支持」三档）**
> **早已落库** ⇒ ⇒ ⇒ ⇒ 本 feature 由 **T047** 事实性更新其中 `StateGraph` / `CompiledGraph` 两行 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **门禁 7 达成**
> ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **故无需按宪法 v1.6.0 登记为分阶段偏离**（**可达** ⇒ 不是「物理不可达成」）
> ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ 宪法 v1.10.2 的括注（「兼容矩阵按 **B24F1 / M4** 才首次落库」）**已被仓库现状超越**
> ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **该括注已按仓库现状订正**（⚠️ **2026-11-16 analyse 轮第五轮 · FND-G1**：页脚 + changelog + 模板**三处已同步**）（**宪法 v1.15.0 · PATCH** · 2026-11-16 · **经发起者授权** ⇒ ⇒ 生效副本 + `constitution-changelog.md` + 模板 `init_constitution.md` **三处已同步** ⇒ ⇒ ⇒ **MUST NOT** 再以「按 B24F1 / M4 才首次落库」为由把门禁 7 登记为分阶段偏离）。

**追认要求**：EV-1 / EV-2 / EV-4 与**破冻结面 5 类**（**唯一事实源 = spec.md「Assumptions」的「破面全集 5 类」**）的追认合并为**一次**发起者追认，文字落
`harness/verification/B7F3/manual-verification.md`；**未追认前 MUST NOT 合入**。
红线（依赖 / 许可证 / 商标 / 零出站 / 零环境变量）**不适用**本条，照常执行。

---

## Project Structure

### Documentation (this feature)

```text
specs/b7f3-invoke-full-state/
├── plan.md                     # 本文件
├── research.md                 # Phase 0（上游实测 E-1…E-10 + 设计决策 DD-1…DD-12 + spec 回修 S-1…S-45）
├── data-model.md               # Phase 1（实体 / 键集推导链 / 归一算法 / 失败信号 / 生命周期）
├── quickstart.md               # Phase 1（可运行的五段验证指南）
├── contracts/
│   ├── invoke-contract.md      # 执行契约（入口 / 执行语义 / 返回值 / 失败信号 / 跨 feature 接口 / 自检 I-01…I-14）
│   └── upstream-parity.md      # 上游对照底稿（P-01…P-14 + D-92…D-102 + X-1…X-6）
├── spec.md                     # 需求与判据的唯一权威（含 2026-11-16 clarify 轮）
├── checklists/
│   └── requirements.md         # 规格质量清单（38/38）
└── tasks.md                    # Phase 2（/speckit.tasks 产出）
```

### Source Code (repository root)

```text
src/freegraph/
├── _stategraph.py              # 本 feature 主战场（L3 · 桩原地替换 + _full_state 单一实现点）
├── graph.py                    # 门面（零改动 · 导出面 7 符号不变）
├── contracts/                  # L1（唯一破面 = protocols.py 的 invoke 两处注解）
│   ├── protocols.py            # 改：invoke 签名 + docstring 表行
│   ├── types.py                # 零改动（RunConfig 9 字段）
│   └── errors.py               # 零改动（InvalidUpdateError / GraphRecursionError / GraphInterrupt）
└── runtime/                    # L2（**仅** `run_graph` 的 `max_concurrency` 读取点 · 兼容扩展 · 破冻结面 T-3）
    ├── superstep.py            # run_graph / SuperStepResult / InterruptResult / _sparse_state
    ├── read.py                 # read_channels（键保序 · 稀疏）
    ├── channel.py              # Channel / LastValue / BinaryOperatorAggregate / EphemeralValue
    ├── _recursion.py           # resolve_config / resolve_limit / validate_limit
    └── _interrupt.py           # interrupt() / prepare_task / bind_run

tests/
├── facade/
│   ├── test_invoke_full_state.py  # 新增：US1 / US2（键集 / 补齐 / 合并 / 覆盖）
│   ├── test_invoke_errors.py      # 新增：US3（未知 key / 原异常 / 不包装）
│   ├── test_invoke_config.py      # 新增：US4（config 双形态 / 递归上限 / 并发度）
│   ├── test_invoke_interrupt.py   # 新增：US5（挂起 / 恢复 / 键集）
│   ├── test_invoke_isolation.py   # 新增：US6（连续 / 并发隔离）
│   ├── test_invoke_purity.py      # 新增：US7（零 env / 零出站 / 零依赖）
│   ├── _invoke_support.py         # 新增：夹具
│   ├── test_compiled_graph.py     # 改：invoke 的未就绪断言 ⇒ 反面断言
│   ├── test_facade.py             # 改：两处 invoke 桩断言 ⇒ 反面断言
│   └── _gatesupport.py            # 零改动（SIGNED_SOURCE_FILES **不扩** · 新文件由 G30 覆盖）
├── runtime/
│   └── test_acceptance_script.py # 改：rc==2 的断言 ⇒ 「脚本成功 = rc == 0」
├── differential/
│   ├── parity_probe.py         # 改：InvokeScenario + D-92…D-102 + run_all() 接入
│   └── test_parity_probe.py    # 改：新模型纳入判词词汇封闭检查
└── gates/                      # 零改动

harness/
├── demo/
│   ├── graph_core.py           # 改：用例组按「依赖是否已交付」重新分级 + 修陈旧断言
│   ├── agent_loop.py           # 改：工具循环断言降级 + 标注归属
│   ├── README.md               # 改：软/硬断言清单事实性同步
│   └── target.py               # 只读（零改动 · G29 ①）
└── verification/B7F3/
    ├── acceptance.py           # 新增：一键验收
    └── manual-verification.md  # 新增：五段式 + EV-1/EV-2 + 追认文字
```

**Structure Decision**：沿用仓库既有的单包分层，**零新增源文件** —— 实现体落在
`src/freegraph/_stategraph.py`（L3）里，与 B7F2 的 `CompiledGraph` **同模块**。
理由：层注册表把该文件登记为**文件级 L3 条目**，G25 对 **L2–L5 的同层横向 import 一律判违规**
⇒ 新建 `src/freegraph/_invoke.py` 会构成 **L3 → L3** 违规（或迫使改**冻结**的层注册表）
⇒ ⇒ **单文件**是零层注册表改动、零门禁扫描面缺口的形态（与 B7F2 **DD-02** 同款论证）。
「补齐」逻辑写成**模块级私有函数**（而非 `CompiledGraph` 的第 4 个私有字段 / 第 7 个方法）⇒
⇒ 编译产物的持有面**仍是 3 私有 + 8 公开**（`vars()` 恰 11 键 · B7F2 冻结面）。

---

## Implementation Strategy

> 顺序原则：先做**L1 协议与骨架**（无行为），再实现**执行与归一**（主体），然后**测试 / 差分 /
> 验收 / 文档**，最后**分级与接线**。每个阶段结束跑 `pytest -q`，MUST NOT 让基线变红。
> ⚠️ **阶段 0 MUST 先记录绿基线**（宪法 v1.12.0「冻结断言清单 MUST 实测化」）。

### Phase 0 · 基线与冻结面登记（**实测化**）

> ⚠️ **阶段划分（2026-11-16 analyse 轮 · **M4 / S-18**）**：本块**原**同时含「前置项」（0.1–0.3）与
> 「后置项」（0.4 · 需 `invoke` 接通）⇒ ⇒ 与本 plan 的 GATE 声明（「Must pass before Phase 0
> research」）**自相矛盾** ⇒ ⇒ ⇒ ⇒ 现拆为 **Phase 0（前置）** 与 **Phase 0′（后置 · = tasks
> **T011** · 位于 Phase B 之后）** ⇒ ⇒ ⇒ ⇒ ⇒ **tasks.md 的 Phase 1 / Phase 2 已按此拆分**
> （T001 立候选清单 · T011 实测）⇒ ⇒ ⇒ ⇒ ⇒ **判据零放宽**。

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| 0.1 | **跑既有测试套件并记录绿基线**（计数）⇒ 实施前的绿基线 MUST 有记录 | 全仓 | 宪法 v1.12.0「基线义务」 |
| 0.2 | **实测化「冻结断言清单」**（**候选清单**的登记 · 推理阶段）：按本 feature 的落地形态改动源码 ⇒ 跑既有套件 ⇒ **变红**的断言即入清单 ⇒ MUST 逐条带 `文件:行号` + 变红原因 ⇒ **MUST NOT** 只凭推理登记 ⇒ ⇒ ⚠️ **本条只立「候选」**（实测在 **Phase 0′ / tasks T011**）⇒ ⇒ **MUST NOT** 在此写 `manual-verification.md`（该文件由 **T044** 创建） | 全仓 | 已知**候选**：`tests/facade/test_compiled_graph.py:73-86` · `tests/facade/test_facade.py:195-200` · `:217-234` · `tests/runtime/test_acceptance_script.py:15-34` ⇒ **实测确认后**回写 spec 的破冻结面清单（**拆分而不删**） |
| 0.3 | 记录 G30 的**既有**违规数（B7F2 已登记 **8** 条 · tracked 文档问题）⇒ 本 feature **MUST NOT 新增** | — | 门禁 G30 |

### Phase 0′ · 实测化与红点登记（**后置** · = tasks **T011** · 在 Phase B 之后）

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| 0′.1 | ⚠️ **首次执行验收脚本并据实登记红点**（2026-11-16 analyse 轮 · **新增**）：`invoke` 接通后（tasks **T010** 之后 · **MUST NOT** 在接通前做 ⇒ 届时脚本仍以退出码 2 结束）⇒ 跑 `harness/demo/graph_core.py` 与 `harness/demo/agent_loop.py` ⇒ ⇒ 把**首次变为可达**的用例组的**真实**结果逐条记录（红的写**红点** + 原因 + 是否依赖未交付 feature）⇒ ⇒ ⚠️ **产出落「本条自带的 checklist note」**（**不写** `harness/verification/B7F3/manual-verification.md` —— 该文件由 **T044** 创建 ⇒ 提前写 ⇒ 撞 T001 的禁令 + 产生半成品文档）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **T044 MUST 转录本条的实测结果**（与 T001 的绿基线计数一并）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **A1 / A2 / A4 / A7 / A8**（`graph_core`）与 **B1 / B2 / B3**（`agent_loop`）**此前从未真正执行** （长期被就绪探针挡住 ⇒ `graph_core.py` 以退出码 2 结束）⇒ ⇒ ⇒ ⇒ ⇒ **实测登记 ⇒ MUST NOT 只凭推理**（宪法 v1.12.0）⇒ ⇒ ⇒ ⇒ ⇒ 该记录 MUST 作为 **Phase 2′（= tasks T040 / T042）**（降级范围）的**事实依据** ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **与本 feature 无关的红点 MUST 单独登记并据实处置**（**MUST NOT** 顺手降级掩盖） | `harness/demo/graph_core.py` · `harness/demo/agent_loop.py` | SC-015 · SC-018 · G29 · EV-1 / EV-2 / EV-4 |
| 0′.2 | **冻结断言清单的实测化**（宪法 v1.12.0 的「MUST NOT 只凭推理登记」）：按本 feature 的落地形态改动源码 ⇒ 跑既有 pytest 套件 ⇒ ⇒ ⇒ **变红**的断言即入清单 ⇒ ⇒ ⇒ **MUST** 逐条带 `文件:行号` + 变红原因 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ 与 0.2 的**候选清单**合并成一份**实测清单** | 全仓 | 宪法 v1.12.0「冻结断言清单 MUST 实测化」 |

### Phase A · L1 协议放宽 + 桩替换骨架

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| A1 | 放宽 L1 `CompiledGraph.invoke` 的签名（`:270-272`）：`input: StateDict \| Command \| None` + `config: RunConfig \| Mapping[str, Any] \| None = None`；docstring 表行（`:240` / `:263`）标注「**自 B7F3 起**」 | `contracts/protocols.py` | FR-001 · 裁定 1 · SC-019 |
| A2 | 回溯修订 `public-api.md:82` + `:195`（标注放宽）⇒ ⚠️ **MUST NOT** 改 `public-api-snapshot.txt` | `specs/b2f1-contracts-protocols/contracts/public-api.md` | 裁定 1 · R-6 |
| A3 | 把 `CompiledGraph.invoke` 的桩换成**真实签名 + docstring**（docstring MUST 含「**只读快照 · 不要原样回喂**」**及理由**）⇒ 暂抛 `NotImplementedError` 占位（Phase B 再实现）⇒ 保持测试可跑 | `_stategraph.py` | FR-009 · SC-020 |
| A4 | `_stategraph.py` 的 import 补 `run_graph`（`EphemeralValue` 已在）⇒ **零新增** L2 导出面（`freegraph.runtime.__all__` 仍 23） | `_stategraph.py` | FR-002 · SC-016 |

### Phase B · 执行与完整状态（**主体**）

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| B1 | 新增**模块级私有函数** `_full_state(spec, sparse) -> dict`：键集 = `spec.channels` 扣除 `isinstance(channel, EphemeralValue)`（**保序**）；值 = `sparse.get(key, None)`；**保留**已有的 `"__interrupt__"` 键 | `_stategraph.py` | FR-008 / FR-009 / FR-012 · 裁定 2 / 3 / 4 · SC-001 / SC-003 |
| B2 | 实现 `invoke`：① `config` **原样**传给 `run_graph(config=...)`（**MUST NOT** 翻译映射）② 调 `run_graph(self._spec, input, checkpointer=self.checkpointer, config=config)` ⇒ **不传 `state=`** ③ 结果归一：挂起 ⇒ `as_result_dict()` ⇒ 再 `_full_state` | `_stategraph.py` | FR-002 / FR-004 / FR-005 / FR-013 / FR-014 · 裁定 3 / 8 / 10 · SC-002 / SC-008 / SC-009 / SC-010 |
| B2b | **L2 的兼容扩展**：`run_graph` 的 `max_concurrency` **读取点** —— 关键字缺省时回落到 `config.max_concurrency`（**关键字优先**）⇒ ⇒ **签名一字不动** · 关键字的校验**仍在 `resolve_config` 之前**（既有失败顺序**逐字不变**）⇒ ⇒ ⇒ 回溯修订 B10F1 / B12F1 的契约行 | `runtime/superstep.py` + 两份契约 | FR-023 · 裁定 13 · SC-006 · 破冻结面 **T-3** |
| B3 | **零 `try/except`** ⇒ 失败信号原样传播（`InvalidUpdateError` / `GraphRecursionError` / `InterruptError` / 用户异常） | `_stategraph.py` | FR-016…FR-020 · 裁定 9 · SC-004 / SC-005 / SC-007 |
| B4 | `input` 的三种形态（字典 / `Command` / `None`）**原样**交给 L2 ⇒ 门面**不判**形态 | `_stategraph.py` | FR-015 · 裁定 7 · SC-010 |
| B5 | 复核「归约型通道的**类型空值**不被改写成 `None`」⇒ `_full_state` MUST 用 `sparse.get(key, None)`（**不是**「值为 None ⇒ 视为无值」） | `_stategraph.py` | data-model §2.3 · SC-003 |

### Phase 2′ · 验收脚本分级（**= tasks T040 / T041 / T042** · 2026-11-16 第三轮回修 · **FND-A3 · CRITICAL**）

> ⚠️ **为什么前移**：原 **E1 / E2 / E3**（验收脚本分级 + 修陈旧断言）排在 **Phase E** ⇒ ⇒ 但 **T010 接通 `invoke`** 后
> `graph_core.py` 必以 `rc == 1` 结束（既有陈旧断言 `graph_core.py:509-512` + 依赖 **B8F1 / B8F3** 的
> A5 / A6(C16) / A9(context) / A10 组）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **tasks 的 T014④（`rc == 0`）在 Phase 2 自身必红** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒
> ⇒ ⇒ **Phase 2 的「pytest 全绿」门禁不可达成** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **违反宪法 v1.6.0 红线「MUST NOT 写永久红的 CI」**
> ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **处置（发起者 2026-11-16 拍板）**：**E1 / E2 / E3 前移到本阶段（= tasks T040 / T041 / T042）**
> ⇒ ⇒ ⇒ 置于 **Phase 0′（= tasks T011 · 实测红点登记）之后** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **T014 MUST 在本阶段内完成**（脚本先修绿 · 再替换冻结断言）
> ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **任务号与行号（E1 / E2 / E3）均不变 · 仅换阶段** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **Phase E 只留接线 / 文档 / 全量回归**。

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| **E1**（= **T040**） | `graph_core.py` 的**用例组按「依赖是否已交付」重新分级**：A5 / A6(C16 段) / A9(context 段) / A10 ⇒ **降级为 `soft()`** + 标注归属 feature（B8F1 / B8F3）⇒ ⇒ ⚠️ **2026-11-16 第三轮回修（FND-B2 · 清单补全）**：原清单**漏**了 **A6 的 C17 段（中断与恢复 · `graph_core.py:357-405`）** ⇒ ⇒ ⇒ ⇒ **该段 MUST 保持硬断言**（**挂起半边**：结果含 `__interrupt__` / 元素有 `.value` / `.id` / 载荷原样透出 ⇒ 依赖已交付 ⇒ 必绿）⇒ ⇒ ⇒ ⇒ ⇒ 其**恢复半边**（`Command(resume=)`）沿用**仓库既有写法** = `soft()`（「恢复需 checkpointer 支持 —— 载体待 **B14F1** 锁定」）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **MUST NOT** 把该段**整体**降级 ⇒ ⇒ ⇒ ⇒ ⚠️ **降级范围 MUST 以 Phase 0′（= tasks T011）的实测红点为依据**（**MUST NOT** 只凭推理）⇒ ⇒ **就绪探针 MUST NOT 改**（自动切换） | `harness/demo/graph_core.py` | SC-015 · G29 |
| **E2**（= **T041**） | **修陈旧断言**：`graph_core.py:509-512` 的 `not hasattr(cfg, "configurable")` ⇒ 改为 `cfg.configurable == {}`（**保留**判词原意）⇒ ⇒ 理由：L1 的 `RunConfig` **已冻结**为**有** `configurable` 字段（`types.py:215`）⇒ 原断言**已红**（只在 `invoke` 就绪后才可达） | `harness/demo/graph_core.py` | SC-015 · G29 · R-3 |
| **E3**（= **T042**） | `agent_loop.py`：**B1 / B2 / B3** 三个用例组（工具循环 / tool_call 形状 / 人工审批插入工具循环）⇒ **全部降级为 `soft()`** + 标注归属 **B8F1**（三者**均依赖**条件边路由）⇒ ⇒ **B4**（`Command(update=)` · **静态边**）与 **C11 完整状态的静态边**断言**保持硬断言** ⇒ ⇒ ⇒ ⚠️ **降级范围 MUST 以 Phase 0′（= tasks T011）的实测红点为依据** | `harness/demo/agent_loop.py` | G29 · EV-2 |

### Phase C · 测试与差分

> ⚠️ **2026-11-16 analyse 轮第四轮 · H2 回修**：本阶段**只含 C1–C5**（测试 / 差分 / 夹具 / 冻结断言拆分）
> ⇒ ⇒ ⇒ 原 **C6**（人工验证记录的守卫断言）**已移出本阶段** ⇒ ⇒ ⇒ 理由：它的判据依赖
> **Phase D 的 D2**（写 `manual-verification.md`）⇒ ⇒ ⇒ 而 Phase D 在本阶段**之后** ⇒ ⇒ ⇒ ⇒
> ⇒ ⇒ ⇒ ⇒ 留在本阶段 ⇒ **Phase C 末即永久红**（撞宪法 v1.6.0 红线「MUST NOT 写永久红的 CI」）
> ⇒ ⇒ ⇒ ⇒ ⇒ **现落在 tasks T046（Phase 10 · 在 T044 / T045 之后）** ⇒ ⇒ ⇒ ⇒ ⇒ **零红窗口**。

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| C1 | 新增**每故事一个**测试模块（**6** 个 · 见「改动面」§11）：契约 §6 的 **I-01…I-14** 逐条（键集 / 顺序 / 补齐 / 类型空值 / 路由通道排除 / 挂起键 / 未知 key / 原异常 / 递归上限 / 连续并发隔离 / `vars()` 11 键 / 文档禁令） ⇒ ⇒ ⚠️ **2026-11-16 analyse 轮第四轮 · L1 补记**：本行的枚举**只列 12 项** ⇒ ⇒ ⇒ 缺 **I-12**（`invoke` 在合法路径上不抛 `NotImplementedError` ⇒ ⇒ **T014**）· **I-13**（多源汇合屏障 ⇒ ⇒ **T017⑦**）· **I-14**（人工记录守卫 ⇒ ⇒ **T046**） ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **三条不在本阶段**（I-12 在 Phase 2 的 T014 · I-13 在 Phase 3 的 T017⑦ · I-14 在 Phase 10 的 T046） ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **本阶段承载其余 11 项**⇒ ⇒ **每故事的文件互不重叠** ⇒ 故事可独立并行测试 | `tests/facade/` | SC-001…SC-016 · SC-020 |
| C2 | 新增 `_invoke_support.py`（schema / 节点替身 / `CallCounter` / ✅ **自足桩 checkpointer**（**S-22** · 恢复路径载体 · 仅供测试）/ 条件边图构造器 / **并发 fan-out 图构造器**）⇒ **带署名头**（G30） | `tests/facade/` | G5 / G19 / G30 |
| C3 | **拆分而不删**：`test_compiled_graph.py:73-86` 的 `invoke` 条目 ⇒ 反面断言；`test_facade.py:195-200` 与 `:217-234` ⇒ 反面断言；`test_acceptance_script.py:15-34` ⇒ **「脚本成功」= `rc == 0`**（⚠️ **2026-11-16 analyse 轮 · 第三轮回修（FND-A2）**：原写「不再是 2」⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **S-17 已明令废弃**（真失败 rc==1 仍判绿 ⇒ 门禁失效）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **已订正** · 判据只可更严） | `tests/` | SC-015 · spec 破冻结面清单 |
| C4 | 扩展 `parity_probe.py`：新增 **`InvokeScenario`**（`fg` / `up` / `verdict` / `note`）⇒ 落 **D-92…D-102** ⇒ 接入 `run_all()`；**STRICTER 的三条 MUST 带 `note`** | `tests/differential/` | SC-017 |
| C5 | `test_parity_probe.py`：新增 `invoke` 场景的 pytest 包装 + **把新模型纳入** `test_the_verdict_vocabulary_is_closed` 的循环 | `tests/differential/` | SC-017 |
| **C1b**（= **T053** · **FND-A5**） | **G19 的兼容矩阵行白名单**（**破冻结面 T-4** · **追认的第 ④ 项**）：`tests/facade/test_facade_gates.py` 新增 `MATRIX_ROWS_UPDATABLE_BY_B7F3 = frozenset({"CompiledGraph"})` ⇒ ⇒ **只放行这一行**（其余契约层行仍逐字未改 ⇒ 判据只放宽一处）⇒ ⇒ **比照 B9F1 / B11F1 / B12F1 的三处既有白名单写法** ⇒ ⇒ ⇒ **「等价程度（第三列）MUST NOT 变差」的护栏 MUST 一并接入**（`CompiledGraph` 保持 **部分等价**）⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 改动 G19 判据本身的强度 ⇒ ⇒ ⇒ ⇒ ⇒ **MUST** 在 **T047**（README 矩阵行更新）之前落地 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **未追认前 MUST NOT 合入** | `tests/facade/test_facade_gates.py` | 破冻结面 **T-4** · SC-019 · G19 |
| C6 | ⚠️ **人工验证记录守卫测试**（2026-11-16 analyse 轮 · **新增** · 判据级覆盖）：在 `tests/facade/test_invoke_purity.py` 里断言 `harness/verification/B7F3/manual-verification.md` **存在** 且 含 **fake 模型轮** / **真实模型轮** 两轮的**非空实测输出** 且 含**发起者追认**文字（**五项** —— **唯一事实源 = spec.md「Assumptions」的「破面全集 5 类」**：① L1 `invoke` 的 `input` 注解放宽 ② L1 `invoke` 的 `config` 注解放宽 ③ L2 `run_graph` 的 `max_concurrency` 读取点（兼容扩展）④ **G19**「既有契约层矩阵行逐字未改」判据（新增 `MATRIX_ROWS_UPDATABLE_BY_B7F3` 白名单 · 只放行 `CompiledGraph` 一行）⑤ **四处**「invoke 未就绪」冻结断言的拆分替换）⇒ ⇒ ⇒ ⇒ ⚠️ **MUST** 在 **Phase D 的 manual-verification 写就之后**才转绿（⇒ ⇒ **MUST NOT** 造成「永久红的 CI」）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 「写记录」类任务**不**构成判定覆盖（宪法原则 VI v1.11.0 + v1.13.0 的「人工门禁类 SC」条款） ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **阶段归属（2026-11-16 analyse 轮第四轮 · H2 回修）**：本条**原**挂在 **Phase C** ⇒ ⇒ ⇒ 但 Phase C 在 Phase D **之前** ⇒ ⇒ ⇒ 而本条的判据依赖 **Phase D 的 D2**（写 `manual-verification.md`） ⇒ ⇒ ⇒ ⇒ ⇒ **plan 的阶段顺序与本条自身自相矛盾** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **已回修** ⇒ **本条 = tasks T046**（落在 **Phase 10** · 排在 **T044 / T045** 之后） ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **Phase C 只保留 C1–C5**（测试 / 差分 / 夹具 / 冻结断言拆分） | `tests/facade/test_invoke_purity.py` | SC-018 · SC-019 · 契约 §6 的 **I-14** |

### Phase D · 验收脚本 / 人工验证 / 文档

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| D1 | 新增 `harness/verification/B7F3/acceptance.py`（A1–A3 + 完整状态 + 失败信号 + 隔离 + `config` 双形态）⇒ 退出码 0 / 1 / 2 | `harness/verification/B7F3/` | SC-001…SC-010 |
| D2 | 新增 `manual-verification.md`（**五段式** + **EV-1 / EV-2** + **破冻结面的发起者追认文字** + 两轮的实测输出） | `harness/verification/B7F3/` | SC-018 / SC-019 · 原则 V |
| D3 | `README.md`：兼容矩阵两行事实性更新 + 「只读快照 · 不要原样回喂」 | `README.md` | SC-020 · G19 |
| D4 | `harness/verification/README.md` 记录表补 B7F3 | `harness/verification/README.md` | 原则 V |
| D5 | 下游提示词初稿**只接线**：**B8F2**（D-1）/ **B8F1**（D-2）/ **B22F1 + B23F1**（D-3）/ **B14F1**（D-4）/ **B8F2 + B15F1 + B16F1**（D-5）各追加一条 | `harness/features/` | D-1…D-5 |
| D6 | **G22 的 ③② 运行期（最小图）断言**（**只接线 · 不新增门禁编号**）：在 `gate_G22_isolated_env.py` 新增步骤 6（验收环境里 **建图 → compile → invoke** ⇒ 断言 `sys.modules` 无 langchain 家族 + 框架出站 == 0）⇒ ⇒ 其**反向用例 MUST 同步能失败** | `harness/scripts/gates/gate_G22_isolated_env.py` | FR-027 · SC-014 · **EV-1** |
| D7 | **G27 的观测面声明**：把「当前观测面：测试套件执行期（**尚不含内核运行时 —— 运行期待 M2**）」改为「**已含内核运行时（M2 · B7F3 起）**」⇒ ⇒ B3F1 SC-006 ①（零出站断言**必须**附带观测面声明 ⇒ 声明过期 ⇒ 「零出站已被证明」会被误读） | `harness/scripts/gates/gate_G27_zero_egress.py` | SC-011 · 原则 I |

### Phase E · 接线 + 文档 + 全量回归

> ⚠️ **2026-11-16 analyse 轮 · 第三轮回修（FND-A3）**：**E1 / E2 / E3（验收脚本分级 + 修陈旧断言）已前移至 Phase 2′** ⇒ ⇒ ⇒ ⇒ **理由**：`invoke` 接通后 `graph_core.py` 必以 `rc == 1` 结束 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ 若脚本修复留在本阶段 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **Phase 2 → Phase E 之间存在红窗**（撞宪法 v1.6.0 红线「MUST NOT 写永久红的 CI」）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **行号不变 · 仅换阶段**。

| # | 动作 | 文件 | 判据 |
|---|---|---|---|
| E4 | `harness/demo/README.md` 的软 / 硬断言清单事实性同步 | `harness/demo/README.md` | 原则 X |
| E5 | 全量回归 + 门禁（G1–G30；重点：G14 / G16 / G19 / G25 / G26 / **G22** / G27 / G28 / **G29** / G30）⇒ MUST 在 C1–E4 与 D6–D7 之后执行 ⇒ ⇒ ⚠️ **G28（断网等价性）** 须在**已断网**的环境内跑（`unshare --net --map-root-user …`）⇒ ⇒ **本地默认不跑**（CI 档执行）⇒ ⇒ ⇒ **本 feature 的新增测试 MUST NOT** 依赖网络 ⇒ ⇒ ⇒ ⚠️ **`visualization.py` 仍为 `ENV_NOT_READY`**（B22F1 / B23F1 / B8F2）⇒ ⇒ ⇒ **三个**验收脚本里只有 `graph_core` / `agent_loop` MUST 全绿 | 全仓 | SC-011 / SC-012 / SC-013 / SC-014 / SC-015 |
| E6 | 复核 spec / plan / research / data-model / contracts 的编号逐项一致（裁定 1–16 · P-01…P-14 · D-92…D-102（**11 条**）· X-1…X-6 · I-01…I-14 · **ES-01…ES-11** · EV-1 / EV-2 / EV-4 · **S-1…S-45**（⚠️ **2026-11-16 analyse 轮第五轮订正**：原写 `S-1…S-26`，已过期 ⇒ ⇒ ⇒ **第五轮再订正**：追加 **S-38…S-45**））⇒ 如发现漂移只做**事实性**修正 | 文档 | FR / SC 一致性 |

> **与 `tasks.md` 的阶段映射**：本 plan 的 Phase 0→绿基线与变红清单 · A→L1 协议与骨架 ·
> B→执行与归一（主体）· **2′→验收脚本分级（= tasks T040 / T041 / T042）** · C→测试与差分（**只含 C1–C5** + **C1b = tasks T053** · G19 白名单）· D→验收脚本 / 人工验证 / 文档 · E→接线 / 文档 / 全量回归 ⇒ ⇒ ⚠️ **2026-11-16 analyse 轮第四轮 · H2 回修**：原映射把 **C6**（人工记录守卫）算在 Phase C ⇒ ⇒ ⇒ ⇒ ⇒ 它的判据依赖 **Phase D 的 D2** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **已改**：**C6 = tasks T046**（Phase 10）。
> `tasks.md` 的 Phase 1–9 是 speckit 的标准分组（按用户故事），**以 `tasks.md` 的执行顺序为准**；
> 本 plan 的 A–E 只描述**技术分层**。

---

## Design Decisions（摘要 · 详见 research.md §4）

| # | 决策 | 选定 |
|---|---|---|
| **DD-1** | `invoke` 的实现落点 | `src/freegraph/_stategraph.py`（**零新增源文件** · L3 单文件） |
| **DD-2** | 「完整状态」的归一函数 | 模块级私有 `_full_state(spec, sparse)`（**单一实现点** · 供 B8F2 复用） |
| **DD-3** | 驱动路径 | `run_graph(self._spec, input, checkpointer=..., config=...)` ⇒ **不传 `state=`** ⇒ ⇒ ⚠️ **门面 MUST NOT 传 `max_concurrency` 关键字**（旋钮的读取点在 L2 · **DD-4** ⇒ 关键字缺省时由 L2 回落到 `config.max_concurrency`）⇒ ⇒ ⇒ ⇒ ⇒（2026-11-16 analyse 轮订正：初版此处仍写门面传该关键字 ⇒ 与 clarify 轮的「下沉到 L2」决策**冲突** ⇒ 已订正） |
| **DD-4** | `max_concurrency` 的**读取点** | ⚠️ **2026-11-16 clarify 轮 · 用户拍板（Q2 = B）**：**下沉到 L2** —— `run_graph` 在**关键字缺省时**回落到 `config.max_concurrency`（**关键字优先**）⇒ ⇒ **兼容扩展**（既有调用方零改动 · 失败顺序逐字不变：其校验仍在 `resolve_config` 之前）⇒ ⇒ ⇒ 门面层**零搬运逻辑** ⇒ ⇒ ⇒ 回溯修订 B10F1 / B12F1 的契约行（破冻结面 **T-3**）⇒ ⇒ ⇒ ⚠️ **2026-11-16 analyse 轮补记**：**config 兜底值的校验点 = `resolve_config` 之后、`_first_graph` 之前**（它只能在 resolve 之后才读到）⇒ ⇒ ⇒ ⇒ 失败信号与关键字形态**同款**（`TypeError` / `ValueError` 点名该参数）⇒ ⇒ ⇒ ⇒ **关键字形态的失败先后逐字不变**（`RunConfig.from_dict` **不校验**该字段 ⇒ 今日 `{"max_concurrency": 0}` **完全静默**） |
| **DD-5** | `config` 的两形态 | **原样**交给 L2（`resolve_config` 归一 · 未知键宽容忽略） |
| **DD-6** | 挂起结果的归一**顺序** | ① `as_result_dict()`（唯一转成路径）② **再**补齐（`__interrupt__` 保留） |
| **DD-7** | 错误传播 | 门面**零 `try/except`** ⇒ 原样传播 |
| **DD-8** | `input` 的形态 | **原样**交给 L2 ⇒ 门面**不判**形态 |
| **DD-9** | L1 协议的放宽 | `input` + `config` **两处** · **同属一次**追认 · 与 L2 逐字同款 |
| **DD-10** | 文档 | `invoke` docstring + `README.md` MUST 含「只读快照 / 不得回喂」**及理由** |
| **DD-11** | 差分探针 | 新增 `InvokeScenario` 模型（与 `CompileScenario` 同款）+ `D-92…D-102` + 纳入判词词汇封闭检查 |
| **DD-12** | 就绪探针与门禁风险 | 探针**不动**（自动切换）⇒ ⇒ ⚠️ 两个验收脚本**必须全绿**（G29 判定 2） |

---

## Risks & Mitigations

| # | 风险 | 影响 | 缓解 |
|---|---|---|---|
| **R-1** | **L1 冻结面的破面**：两处注解放宽 | 未走「登记 + 回溯修订 + 追认」⇒ 违反宪法 v1.8.0 / v1.12.0 | **A1 / A2**：两处**同属一次**登记 + 回溯修订 + 追认（追认文字落 `manual-verification.md` §7）⇒ ⇒ ⚠️ **MUST NOT** 改 `public-api-snapshot.txt`（G16）⇒ ⇒ 追认次数 == 1（额度用尽） |
| **R-2** | **绿基线缺失 / 变红清单靠推理** | 永久红 CI（宪法 v1.12.0 明列的失败模式） | **Phase 0**：先跑绿基线并记录计数 ⇒ 再实测化变红清单（逐条带 `文件:行号`）⇒ **MUST NOT** 只凭推理登记 |
| **R-3** | **`graph_core.py` 的陈旧断言**（`not hasattr(cfg, "configurable")`） | `invoke` 就绪后该断言**可达** ⇒ rc=1 ⇒ **G29 判 FAIL** | **E2**（Phase 2′）：改为 `cfg.configurable == {}`（**保留**判词原意）⇒ ⇒ ⚠️ 该断言**在 B7F3 之前不可达** ⇒ 是本 feature **首次暴露**的既有红 |
| **R-4** | **验收脚本在 `invoke` 就绪后暴露「依赖未交付 feature」的失败**（`graph_core`：A5 条件边 ⇒ B8F1 · A9 context / A10 别名 ⇒ B8F3；⚠️ **`agent_loop`：B1 / B2 / B3 全部依赖 B8F1 的路由** ⇒ **B2 会 `IndexError`**（`msgs[1]` · `msgs` 长度为 1）⇒ 被 `main()` 兜底捕获成失败） | rc=1 且失败**非** `NotImplementedError` ⇒ **G29 判 FAIL** ⇒ CI 红 | **E1 / E3**（Phase 2′）：按「依赖是否已交付」**重新分级**（未交付 ⇒ `soft()` + 标注归属 feature · 沿用 C17 恢复项的既有写法）⇒ ⇒ ⚠️ **MUST NOT** 改就绪探针 ⇒ ⇒ **判据不放宽**（软断言只是「不判失败」，缺口**具名**登记）⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **降级范围 MUST 以 Phase 0′ 的实测红点为据**（**MUST NOT** 只凭推理 ⇒ **MUST NOT** 顺手降级与本 feature 无关的红点） |
| **R-5** | **补齐 `None` 造成的回喂污染** | 用户把返回值原样回喂 ⇒ `None` 被写进通道 ⇒ 节点里 `state.get(k, 0) + 1` **崩溃** | 裁定 3 + **DD-10**：返回值是**只读快照** ⇒ 禁令 MUST 写进 docstring + `README.md`（SC-020）⇒ ⇒ 上游因省略而**无此坑**（E-5）⇒ ⇒ 该差异**如实登记**（X-1 的「已知代价」列） |
| **R-6** | **误改 `public-api-snapshot.txt`** | G16 逐字节红 | **A2** / 改动面 §「不改动」：MUST NOT 改（该快照只渲染门面导出面 · **不含** `invoke`）⇒ ⇒ 回溯修订目标是 `public-api.md:82` / `:195` |
| **R-7** | **`max_concurrency` 仍然失效** | `RunConfig.max_concurrency` 静默失效（L2 的 `run_graph` 只认关键字）⇒ ⇒ **Q2-B 的 L2 改动若漏做** ⇒ 用户设了旋钮却毫无效果 | **DD-4 / B2**：L2 的 `run_graph` 读 `config.max_concurrency`（关键字优先）⇒ ⇒ **测试断言 MUST 用「可观测并发度」**（两个并发节点各自记录「同时在飞」的**重叠计数**：`max_concurrency=1` ⇒ 重叠 == **0**（串行基线）· 缺省档 ⇒ 重叠 **≥ 1**）⇒ ⇒ ⇒ ⚠️ **「最终状态逐字相等」无法判定旋钮是否生效**（最终状态与并发度**无关** ⇒ 旋钮被忽略时**照样通过**）⇒ ⇒ ⇒ ⇒ 该判据**只作补充**（SC-006 的第二条子句）⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **2026-11-16 analyse 轮补齐**：「重叠」的测量 **MUST 是确定性的**（`threading.Event` / `Barrier` 互等到齐）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 依赖时间流逝（⇒ ⇒ CI 慢档 / Windows 档会假红 —— 仓库已有一次「时序测量假红」的修复史）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ `max_concurrency=1` 档的「等不到对端」**MUST** 以**超时兜底**（超时**不**判失败 · 串行**正是**期望）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据数值一字不改** |
| **R-8** | **把路由通道漏进返回键集** | 键集 ≠ schema 全集（多出 `branch:to:*`）⇒ SC-001 失败 | **DD-1/B1**：用 `isinstance(channel, EphemeralValue)` 判定（B7F1 冻结口径）⇒ ⇒ **C1** 断言条件边图上 `"branch:to:*" not in out` |
| **R-9** | **把「值为 `None`」误判成「无值」** | 归约型通道的**类型空值**被改写成 `None`（`[]` → `None`）⇒ 与上游分叉且违反 SC-003 | **DD-2 / B5**：用 `sparse.get(key, None)`（**不**判「值是否为 None」）⇒ ⇒ **C1** 断言 `list` 型归约通道的未写初值仍是 `[]` |
| **R-10** | **挂起路径的键集**只含稀疏 key | 挂起时 FR-008 失效（与 FR-014 冲突） | **DD-6**：归一**顺序** = `as_result_dict()` → **再**补齐（`__interrupt__` 保留）⇒ ⇒ spec FR-014 已回修（S-2）⇒ ⇒ **C1** 断言挂起结果的键集 == schema 全集 **+** `__interrupt__` |
| **R-11** | **另写一条「异常 → `__interrupt__` 键」的转成路径** | 违反 B10F1 的「转成路径只此一条」 | **DD-6 / B2**：只调 `as_result_dict()` ⇒ ⇒ 静态挂起**同款** ⇒ ⇒ 契约 §6 的 **I-04 / I-05** 断言 |
| **R-12** | **门面层另写一份「补齐」逻辑** | B8F2 必然重写一份（违反下游承接 D-1） | **DD-2**：**一个**模块级私有函数 ⇒ ⇒ **C1** 的代码结构审查 + 下游承接 **D-1** 的接线 |
| **R-13** | **L2 的改动**（`run_graph` 读 `config.max_concurrency`） | 属 B10F1 / B12F1 的冻结面 ⇒ 需**回溯修订** + 追认（额度 ≤ 1 次 ⇒ 与 L1 的两处放宽**同属一次**）⇒ ⇒ 若改成「扩 L2 导出面」则额度会突破 | **DD-4**：**兼容扩展**（**签名一字不动** · 关键字的失败顺序**逐字不变** · 既有调用方零改动）⇒ ⇒ 回溯修订 B10F1 / B12F1 的**契约行**（**拆分而不删**）⇒ ⇒ **`freegraph.runtime.__all__` 仍 23**（**不新增 L2 导出**）⇒ ⇒ ⇒ **MUST NOT** 为此新增 L2 符号 |
| **R-14** | **EV-2（工具循环轮）被写成「未验证」** | 违反 B10F1 **D-8**（「本 feature 未跑固定脚本」**不得**写成「本 feature 未验证」）⇒ ⇒ 且判据被悄悄放宽 | **D2**：`manual-verification.md` 照常五段式 ⇒ fake 轮的**静态边**部分**真跑**并记录 ⇒ 工具循环段**具名**承接 **B8F1** ⇒ ⇒ ⇒ **EV-2** 如实登记（**不放宽**） |
| **R-15** | **差分探针把「上游省略 / freegraph 保留」误判** | 判词与实际不符 ⇒ 差分假绿 | **DD-11**：新增 `InvokeScenario` 的 `verdict` **只允许** `SAME` / `STRICTER` / `DIFF`（`test_the_verdict_vocabulary_is_closed` 强制）⇒ ⇒ **STRICTER 的三条 MUST 带 `note`**（**D-94 / D-95 / D-96**） |
| **R-16** | **G30 新增署名头违规** | 全仓扫描红 | **C2 / D1 / D2**：新增 `.py`（`_invoke_support.py` / `test_invoke_full_state.py` / `acceptance.py`）**必须**带**逐字**署名头 ⇒ ⇒ 既有 **8** 条违规**不归**本 feature |
| **R-17** | ⚠️ **验收脚本的用例组从未真正执行过**（2026-11-16 analyse 轮 · **新增**）：`graph_core` 的 **A1 / A2 / A4 / A7 / A8** 与 `agent_loop` 的 **B1 / B2 / B3** 长期被就绪探针挡住 ⇒ ⇒ 首次执行可能暴露**与降级无关**的红点 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ | **G29 判 FAIL** ⇒ CI 红，且届时**无既定处置口径** | **Phase 0′**：**实测登记**首次执行的全部红点（**MUST NOT** 只凭推理）⇒ ⇒ ⇒ ⇒ ⇒ 与本 feature 相关的红点按本 feature 修；与本 feature 无关的红点**单独登记并据实处置**（**MUST NOT** 顺手降级掩盖）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据不放宽** |

---

## Test & Verification Strategy

| 层 | 内容 | 判据 |
|---|---|---|
| **门面 · 完整状态** | 键集 == schema 全集（**顺序**）· 无值 key = `None` · 归约型**类型空值**保留 · 路由通道**排除** · `messages` == 初始 + 新增 · `llm_calls` == 覆盖值 | SC-001 / SC-002 / SC-003 |
| **门面 · 失败信号** | 未知 key ⇒ `InvalidUpdateError` + 消息含 key 名（**多个**含全部）· 真异常**原类型 + 原消息** · `GraphRecursionError` **不包装** | SC-004 / SC-005 / SC-007 |
| **门面 · 配置** | `RunConfig` / 普通映射**双形态** · `recursion_limit` 生效 · `max_concurrency=1` ⇒ **可观测并发度**的重叠计数 == **0**（串行基线）· 缺省档 ⇒ 重叠 **≥ 1**（⇒ **旋钮生效**的可判定证据）· `max_concurrency=1` 与并发档**结果逐字相等**（补充判据） · 映射的未知键**宽容忽略** ⇒ ⇒ ⚠️ **重叠的测量 MUST 确定性**（`Event` / `Barrier` 互等到齐 ⇒ **MUST NOT** 依赖时间流逝；串行档以**超时兜底**且超时**不**判失败） | SC-006 / SC-007 |
| **门面 · 屏障** | **多源汇合边**（`add_edge([a, b], c)`）⇒ 屏障目标 `c` 的写入出现在**所有**源之后（执行序 `a`/`b` → `c`）⇒ 完整状态含 `c` 的写入 | SC-013 · H-8 · FR-003 |
| **门面 · 隔离** | 连续两次**不累积** · 并发两次**不串扰** · 编译产物的通道**零残留** | SC-008 / SC-009 |
| **门面 · 挂起** | `__interrupt__` 存在 · 元素有 `.value` / `.id` · 键集 == schema 全集 **+** 该键 · 未挂起时**不**含该键 | SC-010 |
| **门面 · 纯净** | 零 env · 零出站 · `sys.modules` 无 `langchain*` / `langgraph*` / `langsmith` | SC-011 / SC-012 |
| **结构冻结** | `vars(compiled)` 恰 **11** 键 · 门面导出面恰 **7** 符号 · `runtime.__all__` 恰 **23** 符号 · `public-api-snapshot.txt` **逐字节**不变 | SC-016 |
| **文档** | 「只读快照 / 不得回喂」**及理由**出现在 docstring + README | SC-020 |
| **最小图闭环** | 建图 → compile → execute 的**运行期**断言被点亮（G22 场景②） | SC-014 |
| **差分** | `D-92…D-102`（上游缺席 `skip`）· 判词与对照表一致 | SC-017 |
| **验收脚本** | ⚠️ **G29 的验收脚本集是**三**个**（`gate_G29_contract_carrier.py:60` 的 `ACCEPTANCE_SCRIPTS = ("graph_core", "agent_loop", "visualization")`）⇒ ⇒ 本 feature 后：`graph_core.py` / `agent_loop.py` **全绿**（退出码 **0**）· `visualization.py` **仍为 `ENV_NOT_READY`**（其用例组 = `get_graph` / `draw_mermaid` / `draw_mermaid_png` / `stream` ⇒ 归 **B22F1 / B23F1 / B8F2** · **本 feature MUST NOT** 越界实现 ⇒ ⇒ ⇒ **G29 判为 `ENV_NOT_READY` ⇒ 不判 FAIL** ⇒ ⇒ ⇒ **MUST NOT** 被读成「三个脚本全绿」）· `acceptance.py`（本 feature 新增）全绿 ⇒ ⇒ ⚠️ **降级范围 MUST 以 Phase 0′ 的实测红点为据**（**MUST NOT** 只凭推理 ⇒ **MUST NOT** 顺手降级与本 feature 无关的红点） | SC-015 · G29 |
| **人工** | 五段式 + **EV-1 / EV-2 / EV-4** + **追认文字** + 两轮实测输出 | SC-018 / SC-019 · 原则 V |
| **人工记录守卫** | `manual-verification.md` **存在** + 含**两轮非空实测输出** + 含**追认文字**（**文档守卫断言** ⇒ 「写记录」**不**构成判定覆盖） | SC-018 · SC-019 · 契约 §6 的 **I-14** |

---

## Downstream Wiring（spec D-1…D-4 · 只接线）

| # | 承接方 | 动作 | 落点 | 接线状态 |
|---|---|---|---|---|
| **D-1** | **B8F2** | `stream()` 的 `values` 档 MUST 与本 feature 的 `invoke` **逐字同款**（**复用** `_full_state` ⇒ **MUST NOT** 另写一份「补齐」）· `updates` 档（增量）不受本口径约束 | `harness/features/B8F2_*.md` 的 `## 下游承接` 块 | 待接线（tasks 落一条最小改动） |
| **D-2** | **B8F1** | 条件边路由求值 MUST 在本 feature 的**同一条**执行路径上生效（**MUST NOT** 另开路径）⇒ 路由产生的写入进入**同一份**完整状态 ⇒ 路由通道**不进**返回键集 ⇒ ⇒ ⚠️ **消歧（2026-11-16 analyse 轮）**：**「多源汇合（屏障）」≠「条件边路由」** —— 前者是**静态多源边**（B7F4 已交付于 L2 · **本 feature 判定** · SC-013 整条）⇒ ⇒ ⇒ 后者才是 **B8F1** 的动作（**能力尚未交付**）⇒ ⇒ ⇒ ⇒ 两者**不可**混为一条 | `harness/features/B8F1_*.md` | 待接线 |
| **D-3** | **B22F1 / B23F1** | `get_graph` / `draw_mermaid_png` MUST **先于** `invoke` 就绪（只读基准脚本的调用顺序）⇒ 本 feature **MUST NOT** 越界实现二者 | `harness/features/B22F1_*.md` / `B23F1_*.md` | 待接线 |
| **D-4** | **B14F1** | `checkpointer` 的**落盘**与 saver 实现归 B14F1 ⇒ 本 feature **只透传** ⇒ 恢复语义（MUST 挂 checkpointer）在 B14F1 落地前由 **L2 的既有失败信号**承担 | `harness/features/B14F1_*.md` | 待接线 |
| **D-5** | **B8F2 / B15F1 / B16F1** | **L1 其余 4 个带 `config` 参数的方法**（`stream` / `get_state` / `get_state_history` / `update_state`）的 **`config` 注解放宽** ⇒ 本 feature 只放宽 `invoke`（追认额度已用尽）⇒ ⇒ 这 4 处**各自**走「登记 + 回溯修订 + 发起者追认」⇒ ⇒ ⇒ **下游 MUST 复用本 feature 已定的载体边界**（`RunConfig` = 会话面 + `max_concurrency`；普通映射 = 运行期参数 ⇒ 原样交给 L2 ⇒ MUST NOT 翻译成 `RunConfig`） | `harness/features/B8F2_*.md` · `B15F1_*.md` · `B16F1_*.md` | 待接线 |

> spec 已冻结上述接口；目标提示词初稿**尚未**逐字写入 B7F3 → 目标的承接条目 ⇒ 本 feature 的
> tasks MUST 包含**五条**「只接线 · 逐条最小改动」任务；**MUST NOT** 越界实现下游行为。

---

## spec 回修登记（plan 阶段 · S-1…S-11 · analyse 轮复审追加 **S-12…S-18** · analyse 轮第三轮追加 **S-19…S-26** · analyse 轮第四轮追加 **S-27…S-37** · analyse 轮第五轮追加 **S-38…S-45**）

> **纪律**：plan 阶段的上游 / 内核自查若发现 spec 的口径不完整或自相矛盾，MUST 如实登记并
> **最小回修**（MUST NOT 放宽判据）。**已全部回修**（见 `research.md` §5）。
> ⚠️ **S-7…S-11 = 2026-11-16 analyse 轮的复审回修**（⇒ **S 表为连续编号** · 判据零放宽）。
> ⚠️ **S-12…S-18 = 2026-11-16 analyse 轮（第二轮 · 跨工件对齐审查）的复审回修**
> ⇒ ⇒ **C1（三态标注令牌 · 宪法原则 XI 末条）· S-13（判词分布挂错对象）· S-14（「无值 key」限定分裂）
> · S-15（契约编号域与实测台账撞名）· S-16（提示词 SC 编号错位）· S-17（冻结断言替换判据被弱化）
> · S-18（Phase 0 阶段划分 + 红点落点的永久红窗口）** ⇒ ⇒ ⇒ ⇒ **全部为「事实性 / 一致性」修订
> ⇒ ⇒ ⇒ ⇒ ⇒ **判据零放宽**（S-17 为**收紧**）。

| # | 问题 | 处置（**已回修 spec**） |
|---|---|---|
| **S-1** | 破冻结面清单把 `public-api-snapshot.txt` 列为 `invoke` 签名行的回溯修订目标 ⇒ 该快照**不含** `invoke` 行 ⇒ 改它 ⇒ **G16 红** | 清单的 ③ 改为 `public-api.md:82` + `:195`；并新增一行「⚠️ `public-api-snapshot.txt` **MUST NOT** 改」 |
| **S-2** | FR-014（`as_result_dict()` 逐字返回）与 FR-008（键集 == schema 全集）**冲突** | FR-014 改为「走 `as_result_dict()` 这唯一转成路径 ⇒ **再**按 FR-008 补齐（保留该键）」⇒ 裁定 8 同步加注 |
| **S-3** | Assumptions 的「L1 冻结面」条只写「唯一破面 = `input`」 | 改为「**两处**（`input` + `config`）· **同属一次**登记 / 回溯修订 / 追认」 |
| **S-4** | 承接条款 H-4 ① 只提 `input` 的放宽 | 补上 `config` 注解的放宽（逐字按裁定 1 + clarify 轮） |
| **S-5** | 上游 `invoke(None)` 在新会话 ⇒ `EmptyInputError`（**实测 E-7**）⇒ freegraph 更宽松 ⇒ 上游对照表**未覆盖** | spec 新增 **P-14** + 偏离 **X-6**（DIFF · 只透传 · 源自 B10F1 FR-013）⇒ **如实登记、不掩盖** |
| **S-6** | `harness/demo/graph_core.py:509-512` 的 `not hasattr(cfg, "configurable")` 与**已冻结**的 `RunConfig`（**有** `configurable`）矛盾 ⇒ 该断言**已红**（只在 `invoke` 就绪后可达） | 登记为 **R-3** + 改动面 §8 / §「E2」⇒ **MUST** 修（`cfg.configurable == {}`）⇒ ⇒ 属**验收脚本**（可改），**不**触及只读基准 |
| **S-7** | spec 的「破冻结面的回溯修订清单」只列了 **2 处**「invoke 未就绪」冻结断言（`test_compiled_graph.py:73-86` · `test_acceptance_script.py:15-34`）⇒ **漏** `tests/facade/test_facade.py:195-200` 与 `:217-234`（plan 改动面 §6 / tasks **T001 / T014** 均按 **4 处**计 ⇒ ⇒ ⇒ ⇒ ⇒ **追认范围**亦含糊（「第 4 处」） | 实测（`grep` + 读文件）确认两处断言存在 ⇒ ⇒ **回填** spec 清单为 **4 处**（第 4 / 5 / 6 / 7 行）⇒ ⇒ ⇒ 追认文字改为「**四处**冻结断言的拆分替换」⇒ ⇒ ⇒ ⇒ ⇒ **判据不放宽**（拆而不删） |
| **S-8** | **SC-018 无判定任务**（只挂「写记录」类任务）⇒ 违反**宪法原则 VI v1.11.0**；且「两轮」若指固定脚本 ⇒ **物理不可达成**（EV-1 同一根因） ⇒ ⇒ **证据**：宪法原则 VI v1.11.0「SC MUST 挂能判定它的任务」+ 宪法 v1.6.0 的分阶段窄口径 | ① spec 的 SC-018 补「**两轮的定义**」+「**判据级覆盖**」条款（文档守卫断言）⇒ ⇒ ⇒ ② **登记 EV-4**（固定脚本端到端轮 ⇒ 承接 B8F1 / B22F1 / B23F1 / B25F1）⇒ ⇒ ⇒ ③ 契约新增自检项 **I-14** ⇒ ⇒ ⇒ ⇒ ⇒ **判据不放宽**（两轮仍 MUST 有非空实测输出） |
| **S-9** | **SC-006 的「可观测并发度」判据依赖时序竞争**（缺省档要求「重叠 ≥ 1」）⇒ CI 慢档 / Windows 档可能假红（仓库已有一次「时序测量假红」的修复史） ⇒ ⇒ **证据**：仓库历史：commit `88331ed`「修 Windows + CPython 3.11 档的**时序测量**假红（只修测量 · 不动断言）」 | spec 的 SC-006 补「**测量 MUST 是确定性的**」条款（同步手段 + 超时兜底）⇒ ⇒ ⇒ **判据数值一字不改**（重叠 == 0 / ≥ 1）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ |
| **S-10** | **差分 D-94 未指明「缺的那个 key」的类型** ⇒ 若误用**归约型** key ⇒ 其值是**类型空值**（`[]`）而非 `None`（⇒ 与 FR-009 的消歧口径冲突） ⇒ ⇒ **证据**：FR-009 的消歧（归约型未写 ⇒ 类型空值 · 不改写成 `None`）| D-94 指明用**覆盖型（无归约器）** key（如 `llm_calls`）⇒ ⇒ ⇒ ⇒ ⇒ **判据不放宽** |
| **S-11** | **编号与计数的漂移**：① spec Assumptions 写「差分探针场景（D-92…D-101）」⇒ **漏 D-102**；② tasks 原写「D-92…D-102（**10 条**）」⇒ 实为 **11 条**；③ spec SC-010 有「`.id**`」笔误；④ **实测台账实为 E-1…E-10**（research 已有 E-10 行）而 research / upstream-parity / plan 三处仍写「E-1…E-9」⇒ ⇒ ⇒ ⇒ upstream-parity §3 的 **E-10 是悬空引用** ⇒ ⇒ **证据**：`grep` 全量核对（research / upstream-parity / plan / tasks）+ 逐条读 | ① Assumptions 订正为「D-92…D-102 · **11 条**」；② tasks 订正为 **11 条**；③ SC-010 笔误订正；④ **统一为 E-1…E-10** 并把 E-10 补进 upstream-parity §1 的实测台账（消除悬空引用）⇒ ⇒ ⇒ ⇒ ⇒ **纯事实性订正 · 判据零放宽** |
| **S-12** | ⚠️ **2026-11-16 analyse 轮复审**：spec 偏离登记的「类别」列**原**写「更严（…）」/「更严的失败信号」⇒ ⇒ 与上游对照表的 `STRICTER` **分类词不同** ⇒ ⇒ ⇒ 违反**宪法原则 XI 末条**（三态标注 **MUST 逐字一致**）⇒ ⇒ ⇒ ⇒ （且偏离了仓库既有先例 **B10F1** 的 `STRICTER（…）` / `DIFF（…）` 写法）⇒ ⇒ ⇒ **证据**：`specs/b10f1-interrupt-resume/spec.md:523`（`STRICTER（失败信号更严 · 更结构化）`） | spec 的 **X-1 / X-2 / X-3** 的「类别」列**加 `STRICTER` 令牌**（`STRICTER（更严 · …）` / `STRICTER（更严的失败信号）`）⇒ ⇒ ⇒ 「三态标注一致性」注补写本次回修的说明 + **「无孤行 / 漏行」的方向性澄清**（P-08 / P-12 属非更严的 DIFF ⇒ 原则 XI 末条**不**要求登记）⇒ ⇒ ⇒ ⇒ ⇒ **只改分类词 · 判据零放宽** |
| **S-13** | ⚠️ **2026-11-16 analyse 轮复审**：spec **SC-017** 称「判词分布与 §Upstream Parity 表**逐条一致**（SAME 7 / STRICTER 3 / DIFF 1）」⇒ ⇒ **实测**：对照表（P-01…P-14）= **SAME 6 / STRICTER 3 / DIFF 5**；「7/3/1」是**差分场景组**（D-92…D-102）的分布 ⇒ ⇒ ⇒ **括注挂错了对象** | SC-017 的括注**改挂「差分场景组」**并同时给出对照表的真实分布 ⇒ ⇒ ⇒ plan 的 re-check 行补「判词分布」一行（两对象 · 两套分布）⇒ ⇒ ⇒ ⇒ ⇒ **纯事实性订正 · 判据零放宽** |
| **S-14** | ⚠️ **2026-11-16 analyse 轮复审**：「无值 key 填 `None`」这条规则在 spec / 契约 / data-model 共 **12 处**重述⇒ ⇒ 其中 **6 处带**「仅覆盖型（无归约器）」限定、**6 处未带** ⇒ ⇒ ⇒ 归约型通道未写时值是**类型空值**（`[]` / `0`）⇒ ⇒ ⇒ 未限定处与已限定处**字面冲突** ⇒ ⇒ ⇒ （且 tasks **T052** 的「六处逐字同义」自检按现状**会红**）⇒ ⇒ **证据**：spec 裁定 3 / FR-009 首句 / Edge Cases 首条 / Key Entities · 契约 R-03 · data-model §2.5 **未带限定**；spec FR-009 消歧 / US2 口径注 / SC-003 · 契约 R-06 · data-model §2.3 **已带限定** | ① spec 裁定 3 / FR-009 首句 / Edge Cases 首条 / Key Entities **补上限定**（Edge Cases 拆为「覆盖型 ⇒ `None`」/「归约型 ⇒ 类型空值」两条）② 契约 **R-03** 补限定 ③ data-model **§2.5** 补两行形态 ④ tasks **T052** 的必查项从「6 处」扩到「**12 处**」并列出两侧清单 ⇒ ⇒ ⇒ ⇒ ⇒ **只补限定语 · 不改任何判定内容 · 判据零放宽** |
| **S-15** | ⚠️ **2026-11-16 analyse 轮复审**：契约 §2 的条款编号 `E-01…E-11`（执行语义）与 **实测台账 `E-1…E-10`**（上游实测）**同前缀不同义** ⇒ ⇒ ⇒ 契约表内「实测 E-2 / 实测 E-6」与同表的 **E-02 / E-06** **同表歧义** ⇒ ⇒ ⇒ research §3 的编号域注**漏了**契约这一套 | 契约 §2 的条款编号改为 **`ES-01…ES-11`**（执行语义 · Execute-Semantics）⇒ ⇒ ⇒ 契约 §2 加**编号域注**（与实测 `E-1…E-10` 刻意区别）⇒ ⇒ ⇒ research §3 的编号域注扩为**四者**（`EX-` / `ES-` / `R-01…R-11` / `R-1…R-17`）+ 补「凡『实测 E-n』皆指 §1 台账」⇒ ⇒ ⇒ ⇒ ⇒ **纯编号隔离 · 判据零放宽** |
| **S-16** | ⚠️ **2026-11-16 analyse 轮复审**：**提示词初稿 §5 的 `SC-001…SC-005`** 与本 spec 的 `SC-001…SC-020` **编号同形、含义不同**（初稿 SC-003 = 未知 key ⇒ 实为 spec SC-004；初稿 SC-004 = config 双形态 ⇒ 实为 spec SC-006；初稿 SC-005 = 零出站 ⇒ 实为 spec SC-011/012）⇒ ⇒ ⇒ spec 的「引文差异」表**未登记**这处编号错位 ⇒ ⇒ ⇒ ⇒ 实施者可能按初稿 SC-003 去查 spec SC-003（= `llm_calls` 覆盖语义）⇒ ⇒ **证据**：`harness/features/B7F3_invoke返回完整状态.md:161-165` | spec 的「引文差异」表**新增第 11 条**（编号域隔离 · 提示词的 SC 编号**作废**）⇒ ⇒ ⇒ ⇒ ⇒ **纯事实性订正 · 判据零放宽** |
| **S-17** | ⚠️ **2026-11-16 analyse 轮复审**：第 4 处冻结断言（`tests/runtime/test_acceptance_script.py:15-34`）的替换判据**原**写「退出码**不再是 2**（⇒ ∈ {0,1}）」⇒ ⇒ ⇒ **真失败（rc == 1）仍判绿** ⇒ ⇒ ⇒ ⇒ 而 G29 判定 2 与 T051 均要求验收脚本 **rc == 0** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据被弱化** ⇒ ⇒ ⇒ **证据**：`gate_G29_contract_carrier.py:97-124`（判定 2）+ `harness/demo/graph_core.py:79-89`（`check` / `soft` 的失败行格式） | spec 破冻结面清单第 4 行 + plan 改动面 §7 + tasks **T014** 三处**统一**改为「**脚本成功** = `rc == 0`」⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据只可更严 · MUST NOT 放宽**（与 T040 / T041 / T042 的降级口径一致：降级只降低**断言强度**、脚本 MUST 仍全绿）⇒ ⇒ ⇒ ⇒ ⇒ **纯事实性订正 · 判据零放宽（判据**收紧**）** |
| **S-18** | ⚠️ **2026-11-16 analyse 轮复审**：① plan 的 **Phase 0** 同时含前置项（0.1–0.3）与后置项（0.4 · 需 `invoke` 接通）⇒ ⇒ 与 plan 自身的 GATE 声明（「Must pass before Phase 0 research」）**自相矛盾**；② 0.4 要求把实测红点写进 `harness/verification/B7F3/manual-verification.md`，而 tasks **T001** 明写该文件由 **T044**（Phase 10）创建 ⇒ ⇒ ⇒ ⇒ ⇒ **文件创建时点矛盾** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **两者都会造成「永久红 CI」窗口**（撞宪法 v1.6.0 红线「MUST NOT 写永久红的 CI」）⇒ ⇒ **证据**：plan 的 GATE 行 + Phase 0′ 行 · tasks T001 / T011 / T044 三行 | ① plan 的 Phase 0 拆为 **Phase 0（前置）** + **Phase 0′（后置 · = tasks T011）**；② **0′.1 的产出落「本条自带的 checklist note」**（**不写** `manual-verification.md`）⇒ ⇒ ⇒ **T044 MUST 转录 T001 的绿基线计数 + T011 的实测结果**（tasks T011 / T044 已同步）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **零红窗口 · 判据零放宽** |
| **S-19** | ⚠️ **2026-11-16 analyse 轮第三轮**：plan Summary 的「执行路径」行写 `run_graph(..., max_concurrency=...)` ⇒ ⇒ 与 **DD-3 / DD-4**、契约 **ES-01**、tasks **T010 / T026** 的「门面**恒不传**该关键字」**直接冲突** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **证据**：plan Summary 表 vs DD-3 / 契约 ES-01 | **已回修**：Summary 行删去 `max_concurrency=...` ⇒ 改为「**旋钮读取点在 L2**（关键字优先 · `config` 兜底）· 门面零搬运逻辑」⇒ ⇒ ⇒ ⇒ ⇒ **判据零放宽** |
| **S-20** | ⚠️ **2026-11-16 analyse 轮第三轮**：plan 的「Project Structure 树」与「Phase C3」两处仍写「不再是 2」⇒ ⇒ 与 **S-17**（判据只可更严）与宪法 **v1.14.0** **冲突**（真失败 `rc == 1` 仍判绿 ⇒ 门禁失效）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **证据**：plan 两处 vs spec 破冻结面清单第 4 行 / tasks T014 | **已回修**：两处统一为「**脚本成功 = `rc == 0`**」⇒ ⇒ ⇒ ⇒ ⇒ **判据收紧（与 S-17 同向）** |
| **S-21** | ⚠️ **2026-11-16 analyse 轮第三轮**：tasks 的**阶段编排**导致「Phase 2 → Phase 10」的红窗 —— `invoke` 接通（T010）后 `graph_core.py` 必以 `rc == 1` 结束 ⇒ ⇒ 而修脚本的 **T040 / T041 / T042** 排在 Phase 10 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **证据**：tasks T010 / T014 / T040–T042 三处 | **已回修**（发起者 2026-11-16 拍板）：**T040 / T041 / T042 前移至 Phase 2′**（置于 **T011** 之后）⇒ ⇒ ⇒ **T014 移至本阶段末尾**（脚本先修绿 · 再替换冻结断言）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **红窗收敛为阶段内的「T010 → T014」**（宪法 v1.12.0 的「冻结断言清单 MUST 实测化」强制该窗口存在 ⇒ **有界**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **任务号不变 · 仅换阶段** |
| **S-22** | ⚠️ **2026-11-16 analyse 轮第三轮**：**SC-010** 的「恢复后拿到 resume 值」**缺 checkpointer 载体** —— `src/freegraph/**` 内**零** saver 实现（`MemorySaver` 归 **B14F1**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **证据**：仓库既有验收脚本把该路径定为 **soft** 且注「载体待 **B14F1** 锁定」（`graph_core.py:392-393` · `agent_loop.py:275-280`） | **已回修**：**载体 = 测试侧的「自足桩 checkpointer」**（**T002** 交付 · 形态参照 `tests/differential/parity_probe.py:251-255`）⇒ ⇒ ⇒ ⇒ ⇒ **T029① MUST 挂它** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据不放宽**（仍是硬判据 · **MUST NOT** 因「无载体」降级为 soft）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **MUST NOT** 在 `src/` 内实现任何 saver（宪法原则 IV + 原则 VII） |
| **S-23** | ⚠️ **2026-11-16 analyse 轮第三轮**：「无值 key 填 `None`」在 **spec P-03 / X-1** 与 **`upstream-parity.md` P-03 / X-1** 共 **4 处**仍**未带**「仅覆盖型（无归约器）」限定 ⇒ ⇒ 与 **裁定 3 / FR-009** **字面冲突**（归约型未写 ⇒ 类型空值 `[]` / `0`）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **证据**：四处文本 vs 裁定 3 | **已回修**：四处**补限定** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **T052 必查项① 的处数由 12 扩到 16** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据零放宽** |
| **S-24** | ⚠️ **2026-11-16 analyse 轮第三轮**：验收脚本的**用例组清单**漏 **「A6 的 C17 段（中断与恢复）」**（既不在「保持硬断言」列表，也不在「降级」列表）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **证据**：`harness/demo/graph_core.py:357-405` | **已回修**：该段 **MUST 保持硬断言**（**挂起半边** ⇒ 依赖已交付 ⇒ 必绿）⇒ ⇒ ⇒ ⇒ 其**恢复半边**沿用**仓库既有写法** = `soft()` ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 整体降级 |
| **S-25** | ⚠️ **2026-11-16 analyse 轮第三轮**：① **同文件 `[P]` 冲突**（**T022 / T023** 同改 `test_invoke_errors.py`；**T025 / T027** 同改 `test_invoke_config.py`；**T040 / T041** 同改 `graph_core.py`）⇒ ⇒ 与 `[P]` 的定义（「不同文件、无未完成依赖」）冲突；② **T037** 标 `[P]` 但**依赖 T036**；③ tasks 追溯表 **T002 / T008** 行与任务正文不符；④ **FR-006** 的「步末清空（路由通道值不残留）」**无专门用例** | **已回修**：① **T023 / T027 / T037 / T041 去掉 `[P]`**（**T040 保留** ⇒ 可与 T042 并行）；② 追溯表 **T002** 行补 SC 挂载（标 ※）、**T008** 归属改为「裁定 1 / 3 / 8」；③ **T031 增 ④**（条件边图连续两次 ⇒ 无路由通道残留 · 键集逐字相等）⇒ ⇒ ⇒ ⇒ ⇒ **判据只可更严** |
| **S-26** | ⚠️ **2026-11-16 analyse 轮第三轮**（杂项）：① plan 风险 **R-9** 的缓解误引 **DD-5**（应为 **DD-2**）；② plan 改动面 §11 写「I-01\|I-13」（应含 **I-14**）；③ spec **Edge Cases** 的未交付方法列表漏 `get_state_history()`；④ tasks **T045** 未强调「追认 **MUST 由发起者本人作出** · **MUST NOT 由实现者代签**」（宪法 v1.6.0）；⑤ spec 裁定 **11–16** 无 Q&A 出处；⑥ 门禁 7 的「API 兼容矩阵已更新」在 README `:79` 起**早已落库** ⇒ **可达** ⇒ **无需**登记为分阶段偏离（宪法 v1.10.2 的括注已被仓库现状超越 · 其修订属发起者职权） | **已回修**：① **DD-5 → DD-2**；② **I-13 → I-14**；③ Edge Cases 补 **`get_state_history()`**；④ **T045 补「追认 MUST 由发起者本人作出」**；⑤ 裁定表**补来源注**（10 设计 + 6 承接 = 16 · 不是 18）；⑥ plan 的 EV 表**补门禁 7 的可达性说明** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据零放宽** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⚠️ **2026-11-16 analyse 轮第五轮 · 事实更新**：该括注**已按仓库现状订正**（**宪法 v1.15.0 · PATCH** · 生效副本 + `constitution-changelog.md` + 模板 **三处已同步**）⇒ ⇒ 「其修订属发起者职权」的历史状态**已终结** |
| **S-27** | ⚠️ **2026-11-16 analyse 轮第四轮（CRITICAL）**：plan 改动面 §4 与 research **DD-10** 均断言「README 兼容矩阵的两行**已在 G19 的可更新白名单**内」⇒ ⇒ **事实错误**（`StateGraph` 属**门面层 7 符号** ⇒ **不**参与 G19 的逐字节比对；`CompiledGraph` 属**契约层 21 符号**（`public-api.md` §0 的清单驱动口径 · 不硬编码个数） ⇒ **受**该比对保护且**原不在任何白名单**）⇒ ⇒ ⇒ ⇒ **破冻结面未按宪法 v1.9.0 登记 + 回溯修订 + 追认** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ | **已回修**：① `tests/facade/test_facade_gates.py` 新增 `MATRIX_ROWS_UPDATABLE_BY_B7F3`（**只放行 `CompiledGraph` 一行** · 「等价程度 MUST NOT 变差」护栏适用）；② spec 的破冻结面清单**新增一行**（**破冻结面 T-4**）；③ spec Assumptions 的**破面全集**改为 5 类；④ **T045** 追认文字增第 ④ / ⑤ 项、**T046** 守卫断言同步；⑤ **T047** 修正事实错误并指向白名单；⑥ plan 的 Constitution Check / Post-Design re-check 的冻结面行同步；⑦ **T052** 增必查项 ⑧ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据零放宽**（门禁只放宽一处 · 其余契约层行仍逐字未改） |
| **S-28** | ⚠️ **2026-11-16 analyse 轮第四轮**：**编号域碰撞** —— spec 的承接条款用 `H-1…H-10`，而 plan / tasks 用 `H4` / `H5` 指 analyse 轮的发现编号 ⇒ ⇒ **只差一个连字符** ⇒ ⇒ 且 analyse 轮的发现编号（`A1…A5` / `B1…B5` / `C1…C7` / `H1…H7` / `L1…L3` / `M1…M7`）在**五份工件里均无定义表** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ | **已回修**：① 全部发现编号统一加 **`FND-`** 前缀；② `research.md` 新增 **§7「编号域与发现编号对照表」**（**消歧的唯一权威**）⇒ 含编号域一览 + 发现编号逐条对照 + 三条「同前缀不同义」的消歧口径；③ **T052** 增必查项 ⑨（`FND-` 编号集 MUST 与对照表**逐项相等**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据零放宽** |
| **S-29** | ⚠️ **2026-11-16 analyse 轮第四轮**：plan 的 **Phase C** 含 **C6**（人工验证记录的守卫断言）⇒ ⇒ 而 C6 的判据依赖 **Phase D 的 D2**（写 `manual-verification.md`）⇒ ⇒ ⇒ ⇒ ⇒ **plan 的阶段顺序与其自身条目自相矛盾** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ | **已回修**：① plan 的 Phase C 标题加注「**只含 C1–C5**」；② plan 的 **C6** 条目改写为「= tasks **T046** · Phase 10 · 在 T044 / T045 之后」；③ plan 的**阶段映射**行同步；④ **T052** 增必查项 ⑩ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **零红窗口**（守卫断言仍 MUST 在记录写就之后才转绿） |
| **S-30** | ⚠️ **2026-11-16 analyse 轮第四轮**：**SC-010 的「恢复取值」半边缺可核验的载体口径** —— tasks **T002** 只写「实现 L1 `Checkpointer` 协议的 `get_tuple` / `put` / `put_writes` / `list` **等最小集**」⇒ ⇒ L1 协议实为 **8 方法**（`public-api.md:79`）⇒ ⇒ 且 L2 恢复路径**实际调用哪些方法**在工件里**未点名** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ | **已回修**：契约 **F-05** 冻结桩的方法集（**实测 L2 的调用点** `superstep.py:1873` / `:1885` / `:1904` / `:2007` / `:2092` / `:2169`）⇒ ⇒ ⇒ **3 个方法** + `get_tuple` 返回值的**3 个具名属性** + snapshot 的**4 个字段** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **T002** 按该清单实现（**MUST NOT** 以「等最小集」开放表述取舍）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据不放宽**（仍是硬判据） |
| **S-31** | ⚠️ **2026-11-16 analyse 轮第四轮**：**`max_concurrency` 的 config 兜底校验点**在 spec FR-023 与契约 ES-08 里有、但 **tasks T012 缺** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ | **已回修**：**T012** 补「config 兜底值的校验点 = `resolve_config` **之后**、`_first_graph` **之前**」+ 失败信号与关键字形态同款 ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据零放宽**（失败信号不变） |
| **S-32** | ⚠️ **2026-11-16 analyse 轮第四轮**：**D-94 的「覆盖型 key」限定**在 spec D-94 有、**tasks T036 丢** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ | **已回修**：**T036** 的 D-94 条目补「**MUST** 用覆盖型（无归约器）key（如 `llm_calls`）· **MUST NOT** 用归约型 key」⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据零放宽** |
| **S-33** | ⚠️ **2026-11-16 analyse 轮第四轮**：**FR-020** 在「FR → SC」追溯表里映射到 **SC-005** ⇒ ⇒ 而 SC-005 判的是「**节点抛出真异常**」⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ | **已回修**：FR-020 的追溯行加注「**兜底分支** · 与 FR-017 同一判定任务 **T023** · 正常路径不触达」⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 另立 SC（避免扩大追认面）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据零放宽** |
| **S-34** | ⚠️ **2026-11-16 analyse 轮第四轮**：spec「裁定编号映射」的来源注把 **H-5** 列进「**裁定 11–16** 的来源」⇒ ⇒ 而 **H-5** 落在**裁定 5**（设计裁定）的来源里、**裁定 16** 的来源是**下游承接 D-3** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ | **已回修**：来源注改为「裁定 1–10 ← Q1–Q10（裁定 5 兼采 H-5）；裁定 11–16 ← H-1(×2) / H-3 / H-9 / H-6 + **下游承接 D-3**」⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **「16 条」的计数口径不变**（10 + 6）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **计数与来源正交** |
| **S-35** | ⚠️ **2026-11-16 analyse 轮第四轮（LOW 杂项）**：① plan Phase C1 的「I-01…I-14」枚举**只列 12 项**（缺 I-12 / I-13 / I-14）；② spec 破冻结面清单的跨工件引用写「tasks **T005/T007**」（契约行注记实际在 **T006**）；③ plan 的 Project Structure 写 checklist「**16/16**」（实测 **36** 项已勾）；④ spec **FR-026** 把**协议面**与**非协议面**能力混列；⑤ **T034①** 与 **T020⑤** 重复覆盖「显式 `None` 初始值」；⑥ **T051** 的 **G28** 写「必跑」同时写「本地默认不跑」；⑦ spec 的「**第 4/5/6/7 处**」易与「第 4 条冻结断言」混淆 | **已回修**：① plan Phase C1 补出 **I-12 ⇒ T014** · **I-13 ⇒ T017⑦** · **I-14 ⇒ T046**；② 引用改为「**T005**（协议注解）+ **T006**（契约行注记）」；③ 改为「**36/36**」；④ **FR-026** 拆为 ① 协议面 · ② 非协议面两句；⑤ **T034①** 只留 docstring 守卫（「显式 `None`」归 **T020⑤** · 单一实现点）；⑥ **T051** 的 G28 判据写准（**本地跳过并注明 · CI 档 MUST 跑且 MUST 绿**）；⑦ spec 改为「**冻结断言 ①–④**」（清单行号另标）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据零放宽** |
| **S-36** | ⚠️ **2026-11-16 analyse 轮第四轮**：**tasks T036 把 D-92 / D-93 合并成一句** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ | **已回修**：拆成两句（D-92 判 `messages` 逐字相等 · D-93 判**键集 + 键序**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据零放宽** |
| **S-37** | ⚠️ **2026-11-16 analyse 轮第四轮**：**宪法的 v1.10.2 括注**仍写「兼容矩阵按 **B24F1 / M4** 才首次落库」⇒ ⇒ 而该章节**早已落库** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ | **已回修**（经发起者授权）：宪法括注**订正为事实**（矩阵已于 **B2F2** 落库 ⇒ 后续 feature 的门禁 7 **可达**）⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据零放宽**（v1.6.0 的三条要求一字未改） |
| **S-38** | FND-B10（CRITICAL）| **三对 `[P]` 任务同文件冲突**：`T017`×`T020`（`test_invoke_full_state.py`）· `T028`×`T029`（`test_invoke_interrupt.py`）· `T015`×`T036`（`parity_probe.py`，且 `T036` 依赖 `T015`）=> **第三轮回修（FND-B5）只修了 3 组，漏了这 3 组** => 违反 tasks.md:13 的 `[P]` 定义 => **处置**：三处**去 `[P]`** + 串行清单补为**五组** => 判据零放宽 | **已回修** |
| **S-39** | FND-H7（CRITICAL）| **T052 的三条 grep 型自检判据不可执行**：④「全文 grep『不再是 2』命中数 == 0」（实测 **7** 处命中，全在**禁止语境**）· ⑥「全文 MUST NOT 出现『…Phase 10…』」（实测 **4** 处**历史陈述**命中）· ⑦「…『门面传 max_concurrency』…」（实测 **3** 处**禁止语境**命中）=> **处置**：三条改为**判据形态 / 语义形态**的 grep（排除禁止语境与历史陈述）=> 判据零放宽 | **已回修** |
| **S-40** | FND-N1（HIGH）| **plan 的 Constitution Check「原则 X」行仍断言**「`StateGraph` / `CompiledGraph` 两行在 G19 的白名单内」=> **事实错误**（两行**都不在**任何白名单里；`StateGraph` 属门面层 7 符号不参与逐字节比对，`CompiledGraph` 属契约层 21 符号**受**该比对保护）=> 与 plan 改动面 §4 的 C1 回修、spec 破冻结面 T-4、tasks T052 必查项 ⑧④ **直接冲突** | **已回修**：plan 原则 X 行改写 |
| **S-41** | FND-N2（HIGH）| **T002 内部自相矛盾**：前半句「MUST 实现 `get_tuple`/`put`/`put_writes`/`list` 等最小集」与后半句「MUST 逐字按契约 §4 F-05 的 3 个方法」+「MUST NOT 以『等最小集』开放表述」**互斥**（F-05 明写 `list` 等 5 个方法 L2 不调用）=> **处置**：前半句并入 F-05 口径，删除 `list` 与「等最小集」 | **已回修** |
| **S-42** | FND-N3（MEDIUM）| **US4 的验收场景缺 SC-006 修订后的判定性半边**（「可观测并发度」）且 Independent Test 用**自环图**（单节点 => 重叠恒为 0 => 断言空洞）=> **处置**：US4 增两条验收场景（fan-out 图 · 重叠 0 / >= 1）+ Independent Test 补 fan-out 图 | **已回修** |
| **S-43** | FND-N4（MEDIUM）| **L1 其余 4 个带 `config` 参数的方法**（`stream`/`get_state`/`get_state_history`/`update_state`）的 **`config` 注解放宽**未登记为下游承接义务 => B8F2/B15F1/B16F1 将来各自再破一次冻结面且未登记 => **处置**：新增下游承接 **D-5** + 契约 **CF-05** + plan/tasks 接线 | **已回修** |
| **S-44** | FND-N5（LOW）| **计数过期**：「契约层 18 符号 / 18 行」=> 实际 **21 个**（`public-api.md` §0 · 清单驱动）=> **另**：spec X-1 与 `upstream-parity.md` X-1 的**实测引用**不一致（E-1/E-8 vs E-1）=> **另**：plan 改动面 §16 的夹具清单漏 `build_two_node_graph()` / `build_loop_graph()` => **另**：demo README「RunConfig 四字段」与现状 9 字段矛盾 | **已回修** |
| **S-45** | ⚠️ **2026-11-16 实施期实测发现（quickstart 事实订正）**：quickstart §3 的节点原写成 `return {"messages": list(state.get("messages", [])) + ["x"]}`（**返回全量**）⇒ ⇒ 归约器（`operator.add`）把已有内容**再追加一遍** ⇒ ⇒ 实测 `run1 : ['a', 'a', 'x']` ⇒ ⇒ 断言 `out2["messages"] == ["b", "x"]` **恒红** ⇒ ⇒ **处置**：节点改为返回**增量** `return {"messages": ["x"]}`（与 §1 的 `a` / `b` 节点**同款**）⇒ ⇒ **判据零放宽**（期望值**逐字不变**）⇒ ⇒ 只修**节点的返回值形态** ⇒ ⇒ 归 **FND-B1**（quickstart 属 `specs/` 构件） | **已回修** |

---

## Post-Design Constitution Re-Check（Phase 1 后）

| 复核项 | 结果 |
|---|---|
| **原则 XI 判定顺序** | P-01…**P-14** 全部带版本 + `路径:行号`；行为断言有**实测 E-1…E-10** 支撑；失败信号分叉仅 X-2 / X-3；X-4 / X-5 / X-6 属已登记的形态 / 缺省来源 / 阶段性差异 |
| **三态标注一致性** | DIFF → P-07 / P-08 / P-09 / P-12 / P-14 ⇒ X-4 / X-5 / X-6（+ **P-08** = `config` 载体面 · **非更严** ⇒ 原则 XI 末条只要求「标 **STRICTER** 的分叉 MUST 落在偏离登记里」⇒ **P-08 不必登记** · + P-12 的未就绪信号 · B7F2 已冻结）；STRICTER → P-03 / P-04 / P-05 ⇒ X-1 / X-2 / X-3；SAME → 其余；**「无孤行 / 漏行」指「偏离登记的每一条都有对照表的对应行」这一方向**（⚠️ **S-12 已回修**：X-1/X-2/X-3 的「类别」列**原**写「更严（…）」⇒ 分类词与 `STRICTER` 不同 ⇒ **已加 `STRICTER` 令牌** · 与 **B10F1** 先例同款） |
| **判词分布** | ⚠️ **S-13 已回修**：**差分场景组**（D-92…D-102）= **SAME 7 / STRICTER 3 / DIFF 1**；**上游对照表**（P-01…P-14）= **SAME 6 / STRICTER 3 / DIFF 5** ⇒ ⇒ ⇒ **两个对象 · 两套分布** ⇒ SC-017 的括注**已改**挂「差分场景组」 |
| **层纪律** | L3 单文件；L3 → L1 / L2 合法；**零新增源文件** ⇒ **无 L3 → L3**；**零新增 L2 导出** |
| **导出面** | `freegraph.graph` 仍 **7** 个；`freegraph.runtime.__all__` 仍 **23** 个；`public-api-snapshot.txt` **逐字节不变** |
| **冻结面** | **5 类破面**（**唯一事实源 = spec.md「Assumptions」的「破面全集 5 类」**）：L1 `invoke` 的 `input` 注解放宽 ＋ L1 `invoke` 的 `config` 注解放宽 ＋ L2 `run_graph` 的 `max_concurrency` **读取点**（**兼容扩展**）＋ ⚠️ **G19 的 `CompiledGraph` 矩阵行白名单**（**C1 回修** · **破冻结面 T-4**）＋ **四处**「invoke 未就绪」冻结断言的拆分替换 ⇒ **同属一次**追认（**追认项 = 5 类** · 见 tasks T045）；B7F2 的编译产物持有面**不破**；L2 **签名零改动** |
| **可判定性** | 28 FR / 20 SC 均可由自动化测试或人工记录判定（**SC-018 / SC-019 由「人工记录守卫」判定**）；`D-92…D-102`（**11 条**）判词齐备；契约 §6 的 **I-01…I-14** 逐条可测 |
| **永久红** | **EV-1**（B22F1 / B23F1 / B8F1）· **EV-2**（B8F1 / B25F1）· **EV-4**（B8F1 / B22F1 / B23F1 / B25F1）具名承接；**MUST NOT** 写永久红 CI（⇒ ⇒ **人工记录守卫断言 MUST 在记录写就之后才存在** ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 把守卫放在记录写就之前） |
| **零出站 / 零 env** | 零新依赖 / I/O / 网络；`warnings` 为本地输出（非出站） |

---

## 范围变更登记（PR-1 · 对立项书 §5.2 的行数口径）

> **纪律**：宪法「MUST NOT 悄悄超支」⇒ ⇒ 任何偏离立项书行数口径的估算 MUST **如实登记**。

| # | 偏离项 | 立项书口径 | 本 feature 估算 | 原因 | 处置 |
|---|---|---|---|---|---|
| **PR-1** | **测试行数** | 980 行（实现 460 / 测试 520） | 实现 **≈ 220** · 测试 **≈ 960**（合计 **≈ 1,180**） | ① **每个用户故事一个测试文件**（6 个 · 便于独立并行测试）② 差分场景 **D-92…D-102**（**11** 条 + 新 `InvokeScenario` 模型）③ 一键验收脚本 + 五段式人工验证记录 ④ 4 处冻结断言的**拆分替换** ⑤ **人工验证记录的守卫断言**（判据级覆盖 · I-14） | **登记**（本 feature **不**单方面改立项书数字 —— **依据 = 仓库既有惯例 + 立项口径属发起者批准**；⚠️ 宪法 v1.12.0 无此 MUST ⇒ 不假托宪法）⇒ ⇒ 实现侧**低于**立项书预算 ⇒ 差额优先回投测试侧 |

---

## Complexity Tracking

> 无未登记的宪法违规。**EV-1 / EV-2 / EV-4** 属宪法 v1.6.0 的**门禁分阶段**，已具名承接
> B8F1 / B22F1 / B23F1 / B25F1；**判据未放宽**。
> **X-1**（返回键集更严）属原则 XI ② 类（上游自身的不确定）· **X-2 / X-3**（更严的失败信号）·
> **X-4**（值形态）· **X-5**（缺省来源）· **X-6**（阶段性差异 · 更宽松）—— 全部已登记，
> 且与上游对照表的标注**逐字一致**。

| 复杂度来源 | 为什么需要 | 更简单的替代为何被拒 |
|---|---|---|
| 「稀疏视图 + 补齐无值 key」的**单一实现点**（约 +25 行） | 下游 **B8F2** 的 `stream` MUST 复用（下游承接 D-1）⇒ 两处各写一份必然漂移 | 内联在 `invoke` 里 ⇒ B8F2 必然重写；放进 `freegraph.runtime` ⇒ **扩 L2 导出面**（破冻结面） |
| 挂起结果的**两段归一**（`as_result_dict()` → 补齐） | `as_result_dict()` 的 `.state` 是**稀疏** ⇒ 与 FR-008 的 100% 键集冲突 ⇒ 必须在其**之后**补齐 | 逐字返回 `as_result_dict()` ⇒ 挂起路径的键集 ≠ schema 全集（FR-008 失效）；另写一条挂起专用转成 ⇒ 违反「转成路径只此一条」 |
| `max_concurrency` 的**读取点下沉到 L2**（`run_graph` 关键字优先 · config 兜底） | 上游的旋钮本就住在 **config** 里 ⇒ L2 读取 = 与上游**更同款**；且避免门面再写一份搬运逻辑 | 门面定点搬运（**次优** · 绕过根因 · 门面多一份搬运语义）；翻译整个映射 ⇒ 违反 FR-021 |
| L1 协议的**两处**注解放宽（破冻结面） | `input` 收 `Command` / `None`、**`config`** 收普通映射 ⇒ 都是**已锁定**的对外形态 ⇒ 契约必须写准 | 不放宽 ⇒ 契约说谎、下游照错口径写；只放宽 `input` ⇒ FR-002 无法落地 |
| 验收脚本的**用例组重新分级**（A5 / A6 / A9 / A10 ⇒ 软断言） | `invoke` 就绪后，这些组**首次可达** ⇒ 它们的依赖（B8F1 / B8F3）尚未交付 ⇒ 硬断言 ⇒ rc=1 ⇒ **G29 判 FAIL** | 保持硬断言 ⇒ CI 红；改就绪探针（「6 方法齐备即就绪」）⇒ 会**假装就绪**（B7F2 的同一教训） |
