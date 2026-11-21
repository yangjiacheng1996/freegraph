# Research: B20F1 · 本地 Trace 存储：JSONL 文件后端（零依赖）

**Date**: 2026-11-21
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**Baseline**: `.venv/bin/python -m pytest -q --tb=no` ⇒ **1917 passed, 6 skipped**（2026-11-21 实跑）
**Upstream**: `langgraph 1.2.11` / `langchain-core 1.7.6` / `langsmith 0.14.17`（`.venv` 实测）

> 本文件只记录**设计决策**（Decision / Rationale / Alternatives），不重复 spec 的 FR/SC。
> 上游行为断言来自 spec 的 P-01…P-07 / E-1…E-3；本 feature 不新增上游行为探针。

---

## D-01 · 公开载体：`FileTraceStore(directory=...)` + `compile(tracer=...)`

- **Decision**：`freegraph.observability.FileTraceStore(directory: str | os.PathLike[str],
  *, on_error: Callable[[BaseException], None] | None = None)`；经 B19F1 已锁定的
  `StateGraph.compile(*, tracer=...)` 注入。`directory` 必填、无默认值。
- **Rationale**：spec 已锁定；复用 B19F1 注入点，不新增第二种形态；`directory` 与
  B20F2 的 `SqliteTraceStore(database=...)` 可并列；与 Q6 / `harness/notes` 的
  `FileTraceStore`（JSONL，零依赖）命名一致。
- **Alternatives considered**：
  - 扩 `RunConfig.trace_dir` ⇒ 破 L1 9 字段冻结面 / 纯数据纪律。
  - 读 `FREEGRAPH_TRACE_DIR` 等环境变量 ⇒ 违反零环境变量；默认关闭必须由显式注入决定。
  - 单文件全局 `trace.jsonl` ⇒ 无法按 `run_id` 独立归档 / 无法满足 P1。
  - 用户直接传文件路径 ⇒ 无法按 run 自动分文件；`directory` 语义更清晰。

---

## D-02 · 文件粒度：每个 `run_id` 一个 `trace-<run_id>.jsonl`

- **Decision**：`<directory>/trace-<run_id>.jsonl`；目录惰性创建（第一次真正写行时，
  `parents=True, exist_ok=True`）；写入模式 = 追加；已有同名文件则续写，不截断。
- **Rationale**：C22「一次运行一个 `run_id`」；同一 store 实例可跨多次 `invoke()` /
  `stream()` 复用；不同 run 不混写；构造 store 不产生副作用。
- **Alternatives considered**：
  - 单文件全局 `trace.jsonl` ⇒ 混写 / 无法按 run 归档。
  - 每次写一行建一个文件 ⇒ 文件爆炸 / 不可读。
  - 构造时创建目录 ⇒ 只构造不运行也会有副作用（违反 FR-005 / SC-003）。

---

## D-03 · 行结构：`kind="span"` + `kind="trace_record"`

- **Decision**：文件无头部 / 尾部 / 注释；每行一个 JSON 对象，`kind` 区分：
  - `kind="span"`：`Span` 全部 **11 字段** + `kind`；
  - `kind="trace_record"`：`TraceRecord.to_jsonable()` 全部 **13 字段** + `kind`。
  - span 字段用**手工 11 字段映射**，不用 `dataclasses.asdict`；`attributes` / `context`
    走 `dict(...)` 浅拷贝。record 直接 `record.to_jsonable()`。
- **Rationale**：`TraceRecord` 不含 `Span` 的 `name` / `attributes` / `parent` /
  `start_time` / `end_time` / `context`，只落 record 无法满足 FR-003；两者通过
  `span_id` ↔ `id` 关联。手工映射避免 `asdict` 对嵌套对象的深拷贝 / 额外失败面，
  且把 11 字段契约显式写在代码里。`kind` 是唯一新增字段。**当经 B19F1 注入且
  `on_trace_record` 可用时**，每个节点任务同时有 span + record；接收端不含
  `on_trace_record`（span-only 适配器 / 纯 span sink）时允许 span-only（见 spec Edge
  Cases）；`FileTraceStore` 本身始终写 record。
- **Alternatives considered**：
  - 只落 record ⇒ 缺 Span 字段。
  - 只落 span ⇒ 缺 input/output/triggers/concurrency/barrier。
  - 嵌套 `{"kind":"span","span":{...}}` ⇒ 多一层；与 spec 写死的扁平结构不符。
  - `dataclasses.asdict(span)` ⇒ 深拷贝 / 对嵌套对象更敏感；无必要。
  - 把 record 塞进 `Span.attributes` ⇒ 破 B18F1 Q11 / 11 字段。

