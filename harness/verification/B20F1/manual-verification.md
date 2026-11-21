# B20F1 · 人工验证记录（本地 Trace 存储：JSONL 文件后端）

**Feature**: B20F1 · **日期**: 2026-11-21 · **实现者**: 自动化实现轮次（OpenCode / speckit.implement）

## 1. 验证环境

| 项 | 值 |
|---|---|
| 仓库 | `freegraph` |
| 提交 | `ebd1009` |
| Python | CPython **3.11.16**（`.venv`） |
| pytest | 9.2.0 |
| 平台 | Linux |
| 网络 / 账号 | 不设 `LANGSMITH_*` / `LANGCHAIN_*`；不使用任何外部服务 / API key |
| 基线 | **1917 passed, 6 skipped**（实施前，`/speckit.plan` 记录） |

### 1.1 基线

实施前按 `plan.md` 记录的基线：

```text
.venv/bin/python -m pytest -q --tb=no
1917 passed, 6 skipped in 112.86s
```

## 2. 验证步骤

1. 运行 B20F1 定向测试（observability / contracts / differential）；
2. 运行一键验收脚本 `harness/verification/B20F1/acceptance.py`（A1–A5）；
3. 逐行读回生成的 JSONL，确认字段 / 编码 / 关联键；
4. 对不可写路径运行图，确认不阻断 + 四路诊断；
5. 在未注入 / 只构造 / 设置 env 变量三种情况下确认零痕迹；
6. 运行全量回归。

## 3. 实际输出

### 3.1 JSONL 样例行

```json
{"kind": "trace_record", "span_id": "048225e734fd4006ae633d8c1406283c", "task_id": "a", "run_id": "067cfa8ad2fd44f3b780873ffc1d68fe", "thread_id": null, "checkpoint_id": null, "node": "a", "superstep": 0, "triggers": [["e", "__start__"]], "concurrency_group": ["a"], "barrier_groups": [], "input_state": {"x": 0}, "output_state": {"x": 1}, "error": null}
{"kind": "span", "id": "048225e734fd4006ae633d8c1406283c", "name": "a", "attributes": {}, "parent": null, "start_time": "2026-11-21T14:48:59.489525494+00:00", "end_time": "2026-11-21T14:48:59.490626751+00:00", "context": {}, "thread_id": null, "run_id": "067cfa8ad2fd44f3b780873ffc1d68fe", "node": "a", "checkpoint_id": null}
{"kind": "trace_record", "span_id": "935e0d98f6284f4aaedcf2889f44628f", "task_id": "b", "run_id": "067cfa8ad2fd44f3b780873ffc1d68fe", "thread_id": null, "checkpoint_id": null, "node": "b", "superstep": 1, "triggers": [["e", "a"]], "concurrency_group": ["b"], "barrier_groups": [], "input_state": {"x": 1}, "output_state": {"x": 2}, "error": null}
{"kind": "span", "id": "935e0d98f6284f4aaedcf2889f44628f", "name": "b", "attributes": {}, "parent": null, "start_time": "2026-11-21T14:48:59.498175197+00:00", "end_time": "2026-11-21T14:48:59.499251591+00:00", "context": {}, "thread_id": null, "run_id": "067cfa8ad2fd44f3b780873ffc1d68fe", "node": "b", "checkpoint_id": null}
```

### 3.2 `json.loads` 读回

```text
file= trace-f6f9e0b4eb564bd9a1478a2e3a94987e.jsonl
lines= 4
kinds= {'trace_record': 2, 'span': 2}
c23_all= True
span_fields= ['attributes', 'checkpoint_id', 'context', 'end_time', 'id', 'kind', 'name', 'node', 'parent', 'run_id', 'start_time', 'thread_id']
```

### 3.3 一键验收（A1–A5）

```text
.venv/bin/python harness/verification/B20F1/acceptance.py
[PASS] A1 每个 run 一个 trace-<run_id>.jsonl
[PASS] A1 含 span 行
[PASS] A1 含 record 行
[PASS] A1 两个节点 span
[PASS] A1 两个节点 record
[PASS] A2 框架出站 == 0
[PASS] A3 每行是 JSON 对象
[PASS] A3 含 C23 四项
[PASS] A3 每行是 JSON 对象
[PASS] A3 含 C23 四项
[PASS] A3 每行是 JSON 对象
[PASS] A3 含 C23 四项
[PASS] A3 每行是 JSON 对象
[PASS] A3 含 C23 四项
[PASS] A4 写入失败不阻断图执行
[PASS] A4 write_errors > 0
[PASS] A4 last_error 非空
[PASS] A4 on_error 每次失败调用一次
[PASS] A4 logging.WARNING 出现
[PASS] A4 无 trace 文件产生
[PASS] A5 未注入 ⇒ 零目录 / 零文件
[PASS] A5 只构造 ⇒ 零目录 / 零文件
[PASS] A5 env 不开启观测
B20F1 acceptance: PASS（23 项检查）
```

