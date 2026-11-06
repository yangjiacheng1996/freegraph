# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""契约层的**八条架构门禁**（US3）。

门禁定义见 ``specs/b1f1-contracts-core/contracts/architecture-gates.md``：

======  ==========================================================  ==========
门禁    含义                                                        spec 条目
======  ==========================================================  ==========
G1      顶层包**惰性**（``import freegraph`` 不连带加载子模块）      FR-011/SC-006
G2      契约层**零**内部 import + **零**第三方 import               FR-005/007/008
G3      依赖闭包**为空**（基础安装零第三方依赖）                   FR-007/SC-002
G4      **零**环境变量读取 + **零**出站                              FR-013
G5      每个新源文件带署名头且 docstring 为首个语句                  FR-010/SC-007
G6      ``py.typed`` 存在且为空（PEP 561）                          FR-009
G7      公开符号面**恰为 8 个**                                      FR-015
G8      文档合规门禁（兼容矩阵 + ``THIRD_PARTY_NOTICES``）           FR-016
======  ==========================================================  ==========

「已加载模块清单」类断言 MUST 在**子进程**中执行——测试进程自身已被
pytest 污染，同进程 ``sys.modules`` 不可作依据（research D-11）。
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, metadata, requires
from pathlib import Path

import pytest

# ── 门禁常量 ────────────────────────────────────────────────────────────

SIGNATURE_HEADER = (
    "# Copyright (c) 2026 杨家成 · MIT License · "
    "https://github.com/yangjiacheng1996/freegraph"
)

#: 契约层的公开符号面（恰 8 个）——与 ``contracts/public-api.md`` §0 一致。
PUBLIC_SYMBOLS = {
    "StateDict",
    "Command",
    "StateSnapshot",
    "RunConfig",
    "FreegraphError",
    "InvalidUpdateError",
    "GraphRecursionError",
    "GraphInterrupt",
}

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
    "tests/contracts/conftest.py",
    "tests/contracts/test_types.py",
    "tests/contracts/test_errors.py",
    "tests/contracts/test_architecture.py",
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


# ── G1 · 顶层包惰性（SC-006）──────────────────────────────────────────


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


# ── 扫描纯函数（供门禁断言与门禁自检共用）──────────────────────────────


def _check_module_target(
    path: Path, lineno: int, module: str, level: int
) -> list[str]:
    """判定单个 import 目标是否违规（G2）。"""
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
    if root not in sys.stdlib_module_names and root not in ALLOWED_THIRD_PARTY:
        return [f"{path.name}:{lineno}: 第三方 import: {module}"]
    return []