---

## D-04 · 写入时机：span 在 `on_span_end`，record 在 `on_trace_record`

- **Decision**：`on_span_start` 恒 no-op（不写盘、不建目录）；`on_span_end` 写 span 行；
  `on_trace_record` 写 record 行。行序 = B19F1 回调到达顺序；同一节点任务 record 行在
  span 行之前。
- **Rationale**：开始快照 `end_time=None` 是半成品；结束快照是 `end_time` 已填的
  新实例。B19F1 已锁定 `on_span_start → on_trace_record → on_span_end`；本 feature
  只消费，不重排。
- **Alternatives considered**：
  - 开始/结束都写 ⇒ 重复 span / 半成品。
  - 结束后写 record ⇒ 违背 B19F1 顺序 / 丢失「record 内 current_span = 节点 span」的语义。
  - 排序 / 按时间聚合 ⇒ 并发到达顺序不稳定；确定性由字段内顺序承载。

---

## D-05 · 持久化：每行 `flush`，不逐行 `fsync`；逐行短生命周期

- **Decision**：每行写完 `flush` 到操作系统即视为成功；**MUST NOT** 逐行 `fsync`；
  每行独立 `open → append → flush → close`；不提供 `close()` / 上下文管理器 / 持久句柄。
- **Rationale**：用户 clarify 明确选择；诊断型 trace 优先「不阻断执行」与吞吐；
  进程崩溃不丢已 flush 行，OS 崩溃 / 断电可丢最后若干行（spec 明确不判缺陷）。
  逐行开/关避免线程间句柄泄漏与「忘了 close」的 API 负担。
- **Alternatives considered**：
  - 每行 `fsync` ⇒ 高频磁盘同步，拖慢运行；用户已拒绝。
  - 持久句柄 + `close()` / 上下文管理器 ⇒ 增加生命周期 API / 泄漏风险；用户已拒绝。
  - 后台线程批量写 ⇒ 引入线程 / 关闭 / 退出时 flush 的复杂度；超出 820 行目标。

---

## D-06 · 权限：POSIX `0o600`，不提供配置

- **Decision**：新建文件用 `os.open(..., 0o600)`；`umask` 只能进一步收紧；已存在文件
  **不主动放宽**（可选收紧在 v1 不实现）；不提供权限配置参数；Windows 由平台 ACL 解释。
- **Rationale**：用户 clarify 选择「仅本人可读写」；trace 可能含用户状态 / 消息 /
  工具参数，按敏感数据处理；`0o600` 是安全的默认。
- **Alternatives considered**：
  - 遵循 umask ⇒ 可能同组 / 其他用户可读。
  - 可配置权限 ⇒ 增加 API 面，用户可能误设过宽。
  - 父目录也 `0o700` ⇒ spec 未要求；目录权限留给用户 / 部署环境，本 plan 不锁定。

---

## D-07 · 并发：每 store 实例一把锁；`on_error` 锁外

- **Decision**：每个 `FileTraceStore` 实例持有自己的 `threading.Lock`；不共享模块级 /
  进程级全局锁，不建「每 run 锁表」。序列化在锁外；锁内只做「记偏移 → 追加 →
  `flush` → 关闭」与 `write_errors` / `last_error` 更新；`on_error` 在锁外调用；
  用 `threading.local` 防 `on_error` 重入后的递归回调。
- **Rationale**：上游没有本地 JSONL，也没有 per-run 文件锁；其锁是 per-Client / 全局
  （`langsmith/client.py:149,1344,1346`），写入侧用队列 + 后台线程
  （`langsmith/_internal/_background_thread.py:327-377`）。per-instance 锁最接近
  upstream 的 per-Client 锁，且避免「每 run 锁表」生命周期；trace 写入不是高频热点。
- **Alternatives considered**：
  - 模块级全局锁 ⇒ 不同 store 实例互相阻塞。
  - 每 run 一把锁 ⇒ 需要锁表 / 引用计数 / 清理，复杂度和死锁风险更高。
  - 不加锁 ⇒ 跨平台 `O_APPEND` 原子性不可靠；长行可能交错。

---

## D-08 · 失败：四路诊断 + 不重试 + 截断半行

- **Decision**：`Exception` 范围内的写入失败（序列化 / `open` / 追加 / `flush` /
  `close`）不传播；`write_errors += 1`；`last_error = f"{type(exc).__name__}: {exc}"`；
  可选 `on_error(exc)`（锁外；自身异常被吞并记日志）；`logging.WARNING`（含异常栈）；
  **不重试**；部分写入截断回写前偏移。
