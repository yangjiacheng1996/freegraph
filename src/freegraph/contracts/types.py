# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""freegraph 契约层的**四个核心类型**。

本模块定义后续全部 Phase 都会引用的类型地基：

* :data:`StateDict` —— 状态字典（类型别名，与 ``dict[str, Any]`` 完全等价）；
* :class:`Command` —— 命令原语（跳转 / 写入 / 恢复三个语义位）；
* :class:`StateSnapshot` —— 状态快照（某一时刻的完整定格）；
* :class:`RunConfig` —— 运行配置（单次运行的配置载体）。

本模块**零** freegraph 内部 import、**零**第三方 import（仅标准库），
因此可被外部项目单独消费（如 freechain 只取契约而不拖进运行时）。
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields
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
    ============== ==================================== ==========

    **填写规则（冻结）**：三个语义位**至少填一个**——
    三者全为 ``None``（未提供）时构造即抛 :class:`FreegraphError`；
    三者**可任意组合**（「跳转 + 写入」「恢复 + 跳转」均合法），互不排斥。
    某位**显式给了但内容为空**（``update={}`` / ``goto=()``）亦合法，
    语义为「该位不产生动作」——与「未提供」（``None``）**严格区分**。

    **浅不可变**：对象本身不可改（``frozen=True``），但 ``update`` 装的是 dict、
    ``goto`` 装列表时**其内容仍可变**。

    **``goto`` 不归一化**：传元组存元组、传列表存列表（与冻结注解逐字一致）。

    .. note::
       运行时（F9P1）解释 ``goto`` 时 MUST 先判 ``isinstance(x, str)`` ——
       ``str`` 本身也是 ``Sequence[str]``，顺序判断会把它拆成字符序列。
    """

    goto: str | Sequence[str] | None = None
    update: StateDict | None = None
    resume: Any | None = None

    PARENT: ClassVar[Literal["__parent__"]] = "__parent__"
    """「跳向最近的父图」的字符串哨兵值。

    类属性（``ClassVar``）而**非**实例字段——dataclass 不会把它当字段，
    ``slots=True`` 也不会为它留槽位。节点名 ``__parent__`` 视为**保留名**
    （校验归 F7P2 / F9P1）。
    """

    def __post_init__(self) -> None:
        """构造期 fail fast：三个语义位全空即抛 ``FreegraphError``。

        这是契约层**仅有的两条构造期校验**之一（另一条是
        ``RunConfig.from_dict`` 的未知键判定）；其余一律只做类型注解、
        不校验值。
        """
        if self.goto is None and self.update is None and self.resume is None:
            raise FreegraphError(
                "Command requires at least one of 'goto', 'update' or 'resume' "
                "to be provided."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class RunConfig:
    """**运行配置** —— 单次运行的配置载体。

    ============== ============================ ==========
    字段            类型                          缺省
    ============== ============================ ==========
    ``thread_id``  ``str | None``                ``None``
    ``context``    ``Any``                       ``None``
    ``metadata``   ``Mapping[str, Any]``         空映射
    ``tags``       ``Sequence[str]``             空序列
    ============== ============================ ==========

    四字段**全部可选**，构造无前置条件。``thread_id`` 是**会话**标识
    （用户可指定）；``context`` 是**运行时上下文的独立通道**（C21），
    **不**塞进 ``configurable``；``metadata`` 与 ``tags`` 只作附加信息、
    **不参与标识**。

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

    def __post_init__(self) -> None:
        """构造期把 ``metadata`` / ``tags`` 拷为自身持有的新容器。

        ``frozen=True`` 下普通赋值会抛 ``FrozenInstanceError``，
        故 MUST 用 ``object.__setattr__``。拷贝为**浅拷贝**。

        本方法**不校验值**——``thread_id`` 的实际类型、``tags`` 的元素类型等
        均不在构造期校验（只做类型注解）。
        """
        object.__setattr__(self, "metadata", dict(self.metadata))
        object.__setattr__(self, "tags", tuple(self.tags))

    @classmethod
    def from_dict(
        cls,
        d: Mapping[str, Any],
        *,
        ignore_unknown: bool = False,
    ) -> "RunConfig":
        """从**裸 dict** 构造运行配置。

        智能体上下文本就是 JSON，用户手上天然是裸 dict——有了这条路，
        运行入口将来（归 F7P3）就能容忍裸 dict 传入，调用方不必逐字段搬运。

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

    ================= ============================ ====================
    字段               类型                          语义
    ================= ============================ ====================
    ``values``        ``StateDict``                 该时刻的完整状态（稀疏映射）
    ``next``          ``tuple[str, ...]``           本步之后要执行的节点名
    ``config``        ``RunConfig``                 取回该快照所用的运行配置
    ``metadata``      ``Mapping[str, Any]``         附加信息（可为空映射）
    ``created_at``    ``str``                       创建时刻（UTC ISO-8601）
    ``tasks``         ``tuple[Any, ...]``           本步任务列表
    ``interrupts``    ``tuple[Any, ...]``           本步发生的中断
    ================= ============================ ====================

    七字段**全部必填**（无缺省值）——不存在「字段缺失的快照」。
    ``next`` 的**空元组** = 无后续节点。``created_at`` **必填**，
    且 MUST 一律为 **UTC 的 ISO-8601 字符串**（各持久化后端不得各写各的，
    否则时间线排序与对比出错）；其**格式由生产者保证**，契约层构造期不校验。

    **浅不可变**：对象本身不可改（``frozen=True``），但 ``values`` /
    ``metadata`` 装的是可变容器，其内容仍可变。

    **容器防御性拷贝**：构造时**只拷** ``metadata``（快照**没有** ``tags`` 字段）
    ——``dict(...)``，**浅拷贝**。
    """

    values: StateDict
    next: tuple[str, ...]
    config: RunConfig
    metadata: Mapping[str, Any]
    created_at: str
    tasks: tuple[Any, ...]
    interrupts: tuple[Any, ...]

    def __post_init__(self) -> None:
        """构造期**只拷** ``metadata``（``dict(...)``，浅拷贝）。

        ``frozen=True`` 下普通赋值会抛 ``FrozenInstanceError``，
        故 MUST 用 ``object.__setattr__``。

        本方法**不校验值**——``created_at`` 的格式不符**不抛错**
        （格式合规是生产者、即各持久化后端的责任）。
        """
        object.__setattr__(self, "metadata", dict(self.metadata))
