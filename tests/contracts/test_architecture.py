# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""契约层的**十三条架构门禁**（G1–G13）。

门禁定义见 ``specs/b2f1-contracts-protocols/contracts/architecture-gates.md``：

======  ==========================================================  ==========================
门禁    含义                                                     spec 条目
======  ==========================================================  ==========================
G1      顶层包**惰性**（``import freegraph`` 不连带加载子模块）    FR-011/SC-002
G2      契约层**零**内部 import + **零**第三方 import（两档范围）  FR-008/SC-003
G3      依赖闭包**为空**（基础安装零第三方依赖）                   FR-011/SC-002
G4      **零**环境变量读取 + **零**出站（范围含夹具目录）           FR-011
G5      每个新源文件带署名头且 docstring 为首个语句                FR-015/SC-009
G6      ``py.typed`` 存在且为空（PEP 561）                         FR-011
G7      公开符号面**恰为 18 个**（清单驱动 · 分两段落地）           FR-012/SC-001/SC-017
G8      文档合规门禁（兼容矩阵逐符号覆盖 + ``THIRD_PARTY_NOTICES``） FR-013/SC-020/SC-021
G9      **运行时环境基线**：typing 构件上限 = 3.11                  FR-011
G10     协议**纯抽象**（方法体只有 ``...``）                        FR-007/SC-008
G11     结构化子类型判定可用（完整实现真 / 缺方法假）               FR-007/SC-007
G12     公开符号面**唯一权威**（机器标记）                          FR-013/SC-020
G13     **纯数据纪律**（数据类不得含对象引用字段）                  FR-006/SC-013
======  ==========================================================  ==========================

G1–G6 / G9 继承自 **B1F1**（``specs/b1f1-contracts-core/contracts/architecture-gates.md``），
G7 / G8 由本 feature **修改**（8 → 18 · 改为清单驱动），G10–G13 为**新增**。

「已加载模块清单」类断言 MUST 在**子进程**中执行——测试进程自身已被
pytest 污染，同进程 ``sys.modules`` 不可作依据（research D-11）。
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import types
from collections import Counter
from collections.abc import Mapping
from importlib.metadata import PackageNotFoundError, metadata, requires
from pathlib import Path
from typing import Any, Iterable, Sequence, Union, get_args, get_origin, get_type_hints

import pytest

# ── 门禁常量 ────────────────────────────────────────────────────────────

SIGNATURE_HEADER = (
    "# Copyright (c) 2026 杨家成 · MIT License · "
    "https://github.com/yangjiacheng1996/freegraph"
)

#: 契约层的公开符号面（恰 18 个）——**唯一权威**是
#: ``specs/b2f1-contracts-protocols/contracts/public-api.md`` §0。
#:
#: **期望值一律从 §0 解析**（:func:`parse_public_api_symbols`），MUST NOT 硬编码
#: ——清单变、断言自动跟随，杜绝两处漂移（B2F1 复核裁定 · 2026-11-06）。
PUBLIC_API_MANIFEST = Path("specs/b2f1-contracts-protocols/contracts/public-api.md")

#: FR-012 所列的**本 feature 新增**的 10 个公开符号（SC-017 的机械落点）。
FR012_NEW_SYMBOLS = {
    "NodeFunc",
    "Checkpointer",
    "TraceSink",
    "Store",
    "CompiledGraph",
    "Graph",
    "Node",
    "Edge",
    "Span",
    "TraceQuery",
}

#: 本层 10 个符号中**在上游没有同名符号**者 ⇒ 兼容矩阵该行 MUST 写
#: 「无上游对应」+ 契约条目号，**MUST NOT** 硬凑行号（宪法原则 VIII）。
NO_UPSTREAM_SYMBOLS = {"NodeFunc", "TraceSink", "Span", "TraceQuery"}

#: 契约包自身的名字（包内绝对/相对导入均落在它之内 → 合法）。
CONTRACT_PACKAGE = "freegraph.contracts"

#: 获准的第三方依赖——**空集**（基础安装零第三方运行时依赖，宪法 v1.2.0）。
#:
#: 契约层**只允许标准库**（判据：``module`` ∈ ``sys.stdlib_module_names``）。
#: 曾获准 ``typing_extensions``（宪法 v1.1.0 及以前），
#: 已于 **v1.2.0** 剥离——最低 Python 版本抬至 3.11 后不再需要。
ALLOWED_THIRD_PARTY: frozenset[str] = frozenset()

#: G4 禁止的模块（网络 / 外部进程 / LangChain 家族）。
FORBIDDEN_MODULES = frozenset(
    {
        "socket",
        "http",
        "urllib",
        "requests",
        "httpx",
        "subprocess",
        "langchain",
        "langchain_core",
        "langsmith",
        "langgraph",
        "langgraph_core",
        "langgraph_sdk",
        "langsmith_sdk",
    }
)

#: G4 禁止的环境变量读取 API。
FORBIDDEN_ENV_ATTRS = frozenset({"environ", "environb", "getenv"})

#: 本 feature 新建的源文件（原则 X 的署名头适用范围，含 ``tests/``）。
SIGNED_SOURCE_FILES = (
    "src/freegraph/__init__.py",
    "src/freegraph/contracts/__init__.py",
    "src/freegraph/contracts/types.py",
    "src/freegraph/contracts/errors.py",
    "src/freegraph/contracts/protocols.py",
    "src/freegraph/contracts/graph.py",
    "src/freegraph/contracts/trace.py",
    "tests/contracts/conftest.py",
    "tests/contracts/test_types.py",
    "tests/contracts/test_errors.py",
    "tests/contracts/test_architecture.py",
    "tests/contracts/test_protocols.py",
    "tests/contracts/test_graph.py",
    "tests/contracts/test_span.py",
    "tests/contracts/fixtures/__init__.py",
    "tests/contracts/fixtures/external_impl.py",
)


# ── 子进程辅助 ──────────────────────────────────────────────────────────


def _run_python(code: str, src_dir: Path, cwd: Path) -> str:
    """在**子进程**中执行一段 Python 代码并返回其标准输出。

    注入 ``PYTHONPATH=<src_dir>`` —— 既不依赖当前工作目录，
    也不要求先 ``pip install``；``cwd`` 取临时目录，避免仓库根里的同名
    目录劫持导入。
    """
    env = {**os.environ, "PYTHONPATH": str(src_dir)}
    proc = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, f"子进程失败：\n{proc.stderr}"
    return proc.stdout.strip()


def _loaded_freegraph_modules(code: str, src_dir: Path, cwd: Path) -> list[str]:
    """返回子进程中已加载的 ``freegraph*`` 模块清单。"""
    snippet = (
        f"{code}\n"
        "import sys\n"
        "print(sorted(m for m in sys.modules if m.startswith('freegraph')))"
    )
    return ast.literal_eval(_run_python(snippet, src_dir, cwd))


# ── 扫描纯函数（供门禁断言与门禁自检共用）──────────────────────────────


def _iter_python_files(dirs: Iterable[Path]) -> list[Path]:
    """列出给定目录（可多个）下的全部 ``*.py``，按路径排序。"""
    files: list[Path] = []
    for directory in dirs:
        directory = Path(directory)
        if not directory.is_dir():
            continue
        files.extend(sorted(directory.rglob("*.py")))
    return files


def _check_internal_target(
    path: Path, lineno: int, module: str, level: int
) -> list[str]:
    """判定单个 import 目标是否违反 G2 的**内部 import 档**。

    内部档只管「指向 freegraph 顶层或包外 ``freegraph.*``」的 import——
    ``freegraph.contracts`` **内部**的导入（相对或绝对）**一律合法**
    （外部实现夹具只能写绝对导入）。
    """
    if level >= 2:
        # 相对导入跳到包外（如 ``from ..runtime import X``）⇒ 违规。
        return [
            f"{path.name}:{lineno}: 包外相对 import: "
            f"{'.' * level}{module} (level={level})"
        ]
    if level == 1:
        # 包内相对导入 ⇒ 解析后落在 ``freegraph.contracts`` 内 ⇒ 合法。
        return []

    root = module.split(".")[0]
    if root == "freegraph":
        if module == CONTRACT_PACKAGE or module.startswith(CONTRACT_PACKAGE + "."):
            return []
        return [f"{path.name}:{lineno}: 内部模块 import: {module}"]
    return []


def _check_third_party_target(
    path: Path, lineno: int, module: str, level: int
) -> list[str]:
    """判定单个 import 目标是否违反 G2 的**第三方 import 档**。

    只认「非标准库且非 freegraph 自身」的顶层包（``langchain`` /
    ``langchain-core`` / ``langgraph`` / ``langsmith`` / ``pydantic`` /
    ``typing_extensions`` 及任何其它第三方包）。
    """
    if level >= 1:
        # 相对 import ⇒ 包内 ⇒ 不是第三方。
        return []
    root = module.split(".")[0]
    if not root:
        return []
    if root == "freegraph":
        # 本项目自己的包不是第三方依赖。
        return []
    if root in sys.stdlib_module_names:
        return []
    if root in ALLOWED_THIRD_PARTY:
        return []
    return [f"{path.name}:{lineno}: 第三方 import: {module}"]


def scan_internal_imports(dirs: Sequence[Path]) -> list[str]:
    """G2 · **内部 import 档** —— 返回违规清单（空清单 = 合规）。

    扫描范围：``src/freegraph/contracts/**`` + ``tests/contracts/**``
    （**含** ``fixtures/``）——凡指向 ``freegraph`` **顶层**或包外
    ``freegraph.*`` 的 import 即违规。

    这是个**纯函数**——只吃目录列表、只吐一个列表，故门禁自检可以喂它
    造出来的临时违规目录，证明门禁本身有效。
    """
    violations: list[str] = []
    for path in _iter_python_files(dirs):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    violations.extend(
                        _check_internal_target(path, node.lineno, alias.name, 0)
                    )
            elif isinstance(node, ast.ImportFrom):
                violations.extend(
                    _check_internal_target(
                        path, node.lineno, node.module or "", node.level
                    )
                )
    return violations


