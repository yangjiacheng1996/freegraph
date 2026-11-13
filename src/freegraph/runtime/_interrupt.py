# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L2 执行内核层 · **中断原语**（``interrupt()``） —— 属 **B10F1**（**内部模块**）。

本模块是 ``interrupt()`` 的**运行期机制**的唯一落点：**两级** ``contextvars``
+ **任务现场** + **``.id`` 生成** + **恢复值消费**。

**契约权威**：``specs/b10f1-interrupt-resume/contracts/interrupt-resume-contract.md``
（§3「两级上下文」· §4「``interrupt()`` 的语义」· §4.1「``.id`` 的生成」）
⇒ 本模块 MUST NOT 另立一套口径。

**设计要点**（逐条附来源）：

* **两级 ``ContextVar``**（契约 §3）—— ① **运行级**（``_RUN``）：载荷 =
  「**按节点名**的现场表」（``{节点名: _TaskScratchpad}``）⇒ 由
  :func:`bind_run` 在**整次运行**期间设置、返回前 ``reset(token)`` 复原；
  ② **任务级**（``_TASK``）：载荷 = **该节点**的现场 ⇒ 由 :func:`bind_task`
  在**每个节点执行**前设置、执行后 ``reset(token)`` 复原；
* ⚠️ **线程池**不继承 ``contextvars``（**实测**：``ThreadPoolExecutor`` 的工作
  线程读到的是**缺省值**）⇒ ⇒ **运行级**的现场表由**主线程**的 ``_RUN``
  读出后**显式**交给工作线程（``bind_task`` 的第二个参数）⇒ ⇒
  「**现场表**」与「**ContextVar**」**并存**（ContextVar 承载**可见性**、
  显式参数承载**跨线程可达性**）⇒ ⇒ **零**共享可变状态；
* **任务现场**的**四个**字段（契约 §3）：``resume``（该节点**已提供**的恢复值 ·
  **按节点内顺序**）· ``index``（该节点内**第几次**调用 ``interrupt()``）·
  ``existing``（该节点**先前**挂起时的中断载荷 ⇒ **复用**其 ``.id``）·
  ``namespace``（命名空间 ``f"{节点名}:{uuid4().hex}"``）；
* **``.id`` 的生成**（契约 §4.1 · DR-03）—— 命名空间 = ``f"{节点名}:{uuid4().hex}"``
  ⇒ **含随机量** ⇒ **不可猜**；摘要 = ``hashlib.blake2b(ns, digest_size=16)``
  ⇒ **32 位十六进制**（与上游 ``xxh3_128`` **同长度**）⇒ ⇒ **零第三方依赖**
  （宪法「依赖白名单」：必装运行时依赖 = 无）⇒ 偏离登记 **X-4**；
* ⚠️ **跨恢复稳定**（spec **F-1**）—— **恢复时直接复用** pending writes 里那个
  ``Interrupt`` 的**既有** ``.id`` ⇒ ⇒ **不重算** ⇒ ⇒ **零新增持久化字段**
  （uuid **不落盘**）⇒ ⇒ 同一「挂起 → 恢复 → 再挂起」循环内 ``.id`` **逐字相同**；
* **恢复值的消费**（spec **裁定 7** · 上游 ``langgraph/types.py:955-958``）——
  第 ``index`` 次调用 ⇒ 若 ``index < len(resume)`` ⇒ **返回** ``resume[index]``
  ⇒ **不**抛中断；**否则** ⇒ **再次挂起**（**不**报错）。

**依赖纪律**（FR-023 · L2）：本模块只依赖**标准库**（``contextvars`` /
``hashlib`` / ``uuid`` / ``dataclasses`` / ``contextlib``）与 **L1** 的
``freegraph.contracts`` ⇒ **零第三方依赖**；MUST NOT import ``langchain*`` /
``langgraph*`` / ``langsmith``；MUST **零出站**、零文件 I/O、零环境变量读取。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import contextvars
import hashlib
import uuid
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from freegraph.contracts.errors import GraphInterrupt
from freegraph.contracts.types import Interrupt

from .errors import InterruptError

#: **私有模块** ⇒ ``__all__`` **恒空**（不进 ``freegraph.runtime.__all__``
#: ⇒ 不进 API 兼容矩阵 · 与 B12F1 的 ``_concurrency.py`` **同款**）。
__all__: list[str] = []


