# B19F1 · `TraceSink` 接入 + `current_span()` + 默认关闭 —— 人工验证记录

## 1. 验证环境

- 日期：2026-11-21
- Python：3.11.16（Linux x86_64）
- 仓库：`freegraph`（`/home/ctyun/workspace/github/freegraph`）
- 上游取证版本：`langgraph 1.2.11` / `langchain-core 1.7.6` / `langsmith 0.14.17`
- 运行时依赖：**空集**（`pyproject.toml` 未改动）
- 零环境变量 / 零主动出站：新模块静态扫描 + 动态 socket 监测（框架出站 == 0）

### 1.1 基线

```text
.venv/bin/python -m pytest -q --tb=no
1863 passed, 6 skipped in 112.61s (0:01:52)
```

实施后最终全量回归：

```text
.venv/bin/python -m pytest -q --tb=short
1917 passed, 6 skipped in 117.05s (0:01:57)
```

## 2. 验证步骤

1. **默认关闭 / 零副作用**：不传 `tracer`、显式 `tracer=None`、以及
   `compile(tracer=sink)` 但从不运行；断言 `Span` / `SpanProducer` / record /
   `bind_run_ids` 计数均为 0。
2. **注入即推送**：`compile(tracer=sink)` 跑 `a → b`；断言节点 span 成对、
   `id` 相同、`end_time` 非空、`run_id` 非空、`thread_id` 来自 `RunConfig`。
3. **异常路径**：节点抛 `RuntimeError`；断言 span 仍成对、原异常对象原样重抛；
   `FailingSink` 的回调异常被隔离。
4. **嵌套 / `current_span()`**：模型 → 工具 → 模型三层嵌套；断言父链逐层正确，
   内层结束后恢复外层，空上下文返回 `None`。
5. **流式 id**：`stream()` 事件与 `TraceSink` span 的 `(run_id, thread_id)` 逐字相同；
   信封不含 trace 字段。
6. **补充 trace 记录**：触发源覆盖静态边 / `Command.goto` / `Send` fan-out；
   并发组 / 屏障组 / `superstep` / `input_state` / `output_state` / `error` 可判定；
   `json.dumps(record.to_jsonable())` 不抛。
7. **中断 / 取消**：中断节点 `error` = 原 `GraphInterrupt`；节点自身
   `CancelledError` 保留原对象；`record 数 == 节点 span 数`。
8. **嵌套 compiled graph**：B19F1 作用域内层未注入 ⇒ 0 span / 0 record；
   内层注入 ⇒ 独立 `run_id`、顶层 `parent is None`；作用域外 B18F1 直接绑定保持；
   作用域内直接绑定按 B19F1 作用域优先被屏蔽。
9. **门禁**：G21 / G23 / G24 / G25 / G26 / G27 全绿；G27 框架出站 == 0
   （用户出站 2 条记录在案，不判失败）。

### 2.1 一键验收

```bash
.venv/bin/python harness/verification/B19F1/acceptance.py
# B19F1 acceptance: PASS（31 项检查）
```

### 2.2 自动化测试落点

- `tests/observability/test_b19f1_push.py` / `test_b19f1_exception.py` /
  `test_b19f1_stream.py` / `test_b19f1_current_span.py` /
  `test_b19f1_callback_span.py` / `test_b19f1_default_off.py` /
  `test_b19f1_record.py` / `test_b19f1_json_safe.py`
- `tests/runtime/test_b19f1_nested_scope.py` / `test_b19f1_alignment.py` /
  `test_b19f1_triggers.py` / `test_b19f1_concurrency_barrier.py` /
  `test_b19f1_invoke_records.py`
- `tests/contracts/test_b19f1_contracts.py` / `test_b19f1_gates.py` /
  `test_b19f1_lazy.py`
- `tests/runtime/test_acceptance_script.py::test_b19f1_one_click_acceptance_script_passes`
- `tests/differential/test_b19f1_trace_access_parity.py`（D-301 / D-302 / D-304 /
  D-305 / D-307 / D-310；上游缺席即 skip）

## 3. 实际输出

