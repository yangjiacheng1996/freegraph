# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""门面的**七条架构门禁**（G14–G20）与它们的**八条自检**。

门禁定义见 ``specs/b2f2-public-api-facade/contracts/architecture-gates.md``：

======  ==============================================================  ==========================
门禁    含义                                                            spec 条目
======  ==============================================================  ==========================
G14     门面**零实现体**（AST 判据 + 语句白名单）                        FR-006/SC-004
G15     门面导出面**两处相等**（``__all__`` **且** 公开名集合）            FR-002/SC-003
G16     **API 快照**逐字节比对 + **可复现** + 更新入口**默认不生效**      FR-010/FR-011/SC-005
G17     门面**依赖卫生**（两档：内部 L4/L5 + 第三方 / 零环境变量 / 零 I/O）FR-014/SC-009
G18     门面的**模块加载面**（不横依赖 L4/L5 + 顶层包惰性）              FR-013/FR-014/SC-007
G19     兼容矩阵**覆盖门面 7 个符号**                                    FR-012/SC-012
G20     本 feature **新建源文件**的**署名头**                            FR-017/SC-014
======  ==============================================================  ==========================

**每条新增门禁 MUST 有自检**——故意造一处违规，门禁**确实报出**才算通过
（只测「合规时通过」的门禁等于没测）。**7 条门禁 ⇒ 8 条自检**
（**G15 的两段各一条**：子集段抓「多导出」· 集合相等段抓「漏导出」）。

