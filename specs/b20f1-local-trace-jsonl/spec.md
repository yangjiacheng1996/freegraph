# Feature Specification: B20F1 · 本地 Trace 存储：JSONL 文件后端（零依赖）

**Feature Branch**: `b20f1-local-trace-jsonl`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`，无 `before_specify` 钩子；既有 feature 同样在 `main` 上开发）

**Created**: 2026-11-21

**Status**: Draft

**Input**: User description: `harness/features/B20F1_本地Trace存储JSONL.md` —— 交付**本地 trace 存储**的第一段：一个**零依赖**的 **JSONL 文件后端**，把运行中产生的 span / 逐节点 trace 记录落盘成一行一条的 JSON 记录。判定：**trace 落盘，零出站**。

> **范围提醒**：本 feature 是 **L5 可观测层**的**写入侧**。只负责把 B18F1 的 `Span` 与
> B19F1 的 `TraceRecord` **原样**持久化为本地 JSONL；**不实现查询 API、不实现 SQLite 后端**
> （属 **B20F2**），**不实现 OTLP 导出**（属 **B21F1**），**不实现前端 / UI**（v2 / B26）。
> `Span` 11 字段、`TraceSink` 3 方法、`TraceRecord` 字段面、`RunConfig` 9 字段、
> `SuperStepResult` / `PregelTask`、`freegraph.graph` 门面符号面**一律不改**。

---

## 形态锁定裁定（FR-006 的「写死」结论）

> 提示词要求：本地 trace 目录/路径的**注入形态与参数名** MUST 在本 feature 锁定。
> 本节是**锁定结论**，`/speckit.plan` 与 `/speckit.implement` **MUST** 照此执行，
> `harness/demo/README.md` 的「待锁定形态」清单 MUST 据此更新。

### 1. 公开写入载体

**锁定形态：`freegraph.observability.FileTraceStore(directory: str | os.PathLike[str], *,
on_error: Callable[[BaseException], None] | None = None)`。**

| 备选 | 是否采用 | 理由 |
|---|---|---|
| **`FileTraceStore(directory=...)` 作为 B19F1 sink 注入** | ✅ **采用** | ① 复用 B19F1 已锁定的 `compile(tracer=...)` 注入点，**不新增**第二种注入形态；② `directory` 明确表达「存储目录」，与 B20F2 的 `SqliteTraceStore(database=...)` 可并列；③ 写侧接口 = 已冻结的 sink 回调 + 可选 `on_trace_record`，后端可替换；④ 与 `harness/notes/项目全貌.md` / Q6 的 **`FileTraceStore`（JSONL，零依赖，默认）** 命名一致。 |
| 在 `RunConfig` 中加 `trace_dir` | ❌ **不采用** | `RunConfig` 是 L1 **9 字段冻结面**；存储目录是 L5 外部能力注入，MUST NOT 污染 L1 纯数据面。 |
| 读环境变量 `FREEGRAPH_TRACE_DIR` 等 | ❌ **不采用** | 违反「零环境变量」硬约束；默认关闭 MUST 由**是否注入**决定，环境变量不得开启 / 关闭 / 改变行为。 |
| 单文件全局 `trace.jsonl`（所有 run 混写） | ❌ **不采用** | 与 `run_id` 的「一次运行一条链」语义冲突；无法按运行独立归档，也不满足 P1 的「这次运行的完整记录」。 |

**运行期语义**：用户 `compile(tracer=FileTraceStore(directory=...))` 后，
B19F1 的 `SpanProducer` 会把 `on_span_start` / `on_span_end` / `on_trace_record`
转发给该对象；`FileTraceStore` **只落盘**，不产生 span、不读写当前 span 栈。
`current_span()` 仅为满足静态 `TraceSink` 形态而实现，**恒返回 `None`**（它不是生产者）。

### 2. 目录与文件命名

| 项 | 锁定值 |
|---|---|
| 参数名 | **`directory`**（必填；接受 `str` 或 `os.PathLike[str]`） |
| 默认值 | **无**（MUST NOT 提供默认目录；不注入 = 不落盘） |
| 路径处理 | 按传入值构造 `pathlib.Path`；**MUST NOT** 调用 `expanduser` / `expandvars` / 读环境变量 |
| 文件粒度 | **每个 `run_id` 一个文件** |
| 文件名 | **`trace-<run_id>.jsonl`**（`run_id` 为 B18F1 / B19F1 生成的非空标识） |
| 目录创建 | **惰性**：构造 `FileTraceStore` 时**不创建**目录；第一次真正写行时才创建（`parents=True, exist_ok=True`） |
| 写入模式 | **追加**（`append`）；已有同名 run 文件则续写，不截断 |
| 持久化强度 | **每行 `flush` 到操作系统即视为成功**；**MUST NOT** 逐行 `fsync`；断电 / OS 崩溃可丢最后若干行（见 FR-024） |
| 文件权限 | 新建文件在 POSIX 上 **不宽于 `0o600`**（仅本人可读写）；v1 不提供权限配置参数；Windows 由平台 ACL 解释（见 FR-025） |
| 句柄生命周期 | **每行独立 `open → append → flush → close`**；MUST NOT 提供 `close()` / 上下文管理器 / 持久句柄（见 FR-026） |
| 失败重试 | **不重试同一行**；失败即丢弃并记诊断，下一行继续；不睡眠 / 不退避 / 不进后台重试队列（见 FR-028） |
| 换行 | `\n`（LF），最后一行也以 `\n` 结束 |
| 编码 | UTF-8（无 BOM）；`json.dumps(..., ensure_ascii=False)`，中文 / Unicode 可直接阅读 |

### 3. JSONL 行结构（写死）

文件**无头部、无尾部、无注释**；每行是一个独立 JSON 对象，**恰好一个 `kind` 字段**区分两类记录：

**A. span 行**（`kind = "span"`，在 `on_span_end` 写一次）：

```json
{"kind": "span", "id": "<span-id>", "name": "<name>", "attributes": {}, "parent": null, "start_time": "<ISO-8601>", "end_time": "<ISO-8601>", "context": {}, "thread_id": "<tid>", "run_id": "<rid>", "node": "<node>", "checkpoint_id": null}
```

- 字段 = **`Span` 的全部 11 字段**（`id` / `name` / `attributes` / `parent` /
  `start_time` / `end_time` / `context` / `thread_id` / `run_id` / `node` /
  `checkpoint_id`）+ `kind`；字段名 **MUST NOT** 改名。
- 只在**结束**回调写：此时 `end_time` 非空；**开始回调不写行**（v1 不落半成品 span）。
- 模型 / 工具 span 同样落盘（它们也是 `Span`）；因此文件是**完整 span 树**，不只有节点 span。

**B. trace 记录行**（`kind = "trace_record"`，在 `on_trace_record` 写一次）：

```json
{"kind": "trace_record", "span_id": "<span-id>", "task_id": "<task-id>", "run_id": "<rid>", "thread_id": "<tid>", "checkpoint_id": null, "node": "<node>", "superstep": 0, "triggers": [["e", "a"]], "concurrency_group": ["b"], "barrier_groups": [], "input_state": {}, "output_state": {}, "error": null}
```

- 字段 = **B19F1 `TraceRecord.to_jsonable()` 的原样 JSON 视图** + `kind`；
  `span_id` / `task_id` / `run_id` / `thread_id` / `checkpoint_id` / `node` /
  `superstep` / `triggers` / `concurrency_group` / `barrier_groups` /
  `input_state` / `output_state` / `error` 字段名 **MUST NOT** 改名 / 重新定义。
- `error` 的 JSONL 视图为 **`{"type": ..., "message": ...}` 或 `null`**（由
  `to_jsonable()` 提供）；MUST NOT 把原异常对象 / `repr` 写进文件。
- 记录**不是** `Span` 的字段：MUST NOT 塞进 `Span.attributes` / `Span.context`。

**C. 行序**：

- 按 B19F1 的回调到达顺序落盘；对同一节点任务，记录行在**节点 span 行之前**到达
  （B19F1 的顺序 = `on_span_start → on_trace_record → on_span_end`）。
- **MUST NOT** 排序、聚合或重写回调顺序；并发任务的到达顺序可不稳定，
  确定性由 `triggers` / `concurrency_group` 的字段内顺序承载（B19F1 已保证）。
- **当经 B19F1 注入且 `on_trace_record` 可用时**：`trace_record` 行数 == **节点任务数**；
  `span` 行数 == **全部已结束 span 数**（节点 + 模型 + 工具）；节点
  `trace_record.span_id` MUST 能在同文件找到 `id` 相等的 `span` 行。
- **接收端不含 `on_trace_record` 时**（例如仅转发 start/end 的 span-only 适配器 /
  纯 span sink）：文件 MAY 只含 span 行；`trace_record` 行数 == 0 合法（见 Edge Cases）。
  该情形 MUST NOT 被判定为缺陷。**注意**：`FileTraceStore` 始终实现
  `on_trace_record`，因此它本身不属于 span-only 情形；需要 span-only 时 MUST 用
  适配器屏蔽 record（见 Edge Cases / T052）。

### 4. 写入失败如何被感知（FR-007 的「写死」结论）

**锁定：写入失败永不使运行失败，但 MUST 通过「计数 + 最后错误 + 可选回调 + 标准库日志」四路可感知。**

| 感知通道 | 形态 | 判定 |
|---|---|---|
| 计数 | 公开只读属性 **`write_errors: int`**（单调递增，初值 0） | 失败一次 ⇒ +1 |
| 最后错误 | 公开只读属性 **`last_error: str \| None`** | 失败后非空，含异常类型名与消息 |
| 回调 | 构造参数 **`on_error: Callable[[BaseException], None] \| None`** | 提供时每次失败调用一次；回调自身抛异常被吞并记日志 |
| 日志 | 标准库 `logging` 的 **`WARNING`**（含异常栈） | 失败一次 ⇒ 一条警告，不中断运行 |

- 失败 = **`Exception`** 范围内的任何异常（目录不可写 / 路径是文件 / 磁盘满 /
  序列化失败 / `flush` 失败等）；`BaseException`（`KeyboardInterrupt` /
  `SystemExit` 等）**MUST NOT** 被吞（与 B18F1 / B19F1 的隔离口径一致）。
- **MUST NOT** 静默吞错：只有「运行不失败」是硬承诺；「用户能知道 trace 没记上」同样是硬承诺。
- 失败后 MUST NOT 留下**半行** JSON：写一行前记录文件偏移，失败时截断回该偏移；
  截断也失败时记诊断，但运行仍继续。后续行仍可尝试写入。
- **不重试**：同一行失败后 MUST NOT 重试 / 睡眠 / 退避；直接丢弃该行并继续后续行
  （见 FR-028）。

---

## Clarifications

### Session 2026-11-21（spec 阶段写死 · plan 不得再翻）

- Q: 记录应该只落 B19F1 的 `TraceRecord`，还是也要落 B18F1 的 `Span`？
  → A: **两者都落**，用 `kind` 区分。`TraceRecord` 不含 `Span` 的 `name` /
  `attributes` / `parent` / `start_time` / `end_time` / `context`；只落 record 无法满足
  FR-003「含 Span 全部字段」。两者通过 `span_id` ↔ `id` 关联，**MUST NOT** 把 record
  塞进 `Span` 字段（B19F1 D-3）。
- Q: `Span` 在开始回调就写，还是结束回调才写？
  → A: **结束回调写**。开始快照 `end_time is None`，落盘会留下半成品；结束快照是同 `id`
  且 `end_time` 已填的**新实例**，是「完整 span 记录」的唯一稳定视图。开始回调 MUST 不写盘。
- Q: 每次运行一个文件，还是整个目录一个文件？
  → A: **每个 `run_id` 一个 `trace-<run_id>.jsonl`**。与 C22「一次运行一个 `run_id`」
  对齐，支持同一 store 实例跨多次 `invoke()` / `stream()` 复用；不同 run 不混写。
- Q: 写入失败的「可感知」用日志、回调还是计数？
  → A: **四路同时**：`write_errors` 计数 + `last_error` + 可选 `on_error` 回调 +
  `logging.WARNING`。单选日志容易被静默；单选回调在未提供时不可感知；计数 + 最后错误
  是**始终可用**的最小面（见「形态锁定裁定」§4）。
- Q: 默认目录是什么？不传 `directory` 能否落盘？
  → A: **没有默认目录**；`directory` 必填。不注入 `FileTraceStore` / 不传 `tracer=` ⇒
  零文件、零目录、零副作用。环境变量一律不读。
- Q: 并发回调（同一 super-step 多节点 / 多线程）如何保证 JSONL 不被写坏？
  → A: **每个 store 实例一把进程内锁串行化整行写入**；每行先完整序列化，再在锁内完成
  「记偏移 → 追加 → flush」，失败回滚偏移。MUST NOT 让两行的字节交错。
- Q: 文件格式是否属于对外契约？
  → A: **文件格式是内部实现细节**（C27 ⑤）；对外只承诺「本地落盘 + 每行可 `json.loads` +
  含关联键」以及 `FileTraceStore` 的写入行为。查询 API 归 B20F2，Studio 不直连文件
  （立项书 §5.8.4）。

### Session 2026-11-21（clarify 轮 · 用户参与）

- Q: 每一行写入后，是「flush 到操作系统」就算成功，还是必须「fsync 到磁盘」才算成功？
  → A: **只 flush，不逐行 fsync**。每行写完并 `flush` 后即视为该行写入成功；进程崩溃不丢
  已 flush 的行，但操作系统崩溃 / 断电可能丢最后若干行。MUST NOT 要求逐行 `fsync`；
  该持久化强度取舍写入 FR-011 / FR-024 / SC-015。
- Q: trace 文件创建时使用什么文件权限？
  → A: **0o600（仅本人可读写）**。trace 按敏感数据处理；新建文件在 POSIX 上 MUST 以
  不宽于 `0o600` 的权限创建；v1 **不提供**权限配置参数（避免误设过宽）。Windows 上由
  平台 ACL 解释，不做 POSIX 权限位承诺。该决定写入 FR-025 / SC-016。
- Q: `FileTraceStore` 每写一行就关闭文件，还是保持句柄并要求用户 `close()`？
  → A: **每行独立打开 → 追加 → `flush` → 关闭，不提供 `close()` / 上下文管理器 /
  持久句柄**。trace 写入不是高频热点；换来「无线程间句柄泄漏、跨 run 安全、用户无需
  记得关闭」。该决定写入 FR-026 / SC-017。
- Q: 同一个 store 同时服务多个 run 时，用全局锁、每 run 锁，还是每 store 实例一把锁？
  → A: **每个 `FileTraceStore` 实例一把锁**。上游只有 per-Client / 全局锁与后台队列
  （`langsmith/client.py:149,1344,1346` · `_background_thread.py:327-377`），没有按 run
  分文件锁；每实例一把锁既不让不同 store 互相阻塞，也不需要「每 run 锁表」的生命周期
  管理。锁只保护「记偏移 → 追加 → `flush` → 关闭」与诊断计数；用户 `on_error` MUST 在
  锁外调用。该决定写入 FR-027 / SC-018。
- Q: 某一行写入失败后，是否应该重试该行？
  → A: **不重试**。失败即丢弃该行并记诊断，下一行继续尝试；MUST NOT 睡眠 / 退避 /
  循环重试，避免因磁盘 / 权限问题拖慢或阻塞图执行。该决定写入 FR-028 / SC-019。

---

## 分析修复记录（2026-11-21）

- **质量门禁 5**：登记偏离（发起者选择 A）；B20F1 只跑 fake / 本地轮，真实模型轮由
  B25F1（M4）承接；正式追认文字由发起者本人签署。
- **FR-003 / §3 C / SC-009**：把「每节点任务必有 span + record」限定到「经 B19F1 注入且
  `on_trace_record` 可用」；保留「接收端不含 `on_trace_record`」的 span-only Edge Case
  （`FileTraceStore` 始终实现 record，故需经适配器）。
- **SC-012 / SC-013**：新增 `tests/runtime/test_b20f1_manual_record_guard.py`（T053）自动文档守卫。
- **SC-014**：新增 `tests/observability/test_b20f1_run_id_safety.py`（T050）判定覆盖。
- **SC-015**：新增 `tests/observability/test_b20f1_flush_durability.py`（T051）判定覆盖。
- **FR-021**：明确 `write_errors` 只统计持久化失败；`on_error` 自身异常只记日志、不增加计数。
- **文档登记**：新增 `harness/verification/README.md` 的 B20F1 行更新任务（T049）。

### 第二轮分析修复（2026-11-21 · 跨工件对齐）

- **I1（span-only 可执行性）**：明确 `FileTraceStore` 始终实现 `on_trace_record`；
  span-only 只适用于「接收端不含 `on_trace_record`」的适配器 / 纯 span sink。T052 改为
  通过 **span-only 适配器**绑定 B18F1（适配器补 `current_span_id()`）。
- **I2（`run_id` 安全规则）**：全工件统一为默认拒绝**任意点号**（`.` / `..` 均拒绝）；
  安全 allowlist 收紧为 `^[A-Za-z0-9][A-Za-z0-9_-]*$`（内部 `uuid4().hex` 天然满足）。
- **I3（差分落点）**：统一为 `tests/differential/test_b20f1_local_trace_parity.py`。
- **I4（SC-011 范围）**：限定为本 feature 新增模块（`_file_store.py`）的 L5 → L2/L3/L4
  反向 import == 0；既有 `_inject.py` 的 R-2 例外不回溯改写。
- **I5（L5 冻结面处置）**：与 plan / contract 对齐为「**无需拆分**」；现有断言不扫相对
  导入，只需把新文件加入扫描 / 署名头清单（只增）。
- **I6（上游对照一致性）**：补 **X-6**，登记 P-01 的 DIFF（表示层）。
- **G1 / G2 / U1**：补齐双向追溯、明确 SC-012 判定由 T053 承担、plan 测试树补列遗漏文件。

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 跑完一次图，本机留下完整轨迹 (Priority: P1)

作为用户，我跑完一次图后，希望在**本地目录**里看到这次运行的完整 span / 节点记录，
以便事后排查（不依赖云服务、不需要账号、不需要 API key）。

**Why this priority**: 这是 C27 写入侧的最小价值切片；没有它，B18F1 / B19F1 生产的
span 与 trace 记录只停在内存里，用户拿不到任何可归档证据。

**Independent Test**: 用 `compile(tracer=FileTraceStore(directory=tmp))` 编译并运行一个
`a → b` 线性图；断言 `tmp` 下生成**恰好一个** `trace-<run_id>.jsonl`，其中含两个节点的
`kind="span"` 行与 `kind="trace_record"` 行，且 `run_id` 一致。

**Acceptance Scenarios**:

1. **Given** 注入 `FileTraceStore(directory=tmp)`，**When** 运行 `a → b`，**Then** `tmp`
   下生成 1 个 JSONL 文件；每个节点各有 1 条 span 行与 1 条记录行。
2. **Given** 同一 store 实例连续运行两次（两次 `invoke()`），**When** 两次运行结束，
   **Then** `tmp` 下有 2 个以各自 `run_id` 命名的文件；文件内容不互相混写。
3. **Given** 节点内部调用模型 / 工具，**When** 运行结束，**Then** 文件中额外包含模型 /
   工具 span 行（`parent` 指向所在节点 span 的 `id`），节点记录行不替代这些 span 行。
4. **Given** 节点抛异常，**When** 运行结束，**Then** 该节点的 span 行仍落盘（`end_time`
   非空），其记录行 `error` 为 `{"type","message"}`；原异常仍按 B19F1 语义抛给调用方。

---

### User Story 2 - 记录可被人与机器读取 (Priority: P2)

作为用户，我希望文件是**每行一条 JSON**：可直接用 `jq` 过滤、可用文本编辑器查看，
也可以被测试代码逐行 `json.loads`。

**Why this priority**: 「落盘」若不可读，就只是二进制垃圾；JSONL 是 v1 对外承诺的
零依赖、可审计存储形态。

**Independent Test**: 逐行 `json.loads`，断言每行是 `dict` 且含 `kind`；用 `jq`
（或等价的纯 Python 解析）按 `kind` / `node` / `run_id` 过滤得到预期条数。

**Acceptance Scenarios**:

1. **Given** 任意生成的 JSONL 文件，**When** 逐行读取，**Then** 每行均可被
   `json.loads` 解析为 `dict`，无空行、无多行对象、无尾随垃圾。
2. **Given** 一条 span 行，**When** 读取字段，**Then** `Span` 的 11 字段全部存在且
   字段名逐字等于 `Span` 定义；`kind == "span"`。
3. **Given** 一条记录行，**When** 读取字段，**Then** B19F1 `to_jsonable()` 的 13 字段
   全部存在且字段名逐字不变；`kind == "trace_record"`。
4. **Given** 含中文 / 换行 / Unicode 的状态值，**When** 写入并读回，**Then** 值无损
   （JSON 转义正确），且每个对象仍只占一行。

---

### User Story 3 - 写入失败不阻断，但我不被蒙在鼓里 (Priority: P2)

作为用户，我的 trace 目录可能不可写（只读、磁盘满、路径是文件）；我希望图**照常跑完**，
同时能明确知道「这次 trace 没记上 / 记了一部分」，而不是以为已经记好了。

**Why this priority**: 宪法原则 IV 规定可视化层 MUST NOT 阻断执行；但 B20F1 的风险提示
明确要求「失败如何被感知」必须可判定，否则静默吞错会制造虚假安全感。

**Independent Test**: 把 `directory` 指向一个只读目录（或一个普通文件），注入 store 后
运行同一张图；断言运行结果与不注入时**逐字相同**、无异常逃逸；同时
`store.write_errors > 0`、`store.last_error` 非空、`on_error` 被调用、日志出现 WARNING。

**Acceptance Scenarios**:

1. **Given** 目录不可写，**When** 运行图，**Then** 图正常返回；异常传播数 == 0。
2. **Given** 目录不可写且提供 `on_error`，**When** 每次写失败，**Then** 回调收到原异常；
   `write_errors` 递增；`last_error` 更新。
3. **Given** 目录不可写且未提供 `on_error`，**When** 运行，**Then** 仍能通过
   `write_errors` / `last_error` / 日志感知失败，不出现「静默成功」。
4. **Given** 写第 N 行时中途失败，**When** 检查文件，**Then** 文件中**不留下**半行
   JSON（截断回写前偏移）；后续可继续尝试写新行。

---

### User Story 4 - 不启用时完全不留痕迹 (Priority: P3)

作为用户，我不诊断时，希望 freegraph **完全静默**：不创建目录、不创建文件、不读环境变量、
不因 trace 改变任何运行行为。

**Why this priority**: 这是宪法原则 I / IV 的硬承诺；默认关闭必须可测，否则任何观测增强
都可能在用户不知情时留下副作用。

**Independent Test**: 不注入 tracer（或显式 `compile(tracer=None)`），运行图；对目标目录
做前后快照，断言 0 个新文件、0 个新目录；再设置 `LANGSMITH_TRACING=true` /
`FREEGRAPH_TRACE_DIR=...` 等环境变量，断言行为不变。

**Acceptance Scenarios**:

1. **Given** 未注入 tracer，**When** 运行任意图（含异常 / 并发 / `stream()`），
   **Then** 目标目录不存在或不新增任何文件；`Span` / `TraceRecord` 构造数不变
   （沿用 B19F1 的默认关闭断言）。
2. **Given** 只构造 `FileTraceStore(directory=tmp)` 但**从不运行**，**When** 检查 `tmp`，
   **Then** 目录不创建、文件为 0（构造无副作用）。
3. **Given** 设置了 `FREEGRAPH_TRACE_DIR` / `LANGSMITH_TRACING=true` 等环境变量，
   **When** 未注入 store，**Then** 仍零文件；注入 store 时也**只认**显式 `directory`，
   环境变量不得覆盖 / 开启 / 关闭。

---

### Edge Cases

- **目录路径是普通文件**：`makedirs` 失败 ⇒ 按「写入失败」处理；运行不失败，诊断可见。
- **目录只读 / 父目录不可写**：同上；已有子目录不可写时 `open(append)` 失败同样处理。
- **磁盘满 / `flush` 失败**：截断回写前偏移；`write_errors` 递增；运行继续。
- **进程崩溃 / 操作系统崩溃 / 断电**：只保证 `flush` 强度——进程崩溃不丢已 flush 行；
  OS 崩溃 / 断电可丢最后若干行，**不判缺陷**；MUST NOT 逐行 `fsync` 来「消除」该风险。
- **序列化失败**：`Span` / `TraceRecord` 的正常视图应可序列化；若外部构造了不可序列化值，
  按写入失败处理，MUST NOT 让 `json.dumps` 的异常传播到图执行。
- **`run_id` 为空**：视为上游实现缺陷；不写文件，记诊断（MUST NOT 伪造 / 生成新 id）。
- **`run_id` 含路径分隔符，或含任意 `.`（含 `..`）**：拒绝作为文件名，记诊断；
  MUST NOT 允许目录穿越。安全 allowlist = `^[A-Za-z0-9][A-Za-z0-9_-]*$`（无点号）。
- **同一 `run_id` 多进程 / 多实例写同一文件**：v1 只保证**进程内**整行不交错；
  跨进程并发不在本 feature 承诺（SQLite 后端的跨进程场景归 B20F2）。
- **一个 span 只开始未结束（进程崩溃）**：v1 不写开始行 ⇒ 该 span 无行；已结束的
  更早 span 仍完整可读。
- **没有 span 的执行（store 未收到任何回调）**：不写文件；不报错。
  v1 的 `StateGraph` 在构造期拒绝「没有节点」的图，故该 Edge Case 由「store 未收到
  任何回调」等价覆盖（测试见 T011）。
- **`on_trace_record` 未被调用**（例如使用仅转发 start/end 的 **span-only 适配器**，
  或接收端本身不含 `on_trace_record`）：仍只落 span 行；文件结构合法，只是没有
  `kind="trace_record"` 行。`FileTraceStore` 始终实现 `on_trace_record`，故不能
  直接充当 span-only sink；测试 MUST 用适配器屏蔽 record（见 T052）。
- **错误记录**：`error` 为原异常时，JSONL 中只出现 `{"type","message"}`，MUST NOT
  出现对象 `repr` / 堆栈 / 原始对象。
- **非 ASCII / 换行 / 引号 / 控制字符**：由 `json.dumps` 转义；对象不跨行。
- **符号链接 / 相对路径**：`directory` 按传入值使用；不解析、不展开、不读环境变量。
- **同一目录已有其它文件**：只追加 / 创建 `trace-<run_id>.jsonl`，MUST NOT 删除或改写
  其它文件；不实现保留期 / 清理。
- **同名 run 文件已存在且权限更宽**：MUST NOT 主动放宽；实现 MAY 尝试收紧到 `0o600`，
  收紧失败只记诊断、不阻断运行（POSIX）；Windows 由平台 ACL 解释。
- **`on_error` 内重入 store**：回调 MUST 在锁外调用；重入写入 MUST 不造成死锁；
  若重入写入再次失败，MUST 不递归调用 `on_error`（避免无限递归）。
- **瞬时错误（如 Windows 共享冲突）**：v1 **不重试**；该行丢弃并记诊断，下一行仍可写；
  不睡眠 / 不阻塞。

---

## Upstream Parity *(mandatory — 宪法 v1.12.0 原则 XI「上游优先」)*

**Upstream version**: `langgraph` **1.2.11** / `langchain-core` **1.7.6** / `langsmith` **0.14.17**（取证于 2026-11-21，本仓库 `.venv` 实际安装版本；沿用 B19F1 的版本钉住口径）

> **口径说明**：上游**没有** freegraph 这样的「本地 JSONL trace 存储后端」。上游的可观测
> 数据面由 LangChain callbacks / LangSmith `RunTree` 承载，默认关闭，开启后经 HTTP 批量
> 发送到 LangSmith（或其它远端）。因此本 feature 的主体落在原则 XI 的**必须自研区 ③
> （上游没有的能力）**、**①（零账号 / 零主动出站 / 零依赖）**；只有「默认关闭」
> 「失败不阻断」「按 `run_id` 分组」这几类**行为面**需要与上游对齐。

### §1 逐条对照（P-01…P-07）

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| **P-01** | **默认关闭**：不显式配置就没有观测副作用 | `langchain_core/tracers/context.py:114-120`（`_get_trace_callbacks` 仅在 `_tracing_v2_is_enabled()` 时构造 tracer）· B19F1 实测 **E-1**（不传 callbacks ⇒ 0 个 handler 事件） | 不注入 `FileTraceStore` / 不传 `tracer=` ⇒ 零文件 / 零目录 / 零回调；`compile(tracer=None)` 等价于未注入 | **SAME**（行为面）· **DIFF**（表示：本地文件 vs 上游 callback） | 默认关闭是宪法原则 I / IV；本 feature 不改变 B19F1 的默认关闭语义 |
| **P-02** | **环境变量不得自动开启观测** | `langsmith/utils.py:119-144`（`TRACING_ENABLED` / `TRACING_V2` / `TRACING` 等环境变量可影响 tracing 开关）· `langchain_core/tracers/context.py:120` | 只认显式 `compile(tracer=FileTraceStore(directory=...))`；MUST NOT 读 `LANGSMITH_*` / `LANGCHAIN_*` / `FREEGRAPH_*` / `OTEL_*` | **STRICTER** | 宪法原则 I / 配置层黑名单；本项目反「key / env 存在即自动开 tracing」 |
| **P-03** | **持久化落点与出站** | `langsmith/client.py:139`（`httpx` 客户端）· `:619`（默认 `https://api.smith.langchain.com`）· `langsmith/_internal/_background_thread.py:377`（批量 ingest） | 本地 JSONL 文件；零网络、零账号、零 API key；MUST NOT 发起任何出站请求 | **STRICTER** | 宪法原则 IV / V；「trace 落盘，零出站」是本 feature 的判定 |
| **P-04** | **一次运行可按运行标识归组** | `langsmith/run_helpers.py:107-113`（当前 run tree）· `langchain_core/tracers/base.py:47,53`（run / parent run id） | 每个 `run_id` 一个 `trace-<run_id>.jsonl`；span / record 都带 `run_id` | **SAME**（id 分组语义）· **DIFF**（表示：文件 vs run tree） | C22 / C23 已冻结「一次运行一个 `run_id`」；本 feature 只按它归档 |
| **P-05** | **观测失败不改变图结果** | `langchain_core/callbacks/manager.py:351-354`（handler 异常被捕获并记警告） | 写入失败隔离 `Exception`；图结果与不注入时逐字相同；`BaseException` 不吞 | **SAME**（隔离语义）· **STRICTER**（可感知面：`write_errors` / `last_error` / `on_error`） | 宪法原则 IV；B18F1 / B19F1 已隔离接收端异常，本 feature 不得削弱，并补可感知信号 |
| **P-06** | **span / 补充记录的统一持久化形态** | 上游**没有**等价的「节点 span + 逐节点输入输出 / 触发源 / 并发组 / 屏障组」统一本地视图；这些事实散落在 callback / debug payload / 调度内部 | 两类 JSONL 行：完整 `Span` 行 + `TraceRecord.to_jsonable()` 行；`kind` 区分、`span_id` ↔ `id` 关联 | **DIFF**（自研区 ③：上游没有的能力） | B18F1 / B19F1 的下游承接要求；上游无同款本地存储结构 ⇒ 只能自研 |
| **P-07** | **并发写入的串行化载体** | 上游无本地文件锁；用**进程内队列 + 后台线程**批量 ingest（`langsmith/_internal/_background_thread.py:327-377`），锁是 per-Client / 全局（`langsmith/client.py:149` 的 `_tracing_drops_lock`、`:1344` 的 `_futures_lock`、`:1346` 的 `_run_ops_buffer_lock`），**没有按 run 分文件锁** | 每个 `FileTraceStore` **实例**一把 `threading.Lock`；锁只包住单行写入与诊断计数；`on_error` 在锁外调用 | **SAME**（实例内串行语义）· **DIFF**（表示：本地文件锁 vs 队列 + 后台线程） | 上游无本地 JSONL；per-instance 锁最接近 per-Client 锁，且不需要「每 run 锁表」 |

