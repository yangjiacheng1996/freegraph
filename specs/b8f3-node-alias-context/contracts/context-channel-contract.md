# 契约：B8F3 · `context` 独立通道（C21 / C22 运行期接线）

**Feature**: `B8F3` · **Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md)
**上游**: `langgraph` **1.2.11** / `langchain-core` **1.7.6**（取证于 2026-11-20）
**状态**: Phase 1 设计契约 · **可被 `/speckit.tasks` 追溯** · **MUST NOT** 被测试解析

---

## §0 公开面（零新增）

| 面 | 本 feature 之后 |
|---|---|
| `RunConfig` | 九字段**零改动**；`context` 已存在（C22） |
| `invoke(input, config=None)` | 签名**零改动**；**不新增** `context=` 关键字 |
| `stream(input, config=None, *, stream_mode=None)` | 签名**零改动**；**不新增** `context=` 关键字 |
| `StateGraph` / `CompiledGraph` | 签名**零改动**（alias 移除除外） |
| `freegraph.runtime.__all__` | 仍 **23**；不新增公开符号 |
| `freegraph.contracts` | 零新增类型 |
| 新私有模块 | `src/freegraph/runtime/_context.py`（`__all__ = []`） |

> **唯一来源**：`RunConfig.context`。mapping 形态 `{"context": ...}` 经
> `RunConfig.from_dict` 落成 `RunConfig.context`。

---

## §1 `context` 的来源与解析

### 1.1 解析顺序（逐字）

```text
config is RunConfig        → 原样使用（含 .context）
config is Mapping          → RunConfig.from_dict(config, ignore_unknown=True)
config is None             → RunConfig()
其它类型                    → 既有 resolve_config 的 TypeError（不改）
```

- `context` **MUST** 只从 `RunConfig.context` 读取。
- **MUST NOT** 读取 `configurable["context"]`。
- **MUST NOT** 新增 `invoke(..., context=...)` / `stream(..., context=...)`。
- `thread_id` / `metadata` / `tags` / `configurable` **MUST NOT** 被注入状态或 context view。

### 1.2 `RunConfig` 四核心字段（C22）

| 字段 | 类型 | 语义 |
|---|---|---|
| `thread_id` | `str \| None` | 会话标识 |
| `context` | `Any` | 运行期上下文（C21） |
| `metadata` | `Mapping[str, Any]` | 附加信息 |
| `tags` | `Sequence[str]` | 附加信息（构造期转 `tuple`） |

既有五个兼容字段（`configurable` / `max_concurrency` / `recursion_limit` / `run_name` /
`run_id`）保留，语义不变。

---

## §2 运行期载体

### 2.1 `_CONTEXT`（L2 私有）

| 项 | 契约 |
|---|---|
| 载体 | `contextvars.ContextVar[Any]` |
| 缺省 | `None` |
| 绑定 | `bind_context(context)`（contextmanager） |
| 读取 | `get_context()`（L2 私有） |
| 复原 | token + `finally`；**MUST NOT** 手工 `set(None)` |
| 公开面 | 不公开；`__all__ = []` |

### 2.2 绑定点

| 路径 | 绑定点 | 复原点 |
|---|---|---|
| `invoke` | `run_graph`（`src/freegraph/runtime/superstep.py:2178-2260`）· 与 `bind_run` 同一作用域 | `run_graph` 退出时 |
| `stream` | `StreamSession.__enter__`（`src/freegraph/runtime/_stream.py:74-118`） | `StreamSession.__exit__`（`:119-133`） |
| 低层入口 | **不绑定**（`run_super_step` / `run_super_steps` / `_stream_tick` 直接调用） | —— |

- **每次运行独立**：不跨 `invoke` / `stream` 泄漏。
- **嵌套**：不承诺；每个运行入口绑定一次。

---

## §3 节点入参

### 3.1 标准节点入参（`_node_input`）

```text
node_input = read_channels(subset)          # 稀疏 dict（C4）
if get_context() is None:
    return node_input                       # 精确 dict
else:
    return _ContextState(node_input, ctx)   # dict 子类 + 只读 .context
```

| 条件 | 类型 | `type(...) is dict` | `isinstance(..., dict)` | `.context` |
|---|---|---|---|---|
| `context is None` | `dict` | 真 | 真 | 无（`getattr` ⇒ `None`） |
| `context is not None` | `_ContextState` | 假 | 真 | 本次 context（同一对象） |

**映射不变量**：

- 键集 / 顺序 / 值 == `read_channels(subset)`（C4 / I-2）。
- **MUST NOT** 出现 `"context"` 键。
- `dict(view)` == 原稀疏 `dict`。
- `state.get(key, default)` 行为与普通 `dict` 一致。
- `.context` 只读；映射内容仍可变（与普通 `dict` 一致）；未知属性 ⇒ `AttributeError`。

