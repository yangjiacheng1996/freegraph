# Upstream Parity: B20F2

**Feature**: B20F2 · **Date**: 2026-11-22 · **Spec**: [../spec.md](../spec.md)
**Upstream**: `langgraph 1.2.11` / `langchain-core 1.7.6` / `langsmith 0.14.17`
（取证于 2026-11-21，本仓库 `.venv` 实际安装版本；沿用 B20F1 的版本钉住口径）

> **口径**：上游**没有** freegraph 这样的「本地 trace 查询 API + 可替换本地后端」。
> 上游的可观测查询是 **LangSmith SaaS 的远端 run 查询**（`langsmith.Client.list_runs` /
> `read_run`），默认关闭，开启后经 HTTP 访问远端。本 feature 主体落在原则 XI 的
> **必须自研区 ③**（上游没有的能力）与 **①**（零账号 / 零主动出站 / 零依赖）；
> 只有「空过滤器取全部」「按 run id 过滤」「失败隔离」「默认关闭」几类**行为面**
> 与上游对齐。

---

## 1. 逐条对照（P-01…P-07）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| **P-01** | **本地 trace 查询能力** | **上游无本地查询**；查询是 LangSmith 远端 `langsmith/client.py:4224`（`list_runs`）/ `:4068`（`read_run`），返回远端 `Run` 模型 | 两个本地后端共享 `query(TraceQuery \| None) -> list[dict]`；无网络、无账号 | **DIFF**（自研区 ③：上游没有的能力） | 本地可检索是 freegraph 的增量价值；上游查询必须连 SaaS |
| **P-02** | **过滤器集合** | `langsmith/client.py:4224-4243`（`project_id` / `run_type` / `trace_id` / `filter` / `start_time` / `run_ids` / …） | 四类过滤器 `run_id` / `thread_id` / 时间范围 / 节点名，AND 组合；**不含** `checkpoint_id` / `task_id` / `superstep` | **DIFF**（自研形态）· **STRICTER**（过滤器面收窄到 C27 冻结项） | C27 / DF6 已冻结 5 字段请求；不收窄会让契约漂移 |
| **P-03** | **零出站 / 零账号** | `langsmith/client.py:139`（`httpx` 客户端）· `:619`（默认 `https://api.smith.langchain.com`）· `langsmith/_internal/_background_thread.py:377`（批量 ingest） | 查询只读本地文件 / 本地 SQLite；零网络、零账号、零 API key | **STRICTER** | 宪法原则 I / IV / V；「查询本地 trace」不得变成远端请求 |
| **P-04** | **空过滤器取全部** | `langsmith/client.py:4224` 的 `list_runs` 在无过滤参数时列举项目内 runs（远端语义，源码阅读） | `TraceQuery()` / `query=None` 返回本地全部条目；无隐式截断 | **DIFF**（表示 / 远端语义：本地列表 vs 远端迭代器；**不标 SAME 行为面**） | C27 / FR-009 的「空过滤器」要求；上游侧未实测，不宣称行为面等价 |
| **P-05** | **失败隔离** | `langchain_core/callbacks/manager.py:351-354`（handler 异常被捕获并记警告） | 查询独立于写入回调；写入失败隔离沿用 B20F1；查询异常只到调用方 | **SAME**（隔离语义）· **STRICTER**（写入可感知面沿用 B20F1 四路诊断） | 宪法原则 IV；本 feature 不削弱 B20F1 |
| **P-06** | **结果表示** | 上游返回 `ls_schemas.Run` 等 SDK 对象，需再序列化 | 返回纯 `dict` 列表（B20F1 行视图），直接 `json.dumps` | **DIFF**（表示层：SDK 模型 vs 纯数据） | C27 ③；P4 的 CI 断言要求纯数据 |
| **P-07** | **默认关闭 / 环境变量** | `langchain_core/tracers/context.py:114-120`（只有启用 tracing 才构造 tracer）· `langsmith/utils.py:119-144`（`LANGSMITH_*` 环境变量可影响开关） | 不显式注入 store ⇒ 零查询 / 零存储；查询只认显式 `TraceQuery`，不读环境变量 | **SAME**（默认关闭）· **STRICTER**（不读 env） | 宪法原则 I / 配置层黑名单 |

---

## 2. 实测基线（E-1…E-3 · 沿用 B19F1 / B20F1 · 取证于 2026-11-21）