### §2 实测基线（E-1…E-3 · 沿用 B19F1 · 取证于 2026-11-21）

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

### §3 差分场景组 *(mandatory)*

> 编号段 **D-401…D-408**（避开 B18F1 的 D-201…D-208 与 B19F1 的 D-301…D-310）。

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

⇒ **判词分布**：**SAME 行为面 3**（D-401 / D-405 的隔离段 / D-408 的串行语义）+ **STRICTER 3**（D-403 / D-404 / D-407；D-405 另有 STRICTER 感知面）+ **DIFF 3**（D-402 / D-406 / D-408 的表示层；D-402 同时含 P-06 自研结构）。

⇒ **落点**：`tests/differential/test_b20f1_local_trace_parity.py` ⇒ **CI 的 Linux 全量档真跑**
（上游缺席即 skip · 沿用 B5F2 的「缺席即 skip」纪律）。本 feature 的本地 JSONL 形态
不与上游逐字节对比，只对齐「默认关闭 / 失败隔离 / 按 run 分组 / 实例内串行」四类行为面。

### §4 偏离登记 *(仅限三类 · 其余一律照抄)*

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-1** | **DIFF**（自研区 ③：上游没有的能力） | 上游无本地 JSONL trace 后端、无「完整 `Span` + `TraceRecord`」双行持久化、无 `kind` 区分（对应 **P-06**） | C27 的写入侧必须自研；上游对应物是 LangSmith 远端 run tree，引入即破零依赖 / 零出站 | 本 feature（写入侧）· B20F2（查询侧） |
| **X-2** | **STRICTER**（自研区 ①：零账号 / 零主动出站 / 零依赖） | 上游 tracing 可由环境变量开启并经 HTTP 发往 LangSmith（对应 **P-02 / P-03**） | freegraph MUST 零第三方依赖、零环境变量、零主动出站；只认显式注入的 `directory` | 宪法原则 I / II / IX · 本 feature |
| **X-3** | **DIFF**（自研区 ③：上游没有的能力 · 表示层） | 本地文件粒度 = 每个 `run_id` 一个 `trace-<run_id>.jsonl`；上游是一个远端 run tree（对应 **P-04**） | 文件是内部实现细节（C27 ⑤）；按 `run_id` 归档使「一次运行一条链」可直接落地，且不把 trace 塞进 `stream()` 信封 | 本 feature · B20F2（按 `run_id` 查询） |
| **X-4** | **STRICTER**（更严的失败信号） | 写入失败除「不阻断」外，还 MUST 提供 `write_errors` / `last_error` / `on_error` / 日志四路可感知（对应 **P-05**） | 静默吞错会让用户以为 trace 已记录；宪法原则 IV 要求可诊断，本项目要求失败信号**可判定** | 本 feature |
| **X-5** | **DIFF**（自研区 ③：上游没有的能力 · 表示层） | 并发写入载体 = **每个 store 实例一把 `threading.Lock`**；上游是进程内队列 + 后台线程批量 ingest（对应 **P-07**） | 上游无本地 JSONL，也没有按 run 分文件锁；per-instance 锁比「每 run 锁表」简单，且与上游 per-Client 锁最接近 | 本 feature |
| **X-6** | **DIFF**（自研区 ③：上游没有的能力 · 表示层） | 默认关闭的**表示**：本地文件 sink vs 上游 callback / tracer（对应 **P-01** 的 DIFF 半段） | 默认关闭的**行为面**是 SAME；差异仅在「观测结果落到本地文件」这一表示层，属自研区 ③ | 本 feature |

