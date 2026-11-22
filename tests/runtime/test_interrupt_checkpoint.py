# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**US4** · 恢复路径确实经由 checkpointer（**P4**）—— 读侧 / 写侧契约 + **桩**。

**判据**：SC-005（恢复时读到**快照 + 待写入**）· SC-012 的写侧半边（挂起时
**写**快照 + **写**中断留痕）· FR-010 的**核心禁令**（**跨运行**不得持有
「待恢复现场」）· data-model **V-12**（``.scheduler`` 的 **JSON** 往返）。

**契约权威**：``specs/b10f1-interrupt-resume/contracts/checkpoint-contract.md``
§2（读侧）· §3（调度账本的编码）· §4（写侧）· §5（保留通道名）。

⚠️ **本 feature MUST NOT 交付任何 checkpointer 实现**（FR-019 ⇒ ``MemorySaver``
属 **B14F1 / M3**）⇒ ⇒ 本模块的 ``StubCheckpointer`` 是**测试替身**
（记录调用的**桩**）⇒ ⇒ **零** saver 语义。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from freegraph.contracts.types import RunConfig, StateSnapshot
from freegraph.graph import interrupt
from freegraph.runtime import GraphSpec, InterruptResult, NodeSpec, run_graph
from freegraph.runtime.channel import LastValue

#: 图的通道（**覆盖型** · 无归约器 ⇒ 覆盖）。
_CHANNELS: dict[str, LastValue] = {
    "messages": LastValue("messages", list),
    "count": LastValue("count", int),
}


def _thread_id(config: Any) -> str:
    """取会话标识（``RunConfig.thread_id`` · 兼容 ``configurable`` 里的写法）。"""
    resolved = getattr(config, "resolved_thread_id", None)
    if callable(resolved):
        value = resolved()
        if value is not None:
            return str(value)
    return str(getattr(config, "thread_id", ""))


class _CheckpointTuple:
    """``get_tuple`` 的返回值 —— **三个具名属性**（契约 §2）+ **访问记录**。

    ⚠️ **访问记录** ⇒ ⇒ 「三项**均被读取**」**可判定**（SC-005）⇒ ⇒
    「恢复**确实**经由 checkpointer」**不是**一句口号（**逐项**可断言）。
    """

    def __init__(
        self,
        snapshot: StateSnapshot,
        pending_writes: tuple[tuple[str, str, Any], ...],
        scheduler: dict[str, Any],
    ) -> None:
        self._snapshot = snapshot
        self._pending_writes = pending_writes
        self._scheduler = scheduler
        #: 被**读取过**的属性名（SC-005 的判据载体）。
        self.accessed: set[str] = set()

    @property
    def snapshot(self) -> StateSnapshot:
        self.accessed.add("snapshot")
        return self._snapshot

    @property
    def pending_writes(self) -> tuple[tuple[str, str, Any], ...]:
        self.accessed.add("pending_writes")
        return self._pending_writes

    @property
    def scheduler(self) -> dict[str, Any]:
        self.accessed.add("scheduler")
        return self._scheduler


@dataclass
class StubCheckpointer:
    """**桩** checkpointer —— 记录调用 + 存**最小**载荷（FR-019）。

    * ``calls`` —— 记录被调用过的方法名（**顺序**保留）⇒ ⇒ 「恢复**确实**
      经由 checkpointer」**可判定**（SC-005）；
    * ``snapshots`` —— ``{thread_id: {"values": ..., "metadata": ...}}``；
    * ``pending`` —— ``{thread_id: [(task_id, channel, value), ...]}``。

    ⚠️ **同一任务 + 同一通道** ⇒ **覆盖**（上游 saver 的语义 · 实测：上游的
    ``InMemorySaver.put_writes`` 对**已知通道**用**固定索引**⇒ 覆盖）。
    """

    calls: list[str] = field(default_factory=list)
    snapshots: dict[str, dict[str, Any]] = field(default_factory=dict)
    pending: dict[str, list[tuple[str, str, Any]]] = field(default_factory=dict)
    #: 最近一次 ``get_tuple`` 返回值的**属性访问记录**（SC-005 的判据载体）。
    accessed: set[str] = field(default_factory=set)

    # ── 读侧（契约 §2）──────────────────────────────────────────────────

    def get_tuple(self, config: RunConfig) -> _CheckpointTuple | None:
        """取回**最新**快照（**查不到**该会话 ⇒ ``None``）。"""
        self.calls.append("get_tuple")
        thread_id = _thread_id(config)
        stored = self.snapshots.get(thread_id)
        if stored is None:
            return None
        metadata = dict(stored["metadata"])
        snapshot = StateSnapshot(
            values=dict(stored["values"]),
            next=tuple(metadata.get("next", ())),
            config=config,
            metadata=None,
            created_at=None,
            parent_config=None,
            tasks=tuple(metadata.get("tasks", ())),
            interrupts=tuple(metadata.get("interrupts", ())),
        )
        entry = _CheckpointTuple(
            snapshot=snapshot,
            pending_writes=tuple(self.pending.get(thread_id, ())),
            scheduler=dict(metadata.get("scheduler", {})),
        )
        self.accessed = entry.accessed
        return entry

    # ── 写侧（契约 §4）──────────────────────────────────────────────────

    def put(
        self,
        config: RunConfig,
        values: Any = None,
        metadata: Any = None,
        **kwargs: Any,
    ) -> None:
        """写入**快照**（``values`` + ``metadata``）。"""
        self.calls.append("put")
        thread_id = _thread_id(config)
        self.snapshots[thread_id] = {
            "values": dict(values or {}),
            "metadata": dict(metadata or {}),
        }

    def put_writes(
        self,
        config: RunConfig,
        writes: Any = None,
        task_id: Any = None,
        task_path: Any = None,
        **kwargs: Any,
    ) -> None:
        """写入**待写入数据**（同一任务 + 同一通道 ⇒ **覆盖**）。"""
        self.calls.append("put_writes")
        thread_id = _thread_id(config)
        bucket = self.pending.setdefault(thread_id, [])
        for channel, value in writes or ():
            for index, entry in enumerate(bucket):
                if entry[0] == task_id and entry[1] == channel:
                    bucket[index] = (task_id, channel, value)
                    break
            else:
                bucket.append((task_id, channel, value))


