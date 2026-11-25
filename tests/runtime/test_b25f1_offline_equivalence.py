# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B25F1 · 进程内断网等价性（核心用例全绿）。

* 在进程内禁用 ``socket.socket.connect`` / ``socket.create_connection``（抛异常）；
* 以同进程 ``runpy.run_path`` 执行四个零依赖验收脚本 + fake 轮；
* fake 轮缺 `langchain` / `IPython` 时**仅该项 skip**（其余四组仍执行）；
* OS 级 G28 是条件增强，不替代本进程内层。
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import runpy
import socket
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
_HARNESS = _REPO_ROOT / "harness"
_B25F1 = _HARNESS / "verification" / "B25F1"

for _path in (_SRC, _B25F1):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

_ZERO_DEPENDENCY_SCRIPTS = (
    _HARNESS / "demo" / "graph_core.py",
    _HARNESS / "demo" / "agent_loop.py",
    _HARNESS / "demo" / "visualization.py",
    _HARNESS / "demo" / "diagnostics.py",
)


def _run_script(path: Path) -> tuple[int, str]:
    buffer = io.StringIO()
    original_argv = sys.argv
    sys.argv = [str(path)]
    try:
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            try:
                runpy.run_path(str(path), run_name="__main__")
            except SystemExit as exc:
                code = int(exc.code or 0) if isinstance(exc.code, int) else 1
                return code, buffer.getvalue()
            except Exception as exc:  # noqa: BLE001
                return 1, buffer.getvalue() + f"\n{type(exc).__name__}: {exc}"
    finally:
        sys.argv = original_argv
    return 0, buffer.getvalue()


def _fake_round_ready() -> bool:
    return (
        importlib.util.find_spec("langchain") is not None
        and importlib.util.find_spec("IPython") is not None
    )


def test_process_internal_offline_core_cases(monkeypatch: pytest.MonkeyPatch) -> None:
    def _offline(*args: object, **kwargs: object) -> object:
        raise OSError("offline: socket disabled by B25F1 offline equivalence")

    monkeypatch.setattr(socket.socket, "connect", _offline)
    monkeypatch.setattr(socket, "create_connection", _offline)

    for script in _ZERO_DEPENDENCY_SCRIPTS:
        assert script.is_file(), script
        code, output = _run_script(script)
        assert code == 0, f"{script.name} 在断网下退出码非 0\n{output}"

    if not _fake_round_ready():
        # fake 轮项 skip（其余四组已执行）；不把整个测试标成 skip。
        return
    code, output = _run_script(_B25F1 / "fake_round.py")
    assert code == 0, f"fake_round.py 在断网下退出码非 0\n{output}"
