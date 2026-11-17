# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L2 执行内核层 · **条件边路由求值** —— 属 **B8F1**（私有模块）。

本模块承载**条件边**（``add_conditional_edges``）的运行期语义：

* :func:`evaluate_routes` —— 求值某个源节点名下的**全部**条件边 ⇒
  ``(动态边目标序列, fan-out 任务序列)``；
* :func:`call_route_function` —— 路由函数的**调用形态**（单参 / 双参）
  ⇒ **照抄上游** ``RunnableCallable`` 的判别规则；
* :func:`resolve_route_result` —— 路由返回值的**目标解析**
  （``path_map`` 双形态 · 序列 · ``END`` · ``Send``）；
* :func:`validate_conditional_payload` —— **V-27**（条件边载荷的**五键**形态
  · **构造期**校验）。

**契约权威**：
``specs/b8f1-conditional-edges-fresh-read/contracts/conditional-edge-contract.md``
（``<!-- authority: yes -->``）⇒ 本模块 MUST NOT 另立一套口径。

**上游对齐**（``langgraph 1.2.11`` · 原则 XI「上游优先」）：

* 调用形态 ⇒ ``langgraph/_internal/_runnable.py:341-365``（``RunnableCallable``
  的判别循环 · 按**参数名** ``config`` + ``VALID_KINDS`` + 注解**匹配集**）；
* 目标解析 ⇒ ``langgraph/graph/_branch.py:199-211``（查表 ⇒ ``None`` / ``START``
  校验 ⇒ ``Send`` 不查表）；
* ``END`` 的**过滤** ⇒ ``langgraph/graph/state.py:1592``（``p != END`` · 对
  **标量与序列同款** · 作用在**解析后**的目的地上）。

**依赖纪律**：只依赖**标准库**与 L1 的 ``freegraph.contracts`` ⇒ 零第三方依赖
⇒ MUST NOT import ``langchain*`` / ``langgraph*`` / ``langsmith``。
**本模块私有** ⇒ 不进 ``freegraph.runtime.__all__``（门禁 **G7 / G15 / G19**
恒绿）⇒ ⇒ **零新增公开 API**。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Container, Hashable, Mapping, Sequence
from typing import Any, Optional

from freegraph.contracts.types import RunConfig, Send

from ._fanout import make_fanout
from .channel import Channel
from .read import local_read

__all__: list[str] = []

#: 入口哨兵（门面 ``START`` 的值）—— **不是**合法目标（契约 §4.1）。
_START_MARKER = "__start__"

#: 终止标记（门面 ``END`` 的值）—— 逐字等于 ``src/freegraph/graph.py:45``。
_END_MARKER = "__end__"

#: 条件边载荷的**五键**（顺序固定 · L3 的 ``_conditional_mapping()`` 产出）。
CONDITIONAL_PAYLOAD_KEYS: tuple[str, ...] = (
    "branch",
    "path",
    "path_map",
    "targets",
    "route_channels",
)

#: ``config`` 参数的**注解匹配集**（**照抄上游** ``KWARGS_CONFIG_KEYS`` 的
#: ``"config"`` 项 · **同形** · 仅**载体类型**不同 ⇒ 偏离登记 **X-5**）。
#:
#: * 上游 = ``(RunnableConfig, "RunnableConfig", Optional[RunnableConfig],
#:   "Optional[RunnableConfig]", inspect.Parameter.empty)``（精确 **5** 元组
#:   · ``langgraph/_internal/_runnable.py:170-176``）；
#: * freegraph = 同形 **9** 元组（每种载体类型**两个字面量** · 类对象 + 字符串
#:   + ``Optional`` + ``PEP-604`` 等价形式 · 无注解）；
#: * ⚠️ **字符串槽只含**每种载体类型**两个字面量** ⇒ ``"RunConfig | None"``
#:   这样的**字符串**不被接受（上游同款 · 实测 **P-A17**）；
#: * ⚠️ **PEP-604 的类对象形式**（``RunConfig | None``）**被接受** ⇒ 因为
#:   ``RunConfig | None == Optional[RunConfig]``（**逐字相等** ⇒ 落在同一项）。
_CONFIG_ANNOTATIONS: tuple[Any, ...] = (
    RunConfig,
    "RunConfig",
    Optional[RunConfig],
    "Optional[RunConfig]",
    Mapping[str, Any],
    "Mapping[str, Any]",
    Optional[Mapping[str, Any]],
    "Optional[Mapping[str, Any]]",
    inspect.Parameter.empty,
)