def _spec(nodes: dict[str, NodeSpec], edges: dict[str, tuple[str, ...]]) -> GraphSpec:
    """组装一张图规格（**入口哨兵** ``__start__`` 作为边源）。"""
    return GraphSpec(channels=dict(_CHANNELS), nodes=nodes, edges=edges)


def _ask_node(log: list[str] | None = None) -> NodeSpec:
    """一个调用 ``interrupt("approve?")`` 的节点。"""

    def _run(state: dict[str, Any]) -> dict[str, Any]:
        if log is not None:
            log.append("ask")
        answer = interrupt("approve?")
        return {"messages": [f"answer={answer}"]}

    return NodeSpec(subscribes=(), run=_run)


def test_the_resume_reads_snapshot_and_pending_writes() -> None:
    """**SC-005** / **A4①**：恢复时**确实**经由 checkpointer ⇒ ⇒ 桩记录到
    ``get_tuple`` 调用 ⇒ ⇒ 且返回值的 ``.snapshot`` / ``.pending_writes`` /
    ``.scheduler`` **三项均被读取**（**缺失即失败** ⇒ ⇒ 恢复**不**是内存态旁路）。"""
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-read")
    spec = _spec({"ask": _ask_node()}, {"__start__": ("ask",)})

    paused = run_graph(spec, checkpointer=stub, config=config)
    assert isinstance(paused, InterruptResult)

    from freegraph.contracts.types import Command

    run_graph(spec, Command(resume="yes"), checkpointer=stub, config=config)

    # ⇒ 恢复那一轮**确实**调了 ``get_tuple``（首次运行那一轮也会调 ——
    # 「会话连续」要**读**快照判定有无历史 ⇒ ⇒ 断言**次数** ≥ 1）
    assert stub.calls.count("get_tuple") >= 1
    # ⇒ 三项**均被读取** ⇒ ⇒ 恢复路径**不是**内存态旁路（FR-010）
    assert stub.accessed == {"snapshot", "pending_writes", "scheduler"}


def test_the_scheduler_ledger_survives_a_json_round_trip() -> None:
    """**SC-005** 的账本半边 · data-model **V-12**：``.scheduler`` 是
    **JSON 可序列化**的**纯数据** ⇒ ⇒ ``json.dumps`` → ``json.loads`` 往返
    ⇒ ⇒ 还原后的账本与原对象**逐字段相等**。"""
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-json")
    spec = _spec({"ask": _ask_node()}, {"__start__": ("ask",)})

    run_graph(spec, checkpointer=stub, config=config)

    entry = stub.get_tuple(config)
    assert entry is not None
    ledger = entry.scheduler
    round_tripped = json.loads(json.dumps(ledger))
    assert round_tripped == ledger

    from freegraph.runtime import SchedulerState

    restored = SchedulerState.from_checkpoint(round_tripped)
    original = SchedulerState.from_checkpoint(ledger)
    assert restored.versions_seen == original.versions_seen
    assert restored.channel_versions == original.channel_versions
    assert restored.node_versions == original.node_versions
    assert restored.dynamic_edges == original.dynamic_edges
    # ⚠️ ``step`` **不落盘** ⇒ ⇒ 还原后**重新计数**（契约 §3）
    assert restored.step == 0


def test_the_pause_writes_the_snapshot_and_the_interrupt_trace() -> None:
    """**SC-005** 的写侧半边 · FR-012：挂起时桩记录到**快照写入**（``put``）
    与**待写入写入**（``put_writes`` · 通道名 ``__interrupt__``）⇒ ⇒ 挂起态
    **可被再次恢复**（闭环**可重复** · SC-013）。"""
    stub = StubCheckpointer()
    config = RunConfig(thread_id="t-write")
    spec = _spec({"ask": _ask_node()}, {"__start__": ("ask",)})

    run_graph(spec, checkpointer=stub, config=config)

    assert "put" in stub.calls
    assert "put_writes" in stub.calls
    pending = stub.pending["t-write"]
    channels = {channel for _, channel, _ in pending}
    assert "__interrupt__" in channels


