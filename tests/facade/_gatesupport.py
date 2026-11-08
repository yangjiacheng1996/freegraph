# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""门面门禁的**共享辅助**（判定用的纯函数 + 子进程执行器）。

本模块为门禁 **G14–G20** 提供三类能力：

1. **AST 判定纯函数** —— 门面零实现体（**G14**）、import 两档扫描
   （**G17** ①② · research D-22）、环境变量与出站 / 文件 I/O
   （**G17** ③④）；
2. **子进程执行器** —— ``run_in_subprocess`` / ``loaded_freegraph_modules``
   （**G18** 的模块加载面 MUST 在**子进程**判定——测试进程自身已导入 pytest）；
3. **期望值来源** —— ``parse_manifest_symbols``（**G15 / G19**）从
   **手写**的 ``contracts/facade-api.md`` §0 解析 ⇒ 判定**非循环**
   （research D-07）。

> **为何判定逻辑 MUST 是纯函数**：门禁自检 MUST 证明「门禁**确实报出**」
> ⇒ 判定 MUST 能被喂进**人造违规**并返回**违规清单**（空清单 = 合规）。
> 只断言「真实目录无违规」的门禁，等于没测——「恰好没触发」与「有效」不可区分。
"""

from __future__ import annotations

import ast
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# ── 常量 ────────────────────────────────────────────────────────────────

#: 署名头（**逐字**）——门禁 G20 的判定基准（宪法原则 X）。
SIGNATURE_HEADER = (
    "# Copyright (c) 2026 杨家成 · MIT License · "
    "https://github.com/yangjiacheng1996/freegraph"
)

#: 本 feature **新建**的 10 个 ``.py``（门禁 G20 的扫描清单 · 逐字）。
SIGNED_SOURCE_FILES = (
    "src/freegraph/graph.py",
    "src/freegraph/_stategraph.py",
    "src/freegraph/_primitives.py",
    "tests/facade/__init__.py",
    "tests/facade/conftest.py",
    "tests/facade/_gatesupport.py",
    "tests/facade/_snapshot_tools.py",
    "tests/facade/test_facade.py",
    "tests/facade/test_api_snapshot.py",
    "tests/facade/test_facade_gates.py",
)

#: 门面的三个模块（**G14 / G17** 的扫描范围）。
FACADE_MODULES = (
    "src/freegraph/graph.py",
    "src/freegraph/_stategraph.py",
    "src/freegraph/_primitives.py",
)

#: **L4（持久化）/ L5（可观测）**的层段名——门禁 G17 内部档禁用的层。
#:
#: 只禁 L4 / L5（与 FR-014 ④ 同口径）——**L2 / L3 合法**：
#: 门面是 ARCH-1 的**唯一例外**（可 import L1–L3 · 裁定 9），
#: B6F1 / B10F1 / B11F1 接线后**必须** import L2 与 L3。
FORBIDDEN_LAYER_SEGMENTS = frozenset({"persistence", "observability"})

#: 门禁 G17 第三方档禁用的导入名（``langchain*`` / ``langgraph*`` /
#: ``langsmith`` / ``pydantic`` / ``typing_extensions``）。
FORBIDDEN_THIRD_PARTY_EXACT = frozenset(
    {"langsmith", "pydantic", "typing_extensions"}
)
FORBIDDEN_THIRD_PARTY_PREFIXES = ("langchain", "langgraph")

#: 环境变量读取 API（门禁 G17 ③）。
FORBIDDEN_ENV_ATTRS = frozenset({"environ", "environb", "getenv"})

#: 出站 / 外部进程模块（门禁 G17 ④）。
FORBIDDEN_IO_MODULES = frozenset({"socket", "urllib", "http", "subprocess"})

#: README「API 兼容矩阵」章节的定位正则（门禁 G19 的取行范围）。
COMPAT_MATRIX_PATTERN = re.compile(
    r"^## API 兼容矩阵\s*$(.*?)(?=^## |\Z)", re.S | re.M
)

#: 仓库根与源码树（本文件的路径基准）。
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"

#: 本 feature 的规格目录与契约目录。
SPEC_DIR = REPO_ROOT / "specs" / "b2f2-public-api-facade"
CONTRACTS_DIR = SPEC_DIR / "contracts"

#: 门面导出面清单（**手写**权威）——门禁 G15 / G19 的期望值来源。
FACADE_MANIFEST = CONTRACTS_DIR / "facade-api.md"

#: API 签名快照（**机器生成** · 入库比对点）——门禁 G16 的比对对象。
SNAPSHOT_PATH = CONTRACTS_DIR / "public-api-snapshot.txt"

#: 契约层的公开符号面清单（**手写**权威 · B2F1）——整表矩阵完整性的另一半。
CONTRACT_API_MANIFEST = (
    REPO_ROOT / "specs" / "b2f1-contracts-protocols" / "contracts" / "public-api.md"
)

#: 两份清单的 ``from ... import (`` **锚点**（解析 §0 代码块用）。
FACADE_MANIFEST_ANCHOR = "from freegraph.graph import ("
CONTRACT_MANIFEST_ANCHOR = "from freegraph.contracts import ("


# ── G14 · 门面零实现体 ─────────────────────────────────────────────────


def facade_body_violations(path: Path) -> list[str]:
    """门禁 **G14** —— 返回门面的「零实现体 + 语句白名单」违规清单。

    两条判据（``contracts/architecture-gates.md`` G14）：

    1. 模块体内的 ``class`` / ``def`` / ``async def`` 语句数 **== 0**
       （违规时报出**行号**与语句名）；
    2. 模块体只允许 ``Import`` / ``ImportFrom`` / ``Assign``（常量赋值）
       / ``Expr``（**仅**模块 docstring）——其他语句类型即失败。

    **纯函数**：只吃一个路径、只吐一个列表 ⇒ 门禁自检可以喂它造出来的
    临时违规文件，证明门禁本身有效。
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            violations.append(
                f"{path.name}:{node.lineno}: 门面内不得有实现体"
                f"（{type(node).__name__} {node.name}）"
            )
        elif isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign)):
            continue
        elif isinstance(node, ast.Expr):
            if not (
                isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                violations.append(
                    f"{path.name}:{node.lineno}: 门面内的表达式只能是模块 docstring"
                )
            continue
        else:
            violations.append(
                f"{path.name}:{node.lineno}: 门面内不得出现该语句类型"
                f"（{type(node).__name__}）"
            )
    return violations


# ── G17 · 依赖卫生（两档）──────────────────────────────────────────────


def layer_segment(module: str) -> str:
    """取导入路径的**层段**（research D-22 写死的取法）。

    首段为 ``freegraph`` 时取**第二段**，否则取**首段**：

    * ``freegraph.persistence`` ⇒ ``persistence``（**违规**）；
    * ``freegraph.contracts.types`` ⇒ ``contracts``（合法）；
    * ``_stategraph``（包内相对导入）⇒ ``_stategraph``（合法）。
    """
    parts = [part for part in module.split(".") if part]
    if not parts:
        return ""
    if parts[0] == "freegraph":
        return parts[1] if len(parts) > 1 else parts[0]
    return parts[0]


def is_forbidden_third_party(root: str) -> bool:
    """判定一个顶层包名是否落在 G17 第三方档的禁用清单内。"""
    if root in sys.stdlib_module_names:
        return False
    if root in FORBIDDEN_THIRD_PARTY_EXACT:
        return True
    return root.startswith(FORBIDDEN_THIRD_PARTY_PREFIXES)


def import_violations(path: Path) -> list[str]:
    """门禁 **G17 ①②** —— 返回 import 两档的违规清单（空 = 合规）。

    ① **内部档**：层段 ∈ {``persistence``, ``observability``} ⇒ 违规；
    ② **第三方档**：``langchain*`` / ``langgraph*`` / ``langsmith`` /
       ``pydantic`` / ``typing_extensions`` ⇒ 违规。

    **相对导入与绝对导入同等对待**（与 B2F1 的 G2 同口径）：``level >= 1``
    的导入解析后落在**包内** ⇒ 不是第三方；层段仍按同一规则取。
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                segment = layer_segment(alias.name)
                if segment in FORBIDDEN_LAYER_SEGMENTS:
                    violations.append(
                        f"{path.name}:{node.lineno}: 禁止的内部层 import: "
                        f"{alias.name}（层段 {segment}）"
                    )
                if is_forbidden_third_party(alias.name.split(".")[0]):
                    violations.append(
                        f"{path.name}:{node.lineno}: 第三方 import: {alias.name}"
                    )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            segment = layer_segment(module)
            if segment in FORBIDDEN_LAYER_SEGMENTS:
                violations.append(
                    f"{path.name}:{node.lineno}: 禁止的内部层 import: "
                    f"{'.' * node.level}{module}（层段 {segment}）"
                )
            if node.level == 0 and is_forbidden_third_party(module.split(".")[0]):
                violations.append(
                    f"{path.name}:{node.lineno}: 第三方 import: {module}"
                )
    return violations


def _dotted_name(node: ast.AST) -> str:
    """把属性链 / 名字还原成点号形态（``os.environ`` / ``Path.write_text``）。"""
    parts: list[str] = []
    current: Any = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def env_and_io_violations(path: Path) -> list[str]:
    """门禁 **G17 ③④** —— 返回环境变量读取与出站 / 文件 I/O 的违规清单。

    ③ **环境变量读取**：``os.environ`` / ``os.getenv`` / ``os.environb``
       （属性链）或 ``from os import environ`` 形态；
    ④ **出站 / 文件 I/O**：``socket.*`` / ``urllib.*`` / ``http.*`` /
       ``subprocess.*`` / ``open(...)`` / ``Path.write_*`` / ``Path.open``。

    判定以 **AST** 为准——**不扫** docstring 与注释（纯文本子串匹配会把
    「docstring 里提到 ``subprocess``」误判为违规）。
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_IO_MODULES:
                    violations.append(
                        f"{path.name}:{node.lineno}: 禁止的出站 / 外部进程模块: "
                        f"{alias.name}"
                    )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.split(".")[0] in FORBIDDEN_IO_MODULES:
                violations.append(
                    f"{path.name}:{node.lineno}: 禁止的出站 / 外部进程模块: "
                    f"{module}"
                )
            if module == "os":
                for alias in node.names:
                    if alias.name in FORBIDDEN_ENV_ATTRS:
                        violations.append(
                            f"{path.name}:{node.lineno}: 环境变量读取: "
                            f"from os import {alias.name}"
                        )
        elif isinstance(node, ast.Attribute):
            if (
                node.attr in FORBIDDEN_ENV_ATTRS
                and isinstance(node.value, ast.Name)
                and node.value.id == "os"
            ):
                violations.append(
                    f"{path.name}:{node.lineno}: 环境变量读取: os.{node.attr}"
                )
            dotted = _dotted_name(node)
            head = dotted.split(".")[0]
            if head in FORBIDDEN_IO_MODULES:
                violations.append(
                    f"{path.name}:{node.lineno}: 出站 / 外部进程调用: {dotted}"
                )
            if node.attr in {"write_text", "write_bytes"} and dotted.endswith(
                node.attr
            ):
                violations.append(
                    f"{path.name}:{node.lineno}: 文件写入调用: {dotted}"
                )
            if node.attr == "open" and "Path" in dotted:
                violations.append(
                    f"{path.name}:{node.lineno}: 文件 I/O 调用: {dotted}"
                )
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "open":
                violations.append(
                    f"{path.name}:{node.lineno}: 文件 I/O 调用: open(...)"
                )
    return violations


# ── G18 · 子进程模块加载面 ─────────────────────────────────────────────


def run_in_subprocess(code: str) -> str:
    """在**子进程**中执行一段 Python 代码并返回其标准输出。

    **必须子进程**：测试进程自身已导入 pytest，同进程 ``sys.modules``
    不可作依据（沿用 B1F1 / B2F1 的判定口径）。

    **必须注入** ``PYTHONPATH=<src_dir>``（否则子进程 import 不到
    ``freegraph`` ⇒ 门禁**假红**）；**cwd 设为临时目录**——防仓库根里的
    同名目录劫持导入（照抄 ``tests/contracts/test_architecture.py`` 的
    ``_run_python`` 口径）。
    """
    with tempfile.TemporaryDirectory(prefix="fg-facade-gate-") as tmp:
        env = {**os.environ, "PYTHONPATH": str(SRC_DIR)}
        proc = subprocess.run(
            [sys.executable, "-c", code],
            env=env,
            cwd=tmp,
            capture_output=True,
            text=True,
            # 子进程输出按 UTF-8 **容错解码**（Windows 管道默认 cp1252 ⇒ 否则解码失败）
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    assert proc.returncode == 0, f"子进程失败：\n{proc.stderr}"
    return proc.stdout.strip()


def loaded_freegraph_modules(code: str) -> list[str]:
    """返回子进程执行 ``code`` 后已加载的 ``freegraph*`` 模块清单。"""
    snippet = (
        f"{code}\n"
        "import sys, json\n"
        "print(json.dumps(sorted(m for m in sys.modules if m.startswith('freegraph'))))"
    )
    return json.loads(run_in_subprocess(snippet))


def forbidden_loaded_modules(
    loaded: list[str], forbidden_prefixes: tuple[str, ...]
) -> list[str]:
    """从**已加载模块清单**里挑出命中禁用前缀的模块（空 = 合规）。

    门禁 **G18** 的判定纯函数——前缀匹配（含其子模块）：
    ``freegraph.persistence`` ⇒ ``freegraph.persistence.store`` 也命中。
    """
    return sorted(
        name
        for name in loaded
        if any(
            name == prefix or name.startswith(prefix + ".")
            for prefix in forbidden_prefixes
        )
    )


def facade_re_export_violations(source: str) -> list[str]:
    """检出**顶层包导入门面**的语句（源码文本判据 · FR-013）。

    ``freegraph/__init__.py`` MUST NOT ``from .graph import ...``（MUST NOT 以
    任何形式 re-export 门面）——否则顶层包的惰性被打破、契约层「可单独消费」
    的收益归零。

    **纯函数**：吃源码文本、吐违规清单 ⇒ 门禁自检**不得真的改** ``__init__.py``。
    """
    tree = ast.parse(source)
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "freegraph.graph" or alias.name.startswith(
                    "freegraph.graph."
                ):
                    violations.append(f"顶层包不得 import 门面：{alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module in ("graph", "freegraph.graph") or module.startswith(
                "freegraph.graph."
            ):
                violations.append(
                    f"顶层包不得 from {'.' * node.level}{module} import —— 门面"
                    "只能经由 freegraph.graph 显式导入"
                )
    return violations


# ── G15 / G19 · 期望值来源 ─────────────────────────────────────────────


def parse_manifest_symbols(
    path: Path, anchor: str = FACADE_MANIFEST_ANCHOR
) -> set[str]:
    """解析某份清单 §0 的符号清单 → **集合**。

    解析规则（``contracts/facade-api.md`` §0 写死）：

    ① 只取 ``from ... import (`` 与其**配对** ``)`` 之间的行；
    ② **跳过**以 ``#`` 开头的注释行（含缩进注释行）；
    ③ 每行取**第一个逗号之前**的标识符（``strip()`` 后）；空行跳过；
    ④ 结果为**集合**（顺序不作判据）。

    **期望值 MUST 来自手写清单**——若从**生成的**快照解析期望值，
    门禁就成了「代码 → 快照 → 快照 vs 代码」的**循环论证**（research D-07）。

    ``anchor`` 用于切换清单类型（门面的 ``from freegraph.graph import (``
    与契约层的 ``from freegraph.contracts import (``）。
    """
    text = path.read_text(encoding="utf-8")
    blocks = re.findall(r"```[A-Za-z0-9_+-]*\n(.*?)```", text, re.S)
    candidates = [
        block for block in blocks if block.lstrip().startswith(anchor)
    ]
    assert len(candidates) == 1, (
        f"{path} §0 的符号清单代码块 MUST **恰有 1 个**，"
        f"实得 {len(candidates)} 个"
    )
    lines = candidates[0].splitlines()
    assert lines[0].strip() == anchor, (
        f"{path} §0 代码块的首行 MUST 是 {anchor!r}"
    )
    end = next(
        (i for i, line in enumerate(lines) if line.strip() == ")"),
        None,
    )
    assert end is not None, f"{path} §0 代码块缺少收尾的 ')'"

    symbols: set[str] = set()
    for raw in lines[1:end]:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        name = stripped.split(",")[0].split("#")[0].strip()
        assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name), (
            f"{path} §0 的符号行不是合法标识符：{raw!r}"
        )
        symbols.add(name)
    return symbols


def g15_subset_violations(
    exports: set[str], public_names: set[str], allowed: set[str]
) -> list[str]:
    """门禁 **G15 子集段** —— 清单外的符号（空 = 合规）。

    抓「偷偷多导出一个」；``__all__`` 与**公开名集合**两处都要判——
    只判 ``__all__`` 有漏洞（``from ._impl import helper`` 未进 ``__all__``
    时照样可被 ``from freegraph.graph import helper`` 取到）。
    """
    return sorted((exports - allowed) | (public_names - allowed))


def g15_equality_violations(
    exports: set[str], public_names: set[str], expected: set[str]
) -> list[str]:
    """门禁 **G15 集合相等段** —— 与期望集合的**对称差**（空 = 合规）。

    抓「漏导出」——子集段抓不到这一类。
    """
    return sorted((exports ^ expected) | (public_names ^ expected))


# ── G16 · 快照比对 ─────────────────────────────────────────────────────


def snapshot_diff(expected: str, actual: str) -> str:
    """返回两段快照文本的 **unified diff**（空 = 逐字节相同）。"""
    return "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile="committed/public-api-snapshot.txt",
            tofile="generated",
        )
    )