#: 上游的**合法参数种类**（``langgraph/_internal/_runnable.py:248``）——
#: ``POSITIONAL_OR_KEYWORD`` / ``KEYWORD_ONLY`` ⇒ ⇒ ``POSITIONAL_ONLY``
#: **不在内**（上游同款 · 实测 **P-A18**）。
_VALID_PARAM_KINDS = (
    inspect.Parameter.POSITIONAL_OR_KEYWORD,
    inspect.Parameter.KEYWORD_ONLY,
)


def validate_conditional_payload(conditional_edges: Mapping[str, Any]) -> None:
    """**V-27** —— 条件边载荷的**五键**形态校验（**构造期** · L2 消费 L3 产物时核对）。

    * 外层 key MUST 是 **源节点名**（``str``）；
    * 内层 MUST 是 **tuple**（顺序 = **登记顺序**）；
    * 每项 MUST 是**恰 5 键**的 plain mapping（缺键 / 多键 / 键名不符 ⇒ 失败）；
    * 失败信号 = 内置 ``ValueError``（**零新增错误类型**）。

    ⚠️ **L3 的产出形态逐字已满足它** ⇒ 本校验是 **L2 侧的防御性核对**
    ⇒ ⇒ ⇒ **MUST NOT** 因为形态不符而**静默跳过**该条件边。
    """
    for source, entries in conditional_edges.items():
        if not isinstance(source, str):
            raise ValueError(
                f"conditional edge source must be str, got "
                f"{type(source).__name__} (V-27)"
            )
        if not isinstance(entries, tuple):
            raise ValueError(
                f"conditional edges for source {source!r} must be a tuple of "
                f"payloads, got {type(entries).__name__} (V-27)"
            )
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(
                    f"conditional edge payload for source {source!r} must be a "
                    f"mapping, got {type(entry).__name__} (V-27)"
                )
            keys = set(entry)
            if keys != set(CONDITIONAL_PAYLOAD_KEYS):
                raise ValueError(
                    f"conditional edge payload for source {source!r} must have "
                    f"exactly the keys {list(CONDITIONAL_PAYLOAD_KEYS)}, got "
                    f"{sorted(keys)} (V-27)"
                )


def evaluate_routes(
    channels: Mapping[str, Channel],
    entries: Sequence[Mapping[str, Any]],
    writes: Mapping[str, Sequence[Any]],
    *,
    producer: str,
    node_names: Container[str],
    config: Any,
) -> tuple[tuple[str, ...], tuple[Any, ...]]:
    """求值**一批**条件边 ⇒ ``(动态边目标序列, fan-out 任务序列)``。

    * ``channels`` —— **整张**通道表（fresh 读覆盖**全表** · 非「订阅集」）；
    * ``entries`` —— 同一源节点名下的**全部**条件边载荷（顺序 = 登记顺序）；
    * ``writes`` —— 该源节点**本次**的待写入（fresh 读的第二个入参）；
    * ``producer`` —— 源节点名（fan-out 任务的产生者）；
    * ``node_names`` —— **已注册节点名**（动态目标的校验口径）；
    * ``config`` —— 用户交给 ``invoke`` 的**原始** ``config``（双参形态的第二参）。

    ⚠️ **fresh 视图只构造一次** ⇒ 同一源节点的多条条件边**共享**同一份视图
    ⇒ ⇒ ⇒ 「每条条件边各求值一次」（FR-004）指的是**路由函数**的**调用次数**。

    ⚠️ **待写入只取「通道表里有的 key」** ⇒ ⇒ ⇒ fresh 读**不会**因「未知 key」
    提前抛 ``InvalidChannelUpdateError`` ⇒ ⇒ ⇒ 未知 key 仍由**阶段 ⑤**的写入
    合并抛既有的 ``InvalidUpdateError``（**失败信号逐字同款** · B7F3 的 **X-2**）。
    """
    if not entries:
        return (), ()
    known_writes = {
        key: values for key, values in writes.items() if key in channels
    }
    fresh = local_read(channels, known_writes, fresh=True)
    targets: list[str] = []
    fanout: list[Any] = []
    for entry in entries:
        resolved, sends = resolve_route_result(
            call_route_function(entry["path"], fresh, config),
            entry["path_map"],
            producer=producer,
            node_names=node_names,
        )
        targets.extend(resolved)
        fanout.extend(sends)
    return tuple(_dedupe(targets)), tuple(fanout)


