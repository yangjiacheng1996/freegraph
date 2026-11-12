# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L2 执行内核层 · **并发执行器** —— 属 **B12F1**（**内部模块** · **不进** ``__all__``）。

本模块是 freegraph 的**同轮并发执行**的唯一实现点：把「同一 super-step 内的**全部**
被触发节点任务」放到**标准库线程池**里**并发**跑，并让每个任务只产出一个**私有的
结果槽**（**执行期零共享状态写**）。

**契约权威**：``specs/b12f1-concurrency-errors/contracts/concurrency-contract.md``
（``<!-- authority: yes -->``）⇒ 本模块 MUST NOT 另立一套口径。

**设计要点**（逐条附来源）：

* **线程**（不是 async / 不是进程）—— 上游同款：上游**同步**路径用线程池跑节点任务
  （``langgraph/pregel/_executor.py:40-52`` 的 ``BackgroundExecutor`` · ``:54-75`` 的
  ``submit``）⇒ 语义与上游同构（spec 裁定 1）；
* **并发度有上限** —— 缺省 ``min(32, cpu+4)``（**上游同款** · ``langchain_core/
  runnables/config.py:660-674`` 的 ``get_executor_for_config``）；显式 ``N`` ⇒
  ``min(本轮任务数, N)`` ⇒ **N MUST NOT** 被 32 再夹一次（spec 裁定 2 / 18）；
* **每轮新建 + 每轮关闭** —— 线程池 MUST 在**本轮返回前**结束 ⇒ **零悬挂线程**
  （上游同款 · ``langgraph/pregel/_executor.py:93-119`` 的 ``BackgroundExecutor.__exit__``）；
* **执行期零共享状态写** —— 工作线程**只**产出**结果槽** ⇒ 轮末由调度器按
  **节点名序**统一落回（spec FR-010 · 裁定 11）⇒ 杜绝竞态；
* **失败处置** —— 首个真实异常出现 ⇒ **取消「排队未启动」**的任务
  （``Future.cancel()`` → ``True``）⇒ **运行中**的任务**不中断**、但**被等待**
  （**上游同款** · ``langgraph/pregel/_runner.py:679-680``）⇒ 「**取消**」的触发口径是
  **墙钟时刻第一个**失败，而「**抛出哪个**」的口径是**节点名序**最靠前者 ⇒
  **两个独立口径**（spec FR-003 的「口径分离」段）；
* **异常原样** —— 工作线程**不包装**异常 ⇒ ``caught is raised_by_node`` 成立
  （spec FR-003 · B7F1 契约 I-15 不破）；
* **中断不是「出错」** —— ``GraphInterrupt`` 被**原样收集**进结果槽的 ``interrupts``
  ⇒ 轮末合并抛出**一个**（载荷 = **元组** · **节点名序**）（spec FR-004 / FR-013）。

**依赖纪律**（FR-007 · L2）：本模块只依赖**标准库**（``concurrent.futures`` /
``os`` / ``threading``）与 **L1** 的 ``freegraph.contracts.errors`` /
``freegraph.contracts.types`` ⇒ **零第三方依赖**；MUST NOT import
``langchain*`` / ``langgraph*`` / ``langsmith``；MUST **零出站**、零文件 I/O、
零环境变量读取（``os.cpu_count()`` 是**系统调用** · **非**环境变量）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Any

from freegraph.contracts.errors import GraphInterrupt
from freegraph.contracts.types import Interrupt

__all__: list[str] = []

#: **并发度的缺省上限**（**上游同款** · ``langchain_core/runnables/config.py:660-674``）。
#:
#: 上游把 ``max_workers`` 交给 Python 标准库的线程池 ⇒ 缺省即
#: ``min(32, (os.cpu_count() or 1) + 4)`` ⇒ **freegraph 同款**（spec 裁定 2 / 18）。
_DEFAULT_CAP_FLOOR = 32

#: 线程名前缀（便于诊断与线程计数断言 · 契约 §4）。
_THREAD_NAME_PREFIX = "freegraph-node"

#: **其余并发失败**的附注前缀（**固定格式** · 契约 §6 · spec FR-003 · 裁定 6）。
NOTE_PREFIX = "其它并发失败"


@dataclass(frozen=True, slots=True)
class _TaskOutcome:
    """一个任务在**执行期**产出的**私有**结果（执行期**零共享状态写**）。

    **契约**：``specs/b12f1-concurrency-errors/data-model.md`` §2.1（EM-1）·
    ``contracts/concurrency-contract.md`` §4。

    * ``writes`` —— **待写入**（通道 key → 值序列）；
    * ``gotos`` —— **跳转目标**（``Command.goto`` 解析后的）；
    * ``error`` —— **真实异常**（**原对象** · **不包装**）⇒ ``None`` 表示本节点未失败；
    * ``interrupts`` —— 该节点 ``GraphInterrupt.args[0]``（≡ ``payload``）的
      **元素**（``Interrupt`` 对象 · **原样** · 不包装）⇒
      ⚠️ MUST **NOT** 是 ``payload`` **本身**（那是元组 ⇒ 嵌套元组 ⇒ 元素**没有**
      ``.value`` / ``.id`` ⇒ SC-010 不可判定）（spec FR-004 / FR-013 · 裁定 7）。

    ⚠️ **私有**（前导下划线）⇒ **不进** ``freegraph.runtime.__all__``（仍 20 个符号 ·
    裁定 13）⇒ **不进** API 兼容矩阵。
    """

    writes: dict[str, tuple[Any, ...]]
    gotos: tuple[str, ...]
    error: BaseException | None
    interrupts: tuple[Interrupt, ...]


