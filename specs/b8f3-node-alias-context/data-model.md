# 数据模型（Data Model）—— B8F3 的 `context` 独立通道与 alias 移除

**Feature**: `B8F3` · **Spec**: [spec.md](./spec.md)
**契约**: [contracts/context-channel-contract.md](./contracts/context-channel-contract.md) ·
[contracts/alias-removal-contract.md](./contracts/alias-removal-contract.md)
**核实环境**: CPython **3.11** · 上游 `langgraph` **1.2.11**（取证于 2026-11-20）

> **落位**：`context` 的运行期载体落 **L2 私有**（`src/freegraph/runtime/_context.py`）；
> 节点入参包装落 L2（`superstep.py` 的 `_node_input` / `_run_round`）；
> invoke 绑定落 L2（`run_graph`）；stream 绑定落 L2（`StreamSession`）。
> **零新增公开 L2 符号**（`freegraph.runtime.__all__` 仍 **23**）。
> **MUST NOT** 被测试解析（测试**直接断言行为**）。

---

## 1. 实体总览

| 实体 | 角色 | 生命周期 | 可变性 |
|---|---|---|---|
| **`RunConfig`（L1 既有）** | 单次运行的配置载体（C22） | 单次运行 | frozen |
| **`RunConfig.context`** | 运行期上下文的唯一来源 | 单次运行 | 原对象（不复制） |
| **`_CONTEXT`（L2 私有）** | 当前运行的 context 的 `ContextVar` | 单次运行 | token 绑定 / 复原 |
| **`_ContextState`（L2 私有）** | 节点入参的 context-bearing `dict` 子类 | 单次节点执行 | `.context` 只读 |
| **标准节点入参** | `read_channels(...)` 的稀疏 `dict` | 单次节点执行 | 每次新建 |
| **`Send.arg`（L1 既有）** | fan-out 的入参（任意对象） | 单次 fan-out 任务 | 原对象 / 按需包装 |
| **`_NodeRecord`（L3 私有）** | 构建期节点登记项 | 构建期 / 编译快照 | frozen |
| **`_BuilderSpec`（L3 私有）** | 构建期冻结快照 | 编译期 | frozen |
| **`Node.name`（L1 既有）** | 图导出的**展示名**（不是 C25 别名） | 图导出 | frozen |

> **术语防混**：`Node.name` 是 `get_graph()` 的图节点展示字段，缺省归一为 `id`；
> 它**不是** C25 的「节点注册别名」。C25 **已正式作废**（编号保留不复用；active 契约清单 = C1–C24 + C26–C27）。

---

## 2. `RunConfig`（C22 · 零改动）

| 字段 | 类型 | 缺省 | 语义 | 本 feature |
|---|---|---|---|---|
| `thread_id` | `str \| None` | `None` | 会话标识 | 零改动 |
| `context` | `Any` | `None` | 运行期上下文（C21） | **唯一来源**；运行期接线 |
| `metadata` | `Mapping[str, Any]` | 空映射 | 附加信息 | 零改动；不注入状态 / context |
| `tags` | `Sequence[str]` | 空序列 | 附加信息（构造期转 `tuple`） | 零改动；不注入状态 / context |
| `configurable` | `Mapping[str, Any]` | 空映射 | 上游兼容字段 | 零改动；**不承载 context** |
| `max_concurrency` | `int \| None` | `None` | 并发上限 | 零改动 |
| `recursion_limit` | `int \| None` | `None` | 递归上限 | 零改动 |
| `run_name` | `str \| None` | `None` | 上游兼容 | 零改动 |
| `run_id` | `str \| None` | `None` | 上游兼容（运行时忽略其事件 id 用途） | 零改动 |

**解析规则**：

```text
config is RunConfig        → 原样使用
config is Mapping          → RunConfig.from_dict(config, ignore_unknown=True)
config is None             → RunConfig()
```

- `RunConfig.context` 只从该字段读取；**MUST NOT** 读 `configurable["context"]`。
- 本 feature **MUST NOT** 新增 `invoke(..., context=...)` / `stream(..., context=...)`。

---

## 3. `context` 通道（C21）

### 3.1 `_CONTEXT`（L2 私有）

| 项 | 契约 |
|---|---|
| 类型 | `contextvars.ContextVar[Any]` |
| 名称 | `freegraph_run_context`（私有；不冻结字符串） |
| 缺省 | `None` |
| 绑定入口 | `bind_context(context)`（contextmanager） |
| 读取入口 | `get_context()`（L2 私有） |
| 复原 | `bind_context` 的 `finally` 用 token 复原；**MUST NOT** 手工 `set(None)` |
| 嵌套 | 不承诺嵌套；`run_graph` / `StreamSession` 各自在入口绑定一次 |
| 公开面 | **不公开**；`_context.py` 的 `__all__ = []` |