### 3.4 失败感知证据

```text
result= {'x': 1}
write_errors= 2
last_error= FileExistsError: [Errno 17] File exists: '/tmp/.../occupied'
on_error_calls= 2
WARNING: trace write failed: FileExistsError: [Errno 17] File exists: '/tmp/.../occupied'
```

- 图正常返回 `{'x': 1}`，异常传播数 **0**；
- `write_errors` / `last_error` / `on_error` / `logging.WARNING` 四路均可感知；
- 目录不可写时未产生 `trace-*.jsonl`。

### 3.5 零出站证据

一键验收 A2 使用 socket 监测夹具（只观测、不阻断）：**框架出站 == 0**。  
B20F1 的 `_file_store.py` 不含 `socket` / `http` / `urllib` / `requests` / `httpx` / `subprocess` import，也不读取环境变量。

### 3.6 `observability.__all__` 更新追认

B19F1 的精确集合断言已**只增** `FileTraceStore`：

```text
{"FileTraceStore", "SpanProducer", "TraceRecord", "current_span", "invoke_model", "invoke_tool"}
```

既有 5 符号逐字保留；`trace_run_scope` 仍不导出；`FileTraceStore` 不进 `freegraph.graph` / `freegraph.runtime.__all__`。

### 3.7 README 形态锁定

`harness/demo/README.md` 的「本地 trace 存储目录的参数名」已标为：

```text
已锁定（B20F1）：FileTraceStore(directory=...)
```

### 3.8 定向测试与全量回归

```text
# B20F1 定向测试（observability + contracts + differential + runtime guard + acceptance）
72 passed, 1 skipped in 2.75s

# 全量回归
.venv/bin/python -m pytest -q --tb=no
1991 passed, 7 skipped in 109.72s
```

- 基线 **1917 passed / 6 skipped** ⇒ 全量 **1991 passed / 7 skipped**（**+74 passed**；
  新增的 1 个 skip 是 Windows-only 权限分支，POSIX 档不适用）；
- 既有测试**零退化**。

### 3.9 门禁与只读文件

```text
.venv/bin/python -m pytest tests/gates -q
42 passed in 23.46s

.venv/bin/python harness/scripts/gates/gate_G25_import_graph.py
[G25] PASS —— 导入图单向（ARCH-1 · 层注册表驱动）

git diff --exit-code -- harness/demo/target.py pyproject.toml THIRD_PARTY_NOTICES \
  specs/b2f2-public-api-facade/contracts/public-api-snapshot.txt
EXIT=0
```

## 4. 结论

- A1–A5 全部通过；B20F1 定向测试全绿；
- 写入失败不阻断，四路诊断可用；JSONL 每行可独立 `json.loads`；
- 未注入 / 只构造 / env 变量场景零文件零目录；
- 零出站、零环境变量、零第三方依赖；
- `Span` / `TraceSink` / `TraceRecord` / `RunConfig` / `SuperStepResult` / `PregelTask` 字段面零改动。

### 4.1 质量门禁 5 偏离声明

| 项 | 内容 |
|---|---|
| 被偏离门禁 | 质量门禁 5「人工验证记录，含真实模型一轮」 |
| 根因 | B20F1 是 L5 本地 JSONL 写入层，不交付模型 provider；真实模型轮不产生本 feature 的新判据 |
| 判据未放宽 | 本地图 + 本地 sink 的 fake / 本地轮照常；JSONL 字段、四路诊断、零出站、默认关闭、`0o600`、per-instance 锁、逐行短生命周期**一字未改** |
| 承接方 / 机制 | **B25F1（M4 · 双跑验收）** 补真实模型轮（含 `FileTraceStore` 落盘证据）；承接条款已写入 `harness/features/B25F1_双跑验收与迁移说明.md` §「下游承接（B20F1）」 |
| 发起者追认 | **已追认（2026-11-21）**：本人已审阅上述质量门禁 5 偏离登记，同意 B20F1 只交付 fake / 本地轮证据，真实模型轮由 **B25F1（M4）** 承接。确认人：**杨家成（发起者）** · 日期：**2026-11-21** |

> 说明：本 feature 的 fake / 本地轮证据已齐备；真实模型轮按登记偏离由 B25F1 承接。
> 追认依据：发起者在本轮验收中的明确授权（「人工验收通过…该签的就签」）。

## 5. 遗留问题

- `checkpoint_id` 在未挂 checkpointer 时仍为 `null`（C23 允许）；
- 本 feature 不提供查询 API（归 B20F2）、SQLite 后端（B20F2）、OTLP（B21F1）、UI（v2 / B26）；
- 不实现保留期 / 清理 / 轮转；
- 跨进程并发写同一文件不在 v1 承诺（SQLite 场景归 B20F2）；
- v1 `StateGraph` 不允许「没有节点」的图；无 span 的等价场景由「store 未收到任何回调」覆盖；
- 质量门禁 5 偏离已由发起者追认（2026-11-21，见 §4.1）。
