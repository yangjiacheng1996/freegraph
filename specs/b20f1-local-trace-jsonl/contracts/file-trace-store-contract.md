# Contract: 本地 Trace 存储（`FileTraceStore` · JSONL）

**Feature**: B20F1 · **Date**: 2026-11-21 · **Spec**: [../spec.md](../spec.md)
**Plan**: [../plan.md](../plan.md) · **Data model**: [../data-model.md](../data-model.md)

> `FileTraceStore` 是 **L5** 的本地 trace 存储后端（写入侧）。它实现 B19F1 的
> sink 鸭子类型接口，**不**改变 `TraceSink` 三方法协议；**不**提供查询 API
> （B20F2）。文件格式是 C27 ⑤ 的**内部实现细节**，但本 feature 写死以保证可验收。

---

## 1. 公开面

```python
class FileTraceStore:
    def __init__(
        self,
        directory: str | os.PathLike[str],
        *,
        on_error: Callable[[BaseException], None] | None = None,
    ) -> None: ...

    @property
    def write_errors(self) -> int: ...

    @property
    def last_error(self) -> str | None: ...

    def on_span_start(self, span: Span) -> None: ...
    def on_span_end(self, span: Span) -> None: ...
    def on_trace_record(self, record: TraceRecord) -> None: ...
    def current_span(self) -> Span | None: ...
```

| 规则 | 内容 |
|---|---|
| 注入 | `compile(tracer=FileTraceStore(directory=...))`（B19F1 已锁定） |
| `directory` | 必填；`str` / `os.PathLike[str]`；无默认；不展开 `~` / env |
| `on_error` | 可选；每次持久化失败调用一次；**锁外**；自身异常被吞并记日志 |
| 诊断 | `write_errors` / `last_error` 只读；实例级；跨 run 累计 |
| 回调 | `on_span_start` no-op；`on_span_end` 写 span 行；`on_trace_record` 写 record 行 |
| `current_span` | 恒 `None`（sink 不是 producer） |

**MUST NOT** 提供：`close()` / `__enter__` / `__exit__` / 上下文管理器 / 查询方法。

---

## 2. 文件粒度与命名

| 项 | 规则 |
|---|---|
| 文件 | 每个 `run_id` 一个 `<directory>/trace-<run_id>.jsonl` |
| 目录 | 惰性创建（第一次写行时；`parents=True, exist_ok=True`） |
| 构造 | **零文件系统副作用**；只保存参数 / 初始化锁与诊断 |
| 写入模式 | 追加（`append`）；同名文件续写；不截断 |
| 编码 | UTF-8（无 BOM）；`\n`（LF）；`ensure_ascii=False` |
| 头部 | 无头部 / 尾部 / 注释 / 空行 |
| `run_id` 安全 | MUST 匹配 `^[A-Za-z0-9][A-Za-z0-9_-]*$`（**无点号**）；含任意 `.`（含 `..`）或路径分隔符 ⇒ 诊断 + 跳过 |
| 空 `run_id` | 拒绝；不写；不伪造新 id |
| 目录权限 | 默认 `mkdir`（受 umask）；不额外 `chmod` |
| 文件权限 | POSIX 新建 `0o600`；`umask` 只能收紧；已存在不放宽；v1 无配置 |

---

## 3. 写入语义

| 事件 | 行为 |
|---|---|
| `on_span_start(span)` | **no-op**；不写盘 / 不建目录 |
| `on_span_end(span)` | 写 1 条 `kind="span"` 行（`Span` 11 字段 + `kind`） |
| `on_trace_record(record)` | 写 1 条 `kind="trace_record"` 行（`to_jsonable()` 13 字段 + `kind`） |
| 行序 | 保留 B19F1 回调到达顺序；同节点 record 在 span 前；不排序 / 不聚合 |
| 并发 | 每实例一把锁；每行完整、字节不交错 |
| 句柄 | 每行独立 `open → append → flush → close`；无持久句柄 |
| 持久化 | 每行 `flush` 到 OS 即成功；**不**逐行 `fsync` |
| 重试 | **不重试**；失败行丢弃；后续行继续 |
| 半行 | 写前记偏移；失败截断回该偏移；截断失败只记诊断 |

> 行结构 / 字段表 / 示例见 [jsonl-record-contract.md](./jsonl-record-contract.md)。
> **span-only 例外**：接收端不含 `on_trace_record`（span-only 适配器 / 纯 span sink）时，
> 允许只写 span 行；该情形 `trace_record` 行数 == 0，且 MUST NOT 被判为缺陷。
> `FileTraceStore` 本身始终实现 `on_trace_record`，需经适配器才能进入该情形。

