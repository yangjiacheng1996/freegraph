#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B25F1 · fake 轮（A1）：原样执行 `harness/demo/target.py`。

两种注入路径，**都不修改固定脚本**：

* 默认（同进程）：先猴补 `langchain.chat_models.init_chat_model`，再
  `runpy.run_path(target.py)`；
* `--subprocess`：生成临时 `sitecustomize.py`，通过 `PYTHONPATH` 在子进程启动期
  完成注入（证明「不改进程也能注入」）。

断言（立项书 §9.2 / spec FR-003）：

* `messages` 长度 == 4（Human + AI(tool_call) + ToolMessage + AI final）；
* `llm_calls` == 2；
* 工具结果归一为 ``7``；
* `invoke()` 返回完整状态（含 `messages` 与 `llm_calls` 两个键）；
* `draw_mermaid_png()` 产出合法 PNG（签名 + IHDR + IEND）；
* 框架出站 == 0；用户出站逐条记录、不判失败。

退出码：0 = PASS · 1 = 断言失败 · 2 = 环境未就绪。
最后一行 MUST 打印 ``B25F1 fake round: PASS|FAIL``。
"""

from __future__ import annotations

import argparse
import json
import os
import runpy
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
B25F1_DIR = Path(__file__).resolve().parent
GATES_DIR = REPO_ROOT / "harness" / "scripts" / "gates"
TARGET = REPO_ROOT / "harness" / "demo" / "target.py"

for _path in (SRC_DIR, B25F1_DIR, GATES_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _png_ok(data: Any) -> bool:
    if not isinstance(data, (bytes, bytearray)) or not data.startswith(PNG_SIGNATURE):
        return False
    if len(data) < 8 + 12 + 13 + 12:
        return False
    length = struct.unpack(">I", bytes(data[8:12]))[0]
    if data[12:16] != b"IHDR" or length != 13:
        return False
    return data.rfind(b"IEND") >= 0


def _message_view(messages: list[Any]) -> list[dict[str, Any]]:
    view: list[dict[str, Any]] = []
    for message in messages:
        view.append(
            {
                "cls": type(message).__name__,
                "content": getattr(message, "content", None),
                "tool_calls": list(getattr(message, "tool_calls", []) or []),
                "tool_call_id": getattr(message, "tool_call_id", None),
            }
        )
    return view


def _validate(payload: dict[str, Any], png: bytes | None, egress: list[dict[str, str]]) -> list[str]:
    failures: list[str] = []
    messages = payload.get("messages") or []
    if payload.get("type") != "dict":
        failures.append(f"invoke() 返回类型不是 dict：{payload.get('type')!r}")
    if not {"messages", "llm_calls"}.issubset(set(payload.get("keys") or [])):
        failures.append(f"完整状态缺键：{payload.get('keys')!r}")
    if len(messages) != 4:
        failures.append(f"messages 长度 != 4（实际 {len(messages)}）")
    if payload.get("llm_calls") != 2:
        failures.append(f"llm_calls != 2（实际 {payload.get('llm_calls')!r}）")

    tool_contents = [m["content"] for m in messages if m["cls"] == "ToolMessage"]
    if not tool_contents:
        failures.append("缺 ToolMessage")
    else:
        try:
            if int(tool_contents[0]) != 7:
                failures.append(f"工具结果 != 7（实际 {tool_contents[0]!r}）")
        except (TypeError, ValueError):
            failures.append(f"工具结果不可归一为 int：{tool_contents[0]!r}")

    first_ai = next((m for m in messages if m["cls"] == "AIMessage"), None)
    if first_ai is None or not first_ai["tool_calls"]:
        failures.append("第 1 轮 AIMessage 缺 tool_calls")
    else:
        if first_ai["tool_calls"][0].get("id") != "call_1":
            failures.append(f"tool_call.id != 'call_1'：{first_ai['tool_calls'][0]!r}")
    tool = next((m for m in messages if m["cls"] == "ToolMessage"), None)
    if tool is not None and tool.get("tool_call_id") != "call_1":
        failures.append(f"ToolMessage.tool_call_id != 'call_1'：{tool.get('tool_call_id')!r}")

    if not _png_ok(png):
        failures.append("draw_mermaid_png() 未产出合法 PNG")

    framework = [item for item in egress if item.get("attribution") == "framework"]
    if framework:
        failures.append(f"框架出站 != 0（{len(framework)} 条）")
    return failures


def _run_same_process() -> tuple[int, list[str]]:
    try:
        import fake_model  # noqa: WPS433 - 测试侧动态导入
        import _gatekit
        import IPython.display as ipython_display
        import langchain.chat_models as chat_models
    except ImportError as exc:
        print(f"[环境未就绪] 缺少 fake 轮依赖：{exc}")
        return 2, [f"环境未就绪：{exc}"]

    original_init = getattr(chat_models, "init_chat_model", None)
    original_display = ipython_display.display
    png: list[bytes] = []

    def _capture_display(value: Any) -> None:
        data = getattr(value, "data", None)
        if data is not None:
            png.append(bytes(data))

    fake = fake_model.install()
    ipython_display.display = _capture_display  # type: ignore[assignment]
    records: list[_gatekit.EgressRecord] = []
    try:
        with _gatekit.record_egress(records):
            namespace = runpy.run_path(str(TARGET), run_name="__main__")
    finally:
        ipython_display.display = original_display  # type: ignore[assignment]
        if original_init is not None:
            chat_models.init_chat_model = original_init  # type: ignore[attr-defined]

    state = namespace.get("messages")
    if not isinstance(state, dict):
        return 1, [f"target.py 未产出完整状态（messages = {type(state).__name__}）"]
    payload = {
        "type": "dict",
        "keys": sorted(state),
        "llm_calls": state.get("llm_calls"),
        "messages": _message_view(list(state.get("messages") or [])),
        "fake_calls": fake.calls,
    }
    egress = [
        {"target": record.target, "attribution": record.attribution}
        for record in records
    ]
    failures = _validate(payload, png[-1] if png else None, egress)
    if fake.calls != 2:
        failures.append(f"fake 模型调用次数 != 2（实际 {fake.calls}）")

    print(f"[fake] 模型调用次数 = {fake.calls}")
    print(f"[fake] messages 长度 = {len(payload['messages'])}")
    print(f"[fake] llm_calls = {payload['llm_calls']}")
    print(f"[fake] PNG 字节数 = {len(png[-1]) if png else 0}")
    print(f"[fake] 框架出站 = {sum(1 for e in egress if e['attribution'] == 'framework')}")
    print(f"[fake] 用户出站 = {sum(1 for e in egress if e['attribution'] == 'user')}（记录在案，不判失败）")
    return (0 if not failures else 1), failures


_SITECUSTOMIZE = r'''
import atexit
import json
import os
import sys

sys.path.insert(0, os.environ["B25F1_GATES_DIR"])
sys.path.insert(0, os.environ["B25F1_DIR"])

import fake_model
import _gatekit

fake_model.install()

from IPython.display import display as _unused_display  # noqa: F401
import IPython.display as _ipython_display


def _capture_display(value):
    data = getattr(value, "data", None)
    if data is not None:
        with open(os.environ["B25F1_PNG_PATH"], "wb") as handle:
            handle.write(bytes(data))


_ipython_display.display = _capture_display

_records = []
_cm = _gatekit.record_egress(_records)
_cm.__enter__()


def _dump():
    _cm.__exit__(None, None, None)
    payload = [
        {"target": record.target, "attribution": record.attribution}
        for record in _records
    ]
    with open(os.environ["B25F1_EGRESS_PATH"], "w", encoding="utf-8") as handle:
        json.dump(payload, handle)


atexit.register(_dump)
'''

_RUNNER = r'''
import json
import os
import runpy

namespace = runpy.run_path(os.environ["B25F1_TARGET"], run_name="__main__")
state = namespace["messages"]
messages = []
for message in state["messages"]:
    messages.append(
        {
            "cls": type(message).__name__,
            "content": getattr(message, "content", None),
            "tool_calls": list(getattr(message, "tool_calls", []) or []),
            "tool_call_id": getattr(message, "tool_call_id", None),
        }
    )
payload = {
    "type": type(state).__name__,
    "keys": sorted(state),
    "llm_calls": state.get("llm_calls"),
    "messages": messages,
}
with open(os.environ["B25F1_STATE_PATH"], "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
'''


def _run_subprocess() -> tuple[int, list[str]]:
    if not TARGET.is_file():
        return 2, [f"找不到固定脚本：{TARGET}"]

    with tempfile.TemporaryDirectory() as raw:
        temp = Path(raw)
        (temp / "sitecustomize.py").write_text(_SITECUSTOMIZE, encoding="utf-8")
        (temp / "runner.py").write_text(_RUNNER, encoding="utf-8")
        png_path = temp / "png.bin"
        state_path = temp / "state.json"
        egress_path = temp / "egress.json"
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("LANGSMITH_")
        }
        env.update(
            {
                "PYTHONPATH": os.pathsep.join(
                    [str(temp), str(B25F1_DIR), str(SRC_DIR)]
                    + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
                ),
                "PYTHONUTF8": "1",
                "PYTHONIOENCODING": "utf-8",
                "B25F1_DIR": str(B25F1_DIR),
                "B25F1_GATES_DIR": str(GATES_DIR),
                "B25F1_TARGET": str(TARGET),
                "B25F1_PNG_PATH": str(png_path),
                "B25F1_STATE_PATH": str(state_path),
                "B25F1_EGRESS_PATH": str(egress_path),
            }
        )
        proc = subprocess.run(
            [sys.executable, str(temp / "runner.py")],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            return 1, [f"子进程退出码 {proc.returncode}"]
        if not state_path.is_file():
            return 1, ["子进程未写出状态证据"]
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        png = png_path.read_bytes() if png_path.is_file() else None
        egress = (
            json.loads(egress_path.read_text(encoding="utf-8"))
            if egress_path.is_file()
            else []
        )
        failures = _validate(payload, png, egress)
        print(f"[subprocess] messages 长度 = {len(payload['messages'])}")
        print(f"[subprocess] llm_calls = {payload['llm_calls']}")
        print(f"[subprocess] PNG 字节数 = {len(png) if png else 0}")
        print(
            "[subprocess] 框架出站 = "
            f"{sum(1 for e in egress if e['attribution'] == 'framework')}"
        )
        print(
            "[subprocess] 用户出站 = "
            f"{sum(1 for e in egress if e['attribution'] == 'user')}（记录在案，不判失败）"
        )
        return (0 if not failures else 1), failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B25F1 fake 轮（A1）")
    parser.add_argument(
        "--subprocess",
        action="store_true",
        help="通过临时 sitecustomize.py 在子进程启动期注入 fake 模型",
    )
    args = parser.parse_args(argv)

    try:
        if args.subprocess:
            code, failures = _run_subprocess()
        else:
            code, failures = _run_same_process()
    except Exception as exc:  # noqa: BLE001 - 验收脚本：显式失败
        print(f"[FAIL] {type(exc).__name__}: {exc}")
        code, failures = 1, [f"{type(exc).__name__}: {exc}"]

    if code == 2:
        print("B25F1 fake round: FAIL (environment not ready)")
        return 2
    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        print("B25F1 fake round: FAIL")
        return 1
    print("B25F1 fake round: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