### §5 破冻结面的回溯修订清单 *(本 feature 触发)*

| 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 |
|---|---|---|---|
| `freegraph.observability.__all__` 的**精确集合断言**（B19F1 交付） | `tests/facade/test_api_snapshot.py:330`（`set(observability.__all__) == {...}`）· `tests/contracts/test_b19f1_lazy.py:38-40`（`current_span` / `TraceRecord` 在、`trace_run_scope` 不在） | **只增不改**：新增 `FileTraceStore` 到 L5 导出面；既有 5 个符号逐字保留；`trace_run_scope` 仍不导出。更新精确集合断言（**更新非放宽**） | 在 `harness/verification/B20F1/manual-verification.md` 追认 |
| **L5 依赖面**（B18F1 / B19F1 的「L5 只 import 标准库 + L1」断言） | `src/freegraph/observability/_file_store.py`（具体路径见 plan） | **无需拆分**：现有断言只扫绝对 import，同层相对导入天然被忽略；`_file_store.py` 只 import 标准库 + L1 `Span` + 同层 `TraceRecord`（L5），MUST NOT import L2 / L3 / L4 / 第三方；只需把新文件加入扫描 / 署名头清单（只增） | 无需为「拆分」追认；`observability.__all__` 更新仍按本表上一行追认 |