---

## 4. 失败语义（永不阻断运行）

| 失败点 | 处置 |
|---|---|
| payload 构造 / `to_jsonable()` / `json.dumps` | `Exception` 捕获；不写；诊断 |
| `run_id` 空 / 不安全 | `ValueError` 捕获；不写；诊断 |
| `mkdir` / `stat` / `os.open` | 捕获；诊断 |
| `write` / `flush` / `close` | 捕获；截断回写前偏移；诊断 |
| 截断失败 | 只记日志；不重试；运行继续 |
| `on_error` 抛 `Exception` | 吞并记日志；不递归 |
| `on_error` 抛 `BaseException` | **不吞**（传播） |
| 写入 `BaseException` | **不吞**；只有 `Exception` 被隔离 |

### 4.1 四路诊断

| 通道 | 形态 | 判定 |
|---|---|---|
| 计数 | `write_errors: int`（只读，初值 0，单调递增） | 失败一次 ⇒ +1 |
| 最后错误 | `last_error: str \| None` | `f"{type(exc).__name__}: {exc}"` |
| 回调 | `on_error(exc)`（锁外，最多一次/失败；重入不递归） | 提供时调用 |
| 日志 | `logging.getLogger(__name__).warning(..., exc_info=exc)` | 失败一次 ⇒ 一条 WARNING |

**不变量**：`write_errors` 只统计持久化失败；`on_error` 自身异常不增加计数；
`BaseException` 不被吞；失败后 **MUST NOT** 留下半行 JSON。

---

## 5. 并发 / 锁

| 规则 | 内容 |
|---|---|
| 锁粒度 | **每个 `FileTraceStore` 实例一把 `threading.Lock`** |
| 不共享 | 不同实例 MUST NOT 共享锁；MUST NOT 用模块级 / 进程级全局锁 |
| 不建锁表 | MUST NOT 用「每 run 文件一把锁」的锁表 |
| 锁内 | 单行写入临界区（记偏移 → 追加 → `flush` → 关闭）+ 诊断更新 |
| 锁外 | JSON 序列化 + `on_error` |
| 同实例多线程 | 串行；每行完整 |
| 跨实例 | 互不阻塞 |
| 跨进程 | v1 不承诺事务性 |

---

## 6. 生命周期

| 规则 | 内容 |
|---|---|
| 每行 | 独立 `open → append → flush → close` |
| 持久句柄 | **MUST NOT**（回调之间不持有） |
| `close()` | **MUST NOT** 提供 |
| 上下文管理器 | **MUST NOT** 提供 |
| `__del__` 依赖 | **MUST NOT** |
| 回调返回后 | 无打开的 trace 文件句柄；Windows 上可立即 rename / delete |
| 跨 run | 同一 store 可直接用于多次 `invoke()` / `stream()`；无需额外清理 |

---

## 7. 默认关闭 / 零副作用

| 场景 | 必须 |
|---|---|
| 未注入 tracer（或 `compile(tracer=None)`） | 0 文件 / 0 目录 / 0 回调 / 不读 env |
| 只构造 `FileTraceStore(directory=tmp)` 不运行 | 0 目录 / 0 文件 |
| `FREEGRAPH_TRACE_DIR` / `LANGSMITH_TRACING` 等 env 存在 | 不改变行为；只认显式 `directory` |
| `import freegraph` | 不加载 L5；不创建任何文件 |

---

## 8. 明确不做

- 查询 API / `TraceQuery` 过滤 / 结果集合 —— B20F2。
- SQLite 后端 / `sqlite3` —— B20F2。
- OTLP 导出 / 远端后端 —— B21F1。
- 前端 / UI / Studio —— v2 / B26。
- 保留期 / 清理 / 轮转 / 压缩 —— v1 不做。
- 跨进程并发事务性 —— v1 不承诺。
- 评测 / 数据集 —— 永不做。

---

## 9. 验收映射

| 判据 | 覆盖 |
|---|---|
| A1 trace 落盘 | 注入后生成 `trace-<run_id>.jsonl`，含 span + record 行 |
| A2 零出站 | socket 夹具「框架出站 == 0」 |
| A3 每行可解析 + 关联键 | 逐行 `json.loads`；含 `thread_id` / `run_id` / `node` / `checkpoint_id` |
| A4 失败不阻断 + 可感知 | 只读目录；`write_errors > 0` + `last_error` + `on_error` / WARNING；无半行 |
| A5 不启用零痕迹 | 未注入 / 只构造 / env 变量 ⇒ 0 文件 / 0 目录 |