- **Rationale**：宪法原则 IV；静默吞错会让用户以为 trace 已记录；四路覆盖「始终可用
  的计数 / 最后错误」与「调用方回调 / 日志」；不重试避免因磁盘 / 权限问题阻塞图执行。
- **Alternatives considered**：
  - 静默吞错 ⇒ 虚假安全感。
  - 只日志 ⇒ 程序化不可感知；只回调 ⇒ 未提供回调时不可感知。
  - 重试 / 睡眠 / 后台队列 ⇒ 可能阻塞或增加生命周期；用户已拒绝。
  - 不截断 ⇒ 留下半行，破坏「每行可 `json.loads`」。

---

## D-09 · JSON 编码：UTF-8 / LF / `ensure_ascii=False` / 一行一对象

- **Decision**：`json.dumps(obj, ensure_ascii=False)`（默认分隔符）；每行以 `\n` 结束；
  UTF-8 无 BOM；`kind` 放在对象第一个键；无头部 / 尾部 / 注释；非有限浮点遵循
  Python `json` 的 `NaN` / `Infinity` 语义（`json.loads` 可解析；不额外改写）。
- **Rationale**：`ensure_ascii=False` 让中文 / Unicode 可直接阅读；默认分隔符比紧凑
  更易读；`\n` 保证跨平台一致；不另造第二套 `json_safe`（B19F1 已提供）。
- **Alternatives considered**：
  - `ensure_ascii=True` ⇒ 中文不可读。
  - 紧凑分隔符 ⇒ 文件更小但可读性略差；无必要。
  - 头部元数据行 ⇒ 违反「每行都是 span / record」与 A3 的每行关联键。
  - `allow_nan=False` ⇒ 含 `NaN` 的合法 `json_safe` 值会被丢弃；与 B19F1 的
    `json.dumps` 口径不一致。

---

## D-10 · `run_id` 文件名安全

- **Decision**：`run_id` 必须匹配 `^[A-Za-z0-9][A-Za-z0-9_-]*$`（**无点号**）；否则记诊断
  并跳过该行，**不**写文件、**不**伪造新 `run_id`。内部 B18F1 / B19F1 的 `uuid4().hex`
  天然满足。
