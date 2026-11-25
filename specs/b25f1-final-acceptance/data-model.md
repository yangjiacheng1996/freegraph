# Data Model: B25F1 · 双跑验收 + 迁移说明 + README 收口

**Date**: 2026-11-25 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

> 本 feature **不引入运行时数据结构**。下列实体是**验收材料 / 证据 / 文档**的数据模型，
> 用于把 spec 的实体与验收规则落成可判定的形状。所有瞬时数据（trace / checkpoint）
> 只写入临时目录，**不进入仓库**。

---

## 1. 实体总览

| 实体 | 载体 | 作用 |
|---|---|---|
| `FixedScriptBaseline` | `tests/runtime/data/b25f1_target_py.sha256` + git ref | 固定脚本只读基准 |
| `FakeInjection` | `harness/verification/B25F1/fake_model.py` | fake 模型与注入入口 |
| `FakeSequence` | fake 模型返回值 | 固定 2 轮输出 |
| `FakeRoundResult` | `fake_round.py` / 测试 | A1 的四条断言点 |
| `EgressRecord` | 监测夹具 / 记录 | 框架出站 / 用户出站 |
| `AcceptanceRun` | `harness/verification/B25F1/acceptance.py` | 一键验收的步骤与结论 |
| `ManualVerificationRecord` | `harness/verification/B25F1/manual-verification.md` | 五要素 + 三附件 |
| `RealRoundEvidence` | `real_round.py` 输出 / 记录 | 两段式真实轮证据 |
| `TraceEvidence` | 临时 JSONL / SQLite 查询结果 | B20F1 / B20F2 承接证据 |
| `OtlpEvidence` | 记录型 exporter / 本地接收端 | B21F1 承接证据 |
| `CheckpointEvidence` | `SqliteSaver` 读回结果 | B15F1 / B16F1 承接证据 |
| `MigrationGuide` | `harness/proposals/更名与迁移说明.md` | 三类迁移 + Y-01 |
| `ReadmeDoc` | `README.md` | 三条承诺 + 能力表 + 绝对链接 |
| `DiagnosticsCase` | `harness/demo/diagnostics.py` | trace / checkpoint / 时间旅行 |
| `ModelFactorySpec` | `tests/differential/spec_builder.py` | 模型形状图规格 |

---

## 2. `FixedScriptBaseline`（固定脚本只读基准）

| 字段 | 类型 | 规则 |
|---|---|---|
| `path` | `"harness/demo/target.py"` | 仓库内只读基准 |
| `sha256` | `str`（64 hex） | 来自 `tests/runtime/data/b25f1_target_py.sha256` |
| `baseline_ref` | `str` | 默认 `origin/main`；可由 `B25F1_BASELINE_REF` 覆盖 |
| `sha_match` | `bool` | 当前文件内容哈希 == `sha256` |
| `ref_diff_empty` | `bool \| None` | `git diff <baseline_ref> -- target.py` 为空；不可判定 ⇒ `None` |
| `ref_status` | `"ok" \| "unavailable" \| "not_git"` | 基线 ref 的可用性 |

**校验（FR-011 / A5）**：

- `sha_match == True` ⇒ 内容真值通过；否则 **失败**。
- `ref_diff_empty == True` ⇒ 历史真值通过；`None` ⇒ **环境偏离**（记录原因），但仍保留 SHA 断言；
  `False` ⇒ **失败**。
- **MUST NOT** 只依赖 `git diff HEAD`；已提交篡改必须由基线 ref 发现。
- 任何格式化 / 换行 / 注释改动都会改变 SHA ⇒ **失败**。

---

## 3. `FakeInjection` / `FakeSequence`（fake 注入与固定序列）

| 字段 | 类型 | 规则 |
|---|---|---|
| `factory_target` | `"langchain.chat_models.init_chat_model"` | 猴补目标（测试 / 验收层） |
| `mode` | `"in_process" \| "subprocess_sitecustomize"` | 两条等价注入路径 |
| `model` | `FakeModel` | 实现 `bind_tools()` / `invoke()` |
| `sequence` | `list[FakeTurn]` | **恰好 2 轮**；第 3 次调用 ⇒ 显式失败 |
| `patched_before_import` | `bool` | MUST 为 `True`（`target.py:23` 导入前） |