> **不破的冻结面**：`Span` 11 字段 · `TraceSink` 3 方法 · `TraceRecord` 字段面 ·
> `RunConfig` 9 字段 · `SuperStepResult` 5 字段 / `PregelTask` 7 字段 · `stream()` 事件信封 ·
> `freegraph.graph` 门面 8 符号 · L1 契约 22 符号 · `freegraph.runtime.__all__`。
> **唯一新增公开符号**：`freegraph.observability.FileTraceStore`（L5，不进 `freegraph.graph`
> 门面，`import freegraph` 仍不加载 L5）。

---

## Requirements *(mandatory)*

### Functional Requirements

#### A. 本地 JSONL 写入

- **FR-001**：系统 MUST 提供本地 trace 存储后端 **`freegraph.observability.FileTraceStore`**，
  默认实现为 **JSONL 文件后端**；MUST 只用标准库（`json` / `os` / `pathlib` /
  `threading` / `logging` 等），MUST NOT 引入任何第三方依赖。
- **FR-002**：每条记录 MUST 序列化为**一行一个 JSON 对象**，可被 `json.loads` 独立解析；
  文件 MUST 无头部 / 尾部 / 多行对象 / 空行；每行以 `\n` 结束；UTF-8 编码。
- **FR-003**：文件 MUST 含两类行，用 `kind` 区分：
  - `kind="span"`：**`Span` 的全部 11 字段**（`id` / `name` / `attributes` / `parent` /
    `start_time` / `end_time` / `context` / `thread_id` / `run_id` / `node` /
    `checkpoint_id`）；
  - `kind="trace_record"`：**B19F1 `TraceRecord.to_jsonable()` 的全部字段**
    （`span_id` / `task_id` / `run_id` / `thread_id` / `checkpoint_id` / `node` /
    `superstep` / `triggers` / `concurrency_group` / `barrier_groups` /
    `input_state` / `output_state` / `error`）。
  - **当经 B19F1 注入且 `on_trace_record` 可用时**：每个**节点任务** MUST 同时有对应的
    span 行与 record 行（通过 `span_id` ↔ `id` 关联）；模型 / 工具 span 只需 span 行。
  - **接收端不含 `on_trace_record` 时**（span-only 适配器 / 纯 span sink）：MUST 仍落
    span 行；MAY 无 `trace_record` 行（见 Edge Cases）；该情形 MUST NOT 被判定为缺陷。
    `FileTraceStore` 本身始终实现 `on_trace_record`，故 span-only 须经适配器。
