# Upstream Parity: B20F1

**Feature**: B20F1 · **Date**: 2026-11-21 · **Spec**: [../spec.md](../spec.md)
**Upstream**: `langgraph 1.2.11` / `langchain-core 1.7.6` / `langsmith 0.14.17`
（取证于 2026-11-21，本仓库 `.venv` 实际安装版本）

> **口径**：上游**没有** freegraph 这样的「本地 JSONL trace 存储后端」。上游的可观测
> 数据面由 LangChain callbacks / LangSmith `RunTree` 承载，默认关闭，开启后经 HTTP 批量
> 发送到 LangSmith（或其它远端）。本 feature 主体落在原则 XI 的**必须自研区 ③**
> （上游没有的能力）与 **①**（零账号 / 零主动出站 / 零依赖）；只有「默认关闭」
> 「失败不阻断」「按 `run_id` 分组」「实例内串行」几类**行为面**与上游对齐。

---

## 1. 逐条对照（P-01…P-07）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| **P-01** | **默认关闭**：不显式配置就没有观测副作用 | `langchain_core/tracers/context.py:114-120`（`_get_trace_callbacks` 仅在 `_tracing_v2_is_enabled()` 时构造 tracer）· B19F1 实测 **E-1**（不传 callbacks ⇒ 0 个 handler 事件） | 不注入 `FileTraceStore` / 不传 `tracer=` ⇒ 零文件 / 零目录 / 零回调；`compile(tracer=None)` 等价于未注入 | **SAME**（行为面）· **DIFF**（表示：本地文件 vs 上游 callback） | 默认关闭是宪法原则 I / IV；本 feature 不改变 B19F1 的默认关闭语义 |
| **P-02** | **环境变量不得自动开启观测** | `langsmith/utils.py:119-144`（`TRACING_ENABLED` / `TRACING_V2` / `TRACING` 等环境变量可影响 tracing 开关）· `langchain_core/tracers/context.py:120` | 只认显式 `compile(tracer=FileTraceStore(directory=...))`；MUST NOT 读 `LANGSMITH_*` / `LANGCHAIN_*` / `FREEGRAPH_*` / `OTEL_*` | **STRICTER** | 宪法原则 I / 配置层黑名单；本项目反「key / env 存在即自动开 tracing」 |
| **P-03** | **持久化落点与出站** | `langsmith/client.py:139`（`httpx` 客户端）· `:619`（默认 `https://api.smith.langchain.com`）· `langsmith/_internal/_background_thread.py:377`（批量 ingest） | 本地 JSONL 文件；零网络、零账号、零 API key；MUST NOT 发起任何出站请求 | **STRICTER** | 宪法原则 IV / V；「trace 落盘，零出站」是本 feature 的判定 |
| **P-04** | **一次运行可按运行标识归组** | `langsmith/run_helpers.py:107-113`（当前 run tree）· `langchain_core/tracers/base.py:47,53`（run / parent run id） | 每个 `run_id` 一个 `trace-<run_id>.jsonl`；span / record 都带 `run_id` | **SAME**（id 分组语义）· **DIFF**（表示：文件 vs run tree） | C22 / C23 已冻结「一次运行一个 `run_id`」；本 feature 只按它归档 |
| **P-05** | **观测失败不改变图结果** | `langchain_core/callbacks/manager.py:351-354`（handler 异常被捕获并记警告） | 写入失败隔离 `Exception`；图结果与不注入时逐字相同；`BaseException` 不吞 | **SAME**（隔离语义）· **STRICTER**（可感知面：`write_errors` / `last_error` / `on_error`） | 宪法原则 IV；B18F1 / B19F1 已隔离接收端异常，本 feature 不得削弱，并补可感知信号 |
| **P-06** | **span / 补充记录的统一持久化形态** | 上游**没有**等价的「节点 span + 逐节点输入输出 / 触发源 / 并发组 / 屏障组」统一本地视图；这些事实散落在 callback / debug payload / 调度内部 | 两类 JSONL 行：完整 `Span` 行 + `TraceRecord.to_jsonable()` 行；`kind` 区分、`span_id` ↔ `id` 关联 | **DIFF**（自研区 ③：上游没有的能力） | B18F1 / B19F1 的下游承接要求；上游无同款本地存储结构 ⇒ 只能自研 |
| **P-07** | **并发写入的串行化载体** | 上游无本地文件锁；用**进程内队列 + 后台线程**批量 ingest（`langsmith/_internal/_background_thread.py:327-377`），锁是 per-Client / 全局（`langsmith/client.py:149` 的 `_tracing_drops_lock`、`:1344` 的 `_futures_lock`、`:1346` 的 `_run_ops_buffer_lock`），**没有按 run 分文件锁** | 每个 `FileTraceStore` **实例**一把 `threading.Lock`；锁只包住单行写入与诊断计数；`on_error` 在锁外调用 | **SAME**（实例内串行语义）· **DIFF**（表示：本地文件锁 vs 队列 + 后台线程） | 上游无本地 JSONL；per-instance 锁最接近 per-Client 锁，且不需要「每 run 锁表」 |