**`FakeTurn`**：

| 字段 | 第 1 轮 | 第 2 轮 |
|---|---|---|
| `content` | `""`（或占位文本） | 最终文本答案（与「Add 3 and 4.」对齐） |
| `tool_calls` | `[{name: "add", args: {"a": 3, "b": 4}, id: "call_1"}]` | `[]` |
| `message_type` | `AIMessage` | `AIMessage` |

**校验（FR-001 / FR-002 / FR-003 / H-1）**：

- fake **必须**产生 `tool_calls`；只产出文本 ⇒ **失败**（退化为「单轮无工具」）。
- `tool_call.id` 必须与 `ToolMessage.tool_call_id` 一致。
- 注入**只替换模型对象**；`should_continue` 仍读 `state["messages"][-1].tool_calls`
  ⇒ 路由函数语义不变（正交）。
- 注入代码 **MUST NOT** 进入 `src/freegraph/`。

---

## 4. `FakeRoundResult`（A1 的四条断言点）

| 字段 | 类型 | 期望 |
|---|---|---|
| `messages_len` | `int` | **4**（Human + AI(tool_call) + ToolMessage + AI final） |
| `llm_calls` | `int` | **2** |
| `tool_result` | `Any` | **7**（`add(3, 4)`；`ToolMessage.content` 实测为 `"7"` ⇒ 断言**归一为 int**） |
| `state_keys` | `set[str]` | 含 `messages` 与 `llm_calls` |
| `final_message` | `Any` | 第 2 轮最终 AIMessage |
| `png_bytes` | `bytes` | `draw_mermaid_png()` 的实际返回 |
| `png_signature_ok` | `bool` | PNG 结构判据（签名 / IHDR 等） |
| `framework_egress` | `int` | **0** |
| `user_egress` | `list[EgressRecord]` | 任意；只记录 |

**校验**：任一硬断言不成立 ⇒ `FakeRoundResult.ok == False` ⇒ 退出码 1。

---

## 5. `EgressRecord`（出站监测）

| 字段 | 类型 | 规则 |
|---|---|---|
| `target` | `str` | `host:port` 或等价目标 |
| `attribution` | `"framework" \| "user"` | **第一个非标准库帧**在 `freegraph/` ⇒ framework；否则 user |
| `frames` | `list[Frame]` | 最近的若干帧（模块 / 路径） |
| `blocked` | `bool` | **恒 `False`**（只观测不阻断） |

**校验（FR-004 / A3）**：

- `attribution == "framework"` 的条目数 MUST == **0**。
- `attribution == "user"` 的条目**逐条记录**；任意目标、任意条数；**不判失败**；
  **MUST NOT** 做目标白名单校验（通用型图框架）。
- 监测夹具 MUST NOT 阻断连接（`blocked == False`）。

---

## 6. `AcceptanceRun`（一键验收）

| 字段 | 类型 | 规则 |
|---|---|---|
| `steps` | `list[AcceptanceStep]` | 顺序执行 |
| `exit_code` | `int` | `0` / `1` / `2` |
| `verdict` | `"PASS" \| "FAIL" \| "NOT_READY"` | 由 `exit_code` 映射 |
| `real_round_ran` | `bool` | `--real` 时为 `True`；`--skip-real` 时为 `False` |
| `record_path` | `str \| None` | `--record` 的输出路径 |
| `env_deviations` | `list[str]` | 环境偏离（原因 + 范围） |

**`AcceptanceStep`**：

| `id` | 内容 | 失败语义 |
|---|---|---|
| `A1` | fake 轮 + 四条断言点 | `exit 1` |
| `A2` | 真实轮两段式（`--real`） | `exit 1`；未跑 ⇒ 保持 `real_round_ran=False` |
| `A3` | 框架出站 = 0 | `exit 1` |
| `A4` | 四组（含 diagnostics；`harness/demo/acceptance.py`） | `exit 1`；缺组 ⇒ `exit 1` |
| `A5` | 双重基线 | `exit 1`；基线 ref 不可用 ⇒ `env_deviations` |
| `DEP` | 依赖断言 + 反向断言 | `exit 1` |

**状态转换**：