- **FR-004**：存储 MUST **零出站**；MUST NOT 访问任何外部服务 / 网络 / 账号 / API key。
- **FR-005**：未启用存储时，MUST **不创建任何文件 / 目录、不产生任何副作用**；只构造
  `FileTraceStore` 但不运行，同样不得创建目录或文件。
- **FR-006**：系统 MUST 提供**存储目录的注入形态**，参数名锁定为 **`directory`**：
  `FileTraceStore(directory=...)`，经 B19F1 已锁定的 `compile(tracer=...)` 注入。
  MUST NOT 提供 `RunConfig` 字段、环境变量或第二种注入形态作为替代。
- **FR-007**：写入失败（目录不可写 / 路径是文件 / 磁盘满 / 序列化失败 / flush 失败等）
  MUST **不使运行失败**；异常 MUST NOT 传播到节点 / 图执行。失败 MUST 可被感知：
  `write_errors`（计数）+ `last_error`（最后错误）+ 可选 `on_error` 回调 +
  标准库 `logging.WARNING`；MUST NOT 静默吞错。
- **FR-008**：系统 MUST NOT import `langchain` / `langchain-core` / `langsmith` /
  `langgraph*`；MUST NOT 读环境变量；MUST NOT import `sqlite3`（SQLite 归 B20F2）。
