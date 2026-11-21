# Upstream Parity: B19F1

**Feature**: B19F1 · **Date**: 2026-11-21 · **Spec**: [../spec.md](../spec.md)
**Upstream**: `langgraph 1.2.11` / `langchain-core 1.7.6` / `langsmith 0.14.17`
（取证于 2026-11-21，本仓库 `.venv` 实际安装版本）

> **口径**：上游**没有**自有 `TraceSink` / `current_span()`。上游的可观测挂钩是
> `callbacks` / `tracers`（`langchain-core` 类型），「当前 run」由 LangSmith
> `get_current_run_tree()` 提供（`RunTree`）。本 feature 主体落在宪法原则 XI 的
> **必须自研区 ③ / ① / ④**；只有「上下文内当前单元」「默认关闭」「失败也成对」
> 「接收端异常隔离」与上游对齐。

---

## 1. 逐条对照（P-01…P-10）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| **P-01** | 上下文内**当前运行单元**，无则空 | `langsmith/run_helpers.py:107-113` · `langsmith/_internal/_context.py:27,30-37` · `run_helpers.py:152` | `current_span()` 返回最内层 `Span`；无则 `None` | **SAME**（语义）· **DIFF**（表示 / 可得性） | 上游返回 `RunTree`，freegraph 返回 `Span`；E-2 实测 callback 路径不可得 ⇒ freegraph 在节点执行期更强（自研区 ③） |
| **P-02** | **注入载体** | `langchain_core/runnables/config.py:92,134,145,360-383` · `runnables/base.py:319-324` | **编译期关键字** `compile(tracer=...)` | **DIFF** | `RunnableConfig.callbacks` 是 `langchain-core` 类型；复用即破零 LangChain 红线（自研区 ①③） |
| **P-03** | **默认关闭受 env 影响？** | `langchain_core/tracers/context.py:120,141-144` · `langsmith/utils.py:119-144` | 只认显式注入；MUST NOT 读 env | **STRICTER** | 宪法原则 I / 配置层黑名单 |
| **P-04** | 成功路径 start / end 成对 | `langchain_core/tracers/base.py:261,306` · `callbacks/base.py:386` | `on_span_start` / `on_span_end` 按 `id` 成对 | **SAME**（行为面）· **DIFF**（表示） | 载荷从 callback run 改为 `Span` |
| **P-05** | 异常路径仍成对、异常原样重抛 | `langchain_core/tracers/base.py:335` · `runnables/base.py:2366` | 同 `id`、`end_time` 已填的 end span；原异常重抛 | **SAME**（语义）· **DIFF**（表示） | 「失败也成对」同为行为面 |
| **P-06** | 父子 / 嵌套 | `langchain_core/callbacks/manager.py:510,532,623` · `langsmith/run_helpers.py:152` | `Span.parent` = 父 span 的 `id` 字符串 | **SAME**（语义）· **DIFF**（表示） | 父链语义同；表示用 id 字符串（JSON 可序列化） |
| **P-07** | 接收端 / handler 异常隔离 | `langchain_core/callbacks/manager.py:351-354` | 回调异常隔离；可 `logging.warning`；不改图执行 | **SAME** | 由 B18F1 `SpanProducer` 实现，本 feature 不削弱 |
| **P-08** | 运行时依赖闭包 | `langchain-core 1.7.6` 的 `Requires-Dist` 含 `langsmith<1.0.0,>=0.14.9` · B18F1 E-4 | 基础安装闭包**为空集** | **STRICTER** | 宪法原则 I / II / IX |
| **P-09** | 两条事件通道按 id 关联 | `langchain_core/tracers/base.py:47,53` | `stream()` 事件与 span 共享 `run_id` / `thread_id`（L2 contextvar）；两通道独立 | **SAME**（id 语义）· **DIFF**（双通道结构） | D11 已冻结；trace 不塞 stream 信封 |
| **P-10** | 触发源 / 并发组 / 屏障组的统一元数据面 | 上游**没有**等价统一暴露：散落在调度内部 / callback / debug payload（`langgraph/pregel/_algo.py:482` 仅体现节点名序） | L5 自有补充 trace 记录统一给出 `triggers` / `concurrency_group` / `barrier_groups`，经可选 `on_trace_record` 推送；不写进 `Span` | **DIFF**（自研区③） | B9F1 / B11F1 / B12F1 / B7F4 承接要求；上游无同款结构 ⇒ 自研；不破 `Span` / `SuperStepResult` |