```text
start → 环境检查
  ├─ 缺 freegraph / langchain / IPython / 真实模型（仅 --real） → NOT_READY (2)
  ├─ A1/A3/A4/A5/DEP 全过 →
  │     ├─ --real 且 A2 过 → PASS (0)
  │     ├─ --skip-real → PASS (0)  [CI]
  │     └─ --real 且 A2 失败 → FAIL (1)
  └─ 任一自动断言失败 → FAIL (1)
```

---

## 7. `ManualVerificationRecord`（人工验收记录）

| 章节 | 必须内容 |
|---|---|
| **1. 验证环境** | OS / Python / 依赖 / 环境变量清理方式（含 `LANGSMITH_*` 清空）/ 接入路径 |
| **2. 验证步骤** | fake 轮、真实轮（两段）、四组（含 diagnostics）、双重基线、断网、依赖断言；**发布前清单纳入 B14F1 的 `harness/verification/B14F1/manual-verification.md` 与 `harness/verification/B14F1/acceptance.py`** |
| **3. 实际输出** | 每条命令 / 断言的真实输出（非「符合预期」） |
| **4. 结论** | 双跑 / 零出站 / 脚本集 / 只读基准 / 文档 |
| **5. 遗留问题** | 逐条；含 **Y-01** 的 v1 行为提示 |

**三附件**：

1. 依赖断言轮输出（`Requires-Dist` / `pip freeze` / 运行时 `sys.modules` 反向断言）；
2. 「框架出站 = 0」监测记录（框架 0；用户出站逐条）；
3. 反向断言结果（运行时无 `langchain` / `langchain_core`）。

**校验（FR-008 / SC-004）**：

- 五要素齐备且正文非空；三附件齐备；
- 真实轮证据含 B15/B16/B20/B21/B23/B24 的非空实测输出；
- **含 B14F1 的 `harness/verification/B14F1/manual-verification.md` 与
  `harness/verification/B14F1/acceptance.py` 引用**（FR-019）；
- **含接入路径**（官方直连 / 兼容网关；gateway 不得写成官方直连）；
- 环境偏离须写明「已完成 / 未完成 / 原因」；
- **MUST NOT** 回改既有 feature 的记录；
- 常驻 CI 在记录未收口 / 仅有环境偏离时守卫 `skip`；T052 的严格断言**仅在发布 / 人工门禁执行**（宪法 v1.13.0）。

---

## 8. `RealRoundEvidence`（真实轮两段式）

| 字段 | 段 1（固定脚本） | 段 2（专用探针） |
|---|---|---|
| `model_id` | `claude-sonnet-4-6`（脚本硬编码） | 同一模型 / 环境显式配置 |
| `endpoint` | 实际连接目标 | 同一接入 |
| `access_path` | `"official" \| "gateway"` + 原因 | 同 |
| `final_message` | 实际最终消息 | 实际最终消息 |
| `tool_result` | 实际工具结果 | 实际工具结果 |
| `png_bytes` / `png_signature_ok` | 实测 | — |
| `framework_egress` | **0** | **0** |
| `user_egress` | 逐条记录（可任意目标） | 逐条记录 |
| `trace` | — | `TraceEvidence` |
| `otlp` | — | `OtlpEvidence` |
| `checkpoint` | — | `CheckpointEvidence` |
| `time_travel` | — | 重放 / 分叉 / 中断组合的实际输出 |

---

## 9. `TraceEvidence`（B20F1 / B20F2）

| 字段 | 规则 |
|---|---|
| `file_count` | `FileTraceStore` 写出的 `trace-*.jsonl` 文件数 |
| `span_lines` | `kind="span"` 行数 |
| `trace_record_lines` | `kind="trace_record"` 行数 |
| `model_span_parent` | 模型 span 的 `parent` 指向节点 span |
| `correlation_keys` | C23 四项关联键存在 |
| `query_results` | 四类过滤（`run_id` / `thread_id` / `node` / 时间窗）+ 组合 + 空过滤器的条数 |
| `json_serializable` | `json.dumps(rows)` 成功 |

**校验**：两个后端（JSONL / SQLite）各跑**一次独立真实模型运行**，使用同一
`RunConfig(thread_id="b25f1-real")` 并捕获 `run_id` / 起止时间；同一 `TraceQuery` 结果**逐条相等**
（B20F2 证据）。