---

## 2. 实测基线（E-1…E-3 · 沿用 B19F1 · 取证于 2026-11-21）

| # | 实验 | 结果 |
|---|---|---|
| **E-1** | 两节点线性图 `a → b`，`invoke()`，不传 callbacks，环境变量全清 | 正常返回；**无任何** callback 事件（默认关闭） |
| **E-2** | 同图，传入自定义 `BaseCallbackHandler`，节点内调用 `get_current_run_tree()` | 共 6 条 handler 事件；节点内 `get_current_run_tree()` 返回 `None`（callback 路径不填充 `_PARENT_RUN_TREE_REF`） |
| **E-3** | `boom` 节点抛 `RuntimeError("boom")`，传入自定义 handler | 异常原样抛出；事件序列仍完成 run 生命周期（`on_chain_error`） |

> **实测来源**：B19F1 spec §2 的 `/tmp/b19_upstream_probe.py`（2026-11-21 实跑）。
> 本 feature **不新增**上游行为断言；本地 JSONL 形态属自研区，不与上游做逐字节对比。
> **P-07 的锁 / 队列形态**取证于**上游源码阅读**（`langsmith/client.py` ·
> `langsmith/_internal/_background_thread.py`），仅用于说明「上游没有按 run 分文件锁」，
> **不**作为本 feature 的差分行为断言。

---

## 3. 差分场景组（D-401…D-408）

> 编号段避开 B18F1 的 D-201…D-208 与 B19F1 的 D-301…D-310。

| # | 场景 | 断言（节点序列 / 最终状态 / 失败与否） | 判词 |
|---|---|---|---|
| **D-401** | 不注入任何 tracer / handler | freegraph：0 文件 / 0 目录 / 0 回调；上游：0 callback 事件；两侧图都正常完成 | SAME（P-01） |
| **D-402** | 注入 `FileTraceStore` / handler | freegraph：生成 `trace-<run_id>.jsonl`，含 span + record 行；上游：产生 callback 事件（不发本地文件）；两侧图最终状态逐字相等 | DIFF（P-03 / P-06 表示层） |
| **D-403** | 设置 `LANGSMITH_TRACING=true` 等环境变量 | freegraph：未注入 ⇒ 仍 0 文件；注入 ⇒ 只认 `directory`；上游：环境变量可能自动开启 tracing | STRICTER（P-02） |
| **D-404** | 零出站 | freegraph：socket 监测夹具「框架出站 == 0」；上游：开启后向 LangSmith 批量 ingest | STRICTER（P-03） |
| **D-405** | 写入目录不可写 | freegraph：图正常完成、异常传播 0、`write_errors > 0`；上游：handler 异常被捕获并记警告 | SAME（隔离）· STRICTER（可感知） |
| **D-406** | 两次运行归组 | freegraph：两个 `run_id` 两个文件，文件内 `run_id` 唯一；上游：两棵 run tree 由 run id 区分 | SAME（P-04 语义）· DIFF（表示） |
| **D-407** | 依赖闭包 | freegraph 基础安装闭包为空；上游 `langchain-core` 闭包含 `langsmith` / `httpx` 等 | STRICTER（P-03） |
| **D-408** | 同一 store 实例并发写 | freegraph：per-instance 锁串行、每行完整、不同实例互不阻塞；上游：进程内队列 + 后台线程串行 ingest | SAME（实例内串行语义）· DIFF（表示） |

⇒ **判词分布**：**SAME 行为面 3**（D-401 / D-405 的隔离段 / D-408 的串行语义）+
**STRICTER 3**（D-403 / D-404 / D-407；D-405 另有 STRICTER 感知面）+
**DIFF 3**（D-402 / D-406 / D-408 的表示层；D-402 同时含 P-06 自研结构）。