def scan_imports(contracts_dir: Path) -> list[str]:
    """静态扫描契约层的 import 图，返回 **G2 违规清单**（空清单 = 合规）。

    这是个**纯函数**——只吃一个目录、只吐一个列表，故门禁自检（T022）
    可以喂它造出来的临时违规目录，证明门禁本身有效。
    """
    violations: list[str] = []
    for path in sorted(Path(contracts_dir).rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    violations.extend(
                        _check_module_target(path, node.lineno, alias.name, 0)
                    )
            elif isinstance(node, ast.ImportFrom):
                violations.extend(
                    _check_module_target(
                        path, node.lineno, node.module or "", node.level
                    )
                )
    return violations


def scan_forbidden_usage(contracts_dir: Path) -> list[str]:
    """静态扫描契约层，返回 **G4 违规清单**（空清单 = 合规）。

    判定 MUST 以 **AST** 为准：只查 ``Import`` / ``ImportFrom`` 的模块名
    与 ``Attribute`` / ``Name`` 访问，**不扫 docstring 与注释**——
    纯文本子串匹配会把「docstring 里提到 ``subprocess``」误判为违规。
    """
    violations: list[str] = []
    for path in sorted(Path(contracts_dir).rglob("*.py")):
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


class TestNoInternalOrThirdPartyImports:
    """G2 · 契约层零内部 import + 零第三方 import（**仅标准库**获准）。"""

    def test_contracts_layer_has_no_import_violations(self, contracts_dir: Path) -> None:
        """真实目录 MUST 无任何 G2 违规。"""
        assert scan_imports(contracts_dir) == []

    def test_no_langchain_family_import(self, contracts_dir: Path) -> None:
        """契约层 MUST NOT import ``langchain`` / ``langchain_core`` /
        ``langsmith`` / ``langgraph`` 全系列。

        （FR-005 明令「不复用 LangChain 家族的运行配置类型」——
        复用即把 ``langsmith`` 拖回依赖树。）
        """
        text = "\n".join(scan_imports(contracts_dir))
        for forbidden in ("langchain", "langchain_core", "langsmith", "langgraph"):
            assert forbidden not in text


class TestNoEnvVarAndNoEgress:
    """G4 · 零环境变量读取 + 零出站。"""

    def test_contracts_layer_has_no_forbidden_usage(self, contracts_dir: Path) -> None:
        """真实目录 MUST 无任何 G4 违规。"""
        assert scan_forbidden_usage(contracts_dir) == []

    def test_no_env_var_read(self, contracts_dir: Path) -> None:
        """MUST NOT 出现 ``os.environ`` / ``os.getenv`` / ``os.environb``。"""
        text = "\n".join(scan_forbidden_usage(contracts_dir))
        for pattern in ("os.environ", "os.getenv", "os.environb"):
            assert pattern not in text

    def test_no_network_or_process_modules(self, contracts_dir: Path) -> None:
        """MUST NOT import ``socket`` / ``http`` / ``urllib`` / ``requests`` /
        ``httpx`` / ``subprocess``。"""
        text = "\n".join(scan_forbidden_usage(contracts_dir))
        for forbidden in ("socket", "http", "urllib", "requests", "httpx", "subprocess"):
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
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
        assert first_line == SIGNATURE_HEADER

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
    """G7 · 公开符号面恰为 8 个（FR-015）。"""

    def test_all_equals_exactly_eight_symbols(self) -> None:
        """``__all__`` MUST **集合等于**那 8 个名字。

        集合断言才能抓住「偷偷多导出一个」——只断言「都包含」会漏。
        """
        import freegraph.contracts as contracts

        assert set(contracts.__all__) == PUBLIC_SYMBOLS

    def test_every_name_is_gettable(self) -> None:
        """每个名字 MUST 能从 ``freegraph.contracts`` 直接取到。"""
        import freegraph.contracts as contracts

        for name in PUBLIC_SYMBOLS:
            assert getattr(contracts, name) is not None, name

    def test_no_send_or_interrupt_public_symbol(self) -> None:
        """契约层 MUST NOT 出现名为 ``Send`` / ``interrupt`` 的公开符号（归 B2F1）。"""
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
CONSTITUTION_DEPENDENCY_WHITELIST = {
    "pydantic",
    "ormsgpack",
    "opentelemetry-api",
    "opentelemetry-sdk",
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
            dependency_closure(name, seen, with_extras)
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

        （extras 由 B3F1 引入——本 feature 无 extras，该条为空断言。）
        """
        _require_installed()
        base = dependency_closure("freegraph")
        extras = dependency_closure("freegraph", with_extras=True) - base
        assert extras <= CONSTITUTION_DEPENDENCY_WHITELIST, extras

    def test_closure_licenses_are_in_whitelist(self) -> None:
        """闭包内每个包的许可证 MUST ∈ 白名单；MUST NOT 出现传染性许可证。

        取不到许可证信息时该断言 ``skip`` 并提示——不得默认「闭包小就安全」。

        **当前基础安装闭包为空**（零第三方依赖），故本断言暂为空转；
        它在 **B3F1 引入 extras** 后立即变为实质断言——
        故此处**同时覆盖 extras 闭包**，以免那条路径失去校验。
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
        """源码 MUST NOT 使用 3.12+ / 3.13+ 的 typing 构件。"""
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
    """G8 · 兼容矩阵覆盖全部公开符号 + ``THIRD_PARTY_NOTICES`` 已登记。"""

    def test_third_party_notices_exists(self, repo_root: Path) -> None:
        """仓库根 MUST 有 ``THIRD_PARTY_NOTICES``。"""
        assert (repo_root / "THIRD_PARTY_NOTICES").is_file()

    def test_readme_has_compat_matrix_section(self, repo_root: Path) -> None:
        """README MUST 有「## API 兼容矩阵」章节。"""
        readme = (repo_root / "README.md").read_text(encoding="utf-8")
        match = COMPAT_MATRIX_PATTERN.search(readme)
        assert match, "README.md 缺少「## API 兼容矩阵」章节"

    def test_compat_matrix_covers_every_public_symbol(self, repo_root: Path) -> None:
        """矩阵第一列的符号名集合 MUST **等于**契约层的 8 个公开符号。

        （集合断言才能抓住「新增了公开符号但没更新兼容矩阵」。）
        """
        readme = (repo_root / "README.md").read_text(encoding="utf-8")
        match = COMPAT_MATRIX_PATTERN.search(readme)
        assert match, "README.md 缺少「## API 兼容矩阵」章节"
        rows = re.findall(r"^\|\s*`([A-Za-z_]+)`\s*\|", match.group(1), re.M)
        assert set(rows) == PUBLIC_SYMBOLS, set(rows) ^ PUBLIC_SYMBOLS

    def test_compat_matrix_declares_no_affiliation(self, repo_root: Path) -> None:
        """矩阵章节 MUST 含「不构成 affiliation」字样（宪法原则 IX）。"""
        readme = (repo_root / "README.md").read_text(encoding="utf-8")
        match = COMPAT_MATRIX_PATTERN.search(readme)
        assert match, "README.md 缺少「## API 兼容矩阵」章节"
        assert "不构成 affiliation" in match.group(1)

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
        violations = scan_imports(layer)
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
        violations = scan_imports(layer)
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
        violations = scan_imports(layer)
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
        violations = scan_forbidden_usage(layer)
        assert violations, "环境变量读取未被抓出"
        assert any("环境变量读取" in v for v in violations)

    def test_real_layer_has_no_violations(self, contracts_dir: Path) -> None:
        """真实目录 MUST 两条扫描都无违规——证明门禁有效而非恰好没触发。"""
        assert scan_imports(contracts_dir) == []
        assert scan_forbidden_usage(contracts_dir) == []

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