### 3.2 生命周期

```text
invoke:
  CompiledGraph.invoke
    → run_graph(spec, input, config)
      → resolve_config(config) → RunConfig
      → with bind_run(table), bind_context(run_config.context):
          → _first_graph / _resume_graph
            → ... → _node_input(...) 读取 get_context()

stream:
  CompiledGraph.stream
    → StreamSession(spec, input, config, run_id)
      → __enter__:
          resolve_config(config) → RunConfig
          bind_run(new_run_table())
          bind_context(run_config.context)
      → _stream_tick → _run_single_step → _run_round → _node_input(...)
      → __exit__:
          reset stream context
          reset run context
```

- **每次运行独立**：contextvar 在运行入口绑定，运行结束复原；不跨 `invoke` / `stream` 泄漏。
- **低层入口**（`run_super_step` / `run_super_steps` / `_stream_tick` 直接调用）**不绑定**
  context ⇒ `get_context()` 为 `None` ⇒ 节点入参保持精确 `dict`。

---

## 4. 节点入参视图

### 4.1 标准节点入参

| 条件 | 节点收到的对象 | `type(...) is dict` | `isinstance(..., dict)` | `.context` |
|---|---|---|---|---|
| `context is None` | `read_channels(...)` 的普通 `dict` | **真** | 真 | 无（`getattr` ⇒ `None`） |
| `context is not None` | `_ContextState(dict)` | 假 | **真** | 本次 context（同一对象） |

**`_ContextState` 契约**：

| 项 | 契约 |
|---|---|
| 基类 | `dict` |
| 构造 | `_ContextState(mapping, context)`；内容 == `mapping`（键集 / 顺序 / 值不变） |
| `.context` | **只读** property；返回绑定时的 context 对象（`is` 同一对象） |
| `"context"` 键 | **MUST NOT** 出现（context 不是状态 key） |
| `.get(key, default)` | 与普通 `dict` 完全一致（C4） |
| `dict(view)` | 与绑定前的稀疏 `dict` 逐字相等 |
| 不可变承诺 | 不做防御性拷贝；view 是可变的（与普通 dict 一致）；`.context` 只读 |
| 其它属性 | 按普通对象规则；未知属性 ⇒ `AttributeError` |

### 4.2 `Send.arg`（fan-out）

| 条件 | 节点收到的对象 | `.context` |
|---|---|---|
| `context is None` | `Send.arg` 原样 | 不注入 |
| `context is not None` 且 `Send.arg` 是 `dict` | `_ContextState(Send.arg, context)` | 本次 context |
| `context is not None` 且 `Send.arg` 非 `dict` | `Send.arg` 原样 | **不注入**（v1 边界） |

> **边界理由**：`Send.arg` 是任意对象（C18）；只有 `dict` 能安全附加属性；
> 包装所有对象会改变用户对象类型 / 身份。

### 4.3 路由视图

| 项 | 契约 |
|---|---|
| 路由 fresh 状态视图 | 普通 `dict`；**不含** `context` 键；**无** `.context` 属性 |
| 路由第二参 `config` | 用户交给 `invoke` / `stream` 的**原始** config；可以是 `RunConfig(context=...)` / mapping / `None` |
| 路由读 context | 只能从第二参 `config` 读（若用户传入 `RunConfig`）；**MUST NOT** 从 fresh 视图读 |
| 路由目标 | 仍按内部节点名解析；alias 已移除 |

---

## 5. `context` 的状态隔离不变量

| 不变量 | 断言面 |
|---|---|
| `context` **不是**状态 key | `type(node_input) is dict` 时 `"context" not in state`；`_ContextState` 时 `"context" not in view` |
| `context` **不进** schema 通道表 | `GraphSpec.channels` / `SchedulerState.channels` 无 context |
| `context` **不参与**归约 | 节点返回值 / `node_writes` 无 context 写入 |
| `context` **不进** `invoke()` 终态 | 返回 dict 键集 == schema 键集 |
| `context` **不进** `values` 载荷 | 每条 `values` payload 键集 == schema 键集（+ 中断键） |
| `context` **不进** checkpoint | 本 feature 不读写快照；B14F1 另行处理 |
| `context` **不进** `configurable` | `RunConfig.configurable` 保持独立；不读取 `configurable["context"]` |
| `thread_id` / `metadata` / `tags` **不注入** | 节点 view / context view 不含这些 key（除非用户 context 自带） |