@dataclass
class _TaskScratchpad:
    """**任务现场** —— 一个节点在**一次执行**里的中断上下文。

    **四个**字段（契约 §3 · data-model **EM-8** · **逐字冻结**）：

    * ``resume`` —— 该节点**已提供**的恢复值（**按节点内顺序** · 上游同款）⇒
      第 ``index`` 次调用 ``interrupt()`` 取 ``resume[index]``；
    * ``index`` —— 该节点内**第几次**调用 ``interrupt()``（**原子计数** ⇒
      **不**跨节点共享）⇒ **第 2 次**调用取 ``resume[1]``；
    * ``existing`` —— 该节点**先前**挂起时的中断载荷（**恢复时读回** ⇒
      **复用**其 ``.id`` ⇒ 跨恢复**逐字稳定**）⇒ 首次挂起时为**本次**产生的
      中断载荷（**同一字段** · 「该节点挂起时的中断载荷」）；
    * ``namespace`` —— 命名空间 ``f"{节点名}:{uuid4().hex}"``（**含随机量** ⇒
      ``.id`` **不可猜**）。
    """

    resume: list[Any] = field(default_factory=list)
    index: int = 0
    existing: Interrupt | None = None
    namespace: str | None = None


#: **运行级**现场表（契约 §3 · 运行级行）—— 载荷 = ``{节点名: _TaskScratchpad}``。
#:
#: ⚠️ **缺省 = ``None``**（**不是** ``{}``）⇒ ⇒ **不**共享可变缺省值
#: （``ContextVar`` 的可变缺省会被**所有**上下文共享 ⇒ 跨运行串味）。
_RUN: contextvars.ContextVar[dict[str, _TaskScratchpad] | None] = (
    contextvars.ContextVar("freegraph_interrupt_run", default=None)
)

#: **任务级**现场（契约 §3 · 任务级行）—— 载荷 = 该节点的任务现场。
#:
#: ⚠️ 缺省 = ``None`` ⇒ ⇒ 「**图运行之外**调用 ``interrupt()``」**可判定**
#: （``not_in_run`` · spec **FR-025**）。
_TASK: contextvars.ContextVar[_TaskScratchpad | None] = contextvars.ContextVar(
    "freegraph_interrupt_task", default=None
)


def make_namespace(node_name: str) -> str:
    """产出该节点的**命名空间**（契约 §4.1 第 1 步 · **上游同款** · E-23）。

    形态 = ``f"{节点名}:{uuid4().hex}"`` ⇒ ⇒ **含随机量** ⇒ ⇒ ``.id``
    **不可猜**（「替这次审批拍板」的**能力凭据不可被推导」）。

    ⚠️ **标准库 ``uuid``**（``os.urandom`` 支撑 · **非**环境变量）⇒ ⇒
    **零环境变量红线**不破（宪法原则 I）。
    """
    return f"{node_name}:{uuid.uuid4().hex}"


def make_interrupt_id(namespace: str) -> str:
    """由**命名空间**算出 ``.id``（契约 §4.1 第 2–3 步 · 偏离登记 **X-4**）。

    * 摘要 = ``hashlib.blake2b(ns.encode(), digest_size=16)`` ⇒ **16 字节** ⇒
      **32 位十六进制**（与上游 ``xxh3_128_hexdigest`` **同长度** · E-9）；
    * ⚠️ **标准库**（``hashlib``）⇒ ⇒ **零第三方依赖** ⇒ ⇒ 上游的 ``xxhash``
      **不可用** ⇒ **必须自研区 ①**（宪法「依赖白名单」：必装运行时依赖 = 无）。

    ⇒ **长度与唯一性**与上游**同款** ⇒ ⇒ ``.id`` 的**用途**（唯一定位一次中断）
    **不受影响**（偏离登记 **X-4** · **DIFF** · 非更严）。
    """
    return hashlib.blake2b(namespace.encode("utf-8"), digest_size=16).hexdigest()


def new_run_table() -> dict[str, _TaskScratchpad]:
    """新建一张**运行级**现场表（空表 ⇒ 每个节点**首次执行**时现场自建）。"""
    return {}


def current_run_table() -> dict[str, _TaskScratchpad] | None:
    """取当前上下文的**运行级**现场表（**无** ⇒ ``None``）。

    ⚠️ **只在主线程读**（线程池的工作线程**不继承** ``contextvars`` · **实测**）
    ⇒ ⇒ 调用方 MUST 把结果**显式**交给工作线程（见 :func:`bind_task`）。
    """
    return _RUN.get()


@contextmanager
def bind_run(table: dict[str, _TaskScratchpad]) -> Iterator[dict[str, _TaskScratchpad]]:
    """在**整次运行**期间设置**运行级**现场表（契约 §3 · 运行级行）。

    * 返回前 MUST ``reset(token)`` 复原 ⇒ ⇒ **零脏状态**（线程池复用线程时
      **不串味**）；
    * ⚠️ **只在主线程调用**（工作线程**不继承** ``contextvars``）。
    """
    token = _RUN.set(table)
    try:
        yield table
    finally:
        _RUN.reset(token)