---

## 2. 实测基线（E-1…E-3）

| # | 实验 | 结果 |
|---|---|---|
| **E-1** | 两节点线性图 `a → b`，不传 `callbacks`，env 全清 | 正常返回 `{"x": 2}`；**无** callback 事件 |
| **E-2** | 同图 + 自定义 `BaseCallbackHandler`，节点内 `get_current_run_tree()` | **6 条** handler 事件（图 start → a start/end → b start/end → 图 end）；节点 run `parent_run_id` == 图 run id；**节点内 `get_current_run_tree()` 返回 `None`**（callback 路径不填充 `_PARENT_RUN_TREE_REF`） |
| **E-3** | `boom` 抛 `RuntimeError("boom")` + handler | 异常原样抛出；事件 = 图 start → a start/end → boom start → `on_chain_error`（boom）→ `on_chain_error`（图） |

> **实测脚本**：`/tmp/b19_upstream_probe.py`（2026-11-21 实跑 · 不进仓库）。
> **源码参照**：`langsmith/run_helpers.py:107-113,152` · `langsmith/_internal/_context.py:27,30-37` ·
> `langsmith/utils.py:119-144` · `langchain_core/runnables/config.py:92,134,145,360-383` ·
> `langchain_core/runnables/base.py:319-324,2366` · `langchain_core/callbacks/manager.py:351-354,510,532,623` ·
> `langchain_core/callbacks/base.py:386` · `langchain_core/tracers/base.py:47,53,261,306,335` ·
> `langchain_core/tracers/context.py:120,141-144`。

---

## 3. 差分场景组（D-301…D-310）

> 编号段避开 B18F1 的 D-201…D-208。

| # | 场景 | 断言 | 判词 |
|---|---|---|---|
| **D-301** | 不注入 sink / handler | freegraph span / 回调 == 0；上游 callback == 0；两侧正常完成 | SAME（P-03） |
| **D-302** | 两节点线性图 + 注入 | freegraph 2 对节点 start/end；上游 2 组 callback；最终状态逐字相等 | SAME（行为面）· DIFF（表示 · P-04） |
| **D-303** | 节点 → 工具 → 模型嵌套 | freegraph 子 span `parent` == 直接父级 `id`；上游 `parent_run_id` 逐层正确 | SAME（父链语义）· DIFF（表示 · P-06） |
| **D-304** | 环境变量 + 不注入 | freegraph 设 `LANGSMITH_TRACING=true` 后 span 仍 == 0；上游可能自动开启 | STRICTER（P-03） |
| **D-305** | 异常节点 | freegraph 结束 span 仍产生、异常原样重抛；上游 `on_chain_error` 仍触发 | SAME（P-05） |
| **D-306** | 图节点执行期间的当前单元 | freegraph `current_span()` 返回内层 / 外层 / `None`；上游 E-2 在 callback 节点内返回 `None` | DIFF（可得性 / 表示 · P-01） |
| **D-307** | 依赖闭包 | freegraph 闭包为空；上游 `langchain-core` 闭包含 `langsmith` | STRICTER（P-08） |
| **D-308** | 注入载体 | 两侧配置后均产事件；freegraph `compile(tracer=...)`；上游 `config["callbacks"]` | DIFF（P-02 · API 不同） |
| **D-309** | 触发源 / 并发组 / 屏障组元数据 | freegraph：实现 `on_trace_record` 的 sink 收到 `triggers` / `concurrency_group` / `barrier_groups`，且与节点 span 对齐；上游：无等价统一结构 | DIFF（P-10 · 自研区③） |
| **D-310** | 两条事件通道按 id 关联 | freegraph：同一次运行的 `stream()` 事件与 `TraceSink` span 的 `run_id` / `thread_id` 逐字相同；上游：流式事件与 callback run 共享 run 生命周期 | SAME（id 语义）· DIFF（双通道结构 · P-09） |