---

## 6. alias 移除（C25 正式作废）

### 6.1 `add_node` 签名

**之前（历史）**：

```text
add_node(node, action=None, *, alias=None, defer=False,
         metadata=None, destinations=None) -> Self
```

**本 feature 之后**：

```text
add_node(node, action=None, *, defer=False,
         metadata=None, destinations=None) -> Self
```

- `alias` **不存在**；传 `alias=` ⇒ 内置 `TypeError`（消息点名 `alias`）。
- 单 callable 形态 `add_node(fn)`、`defer`、`metadata`、`destinations` 行为不变。
- 失败 MUST NOT 修改构建器状态。

### 6.2 `_NodeRecord` / `_BuilderSpec`

| 实体 | 之前 | 之后 |
|---|---|---|
| `_NodeRecord` | `name, action, alias, defer, metadata, destinations` | `name, action, defer, metadata, destinations` |
| `_BuilderSpec.node_records` | `dict[str, _NodeRecord]`（含 alias） | `dict[str, _NodeRecord]`（无 alias） |
| `_BuilderSpec.nodes` / `edges` / `conditional_edges` | 不含 alias | 不变 |

### 6.3 不受影响的面

| 面 | 结论 |
|---|---|
| `PregelTask.name` | 仍 = 内部节点名（alias 移除后无替代） |
| `stream_mode="updates"` 载荷键 | 仍 = 内部节点名 |
| `get_graph()` 的节点 `id` / `name` | 仍 = 内部节点名；`name == id`（B22F1 现有断言不变） |
| `draw_mermaid()` 标签 | 仍 = 内部节点名 |
| `path_map` 查表 | 仍 = 内部节点名 |
| `Command.goto` / `Send.node` | 仍 = 内部节点名 |
| `Node.name`（图展示名） | **不是** C25 别名；保持现状（缺省归一为 `id`） |

### 6.4 C25 历史处理

| 文件 / 面 | 处理 |
|---|---|
| Q8 §3.4 · 宪法原则 VII · 立项书 §5.2 / §5.3 / §9.2 · 宪法 changelog | C25 文字**保留为历史墓碑**；active 清单改为 **C1–C24 + C26–C27**；C25 编号**不复用**；C26/C27 不重编号；宪法 **1.16.0** + changelog；未来 alias 使用新编号（如 C28） |
| B6F1 / B2F2 / B22F1 / B7F2 / B8F2 | 按 T-3…T-7 移除代码 / 签名 / 兼容矩阵 / 交接注记 |
| `harness/features/B8F3_...md` | **不改写**（历史提示词）；本 spec 的范围变更为权威 |

---

## 7. 验证矩阵（FR / SC 落点）

| FR / SC | 验证面 |
|---|---|
| FR-001 / SC-002 | `RunConfig` 九字段；四核心字段可读；`tags` 为 `tuple` |
| FR-002 / SC-001 | `context` 只从 `RunConfig.context` / mapping 读取；无 `context=` 关键字 |
| FR-003 / SC-001 | 状态 / `values` / `invoke` 终态 / checkpoint 无 context |
| FR-004 / SC-001 | 节点 `getattr(state, "context", None)` == context |
| FR-005 / SC-006 | `context is None` ⇒ `type(state) is dict`；非 None ⇒ `_ContextState` |
| FR-006 / SC-005 | 路由 fresh 视图无 context；第二参 config 可携带 |
| FR-007 / SC-003 | `configurable` 独立；无注入 `configurable` key |
| FR-008 | invoke / stream 同一解析；不跨运行泄漏 |
| FR-009 | 无 `context_schema`；无 checkpoint 持久化 |
| FR-010 | 私有 contextvar；无公开签名改动；`runtime.__all__` 23 |
| FR-011…FR-016 / SC-004 | alias 移除 / `TypeError` / 无 alias 字段 / 无别名映射 |
| FR-017 / SC-008 | 零依赖 / 零环境变量 / 零出站 |
| FR-018 | L3 只依赖 L1 / L2；零新增公开 L2 |
| FR-019 / SC-006 | C4 / C6 / C8 / C11 不破坏 |
| FR-020 / SC-009 / SC-010 | C21 软断言升级；C25 用例移除；demo / README 同步 |
| FR-021 | mapping / `None` 解析；原异常直达 |
| FR-022 / SC-012 | T-2…T-7 契约修订落地；C25 正式作废（编号不复用） |
| SC-007 | D-137…D-144 |
| SC-011 | 人工验证记录 + 追认 |