def _resolve_cap(task_count: int, max_concurrency: int | None) -> int:
    """算本轮的**实际并发度**（契约 §2 / §4）。

    * 缺省（``max_concurrency=None``）⇒ 上限 = ``min(32, cpu+4)``（**上游同款**）；
    * 显式 ``N`` ⇒ 上限 = ``N`` ⇒ ⚠️ **N MUST NOT** 被 32 再夹一次；
    * 实际并发度 = ``min(本轮任务数, 上限)``。

    ⚠️ ``os.cpu_count()`` 是**系统调用**（**非**环境变量）⇒ 不破零环境变量红线
    （spec FR-007 · 宪法原则 I）。
    """
    if max_concurrency is None:
        ceiling = min(_DEFAULT_CAP_FLOOR, (os.cpu_count() or 1) + 4)
    else:
        ceiling = max_concurrency
    return min(task_count, ceiling)


def _worker(node_name: str, fn: Callable[[], dict[str, Any]]) -> _TaskOutcome:
    """工作线程：执行一个任务 ⇒ 产出一个**结果槽**。

    * ``fn`` —— 节点的**纯执行**（调 ``node.run`` + 归一）⇒ **零共享状态写**；
    * **捕获顺序 MUST**：``GraphInterrupt`` **先于** ``Exception``
      ⇒ 因为 ``GraphInterrupt`` 是 ``Exception`` 的子类（``freegraph.contracts.errors``
      的 ``FreegraphError(Exception)``）⇒ 顺序反了会把**中断**误判为**真异常**
      ⇒ 直接冲击 spec FR-014（真异常优先）；
    * ⚠️ **只**捕获 ``Exception`` ⇒ ``KeyboardInterrupt`` / ``SystemExit``
      （``BaseException``）**不进**结果槽 ⇒ 线程池把它**存进 future** ⇒ 轮末
      ``future.result()`` **重抛** ⇒ **中止整轮**（**上游同款** · 上游的
      ``except Exception`` 同样不拦 ``BaseException``）；
    * ⚠️ **其余失败**由调用方（调度器）按**节点名序**挑选「抛出的那个」⇒ 本函数
      **不做**挑选（避免依赖完成时刻的竞态 · spec FR-003 · 偏离登记 **X-1**）。
    """
    try:
        normalized = fn()
    except GraphInterrupt as exc:
        # ⚠️ **原样收集**（裁定 7 · 裁定 20）⇒ 取 ``args[0]``（≡ ``payload``）的
        # **元素** ⇒ MUST **NOT** 把 ``payload`` 本身塞进去（⇒ 嵌套元组）。
        payload = exc.args[0] if exc.args else ()
        return _TaskOutcome(writes={}, gotos=(), error=None, interrupts=tuple(payload))
    except Exception as exc:  # noqa: BLE001 - **原对象**原样上抛（不包装）
        return _TaskOutcome(writes={}, gotos=(), error=exc, interrupts=())
    return _TaskOutcome(
        writes=dict(normalized["writes"]),
        gotos=tuple(normalized["gotos"]),
        error=None,
        interrupts=(),
    )


def _cancel_pending(futures: Iterable[Future[Any]]) -> None:
    """取消「**排队未启动**」的同轮任务（契约 §4 / §6 · spec FR-003）。

    * 遍历**未完成**的 future 调 ``.cancel()`` ⇒ **排队未启动**者返回 ``True``
      （**不执行**）· **运行中**者返回 ``False``（**不中断**、但**被等待**）
      ⇒ **上游同款**（``langgraph/pregel/_runner.py:679-680``）；
    * ⚠️ MUST **NOT** 取消**运行中**的任务（会中断用户代码 ⇒ 用户无法善后）；
    * ⚠️ MUST **NOT** 等待未启动者（它们已被取消 ⇒ 永远不会跑）。
    """
    for fut in futures:
        # ⚠️ 对**已完成**的 future 调 ``cancel()`` 是**安全空操作**（返回 ``False``）
        # ⇒ 无需额外判分支（``Future.cancel()`` 的语义保证）。
        fut.cancel()


