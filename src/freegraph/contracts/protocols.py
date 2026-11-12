# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""契约层的**五个协议**——可插拔能力的类型契约面。

本模块定义 5 个协议：

* :class:`NodeFunc` —— 节点函数协议；
* :class:`Checkpointer` —— 检查点协议（6 方法）；
* :class:`TraceSink` —— 可观测接收端协议（3 方法）；
* :class:`Store` —— 长期存储协议（6 方法）；
* :class:`CompiledGraph` —— 编译产物能力面（6 方法）。

**纯抽象、无默认实现、无继承链**——协议不提供任何方法体（方法体只有 ``...``），
也不提供基类可供继承；扩展靠组合或结构化子类型判定（架构纪律 PD-1）。

> **为何 MUST 纯抽象**：默认实现会让「只声明部分方法」的假实现**静默通过**
> 结构化子类型判定，把「缺实现」这一真实缺陷掩盖到运行时（FR-007 / 门禁 G10）。

本模块**零** freegraph 内部 import、**零**第三方 import（仅标准库）。
"""

from collections.abc import Iterator, Sequence
from typing import Any, Protocol, runtime_checkable

from .graph import Graph
from .trace import Span
from .types import Command, RunConfig, StateDict, StateSnapshot

__all__ = [
    "NodeFunc",
    "Checkpointer",
    "TraceSink",
    "Store",
    "CompiledGraph",
]


@runtime_checkable
class NodeFunc(Protocol):
    """**节点函数协议** —— 图的每个节点由一个满足本协议的可调用对象实现。

    ============== ============================================ ==========
    成员           签名                                          语义
    ============== ============================================ ==========
    ``__call__``   ``(state: StateDict) -> StateDict | Command | list[Command | StateDict] | None`` 节点函数
    ============== ============================================ ==========

    **入参**：**稀疏**状态字典（只含「当前有值」的 key）。

    **返回**：**部分状态字典**（待归约的新状态）/ **命令原语**
    （跳转 / 写入 / 恢复）/ **命令列表**（多条命令按**列表顺序**依次生效）/
    **空值**（不写状态）。

    .. note::
       **「命令列表」形态**（``list[Command | StateDict]``）由 **B9F1** 增补
       （**2026-11-11 · 发起者特批 · 破本协议的 L1 冻结面**）—— 上游 LangGraph 的
       ``ToolNode`` **自身即返回该形态**（多个工具各返回一个 ``Command`` ⇒ 汇总成列表返回），
       故本协议 MUST 与运行时**一致**（否则「用 ``NodeFunc`` 标注的节点」在**类型层**
       无法表达列表返回）。
       ``StateDict`` 即 ``dict[str, Any]`` ⇒ 与 B9F1 的 ``list[Command | dict]`` **逐字等价**。

    .. note::
       ``isinstance(f, NodeFunc)`` 对**任意可调用对象**恒为真（因其自带
       ``__call__``）——该判定的价值是「不是可调用对象时判失败」，**不是**
       「是不是合法节点函数」。「合法节点函数」由**静态类型检查**判定。

    **对应契约**：C5（节点函数签名）/ C6（返回值合并——逐 key 归约语义归
    B4F1 / B5F1，本协议只冻结返回形态）。
    """

    def __call__(
        self, state: StateDict
    ) -> StateDict | Command | list[Command | StateDict] | None: ...


@runtime_checkable
class Checkpointer(Protocol):
    """**检查点协议** —— 持久化后端的**最小能力面**。

    ================ ==================================== ==============================
    成员             签名                                 语义
    ================ ==================================== ==============================
    ``get_tuple``    ``(config: RunConfig) -> Any``        取回**最新**快照
    ``list``         ``(config: RunConfig, ...) -> Any``   列举**历史**快照
    ``put``          ``(config: RunConfig, ...) -> Any``   写入一个**快照**
    ``put_writes``   ``(config: RunConfig, ...) -> Any``   写入**待写入数据**
    ``delete_thread`` ``(thread_id: str) -> Any``           删除某**会话**的全部数据
    ``delete_for_runs`` ``(run_ids: Sequence[str]) -> Any`` 删除若干**运行**的数据
    ``copy_thread``  ``(source_thread_id: str, target_thread_id: str) -> Any`` 复制一个**会话**的数据
    ``get_next_version`` ``(...) -> Any``                  生成**下一个版本号**
    ================ ==================================== ==============================

    ⚠️ **2026-11-12 上游对齐 P3**（**上游同款** · 上游 ``langgraph/checkpoint/base/__init__.py``）：
    新增 ``delete_for_runs``（`:331`）与 ``copy_thread``（`:350`）—— 这两个在**上游是
    **必须实现**的**（无默认实现）⇒ **上游形状的 saver 若缺它们就**结构化**不满足本协议**
    ⇒ 补上后 **上游的 ``BaseCheckpointSaver`` 子类可直接满足本协议** ⇒ **兼容性闭环**。
    ⚠️ **不补**上游的**异步变体**（``aget`` / ``aput`` / …）—— freegraph v1 **无 async**
    （spec FR-008）⇒ 契约层 MUST NOT 声明 async 成员。

    **返回结构与载荷形状挂起 B14F1**——签名中的 ``Any`` **不是**「随便什么」，
    而是「返回结构与载荷形状尚未冻结」的显式标记；收紧属**契约修订**流程
    （宪法 §Governance），不是就地改型。

    **已冻结的三条最小约束**：

    ① 方法集合**恰为**上述**八个**（不多不少 · **2026-11-12 上游对齐 P3** 由六个增为八个）；
    ② 读写面 MUST 能承载**检查点标识**（C23 要求 span 必带它）；
    ③ 载荷 MUST 为**纯数据**（可 JSON 序列化）。

    **对应契约**：C19。
    """

    def get_tuple(self, config: RunConfig) -> Any: ...

    def list(self, config: RunConfig, *args: Any, **kwargs: Any) -> Any: ...

    def put(self, config: RunConfig, *args: Any, **kwargs: Any) -> Any: ...

    def put_writes(self, config: RunConfig, *args: Any, **kwargs: Any) -> Any: ...

    def delete_thread(self, thread_id: str) -> Any: ...

    def delete_for_runs(self, run_ids: Sequence[str]) -> Any: ...

    def copy_thread(self, source_thread_id: str, target_thread_id: str) -> Any: ...

    def get_next_version(self, *args: Any, **kwargs: Any) -> Any: ...


@runtime_checkable
class TraceSink(Protocol):
    """**可观测接收端协议** —— 上层把自己的接收端注入进来的最小能力面。

    ================== ==================== ==================================
    成员                签名                   语义
    ================== ==================== ==================================
    ``on_span_start``  ``(span: Span) -> None``  一个 span **开始**
    ``on_span_end``    ``(span: Span) -> None``  一个 span **结束**
    ``current_span``   ``() -> Span | None``     **当前** span
    ================== ==================== ==================================

    **回调载荷语义**（D-07 · Q9）：

    * 开始回调收到的是「``end_time`` **为空**」的实例；
    * 结束回调收到的是**同 ``id``、``end_time`` **已填**的新实例**；
    * 两次回调按 **``id`` 配对**；
    * **开始时收到的实例 MUST NOT 在事后被改写**（其 ``end_time`` 始终为空）。

    ``current_span()`` 在**无当前 span**时返回**空值**，**MUST NOT** 抛异常。

    **「不注入即零开销零外呼」**：本协议**不提供**任何默认实现——运行时若未
    注入 sink，**不得**创建「空接收端」对象（那是行为，属 B19F1）。

    **对应契约**：C23（可观测挂钩）/ C24（当前 span 上下文）。
    """

    def on_span_start(self, span: Span) -> None: ...

    def on_span_end(self, span: Span) -> None: ...

    def current_span(self) -> Span | None: ...


@runtime_checkable
class Store(Protocol):
    """**长期存储协议** —— 跨运行、跨会话的键值存储能力面。

    ==================== ================================ ==========================
    成员                 签名                              语义
    ==================== ================================ ==========================
    ``get``              ``(namespace, key) -> Any``        按 (命名空间, 键) 取一项
    ``search``           ``(namespace_prefix, ...) -> Any``  在命名空间前缀下检索
    ``put``              ``(namespace, key, value) -> Any``  写入一项
    ``delete``           ``(namespace, key) -> Any``        删除一项
    ``list_namespaces``  ``(*, prefix, ...) -> Any``        列出命名空间

    ⚠️ **2026-11-12 上游对齐 P3**（**上游同款** · 上游 ``langgraph/store/base/__init__.py``）：
    命名空间由 ``Any`` **收紧**为 ``tuple[str, ...]``（上游的 ``NamespacePath`` 是
    **层级元组** · 上游 `:311`）⇒ 上游形状的 store **直接满足**本协议。
    ⚠️ **不补**上游的**异步变体**（``abatch`` / ``aget`` / …）—— freegraph v1 **无 async**。
    ``batch``            ``(ops, ...) -> Any``              **批量**执行多个操作
    ==================== ================================ ==========================

    **寻址语义**：命名空间 = **层级路径**（多段组成），键 = **字符串**；
    取值 MUST 为**纯映射**（可 JSON 序列化）。

    **命名空间的**具体载体形态**（层级元组 / 点分字符串）与 ``batch`` 的
    **操作表示**挂起 v2——故 ``batch`` 的载荷类型以 ``Any`` 占位；
    ⚠️ **2026-11-12 上游对齐 P3**：``namespace`` / ``namespace_prefix`` / ``prefix``
    **已收紧**为 ``tuple[str, ...]``（上游同款 · 上游 ``store/base/__init__.py:311``）。

    .. note::
       ``namespace_prefix`` 与 ``prefix`` **是两个不同的参数名**，逐字镜像
       上游 LangGraph 1.2.11（``search`` 的是**位置参数**、``list_namespaces``
       的是**关键字参数**）——下游实现 MUST 照抄，**不得**为「一个概念一个名字」
       而统一（兼容锚点失效）。

    **v1 无实现**：本协议只定义类型；契约 C20 仍冻结，实现后补（v2）。

    **对应契约**：C20。
    """

    def get(self, namespace: tuple[str, ...], key: str) -> Any: ...

    def search(
        self, namespace_prefix: tuple[str, ...], *args: Any, **kwargs: Any
    ) -> Any: ...

    def put(self, namespace: tuple[str, ...], key: str, value: Any) -> Any: ...

    def delete(self, namespace: tuple[str, ...], key: str) -> Any: ...

    def list_namespaces(
        self, *, prefix: tuple[str, ...] | None = None, **kwargs: Any
    ) -> Any: ...

    def batch(self, ops: Any, *args: Any, **kwargs: Any) -> Any: ...


@runtime_checkable
class CompiledGraph(Protocol):
    """**编译产物协议** —— 图编译后可执行对象的**能力面**（6 方法）。

    =================== ================================================== ==========================
    成员                 签名                                                返回类别
    =================== ================================================== ==========================
    ``invoke``           ``(input, config=None) -> StateDict``                **完整状态字典**
    ``stream``           ``(input, config=None, *, stream_mode="values")``   **事件迭代器**
                         ``-> Iterator[dict[str, Any]]``
    ``get_graph``        ``(*, xray=False) -> Graph``                        **图结构**
    ``get_state``        ``(config) -> StateSnapshot | None``                **状态快照**
    ``get_state_history`` ``(config) -> Iterator[StateSnapshot]``            **状态快照迭代器**
    ``update_state``     ``(config, values, as_node=None) -> StateSnapshot`` **状态快照**
    =================== ================================================== ==========================

    **已冻结**：六个方法的**返回类别** + **参数名**（占位名，见下注）
    + ``get_state`` 的**空值语义**（**查不到返回空值**，MUST NOT 抛异常）。

    **``stream`` 的元素类型 = ``dict[str, Any]``**（**纯数据字典**，非 ``Any``）；
    ``stream_mode`` 的取值是**字符串**，**mode 枚举全集挂起 B8F2**。

    **``get_state`` 的空值语义**：查不到会话状态时返回**空值**，**MUST NOT**
    抛异常。

    **参数名的口径**：上表签名中的参数名（``input`` / ``config`` /
    ``stream_mode`` / ``xray`` / ``as_node``）**冻结为占位名**——协议签名不写死
    参数名即无法实现，静态类型检查（SC-004）与对外文档都需要确切签名。
    下游 feature 确需改名者 MUST 走**契约修订**流程，MUST NOT 就地改型。

    **挂起**：各方法的**行为细节与实现** —— ``invoke`` → B7F3、``stream`` →
    B8F2（mode 枚举）、状态查询 → B15F1、``update_state`` → B16F1。
    **子图实现属 v2**（C26）；v1 只保 ``get_graph(xray=)`` 的**签名兼容**。

    **对应契约**：C10（编译）/ C11（执行）/ C12（流式）/ C13（图结构导出）。
    """

    def invoke(
        self, input: StateDict, config: RunConfig | None = None
    ) -> StateDict: ...

    def stream(
        self,
        input: StateDict,
        config: RunConfig | None = None,
        *,
        stream_mode: str | Sequence[str] = "values",
    ) -> Iterator[dict[str, Any]]: ...

    def get_graph(self, *, xray: bool = False) -> Graph: ...

    def get_state(self, config: RunConfig) -> StateSnapshot | None: ...

    def get_state_history(self, config: RunConfig) -> Iterator[StateSnapshot]: ...

    def update_state(
        self, config: RunConfig, values: StateDict, as_node: str | None = None
    ) -> StateSnapshot: ...
