# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""freegraph 契约层的**四个核心类型**。

本模块定义后续全部 feature 都会引用的类型地基：

* :data:`StateDict` —— 状态字典（类型别名，与 ``dict[str, Any]`` 完全等价）；
* :class:`Command` —— 命令原语（跳转 / 写入 / 恢复三个语义位）；
* :class:`StateSnapshot` —— 状态快照（某一时刻的完整定格）；
* :class:`RunConfig` —— 运行配置（单次运行的配置载体）。

本模块**零** freegraph 内部 import、**零**第三方 import（仅标准库），
因此可被外部项目单独消费（如 freechain 只取契约而不拖进运行时）。
"""

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, fields
from typing import Any, ClassVar, Literal, TypeAlias

from .errors import FreegraphError

StateDict: TypeAlias = dict[str, Any]
"""**状态字典** —— 图状态的**稀疏**映射，只含「当前有值」的 key。

刻意做成**类型别名**而非新造类：节点函数注解 ``state: StateDict``
收到普通 dict 时类型检查必须通过（FR-002 / FR-014）。
**不支持**按 schema 参数化（``StateDict[MySchema]`` 是非法写法）——
需要具体字段补全的用户改用自己的 ``TypedDict`` 标注节点签名。
"""


@dataclass(frozen=True, slots=True, kw_only=True)
class Command:
    """**命令原语** —— 节点返回的命令，承载三个语义位。

    ============== ==================================== ==========
    字段            类型                                   缺省
    ============== ==================================== ==========
    ``goto``       ``str | Sequence[str] | None``          ``None``
    ``update``     ``StateDict | None``                    ``None``
    ``resume``     ``Any | None``                          ``None``
    ``graph``      ``str | None``                          ``None``
    ============== ==================================== ==========

    **填写规则（冻结 · 2026-11-12 上游对齐 P3 订正）**：各语义位**可任意组合**
    （「跳转 + 写入」「恢复 + 跳转」均合法），互不排斥；**MUST NOT** 再要求「至少填一个」
    —— 上游 ``Command`` **无任何构造期校验**（``langgraph/types.py:798-848``）⇒
    四位全为 ``None`` **合法**（= 什么都不做）。
    某位**显式给了但内容为空**（``update={}`` / ``goto=()``）亦合法，
    语义为「该位不产生动作」——与「未提供」（``None``）**严格区分**。

    **浅不可变**：对象本身不可改（``frozen=True``），但 ``update`` 装的是 dict、
    ``goto`` 装列表时**其内容仍可变**。

    **``goto`` 不归一化**：传元组存元组、传列表存列表（与冻结注解逐字一致）。

    .. note::
       运行时（B9F1）解释 ``goto`` 时 MUST 先判 ``isinstance(x, str)`` ——
       ``str`` 本身也是 ``Sequence[str]``，顺序判断会把它拆成字符序列。
    """

    goto: str | Sequence[str] | None = None
    #: ⚠️ **2026-11-12 上游对齐 P3**：``update`` 放宽为 ``Any | None``（**上游同款** ·
    #: 上游 ``langgraph/types.py:822``）⇒ 运行期**接受**的形态随之放宽为
    #: **dict** · **list/tuple of 2-tuples**（上游 ``types.py:836-840``）· 其余形态
    #: **仍显式失败**（**比上游更严** · 上游把它们塞进 ``__root__`` 通道 ⇒ 静默丢弃）。
    update: Any | None = None
    resume: Any | None = None
    #: ``graph`` —— 目标图（上游同款 · ``langgraph/types.py:821``）⇒
    #: ``graph=Command.PARENT`` 表示「跳向最近的父图」（上游的跨层传播写法）。
    #: ⚠️ freegraph v1 **无子图** ⇒ 该槽位的**运行期语义**归 **B10F1**（**不越界**）。
    graph: str | None = None

    PARENT: ClassVar[Literal["__parent__"]] = "__parent__"
    """「跳向最近的父图」的字符串哨兵值。

    类属性（``ClassVar``）而**非**实例字段——dataclass 不会把它当字段，
    ``slots=True`` 也不会为它留槽位。节点名 ``__parent__`` 视为**保留名**
    （校验归 B7F2 / B9F1）。
    """

    # ⚠️ **2026-11-12 上游对齐 P3**：**无构造期校验**（上游 ``Command`` 同款 ·
    # ``langgraph/types.py:798-848`` 只有 ``__repr__`` 与 ``_update_as_tuples``）⇒
    # 原「三个语义位全空即抛 ``FreegraphError``」的校验**已删除**（原为裁定 21 的产物）。

    def __repr__(self) -> str:
        """**上游同款**（``langgraph/types.py:826-831``）—— 跳过**假值**字段。

        ⚠️ **2026-11-12 上游对齐 P3**：原先用 dataclass 的默认 ``repr``
        （会把 ``None`` 字段全列出来）⇒ 与上游**不同款** ⇒ 改为上游口径。
        """
        contents = ", ".join(
            f"{key}={value!r}" for key, value in asdict(self).items() if value
        )
        return f"Command({contents})"


@dataclass(frozen=True, slots=True, kw_only=True)
class Interrupt:
    """**中断信息** —— 一次中断的载荷（**上游同款** · 2026-11-12 上游对齐 P3）。

    ============== ============ ====================================
    字段            类型          语义
    ============== ============ ====================================
    ``value``      ``Any``       中断时携带的值（用户给的内容）
    ``id``         ``str``       中断的标识（可用于**直接恢复**这一次中断）
    ============== ============ ====================================

    ⚠️ **契约 C17**：中断结果的元素 MUST 带 ``.value`` 与 ``.id`` ⇒ 本类就是该结构的
    **载体**（此前 freegraph 的中断载荷是裸 ``Any`` ⇒ 无处安放 ``.id``）。

    ⚠️ **``id`` 的自动生成不在本类**（上游按 checkpoint 的**命名空间**派生 · 上游
    ``langgraph/types.py:599-614``）⇒ freegraph 的命名空间概念归 **B10F1**
    （``interrupt()`` 的实现）⇒ 本类**只**承载已给定的 ``id``。
    """

    value: Any = None
    id: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class PregelTask:
    """**一个任务的定格** —— 某一时刻某个任务的记录（**上游同款** · 2026-11-12 上游对齐 P3）。

    ==================== ================================== ==============
    字段                  类型                                缺省
    ==================== ================================== ==============
    ``id``               ``str``                             —（必填）
    ``name``             ``str``                             —（必填）
    ``path``             ``tuple[str | int | tuple, ...]``   空元组
    ``error``            ``Exception | None``                ``None``
    ``interrupts``       ``tuple[Interrupt, ...]``           空元组
    ``state``            ``RunConfig | StateSnapshot | None`` ``None``
    ``result``           ``Any | None``                      ``None``
    ==================== ================================== ==============

    ⚠️ **上游同款**（``langgraph/types.py:637-646`` 的 ``PregelTask`` NamedTuple）⇒
    字段名与语义**逐字对齐** ⇒ 下游 langchain 可直接消费。
    """

    id: str
    name: str
    path: tuple[str | int | tuple, ...] = ()
    error: Exception | None = None
    interrupts: tuple[Interrupt, ...] = ()
    state: "RunConfig | StateSnapshot | None" = None
    result: Any | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class RunConfig:
    """**运行配置** —— 单次运行的配置载体。

    ==================== ============================ ==========
    字段                 类型                          缺省
    ==================== ============================ ==========
    ``thread_id``       ``str | None``                ``None``
    ``context``         ``Any``                       ``None``
    ``metadata``        ``Mapping[str, Any]``         空映射
    ``tags``            ``Sequence[str]``             空序列
    ``configurable``    ``Mapping[str, Any]``         空映射
    ``max_concurrency`` ``int | None``                ``None``
    ``recursion_limit`` ``int | None``                ``None``
    ``run_name``        ``str | None``                ``None``
    ``run_id``          ``str | None``                ``None``
    ==================== ============================ ==========

    九字段**全部可选**，构造无前置条件。``thread_id`` 是**会话**标识
    （用户可指定）；``context`` 是**运行时上下文的独立通道**（C21），
    **不**塞进 ``configurable``；``metadata`` 与 ``tags`` 只作附加信息、
    **不参与标识**。

    ⚠️ **2026-11-12 上游对齐 P3**：新增 ``configurable`` / ``max_concurrency`` /
    ``recursion_limit`` / ``run_name`` / ``run_id`` 五个键（**上游同款** · 上游
    ``langchain_core/runnables/config.py:98,103,109,115,124``）⇒ **下游 langchain 传的
    ``RunnableConfig`` 可**原样**落进本类型 ⇒ 兼容性闭环。
    ⚠️ 上游把 ``thread_id`` 放在 ``configurable`` **子字典**里（``langgraph/_internal/_constants.py:52``）⇒
    freegraph 保留**顶层** ``thread_id``（B1F1 的冻结面）**并**接受 ``configurable["thread_id"]``
    ⇒ 两种写法都work ⇒ 见 :meth:`resolved_thread_id`。

    **浅不可变**：对象本身不可改（``frozen=True``），但 ``metadata`` 装的是 dict，
    其内容仍可变。

    .. warning::
       **本类不可哈希** —— ``hash()`` 抛 ``TypeError``（因 ``metadata`` 装的是 dict）。
       不可变记录通常按值比较而非按哈希存入集合。

    **容器防御性拷贝**：构造时把 ``metadata`` / ``tags`` 拷为自身持有的新容器
    （``dict(...)`` / ``tuple(...)``），**浅拷贝**——嵌套容器仍与调用方共享同一对象。
    """

    thread_id: str | None = None
    context: Any = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    tags: Sequence[str] = field(default_factory=tuple)
    configurable: Mapping[str, Any] = field(default_factory=dict)
    max_concurrency: int | None = None
    recursion_limit: int | None = None
    run_name: str | None = None
    run_id: str | None = None

    def __post_init__(self) -> None:
        """构造期把 ``metadata`` / ``tags`` 拷为自身持有的新容器。

        ``frozen=True`` 下普通赋值会抛 ``FrozenInstanceError``，
        故 MUST 用 ``object.__setattr__``。拷贝为**浅拷贝**。

        本方法**不校验值**——``thread_id`` 的实际类型、``tags`` 的元素类型等
        均不在构造期校验（只做类型注解）。
        """
        object.__setattr__(self, "metadata", dict(self.metadata))
        object.__setattr__(self, "tags", tuple(self.tags))
        object.__setattr__(self, "configurable", dict(self.configurable))

    def resolved_thread_id(self) -> str | None:
        """返回**生效的**会话标识（**上游同款** · 2026-11-12 上游对齐 P3）。

        ⚠️ 上游把 ``thread_id`` 放在 ``configurable`` **子字典**里
        （``langgraph/_internal/_constants.py:52``）⇒ freegraph 两种写法都接受：
        ``configurable["thread_id"]`` **优先**于**顶层** ``thread_id``
        ⇒ 下游 langchain 原样传的 ``RunnableConfig`` 无需改写。
        """
        nested = self.configurable.get("thread_id")
        if isinstance(nested, str):
            return nested
        return self.thread_id

    @classmethod
    def from_dict(
        cls,
        d: Mapping[str, Any],
        *,
        ignore_unknown: bool = False,
    ) -> "RunConfig":
        """从**裸 dict** 构造运行配置。

        智能体上下文本就是 JSON，用户手上天然是裸 dict——有了这条路，
        运行入口将来（归 B7F3）就能容忍裸 dict 传入，调用方不必逐字段搬运。

        * **默认严格**：``d`` 中出现四字段之外的键时抛 :class:`FreegraphError`，
          消息**点名该键**——当场暴露 ``threadId`` 这类拼写错误，
          而不是静默吞掉（那会表现为「会话没记住」，极难查的 bug）。
        * **``ignore_unknown=True``** 走宽松：忽略未知键，正常构造。

        未知键的比对以 ``dataclasses.fields(cls)`` 为准——**不得**硬编码一份
        字段名清单（那会与 dataclass 脱节、迟早漂移）。
        """
        known = {f.name for f in fields(cls)}
        unknown = [key for key in d if key not in known]
        if unknown and not ignore_unknown:
            listed = ", ".join(repr(key) for key in unknown)
            raise FreegraphError(
                f"Unknown key(s) for RunConfig: {listed}. "
                f"Valid keys are: {', '.join(sorted(known))}. "
                "Pass ignore_unknown=True to ignore unknown keys."
            )
        return cls(**{key: value for key, value in d.items() if key in known})


@dataclass(frozen=True, slots=True, kw_only=True)
class StateSnapshot:
    """**状态快照** —— 某一时刻的完整定格。

    ==================== ============================ ====================
    字段                  类型                          语义
    ==================== ============================ ====================
    ``values``           ``StateDict``                 该时刻的完整状态（稀疏映射）
    ``next``             ``tuple[str, ...]``           本步之后要执行的节点名
    ``config``           ``RunConfig``                 取回该快照所用的运行配置
    ``metadata``         ``Mapping[str, Any] | None``  附加信息（**可为 None**）
    ``created_at``       ``str | None``                创建时刻（UTC ISO-8601 · **可为 None**）
    ``parent_config``    ``RunConfig | None``          取**父快照**所用的配置（**可为 None**）
    ``tasks``            ``tuple[PregelTask, ...]``    本步任务列表
    ``interrupts``       ``tuple[Interrupt, ...]``     本步发生的中断
    ==================== ============================ ====================

    八字段**全部必填**（无缺省值）——不存在「字段缺失的快照」。
    ``next`` 的**空元组** = 无后续节点。``created_at`` 与 ``metadata`` 的**类型可空**
    （**上游同款** · 上游 ``langgraph/types.py:692,694``）⇒ 契约层**不**强制它们非空。
    ⚠️ **2026-11-12 上游对齐 P3**：新增 ``parent_config``（上游 ``types.py:696``）·
    ``created_at`` / ``metadata`` 放宽为**可空**（上游 ``types.py:692,694``）·
    ``tasks`` / ``interrupts`` 的元素类型**收紧**为 ``PregelTask`` / ``Interrupt``
    （上游 ``types.py:698,700``）⇒ 字段集合与上游**逐字同构**。

    **浅不可变**：对象本身不可改（``frozen=True``），但 ``values`` /
    ``metadata`` 装的是可变容器，其内容仍可变。

    **容器防御性拷贝**：构造时**只拷** ``metadata``（快照**没有** ``tags`` 字段）
    ——``dict(...)``，**浅拷贝**。
    """

    values: StateDict
    next: tuple[str, ...]
    config: RunConfig
    metadata: Mapping[str, Any] | None
    created_at: str | None
    parent_config: RunConfig | None
    tasks: tuple[PregelTask, ...]
    interrupts: tuple[Interrupt, ...]

    def __post_init__(self) -> None:
        """构造期**只拷** ``metadata``（``dict(...)``，浅拷贝；**可为 None** ⇒ 不拷）。

        ``frozen=True`` 下普通赋值会抛 ``FrozenInstanceError``，
        故 MUST 用 ``object.__setattr__``。

        本方法**不校验值**——``created_at`` 的格式不符**不抛错**
        （格式合规是生产者、即各持久化后端的责任）。
        """
        if self.metadata is not None:
            object.__setattr__(self, "metadata", dict(self.metadata))