**需要子进程的判定**（G18）**必须在子进程执行**——测试进程自身已导入 pytest。
"""

from __future__ import annotations

import ast
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from ._gatesupport import (
    CONTRACT_API_MANIFEST,
    CONTRACT_MANIFEST_ANCHOR,
    FACADE_MANIFEST,
    FACADE_MODULES,
    SIGNED_SOURCE_FILES,
    SNAPSHOT_PATH,
    compare_snapshot,
    compat_matrix_rows,
    diff_line_count,
    env_and_io_violations,
    facade_body_violations,
    facade_re_export_violations,
    forbidden_loaded_modules,
    g15_equality_violations,
    g15_subset_violations,
    import_violations,
    loaded_freegraph_modules,
    parse_manifest_symbols,
    signature_header_violations,
)
from ._snapshot_tools import render_api_snapshot

#: 门面导出的 7 个符号中，**本 feature 补入兼容矩阵**的 5 个。
MATRIX_NEW_ROWS = {"StateGraph", "START", "END", "Send", "interrupt"}

#: 5 个新增行的「等价程度」逐符号取值（research D-17 · quickstart §8）。
MATRIX_NEW_EQUIVALENCE = {
    "StateGraph": "部分等价",
    "START": "行为等价",
    "END": "行为等价",
    "Send": "部分等价",
    "interrupt": "部分等价",
}

#: 5 个新增行的上游来源行号（核实环境 ``langgraph 1.2.11``）。
MATRIX_NEW_SOURCES = {
    "StateGraph": "langgraph/graph/state.py:131",
    "START": "langgraph/constants.py:30",
    "END": "langgraph/constants.py:28",
    "Send": "langgraph/types.py:704",
    "interrupt": "langgraph/types.py:851",
}


@pytest.fixture(scope="module")
def manifest_symbols() -> set[str]:
    """门面导出面的**手写权威**（``facade-api.md`` §0 解析出的 7 个）。"""
    return parse_manifest_symbols(FACADE_MANIFEST)


def _facade_paths(repo_root: Path) -> list[Path]:
    return [repo_root / relative for relative in FACADE_MODULES]


# ── G14 · 门面零实现体 ─────────────────────────────────────────────────


class TestFacadeHasNoImplementationBody:
    """门禁 **G14** —— 门面模块内**零** ``class`` / ``def`` / ``async def``。"""

    def test_facade_module_has_no_implementation_body(self, repo_root: Path) -> None:
        """门面的语句白名单外**无任何**实现体（违规时报出**行号**）。"""
        path = repo_root / "src/freegraph/graph.py"
        violations = facade_body_violations(path)
        assert violations == [], "\n".join(violations)

    def test_selfcheck_detects_a_definition(self, tmp_path: Path) -> None:
        """**自检** —— 临时造一处 ``def`` ⇒ 门禁**确实报出**。"""
        path = tmp_path / "facade.py"
        path.write_text(
            '"""docstring"""\n'
            "\n"
            "def _helper() -> None:\n"
            "    pass\n",
            encoding="utf-8",
        )
        violations = facade_body_violations(path)
        assert violations, "门面内的 def 未被抓出"
        assert "_helper" in violations[0], violations

    def test_selfcheck_detects_a_class(self, tmp_path: Path) -> None:
        """**自检** —— 临时造一处 ``class`` ⇒ 门禁**确实报出**。"""
        path = tmp_path / "facade.py"
        path.write_text(
            '"""docstring"""\n'
            "\n"
            "class _Hidden:\n"
            "    pass\n",
            encoding="utf-8",
        )
        violations = facade_body_violations(path)
        assert violations, "门面内的 class 未被抓出"
        assert "_Hidden" in violations[0], violations


# ── G15 · 导出面两处相等 ───────────────────────────────────────────────


class TestExportSurfaceIsExact:
    """门禁 **G15** —— 导出面**两处相等**（子集段 + 集合相等段）。"""

    def test_subset_segment(self, manifest_symbols: set[str]) -> None:
        """**子集段**（始终启用）—— 导出面 MUST ⊆ §0 的 7 个。"""
        import freegraph.graph as graph

        exports = set(graph.__all__)
        public = {name for name in vars(graph) if not name.startswith("_")}
        violations = g15_subset_violations(exports, public, manifest_symbols)
        assert violations == [], f"导出面含清单外的符号：{violations}"

    def test_equality_segment(self, manifest_symbols: set[str]) -> None:
        """**集合相等段** —— 导出面 MUST **等于** §0 的 7 个（抓「漏导出」）。"""
        import freegraph.graph as graph

        exports = set(graph.__all__)
        public = {name for name in vars(graph) if not name.startswith("_")}
        violations = g15_equality_violations(exports, public, manifest_symbols)
        assert violations == [], f"导出面与 §0 清单的差集（对称差）：{violations}"

    def test_selfcheck_subset_detects_an_extra_export(
        self, manifest_symbols: set[str]
    ) -> None:
        """**自检（子集段）** —— 塞一个第 8 个公开名 ⇒ 门禁**确实报出**。"""
        allowed = set(manifest_symbols)
        exports = allowed | {"ExtraSymbol"}
        violations = g15_subset_violations(exports, exports, allowed)
        assert violations == ["ExtraSymbol"], violations

    def test_selfcheck_equality_detects_a_missing_export(
        self, manifest_symbols: set[str]
    ) -> None:
        """**自检（集合相等段）** —— 删掉一个导出符号 ⇒ 门禁**确实报出**。

        子集段抓不到这一类（子集**仍然成立**）⇒ 两条自检缺一不可。
        """
        exports = set(manifest_symbols) - {"Send"}
        violations = g15_equality_violations(exports, exports, manifest_symbols)
        assert violations == ["Send"], violations


# ── G16 · API 快照比对 ─────────────────────────────────────────────────


class TestApiSnapshotIsFrozen:
    """门禁 **G16** —— 快照逐字节比对 + 可复现 + 更新入口默认不生效。"""

    def test_snapshot_matches_the_committed_file(self) -> None:
        """生成结果 MUST 与入库快照**逐字节**相同（不一致 ⇒ 输出 diff）。"""
        import freegraph.graph as graph

        namespace = {
            key: value
            for key, value in vars(graph).items()
            if not key.startswith("_")
        }
        generated = render_api_snapshot(namespace)
        committed = SNAPSHOT_PATH.read_text(encoding="utf-8")
        ok, diff = compare_snapshot(committed, generated)
        assert ok, (
            "生成结果与入库快照不一致——MUST NOT 用「自动更新」掩盖（FR-011）。\n" + diff
        )

    def test_snapshot_is_reproducible(self) -> None:
        """同一份代码**两次生成 MUST 逐字节相同**（差异字节数 == 0）。"""
        import freegraph.graph as graph

        namespace = {
            key: value
            for key, value in vars(graph).items()
            if not key.startswith("_")
        }
        first = render_api_snapshot(namespace)
        second = render_api_snapshot(namespace)
        assert first == second
        assert len(first.encode("utf-8")) == len(second.encode("utf-8"))

    def test_update_entry_point_defaults_to_off(self) -> None:
        """更新入口 MUST **默认不生效**（spec FR-011 ①）。"""
        from . import conftest as facade_conftest

        assert facade_conftest.UPDATE_OPTION_DEFAULT is False

    def test_selfcheck_detects_a_broken_snapshot(self, tmp_path: Path) -> None:
        """**自检** —— 故意改坏入库快照 ⇒ 比对**确实失败**且 diff 非空。"""
        import freegraph.graph as graph

        namespace = {
            key: value
            for key, value in vars(graph).items()
            if not key.startswith("_")
        }
        generated = render_api_snapshot(namespace)
        broken = generated.replace("[constant] END = '__end__'", "[constant] END = 'x'")
        assert broken != generated
        ok, diff = compare_snapshot(generated, broken)
        assert not ok, "比对未能抓出改坏的快照"
        assert diff.strip(), "diff 为空"
        assert diff_line_count(generated, broken) >= 1


# ── G17 · 依赖卫生 ─────────────────────────────────────────────────────


class TestFacadeDependencyHygiene:
    """门禁 **G17** —— 门面**零**第三方 import / 零环境变量 / 零 I/O。"""

    def test_no_internal_l4_l5_import(self, repo_root: Path) -> None:
        """**内部档** —— 指向 L4 / L5 的 import 数 MUST == 0（L2 / L3 合法）。"""
        violations: list[str] = []
        for path in _facade_paths(repo_root):
            for violation in import_violations(path):
                if "内部层 import" in violation:
                    violations.append(violation)
        assert violations == [], "\n".join(violations)

    def test_no_third_party_import(self, repo_root: Path) -> None:
        """**第三方档** —— ``langchain*`` / ``langgraph*`` / ``langsmith`` /
        ``pydantic`` / ``typing_extensions`` 的 import 数 MUST == 0。"""
        violations: list[str] = []
        for path in _facade_paths(repo_root):
            for violation in import_violations(path):
                if "第三方 import" in violation:
                    violations.append(violation)
        assert violations == [], "\n".join(violations)

    def test_no_env_var_read_and_no_egress(self, repo_root: Path) -> None:
        """③ 环境变量读取数 MUST == 0；④ 出站 / 文件 I/O 调用数 MUST == 0。"""
        violations: list[str] = []
        for path in _facade_paths(repo_root):
            violations.extend(env_and_io_violations(path))
        assert violations == [], "\n".join(violations)

    def test_selfcheck_detects_an_env_var_read(self, tmp_path: Path) -> None:
        """**自检** —— 临时造一处 ``os.environ`` 读取 ⇒ 门禁**确实报出**。"""
        path = tmp_path / "mod.py"
        path.write_text(
            "import os\n"
            "\n"
            'KEY = os.environ["HOME"]\n',
            encoding="utf-8",
        )
        violations = env_and_io_violations(path)
        assert violations, "环境变量读取未被抓出"
        assert "环境变量读取" in violations[0], violations

    def test_selfcheck_detects_an_l4_import_only(self, tmp_path: Path) -> None:
        """**自检** —— L4 import 被抓出，而 L1 / L2 **不**被抓出。"""
        path = tmp_path / "mod.py"
        path.write_text(
            "from freegraph.persistence import Thing\n",
            encoding="utf-8",
        )
        violations = import_violations(path)
        assert violations, "L4（持久化）import 未被抓出"
        assert any("内部层 import" in v for v in violations), violations

        legal = tmp_path / "legal.py"
        legal.write_text(
            "from freegraph.contracts import Command\n"
            "from freegraph.runtime import Runtime\n"
            "from freegraph._stategraph import StateGraph\n",
            encoding="utf-8",
        )
        assert import_violations(legal) == [], import_violations(legal)


# ── G18 · 模块加载面 ───────────────────────────────────────────────────


class TestFacadeModuleLoadingSurface:
    """门禁 **G18** —— 门面**不横依赖** L4 / L5；顶层包**保持惰性**。"""

    def test_importing_the_facade_loads_no_l4_or_l5(self) -> None:
        """① 子进程 ``import freegraph.graph`` ⇒ 不含持久化 / 可观测层模块。"""
        loaded = loaded_freegraph_modules("import freegraph.graph")
        violations = forbidden_loaded_modules(
            loaded, ("freegraph.persistence", "freegraph.observability")
        )
        assert violations == [], f"门面连带加载了 L4 / L5：{violations}"

    def test_importing_the_facade_loads_the_contract_layer(self) -> None:
        """③ 子进程 ``from freegraph.graph import StateGraph`` ⇒
        ``freegraph.contracts`` **被加载**（门面**可以**依赖 L1 契约层）。"""
        loaded = loaded_freegraph_modules(
            "from freegraph.graph import StateGraph"
        )
        assert "freegraph.contracts" in loaded, loaded

    def test_top_level_package_does_not_reexport_the_facade(
        self, repo_root: Path
    ) -> None:
        """**源码文本**断言 —— 顶层包 MUST NOT 导入门面（FR-013）。

        **为何要源码文本判据**：``import freegraph`` 后 ``freegraph.*`` 子模块数
        **== 0** 那一条**由既有门禁 G1 直接产出**（其口径**已是**
        ``freegraph.*`` 全量 ⇒ 恰为 ``['freegraph']``）——G18 §1-② 已声明
        「**本条不另写断言**」，本门禁**不重复实现**。

        本断言查的是**更靠前**的一环：顶层包的**源码**里**根本没有**对门面的
        导入语句 ⇒ G1 的运行时结论有**因果链**上的根。
        """
        source = (repo_root / "src" / "freegraph" / "__init__.py").read_text(
            encoding="utf-8"
        )
        violations = facade_re_export_violations(source)
        assert violations == [], "\n".join(violations)

    def test_selfcheck_detects_a_top_level_reexport(self) -> None:
        """**自检** —— 临时造一处「顶层包 re-export 门面」⇒ 门禁**确实报出**。

        **不得真的改** ``__init__.py``（只喂源码文本）⇒ 零副作用。
        """
        violations = facade_re_export_violations(
            "from .graph import StateGraph\n"
            "from freegraph.graph import START\n"
            "__all__ = ['StateGraph', 'START']\n"
        )
        assert violations, "顶层包 re-export 门面未被报出"
        assert any("from .graph" in v for v in violations), violations
        assert any("from freegraph.graph" in v for v in violations), violations

        assert facade_re_export_violations("__version__ = '0.0.3'\n") == []

    def test_selfcheck_detects_a_forbidden_loaded_module(self) -> None:
        """**自检** —— 造一份「连带加载 L4」的模块 ⇒ 加载面**确实报出**。"""
        loaded = ["freegraph", "freegraph.contracts", "freegraph.persistence.store"]
        violations = forbidden_loaded_modules(
            loaded, ("freegraph.persistence", "freegraph.observability")
        )
        assert violations == ["freegraph.persistence.store"], violations

    def test_selfcheck_detects_a_facade_pulling_l4(self, tmp_path: Path) -> None:
        """**自检** —— 临时造一个「连带加载 L4」的门面 ⇒ 加载面**确实报出**。"""
        package = tmp_path / "fakepkg"
        package.mkdir()
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "persistence.py").write_text("THING = 1\n", encoding="utf-8")
        (package / "facade.py").write_text(
            "from .persistence import THING\n", encoding="utf-8"
        )
        import os
        import subprocess

        env = {**os.environ, "PYTHONPATH": str(tmp_path)}
        proc = subprocess.run(
            [sys.executable, "-c", "import fakepkg.facade"],
            env=env,
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert proc.returncode == 0, proc.stderr
        violations = forbidden_loaded_modules(
            ["fakepkg", "fakepkg.facade", "fakepkg.persistence"],
            ("fakepkg.persistence",),
        )
        assert violations == ["fakepkg.persistence"], violations


# ── G19 · 兼容矩阵覆盖 ─────────────────────────────────────────────────


class TestCompatMatrixCoversTheFacade:
    """门禁 **G19** —— 兼容矩阵覆盖门面的 7 个符号。

    除门面的 7 个符号外，本门禁还承担**整表**的口径判定（矩阵的符号集合
    == 契约层 18 个 ∪ 门面层 7 个）——既有门禁 **G8** 的范围**只是**契约层
    的 18 个符号（见 ``contracts/architecture-gates.md`` §3 的「分工不重叠」）。
    """

    def test_matrix_covers_every_facade_symbol(
        self, repo_root: Path, manifest_symbols: set[str]
    ) -> None:
        """门面 7 个符号 MUST 在矩阵里**各恰有一行**（多 / 少都失败）。"""
        readme = (repo_root / "README.md").read_text(encoding="utf-8")
        names = [name for name, _ in compat_matrix_rows(readme)]
        counts = Counter(names)
        missing = sorted(name for name in manifest_symbols if counts[name] == 0)
        assert not missing, f"兼容矩阵缺门面层符号：{missing}"
        duplicated = sorted(
            name for name in manifest_symbols if counts[name] > 1
        )
        assert not duplicated, f"兼容矩阵的门面层符号出现多行：{duplicated}"

    def test_matrix_covers_exactly_the_two_layers(
        self, repo_root: Path, manifest_symbols: set[str]
    ) -> None:
        """**整表**口径 —— 矩阵的符号集合 == 契约层 18 个 ∪ 门面层 7 个。

        （抓「清单外符号」——既有门禁 G8 的范围**只是**契约层，故这条判据
        落在本门禁。）
        """
        readme = (repo_root / "README.md").read_text(encoding="utf-8")
        contract = parse_manifest_symbols(
            repo_root / CONTRACT_API_MANIFEST, anchor=CONTRACT_MANIFEST_ANCHOR
        )
        names = {name for name, _ in compat_matrix_rows(readme)}
        assert names == contract | manifest_symbols, names ^ (contract | manifest_symbols)

    def test_new_rows_declare_equivalence_and_source(
        self, repo_root: Path
    ) -> None:
        """新增 5 行 MUST 逐符号标注**等价程度**并附**上游来源行号**。"""
        readme = (repo_root / "README.md").read_text(encoding="utf-8")
        rows = dict(compat_matrix_rows(readme))
        for name, equivalence in MATRIX_NEW_EQUIVALENCE.items():
            assert name in rows, f"兼容矩阵缺 {name} 行"
            cells = rows[name]
            assert len(cells) == 4, f"兼容矩阵行 {name} 的列数不是 4：{cells}"
            assert cells[2] == equivalence, (
                f"兼容矩阵行 {name} 的「等价程度」应为 {equivalence!r}，"
                f"实得 {cells[2]!r}"
            )
            assert MATRIX_NEW_SOURCES[name] in cells[3], (
                f"兼容矩阵行 {name} 缺上游来源 {MATRIX_NEW_SOURCES[name]!r}"
            )

    #: **契约层矩阵行**中**经特批可更新**的行（**B9F1 · 裁定 21 · 登记项 R-7**）。
    #:
    #: ⚠️ **破 G8「既有行逐字未改」判据的唯一白名单** —— 2026-11-11 · 发起者特批：
    #: B9F1 交付了 `Command` 的**运行期语义**（`goto` / `update` / `Command.PARENT`）与
    #: **命令列表**形态 ⇒ 这两行的「差异说明」**必须**随之更新，否则矩阵**过期**
    #: （与原则 X 的「MUST 更新清单」相悖）。
    #: ⇒ **只放行这两行**；其余 **16** 行仍**逐字未改**（判据**只放宽一处**）。
    #: ⚠️ **等价程度（第三列）MUST NOT 变**（`Command` = 部分等价 · `NodeFunc` = 不支持）
    #: —— 本白名单**只放行「差异说明」列的措辞更新**。
    MATRIX_ROWS_UPDATABLE_BY_B9F1 = frozenset({"Command", "NodeFunc"})

    def test_existing_contract_rows_are_unchanged(self, repo_root: Path) -> None:
        """**既有 18 行逐字未改** —— 与 git 中���**上一版**逐字节比对。

        取 ``git show HEAD:README.md`` 的兼容矩阵章节里**契约层的 18 行**
        （首列符号 ∈ 契约层清单），与当前 README 的对应行**逐字节**比对。

        无 git / 无历史版本时 **skip**（不判失败）——「逐字未改」是**交付纪律**，
        其可判定形式依赖版本历史。
        """
        contract = parse_manifest_symbols(
            repo_root / CONTRACT_API_MANIFEST, anchor=CONTRACT_MANIFEST_ANCHOR
        )
        current = {
            name: " | ".join(cells)
            for name, cells in compat_matrix_rows(
                (repo_root / "README.md").read_text(encoding="utf-8")
            )
            if name in contract
        }
        proc = subprocess.run(
            ["git", "show", "HEAD:README.md"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            pytest.skip("无 git 历史版本可比对——「逐字未改」判据不可执行")
        previous = {
            name: " | ".join(cells)
            for name, cells in compat_matrix_rows(proc.stdout)
            if name in contract
        }
        assert previous, "git 历史版本里没有契约层的矩阵行"
        changed = sorted(
            name
            for name in previous
            if name not in self.MATRIX_ROWS_UPDATABLE_BY_B9F1
            and previous[name] != current.get(name)
        )
        assert not changed, f"既有契约层矩阵行被改动：{changed}"

        # ⚠️ **白名单行**（B9F1 · 裁定 21）：**只**放行「差异说明」列的措辞更新
        # ⇒ **等价程度（第三列）MUST NOT 变**。
        for name in self.MATRIX_ROWS_UPDATABLE_BY_B9F1:
            prev_cells = [c.strip() for c in previous[name].split(" | ")]
            curr_cells = [c.strip() for c in current.get(name, "").split(" | ")]
            assert curr_cells[2] == prev_cells[2], (
                f"白名单行 {name} 的「等价程度」被改动："
                f"{prev_cells[2]!r} → {curr_cells[2]!r}"
            )

    def test_selfcheck_detects_a_missing_row(
        self, repo_root: Path, manifest_symbols: set[str]
    ) -> None:
        """**自检** —— 删掉一行 ⇒ 覆盖检查**确实报出**。"""
        readme = (repo_root / "README.md").read_text(encoding="utf-8")
        stripped = "\n".join(
            line
            for line in readme.splitlines()
            if not line.strip().startswith("| `Send` |")
        )
        names = {name for name, _ in compat_matrix_rows(stripped)}
        missing = sorted(manifest_symbols - names)
        assert missing == ["Send"], missing


# ── G20 · 署名头 ───────────────────────────────────────────────────────


class TestSignatureHeaders:
    """门禁 **G20** —— 本 feature 新建的 10 个 ``.py`` MUST 带署名头。"""

    @pytest.mark.parametrize("relative_path", SIGNED_SOURCE_FILES)
    def test_file_carries_the_signature_header(
        self, repo_root: Path, relative_path: str
    ) -> None:
        """逐文件断言：首行**逐字**等于署名头，且 docstring 是**首个语句**。"""
        path = repo_root / relative_path
        assert path.is_file(), f"缺少文件：{relative_path}"
        violations = signature_header_violations(path)
        assert violations == [], "\n".join(violations)

    def test_selfcheck_detects_a_broken_header(self, tmp_path: Path) -> None:
        """**自检** —— 临时破坏署名头 ⇒ 门禁**确实报出**。"""
        path = tmp_path / "mod.py"
        path.write_text('"""docstring"""\n\nX = 1\n', encoding="utf-8")
        violations = signature_header_violations(path)
        assert violations, "缺署名头未被 G20 抓出"

        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert ast.get_docstring(tree) == "docstring"