def call_route_function(
    path: Callable[..., Any],
    fresh_view: Mapping[str, Any],
    config: Any,
) -> Any:
    """按**上游同款**的形态调用路由函数（单参 / 双参）。

    * 判别依据 = **第二参的参数名**是 ``config``（**不是**位置参数个数
      · 上游按**参数名**查 · ``langgraph/_internal/_runnable.py:341-365``）；
    * **永远只传一个位置实参**（fresh 视图）⇒ ``config`` 以**关键字**注入；
    * 第二参**不存在** / 名字**不叫** ``config`` / 是**仅位置**参数
      ⇒ 按**一参**调用（上游同款 ⇒ ``TypeError``）；
    * 第二参的注解**不在匹配集**内 ⇒ **跳过注入** ⇒ 按**一参**调用
      ⇒ ⇒ ⇒ ⚠️ **MUST NOT** 发 ``UserWarning``（上游的**附带诊断信号**
      · ``langgraph/_internal/_runnable.py:352-359`` ⇒ 偏离登记 **X-5**）；
    * ``**kwargs`` 形态 ⇒ **不注入**（上游同款 ⇒ kwargs 为空）；
    * 路由函数**自身**抛出的异常 ⇒ **原类型 + 原消息**传播（**不包装**）。

    ⚠️ **双参形态的第二参 = 用户交给 ``invoke`` 的**原始** ``config``**
    （``RunConfig`` / mapping / ``None`` · **逐字传入** · **MUST NOT** 归一化
    · **MUST NOT** 用 ``context`` 通道顶替）⇒ ⇒ ⇒ 这是 freegraph **自有的载体
    语义** ⇒ ⇒ ⇒ 与上游的 ``RunnableConfig`` **形态不同** ⇒ ⇒ ⇒ **X-5**。
    """
    if _accepts_config(path):
        return path(fresh_view, config=config)
    return path(fresh_view)


def _accepts_config(path: Callable[..., Any]) -> bool:
    """判别路由函数**是否**接受 ``config`` 注入（**照抄上游**的判别循环）。"""
    try:
        params = inspect.signature(path).parameters
    except (TypeError, ValueError):
        return False
    param = params.get("config")
    if param is None:
        return False
    if param.kind not in _VALID_PARAM_KINDS:
        return False
    return param.annotation in _CONFIG_ANNOTATIONS


