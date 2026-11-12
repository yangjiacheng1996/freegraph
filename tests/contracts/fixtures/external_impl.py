# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**外部实现夹具** —— 零内部依赖的可插拔能力实现样本。

本文件只允许 ``from freegraph.contracts import ...`` 与标准库 import
——架构门禁 **G2** 的「内部 import 档」扫 ``tests/contracts/**``（含本目录），
「第三方 import 档」扫本目录 ⇒ 夹具若引入 LangChain 家族或任何第三方包即报错。

存在的意义：让「协议可被外部实现」这条判据**可被静态扫描判定**，
而不是靠人读代码（research D-20）。

**全部方法 MUST 写全类型注解**——``mypy --strict`` 的
``disallow_untyped_defs`` 会把漏注解直接判错（SC-004）。
**参数名 MUST 与协议逐字相同**；**未冻结部分**（返回类型 / 载荷 / 命名空间载体）
用 ``Any`` 占位，与协议侧保持一致。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from freegraph.contracts import Checkpointer, RunConfig, Span, Store, TraceSink


class InMemoryCheckpointer:
    """假 **Checkpointer** —— 内存字典存储 + 版本号自增。

    **不继承任何 freegraph 基类**——只靠「结构化子类型」满足协议，
    这正是「协议可被外部实现」的证明。
    """

    def __init__(self) -> None:
        """初始化内存存储。"""
        self._snapshots: dict[str, dict[str, Any]] = {}
        self._writes: dict[str, list[Any]] = {}
        self._versions: dict[str, int] = {}

    def get_tuple(self, config: RunConfig) -> Any:
        """取回**最新**快照。"""
        thread_id = config.thread_id or ""
        return self._snapshots.get(thread_id)

    def list(self, config: RunConfig, *args: Any, **kwargs: Any) -> Any:
        """列举**历史**快照。"""
        thread_id = config.thread_id or ""
        return list(self._snapshots.get(thread_id, {}))

    def put(self, config: RunConfig, *args: Any, **kwargs: Any) -> Any:
        """写入一个**快照**。"""
        thread_id = config.thread_id or ""
        payload = args[0] if args else kwargs.get("checkpoint")
        self._snapshots.setdefault(thread_id, {})["latest"] = payload
        return None

    def put_writes(self, config: RunConfig, *args: Any, **kwargs: Any) -> Any:
        """写入**待写入数据**（pending writes）。"""
        thread_id = config.thread_id or ""
        payload = args[0] if args else kwargs.get("writes")
        self._writes.setdefault(thread_id, []).append(payload)
        return None

    def delete_thread(self, thread_id: str) -> Any:
        """删除某**会话**的全部快照与写入。"""
        self._snapshots.pop(thread_id, None)
        self._writes.pop(thread_id, None)
        self._versions.pop(thread_id, None)
        return None


    def delete_for_runs(self, run_ids: Sequence[str]) -> Any:
        """删除若干**运行**的数据（**上游同款** · 上游
        ``langgraph/checkpoint/base/__init__.py:331``）。"""
        for run_id in run_ids:
            self._runs.pop(run_id, None)

    def copy_thread(self, source_thread_id: str, target_thread_id: str) -> Any:
        """复制一个**会话**的数据（**上游同款** · 上游
        ``langgraph/checkpoint/base/__init__.py:350``）。"""
        self._threads[target_thread_id] = dict(self._threads.get(source_thread_id, {}))
    def get_next_version(self, *args: Any, **kwargs: Any) -> Any:
        """生成**下一个版本号**（单调递增）。"""
        thread_id = kwargs.get("thread_id") or (args[0] if args else "")
        if thread_id is None:
            thread_id = ""
        next_version = self._versions.get(thread_id, 0) + 1
        self._versions[thread_id] = next_version
        return str(next_version)


class InMemoryStore:
    """假 **Store** —— 内存命名空间 + 键值存储。

    **不继承任何 freegraph 基类**——只靠「结构化子类型」满足协议。
    """

    def __init__(self) -> None:
        """初始化内存存储。"""
        self._data: dict[tuple[str, ...], dict[str, Any]] = {}

    @staticmethod
    def _as_path(namespace: Any) -> tuple[str, ...]:
        """把命名空间**载体**归一为**层级路径**元组。"""
        if namespace is None:
            return ()
        if isinstance(namespace, str):
            return tuple(part for part in namespace.split(".") if part)
        return tuple(str(part) for part in namespace)

    def get(self, namespace: tuple[str, ...], key: str) -> Any:
        """按 **(命名空间, 键)** 取一项。"""
        return self._data.get(self._as_path(namespace), {}).get(key)

    def search(
        self, namespace_prefix: tuple[str, ...], *args: Any, **kwargs: Any
    ) -> Any:
        """在命名空间**前缀**下检索多项。"""
        prefix = self._as_path(namespace_prefix)
        hits: list[dict[str, Any]] = []
        for path, bucket in self._data.items():
            if path[: len(prefix)] == prefix:
                hits.append({"namespace": path, "items": dict(bucket)})
        return hits

    def put(self, namespace: tuple[str, ...], key: str, value: Any) -> Any:
        """写入一项。"""
        self._data.setdefault(self._as_path(namespace), {})[key] = value
        return None

    def delete(self, namespace: tuple[str, ...], key: str) -> Any:
        """删除一项。"""
        bucket = self._data.get(self._as_path(namespace))
        if bucket is not None:
            bucket.pop(key, None)
        return None

    def list_namespaces(
        self, *, prefix: tuple[str, ...] | None = None, **kwargs: Any
    ) -> Any:
        """列出命名空间（层级路径）。"""
        prefix_path = self._as_path(prefix)
        return [
            path
            for path in self._data
            if path[: len(prefix_path)] == prefix_path
        ]

    def batch(self, ops: Any, *args: Any, **kwargs: Any) -> Any:
        """**批量**执行多个操作。"""
        results: list[Any] = []
        for op in ops or []:
            results.append(op)
        return results


class RecordingTraceSink:
    """假 **TraceSink** —— 记录 ``on_span_start`` / ``on_span_end`` 的调用序列。

    **不继承任何 freegraph 基类**——只靠「结构化子类型」满足协议。
    """

    def __init__(self) -> None:
        """初始化调用记录。"""
        self.started: list[str] = []
        self.ended: list[str] = []
        self.end_times: list[str | None] = []
        self.spans: list[Span] = []

    def on_span_start(self, span: Span) -> None:
        """记录一次 span **开始**。"""
        self.started.append(span.id)
        self.spans.append(span)

    def on_span_end(self, span: Span) -> None:
        """记录一次 span **结束**。"""
        self.ended.append(span.id)
        self.end_times.append(span.end_time)
        self.spans.append(span)

    def current_span(self) -> Span | None:
        """返回**当前** span；本夹具恒无当前 span ⇒ 返回**空值**（不抛异常）。"""
        return None


def make_partial_checkpointer(missing: str) -> Any:
    """造一个**缺 ``missing`` 方法**的 checkpointer 实例（用于判假用例）。

    缺方法变体的「存在性」本身即判定依据——``isinstance`` MUST 判**假**。
    """
    namespace: dict[str, Any] = {}
    for name in (
        "get_tuple",
        "list",
        "put",
        "put_writes",
        "delete_thread",
        "get_next_version",
    ):
        if name == missing:
            continue
        namespace[name] = lambda self, *args, **kwargs: None
    return type("PartialCheckpointer", (), namespace)()


def make_partial_store(missing: str) -> Any:
    """造一个**缺 ``missing`` 方法**的 store 实例（用于判假用例）。"""
    namespace: dict[str, Any] = {}
    for name in (
        "get",
        "search",
        "put",
        "delete",
        "list_namespaces",
        "batch",
    ):
        if name == missing:
            continue
        namespace[name] = lambda self, *args, **kwargs: None
    return type("PartialStore", (), namespace)()


def make_partial_trace_sink(missing: str) -> Any:
    """造一个**缺 ``missing`` 方法**的 trace sink 实例（用于判假用例）。"""
    namespace: dict[str, Any] = {}
    for name in ("on_span_start", "on_span_end", "current_span"):
        if name == missing:
            continue
        namespace[name] = lambda self, *args, **kwargs: None
    return type("PartialTraceSink", (), namespace)()


# ── 协议一致性断言（SC-004 · 「证明协议确实可被外部实现」）─────────────


def _takes_checkpointer(value: Checkpointer) -> None:
    """形参标注为**协议类型** ⇒ mypy 静态校验调用点传入的实现确实满足协议。"""


def _takes_trace_sink(value: TraceSink) -> None:
    """形参标注为**协议类型** ⇒ mypy 静态校验调用点传入的实现确实满足协议。"""


def _takes_store(value: Store) -> None:
    """形参标注为**协议类型** ⇒ mypy 静态校验调用点传入的实现确实满足协议。"""


def prove_protocol_conformance(
    checkpointer: Checkpointer, sink: TraceSink, store: Store
) -> None:
    """把三个实现**传给协议类型的形参**——静态验证它们确实满足协议。

    **仅编译夹具文件不构成「协议可被外部实现」的证明**——本函数就是那道
    一致性断言的落点（``mypy --strict`` 会在这里静态校验三者的可赋值性）。
    """
    _takes_checkpointer(checkpointer)
    _takes_trace_sink(sink)
    _takes_store(store)


def prove_conformance_with_concrete_implementations() -> None:
    """用**具体实现类**调用一致性断言——``mypy`` 在此处静态校验三者满足协议。"""
    prove_protocol_conformance(
        InMemoryCheckpointer(), RecordingTraceSink(), InMemoryStore()
    )