- **FR-009**：每个 `run_id` MUST 写一个 **`trace-<run_id>.jsonl`**；同一 store 实例跨多次
  `invoke()` / `stream()` 时，不同 run 写不同文件，MUST NOT 混写。
- **FR-010**：`FileTraceStore` MUST 实现 B19F1 sink 的可选鸭子类型接口：
  `on_span_start(span)`（**不写盘**）、`on_span_end(span)`（写 span 行）、
  `on_trace_record(record)`（写 record 行）；`current_span()` 恒返回 `None`。
  MUST NOT 改变 `TraceSink` 三方法协议 / `Span` / `TraceRecord` 字段面。
- **FR-011**：并发回调下 MUST 保证每行**完整写入并 `flush` 到操作系统、字节不交错**；
  实现 MUST 用**每个 store 实例一把**的进程内锁串行化「记偏移 → 追加 → `flush`」；
  失败时 MUST 截断回写前偏移，
  MUST NOT 留下半行。
- **FR-012**：`FileTraceStore` MUST 位于 **L5**，只依赖标准库 + L1 `Span` + 同层
  `TraceRecord`；MUST NOT import L2 / L3 / L4；MUST NOT 进入 `freegraph.graph` 门面；
  `import freegraph` MUST NOT 加载 L5。
- **FR-013**：本 feature MUST NOT 实现查询 API / SQLite 后端（B20F2）、OTLP 导出（B21F1）、
  前端 / UI（v2 / B26）、保留期 / 清理策略。允许**测试内**读回自己写的文件做校验。
- **FR-014**：`directory` MUST 按传入值使用；MUST NOT `expanduser` / `expandvars` /
  读环境变量 / 联网解析。若 `run_id` 为空、含路径分隔符、或含任意 `.`（含 `..`），
  MUST 拒绝作为文件名并记诊断（MUST NOT 目录穿越、MUST NOT 伪造新 `run_id`）。
  安全 allowlist = `^[A-Za-z0-9][A-Za-z0-9_-]*$`（无点号；内部 `uuid4().hex` 天然满足）。
- **FR-015**：`error` 的 JSONL 视图 MUST 为 `{"type": <异常类名>, "message": <str(exc)>}`
  或 `null`，由 `TraceRecord.to_jsonable()` 提供；MUST NOT 写原对象 / `repr` / 堆栈。
- **FR-016**：记录内容 MUST 原样消费 B19F1 的 `to_jsonable()`，MUST NOT 重新定义 /
  改名字段；`kind` 是**唯一新增字段**。MUST NOT 把 record 塞进
  `Span.attributes` / `Span.context`。
- **FR-017**：交付物 MUST 更新 `harness/demo/README.md`：把「本地 trace 存储目录的参数名」
  从「待锁定形态」清单移除（或标为**已锁定**），并注明锁定依据 = 本 spec
  §「形态锁定裁定」。
- **FR-018**：交付物 MUST 包含 `harness/verification/B20F1/manual-verification.md`，
  记录：JSONL 样例行、`jq` / `json.loads` 读回证据、写入失败感知证据、零出站证据、
  `observability.__all__` 快照更新的追认、**质量门禁 5 偏离声明**
  （真实模型轮由 B25F1 承接）与发起者追认文字；并由
  `tests/runtime/test_b20f1_manual_record_guard.py` 自动核验。

#### B. 数据与生命周期

- **FR-019**：`Span` 行 MUST 在 `on_span_end` 写；此时 `end_time` 非空。开始快照
  （`end_time is None`）MUST NOT 落盘。异常 / 中断节点仍写其 span 行与 record 行。
- **FR-020**：行序 MUST 保留 B19F1 的回调到达顺序；对同一节点任务，record 行在 span 行
  之前。MUST NOT 排序 / 聚合 / 重写。并发到达顺序可不稳定，但每行独立合法。
- **FR-021**：`FileTraceStore` MUST 维护公开只读诊断面：
  `write_errors: int`（初值 0，单调递增）、`last_error: str | None`；`on_error`
  为可选构造参数。诊断更新 MUST 线程安全。`write_errors` 只统计**持久化失败**；
  `on_error` 回调自身抛出的 `Exception` 只记日志，**MUST NOT** 再次增加计数。
- **FR-022**：`FileTraceStore` 的构造 MUST 只保存 `directory` / `on_error`，MUST NOT
  访问文件系统 / 创建目录 / 读环境变量；首次写行时惰性创建目录。
- **FR-023**：同一目录内已有其它文件时，MUST NOT 删除 / 改写它们；同名 run 文件存在时
  MUST 追加，不截断。
- **FR-024**：每行写入的持久化强度锁定为 **`flush` 到操作系统即成功**：
  - MUST NOT 要求逐行 `fsync`（也 MUST NOT 以 `os.fsync` / `O_DSYNC` 等等价强度替代）；
  - 进程崩溃时，已 `flush` 的行 MUST 仍可被读回；
  - 操作系统崩溃 / 断电时，最后若干行 MAY 丢失；该丢失 **MUST NOT** 被判定为缺陷；
  - `flush` 失败仍按 FR-007 处理（不阻断运行 + 四路可感知）。
- **FR-025**：trace 文件权限锁定为 **`0o600`（仅本人可读写）**：
  - 新建 `trace-<run_id>.jsonl` 时，在 POSIX 上 MUST 以**不宽于 `0o600`** 的权限创建
    （实测 `mode & 0o077 == 0`）；`umask` 只能进一步收紧，MUST NOT 放宽；
  - 已存在的同名 run 文件 MUST NOT 被主动放宽权限；实现 MAY 尝试收紧到 `0o600`，
    收紧失败 MUST NOT 阻断运行（按 FR-007 记诊断即可）；
  - v1 **不提供**权限配置参数；MUST NOT 从环境变量 / 配置文件读取权限；
  - Windows 上不做 POSIX 权限位承诺，由平台 ACL 解释；MUST NOT 因无法设置
    POSIX 权限而阻断写入。
- **FR-026**：`FileTraceStore` 的句柄生命周期锁定为**逐行短生命周期**：
  - 每写一行 MUST 独立执行 `open → append → flush → close`；MUST NOT 在回调之间
    持有 run 文件的持久句柄；
  - MUST NOT 提供 `close()` / `__enter__` / `__exit__` / 上下文管理器；MUST NOT 依赖
    `__del__` / 解释器回收来释放句柄；
  - 因为每行都已 `flush` 并关闭，回调返回后 MUST 不留下打开的 trace 文件句柄；
    Windows 上 MUST 能在回调返回后立即重命名 / 删除该文件；
  - 同一 store 跨多次运行 / 多 `run_id` 时，MUST NOT 需要额外的关闭或清理步骤。
- **FR-027**：写入锁粒度锁定为**每个 `FileTraceStore` 实例一把 `threading.Lock`**：
  - MUST NOT 使用模块级 / 进程级全局锁（不同 store 实例 MUST 互不阻塞）；
  - MUST NOT 使用「每个 run 文件一把锁」的锁表（v1 不承担锁表的生命周期 / 清理）；
  - 锁 MUST 只包住单行写入临界区（记偏移 → 追加 → `flush` → 关闭）与
    `write_errors` / `last_error` 的更新；JSON 序列化 MUST 在锁外完成；
  - 用户回调 `on_error` MUST 在**锁外**调用，避免用户重入 store 时死锁；
  - 同一实例内多线程写入 MUST 串行；不同实例之间 MUST NOT 共享该锁。