def test_no_resume_context_survives_across_runs() -> None:
    """**FR-010 的核心禁令**（**初版无直接断言**）：**跨运行** MUST NOT 持有
    「待恢复现场」⇒ ⇒ 第二次运行（**新会话 / 新 thread_id**）**读不到**第一次
    的中断现场 ⇒ ⇒ **不**消费上一次的 ``__resume__`` ⇒ ⇒ 且**内核内**不残留
    上一轮的任务现场。"""
    stub = StubCheckpointer()
    spec = _spec({"ask": _ask_node()}, {"__start__": ("ask",)})

    run_graph(spec, checkpointer=stub, config=RunConfig(thread_id="t-a"))
    run_graph(spec, checkpointer=stub, config=RunConfig(thread_id="t-b"))

    # ⇒ 两个会话的现场**互不干扰**（新会话读不到旧会话的中断）
    assert set(stub.pending) == {"t-a", "t-b"}
    for thread_id in ("t-a", "t-b"):
        channels = {channel for _, channel, _ in stub.pending[thread_id]}
        assert "__resume__" not in channels


def test_the_runtime_never_imports_a_saver_implementation() -> None:
    """**FR-019 / B14F1 R-2**：``runtime/**`` 内**零** saver 实现，且
    **MUST NOT** import ``freegraph.persistence``；``MemorySaver`` 归 L4
    ``freegraph.persistence.memory``。"""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    runtime_dir = repo_root / "src" / "freegraph" / "runtime"
    offenders = [
        path.name
        for path in sorted(runtime_dir.rglob("*.py"))
        if "class MemorySaver" in path.read_text(encoding="utf-8")
        or "class SqliteSaver" in path.read_text(encoding="utf-8")
        or "import freegraph.persistence" in path.read_text(encoding="utf-8")
        or "from freegraph.persistence" in path.read_text(encoding="utf-8")
    ]
    assert offenders == [], offenders

    memory_module = (
        repo_root / "src" / "freegraph" / "persistence" / "memory.py"
    )
    assert "class MemorySaver" in memory_module.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# B13F1 · 静态挂起 metadata / fanout 账本 / 完成快照
# ─────────────────────────────────────────────────────────────────────────────


def test_static_suspend_metadata_has_kind_ack_and_scheduler_mirror() -> None:
    """**F-9**：静态挂起的 metadata 只增 ``suspension_kind`` / ``static_ack``，
    且二者镜像进 ``scheduler`` 子字典。"""
    from freegraph.runtime.superstep import _suspend_metadata

    ack = {"channel_versions": {"count": 1}}
    metadata = _suspend_metadata(
        ("review",),
        (),
        {"next": ("review",), "interrupts": (), "tasks": (), "scheduler": {}},
        suspension_kind="static_before",
        static_ack=ack,
    )
    assert metadata["suspension_kind"] == "static_before"
    assert metadata["static_ack"] == ack
    assert metadata["next"] == ("review",)
    assert metadata["interrupts"] == ()


def test_fanout_ledger_survives_json_round_trip() -> None:
    """**F-3**：``to_checkpoint`` 的 ``fanout`` 键可 JSON 往返，缺键宽容。"""
    from freegraph.contracts import Send
    from freegraph.runtime import SchedulerState
    from freegraph.runtime._fanout import _FanOut, make_fanout

    tasks = make_fanout(
        "fan",
        [Send("worker", {"n": 1}), Send("worker", {"n": 2})],
        {"worker"},
        suppresses_static=False,
    )
    state = SchedulerState(
        fanout={0: _FanOut(producer="fan", tasks=tasks, suppresses_static=False)}
    )
    ledger = state.to_checkpoint()
    assert ledger["fanout"]["0"]["producer"] == "fan"
    assert [t["arg"] for t in ledger["fanout"]["0"]["tasks"]] == [{"n": 1}, {"n": 2}]

    round_tripped = json.loads(json.dumps(ledger))
    restored = SchedulerState.from_checkpoint(round_tripped)
    assert sorted(restored.fanout) == [0]
    assert [task.arg for task in restored.fanout[0].tasks] == [{"n": 1}, {"n": 2}]


def test_from_checkpoint_without_fanout_is_tolerant() -> None:
    from freegraph.runtime import SchedulerState

    restored = SchedulerState.from_checkpoint({})
    assert restored.fanout == {}


def test_decode_fanout_is_defensive_on_malformed_payloads() -> None:
    from freegraph.runtime._fanout import decode_fanout

    restored = decode_fanout(
        {
            "bad": "not-a-mapping",
            "x": {"producer": "fan", "tasks": [{"target": "w"}]},
            "0": {
                "producer": "fan",
                "tasks": [
                    "not-a-mapping",
                    {"target": 1},
                    {"target": "w", "arg": {"n": 1}},
                ],
            },
        }
    )
    assert "bad" not in restored
    assert "x" in restored
    assert [task.target for task in restored[0].tasks] == ["w"]