def resolve_route_result(
    result: Any,
    path_map: Mapping[Hashable, str] | None,
    *,
    producer: str,
    node_names: Container[str],
) -> tuple[tuple[str, ...], tuple[Any, ...]]:
    """路由返回值 ⇒ ``(目标节点名序列, fan-out 任务序列)``。

    **三处判定**（``END`` · 契约 §4.3 · spec **FR-019**）：

    ① **单独返回** ``END``（**非序列**）⇒ **无条件终止**（判定**先于**
       ``path_map`` 查表 ⇒ 即使 ``path_map`` **不含** ``END`` 键也终止）
       ⇒ ⇒ ⇒ 偏离登记 **X-2**（上游：先查表 ⇒ ``{END: "b"}`` ⇒ 路由到 ``b``）；
    ② **标量**经 ``path_map`` **解析后**的目标是 ``END`` ⇒ **终止**该分支；
    ③ **序列**内的 ``END``（**无论以何种形式出现**：元素**恰为** ``END``，
       **或**元素经 ``path_map`` **解析后**为 ``END``）⇒ **被剔除**
       （其余目标**照常执行** · 照抄上游 **E-13**）。

    ⚠️ **序列 ⇒ 多目标**（共享状态 · 无逐目标载荷）⇒ 与 ``Send`` 的**逐目标
    载荷**语义**相异**（裁定 9）⇒ ⇒ ⇒ ``Send`` **不查表**（上游同款
    · ``langgraph/graph/_branch.py:203``）⇒ ⇒ ⇒ ``Send`` 走 **B11F1 的既有
    构造器** ⇒ ⇒ ⇒ **MUST NOT** 另写条件边专属 fan-out 路径。
    """
    if isinstance(result, Send):
        return (), make_fanout(
            producer, [result], node_names, suppresses_static=True
        )
    if isinstance(result, (list, tuple)):
        targets: list[str] = []
        sends: list[Any] = []
        for item in result:
            if isinstance(item, Send):
                sends.append(item)
                continue
            if item == _END_MARKER:
                continue  # ③：元素**恰为** ``END`` ⇒ 剔除（**不**查表）
            resolved = _lookup(item, path_map, node_names=node_names)
            if resolved is None:
                continue  # ③：元素**解析后**为 ``END`` ⇒ 剔除
            targets.append(resolved)
        fanout = (
            make_fanout(producer, sends, node_names, suppresses_static=True)
            if sends
            else ()
        )
        return tuple(targets), fanout
    if result == _END_MARKER:
        return (), ()  # ①：单独返回 ``END`` ⇒ 无条件终止（**先于**查表）
    resolved = _lookup(result, path_map, node_names=node_names)
    if resolved is None:
        return (), ()  # ②：标量**解析后**为 ``END`` ⇒ 终止该分支
    return (resolved,), ()


def _lookup(
    value: Any,
    path_map: Mapping[Hashable, str] | None,
    *,
    node_names: Container[str],
) -> str | None:
    """解析**单个**路由返回值 ⇒ 目标节点名（``None`` ⇒ ``END`` · 该分支终止）。

    * **有** ``path_map`` ⇒ 返回值作 **key** 查表 ⇒ 取其 **value**
      ⇒ ⇒ ⇒ 查表失败 ⇒ 内置 ``KeyError``（**消息比上游详细** · 偏离 **X-1**）
      ⇒ ⇒ ⇒ ⚠️ **不可哈希**的返回值 ⇒ 内置 ``TypeError``（上游同款
      · ``dict.__getitem__`` 对不可哈希键的类型错误）；
    * **无** ``path_map``（动态目标）⇒ 返回值**直接**作节点名
      ⇒ ⇒ ⇒ 非**已注册节点名** / 非 ``END`` ⇒ 内置 ``ValueError``
      （**比上游更严** · 上游**静默忽略** ⇒ 偏离 **X-3**）。
    """
    if path_map is not None:
        try:
            resolved = path_map[value]
        except KeyError:
            raise KeyError(
                f"route function returned {value!r}, which is not a key of "
                f"path_map; allowed return values: {list(path_map)!r}; "
                f"target nodes: {list(path_map.values())!r}"
            ) from None
        return None if resolved == _END_MARKER else resolved
    if value is None or value == _START_MARKER:
        raise ValueError(
            f"route function returned {value!r}, which is not a valid "
            f"destination; registered nodes: {sorted(node_names)!r}"
        )
    if not isinstance(value, str) or value not in node_names:
        raise ValueError(
            f"route function returned {value!r}, which is not a registered "
            f"node; registered nodes: {sorted(node_names)!r}"
        )
    return value


def _dedupe(values: Sequence[str]) -> list[str]:
    """**去重保序**（同一目标**只**触发一次 · 契约 §4.3）。"""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
