# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B15F1 · ``SqliteSaver`` 同实例多线程并发（Windows 必跑 · 不带 linux_only 标记）。"""

from __future__ import annotations

import sqlite3
import threading

from freegraph.contracts import RunConfig
from freegraph.persistence import SqliteSaver


def _metadata():
    return {"next": (), "interrupts": (), "tasks": (), "scheduler": {"fanout": {}}}


def test_same_instance_multi_thread_writes_are_serialized() -> None:
    saver = SqliteSaver(sqlite3.connect(":memory:", check_same_thread=False))
    errors: list[BaseException] = []
    per_thread = 5
    thread_count = 8

    def worker(worker_id: int) -> None:
        try:
            for i in range(per_thread):
                cfg = saver.put(
                    RunConfig(thread_id="shared"),
                    values={"worker": worker_id, "i": i},
                    metadata=_metadata(),
                )
                saver.put_writes(cfg, writes=[("w", i)], task_id=f"task{worker_id}")
        except BaseException as exc:  # pragma: no cover - 失败路径
            errors.append(exc)

    threads = [
        threading.Thread(target=worker, args=(worker_id,))
        for worker_id in range(thread_count)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors, errors
    ids = [
        item.snapshot.config.configurable["checkpoint_id"]
        for item in saver.list(RunConfig(thread_id="shared"))
    ]
    assert len(ids) == thread_count * per_thread
    assert len(set(ids)) == len(ids)
    assert ids == sorted(ids, reverse=True)
    # no leaked "database is locked" in captured errors
    assert not any("database is locked" in str(exc) for exc in errors)


def test_two_instances_different_threads_do_not_corrupt(tmp_path) -> None:
    path = str(tmp_path / "concurrent.db")
    with SqliteSaver.from_conn_string(path) as s1, SqliteSaver.from_conn_string(path) as s2:
        for i in range(5):
            s1.put(RunConfig(thread_id="t1"), values={"i": i}, metadata=_metadata())
            s2.put(RunConfig(thread_id="t2"), values={"i": i}, metadata=_metadata())
    with SqliteSaver.from_conn_string(path) as s3:
        assert len(list(s3.list(RunConfig(thread_id="t1")))) == 5
        assert len(list(s3.list(RunConfig(thread_id="t2")))) == 5
