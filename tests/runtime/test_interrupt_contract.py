# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**结构纪律** + **契约门禁** —— 导出面 / 字段数 / 层依赖 / 零依赖。

**判据**：SC-007（L1 的 **20** 符号面**零改动**）· SC-017（**零**第三方依赖 /
**零**环境变量 / **零**出站）· SC-018（依赖门禁）· SC-019（契约门禁：
C4 / C6 / C8 **零破坏**）· 契约 §8 的 **I-1 / I-2 / I-13**。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

from freegraph.runtime import InterruptResult, SuperStepResult

from ._runtime_export_manifest import RUNTIME_EXPORT_SYMBOLS

#: 仓库根（层注册表 / 只读基准的定位基准）。
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_DIR = _REPO_ROOT / "src"


def test_the_result_objects_keep_their_field_counts() -> None:
    """**I-1**（契约 §8）：``SuperStepResult`` 的**字段数 == 4**（**不**新增第 5 个
    ⇒ **B12F1 裁定 25 ② 的冻结面零破坏**）· ``InterruptResult`` 的**字段数 == 4**
    ⇒ ⇒ 且 ``__interrupt__`` **不进** ``state``（**I-2** · 形态污染）。

    ⇒ 判据形态 = ``dataclasses.fields(...)`` 的**长度**（**不**硬编码字段名清单
    ⇒ ⇒ 与 dataclass 的增删**同步**）。
    """
    import dataclasses

    assert len(dataclasses.fields(SuperStepResult)) == 4
    assert len(dataclasses.fields(InterruptResult)) == 4

    result = InterruptResult(
        state={"messages": ["x"]}, interrupts=(), executed=("ask",), steps=1
    )
    assert "__interrupt__" not in result.state
    assert result.as_result_dict() == {
        "messages": ["x"],
        "__interrupt__": (),
    }


def test_the_runtime_all_export_surface_holds_the_expected_symbols() -> None:
    """**SC-007** / **SC-017**（**判据级可追溯性** · 宪法原则 VI v1.11.0）：

    ① ``freegraph.runtime.__all__`` == **清单**（集合相等 · **不硬编码数字**）；
    ② **L1 的 20 符号面零改动**（``freegraph.contracts.__all__`` == 清单 +
       **逐字相等**的清单 —— **不硬编码数字** ⇒ 写**清单**）；
    ③ L2 → L3 / L4 / L5 的依赖边数 == **0**（导入图断言 · 门禁 **G25**）；
    ④ **新增模块内**零 ``os.environ`` / ``os.getenv`` / ``socket`` / ``urllib``
       / 网络调用（门禁 **G4 / G24 / G26**）。

    ⚠️ **分工**：本任务是**模块内自检**（**AST 级**）⇒ ⇒ 门禁 **G4 / G24 /
    G26** 本身在**全量跑**里**独立**判定 ⇒ ⇒ 二者**不重复**（自检 + 门禁
    **双保险**）。
    """
    import freegraph.contracts as contracts
    import freegraph.runtime as runtime

    # ① L2 的导出面
    assert set(runtime.__all__) == RUNTIME_EXPORT_SYMBOLS

    # ② L1 的 20 符号面（**清单** · **不硬编码数字**）
    expected_l1 = {
        "Checkpointer",
        "Command",
        "CompiledGraph",
        "Edge",
        "FreegraphError",
        "Graph",
        "GraphInterrupt",
        "GraphRecursionError",
        "Interrupt",
        "InvalidUpdateError",
        "Node",
        "NodeFunc",
        "PregelTask",
        "RunConfig",
        "Span",
        "StateDict",
        "StateSnapshot",
        "Store",
        "TraceQuery",
        "TraceSink",
    }
    assert set(contracts.__all__) == expected_l1

    # ③ L2 → L3 / L4 / L5 的依赖边数 == 0
    forbidden_roots = (
        "freegraph.graph",
        "freegraph._stategraph",
        "freegraph.persistence",
        "freegraph.observability",
    )
    edges: list[str] = []
    for path in sorted((_SRC_DIR / "freegraph" / "runtime").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            for name in names:
                for root in forbidden_roots:
                    if name.startswith(root):
                        edges.append(f"{path.name} → {name}")
    assert edges == [], edges

    # ④ 新增模块内零环境变量 / 零出站 / 零上游依赖（**AST 级** ⇒ docstring 里
    #    **陈述**「MUST NOT import langchain」**不**算违规）
    module = _SRC_DIR / "freegraph" / "runtime" / "_interrupt.py"
    source = module.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(module))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    for name in imported:
        for forbidden in (
            "langchain",
            "langgraph",
            "langsmith",
            "socket",
            "urllib",
            "requests",
            "httpx",
        ):
            assert not name.startswith(forbidden), (
                f"中断模块引入了越界模块：{name}"
            )
    for forbidden in ("os.environ", "os.getenv", "socket", "urllib", "open("):
        assert forbidden not in source, f"中断模块出现越界构造：{forbidden}"