def prepare_task(
    table: dict[str, _TaskScratchpad],
    node_name: str,
    *,
    resume: Sequence[Any] = (),
    existing: Interrupt | None = None,
) -> _TaskScratchpad:
    """**预置**某节点的**任务现场**（恢复路径 / 会话连续路径用）。

    * ``resume`` —— 该节点**已提供**的恢复值序列（**已按节点内顺序**）⇒
      节点第 ``index`` 次调用 ``interrupt()`` 取 ``resume[index]``；
    * ``existing`` —— 该节点**先前**挂起时的中断载荷 ⇒ ⇒ **复用**其 ``.id``
      ⇒ ⇒ **跨恢复稳定**（spec **F-1**）；
    * ⚠️ **不**消费 ``__resume__``（会话连续路径 · spec FR-013 末两行）⇒ ⇒
      调用方 MUST **不**在此路径写入恢复值。
    """
    scratchpad = table.get(node_name)
    if scratchpad is None:
        scratchpad = _TaskScratchpad(namespace=make_namespace(node_name))
        table[node_name] = scratchpad
    scratchpad.resume = list(resume)
    scratchpad.existing = existing
    return scratchpad


@contextmanager
def bind_task(
    node_name: str, table: dict[str, _TaskScratchpad] | None = None
) -> Iterator[_TaskScratchpad]:
    """在**每个节点执行**期间设置**任务级**现场（契约 §3 · 任务级行）。

    * ``table`` —— **运行级**现场表（由**主线程**读出后**显式**传入 ⇒
      线程池的工作线程**不继承** ``contextvars`` ⇒ 必须显式传递 · **实测**）；
      **``None``** ⇒ 本次执行**自建**一张临时表（既有入口
      ``run_super_steps`` 的场景 ⇒ 节点里的 ``interrupt()`` **照样**抛中断）；
    * MUST ``reset(token)`` 复原 ⇒ ⇒ 线程池**复用线程**时**零脏状态**。
    """
    target: dict[str, _TaskScratchpad] = table if table is not None else {}
    scratchpad = target.get(node_name)
    if scratchpad is None:
        scratchpad = _TaskScratchpad(namespace=make_namespace(node_name))
        target[node_name] = scratchpad
    run_token = _RUN.set(target)
    task_token = _TASK.set(scratchpad)
    try:
        yield scratchpad
    finally:
        _TASK.reset(task_token)
        _RUN.reset(run_token)


def interrupt(value: Any) -> Any:
    """**请求外部输入** —— 节点内的人工介入（HITL）原语（**上游同款**）。

    **签名**（**逐字冻结** · 契约 §4）::

        interrupt(value: Any) -> Any

    * **位置或关键字**皆可（**上游同款** · ``langgraph/types.py:851``）；
    * **图运行之外**调用 ⇒ 抛 ``InterruptError(reason="not_in_run")``
      （spec **FR-025** · 上游 ``langgraph/config.py:26-29`` 抛 ``RuntimeError``
      ⇒ **类型**差异见偏离登记 **X-2**）；
    * 节点内 · **有**可用的恢复值（``index < len(resume)``）⇒ **返回**
      ``resume[index]``（**不**抛中断 · 上游 ``langgraph/types.py:955-958``）；
    * 节点内 · **无**可用的恢复值 ⇒ 抛 ``GraphInterrupt((Interrupt(...),))``
      （**载荷 = 1-元组** · 上游 ``langgraph/types.py:967-974``）⇒
      ⇒ **图挂起**（spec **FR-001** / **FR-002**）。

    ⚠️ **``.id`` 的三种来源**（**不重算** ⇒ 跨恢复**逐字稳定**）：

    ① 现场带 ``existing``（**恢复路径**）⇒ ⇒ **复用** ``existing.id``；
    ② 否则 ⇒ 由**命名空间**算（``blake2b-128`` · 32 位十六进制）；
    ③ ⇒ 本次产生的载荷**写回** ``existing`` ⇒ ⇒ 同一节点**再次挂起**时
    仍**复用**同一个 ``.id``（spec **F-1**）。

    ⚠️ **``.id`` MUST NOT** 由用户自带（spec **FR-003** · C17）。
    """
    scratchpad = _TASK.get()
    if scratchpad is None:
        raise InterruptError(reason=InterruptError.REASON_NOT_IN_RUN)
    index = scratchpad.index
    scratchpad.index = index + 1
    if index < len(scratchpad.resume):
        return scratchpad.resume[index]
    if scratchpad.existing is not None:
        interrupt_id = scratchpad.existing.id
    else:
        namespace = scratchpad.namespace
        if namespace is None:
            namespace = make_namespace("")
            scratchpad.namespace = namespace
        interrupt_id = make_interrupt_id(namespace)
    produced = Interrupt(value=value, id=interrupt_id)
    # ⚠️ **写回** ``existing`` ⇒ ⇒ 同一节点**再次挂起**时**复用**同一个 ``.id``
    # （spec **F-1** · **跨恢复稳定**）⇒ ⇒ 同时成为「运行级」现场表里的
    # 「本次产生的中断载荷」（供挂起时的写侧按节点落 pending write）。
    scratchpad.existing = produced
    raise GraphInterrupt((produced,))