| # | 实验 | 结果 |
|---|---|---|
| **E-1** | 两节点线性图 `a → b`，`invoke()`，不传 callbacks，环境变量全清 | 正常返回；**无任何** callback 事件（默认关闭） |
| **E-2** | 同图，传入自定义 `BaseCallbackHandler` | 共 6 条 handler 事件；回调路径不填充 `_PARENT_RUN_TREE_REF` |
| **E-3** | `boom` 节点抛 `RuntimeError("boom")`，传入自定义 handler | 异常原样抛出；事件序列仍完成 run 生命周期（`on_chain_error`） |

> **实测来源**：B19F1 spec §2 的 `/tmp/b19_upstream_probe.py`（2026-11-21 实跑）。
> 本 feature **不新增**上游行为断言；P-01 / P-02 / P-03 / P-04 / P-07 的
> 「上游没有本地查询 / 查询走远端 / 空过滤器的远端迭代器语义 / 环境变量可影响开关」
> 取证于**上游源码阅读**与 `.venv` 实际安装版本，仅用于说明能力缺失与表示差异，
> **不**作为本 feature 的差分行为断言（P-05 的隔离语义由 E-1 / E-3 实测支撑）。

---

## 3. 差分场景组（D-501…D-508）

> 编号段避开 B18F1 的 D-201…D-208、B19F1 的 D-301…D-310、B20F1 的 D-401…D-408。

| # | 场景 | 断言（结果 / 失败与否） | 判词 |
|---|---|---|---|
| **D-501** | 本地查询 vs 上游远端查询 | freegraph：本地 `query` 返回条目；上游：需账号 + 远端 `list_runs`；两侧图结果逐字相等 | DIFF（P-01 / P-06） |
| **D-502** | 零出站 | freegraph：socket 监测夹具「框架出站 == 0」；上游：查询经 HTTP 到 LangSmith | STRICTER（P-03） |
| **D-503** | 空过滤器 | freegraph：返回本地全部条目；上游：无过滤列举远端 runs | DIFF（表示 / 远端语义） |
| **D-504** | 四类过滤 + 组合 | freegraph：每个过滤只返回匹配项；两个后端结果相等 | DIFF（自研形态；上游无同款四类本地过滤） |
| **D-505** | 失败隔离 | freegraph：查询/写入失败都不改变图结果；写入诊断沿用 B20F1 | SAME（隔离）· STRICTER（诊断） |
| **D-506** | 环境变量 | freegraph：设置 `LANGSMITH_*` / `FREEGRAPH_*` 不改变查询 / 存储 | STRICTER（P-07） |
| **D-507** | 依赖闭包 | freegraph 基础安装闭包为空；`sqlite3` 属标准库；上游闭包含 `langsmith` / `httpx` 等 | STRICTER（P-03） |
| **D-508** | 并发写 + 查询 | freegraph：per-instance 锁 + SQLite 文件锁；无损坏、无半行；Windows / Linux 均通过 | DIFF（自研本地后端） |

⇒ **判词分布**：**SAME 行为面 1**（D-505 的隔离段）+
**STRICTER 4**（D-502 / D-505 诊断面 / D-506 / D-507）+ **DIFF 4**（D-501 / D-503
表示 / D-504 / D-508）。

⇒ **证据口径**：D-501 / D-503 / D-506 的上游侧是**能力 / 表示层说明**（源码阅读），
不是需要实测的差分行为断言；差分用例只对 freegraph 侧做可执行断言
（D-502 / D-505 / D-507 的零出站 / 隔离 / 依赖闭包除外）。

⇒ **落点**：`tests/differential/test_b20f2_trace_query_parity.py` ⇒ **CI 的 Linux 全量档真跑**
（上游缺席即 skip · 沿用 B5F2 的「缺席即 skip」纪律）。本 feature 不与上游做逐字节
结果对比，只对齐「失败隔离 / 默认关闭 / 零出站」三类行为面；空过滤器仅作本地表示层
说明（P-04 / D-503 标 **DIFF**，**不标 SAME 行为面**）。

---

