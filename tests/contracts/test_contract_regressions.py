# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""契约层**独立回归测试**的**挂载点**（**C4** / **C8**）—— B3F1 只落挂载点。

宪法「质量门禁第 3 项」要求：契约门禁 **MUST 包含 C4（稀疏状态读）与 C8
（条件边 fresh 状态读）两条独立回归测试**。

**C4 的状态（2026-11-10 · B5F2 落地）**：

* C4 的**独立回归测试已存在且常驻 CI** ⇒ 挂载点 ``status`` 由 ``not-landed``
  翻为 ``landed``（**不伪装成「已通过」** —— 落地的是**读取层口径**，
  **节点边界**（真实节点收到的那个 dict）由 **B7F1** 承接）；
* ⚠️ **断言本体不住在本文件** —— 门禁 **G2** 的内部 import 档扫描
  ``tests/contracts/**`` ⇒ 那里**禁止** import ``freegraph.*``
  ⇒ C4 的断言住在 ``tests/runtime/test_read_c4_sparse_state.py``
  ⇒ 本文件只留**标记 + 元测试**（**只做路径扫描** · **零** ``freegraph.*`` import）。

**C8 的状态**：**未落地** ⇒ 挂载点仍为 ``not-landed`` · 承接方 = **B8F1**（M2）
⇒ 本 feature **MUST NOT** 改动该行。

**机器可读标记**（门禁 **G29** ③ 逐条解析）::

    # GATE-MOUNT: <编号> · status=<not-landed|landed> · owner=<承接方> · milestone=<里程碑> · desc=<说明>

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

import pytest

# GATE-MOUNT: C4 · status=landed · owner=B5F2 · milestone=M1 · desc=稀疏状态读
# GATE-MOUNT: C8 · status=not-landed · owner=B8F1 · milestone=M2 · desc=条件边 fresh 状态读

#: 两条回归测试的编号（与宪法质量门禁第 3 项一致）。
CONTRACT_REGRESSIONS = ("C4", "C8")

#: 仓库根目录（路径扫描的定位基准）。
REPO_ROOT = Path(__file__).resolve().parents[2]

#: **C4 独立回归测试**的落点（**断言本体**住这里 —— 门禁 G2 禁止
#: ``tests/contracts/**`` import ``freegraph.*``）。
C4_REGRESSION_RELPATH = "tests/runtime/test_read_c4_sparse_state.py"


def test_c4_sparse_state_read() -> None:
    """**C4** · 稀疏状态读 —— 节点输入**不含**未被写入的 key。

    断言目标形态：``"llm_calls" not in node_input`` 且
    ``node_input.get("llm_calls", 0) == 0``（**否定式** · 验收判据 **A1 / A2**）。

    ⚠️ **本测试是**元测试 —— 只做**路径扫描**，断言 C4 的独立回归测试
    **在位**且**被 pytest 收集**；**MUST NOT** import ``freegraph.*``
    （门禁 **G2** 扫描 ``tests/contracts/**``）。
    """
    regression = REPO_ROOT / C4_REGRESSION_RELPATH
    assert regression.is_file(), f"缺 C4 独立回归测试：{C4_REGRESSION_RELPATH}"

    tree = ast.parse(regression.read_text(encoding="utf-8"))
    test_functions = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]
    assert test_functions, f"{C4_REGRESSION_RELPATH} 里没有可收集的测试函数"

    # 「**被 pytest 收集**」：收集根（``testpaths``）必须覆盖该文件的所在目录。
    config = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    testpaths = config.get("tool", {}).get("pytest", {}).get("ini_options", {})
    roots = testpaths.get("testpaths", [])
    assert roots, "pyproject.toml 未声明 pytest 的 testpaths"
    assert any(
        (REPO_ROOT / root).resolve() == regression.parent.resolve()
        or regression.is_relative_to((REPO_ROOT / root).resolve())
        for root in roots
    ), f"{C4_REGRESSION_RELPATH} 不在 pytest 的收集根 {roots} 内"


@pytest.mark.skip(reason="未落地 —— C8（条件边 fresh 状态读）由 B8F1（M2）建立")
def test_c8_conditional_edge_fresh_state_read() -> None:
    """**C8** · 条件边 fresh 状态读 —— 路由函数看到本节点**刚写入**的值。

    目标形态：条件边的路由函数读到的状态包含上游节点本轮刚写入的 key。
    """
    raise NotImplementedError("C8 尚未落地 —— 由 B8F1（M2）建立")