def scan_third_party_imports(dirs: Sequence[Path]) -> list[str]:
    """G2 · **第三方 import 档** —— 返回违规清单（空清单 = 合规）。

    扫描范围：``src/freegraph/contracts/**`` + ``tests/contracts/fixtures/**``
    （**仅夹具目录**）——其余测试文件**豁免**（``pytest`` 是开发期工具，
    一刀切会让门禁因 ``import pytest`` 恒失败）。
    """
    violations: list[str] = []
    for path in _iter_python_files(dirs):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    violations.extend(
                        _check_third_party_target(path, node.lineno, alias.name, 0)
                    )
            elif isinstance(node, ast.ImportFrom):
                violations.extend(
                    _check_third_party_target(
                        path, node.lineno, node.module or "", node.level
                    )
                )
    return violations


def scan_forbidden_usage(dirs: Sequence[Path]) -> list[str]:
    """G4 · 返回违规清单（空清单 = 合规）。

    判定 MUST 以 **AST** 为准：只查 ``Import`` / ``ImportFrom`` 的模块名
    与 ``Attribute`` / ``Name`` 访问，**不扫 docstring 与注释**——
    纯文本子串匹配会把「docstring 里提到 ``subprocess``」误判为违规。

    扫描范围：``src/freegraph/contracts/**`` + ``tests/contracts/fixtures/**``
    （**夹具同样受检**——夹具不得为了「假装能联网」而 import 网络库）。
    """
    violations: list[str] = []
    for path in _iter_python_files(dirs):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in FORBIDDEN_MODULES:
                        violations.append(
                            f"{path.name}:{node.lineno}: 禁止的模块: {alias.name}"
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                root = module.split(".")[0]
                if root in FORBIDDEN_MODULES:
                    violations.append(
                        f"{path.name}:{node.lineno}: 禁止的模块: {module}"
                    )
                if root == "os":
                    for alias in node.names:
                        if alias.name in FORBIDDEN_ENV_ATTRS:
                            violations.append(
                                f"{path.name}:{node.lineno}: 环境变量读取: "
                                f"from os import {alias.name}"
                            )
            elif isinstance(node, ast.Attribute):
                base = node.value
                if (
                    node.attr in FORBIDDEN_ENV_ATTRS
                    and isinstance(base, ast.Name)
                    and base.id == "os"
                ):
                    violations.append(
                        f"{path.name}:{node.lineno}: 环境变量读取: os.{node.attr}"
                    )
    return violations


def _protocol_class_nodes(tree: ast.Module) -> list[ast.ClassDef]:
    """挑出「以 ``Protocol`` 为基类」的类（协议类）。"""
    found: list[ast.ClassDef] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            base_name = None
            if isinstance(base, ast.Name):
                base_name = base.id
            elif isinstance(base, ast.Attribute):
                base_name = base.attr
            if base_name == "Protocol":
                found.append(node)
                break
    return found


def scan_protocol_abstractness(path: Path) -> list[str]:
    """G10 · 协议**纯抽象** —— 返回违规清单（空清单 = 合规）。

    协议类体内的方法**方法体必须只有 ``...``**（``ast.Expr`` 包裹的
    ``ast.Constant(Ellipsis)``）。出现 ``pass`` / ``raise NotImplementedError``
    / 任何赋值或返回语句 ⇒ 失败。

    **构造期口径**：协议类尚未落地时（扫描结果为空）⇒ 判为**通过**；
    协议类一旦出现即自动受检。
    """
    violations: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for cls in _protocol_class_nodes(tree):
        for fn in cls.body:
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for stmt in fn.body:
                if (
                    isinstance(stmt, ast.Expr)
                    and isinstance(stmt.value, ast.Constant)
                    and stmt.value.value is Ellipsis
                ):
                    continue
                violations.append(
                    f"{path.name}:{cls.lineno}: {cls.name}.{fn.name} 的方法体"
                    "不是纯 ``...``（协议 MUST 为纯抽象）"
                )
    return violations


# ── 公开符号面清单解析（G7 / G8 共用 · 单一来源）────────────────────────


def parse_public_api_symbols(manifest: Path) -> tuple[list[str], list[str]]:
    """解析 ``public-api.md`` §0 的符号清单 → ``(既有, 新增)`` 两段。

    **规则写死**（B2F1 复核裁定 · 2026-11-06）：

    ① 定位**唯一**以 ``from freegraph.contracts import (`` 起始、以 ``)`` 结束的
       代码块（MUST 锚定本块，MUST NOT 取全文第一个代码块）；
    ② **丢弃这两行锚点本身**（它们不是符号）；
    ③ 块内每行先 ``strip()``，**跳过空行**与**以 ``#`` 开头的行**
       （注释行不是符号；分组注释行用于切分「既有 / 新增」）；
    ④ 余下每行按 ``,`` 切分取**首段**再 ``strip()``，并**断言**其匹配
       ``^[A-Za-z_][A-Za-z0-9_]*$``（不匹配即报可读错误，MUST NOT 静默跳过）；
    ⑤ 抽出的符号名集合 MUST 为 **18** 个（否则报可读错误，MUST NOT 静默返回空集）；
    ⑥ 按 §0 的**分组注释**把结果切分为「B1F1 已冻结的 8 个」与
       「B2F1 新增的 10 个」两段。
    """
    text = manifest.read_text(encoding="utf-8")
    blocks = re.findall(r"```[A-Za-z0-9_+-]*\n(.*?)```", text, re.S)
    candidates = [
        block
        for block in blocks
        if block.lstrip().startswith("from freegraph.contracts import (")
    ]
    assert len(candidates) == 1, (
        f"{manifest} §0 的符号清单代码块 MUST **恰有 1 个**，"
        f"实得 {len(candidates)} 个"
    )
    lines = candidates[0].splitlines()
    assert lines[0].strip() == "from freegraph.contracts import (", (
        f"{manifest} §0 代码块的首行 MUST 是 "
        "'from freegraph.contracts import ('"
    )
    end = next(
        (i for i, line in enumerate(lines) if line.strip() == ")"),
        None,
    )
    assert end is not None, f"{manifest} §0 代码块缺少收尾的 ')'"

    existing: list[str] = []
    new: list[str] = []
    bucket = existing
    for raw in lines[1:end]:
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            if "B1F1 已冻结的 8 个" in stripped:
                bucket = existing
            elif "B2F1 新增的 10 个" in stripped:
                bucket = new
            continue
        name = stripped.split(",")[0].split("#")[0].strip()
        assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name), (
            f"{manifest} §0 的符号行不是合法标识符：{raw!r}（期望形状：名字 + ','）"
        )
        bucket.append(name)

    symbols = existing + new
    assert len(symbols) == 18, (
        f"{manifest} §0 解析出的符号数 MUST 为 18，实得 {len(symbols)}：{symbols}"
    )
    assert len(existing) == 8, (
        f"{manifest} §0 的「既有」段 MUST 恰为 8 个，实得 {len(existing)}"
    )
    assert set(new) == FR012_NEW_SYMBOLS, (
        f"{manifest} §0 的「新增」段 MUST 恰为 FR-012 所列的 10 个，"
        f"实得 {sorted(set(new) ^ FR012_NEW_SYMBOLS)}（对称差）"
    )
    return existing, new


def _first_line(path: Path) -> str:
    """取文件的首行（署名头判定的取样点）。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[0] if lines else ""


def _read_all(path: Path) -> list[str]:
    """从模块源码里读出 ``__all__``（**AST 解析**，不执行代码）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    return [ast.literal_eval(element) for element in node.value.elts]
    return []


def g7_subset_violations(exports: set[str], allowed: set[str]) -> list[str]:
    """G7 · **子集段** —— ``__all__`` 中清单外的符号（空清单 = 合规）。"""
    return sorted(exports - allowed)


def g7_equality_violations(exports: set[str], expected: set[str]) -> list[str]:
    """G7 · **集合相等段** —— ``__all__`` 与期望集合的**对称差**（空 = 合规）。"""
    return sorted(exports ^ expected)


# ── G11 / G13 · 判定纯函数 ──────────────────────────────────────────────


def _is_whitelisted_field_type(annotation: Any, pure_data_classes: tuple[type, ...]) -> bool:
    """G13 · 判定一个字段注解是否落在**纯数据白名单**之内。

    白名单：标量（``str`` / ``int`` / ``float`` / ``bool`` / ``None``）、
    ``Mapping[str, Any]``（``Any`` **仅允许**出现在其**值位**）、
    ``tuple[...]``（元素为标量或本层纯数据类）、以及本层纯数据类。
    """
    scalars = (str, int, float, bool, type(None))
    origin = get_origin(annotation)
    if origin is Union or origin is types.UnionType:
        return all(
            _is_whitelisted_field_type(arg, pure_data_classes)
            for arg in get_args(annotation)
        )
    if origin is tuple:
        args = [arg for arg in get_args(annotation) if arg is not Ellipsis]
        return bool(args) and all(
            _is_whitelisted_field_type(arg, pure_data_classes) for arg in args
        )
    if origin is not None:
        if origin is Mapping:
            return get_args(annotation) == (str, Any)
        return False
    if annotation is Any:
        return False
    if isinstance(annotation, type) and issubclass(annotation, pure_data_classes):
        return True
    return annotation in scalars


def scan_pure_data_discipline(cls: type, pure_data_classes: tuple[type, ...]) -> list[str]:
    """G13 · 扫描一个数据类的字段注解，返回违规清单（空清单 = 合规）。

    **失败条件**（任一成立即失败）：① 字段类型落在白名单之外；
    ② 出现**可调用类型**；③ ``Any`` 出现在白名单所列位置**之外**。
    """
    violations: list[str] = []
    for name, annotation in get_type_hints(cls).items():
        if not _is_whitelisted_field_type(annotation, pure_data_classes):
            violations.append(
                f"{cls.__name__}.{name}: 字段类型 {annotation!r} 不在纯数据白名单内"
            )
    return violations


# ── G1 · 顶层包惰性（SC-002）──────────────────────────────────────────