### 3.2 `Send.arg`（fan-out）

| 条件 | 节点收到 | `.context` |
|---|---|---|
| `context is None` | `Send.arg` 原样 | 不注入 |
| `context is not None` 且 `Send.arg` 是 `dict` | `_ContextState(Send.arg, ctx)` | 本次 context |
| `context is not None` 且 `Send.arg` 非 `dict` | `Send.arg` 原样 | **不注入**（v1 边界） |

> `Send.arg` 是任意对象（C18）；只有 `dict` 能安全附加属性。非 `dict` 的
> `.context` **不承诺**；节点可自行从 `Send.arg` 读取所需数据。

### 3.3 `Command.goto` 目标

`Command.goto` 触发的目标在下一轮走**标准节点入参** ⇒ 与 §3.1 同款。

---

## §4 路由（条件边）

| 项 | 契约 |
|---|---|
| fresh 状态视图 | 普通 `dict`；**不含** `context` 键；**无** `.context` 属性 |
| 第二参 `config` | 用户交给 `invoke` / `stream` 的**原始** config（`RunConfig` / mapping / `None`） |
| 从哪读 context | 只能从第二参 `config` 读（若用户传 `RunConfig`）；**MUST NOT** 从 fresh 视图读 |
| `path_map` 查表 | 内部节点名；alias 已移除 |
| 失败信号 | 既有 `KeyError` / `ValueError` 家族；不新增错误类型 |

> 与上游同义：上游条件边可经 `Runtime.context` 读 context；freegraph 的对应物是
> 第二参原始 config。

---

## §5 状态 / 事件 / 持久化隔离

| 面 | 契约 |
|---|---|
| `GraphSpec.channels` | 无 context |
| `SchedulerState.channels` | 无 context |
| 归约 | context 不参与；无 context 写入 |
| `invoke()` 返回 | 键集 == schema 键集；无 `"context"` |
| `stream_mode="values"` | 每条 payload 无 `"context"`（中断时仅多 `"__interrupt__"`） |
| `updates` / `tasks` / `debug` | 与 context 无关；节点名仍内部名 |
| checkpoint | 本 feature 不读写 context；B14F1 另行处理 |
| `RunConfig.configurable` | 独立映射；不承载 context |

---

## §6 边界与失败

| 场景 | 行为 |
|---|---|
| `context=None` | 节点入参精确 `dict`；`getattr(state, "context", None)` ⇒ `None` |
| `context={}` / `0` / `""` | 非 `None` ⇒ `_ContextState`；`.context` 为对应对象 |
| `context` 是任意对象 | 原样透传；不校验 / 不 coerce |
| `context` 自己含 `"context"` 键 | 仍是 context 的值；**不**写进状态字典 |
| 用户修改 context 对象 | 同一 run 内节点读到同一对象；不承诺防御性拷贝 |
| 连续两次运行 | context 不泄漏；第二次的 context 只来自第二次 config |
| 只传 `configurable={"context": ...}` | **不**被当作 context；`context` 仍 `None` |
| 传 `invoke(..., context=...)` | `TypeError`（未新增该关键字） |
| `Send.arg` 非 `dict` | 原样传递；不注入 `.context`（v1 边界） |

---

## §7 验收映射

| 判据 | 验证面 |
|---|---|
| SC-001 | 节点读 context；`invoke` / `values` 无 context |
| SC-002 | `RunConfig` 四字段可读；`tags` 为 `tuple` |
| SC-003 | context view 无注入的 `configurable` 键 |
| SC-005 | 路由 fresh 视图无 context；第二参可携带 |
| SC-006 | 无 context ⇒ `type(state) is dict`；有 context ⇒ `dict` 子类 |
| SC-007 | D-137…D-144 |
| SC-008 | 零依赖 / 零环境变量 / 零出站 |

---

## §8 禁止事项（逐条）

1. **MUST NOT** 把 context 放进状态 key / channels / 归约器。
2. **MUST NOT** 把 context 写进 `RunConfig.configurable` 或从其中读取。
3. **MUST NOT** 新增 `invoke/stream(context=...)` 关键字。
4. **MUST NOT** 改 `run_graph` / `run_super_step` / `run_super_steps` / `_stream_tick`
   的签名。
5. **MUST NOT** 新增公开 L2 符号 / 公开 context getter。
6. **MUST NOT** 在路由 fresh 视图中加入 context。
7. **MUST NOT** 把 context 持久化到 checkpoint。
8. **MUST NOT** 在 `context is None` 时改变节点入参的精确 `dict` 类型。
9. **MUST NOT** 为 `Send.arg` 非 `dict` 的对象强行包装（改变类型 / 身份）。
10. **MUST NOT** import `langchain*` / `langgraph*` / `langsmith` 或读环境变量。
