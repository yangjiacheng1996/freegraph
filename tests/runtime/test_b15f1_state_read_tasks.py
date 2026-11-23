# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B15F1 · ``assemble_tasks`` 的 next-tasks 全场景（含 fan-out 两类来源 / 混合轮）。

直接验证 L2 私有组装助手：``fanout`` 账本来源的 ``id`` 是**本地 index**（非运行时
``task_key``），``next`` 来源的 ``id`` 是运行时 ``task_key``；两源**不跨源去重**。
"""

from __future__ import annotations

from freegraph.contracts import Interrupt
from freegraph.runtime._state_read import assemble_interrupts, assemble_tasks


def _fanout_scheduler() -> dict:
    return {
        "fanout": {
            "0": {
                "producer": "p",
                "suppresses_static": True,
                "tasks": [
                    {"target": "w", "arg": 1, "index": 0},
                    {"target": "w", "arg": 2, "index": 1},
                ],
            }
        }
    }


def test_convergence_and_empty_scheduler_yield_no_tasks() -> None:
    assert assemble_tasks((), {}, ()) == ()
    assert assemble_tasks((), None, ()) == ()


def test_standard_next_task_uses_node_name() -> None:
    tasks = assemble_tasks(("b",), {}, ())
    assert len(tasks) == 1
    task = tasks[0]
    assert task.id == "b"
    assert task.name == "b"
    assert task.path == ("b",)
    assert task.interrupts == ()


def test_fanout_ledger_source_uses_local_index_and_no_interrupts() -> None:
    tasks = assemble_tasks((), _fanout_scheduler(), ())
    assert [(task.id, task.name, task.path, task.interrupts) for task in tasks] == [
        ("w:0", "w", ("w", 0), ()),
        ("w:1", "w", ("w", 1), ()),
    ]


def test_next_fanout_source_uses_runtime_task_key_and_attaches_interrupts() -> None:
    payload = (Interrupt(value={"q": 1}, id="i1"),)
    tasks = assemble_tasks(("w:3",), {}, [("w:3", "__interrupt__", payload)])
    assert len(tasks) == 1
    task = tasks[0]
    assert task.id == "w:3"
    assert task.name == "w"
    assert task.path == ("w", 3)
    assert task.interrupts == payload


def test_mixed_round_does_not_dedup_across_sources() -> None:
    payload = (Interrupt(value={"q": 1}, id="i1"),)
    tasks = assemble_tasks(
        ("w:3",), _fanout_scheduler(), [("w:3", "__interrupt__", payload)]
    )
    ids = [task.id for task in tasks]
    # ledger (w:0 / w:1) and next (w:3) coexist; no cross-source dedup
    assert ids == ["w:0", "w:1", "w:3"]
    assert assemble_interrupts(tasks, ()) == payload


def test_unattached_pending_interrupt_is_appended_not_dropped() -> None:
    payload = (Interrupt(value={"q": 2}, id="i2"),)
    tasks = assemble_tasks((), {}, [("orphan:9", "__interrupt__", payload)])
    assert len(tasks) == 1
    assert tasks[0].id == "orphan:9"
    assert tasks[0].name == "orphan"
    assert tasks[0].interrupts == payload