class TestTopLevelPackageIsLazy:
    """G1 · 顶层包惰性 —— ``import freegraph`` 不连带加载任何子模块。"""

    def test_importing_top_level_loads_only_itself(
        self, src_dir: Path, tmp_path: Path
    ) -> None:
        """已加载的 ``freegraph.*`` 模块 MUST **恰为** ``['freegraph']``。"""
        loaded = _loaded_freegraph_modules("import freegraph", src_dir, tmp_path)
        assert loaded == ["freegraph"]

    def test_importing_contracts_loads_no_internal_layer(
        self, src_dir: Path, tmp_path: Path
    ) -> None:
        """``import freegraph.contracts`` MUST NOT 连带加载任何内部层模块。

        契约层**自身的子模块**（``freegraph.contracts.types`` /
        ``freegraph.contracts.errors``）**不受限**——新增或改名子模块
        不必改这条断言。
        """
        loaded = _loaded_freegraph_modules(
            "import freegraph.contracts", src_dir, tmp_path
        )
        assert loaded, "契约层导入后应至少加载 freegraph 与 freegraph.contracts"
        internal = [
            name
            for name in loaded
            if name != "freegraph"
            and name != CONTRACT_PACKAGE
            and not name.startswith(CONTRACT_PACKAGE + ".")
        ]
        assert internal == [], f"契约层连带加载了内部层模块：{internal}"

    def test_importing_contracts_does_not_pull_known_layers(
        self, src_dir: Path, tmp_path: Path
    ) -> None:
        """显式点名：运行时 / 图定义 / 持久化 / 可观测四层一个都不许出现。"""
        loaded = _loaded_freegraph_modules(
            "import freegraph.contracts", src_dir, tmp_path
        )
        for forbidden in (
            "freegraph.runtime",
            "freegraph.graph",
            "freegraph.persistence",
            "freegraph.observability",
        ):
            assert forbidden not in loaded


class TestNoInternalOrThirdPartyImports:
    """G2 · 契约层零内部 import + 零第三方 import（**两档范围**）。"""

    def test_contracts_layer_has_no_internal_import_violations(
        self, contracts_dir: Path, repo_root: Path
    ) -> None:
        """内部 import 档：``src/freegraph/contracts/**`` + ``tests/contracts/**``。"""
        violations = scan_internal_imports(
            [contracts_dir, repo_root / "tests" / "contracts"]
        )
        assert violations == [], "\n".join(violations)

    def test_contracts_and_fixtures_have_no_third_party_import_violations(
        self, contracts_dir: Path, repo_root: Path
    ) -> None:
        """第三方 import 档：契约层 + **仅**夹具目录（测试文件豁免）。"""
        violations = scan_third_party_imports(
            [contracts_dir, repo_root / "tests" / "contracts" / "fixtures"]
        )
        assert violations == [], "\n".join(violations)

    def test_no_langchain_family_import(self, contracts_dir: Path, repo_root: Path) -> None:
        """契约层 MUST NOT import ``langchain`` / ``langchain_core`` /
        ``langsmith`` / ``langgraph`` 全系列。

        （FR-008 明令「不复用 LangChain 家族的运行配置类型」——
        复用即把 ``langsmith`` 拖回依赖树。）
        """
        text = "\n".join(
            scan_third_party_imports(
                [contracts_dir, repo_root / "tests" / "contracts" / "fixtures"]
            )
        )
        for forbidden in ("langchain", "langchain_core", "langsmith", "langgraph"):
            assert forbidden not in text


class TestNoEnvVarAndNoEgress:
    """G4 · 零环境变量读取 + 零出站。"""

    def test_contracts_and_fixtures_have_no_forbidden_usage(
        self, contracts_dir: Path, repo_root: Path
    ) -> None:
        """真实目录 MUST 无任何 G4 违规（含夹具目录）。"""
        violations = scan_forbidden_usage(
            [contracts_dir, repo_root / "tests" / "contracts" / "fixtures"]
        )
        assert violations == [], "\n".join(violations)

    def test_no_env_var_read(self, contracts_dir: Path, repo_root: Path) -> None:
        """MUST NOT 出现 ``os.environ`` / ``os.getenv`` / ``os.environb``。"""
        text = "\n".join(
            scan_forbidden_usage(
                [contracts_dir, repo_root / "tests" / "contracts" / "fixtures"]
            )
        )
        for pattern in ("os.environ", "os.getenv", "os.environb"):
            assert pattern not in text

    def test_no_network_or_process_modules(
        self, contracts_dir: Path, repo_root: Path
    ) -> None:
        """MUST NOT import ``socket`` / ``http`` / ``urllib`` / ``requests`` /
        ``httpx`` / ``subprocess``。"""
        text = "\n".join(
            scan_forbidden_usage(
                [contracts_dir, repo_root / "tests" / "contracts" / "fixtures"]
            )
        )
        for forbidden in (
            "socket",
            "http",
            "urllib",
            "requests",
            "httpx",
            "subprocess",
        ):
            assert forbidden not in text


class TestSignatureHeader:
    """G5 · 每个新源文件带署名头，且模块 docstring 是首个语句。"""

    @pytest.mark.parametrize("relative_path", SIGNED_SOURCE_FILES)
    def test_first_line_is_the_signature_header(
        self, repo_root: Path, relative_path: str
    ) -> None:
        """文件首行 MUST **逐字**等于署名行。"""
        path = repo_root / relative_path
        assert path.is_file(), f"缺少文件：{relative_path}"
        assert _first_line(path) == SIGNATURE_HEADER

    @pytest.mark.parametrize("relative_path", SIGNED_SOURCE_FILES)
    def test_docstring_is_the_first_statement(
        self, repo_root: Path, relative_path: str
    ) -> None:
        """署名行是**注释**，不构成语句——模块 docstring 仍 MUST 是首个语句。"""
        path = repo_root / relative_path
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        assert ast.get_docstring(tree), f"{relative_path} 缺少模块 docstring"
        first = tree.body[0]
        assert isinstance(first, ast.Expr), f"{relative_path} 的首个语句不是 docstring"
        assert isinstance(first.value, ast.Constant)
        assert isinstance(first.value.value, str)

    def test_gate_docstring_declares_thirteen_gates(self, repo_root: Path) -> None:
        """本文件的模块 docstring 首句 MUST 含「十三条架构门禁」。

        （现状写的是「八条架构门禁」——B1F1 遗留。本 feature 把门禁面扩到
        **G1–G13**，MUST NOT 留下过时的门禁面声明。）
        """
        path = repo_root / "tests/contracts/test_architecture.py"
        docstring = ast.get_docstring(
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        )
        assert docstring, "test_architecture.py 缺少模块 docstring"
        first_sentence = docstring.split("。")[0]
        assert "十三条架构门禁" in first_sentence, (
            f"test_architecture.py 的模块 docstring 首句 MUST 声明"
            f"「十三条架构门禁」，实得：{first_sentence!r}"
        )


class TestPyTypedMarker:
    """G6 · ``py.typed`` 存在且为空（PEP 561）。"""

    def test_py_typed_exists_and_is_empty(self, src_dir: Path) -> None:
        """``src/freegraph/py.typed`` MUST 存在且**内容为空**。"""
        marker = src_dir / "freegraph" / "py.typed"
        assert marker.is_file(), "缺少 src/freegraph/py.typed"
        assert marker.read_bytes() == b"", "py.typed MUST 为空文件"

    def test_no_subpackage_py_typed(self, src_dir: Path) -> None:
        """顶层一个标记即覆盖全部子包——MUST NOT 新建 ``contracts/py.typed``。"""
        assert not (src_dir / "freegraph" / "contracts" / "py.typed").exists()