- **FR-028**：写入失败后的重试策略锁定为**不重试**：
  - 某一行写入失败（含序列化 / `open` / 追加 / `flush` / `close` 任一环节）后，
    MUST NOT 对**同一行**重试；
  - MUST NOT 使用睡眠 / 退避 / 指数重试 / 后台重试队列；失败即丢弃该行并按 FR-007
    记诊断，随后继续尝试后续行；
  - 部分写入已按 FR-011 截断回写前偏移；截断失败也只记诊断，不再重试该行。

### Key Entities *(include if feature involves data)*

- **`FileTraceStore`**（L5，本 feature 新增）：JSONL 文件后端 / sink 实现。
  - 构造：`FileTraceStore(directory, *, on_error=None)`；
  - 写回调：`on_span_start` / `on_span_end` / `on_trace_record`；
  - 诊断：`write_errors` / `last_error`；
  - 不提供查询 API（B20F2 在同一对象上扩展）。
- **`Span`**（L1，B2F1 冻结，本 feature 原样消费）：11 字段；结束快照含完整
  `start_time` / `end_time` / `parent` / `run_id` / `thread_id` / `node` / `checkpoint_id`。
- **`TraceRecord`**（L5，B19F1 交付，本 feature 原样消费）：13 字段；
  `to_jsonable()` 是唯一稳定 JSON 视图；`error` 在内存为原异常、在 JSONL 为
  `{"type","message"}`。
- **JSONL 行**（内部持久化形态）：`kind="span"` 或 `kind="trace_record"` 的单个 JSON 对象。
- **Run 文件**（内部）：`<directory>/trace-<run_id>.jsonl`，每次运行一个，追加写入。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**：注入 `FileTraceStore(directory=tmp)` 后每次运行生成 **1 个**
  `trace-<run_id>.jsonl`；文件中每一条非空行均可被 `json.loads` 解析为 `dict`
  （成功率 **100%**）；空行 / 多行对象 / 尾随垃圾 **0** 处。
- **SC-002**：逐字段断言：`kind="span"` 行含 `Span` **11/11** 字段；`kind="trace_record"`
  行含 `to_jsonable()` **13/13** 字段；**每一行**都含 `run_id` / `thread_id` / `node` /
  `checkpoint_id`（C23 四项），字段名逐字一致；缺失字段 **0**。
- **SC-003**：未注入 store（含 `compile(tracer=None)`）时，目标目录**新文件数 == 0**、
  **新目录数 == 0**；设置 `LANGSMITH_TRACING=true` / `FREEGRAPH_TRACE_DIR=...` 后结果不变；
  只构造 `FileTraceStore` 不运行也**不创建**目录。
- **SC-004**：`directory` 不可写（只读目录 / 普通文件 / 模拟 I/O 失败）时，图运行结果与
  不注入时**逐字相同**、异常传播数 **0**；`write_errors > 0`、`last_error` 非空、
  `on_error` 被调用、日志有 WARNING；文件中**半行数 == 0**。
- **SC-005**：零出站：socket 监测夹具断言「框架出站 == 0」；无 HTTP / DNS / 任何网络调用。
- **SC-006**：基础安装依赖闭包**仍为空集**；`langchain*` / `langsmith` /
  `opentelemetry*` / `sqlite3` 的 import 次数 **== 0**；环境变量读取次数 **== 0**；
  `FileTraceStore` 的公开面**没有**查询方法（查询归 B20F2）。
- **SC-007**：同一 store 实例连续两次运行 ⇒ **2 个**不同 `trace-<run_id>.jsonl`；
  每个文件内的 `run_id` 唯一且与文件名一致；跨文件混写 **0**。
- **SC-008**：**当经 B19F1 注入且 `on_trace_record` 可用时**，并发场景（同一 super-step
  N 个节点）⇒ record 行数 **== N**、每个节点 span 行数 **== 1**；所有行仍可独立
  `json.loads`；字节交错 / 半行 **0**。接收端不含 `on_trace_record`（span-only 适配器 /
  纯 span sink）时允许 span-only，不适用 record 数等式。
- **SC-009**：**当经 B19F1 注入且 `on_trace_record` 可用时**，每个节点 record 行的
  `span_id` MUST 在同文件的 span 行中找到 `id` 相等的行；`record 数 == 节点 span 数`；
  模型 / 工具 span 行可无 record；错误 record 的 `error` 为 `{"type","message"}` 或
  `null`，原对象 / `repr` 出现次数 **== 0**。接收端不含 `on_trace_record`（span-only
  适配器 / 纯 span sink）时，允许 span-only（`record 数 == 0`），该情形不适用上述等式；
  `FileTraceStore` 本身始终写 record，故须经适配器才能得到该情形。
- **SC-010**：文件为 UTF-8、LF、无 BOM、无头部；`kind` 取值只允许 `"span"` 与
  `"trace_record"`；非 ASCII / 换行 / 控制字符经 JSON 转义后仍保持**一行一对象**。
- **SC-011**：`FileTraceStore` 不进入 `freegraph.graph` 门面；`import freegraph` 后
  `sys.modules` 中不出现 L5 写盘模块；**本 feature 新增模块 `_file_store.py`** 的
  L5 → L2 / L3 / L4 反向 import 数 **== 0**（既有 `_inject.py` 的 R-2 例外不回溯改写）。
- **SC-012**：`harness/verification/B20F1/manual-verification.md` 存在，且含
  **非空**的 JSONL 样例、读回命令与实际输出、失败感知证据、零出站证据、
  `__all__` 快照更新追认、**质量门禁 5 偏离声明**与发起者追认文字；并由
  `tests/runtime/test_b20f1_manual_record_guard.py` 自动核验（记录存在 / 五段式非空 /
  必需实测输出 / 偏离与追认标记）。
- **SC-013**：`harness/demo/README.md` 的「待锁定形态」清单中**不再**出现
  「本地 trace 存储目录的参数名」为待锁定项；对应位置标为**已锁定**并指向本 spec
  §「形态锁定裁定」；由 `tests/runtime/test_b20f1_manual_record_guard.py` 同时断言。
