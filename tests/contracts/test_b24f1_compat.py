# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B24F1 · US4 COMPAT.md 覆盖 / 关键措辞 / Store baseline（FR-004 / FR-012 / FR-015 / SC-004）。"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

_FACADE_DIR = Path(__file__).resolve().parents[1] / "facade"
if str(_FACADE_DIR) not in sys.path:
    sys.path.insert(0, str(_FACADE_DIR))

import _gatesupport  # noqa: E402


def _compat(repo_root: Path) -> str:
    return (repo_root / "COMPAT.md").read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    match = re.search(rf"^{re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.S | re.M)
    assert match, f"缺少章节 {heading}"
    return match.group(1)


def _table_rows(section: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if re.fullmatch(r"\|[\s\-|:]+\|", stripped):
            continue
        cells = [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", stripped.strip("|"))]
        if cells and cells[0] in {"#", "freegraph 符号", "行"}:
            continue
        rows.append(cells)
    return rows


def test_machine_section_is_exactly_two_layers(repo_root: Path) -> None:
    rows = _gatesupport.compat_matrix_rows(_compat(repo_root))
    assert len(rows) == 27
    assert all(len(cells) == 4 for _, cells in rows)
    names = [name for name, _ in rows]
    assert len(names) == len(set(names))


def test_18_items_are_complete(repo_root: Path) -> None:
    section = _section(_compat(repo_root), "## 18 项覆盖表")
    rows = _table_rows(section)
    assert len(rows) == 18
    assert [row[0] for row in rows] == [str(i) for i in range(1, 19)]
    assert all(len(row) == 6 and row[5] for row in rows)
    assert "多源汇合边" in rows[3][3]
    assert "B7F4" in rows[3][5]


def test_downstream_rows_are_complete(repo_root: Path) -> None:
    section = _section(_compat(repo_root), "## 下游承接行")
    rows = _table_rows(section)
    symbols = [row[0] for row in rows]
    expected = [
        "多源汇合边",
        "MemorySaver",
        "InMemorySaver",
        "CheckpointTuple",
        "SqliteSaver",
        "CompiledGraph.get_state",
        "CompiledGraph.get_state_history",
        "CompiledGraph.update_state",
        "时间旅行",
        "OtlpExporter",
    ]
    for needle in expected:
        assert any(needle in symbol for symbol in symbols), needle
    assert len(rows) == 10
    for symbol, degree in (
        ("SqliteSaver", "部分等价"),
        ("CompiledGraph.get_state", "部分等价"),
        ("CompiledGraph.get_state_history", "行为等价"),
        ("CompiledGraph.update_state", "部分等价"),
    ):
        row = next(row for row in rows if symbol in row[0])
        assert degree in row[1], (symbol, row)
    get_state = next(row for row in rows if "CompiledGraph.get_state" in row[0])
    assert "Y-02" in get_state[1]


def test_command_and_related_rows(repo_root: Path) -> None:
    rows = dict(_gatesupport.compat_matrix_rows(_compat(repo_root)))
    command = rows["Command"]
    assert command[2] == "部分等价"
    diff = command[3]
    for needle in ("Y-01", "DIFF", "X-06", "STRICTER", "X-2", "X-3", "P3", "99d43aa"):
        assert needle in diff, needle
    assert "更严" in diff  # 说明 goto 缺省不属「更严」

    node_func = rows["NodeFunc"]
    assert node_func[2] == "不支持"
    for needle in ("命令列表", "Send", "list[Send]", "tuple[Send, ...]", "无上游同名协议"):
        assert needle in node_func[3], needle

    send = rows["Send"]
    for needle in ("fan-out", "运行期语义已落地", "不可变", "Y-03", "L1"):
        assert needle in send[3], needle

    state_graph = rows["StateGraph"]
    for needle in ("interrupt_before", "interrupt_after", "recursion_limit"):
        assert needle in state_graph[3], needle

    graph = rows["Graph"]
    assert "占位 PNG" in graph[3]
    assert "[png]" in graph[3]

    compiled = rows["CompiledGraph"]
    for needle in ("Y-02", "None", "StateSnapshot", "v1 能力边界", "update_state"):
        assert needle in compiled[3], needle


def test_evidence_section_is_traceable(repo_root: Path) -> None:
    text = _compat(repo_root)
    evidence = _section(text, "## 证据与来源")
    for needle in (
        "Store",
        "协议等价",
        "v1 无实现",
        "tests/differential/test_differential.py",
        "tests/differential/test_b15f1_state_parity.py",
        "tests/differential/test_b16f1_time_travel_parity.py",
        "tests/differential/test_b24f1_matrix_parity.py",
    ):
        assert needle in evidence, needle


def test_store_machine_row_matches_baseline(repo_root: Path) -> None:
    current = dict(_gatesupport.compat_matrix_rows(_compat(repo_root))).get("Store")
    assert current is not None
    previous = None
    for ref in ("HEAD:COMPAT.md", "HEAD:README.md"):
        proc = subprocess.run(
            ["git", "show", ref],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            continue
        try:
            rows = dict(_gatesupport.compat_matrix_rows(proc.stdout))
        except AssertionError:
            continue
        if "Store" in rows:
            previous = rows["Store"]
            break
    if previous is None:
        pytest.skip("无 baseline 可取——Store 逐字不变判据不可执行")
    assert current == previous, "Store 机读行 MUST 逐字保持既有"
