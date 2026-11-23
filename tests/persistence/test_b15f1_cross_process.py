# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B15F1 · 跨进程持久化（新 Python 子进程读取同一数据库文件）。"""

from __future__ import annotations

import json
import subprocess
import sys

from freegraph.contracts import RunConfig
from freegraph.persistence import SqliteSaver


def test_new_process_reads_same_database(tmp_path) -> None:
    path = str(tmp_path / "cross.db")
    with SqliteSaver.from_conn_string(path) as saver:
        saver.put(
            RunConfig(thread_id="t"),
            values={"n": 7, "items": [1, 2]},
            metadata={
                "next": (),
                "interrupts": (),
                "tasks": (),
                "scheduler": {"fanout": {}},
            },
        )

    script = """
import json
from freegraph.contracts import RunConfig
from freegraph.persistence import SqliteSaver

with SqliteSaver.from_conn_string(%r) as saver:
    t = saver.get_tuple(RunConfig(thread_id="t"))
    snap = t.snapshot
    print(json.dumps({
        "values": snap.values,
        "next": list(snap.next),
        "checkpoint_id": snap.config.configurable["checkpoint_id"],
    }))
""" % path
    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    assert payload == {
        "values": {"n": 7, "items": [1, 2]},
        "next": [],
        "checkpoint_id": f"{1:032d}",
    }