**判词分布**：SAME 行为面 **5**（D-301 / D-302 / D-303 / D-305 / D-310；D-302 / D-303 /
D-310 同时含表示层 DIFF）+ STRICTER **2**（D-304 / D-307）+ DIFF **4**（D-306 可得性 / 表示 ·
D-308 注入载体 API · D-309 统一元数据面 · D-310 双通道结构）。

---

## 4. 偏离登记（X-1…X-5）

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-1** | **DIFF**（自研区 ③；行为面 SAME · 表示层 DIFF） | 上游无自有 `TraceSink` / `current_span()`（P-01 / P-04 / P-05 / P-06 的表示层差异） | C23 / C24 必须自研；`Span` / `TraceSink` 已由 B2F1 冻结 | B2F1（协议 / 字段面）· 本 feature（接入 / 推送） |
| **X-2** | **STRICTER**（自研区 ①） | 上游 tracing 由 `langchain-core` + `langsmith` 承载、可 env 自动开（P-03 / P-08） | 零第三方依赖 / 零 env / 零出站；只认显式注入 | 宪法原则 I / II / IX · 本 feature |
| **X-3** | **DIFF**（自研区 ①③） | 注入载体 = 编译期关键字，而非 `RunnableConfig.callbacks`（P-02） | `RunnableConfig` / callbacks 是 `langchain-core`；`RunConfig` 是纯数据 | 本 feature · spec 形态裁定 |
| **X-4** | **DIFF**（自研区 ③） | 触发源 / 并发组 / 屏障组的统一 trace 元数据面（对应 **P-10** · B9F1 / B11F1 / B12F1 / B7F4） | 上游散落在调度内部 / debug payload，无统一暴露；freegraph 在 L5 统一提供，且不写进 `Span` | 本 feature（承接）· B20（存储） |
| **X-5** | **DIFF**（自研区 ③ · 表示层） | 两条事件通道的载体结构（对应 **P-09**） | 上游 callback run 与流式事件共享 run；freegraph 用 L2 私有 id 载体 + 自有 span，**不把 trace 塞进 `stream()` 信封**；两条通道独立、按 id 合并 | 本 feature（接入）· B8F2（id 载体） |

---

## 5. 破冻结面 / 回溯修订

| 冻结面 | 修订 | 处置 |
|---|---|---|
| `StateGraph.compile` 签名（L3） | 追加 keyword-only `tracer: TraceSink \| None = None` | **只增不改**；`compile()` 仍无参可调用；API 快照**更新（非放宽）** |
| B18F1「L5 只 import 标准库 + L1」断言 | `_inject.py` 需 import L2 私有 hook | **拆分而不删**：纯模块断言保留；`_inject.py` 例外断言 |
| ARCH-1（L3 → L5） | `_stategraph.py` 局部 import `observability._inject` | **R-1 / R-2 / R-3 已获发起者一次性追认（2026-11-21）**；更新 `立项书 §5.1` / `spec §5` / 层注册表 + G25 + verification 追认 |
| ARCH-3（L5 → L2） | `_inject.py` 仅绑定 L2 `_span_hook`（不读 `_stream_context`） | **R-2** 已获一次性追认；只限 tracer 接线 |

> **不破**：`Span` 11 字段 · `TraceSink` 3 方法 · `RunConfig` 9 字段 ·
> `SuperStepResult` / `PregelTask` · `stream()` 信封 · 门面 8 符号 · L1 22 符号 ·
> `freegraph.runtime.__all__`。