---

## 10. `OtlpEvidence`（B21F1）

| 字段 | 规则 |
|---|---|
| `mode` | `"exporter"`（默认记录型）或 `"endpoint"`（本地 gRPC 接收端） |
| `recording_exporter` | `real_round.py` 内定义的 `RecordingSpanExporter`（官方 `SpanExporter` 最小实现，记录到内存、无网络） |
| `span_count` | 接收到的 span 数（> 0） |
| `names` | span `name` 列表 |
| `trace_ids` | `trace_id` 列表 |
| `parents` | 父子关系 |
| `gen_ai_attributes` | `gen_ai.*` 属性存在 |

**校验**：用户显式启用的 OTLP 端点**不计入框架出站**；记录中写明模式与接收端。

---

## 11. `CheckpointEvidence`（B15F1 / B16F1）

| 字段 | 规则 |
|---|---|
| `get_tuple` | 持久化往返（写后读回） |
| `get_state` | 当前快照 / 无快照 ⇒ `None` |
| `get_state_history` | 历史数量、倒序 |
| `stream_checkpoints` | 事件数与 payload |
| `tasks` / `interrupts` | 形状 / 关联 |
| `replay` | `invoke(None, snapshot.config)` 的实际结果 |
| `update_state` | 覆盖 / 归约 / `as_node` 的实际结果 |
| `fork_history_unchanged` | 分叉后原历史不变（`True`） |
| `interrupt_combo` | 中断 + 恢复 + 历史组合的实际结果 |

---

## 12. `ModelFactorySpec`（B5F2 / B25F1）

| 字段 | 纯本地规格 | 模型形状规格 |
|---|---|---|
| `builder` | `build_graph_spec(...)` | `build_model_graph_spec(...)` |
| `model_factory` | **必须为空**；非空 ⇒ `GraphSpecError` | **必须非空**；空 ⇒ `GraphSpecError` |
| 用途 | B5F2 既定差分 | B25F1-D-04 |

**校验（FR-018 / SC-006）**：

- 既有 `build_graph_spec` 的纯本地拒绝语义**不变**；B5F2 的
  `test_a_non_empty_model_factory_is_an_explicit_failure` 仍绿；
- `build_model_graph_spec` 的模型形状规格能被差分夹具执行；
- **MUST NOT** 让模型形状规格「恒空即通过」。

---

## 13. `MigrationGuide` / `ReadmeDoc`（文档）

**`MigrationGuide`**：

| 字段 | 规则 |
|---|---|
| `same_name` | 同名直接可用的 API 列表 |
| `same_name_diff` | 同名但行为有差异（含 **Y-01** / Y-02 / Y-03） |
| `needs_rewrite` | 需改写的调用（`langchain` 层 / 需换包名） |
| `compat_link` | 指向 `COMPAT.md` 的链接 |
| `y01_hint` | `Command.goto` 缺省 `()` vs `None` 的 v1 行为提示 |

**`ReadmeDoc`**：

| 字段 | 规则 |
|---|---|
| `quickstart` | 安装 / 最小图 / `[otlp]` / fake / 真实轮入口 |
| `promises` | 零账号（含零 license key）/ 零出站 / 零第三方运行时依赖 |
| `capability_table` | 能力 → freegraph 处置（5 列 / 8 行，沿用 B24F1） |
| `affiliation` | 独立实现、非 LangChain Inc. 产品 |
| `compat_link` | **绝对 URL** `https://github.com/yangjiacheng1996/freegraph/blob/main/COMPAT.md` |
| `no_full_matrix` | README **不得**含完整逐符号矩阵 |

---

## 14. `DiagnosticsCase`（可诊断性脚本）

| 组 | 用例 | 关键断言 |
|---|---|---|
| `trace` | `FileTraceStore` / `SqliteTraceStore` + `query()` | 文件 / 行 / 过滤条数 / JSON 可序列化 |
| `checkpoint` | `MemorySaver` / `SqliteSaver` | 往返 / 历史倒序 / `tasks` / `interrupts` |
| `time_travel` | 重放 / `update_state` / 分叉 / 中断组合 | 原历史不变 / 覆盖与归约正确 |

**退出码**：`0 = PASS` / `1 = 断言失败` / `2 = 环境未就绪`。
