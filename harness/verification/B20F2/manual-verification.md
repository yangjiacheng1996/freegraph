# B20F2 · 人工验证记录（Trace 查询 API + SQLite 后端）

**Feature**: B20F2 · **日期**: 2026-11-22 · **实现者**: 自动化实现轮次（OpenCode / speckit.implement）

## 1. 验证环境

- CPython 3.11（`.venv`）· Linux x86_64 · 零出站。
- 基线命令：`.venv/bin/python -m pytest -q --tb=no`
- 基线结果：`1991 passed, 7 skipped in 137.38s`（2026-11-22 实跑）。
- 实现后全量回归：`2111 passed, 8 skipped in 149.95s`（2026-11-22 最终实跑；只增不减，新增 1 个 Windows 分支 skip）。
- 定向测试：
  - `.venv/bin/python -m pytest -q tests/observability/test_b20f2_*.py` ⇒ `87 passed, 1 skipped`
  - `.venv/bin/python -m pytest -q tests/contracts/test_b20f2_*.py tests/differential/test_b20f2_trace_query_parity.py` ⇒ `22 passed`
- 一键验收：`.venv/bin/python harness/verification/B20F2/acceptance.py` ⇒ `B20F2 acceptance: PASS（35 项检查）`
- 门禁：`harness/scripts/gates/gate_G25_import_graph.py` ⇒ `[G25] PASS`；`pytest -q tests/gates` ⇒ `42 passed`。
- 只读文件：`git diff --exit-code -- harness/demo/target.py pyproject.toml THIRD_PARTY_NOTICES specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt` ⇒ 退出码 `0`。

## 2. 验证步骤

1. 用同一组 `Span` / `TraceRecord` 分别写入 `FileTraceStore` 与 `SqliteTraceStore`。
2. 覆盖四类过滤（`run_id` / `thread_id` / 时间 / `node`）与 AND 组合。
3. 验证空过滤器、稳定排序、`json.dumps`、独立副本。
4. 验证 JSONL 坏行 / 未知 `kind` / 非白名单 / 符号链接容错。
5. 验证 SQLite 单行 payload 损坏 / 不兼容旧表 / 损坏库。
6. 并发写 + 查询（线程；跨进程由 pytest 用例覆盖；Windows 由 CI 分支覆盖）。
7. 零出站：socket 监测夹具断言「框架出站 == 0」。
8. 冻结面追认：`observability.__all__` 只增 `SqliteTraceStore`；B20F1「无查询方法」断言拆分而不删。

## 3. 实际输出

### 3.1 四类过滤与组合

```text
run_id=run-A: 4
thread_id=t-2: 2
time[T1,T1]: ['am', 'am']
node=a: ['a']
combo: 4
```

### 3.2 空过滤器 / 排序

```text
empty count: 6
order: [('trace_record', 'a1'), ('span', 'a1'), ('trace_record', 'am'), ('span', 'am'), ('trace_record', 'b1'), ('span', 'b1')]
```

同一有效起始时刻：`trace_record` 先于 `span`；平局按 `run_id` / 稳定标识打破。

### 3.3 JSON 可序列化 / 两后端等价

```text
json.dumps: True
parity: True
```

### 3.4 容错

```text
tolerance count (bad file adds 0): 6
```

坏 JSON 行 / 未知 `kind` 被跳过并产生 `logging.WARNING`，其余行照常返回。

### 3.5 并发写 + 查询

```text
concurrency rows: 20 write_errors: 0
```

Windows 说明：并发写 + 查询用例带 `skipif(os.name != "nt")` 显式分支；Windows CI 会执行真实并发用例（`tests/observability/test_b20f2_sqlite_concurrency.py`）。

### 3.6 零出站

```text
egress calls: 0
```

### 3.7 冻结面 / B20F1 断言追认

```text
observability.__all__: ['FileTraceStore', 'SpanProducer', 'SqliteTraceStore', 'TraceRecord', 'current_span', 'invoke_model', 'invoke_tool']
B20F1 query allowed: True
```