## 4. 偏离登记（X-1…X-8）

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-1** | **DIFF**（自研区 ③：上游没有的能力） | 上游无本地 trace 查询 API、无可替换本地查询后端（对应 **P-01 / P-06**） | C27 的读取侧必须自研；上游对应物是 LangSmith SaaS，引入即破零依赖 / 零出站 | 本 feature · B21F1（后端对接文档） |
| **X-2** | **STRICTER**（自研区 ①：零账号 / 零主动出站 / 零依赖） | 上游查询经 HTTP 访问 LangSmith（对应 **P-03**） | freegraph MUST 零第三方依赖、零环境变量、零主动出站；只读本地存储 | 宪法原则 I / II / IX · 本 feature |
| **X-3** | **DIFF**（自研区 ③：上游没有的能力 · 表示层） | 返回纯 `dict` 行视图 vs 上游 SDK `Run` 模型（对应 **P-06**） | C27 ③ 要求 JSON 可序列化；纯数据便于 CI 断言，也保留 B19F1 `to_jsonable()` 原样字段 | 本 feature |
| **X-4** | **STRICTER**（更严的失败信号；隔离语义 SAME） | 写入失败 MUST 沿用 B20F1 的四路可感知（对应 **P-05** 的 STRICTER 半段；隔离语义 SAME） | 静默吞错会让用户以为 trace 已记录；宪法原则 IV 要求可诊断 | 本 feature |
| **X-5** | **DIFF**（自研区 ③：上游没有的能力 · 表示层） | 本地 SQLite / JSONL 后端与内部 schema vs 上游远端存储（对应 **P-01**；P-03 的 STRICTER 由 **X-2** 承接） | 表结构 / 文件格式是 C27 ⑤ 的内部实现细节；本地后端才能离线可查 | 本 feature |
| **X-6** | **DIFF · STRICTER**（自研区 ③ / ②：上游没有的本地过滤器形态 + 收窄到 C27） | 上游 `list_runs` 的过滤器集合（`project_id` / `run_type` / `trace_id` / `filter` / `run_ids` / …）比 freegraph 的四类本地过滤器宽（对应 **P-02** 的 DIFF + STRICTER 两半段） | C27 / DF6 已冻结 5 字段请求；不把过滤器面收窄会让契约漂移 | 本 feature |
| **X-7** | **DIFF**（自研区 ③：上游没有的能力 · 表示层） | 空过滤器的上游表示是远端 `list_runs` 迭代器；freegraph 返回本地 `list[dict]`（对应 **P-04**） | C27 ③ 要求 JSON 可序列化；本地列表便于 CI 断言 | 本 feature |
| **X-8** | **STRICTER**（自研区 ①：零环境变量） | 上游 `LANGSMITH_*` 等环境变量可影响 tracing / 查询开关；freegraph 不读 env（对应 **P-07** 的 STRICTER 半段；默认关闭行为面 SAME） | 宪法原则 I / 配置层黑名单；查询只认显式 `TraceQuery` | 本 feature |

---

## 5. 破冻结面的回溯修订清单（本 feature 触发）

> 本 feature **不改写**已发布的 B20F1 / B19F1 事实，只做**增量接线**与**必要的断言拆分**。

| 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 |
|---|---|---|---|
| `freegraph.observability.__all__` 的**精确集合断言**（B20F1 交付） | `tests/facade/test_api_snapshot.py` / `tests/contracts/test_b19f1_lazy.py` | **只增不改**：新增 `SqliteTraceStore`；既有 6 符号逐字保留 | `harness/verification/B20F2/manual-verification.md` |
| B20F1 的「`FileTraceStore` 公开面**没有**查询方法」断言 / 文字 | `tests/contracts/test_b20f1_contracts.py::test_public_face_is_write_only_and_has_diagnostics`；`specs/b20f1-local-trace-jsonl/spec.md` 的 Clarifications / SC-006 文字；`specs/b20f1-local-trace-jsonl/contracts/file-trace-store-contract.md` §1 / §8 | **拆分而不删**：保留写侧 4 方法 + 2 诊断 + 无生命周期；`queries` 期望由 `[]` 改为 `["query"]`；`search` / `read` / `read_all` 仍禁止；B20F1 文字**只追加**「查询方法归 B20F2，写侧不变」的说明，不删除原事实 | 同上；B20F1 记录不回溯改写 |
| `SIGNED_SOURCE_FILES` / L5 门禁扫描清单 | `tests/contracts/test_architecture.py` · `tests/contracts/test_b19f1_gates.py` | 追加 `_query.py` / `_payloads.py` / `_sqlite_store.py`（**只增**） | 同上 |
| **不破** | `Span` 11 字段 · `TraceSink` 3 方法 · `TraceRecord` 13 字段 · `TraceQuery` 5 字段 · `RunConfig` 9 字段 · `SuperStepResult` / `PregelTask` · `stream()` 信封 · 门面 8 符号 · L1 22 符号 · `freegraph.runtime.__all__` · B20F1 JSONL 写侧 | 零改动 | — |

> **唯一新增公开符号**：`freegraph.observability.SqliteTraceStore`（L5，不进
> `freegraph.graph` 门面，`import freegraph` 仍不加载 L5）；`FileTraceStore.query`
> 是既有类的新方法，不是新符号。