- **Rationale**：防目录穿越（`/` / `\` / `.` / `..`）与 Windows 非法文件名（`:` / `*` /
  `?` 等）；「含任意 `.` 即拒绝」与 spec FR-014 / SC-014 逐字一致；严格 allowlist 比
  「只拒绝几个字符」更可预测；`run_id` 是运行时生成的标识，不应由用户任意控制。
- **Alternatives considered**：
  - 只拒绝 `/` / `\` / `..` ⇒ Windows 仍可能非法 / 不可移植。
  - 把不安全字符替换为 `_` ⇒ 可能碰撞 / 静默改标识；拒绝更明确。
  - 用 `uuid4()` 重新生成 ⇒ 伪造 id，违反 C22 / spec。

---

## D-11 · 分层与导出：L5 私有模块；只依赖标准库 + L1 + 同层

- **Decision**：新增 `src/freegraph/observability/_file_store.py`；imports：
  `json` / `os` / `pathlib` / `re` / `threading` / `logging` / `collections.abc` /
  `typing`（标准库）· `freegraph.contracts.trace.Span`（L1）· `._record.TraceRecord`
  （同层 L5）。导出 `FileTraceStore` 到 `freegraph.observability.__all__`；不进
  `freegraph.graph` 门面；`import freegraph` 不加载 L5。
- **Rationale**：ARCH-1（L5 只依赖 L1，同层允许）· ARCH-2（顶层惰性）· ARCH-3
  （只消费纯数据）。B19F1 已把 `TraceRecord` 放 L5 `_record.py`；复用而不重复。
- **Alternatives considered**：
  - 放 L1 ⇒ 存储行为不属于契约层；且 L1 零内部 import。
  - 放 L2 ⇒ L2 不应负责持久化；且 L2 禁止 import L5。
  - 进门面 ⇒ 破门面 8 符号 / 门面不得 import L5（G17）。
  - 在 L5 重新定义 `TraceRecord` ⇒ 重复载体 / 漂移。

---

## D-12 · 测试 / 验收 / 差分 / 文档落点

- **Decision**：
  - 单元 / 集成 / 失败 / 并发 / 权限：`tests/observability/test_b20f1_*.py`；
  - 契约 / 门禁：`tests/contracts/test_b20f1_contracts.py` / `test_b20f1_gates.py`；
  - 冻结面更新：`test_api_snapshot.py` / `test_b19f1_lazy.py` / `test_b19f1_gates.py` /
    `test_architecture.py`（只增）；
  - 差分：`tests/differential/test_b20f1_local_trace_parity.py`（D-401…D-408；
    上游缺席即 skip）；
  - 一键验收：`harness/verification/B20F1/acceptance.py`（A1–A5）；
  - 守卫：`tests/runtime/test_acceptance_script.py` 追加 B20F1；
  - 覆盖闭包：`test_b20f1_run_id_safety.py`（SC-014）· `test_b20f1_flush_durability.py`
    （SC-015）· `test_b20f1_span_only.py`（INC-01）· `test_b20f1_manual_record_guard.py`
    （SC-012 / SC-013，T053）；
  - 文档：`harness/demo/README.md` 行改「已锁定」；`harness/verification/README.md`
    更新 B20F1 行；
  - 人工：`harness/verification/B20F1/manual-verification.md`。
- **Rationale**：原则 VI 判据级覆盖；原则 V 人工门禁；证据门禁要求 JSONL 样例与
  实际输出；差分 D-401…D-408 与 spec §3 对齐。
- **Alternatives considered**：
  - 只写单元测试 ⇒ 不覆盖真实图 / stream / 多 run / 失败感知。
  - 不写差分 ⇒ 违反原则 XI 的差分场景组要求。
  - 不改 README ⇒ 违反 spec FR-017 / SC-013。

---

## D-13 · 质量门禁 5：登记偏离（2026-11-21 · 发起者选择 A）

- **Decision**：B20F1 只跑本地图 + 本地 sink 的 fake / 本地轮；真实模型轮由 **B25F1（M4 · 双跑验收）**
  承接（B21F1 可选复用）；正式追认文字 + 确认人 + 日期落 `manual-verification.md`，由发起者本人签署。
- **Rationale**：B20F1 是 L5 本地 JSONL 写入层，不交付模型 provider；真实模型轮不产生本 feature
  的新判据。按宪法 v1.6.0「质量门禁的分阶段落地」登记偏离，**判据零放宽**。
- **Alternatives considered**：补真实模型轮（增加 provider / 网络 / 费用，且对本 feature 无新增判据）；
  声明完全不适用（与宪法 MUST 冲突，需更强论证）。

---

## D-14 · SC-012 / SC-013 文档守卫

- **Decision**：新增 `tests/runtime/test_b20f1_manual_record_guard.py`（T053），在 T048 / T049 之后执行；
  断言人工记录存在、五段式非空、含 JSONL 样例 / 读回 / 失败感知 / 零出站 / `__all__` / 质量门禁 5 偏离 /
  发起者追认，并断言 `harness/demo/README.md` 行已锁定。
- **Rationale**：宪法原则 VI v1.13.0 要求人工门禁类 SC 由自动文档守卫承担；「写记录 / 审计」不构成判定覆盖。
- **Alternatives considered**：只靠人工审计（不满足 v1.13.0）；把守卫放在记录之前（永久红 CI）。

---

## 已决项（原「未决项」已收敛）

**无未决项。** spec 的 5 条 clarify 轮裁定 + 7 条 spec 阶段锁定 + 本文件 D-01…D-14 已覆盖
全部设计点；以下实现细节均已由 data-model / contracts / tasks 写死：

- `last_error` 精确文本 = `f"{type(exc).__name__}: {exc}"`；`logging` 用
  `logging.getLogger(__name__).warning(..., exc_info=exc)`。
- `write_errors` 只统计**持久化失败**；`on_error` 自身抛出的 `Exception` 只记日志，
  不再次增加计数（避免递归 / 双计数）。
- `on_error` 重入：`threading.local` 标记；重入写入失败不再调用 `on_error`。
- 写入失败时：`st_size` 在 `os.open` 前读取；截断用 `os.truncate(path, before)`；
  截断失败只记日志。
- 文件权限：`os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)`；
  `os.fdopen(fd, "a", encoding="utf-8", newline="\n")`；不额外 `chmod` 已存在文件。
- JSON 键序：`kind` 第一；span 行按 `Span` 字段声明序；record 行按
  `to_jsonable()` 的顺序。
- 差分 D-404（零出站）用 `socket` 监测夹具，不实际发请求；D-407 依赖闭包复用
  B19F1 D-307 口径。