class TestPublicSymbolSurface:
    """G7 · 公开符号面恰为 18 个（FR-012 · 清单驱动）。"""

    def test_manifest_splits_into_eight_existing_and_ten_new(self, repo_root: Path) -> None:
        """**新增集合段**（始终启用）——既有恰 8 个、新增恰为 FR-012 的 10 个。

        这是 SC-017「新增恰为 10 个」的机械落点（总集合相等断言**不覆盖**这一维）。
        """
        existing, new = parse_public_api_symbols(repo_root / PUBLIC_API_MANIFEST)
        assert len(existing) == 8
        assert set(new) == FR012_NEW_SYMBOLS

    def test_all_equals_public_symbols(self, repo_root: Path) -> None:
        """**集合相等段** —— ``__all__`` MUST **集合等于** §0 解析出的 18 个符号。

        （18 个符号全部导出后启用——抓「漏导出」。集合断言才能抓住
        「偷偷多导出一个」。）
        """
        import freegraph.contracts as contracts

        existing, new = parse_public_api_symbols(repo_root / PUBLIC_API_MANIFEST)
        expected = set(existing) | set(new)
        violations = g7_equality_violations(set(contracts.__all__), expected)
        assert violations == [], (
            f"``__all__`` 与 §0 清单的差集（对称差）MUST 为空：{violations}"
        )

    def test_all_is_a_subset_of_the_manifest(self, repo_root: Path) -> None:
        """**子集段**（始终启用）——``__all__`` ⊆ §0 解析出的 18 个。

        抓住「偷偷多导出一个」；构造期 ``__all__`` 尚未齐全时恒成立。
        """
        import freegraph.contracts as contracts

        existing, new = parse_public_api_symbols(repo_root / PUBLIC_API_MANIFEST)
        violations = g7_subset_violations(
            set(contracts.__all__), set(existing) | set(new)
        )
        assert violations == [], f"``__all__`` 含清单外的符号：{violations}"

    def test_every_exported_name_is_gettable(self) -> None:
        """``__all__`` 里的每个名字 MUST 能从 ``freegraph.contracts`` 直接取到。

        （「清单里的 18 个**全部**已导出」那条断言属 G7 的**集合相等段**——
        在 18 个符号全部导出后启用。）
        """
        import freegraph.contracts as contracts

        for name in contracts.__all__:
            assert getattr(contracts, name, None) is not None, name

    def test_no_send_or_interrupt_public_symbol(self) -> None:
        """契约层 MUST NOT 出现名为 ``Send`` / ``interrupt`` 的公开符号。

        （归 **v2**：B11F1 / B10F1；本 feature **不导出**。）
        """
        import freegraph.contracts as contracts

        assert not hasattr(contracts, "Send")
        assert not hasattr(contracts, "interrupt")

    def test_no_send_or_interrupt_defined_in_the_package(self) -> None:
        """契约层**任何**模块内都不得定义 ``Send`` / ``interrupt``。"""
        import freegraph.contracts as contracts

        package_dir = Path(contracts.__file__).parent
        for path in sorted(package_dir.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                names: list[str] = []
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    names.append(node.name)
                elif isinstance(node, ast.Assign):
                    names.extend(
                        t.id for t in node.targets if isinstance(t, ast.Name)
                    )
                elif isinstance(node, ast.AnnAssign) and isinstance(
                    node.target, ast.Name
                ):
                    names.append(node.target.id)
                for name in names:
                    assert name not in {"Send", "interrupt"}, f"{path.name}: {name}"


# ── G3 · 依赖闭包 + 许可证白名单 ───────────────────────────────────────

#: 宪法依赖白名单（**必装依赖 = 无**；可选 extras 由 B3F1 引入）。
#:
#: ``typing-extensions`` 已于宪法 **v1.2.0** 从必装依赖剥离——最低 Python 版本
#: 抬至 3.11 后，``Self`` / ``NotRequired`` / ``Required`` / ``TypeVarTuple`` /
#: ``Unpack`` / ``LiteralString`` / ``dataclass_transform`` 全部进入标准库。
#:
#: **B3F1 填充实测闭包（tasks T003 · 裁定 8 的唯一一处例外 · 判据句零改动）**：
#: 下面是**四个 extra 的完整递归闭包**的**确切包名集合**（**12 个**）——
#: 有限 · 逐个列名 · **无通配符 · 无前缀匹配**（research D-02 / D-06 实测）。
#: 方向 = **更精确**（原为 4 个宽泛占位包名）⇒ 净效果**变严**（FR-018）。
#:
#: **⚠️ 版本敏感性**：extras 的版本约束是**开区间**（``pydantic>=2.0``）⇒ 上游**新增一个
#: 传递依赖**即会让闭包多出一个包名 ⇒ 白名单失配 ⇒ CI 变红。
#: ⇒ 复核的**双触发点**：① **extras 的版本约束变更**（``[project.optional-dependencies]``
#: 任一条变更）· ② **CI 因闭包失配而红**（本条子集断言失败）—— **二者任一**发生即 MUST
#: **重跑闭包实测**并追认更新白名单（**MUST NOT** 以「放宽白名单让它变绿」的方式绕过 ·
#: FR-018；白名单的扩充只能走宪法修订）。
CONSTITUTION_DEPENDENCY_WHITELIST = {
    "annotated-types",
    "greenlet",
    "opentelemetry-api",
    "opentelemetry-sdk",
    "opentelemetry-semantic-conventions",
    "ormsgpack",
    "playwright",
    "pydantic",
    "pydantic-core",
    "pyee",
    "typing-extensions",
    "typing-inspection",
}

#: 许可证白名单（宪法质量门禁第 2 条）。
ALLOWED_LICENSE_TOKENS = (
    "MIT",
    "APACHE-2.0",
    "BSD-2-CLAUSE",
    "BSD-3-CLAUSE",
    "PSF",
)

#: 传染性 / 限制性许可证（宪法原则 IX —— 一律禁止）。
FORBIDDEN_LICENSE_TOKENS = ("AGPL", "SSPL", "BUSL", "ELASTIC", "GPL-3", "GPL-2")


def _split_requires(specs: list[str] | None) -> list[tuple[str, bool]]:
    """拆 ``Requires-Dist``：返回 ``(名字, 是否带 extras 条件)``。"""
    out: list[tuple[str, bool]] = []
    for spec in specs or []:
        head, _, marker = spec.partition(";")
        name = head.split("[")[0].split(">")[0].split("<")[0].split("=")[0].strip()
        out.append((name, "extra ==" in marker))
    return out


def dependency_closure(
    pkg: str, seen: set[str] | None = None, with_extras: bool = False
) -> set[str]:
    """递归展开依赖闭包。

    ``with_extras=False`` 时**剥离 extras marker**（否则基础安装的闭包
    会被可选依赖污染）。

    **B3F1 修正枚举语义（tasks T003 · 裁定 8 的唯一一处例外 · 判据句零改动）**：
    ``with_extras=True`` 时**只枚举 freegraph 自身的 extras 变体**——
    **传递依赖一律按其「基础依赖」展开**（**不**展开传递依赖自己的 extras）。
    理由：extra 是「**freegraph 对用户的承诺**」，不是「传递依赖的私有细节」
    （dependency-gate.md §2.3）。
    修正前的语义会把 ``pydantic`` 的 ``email`` extra 拉进闭包（过近似）⇒
    闭包多出 ``email-validator`` 等**不在**白名单内的包名 ⇒ 子集断言变红。
    方向 = **更正确** ⇒ 净效果**变严**（FR-018）。
    """
    seen = seen if seen is not None else set()
    for name, is_extra in _split_requires(requires(pkg)):
        if is_extra and not with_extras:
            continue
        key = name.lower().replace("_", "-")
        if key in seen:
            continue
        seen.add(key)
        try:
            # 传递依赖**只展开其基础依赖** ⇒ 递归时不带 extras 标志。
            dependency_closure(name, seen, False)
        except Exception:  # noqa: BLE001 —— 未安装的依赖无元数据，跳过即可
            pass
    return seen


def _license_of(pkg: str) -> str | None:
    """取包的许可证字符串；取不到返回 ``None``。"""
    try:
        meta = metadata(pkg)
    except PackageNotFoundError:
        return None
    for key in ("License-Expression", "License"):
        value = meta.get(key)
        if value and value.strip() and value.strip().upper() != "UNKNOWN":
            return value.strip()
    return None


def _require_installed() -> None:
    """freegraph 未安装（无 dist-info 元数据）时该门禁 MUST ``skip`` 而非失败。"""
    try:
        metadata("freegraph")
    except PackageNotFoundError:
        pytest.skip(
            "freegraph 未安装（无 dist-info 元数据）——依赖闭包门禁须在"
            "隔离环境执行（见 quickstart.md §2.2 / T023）"
        )


class TestDependencyClosure:
    """G3 · 依赖闭包：基础安装**为空**（零第三方运行时依赖，SC-002）。"""

    def test_base_install_closure_is_empty(self) -> None:
        """基础安装（剥离 extras marker）的闭包 MUST 是**空集**。

        这是「零第三方运行时依赖」这条对外承诺的**可判定形式**——
        ``pip install freegraph`` 后 site-packages 里只有 freegraph 自己。
        """
        _require_installed()
        base = dependency_closure("freegraph")
        assert base == set(), base

    def test_base_install_closure_has_no_langchain_family(self) -> None:
        """闭包 MUST NOT 出现 ``langsmith`` / ``langchain*`` / ``langgraph*``。

        （``langchain-core`` 硬依赖 ``langsmith``，故二者是同一条红线。）
        """
        _require_installed()
        base = dependency_closure("freegraph")
        for forbidden in (
            "langsmith",
            "langchain",
            "langchain-core",
            "langgraph",
            "langgraph-core",
        ):
            assert forbidden not in base

    def test_base_install_requires_no_typing_extensions(self) -> None:
        """基础安装 MUST NOT 依赖 ``typing_extensions``。

        （宪法 v1.2.0：该包已从必装依赖剥离——最低 Python 抬至 3.11 后不需要。）
        """
        _require_installed()
        base = dependency_closure("freegraph")
        assert "typing-extensions" not in base
        assert "typing_extensions" not in base

    def test_extras_closure_is_within_constitution_whitelist(self) -> None:
        """extras 变体闭包 MUST 只含宪法依赖白名单内的包。

        （extras 由 B3F1 引入——**该条在 B3F1 起变为实质断言**。）
        """
        _require_installed()
        base = dependency_closure("freegraph")
        extras = dependency_closure("freegraph", with_extras=True) - base
        assert extras <= CONSTITUTION_DEPENDENCY_WHITELIST, extras

    def test_closure_licenses_are_in_whitelist(self) -> None:
        """闭包内每个包的许可证 MUST ∈ 白名单；MUST NOT 出现传染性许可证。

        取不到许可证信息时该断言 ``skip`` 并提示——不得默认「闭包小就安全」。

        **基础安装闭包为空**（零第三方依赖），**extras 闭包非空**——
        extras 由 **B3F1** 引入 ⇒ 该断言自 B3F1 起为**实质断言**
        （前提：四个 extras 的依赖已安装 · 契约 ci-matrix §2 步骤 5.5）。
        """
        _require_installed()
        base = dependency_closure("freegraph")
        extras = dependency_closure("freegraph", with_extras=True) - base
        missing: list[str] = []
        licenses: dict[str, str] = {}
        for pkg in sorted(base | extras):
            lic = _license_of(pkg)
            if lic is None:
                missing.append(pkg)
            else:
                licenses[pkg] = lic
        if missing:
            pytest.skip(f"取不到以下包的许可证信息，跳过许可证白名单断言：{missing}")
        for pkg, lic in licenses.items():
            upper = lic.upper()
            assert any(token in upper for token in ALLOWED_LICENSE_TOKENS), (
                f"{pkg} 的许可证 {lic!r} 不在白名单内"
            )
            assert not any(token in upper for token in FORBIDDEN_LICENSE_TOKENS), (
                f"{pkg} 的许可证 {lic!r} 是传染性 / 限制性许可证"
            )


# ── G9 · 运行时环境基线（Python 版本与 typing 构件上限）─────────────────

#: 3.12+ / 3.13+ 才进入标准库的 typing 构件 —— 宪法「运行时环境基线」明令禁用。
#:
#: 依据：宪法修订记录 **v1.3.0**（新增「运行时环境基线」章节）。
#: 实测：CPython 3.11 的 ``typing`` **没有**这四个；3.12 才有 ``TypeAliasType`` 与
#: ``override``，3.13 才加 ``ReadOnly`` 与 ``TypeIs``。
FORBIDDEN_TYPING_CONSTRUCTS = {
    "TypeAliasType": "3.12",
    "ReadOnly": "3.13",
    "TypeIs": "3.13",
}

#: ``override`` 只在**装饰器用法 / 显式导入**时才算 3.12+ 构件——
#: 一个叫 ``override`` 的普通方法名是合法 Python，不是新构件（避免误报）。
FORBIDDEN_DECORATOR_ONLY = {"override": "3.12"}


def scan_runtime_baseline(package_dir: Path) -> list[str]:
    """G9 · 扫描源码，报告使用了 3.12+ / 3.13+ typing 构件的位置。

    这是个**纯函数**——只吃一个目录、只吐一个列表，故门禁自检可以喂它
    造出来的违规目录，证明门禁本身有效。

    判定口径（宪法「运行时环境基线」）：
      ① 显式导入 / 名字引用：``TypeAliasType`` / ``ReadOnly`` / ``TypeIs``；
      ② 装饰器用法：``@override`` / ``@typing.override``；
      ③ **PEP 695 语法**（``type X = ...`` / ``class C[T]`` / ``def f[T]()``）——
         在 3.11 上连解析都过不了，故用 ``SyntaxError`` 捕获并给出可读报错，
         而不是让开发者对着一个 ``ImportError`` 猜原因。
    """
    violations: list[str] = []
    type_alias_node = getattr(ast, "TypeAlias", None)
    for path in sorted(Path(package_dir).rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            violations.append(
                f"{path.name}:{exc.lineno}: 在 Python 3.11 上无法解析 —— "
                f"疑为 3.12+ 语法（PEP 695 `type` 语句 / 泛型参数）：{exc.msg}"
            )
            continue
        for node in ast.walk(tree):
            if type_alias_node is not None and isinstance(node, type_alias_node):
                violations.append(
                    f"{path.name}:{getattr(node, 'lineno', '?')}: "
                    "PEP 695 `type` 语句（3.12+）"
                )
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if getattr(node, "type_params", None):
                    violations.append(
                        f"{path.name}:{node.lineno}: PEP 695 泛型语法（3.12+）"
                    )
                for deco in node.decorator_list:
                    deco_name = None
                    if isinstance(deco, ast.Name):
                        deco_name = deco.id
                    elif isinstance(deco, ast.Attribute):
                        deco_name = deco.attr
                    if deco_name in FORBIDDEN_DECORATOR_ONLY:
                        version = FORBIDDEN_DECORATOR_ONLY[deco_name]
                        violations.append(
                            f"{path.name}:{node.lineno}: 禁用了 @{deco_name}"
                            f"（{version} 才进标准库）"
                        )
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in FORBIDDEN_TYPING_CONSTRUCTS:
                        version = FORBIDDEN_TYPING_CONSTRUCTS[alias.name]
                        violations.append(
                            f"{path.name}:{node.lineno}: 禁用了 {alias.name}"
                            f"（{version} 才进标准库）"
                        )
                    elif alias.name in FORBIDDEN_DECORATOR_ONLY:
                        version = FORBIDDEN_DECORATOR_ONLY[alias.name]
                        violations.append(
                            f"{path.name}:{node.lineno}: 禁用了 {alias.name}"
                            f"（{version} 才进标准库）"
                        )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in FORBIDDEN_TYPING_CONSTRUCTS:
                        version = FORBIDDEN_TYPING_CONSTRUCTS[root]
                        violations.append(
                            f"{path.name}:{node.lineno}: 禁用了 {root}"
                            f"（{version} 才进标准库）"
                        )
            elif isinstance(node, ast.Name):
                if node.id in FORBIDDEN_TYPING_CONSTRUCTS:
                    version = FORBIDDEN_TYPING_CONSTRUCTS[node.id]
                    violations.append(
                        f"{path.name}:{node.lineno}: 禁用了 {node.id}"
                        f"（{version} 才进标准库）"
                    )
            elif isinstance(node, ast.Attribute):
                if node.attr in FORBIDDEN_TYPING_CONSTRUCTS:
                    version = FORBIDDEN_TYPING_CONSTRUCTS[node.attr]
                    violations.append(
                        f"{path.name}:{node.lineno}: 禁用了 {node.attr}"
                        f"（{version} 才进标准库）"
                    )
    return violations


class TestRuntimeBaseline:
    """G9 · 运行时环境基线 —— 最低 Python 3.11，typing 构件不得高于 3.11。"""

    def test_no_newer_typing_constructs(self, src_dir: Path) -> None:
        """源码 MUST NOT 使用 3.12+ / 3.13+ 的 typing 构件。

        扫描器以 ``rglob("*.py")`` **递归**覆盖 ``src/freegraph/**``——
        本 feature 新增的 ``protocols.py`` / ``graph.py`` / ``trace.py``
        自动落在范围内（``Protocol`` / ``runtime_checkable`` / ``dataclass``
        / ``Mapping`` / ``Sequence`` / ``Iterator`` 全部 ≤ 3.11）。
        """
        violations = scan_runtime_baseline(src_dir / "freegraph")
        assert violations == [], "\n".join(violations)

    def test_interpreter_is_at_least_3_11(self) -> None:
        """运行本门禁的解释器 MUST ≥ 3.11（否则本门禁本身失去意义）。"""
        assert sys.version_info >= (3, 11), (
            f"本门禁须在 Python ≥ 3.11 上运行（当前 {sys.version.split()[0]}）"
        )

    def test_requires_python_declares_3_11(self, repo_root: Path) -> None:
        """``pyproject.toml`` 的 ``requires-python`` MUST 保持 ``>=3.11``。"""
        text = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
        assert 'requires-python = ">=3.11"' in text, (
            "requires-python MUST 为 \">=3.11\"（宪法「运行时环境基线」）"
        )

    def test_allowed_3_11_constructs_are_available(self) -> None:
        """3.11 确实提供了这些构件 —— 本门禁的上限**恰好**卡在 3.11。

        （若将来某个构件在 3.11 不可用，本断言会先于源码扫描失败，
        提醒「上限口径需重新评估」。）
        """
        import typing

        for name in (
            "Self",
            "NotRequired",
            "Required",
            "TypeVarTuple",
            "Unpack",
            "LiteralString",
            "dataclass_transform",
        ):
            assert hasattr(typing, name), f"typing.{name} 在 3.11 上不可用"


# ── G8 · 文档合规门禁 ──────────────────────────────────────────────────

#: README「API 兼容矩阵」章节的定位正则。
#:
#: 该章节是 README 的**最后一个** ``##`` 章节，其后没有下一个 ``##``——
#: 用 ``^## `` 收尾会**匹配失败**，故用 ``(?=^## |\Z)``。
COMPAT_MATRIX_PATTERN = re.compile(
    r"^## API 兼容矩阵\s*$(.*?)(?=^## |\Z)", re.S | re.M
)

#: 原则 IX 的第三方商标禁令声明（README **顶部**，落在矩阵章节**之外**）。
INDEPENDENCE_STATEMENT = "独立实现、非 LangChain Inc. 产品"


def _compat_matrix_section(readme: str) -> str:
    """取出 README「## API 兼容矩阵」章节的正文（**不扫全文**）。"""
    match = COMPAT_MATRIX_PATTERN.search(readme)
    assert match, "README.md 缺少「## API 兼容矩阵」章节"
    return match.group(1)


def _compat_matrix_rows(readme: str) -> list[tuple[str, list[str]]]:
    """取出兼容矩阵的**数据行** → ``[(符号, 单元格列表), ...]``。

    取行范围 = 章节内；只取首列是 ``| `符号` |`` 形态的行（表头与分隔行不含反引号）。
    """
    rows: list[tuple[str, list[str]]] = []
    for line in _compat_matrix_section(readme).splitlines():
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


def _notices_dependency_table_rows(notices: str) -> list[str]:
    """提取 ``THIRD_PARTY_NOTICES`` §2「第三方运行时依赖」表的**数据行**。

    只取**登记了包名**的行——表头行、分隔行与「（暂无条目）」占位行均**不算**。
    这样章节正文里对剥离历史的**说明性**提及不会造成假阳性。
    """
    section = re.search(r"^##\s*2\..*?(?=^##\s|\Z)", notices, re.S | re.M)
    assert section, "THIRD_PARTY_NOTICES 缺少「## 2. 第三方运行时依赖」章节"
    rows: list[str] = []
    for line in section.group(0).splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if re.match(r"^\|[\s\-|:]+\|$", stripped):  # 分隔行
            continue
        if stripped.startswith("| 包 "):  # 表头行
            continue
        if "（暂无条目）" in stripped:  # 空表占位行
            continue
        rows.append(stripped)
    return rows


class TestDocumentationCompliance:
    """G8 · 兼容矩阵逐符号覆盖 + ``THIRD_PARTY_NOTICES`` 已登记。"""

    def test_third_party_notices_exists(self, repo_root: Path) -> None:
        """仓库根 MUST 有 ``THIRD_PARTY_NOTICES``。"""
        assert (repo_root / "THIRD_PARTY_NOTICES").is_file()

    def test_readme_has_compat_matrix_section(self, repo_root: Path) -> None:
        """README MUST 有「## API 兼容矩阵」章节。"""
        readme = (repo_root / "README.md").read_text(encoding="utf-8")
        match = COMPAT_MATRIX_PATTERN.search(readme)
        assert match, "README.md 缺少「## API 兼容矩阵」章节"

    def test_compat_matrix_rows_are_within_the_manifest(
        self, repo_root: Path
    ) -> None:
        """**子集段**（始终启用）——契约层的 18 个符号 MUST **至多一行**。

        （抓「重复 / 超量」。矩阵**整体无重复行**是更一般的判据，一并断言。）

        **口径修订（2026-11-07 · B2F2）**：兼容矩阵自 **B2F2** 起**同时**承载
        **契约层 18 个**与**门面层 7 个**符号 ⇒「矩阵首列符号集合 **==** 契约层
        18 个」这一**整表**判据**不再成立**。本门禁的判定因此**按层收敛到
        契约层**——B2F2 的门禁契约声明本门禁的范围**正是**「契约层 18 个符号」
        （门面层 7 个符号的覆盖由门禁 **G19** 判，两者的**分工不重叠**）；
        整表的「无清单外符号」由 **G19** 一并判。
        **契约层的任何一条判据都未被削弱**——「不多」（本段）与「不少」
        （集合相等段）两条全部保留。
        """
        readme = (repo_root / "README.md").read_text(encoding="utf-8")
        existing, new = parse_public_api_symbols(repo_root / PUBLIC_API_MANIFEST)
        allowed = set(existing) | set(new)
        rows = _compat_matrix_rows(readme)
        names = [name for name, _ in rows]
        assert len(names) == len(set(names)), f"矩阵存在重复行：{names}"
        counts = Counter(names)
        over = sorted(name for name in allowed if counts[name] > 1)
        assert not over, f"契约层符号在矩阵中出现多行：{over}"

    def test_compat_matrix_rows_have_three_columns(self, repo_root: Path) -> None:
        """每行 MUST 含「对应上游符号 / 等价程度 / 差异说明」三列。

        （矩阵**保持 4 列**——既有 8 行逐字不动 ⇒ 不可为来源单开一列。）
        """
        readme = (repo_root / "README.md").read_text(encoding="utf-8")
        for name, cells in _compat_matrix_rows(readme):
            assert len(cells) >= 4, (
                f"矩阵行 {name} 的列数不足 4（期望：符号 / 上游 / 等价程度 / 差异说明），"
                f"实得 {len(cells)}"
            )

    def test_new_rows_declare_upstream_source_or_no_upstream(
        self, repo_root: Path
    ) -> None:
        """**新增行**的上游来源 MUST 合规——有上游同名符号者附来源行号。

        **无上游同名符号者**（``NodeFunc`` / ``TraceSink`` / ``Span`` /
        ``TraceQuery``）MUST 写「无上游对应」+ 契约条目号，**MUST NOT** 硬凑行号。

        （既有 8 行按 FR-017 **逐字不动** ⇒ 不要求行内来源行号。）
        """
        readme = (repo_root / "README.md").read_text(encoding="utf-8")
        _, new = parse_public_api_symbols(repo_root / PUBLIC_API_MANIFEST)
        new_set = set(new)
        for name, cells in _compat_matrix_rows(readme):
            if name not in new_set:
                continue
            row = " | ".join(cells)
            if name in NO_UPSTREAM_SYMBOLS:
                assert "无上游对应" in row, (
                    f"矩阵行 {name} 无上游同名符号，MUST 写「无上游对应」+ 契约条目号"
                )
            else:
                assert re.search(r"[\w/]+\.py:\d+", row), (
                    f"矩阵行 {name} 有上游同名符号，MUST 在「差异说明」单元格末尾"
                    "附上游来源行号（`路径:行号`）"
                )

    def test_compat_matrix_covers_every_manifest_symbol(self, repo_root: Path) -> None:
        """**集合相等段** —— 契约层的 18 个符号 MUST 在矩阵中**全部齐备**。

        （README 已补入本层 10 行 ⇒ 该段自此启用；抓「漏写」。）

        **口径修订（2026-11-07 · B2F2）**：矩阵自 **B2F2** 起同时承载**门面层**
        的 7 个符号 ⇒ 整表集合相等判据改为**按层**判定（契约层 18 个**齐备**
        + 整表符号集合由门禁 **G19** 判）。
        """
        readme = (repo_root / "README.md").read_text(encoding="utf-8")
        existing, new = parse_public_api_symbols(repo_root / PUBLIC_API_MANIFEST)
        rows = [name for name, _ in _compat_matrix_rows(readme)]
        missing = sorted((set(existing) | set(new)) - set(rows))
        assert not missing, f"矩阵缺契约层符号：{missing}"

    def test_compat_matrix_declares_no_affiliation(self, repo_root: Path) -> None:
        """矩阵章节 MUST 含「不构成 affiliation」字样（宪法原则 IX）。"""
        readme = (repo_root / "README.md").read_text(encoding="utf-8")
        assert "不构成 affiliation" in _compat_matrix_section(readme)

    def test_readme_contains_independence_statement(self, repo_root: Path) -> None:
        """README **全文** MUST 含「独立实现、非 LangChain Inc. 产品」。

        （该声明按 T020 放在 README **顶部**、落在矩阵章节**之外**，
        故不能靠上面的章节解析覆盖，必须扫全文。）
        """
        readme = (repo_root / "README.md").read_text(encoding="utf-8")
        assert INDEPENDENCE_STATEMENT in readme

    def test_third_party_notices_registers_no_runtime_dependency(
        self, repo_root: Path
    ) -> None:
        """``THIRD_PARTY_NOTICES`` 的「第三方运行时依赖」表 MUST 反映**实际**依赖。

        基础安装**零第三方运行时依赖**（宪法 v1.2.0），故该表 MUST NOT 登记任何
        必装依赖——原则 X 的登记义务是「登记**实际存在**的依赖」，
        登记一个已剥离的包同样是登记不准。

        判定只看**表格的数据行**（登记了包名的行）——章节正文里对剥离历史的
        **说明性**提及是允许的（原则 VIII 的证据纪律要求把变更写清楚）。
        """
        rows = _notices_dependency_table_rows(
            (repo_root / "THIRD_PARTY_NOTICES").read_text(encoding="utf-8")
        )
        assert rows == [], f"依赖登记表应为空，却登记了：{rows}"

    def test_third_party_notices_dependency_table_has_no_data_row(
        self, repo_root: Path
    ) -> None:
        """「第三方运行时依赖」表 MUST NOT 有登记了包名的数据行。"""
        rows = _notices_dependency_table_rows(
            (repo_root / "THIRD_PARTY_NOTICES").read_text(encoding="utf-8")
        )
        for row in rows:
            assert "typing-extensions" not in row
            assert "typing_extensions" not in row

    def test_third_party_notices_has_registration_sections(self, repo_root: Path) -> None:
        """``THIRD_PARTY_NOTICES`` MUST 四段齐全（代码归属 / 依赖 / 声明 / 规则）。"""
        notices = (repo_root / "THIRD_PARTY_NOTICES").read_text(encoding="utf-8")
        for heading in (
            "## 1.",
            "## 2.",
            "## 3.",
            "## 4.",
        ):
            assert heading in notices, f"THIRD_PARTY_NOTICES 缺少「{heading}」章节"


# ── G10 · 协议纯抽象 ───────────────────────────────────────────────────


class TestProtocolsArePurelyAbstract:
    """G10 · 协议纯抽象 —— 方法体**只有** ``...``。"""

    def test_protocol_methods_have_ellipsis_body_only(
        self, contracts_dir: Path
    ) -> None:
        """``protocols.py`` 的协议类 MUST NOT 有任何默认实现。

        （默认实现会让「只声明部分方法」的假实现**静默通过**结构化子类型
        判定，把「缺实现」这一真实缺陷掩盖到运行时。）
        """
        violations = scan_protocol_abstractness(contracts_dir / "protocols.py")
        assert violations == [], "\n".join(violations)


# ── G11 / G13 · 结构化子类型判定 + 纯数据纪律 ──────────────────────────


class TestStructuredSubtyping:
    """G11 · 结构化子类型判定可用（完整实现真 / 缺方法假）。"""

    def test_all_five_protocols_support_isinstance(self) -> None:
        """五个协议 MUST 均可做 ``isinstance`` 判定（``runtime_checkable`` 生效）。"""
        import freegraph.contracts as contracts

        for name in (
            "NodeFunc",
            "Checkpointer",
            "TraceSink",
            "Store",
            "CompiledGraph",
        ):
            protocol = getattr(contracts, name)
            assert getattr(protocol, "_is_runtime_protocol", False), name

    def test_complete_implementations_are_accepted(self) -> None:
        """夹具的**完整实现** MUST 逐个判**真**。"""
        import freegraph.contracts as contracts
        from fixtures.external_impl import (
            InMemoryCheckpointer,
            InMemoryStore,
            RecordingTraceSink,
        )

        assert isinstance(InMemoryCheckpointer(), contracts.Checkpointer)
        assert isinstance(RecordingTraceSink(), contracts.TraceSink)
        assert isinstance(InMemoryStore(), contracts.Store)

    def test_partial_implementations_are_rejected(self) -> None:
        """缺**任一**方法的实现 MUST 逐个判**假**。"""
        import freegraph.contracts as contracts
        from fixtures.external_impl import (
            make_partial_checkpointer,
            make_partial_store,
            make_partial_trace_sink,
        )

        for missing in (
            "get_tuple",
            "list",
            "put",
            "put_writes",
            "delete_thread",
            "get_next_version",
        ):
            assert not isinstance(
                make_partial_checkpointer(missing), contracts.Checkpointer
            )
        for missing in ("on_span_start", "on_span_end", "current_span"):
            assert not isinstance(
                make_partial_trace_sink(missing), contracts.TraceSink
            )
        for missing in (
            "get",
            "search",
            "put",
            "delete",
            "list_namespaces",
            "batch",
        ):
            assert not isinstance(make_partial_store(missing), contracts.Store)


class TestPureDataDiscipline:
    """G13 · 纯数据纪律 —— 数据类字段不得含对象引用 / 可调用类型。"""

    def test_five_data_classes_obey_the_whitelist(self) -> None:
        """五个纯数据类的字段类型 MUST 全部落在白名单之内。"""
        import freegraph.contracts as contracts

        pure_data_classes = (
            contracts.Graph,
            contracts.Node,
            contracts.Edge,
            contracts.Span,
            contracts.TraceQuery,
        )
        for cls in pure_data_classes:
            violations = scan_pure_data_discipline(cls, pure_data_classes)
            assert violations == [], "\n".join(violations)

    def test_mapping_value_position_is_the_only_any(self) -> None:
        """``Any`` MUST 只出现在 ``Mapping[str, Any]`` 的**值位**。"""
        import freegraph.contracts as contracts

        for cls in (contracts.Node, contracts.Span):
            for name, annotation in get_type_hints(cls).items():
                if get_origin(annotation) is not Mapping:
                    assert annotation is not Any, f"{cls.__name__}.{name}"


class TestPublicSymbolAnnotations:
    """SC-010 / FR-012 · 公开符号面 **18 个符号**的注解 MUST 可被完整解析。"""

    def test_all_eighteen_symbols_have_resolvable_annotations(
        self, repo_root: Path
    ) -> None:
        """18 个符号逐一解析——无未解析的字符串注解、无解析异常。

        （协议取其**方法**注解；数据类取其**字段**注解；类型别名与异常类
        取其自身可解析的部分。）
        """
        import freegraph.contracts as contracts

        existing, new = parse_public_api_symbols(repo_root / PUBLIC_API_MANIFEST)
        symbols = existing + new
        assert len(symbols) == 18

        for name in symbols:
            symbol = getattr(contracts, name)
            for annotation in _symbol_annotations(symbol):
                assert not isinstance(annotation, str), (
                    f"{name} 存在**未解析**的字符串注解：{annotation!r}"
                )

    def test_annotations_of_the_new_symbols_resolve(self) -> None:
        """本 feature 新增的 10 个符号 MUST 全部可解析（逐个点名）。"""
        import freegraph.contracts as contracts

        for name in sorted(FR012_NEW_SYMBOLS):
            symbol = getattr(contracts, name)
            annotations = list(_symbol_annotations(symbol))
            assert annotations, name
            for annotation in annotations:
                assert not isinstance(annotation, str), (
                    f"{name} 存在**未解析**的字符串注解：{annotation!r}"
                )


def _protocol_method_names(proto: type) -> list[str]:
    """列出协议类的**方法名**（**跨 Python 版本**稳定）。

    ``Protocol.__protocol_attrs__`` **只在 Python 3.12+ 存在**（3.11 没有）
    ⇒ 不能依赖它，否则本断言在 **3.11 最低档**恒失败（协议方法取不到注解）。
    改为从类的 ``__dict__`` 里取**公开**的可调用成员（``__call__`` 例外——
    ``NodeFunc`` 的唯一成员就是它）。
    """
    return sorted(
        name
        for name, value in vars(proto).items()
        if (not name.startswith("_") or name == "__call__") and callable(value)
    )


def _symbol_annotations(symbol: Any) -> list[Any]:
    """取一个公开符号的**全部注解**（协议取方法注解，数据类取字段注解）。"""
    annotations: list[Any] = []
    if isinstance(symbol, type) and issubclass(symbol, Exception):
        return annotations
    if isinstance(symbol, type) and getattr(symbol, "_is_protocol", False):
        for method_name in _protocol_method_names(symbol):
            annotations.extend(get_type_hints(getattr(symbol, method_name)).values())
        return annotations
    if isinstance(symbol, type):
        annotations.extend(get_type_hints(symbol).values())
        return annotations
    # 类型别名（如 ``StateDict`` = ``dict[str, Any]``）
    annotations.extend(get_args(symbol))
    return annotations


# ── G12 · 公开符号面唯一权威 ───────────────────────────────────────────

#: 权威清单的**机器标记**——判定**只认标记**，不看字样。
#:
#: B1F1 的同名文件作为**历史快照**保留，其正文仍含「唯一手工维护点」
#: 「权威来源」等**字样**——用关键词判定会把它误计为权威（数出 2 个），
#: 门禁恒失败。故判定只认机器标记，字样仅供人读。
AUTHORITY_MARKER = re.compile(r"<!--\s*authority:\s*(yes|no)\s*-->")

#: 权威清单的文件名（G12 扫的是 ``**/public-api.md``）。
AUTHORITY_FILENAME = "public-api.md"


def scan_authoritative_manifests(repo_root: Path) -> tuple[list[Path], list[Path]]:
    """扫描仓库内的 ``**/public-api.md`` → ``(权威清单, 缺标记清单)``。

    读取每个文件的**首行附近**（前 400 字符）的机器标记
    ``<!-- authority: yes -->`` / ``<!-- authority: no -->``。

    **标记缺失**时按「非权威」处理，并回报该文件（MUST NOT 静默通过）。
    """
    authoritative: list[Path] = []
    unmarked: list[Path] = []
    for path in sorted(repo_root.rglob(AUTHORITY_FILENAME)):
        head = path.read_text(encoding="utf-8")[:400]
        match = AUTHORITY_MARKER.search(head)
        if match is None:
            unmarked.append(path)
            continue
        if match.group(1) == "yes":
            authoritative.append(path)
    return authoritative, unmarked


class TestUniqueAuthorityManifest:
    """G12 · 公开符号面**唯一权威**（机器标记）。"""

    def test_exactly_one_authoritative_manifest(self, repo_root: Path) -> None:
        """标记为 ``yes`` 的清单文件 MUST **恰为 1 个**。"""
        authoritative, _ = scan_authoritative_manifests(repo_root)
        assert len(authoritative) == 1, (
            f"标记为权威的清单文件 MUST 恰为 1 个，实得 {len(authoritative)} 个："
            f"{[str(p.relative_to(repo_root)) for p in authoritative]}"
        )

    def test_the_authoritative_manifest_is_b2f1(self, repo_root: Path) -> None:
        """权威清单 MUST 是 B2F1 的 ``contracts/public-api.md``。"""
        authoritative, _ = scan_authoritative_manifests(repo_root)
        assert len(authoritative) == 1
        relative = authoritative[0].relative_to(repo_root).as_posix()
        assert relative == PUBLIC_API_MANIFEST.as_posix(), relative

    def test_every_manifest_carries_the_machine_marker(self, repo_root: Path) -> None:
        """每个清单文件 MUST 带机器标记（缺失即报错并点名该文件）。"""
        _, unmarked = scan_authoritative_manifests(repo_root)
        assert not unmarked, [
            f"{p.relative_to(repo_root).as_posix()} 缺少 "
            "<!-- authority: yes --> / <!-- authority: no --> 机器标记"
            for p in unmarked
        ]

    def test_b1f1_manifest_is_marked_non_authoritative(self, repo_root: Path) -> None:
        """B1F1 的同名文件 MUST 标记为 ``no``（历史快照）。"""
        legacy = repo_root / "specs" / "b1f1-contracts-core" / "contracts" / AUTHORITY_FILENAME
        assert legacy.is_file(), f"缺少 B1F1 的历史快照文件：{legacy}"
        head = legacy.read_text(encoding="utf-8")[:400]
        match = AUTHORITY_MARKER.search(head)
        assert match is not None, "B1F1 的清单文件缺少机器标记"
        assert match.group(1) == "no", "B1F1 的清单文件 MUST 标记为 authority: no"


# ── 门禁自检 ───────────────────────────────────────────────────────────


class TestGateSelfCheck:
    """门禁自检 —— 刻意引入违规改动，断言门禁**确实报出**。

    US3 验收场景 4：「刻意引入违规改动 → 断言失败并阻断合入」。
    若只断言「真实目录无违规」，则「门禁恰好没触发」与「门禁有效」不可区分——
    故这里必须**喂进违规目录**证明每条判定各自有效。
    """

    @staticmethod
    def _make_layer(root: Path, filename: str, source: str) -> Path:
        layer = root
        layer.mkdir(parents=True, exist_ok=True)
        (layer / filename).write_text(source, encoding="utf-8")
        return layer

    def test_third_party_import_is_detected(self, tmp_path: Path) -> None:
        """① 第三方 import MUST 被抓出，且**不**误报为内部 import。"""
        layer = self._make_layer(
            tmp_path / "third_party",
            "mod.py",
            "from langchain_core.runnables import RunnableConfig\n",
        )
        violations = scan_third_party_imports([layer])
        assert violations, "第三方 import 未被抓出"
        assert any("第三方 import" in v and "langchain_core" in v for v in violations)
        assert not any("内部模块 import" in v for v in violations)

    def test_internal_import_is_detected(self, tmp_path: Path) -> None:
        """② 内部 import MUST 被抓出，且**不**误报为第三方 import。

        （① 与内部导入须**分别验证**，否则无法证明两条判定各自有效。）
        """
        layer = self._make_layer(
            tmp_path / "internal",
            "mod.py",
            "from freegraph.runtime import X\n",
        )
        violations = scan_internal_imports([layer])
        assert violations, "内部 import 未被抓出"
        assert any("内部模块 import" in v and "freegraph.runtime" in v for v in violations)
        assert not any("第三方 import" in v for v in violations)

    def test_package_escaping_relative_import_is_detected(self, tmp_path: Path) -> None:
        """② 包外相对导入（``from ..runtime import X``）MUST 被抓出。"""
        layer = self._make_layer(
            tmp_path / "relative_escape",
            "mod.py",
            "from ..runtime import X\n",
        )
        violations = scan_internal_imports([layer])
        assert violations, "包外相对 import 未被抓出"
        assert any("包外相对 import" in v for v in violations)

    def test_env_var_read_is_detected(self, tmp_path: Path) -> None:
        """③ 属性类违规（``os.environ[...]`` 读取）MUST 被抓出。

        （否则「零环境变量 / 零出站」这条原则 I 门禁的有效性未被验证。）
        """
        layer = self._make_layer(
            tmp_path / "env_read",
            "mod.py",
            'import os\n\nKEY = os.environ["LANGSMITH_API_KEY"]\n',
        )
        violations = scan_forbidden_usage([layer])
        assert violations, "环境变量读取未被抓出"
        assert any("环境变量读取" in v for v in violations)

    def test_real_layer_has_no_violations(
        self, contracts_dir: Path, repo_root: Path
    ) -> None:
        """真实目录 MUST 两条扫描都无违规——证明门禁有效而非恰好没触发。"""
        assert scan_internal_imports(
            [contracts_dir, repo_root / "tests" / "contracts"]
        ) == []
        assert scan_third_party_imports(
            [contracts_dir, repo_root / "tests" / "contracts" / "fixtures"]
        ) == []
        assert scan_forbidden_usage(
            [contracts_dir, repo_root / "tests" / "contracts" / "fixtures"]
        ) == []

    # ── G9 自检 ──────────────────────────────────────────────────────

    @pytest.mark.parametrize(
        ("source", "expect"),
        [
            ("from typing import TypeAliasType\n", "TypeAliasType"),
            ("from typing import ReadOnly\n", "ReadOnly"),
            ("from typing import TypeIs\n", "TypeIs"),
            ("from typing import override\n", "override"),
            ("import typing\n\nX = typing.TypeAliasType\n", "TypeAliasType"),
            ("from typing import override\n\n\n@override\ndef f():\n    pass\n", "override"),
            ("type Alias = int\n", "3.12"),
            ("class C[T]:\n    pass\n", "3.12"),
        ],
        ids=[
            "import-TypeAliasType",
            "import-ReadOnly",
            "import-TypeIs",
            "import-override",
            "attr-TypeAliasType",
            "decorator-override",
            "pep695-type-stmt",
            "pep695-generic-class",
        ],
    )
    def test_g9_detects_newer_typing_constructs(
        self, tmp_path: Path, source: str, expect: str
    ) -> None:
        """G9 MUST 逐一抓出 3.12+ / 3.13+ 构件（否则「上限」只是句口号）。"""
        layer = tmp_path / "g9"
        layer.mkdir(parents=True, exist_ok=True)
        (layer / "mod.py").write_text(source, encoding="utf-8")
        violations = scan_runtime_baseline(layer)
        assert violations, f"未抓出违规：{source!r}"
        assert any(expect in v for v in violations), violations

    def test_g9_does_not_flag_3_11_constructs(self, tmp_path: Path) -> None:
        """G9 MUST NOT 误报 ≤3.11 的合法构件（含叫 ``override`` 的普通方法名）。"""
        layer = tmp_path / "g9_ok"
        layer.mkdir(parents=True, exist_ok=True)
        (layer / "mod.py").write_text(
            "from typing import Self\n"
            "from typing import NotRequired\n"
            "from typing import TypeVarTuple\n"
            "from typing import Unpack\n"
            "from typing import LiteralString\n"
            "from typing import dataclass_transform\n"
            "\n"
            "\n"
            "class Node:\n"
            "    def override(self) -> Self:\n"
            "        return self\n",
            encoding="utf-8",
        )
        assert scan_runtime_baseline(layer) == []

    def test_real_package_has_no_baseline_violation(self, src_dir: Path) -> None:
        """真实包 MUST 无基线违规——门禁在真实代码上确实成立。"""
        assert scan_runtime_baseline(src_dir / "freegraph") == []

    # ── G10 自检 ─────────────────────────────────────────────────────

    def test_g10_detects_non_ellipsis_method_body(self, tmp_path: Path) -> None:
        """G10 MUST 抓出「方法体不是纯 ``...``」的协议类。

        （否则「协议纯抽象」只是句口号——默认实现会让缺实现的假实现静默通过。）
        """
        layer = tmp_path / "g10"
        layer.mkdir(parents=True, exist_ok=True)
        path = layer / "protocols.py"
        path.write_text(
            "from typing import Protocol\n"
            "\n"
            "\n"
            "class Bad(Protocol):\n"
            "    def do(self, x: int) -> int:\n"
            "        pass\n",
            encoding="utf-8",
        )
        violations = scan_protocol_abstractness(path)
        assert violations, "带 `pass` 方法体的协议未被抓出"
        assert any("Bad.do" in v for v in violations), violations

    def test_g10_accepts_ellipsis_method_body(self, tmp_path: Path) -> None:
        """G10 MUST NOT 误报「方法体只有 ``...``」的协议类。"""
        layer = tmp_path / "g10_ok"
        layer.mkdir(parents=True, exist_ok=True)
        path = layer / "protocols.py"
        path.write_text(
            "from typing import Protocol\n"
            "\n"
            "\n"
            "class Good(Protocol):\n"
            "    def do(self, x: int) -> int:\n"
            "        ...\n",
            encoding="utf-8",
        )
        assert scan_protocol_abstractness(path) == []

    # ── G12 自检 ─────────────────────────────────────────────────────

    def test_g12_detects_a_second_authoritative_manifest(self, tmp_path: Path) -> None:
        """G12 MUST 抓出「第二个自称权威的清单文件」。

        （伪造文件 MUST 命名为 ``public-api.md``——G12 扫的是
        ``**/public-api.md``，文件名不符则扫不到、自检**假绿**。）
        """
        root = tmp_path / "repo"
        (root / "a").mkdir(parents=True)
        (root / "b").mkdir(parents=True)
        (root / "a" / AUTHORITY_FILENAME).write_text(
            "<!-- authority: yes -->\n\n# 甲\n", encoding="utf-8"
        )
        (root / "b" / AUTHORITY_FILENAME).write_text(
            "<!-- authority: yes -->\n\n# 乙\n", encoding="utf-8"
        )
        authoritative, _ = scan_authoritative_manifests(root)
        assert len(authoritative) == 2, (
            f"伪造两个权威清单后，G12 MUST 报出（实得 {len(authoritative)} 个）"
        )

    def test_g12_treats_a_missing_marker_as_non_authoritative(
        self, tmp_path: Path
    ) -> None:
        """**标记缺失**时按「非权威」处理，并 MUST 点名该文件。"""
        root = tmp_path / "repo"
        root.mkdir(parents=True)
        (root / AUTHORITY_FILENAME).write_text("# 无标记\n", encoding="utf-8")
        authoritative, unmarked = scan_authoritative_manifests(root)
        assert authoritative == []
        assert [p.name for p in unmarked] == [AUTHORITY_FILENAME]

    # ── G7 自检 ─────────────────────────────────────────────────────

    def test_g7_detects_an_extra_exported_symbol(self, tmp_path: Path) -> None:
        """G7 · **多**导出一个符号 ⇒ **子集段**报出。"""
        package = tmp_path / "pkg"
        package.mkdir()
        (package / "__init__.py").write_text(
            '__all__ = ["Alpha", "Beta"]\n', encoding="utf-8"
        )
        exports = set(_read_all(package / "__init__.py"))
        violations = g7_subset_violations(exports, {"Alpha"})
        assert violations == ["Beta"], violations

    def test_g7_detects_a_missing_exported_symbol(self, tmp_path: Path) -> None:
        """G7 · **少**导出一个符号 ⇒ **集合相等段**报出。"""
        package = tmp_path / "pkg"
        package.mkdir()
        (package / "__init__.py").write_text(
            '__all__ = ["Alpha"]\n', encoding="utf-8"
        )
        exports = set(_read_all(package / "__init__.py"))
        violations = g7_equality_violations(exports, {"Alpha", "Beta"})
        assert violations == ["Beta"], violations

    # ── G11 自检 ────────────────────────────────────────────────────

    def test_g11_detects_a_partial_implementation(self) -> None:
        """G11 MUST 抓住「缺方法」的假实现（结构化子类型判定判假）。"""
        import freegraph.contracts as contracts

        class Partial:
            def get(self, namespace: Any, key: str) -> Any:
                return None

        assert not isinstance(Partial(), contracts.Store)

    # ── G13 自检 ────────────────────────────────────────────────────

    def test_g13_detects_a_callable_field(self) -> None:
        """G13 MUST 抓住「装了可调用对象」的字段（纯数据纪律）。"""
        from dataclasses import dataclass

        @dataclass
        class Holder:
            callback: Any

        violations = scan_pure_data_discipline(Holder, ())
        assert violations, "含可调用 / 对象引用的字段未被 G13 抓出"
        assert "Holder.callback" in violations[0], violations

    def test_g13_accepts_a_pure_data_field(self) -> None:
        """G13 MUST NOT 误报「纯数据」字段。"""
        from dataclasses import dataclass

        @dataclass
        class Holder:
            name: str
            metadata: Mapping[str, Any]

        assert scan_pure_data_discipline(Holder, ()) == []

    # ── G5 自检 ─────────────────────────────────────────────────────

    def test_g5_detects_a_missing_signature_header(self, tmp_path: Path) -> None:
        """G5 MUST 抓住「首行不是署名头」的文件。"""
        path = tmp_path / "mod.py"
        path.write_text('"""docstring"""\n\nX = 1\n', encoding="utf-8")
        assert _first_line(path) != SIGNATURE_HEADER

    def test_g5_detects_a_missing_module_docstring(self, tmp_path: Path) -> None:
        """G5 MUST 抓住「模块 docstring 不是首个语句」的文件。"""
        path = tmp_path / "mod.py"
        path.write_text(f"{SIGNATURE_HEADER}\n\nX = 1\n", encoding="utf-8")
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        assert ast.get_docstring(tree) is None

    def test_g5_accepts_a_correct_file(self, tmp_path: Path) -> None:
        """G5 MUST NOT 误报合规文件（署名头 + docstring 首个语句）。"""
        path = tmp_path / "mod.py"
        path.write_text(f'{SIGNATURE_HEADER}\n\n"""docstring"""\n\nX = 1\n', encoding="utf-8")
        assert _first_line(path) == SIGNATURE_HEADER
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        assert ast.get_docstring(tree) == "docstring"
        assert isinstance(tree.body[0], ast.Expr)

    # ── G2 / G4 的两档范围 ──────────────────────────────────────────

    def test_g2_exempts_pytest_outside_the_fixture_scope(self, tmp_path: Path) -> None:
        """「只 ``import pytest``」的文件在**夹具目录之外** MUST NOT 报出。

        （``pytest`` 是**开发期工具**——测试基础设施须用它驱动门禁；
        一刀切会让 G2 的第三方档恒失败。）
        """
        tests_dir = tmp_path / "tests"
        fixtures_dir = tmp_path / "fixtures"
        tests_dir.mkdir()
        fixtures_dir.mkdir()
        (tests_dir / "test_x.py").write_text("import pytest\n", encoding="utf-8")
        assert scan_third_party_imports([fixtures_dir]) == []

    def test_g2_still_flags_third_party_inside_the_fixture_scope(
        self, tmp_path: Path
    ) -> None:
        """夹具目录**之内**的第三方 import MUST 报出（豁免不适用于夹具）。"""
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        (fixtures_dir / "impl.py").write_text(
            "import langchain_core\n", encoding="utf-8"
        )
        violations = scan_third_party_imports([fixtures_dir])
        assert violations, "夹具目录内的第三方 import 未被抓出"

    def test_g4_flags_network_modules_inside_the_fixture_scope(
        self, tmp_path: Path
    ) -> None:
        """G4 · 夹具目录内的 ``import socket`` MUST 被抓出。"""
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        (fixtures_dir / "impl.py").write_text("import socket\n", encoding="utf-8")
        violations = scan_forbidden_usage([fixtures_dir])
        assert violations, "夹具目录内的网络库 import 未被抓出"

    def test_g9_covers_the_three_new_modules(self, src_dir: Path) -> None:
        """G9 · 本 feature 新增的三个模块 MUST 落在既有扫描范围内。

        （``scan_runtime_baseline`` 以 ``rglob("*.py")`` **递归**覆盖
        ``src/freegraph/**``——**MUST NOT** 重写扫描器。）
        """
        package = src_dir / "freegraph"
        scanned = {path.name for path in package.rglob("*.py")}
        for name in ("protocols.py", "graph.py", "trace.py"):
            assert name in scanned, name
        assert scan_runtime_baseline(package) == []