- **SC-014**：`directory` 按传入值使用：`~` / `$HOME` 等**不展开**、环境变量不参与；
  `run_id` 为空、含 `/` / `\`、或含任意 `.`（含 `.` / `..` / `a.b` / `a..b`）时，
  文件创建数 **== 0**、诊断计数 **+1**，运行不失败、无目录穿越；由
  `tests/observability/test_b20f1_run_id_safety.py` 判定。
- **SC-015**：持久化强度 = **每行 `flush` 即成功**：逐行 `fsync` 调用数 **== 0**；
  写入成功后无需等待磁盘同步即可继续；模拟「flush 成功但随后进程崩溃」时，已写行
  **仍可被 `json.loads` 读回**；断电丢最后若干行**不判失败**；由
  `tests/observability/test_b20f1_flush_durability.py` 判定。
- **SC-016**：POSIX 上新建的 `trace-<run_id>.jsonl` 权限 **不宽于 `0o600`**
  （`mode & 0o077 == 0`）；同目录其它文件权限不被改写；v1 无权限配置参数；
  Windows 用例只断言「不因权限设置失败而阻断」，不比较 POSIX 权限位。
- **SC-017**：`FileTraceStore` 的公开面**没有** `close` / `__enter__` / `__exit__`；
  每行写入后 trace 文件句柄数回到基线（无句柄泄漏）；N 行写入 ⇒ close 次数 **== N**；
  Windows 上回调返回后文件可立即重命名 / 删除（无残留锁）。
- **SC-018**：两个不同 `FileTraceStore` 实例并发写不同目录时，MUST NOT 因共享锁而互相
  阻塞（各自的锁计数独立）；同一实例内多线程写入 MUST 串行且每行完整；`on_error` 在锁外
  调用；构造「`on_error` 重入 store 再写一行」的用例，死锁数 **== 0**、行数正确。
- **SC-019**：注入「第 1 行写入失败、后续行正常」的故障后：第 1 行尝试次数 **== 1**
  （无重试）、诊断计数 **+1**；无 `sleep` / 退避调用；第 2 行仍成功落盘；
  失败行的部分内容 **== 0**（已截断）；图运行结果不变。

### 验收判据（= 立项书 §5.2 B20F1 小目标，逐条可判定）

> 小目标原文：trace 落盘，零出站

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | trace 落盘 | 注入后目录中生成 `trace-<run_id>.jsonl`，含 `kind="span"` 与 `kind="trace_record"` 行 |
| A2 | 零出站 | socket 夹具断言「框架出站 = 0」 |
| A3 | 每行可独立解析 + 含关联键 | 逐行 `json.loads` 成功；每行含 `thread_id` / `run_id` / `node` / `checkpoint_id`（C23） |
| A4 | 写入失败不阻断且可感知 | 只读目录下运行成功；`write_errors > 0` + `last_error` 非空 + `on_error` / WARNING；无半行 |
| A5 | 不启用零痕迹 | 未注入 ⇒ 目录 / 文件零新增；构造不运行也零新增；环境变量不改变行为 |

---

## Dependencies & Out of Scope

### Dependencies

- **B18F1**（已交付）：`Span` 11 字段 + 节点 / 模型 / 工具 span 生产；`asdict(span)`
  可被 `json.dumps` 序列化。
- **B19F1**（已交付）：`TraceSink` 注入点 `compile(tracer=...)`、`TraceRecord` 与
  `to_jsonable()`、可选 `on_trace_record`、`run_id` / `thread_id` / `node` /
  `checkpoint_id` 关联键、失败隔离与回调顺序。
- **B2F1 / C27 / C23**：`Span` / `TraceSink` / 查询契约与关联键字段约定（C27 查询侧
  本 feature **不实现**）。
- **B20F2**（后续）：查询 API + SQLite 后端；本 feature 的 `FileTraceStore` 是其
  可替换后端之一，文件格式仍属内部实现细节。

### Out of Scope

- **查询 API**（按 `run_id` / `thread_id` / 时间 / 节点名检索）——B20F2。
- **SQLite 后端**——B20F2（标准库 `sqlite3`，本 feature MUST NOT import）。
- **OTLP 导出 / 远端后端**——B21F1。
- **前端 / UI / Studio**——v2 / B26；Studio 只能走 B20F2 的查询 API，不直连 JSONL。
- **保留期 / 清理 / 轮转 / 压缩**——v1 不做；本 feature 不删除任何文件。
- **评测 / 数据集**——永不做。
- **跨进程并发写同一文件的事务性**——v1 不承诺；SQLite 场景归 B20F2。

---

## 质量门禁偏离（2026-11-21 · 发起者选择 A）

### 质量门禁 5 · 真实模型轮

| 项 | 内容 |
|---|---|
| 被偏离门禁 | 质量门禁 5「人工验证记录，含真实模型一轮」 |
| 根因 | B20F1 是 **L5 本地 JSONL 写入层**，验收对象是落盘格式 / 失败感知 / 零出站；本 feature 不交付模型 provider，真实模型轮不产生本 feature 的新判据。 |
| 判据未放宽 | 本地图 + 本地 sink 的 fake / 本地轮照常执行；JSONL 字段、四路诊断、零出站、默认关闭、`0o600`、per-instance 锁、逐行短生命周期等判据**一字未改**；人工记录五段式照常。 |
| 承接方 / 机制 | **B25F1（M4 · 双跑验收）**：在 B25F1 的人工验收中补真实模型轮（含 `FileTraceStore` 落盘证据）；承接条款已写入 `harness/features/B25F1_双跑验收与迁移说明.md` §「下游承接（B20F1）」。B21F1（OTLP）可选复用。B20F1 只交付 fake / 本地轮证据。 |
| 追认 | 发起者 2026-11-21 **选择 A（登记偏离）**；正式追认文字 + 确认人 + 日期落 `harness/verification/B20F1/manual-verification.md`，由发起者本人签署。 |

> **先例**：B19F1 已按同一口径登记「fake / 本地真实 sink 轮 + 真实模型轮由后续 feature 承接」；
> 本偏离**不降低**任何红线判据，也不改变 `B20F1` 的 A1–A5 验收。

---

## Assumptions

- **注入形态**按本 spec「形态锁定裁定」锁定为 `compile(tracer=FileTraceStore(directory=...))`；
  `FileTraceStore` 只持有目录与诊断回调，不构造 `SpanProducer`、不绑定运行时。
- **`Span` / `TraceSink` / `TraceRecord`** 均已由 B2F1 / B18F1 / B19F1 冻结；本 feature
  只**消费**，不重定义、不扩字段、不改 `TraceSink` 协议。
- **`TraceRecord.to_jsonable()`** 是 JSONL 记录行的唯一稳定视图；B20F1 MUST NOT 要求
  B19F1 提供第二套序列化，也 MUST NOT 从 `PregelTask` / `SuperStepResult` 重新猜。
- **失败感知**采用「计数 + 最后错误 + 可选回调 + 日志」四路；`write_errors` /
  `last_error` 是本 feature 的**公开诊断面**（不是查询 API）。
- **持久化强度** = **每行 `flush` 即成功**；不逐行 `fsync`。诊断型 trace 优先保证
  「不阻断执行」与吞吐；进程崩溃不丢已 flush 行，OS 崩溃 / 断电可丢最后若干行，
  该取舍**不判缺陷**。
- **trace 数据按敏感数据处理**：新建文件默认 `0o600`（仅本人可读写），v1 不提供权限
  配置参数；Windows 上由平台 ACL 解释，不做 POSIX 权限位承诺。
- **逐行短生命周期**：每行独立 `open → append → flush → close`，不提供 `close()` /
  上下文管理器 / 持久句柄；用户无需管理生命周期，进程内也不会留下 trace 文件句柄。
- **锁粒度 = 每个 store 实例一把锁**：不同实例互不阻塞；同一实例内的写入串行；不引入
  模块级全局锁或「每 run 锁表」。`on_error` 在锁外调用，允许用户重入 store。
- **失败不重试**：单行写入失败即丢弃并记诊断；不睡眠 / 不退避 / 不进后台重试队列；
  后续行继续尝试。trace 是诊断数据，不因落盘问题拖慢或阻塞图执行。
- **C27 ④「同一协议、后端可替换」**：B20F1 只锁定**写侧**接口（B19F1 sink 回调 +
  可选 `on_trace_record`）；查询方法的共同协议由 B20F2 在**同一 store 对象**上补齐
  （`FileTraceStore` 与 `SqliteTraceStore` 共享）。B20F1 MUST NOT 预定义查询面，
  以免与 B20F2 的 `TraceQuery` / 返回结构冲突。
- **文件格式**（`kind` / 文件名 / 行序 / UTF-8 / LF）是**内部实现细节**（C27 ⑤），
  但本 spec 将其写死以保证可重复验收；B20F2 查询实现 MUST 按此读取，Studio MUST NOT 直连。
- **默认关闭**：本 feature 不添加任何默认 sink、不读环境变量、不自动创建目录。
- **`directory` 必填**：没有默认目录；这是有意的「显式启用」设计，避免用户不知情落盘。
- **GIL / 锁**：每个 `FileTraceStore` 实例持有一把 `threading.Lock`；同一实例内并发写入
  由该锁串行化；不依赖 GIL 保证整行原子；不同实例不共享锁。
- **`BaseException`**：`KeyboardInterrupt` / `SystemExit` 等不被吞；只有 `Exception`
  范围的写入失败被隔离并诊断。
- **文档联动**：实现阶段 MUST 更新 `harness/demo/README.md` 的「待锁定形态」清单，
  更新 `harness/verification/README.md` 的 B20F1 行，并生成
  `harness/verification/B20F1/manual-verification.md`；该记录 MUST 由
  `tests/runtime/test_b20f1_manual_record_guard.py` 自动守卫，且 MUST 含
  质量门禁 5 偏离声明与发起者追认文字。