- 最终全量回归：**1917 passed, 6 skipped**（基线 1863 + 新增 54）。
- 新增 B19F1 定向测试：**54 passed**（含差分 10 + 一键验收守卫 1）。
- G21 依赖闭包：PASS；G23 许可证：PASS；G24 零环境变量：PASS；
  G25 导入图单向：PASS；G26 网络静态：PASS；G27 零出站动态：PASS
  （框架出站 0 / 用户出站 2 记录在案）。
- `git diff --exit-code -- harness/demo/target.py pyproject.toml THIRD_PARTY_NOTICES`：退出码 0。
- `import freegraph` 后 `sys.modules` 不含 L5 / `opentelemetry` / `langchain*` / `langsmith`。

## 4. 结论

- B19F1 的 FR-001…FR-021 / SC-001…SC-017 均由上述测试覆盖并通过。
- 嵌套 span 父子关系正确；未注入 / 无外层 tracer 时零副作用；补充记录与节点
  span 一一对齐。
- **R-1 / R-2 / R-3 一次性追认（确认人：杨家成 · 日期：2026-11-21）**：
  - R-1：仅 `_stategraph.py` → `observability/_inject.py`（tracer 接线 / 屏蔽）；
  - R-2：仅 `_inject.py` → `runtime/_span_hook.bind_span_tracer`，**不读** `_stream_context`；
  - R-3：B18F1 的「L5 只 import 标准库 + L1」断言拆分而不删。
- **B8F2 R-6 已收窄**：L2 `_run_round` 读取 stream id，B19F1 从节点 start `Span` 继承。
- **质量门禁 5 偏离登记（确认人：杨家成 · 日期：2026-11-21）**：本 feature 不依赖外部
  模型 provider；验收采用 fake 轮 + 本地真实 `TraceSink` 轮；真实模型轮由 **B21F1** 承接。
  MUST NOT 伪装成已通过。

## 5. 遗留问题

- `checkpoint_id` 仍为 `None`（B18F1 Q5 现状；B14F1 / B15F1 后续补）。
- 跨 compiled graph 的 trace 树统一留 v2 / C26；本 feature 仅保证各产物独立。
- `CompiledGraph` 新增私有 `_tracer` ⇒ `vars(compiled)` 由 11 变 12（只增）；
  已同步更新 B7F2 / B7F3 / B8F1 / B8F2 / B23F1 相关断言与验收脚本。

## 6. 红名单（B-1…B-10）逐条核对

| # | 项目 | 结果 |
|---|---|---|
| B-1 | B18F1「L5 只 import 标准库 + L1」断言 | ✅ 拆分而不删；新增 `_inject.py` 例外断言（`tests/contracts/test_architecture.py`） |
| B-2 | 层注册表 / G25 的 L3 → L5 方向 | ✅ R-1 已登记 `trace-wiring-L3-L5`；G25 PASS |
| B-3 | API 快照 | ✅ 已更新（`compile` 新增 keyword-only `tracer`）；无参可调用 |
| B-4 | `runtime.__all__` 符号数 | ✅ 仍 23 |
| B-5 | C4 / C8 回归 | ✅ 全量回归通过 |
| B-6 | `stream()` 的 `run_id` / `thread_id` | ✅ 全量回归通过；B19F1 stream 测试同 id |
| B-7 | 依赖 / 环境变量 / 出站门禁 | ✅ G21 / G24 / G26 / G27 PASS |
| B-8 | B18F1 直接绑定测试 | ✅ 全量回归通过；作用域外直接绑定回归 + 作用域内屏蔽测试通过 |
| B-9 | Phase 3 US1 的 record 断言 | ✅ T017 只测 span / id / stream 信封；record 断言在 Phase 6 |
| B-10 | `vars(compiled)` 11 → 12 | ✅ 新增私有 `_tracer`；测试 / B8F1 / B7F2 验收脚本已同步 |

## 7. 签署

- 人工验收结论：**PASS**
- 一键验收：`B19F1 acceptance: PASS（31 项检查）`
- 全量回归：`1917 passed, 6 skipped`
- 确认人：杨家成
- 日期：2026-11-21
- 说明：R-1 / R-2 / R-3 一次性追认与质量门禁 5 偏离登记均已于本记录 §4 签字；
  本 feature 满足合入条件。