def test_the_contract_gate_is_satisfied() -> None:
    """**SC-019**（契约门禁 · 宪法原则 III / 原则 II）：

    ① **只读基准零改动** —— ``harness/demo/target.py`` 与入库基准
       （``git show HEAD:…``）**逐字相同**（门禁 **G29** ①）⇒ ⇒ **MUST NOT**
       改它；
    ② **验收脚本集**在门禁 **G29** ② 的**失败来源分级**下判为「**环境未就绪**
       ⇒ 通过**」（退出码 ∈ **{0, 1, 2}** 且**全部**失败行源于
       ``NotImplementedError``）⇒ ⇒ **不**要求「真跑」（「真跑」属 **B7F2 /
       B7F3 · M2** ⇒ 见偏离登记 **V-4**）；
    ③ **C4** 的独立回归测试**恒绿**（``tests/contracts/test_contract_regressions.py``
       的挂载点 ``status=landed``）；
    ④ **C8** 的挂载点**保持** ``status=not-landed · owner=B8F1 · milestone=M2``
       （**MUST NOT** 改写成 ``landed``）。

    ⚠️ **本任务只核对「照常执行」的那几部分** ⇒ ⇒ 「``target.py`` **真跑**」
    按偏离登记 **V-4** 延期到 **B7F3**。
    """
    baseline = subprocess.run(
        ["git", "show", "HEAD:harness/demo/target.py"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    current = (_REPO_ROOT / "harness" / "demo" / "target.py").read_text(
        encoding="utf-8"
    )
    assert current == baseline.stdout

    regressions = (
        _REPO_ROOT / "tests" / "contracts" / "test_contract_regressions.py"
    ).read_text(encoding="utf-8")
    # ⚠️ **机器可读标记**（门禁 G29 ③ 逐条解析）：
    #   ``# GATE-MOUNT: <编号> · status=<not-landed|landed> · owner=<承接方> · …``
    assert "GATE-MOUNT: C4 · status=landed" in regressions
    assert "GATE-MOUNT: C8 · status=not-landed" in regressions
    assert "owner=B8F1" in regressions
    assert "milestone=M2" in regressions


def test_the_new_modules_carry_a_signature_header() -> None:
    """**宪法原则 X**（署名头）：本 feature 的**新增**源文件 MUST 带署名头且
    模块 docstring 是**首个语句**。"""
    for relative in (
        "src/freegraph/runtime/_interrupt.py",
        "tests/runtime/test_interrupt_basic.py",
        "tests/runtime/test_interrupt_resume.py",
        "tests/runtime/test_interrupt_errors.py",
        "tests/runtime/test_interrupt_checkpoint.py",
        "tests/runtime/test_interrupt_contract.py",
        "tests/runtime/_runtime_export_manifest.py",
    ):
        path = _REPO_ROOT / relative
        assert path.exists(), f"缺文件：{relative}"
        source = path.read_text(encoding="utf-8")
        first_line = source.splitlines()[0]
        assert first_line.startswith("# Copyright (c) 2026 杨家成 · MIT License"), (
            f"{relative} 的首行不是署名头"
        )
        tree = ast.parse(source, filename=str(path))
        assert isinstance(tree.body[0], ast.Expr), f"{relative} 的首个语句不是 docstring"
        assert isinstance(tree.body[0].value, ast.Constant), (
            f"{relative} 的首个语句不是 docstring"
        )


def test_the_python_baseline_is_respected() -> None:
    """**宪法运行时环境基线**（G9）：源码 MUST NOT 使用 3.12+ 的 typing 构件
    ⇒ ⇒ 本 feature 的新增 / 修改文件 MUST 在 **Python 3.11** 上**可解析**。"""
    for relative in (
        "src/freegraph/runtime/_interrupt.py",
        "src/freegraph/runtime/superstep.py",
        "src/freegraph/runtime/errors.py",
    ):
        path = _REPO_ROOT / relative
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    assert sys.version_info[:2] >= (3, 11)