def compare_snapshot(expected: str, generated: str) -> tuple[bool, str]:
    """**真实的比对路径** —— 返回 ``(是否一致, diff 文本)``。

    门禁 G16 与其**自检**共用这一条路径 ⇒ 自检证明的是「比对逻辑本身
    抓得出漂移」，而不仅仅是「渲染器能渲染出不同的文本」
    （research **D-23**）。
    """
    if expected == generated:
        return True, ""
    return False, snapshot_diff(expected, generated)


def diff_line_count(expected: str, actual: str) -> int:
    """返回 diff 的**差异行数**（门禁 G16 要求差异行数 ≥ 1）。"""
    return len(
        [
            line
            for line in snapshot_diff(expected, actual).splitlines()
            if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
        ]
    )


# ── G19 · 兼容矩阵取行 ─────────────────────────────────────────────────


def compat_matrix_section(readme: str) -> str:
    """取出 README「## API 兼容矩阵」章节的正文（**不扫全文**）。"""
    match = COMPAT_MATRIX_PATTERN.search(readme)
    assert match, "README.md 缺少「## API 兼容矩阵」章节"
    return match.group(1)


def compat_matrix_rows(readme: str) -> list[tuple[str, list[str]]]:
    """取出兼容矩阵的**数据行** → ``[(符号, 单元格列表), ...]``。

    取行范围 = 章节内；只取首列是 ``| `符号` |`` 形态的行（表头与分隔行
    不含反引号）——README 其它章节里的表格行会被误判（与 B2F1 的 G8
    同一条教训）。
    """
    rows: list[tuple[str, list[str]]] = []
    for line in compat_matrix_section(readme).splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.split("|")[1:-1]]
        if not cells:
            continue
        match = re.fullmatch(r"`([A-Za-z_][A-Za-z0-9_]*)`", cells[0])
        if not match:
            continue
        rows.append((match.group(1), cells))
    return rows


# ── G20 · 署名头 ───────────────────────────────────────────────────────


def signature_header_violations(path: Path) -> list[str]:
    """门禁 **G20** —— 返回署名头 / docstring 位置的违规清单（空 = 合规）。

    两条判据：① 首行**逐字**等于署名头；② **模块 docstring 是首个语句**
    （署名行是注释，不构成语句）。
    """
    violations: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != SIGNATURE_HEADER:
        violations.append(f"{path.name}: 首行不是署名头（逐字不等）")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    if not ast.get_docstring(tree):
        violations.append(f"{path.name}: 缺少模块 docstring")
    elif not (isinstance(tree.body[0], ast.Expr) and isinstance(
        tree.body[0].value, ast.Constant
    )):
        violations.append(f"{path.name}: 模块 docstring 不是首个语句")
    return violations