def attach_failure_notes(
    error: BaseException,
    outcomes: Iterable[tuple[str, _TaskOutcome]],
) -> None:
    """把**其余**并发失败以**附注**记录在抛出的那个异常上（契约 §6 · FR-003 · V-15）。

    * ⚠️ **附注的固定格式**且 MUST 同时含**节点名** · **异常类型名** · **消息**三样
      ⇒ 形如 ``其它并发失败 · 节点 <节点名>：<异常类型名>: <异常消息>``
      ⇒ ⇒ 判据可自动断言 ⇒ MUST **NOT** 只写其中一两样；
    * ⚠️ **附注 MUST NOT** 改变异常的**类型 / 消息 / 对象 identity**
      ⇒ 用标准库的 ``BaseException.add_note``（Python **3.11** 引入）
      ⇒ B7F1 契约 **I-15** 不破；
    * ⚠️ **已取消**的任务**没有结果槽** ⇒ 其异常**不**收集（未发生 ⇒ 无异常）；
    * ⚠️ **抛出**的那个异常本身**不**被附注 ⇒ 只记**其余**失败；
    * ⚠️ 遍历顺序 = **节点名序** ⇒ 附注的**顺序**也可复现。
    """
    for node_name, outcome in outcomes:
        other = outcome.error
        if other is None or other is error:
            continue
        error.add_note(f"{NOTE_PREFIX} · 节点 {node_name}：{type(other).__name__}: {other}")


def run_tasks_concurrently(
    tasks: Iterable[tuple[str, Callable[[], dict[str, Any]]]],
    *,
    cap: int,
) -> list[_TaskOutcome]:
    """并发跑一批任务 ⇒ 返回**按节点名序**排列的结果槽列表（契约 §4）。

    * ``tasks`` —— ``(节点名, 纯执行函数)`` 的序列 ⇒ **提交顺序 = 节点名序**
      ⇒ 「首个异常」的选取 = **扫结果槽的第一个**（**不**依赖完成时刻）；
    * ``cap`` —— **实际并发度**（由 :func:`_resolve_cap` 算）⇒
      ``ThreadPoolExecutor`` 的 ``max_workers``；
    * **零节点** ⇒ 直接返回 ``[]`` ⇒ **MUST NOT** 建池 ⇒ **零线程**
      （spec FR-001 · 契约 §4）；
    * **每轮新建 + 每轮关闭** ⇒ **零悬挂线程**（spec FR-018 · I-16）；
    * ⚠️ **中途感知失败**：``wait(..., return_when=FIRST_COMPLETED)`` ⇒ 一旦有
      future 完成且其结果槽带 ``error`` ⇒ **立刻**取消「排队未启动」者
      ⇒ ⇒ 这正是**上游同款**的时序（上游在 ``_runner.py:281-345`` 的
      ``FIRST_COMPLETED`` 循环里发现失败即 ``break`` → ``_panic_or_proceed``
      取消 ``inflight``）⇒ ⇒ 若等轮末才取消，排队者**早已被启动**
      ⇒ 「机制级」判据（``cancel()`` → ``True``）会**必红**；
    * ⚠️ **运行中者跑完并被等待** ⇒ 收尾时逐个 ``future.result()``；
    * ⚠️ **被取消**的任务**不产出结果槽** ⇒ 它**从未被启动** ⇒ MUST **NOT** 出现在
      ``executed`` 里（spec FR-009 · 裁定 22）；
    * ⚠️ **``BaseException``**（``KeyboardInterrupt`` / ``SystemExit``）⇒ 由
      ``future.result()`` **重抛** ⇒ **中止整轮**（**MUST NOT** 被吞成普通失败）。
    """
    materialized = list(tasks)
    if not materialized:
        return []  # ⚠️ **零节点不建池** ⇒ 零线程（spec FR-001）

    outcomes: dict[str, _TaskOutcome] = {}
    with ThreadPoolExecutor(
        max_workers=max(1, cap), thread_name_prefix=_THREAD_NAME_PREFIX
    ) as executor:
        futures: dict[Future[Any], str] = {}
        for node_name, fn in materialized:
            futures[executor.submit(_worker, node_name, fn)] = node_name

        pending: set[Future[Any]] = set(futures)
        failed = False
        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for fut in done:
                # ⚠️ ``done`` 里的 future **不可能是「被取消」的** —— 取消只发生在
                # 下面 ``_cancel_pending(pending)`` 之后（**wait 返回之后**）⇒
                # ⇒ 这里 ``fut.result()`` **不会**抛 ``CancelledError``。
                outcome = fut.result()  # ⚠️ BaseException 在此**重抛**
                outcomes[futures[fut]] = outcome
                if outcome.error is not None:
                    failed = True
            if failed:
                # ⚠️ **墙钟时刻第一个**失败 ⇒ 取消「排队未启动」者（上游同款）
                _cancel_pending(pending)
                break

        # 收尾：**运行中**者跑完并被等待；被取消者跳过；已收者跳过。
        for fut, name in futures.items():
            if name in outcomes:
                continue
            if fut.cancelled():
                continue
            outcome = fut.result()  # ⚠️ BaseException 在此**重抛**
            outcomes[name] = outcome

    return [outcomes[name] for name in sorted(outcomes)]