⇒ **落点**：`tests/differential/test_b20f1_local_trace_parity.py` ⇒ **CI 的 Linux 全量档真跑**
（上游缺席即 skip · 沿用 B5F2 的「缺席即 skip」纪律）。本 feature 的本地 JSONL 形态
不与上游逐字节对比，只对齐「默认关闭 / 失败隔离 / 按 run 分组 / 实例内串行」四类行为面。

---

## 4. 偏离登记（X-1…X-6）

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-1** | **DIFF**（自研区 ③：上游没有的能力） | 上游无本地 JSONL trace 后端、无「完整 `Span` + `TraceRecord`」双行持久化、无 `kind` 区分（对应 **P-06**） | C27 的写入侧必须自研；上游对应物是 LangSmith 远端 run tree，引入即破零依赖 / 零出站 | 本 feature（写入侧）· B20F2（查询侧） |
| **X-2** | **STRICTER**（自研区 ①：零账号 / 零主动出站 / 零依赖） | 上游 tracing 可由环境变量开启并经 HTTP 发往 LangSmith（对应 **P-02 / P-03**） | freegraph MUST 零第三方依赖、零环境变量、零主动出站；只认显式注入的 `directory` | 宪法原则 I / II / IX · 本 feature |
| **X-3** | **DIFF**（自研区 ③：上游没有的能力 · 表示层） | 本地文件粒度 = 每个 `run_id` 一个 `trace-<run_id>.jsonl`；上游是一个远端 run tree（对应 **P-04**） | 文件是内部实现细节（C27 ⑤）；按 `run_id` 归档使「一次运行一条链」可直接落地，且不把 trace 塞进 `stream()` 信封 | 本 feature · B20F2（按 `run_id` 查询） |
| **X-4** | **STRICTER**（更严的失败信号） | 写入失败除「不阻断」外，还 MUST 提供 `write_errors` / `last_error` / `on_error` / 日志四路可感知（对应 **P-05**） | 静默吞错会让用户以为 trace 已记录；宪法原则 IV 要求可诊断，本项目要求失败信号**可判定** | 本 feature |
| **X-5** | **DIFF**（自研区 ③：上游没有的能力 · 表示层） | 并发写入载体 = **每个 store 实例一把 `threading.Lock`**；上游是进程内队列 + 后台线程批量 ingest（对应 **P-07**） | 上游无本地 JSONL，也没有按 run 分文件锁；per-instance 锁比「每 run 锁表」简单，且与上游 per-Client 锁最接近 | 本 feature |
| **X-6** | **DIFF**（自研区 ③：上游没有的能力 · 表示层） | 默认关闭的**表示**：本地文件 sink vs 上游 callback / tracer（对应 **P-01** 的 DIFF 半段） | 默认关闭的**行为面**是 SAME；差异仅在「观测结果落到本地文件」这一表示层，属自研区 ③ | 本 feature |

---

## 5. 破冻结面 / 回溯修订

| 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 |
|---|---|---|---|
| `freegraph.observability.__all__` 的**精确集合断言**（B19F1） | `tests/facade/test_api_snapshot.py` 的精确集合 · `tests/contracts/test_b19f1_lazy.py` 的成员断言 | **只增不改**：新增 `FileTraceStore`；既有 5 符号逐字保留；`trace_run_scope` 仍不导出 | `harness/verification/B20F1/manual-verification.md` |
| **L5 依赖面**（B18F1 / B19F1 的「L5 只 import 标准库 + L1」断言） | `tests/contracts/test_architecture.py` · `tests/contracts/test_b19f1_gates.py` | **无需拆分**：`_file_store.py` 只 import 标准库 + L1 `Span` + 同层 `TraceRecord`；只需把新文件加入扫描清单（只增） | 同上 |
| **署名头清单** | `tests/contracts/test_architecture.py::SIGNED_SOURCE_FILES` | 追加 `src/freegraph/observability/_file_store.py`（只增） | 同上 |

> **不破**：`Span` 11 字段 · `TraceSink` 3 方法 · `TraceRecord` 13 字段 ·
> `RunConfig` 9 字段 · `SuperStepResult` 5 字段 / `PregelTask` 7 字段 ·
> `stream()` 事件信封 · `freegraph.graph` 门面 8 符号 · L1 契约 22 符号 ·
> `freegraph.runtime.__all__`。**唯一新增公开符号**：L5 `FileTraceStore`
> （不进 `freegraph.graph`，`import freegraph` 仍不加载 L5）。