追认：`observability.__all__` **只增** `SqliteTraceStore`；B20F1 的「`FileTraceStore` 公开面没有查询方法」断言按 **拆分而不删** 处理（写侧 4 方法 / 2 诊断 / 无生命周期断言保留；`queries` 期望更新为 `["query"]`）。

### 3.8 一键验收

```text
[PASS] A1 按 run 检索
[PASS] A2 按 thread 检索
[PASS] A3 时间窗命中
[PASS] A4 按节点名检索
[PASS] A5 四类过滤组合命中
[PASS] A6 两后端等价 ...
[PASS] 零出站：查询无网络调用
B20F2 acceptance: PASS（35 项检查）
```

## 4. 结论

- A1–A6 全部通过；四类过滤 / 组合 / 空过滤器 / 稳定排序 / 两后端逐条等价均已实测。
- 查询只读：不创建 / 改写存储；缺失存储返回 `[]`；坏行 / 未知 `kind` / 字段残缺跳过 + WARNING。
- SQLite 写侧与 B20F1 同语义：开始快照 no-op、`run_id` allowlist、四路诊断、不重试、每实例锁。
- 零出站 / 零环境变量 / 零第三方依赖。

### 4.1 质量门禁 5 偏离声明

| 项 | 内容 |
|---|---|
| 被偏离门禁 | 质量门禁 5「人工验证记录，含真实模型一轮」 |
| 根因 | B20F2 是 L5 本地 trace 读取层 + SQLite 后端；验收对象是过滤语义 / 排序 / 后端等价 / 并发读写，真实模型轮不产生本 feature 的新判据。**沿用 B20F1（2026-11-21 · 发起者选择 A）先例**；判据未放宽。 |
| 判据未放宽 | 四类过滤、组合、空过滤器、排序、`json.dumps`、两后端等价、零出站、零 env、写侧回归等判据一字未改。 |
| 承接方 / 机制 | **B25F1（M4 · 双跑验收）** 补真实模型轮（含 `SqliteTraceStore` / `FileTraceStore` 查询证据；承接条款见 `harness/features/B25F1_双跑验收与迁移说明.md` §「下游承接（B20F2）」，由 T058 守卫）。 |
| 发起者追认 | **已追认（2026-11-21）**：本人已审阅上述质量门禁 5 偏离登记，同意 B20F2 只交付 fake / 本地轮证据，真实模型轮由 **B25F1（M4）** 承接。确认人：**杨家成（发起者）** · 日期：**2026-11-21** |

### 4.2 最终审计（T056）

- FR-001…FR-034 / SC-001…SC-018 均有执行任务；tasks 正反向追溯 **0 / 0** 差异。
- 红名单 B-1…B-13：B-1/B-2/B-3/B-4/B-5 按「只增 / 拆分而不删」更新；其余保持绿（全量 `2111 passed / 8 skipped`，新增 1 个 Windows 分支 skip）。
- P-01…P-07 / D-501…D-508 / X-1…X-8 三态一致；**P-04 / D-503 不标 SAME 行为面**。
- T058：B25F1 §「下游承接（B20F2）」存在，覆盖 `FileTraceStore` / `SqliteTraceStore` 两后端 `query()` 证据。
- 范围守卫：未实现 OTLP / UI / Agent Server / Postgres / retention / eval / `checkpoint_id` 过滤 / 分页。
- schema / 表名 / 列名 / SQL / JSONL 文件格式均为内部实现细节，无公开泄漏。
- 质量门禁 5 偏离已登记并由发起者追认（§4.1）。

### 4.3 验收签署

- 结论：**通过**（A1–A6；全量 `2111 passed / 8 skipped`；G25 PASS；`tests/gates` 42 passed；只读文件 diff 为空）。
- 验收人：**杨家成（发起者）** · 日期：**2026-11-22**。

## 5. 遗留问题

- 不实现 OTLP 导出（B21F1）、前端 / UI（v2 / B26）、本地 Agent Server（v2 / D8）、Postgres 后端（v2）。
- v1 不分页 / 不设上限；调用方需自行控制存储规模。
- SQLite schema 无 `user_version` / 迁移；不兼容旧表返回 `[]` + WARNING，不自动修复。
- 真实模型轮由 B25F1 承接（见 §4.1）。
