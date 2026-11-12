# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""API 签名快照的**比对 / 可复现 / 更新入口**断言（US2）。

覆盖的成功标准：

* **SC-005** 快照与门面形状**逐字节**一致 + 更新入口**默认不生效**
  + **自检三例**（FR-011 ② · research D-23）；
* **SC-006** 快照**可复现**（同一份代码两次生成**逐字节相同**）+
  快照文本**合规**（UTF-8 / LF / 末行换行 / 无非确定内容）。

**自检 MUST 走真实的比对路径**（research **D-23**）：把比对对象指向
``tmp_path`` 下一份**被改动过**的快照文件，断言比对**确实失败**且
**diff 非空**——MUST NOT 只断言「渲染结果 ≠ 入库文本」（那只验证**渲染器**，
守不住「比对逻辑本身坏掉」这条失效模式 ⇒ 门禁形同虚设）。

**零副作用**：自检 MUST NOT 碰真源码、只在 ``tmp_path`` 下操作 ⇒ 可在
只读环境跑（沿用 research D-10 的「纯函数」思路）。
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from ._gatesupport import (
    SNAPSHOT_PATH,
    compare_snapshot,
    diff_line_count,
    snapshot_diff,
)
from ._snapshot_tools import render_api_snapshot

#: 子进程「常规跑 pytest」探针的**递归保护**环境变量。
_PROBE_ENV = "FREEGRAPH_SNAPSHOT_PROBE"


def _namespace() -> dict[str, Any]:
    """门面的**公开名集合**（与门禁 G15 的「公开名」口径**同源**）。

    MUST NOT 由测试侧另造一份符号清单——否则快照与门面**脱钩**，冻结面失效。
    """
    import freegraph.graph as graph

    return {k: v for k, v in vars(graph).items() if not k.startswith("_")}


def _render() -> str:
    """渲染当前门面的快照文本（纯函数 · 无副作用）。"""
    return render_api_snapshot(_namespace())


def _compare(expected_path: Path, generated: str) -> tuple[bool, str]:
    """**真实的比对路径**：把生成结果与 ``expected_path`` 的内容逐字节比。

    返回 ``(是否一致, diff 文本)``——不一致时 diff **非空**。
    """
    expected = expected_path.read_text(encoding="utf-8")
    return compare_snapshot(expected, generated)


def _write_snapshot(target: Path, enabled: bool) -> None:
    """快照的**更新入口**（``enabled`` = 开关是否打开）。

    **默认关闭** ⇒ ``enabled=False`` 时**绝不写盘**（spec FR-011 ①）。
    """
    if not enabled:
        return
    target.write_text(_render(), encoding="utf-8", newline="\n")


# ── T021 · 逐字节比对 + 可复现（SC-005 / SC-006）──────────────────────


class TestSnapshotComparison:
    """生成结果与**入库快照**的逐字节比对。"""

    def test_snapshot_matches_the_committed_file(self) -> None:
        """生成结果 MUST 与 ``contracts/public-api-snapshot.txt`` **逐字节相同**。

        不一致 ⇒ 测试失败并输出 **diff**（差异行数 ≥ 1）。
        """
        generated = _render()
        ok, diff = _compare(SNAPSHOT_PATH, generated)
        assert ok, (
            "生成的快照与入库快照不一致——MUST NOT 用「自动更新」掩盖"
            "（FR-011）；确认是合法变更后跑 "
            "`pytest tests/facade/test_api_snapshot.py --update-api-snapshot` "
            "并**人工 review diff**。\n" + diff
        )

    def test_difference_would_be_reported(self) -> None:
        """**自检（比对路径）** —— 比对确实失败时 **diff 非空**且差异行数 ≥ 1。"""
        generated = _render()
        broken = generated.replace("[constant] START", "[constant] STARTX")
        assert broken != generated
        diff = snapshot_diff(generated, broken)
        assert diff.strip(), "diff 为空——比对路径抓不出差异"
        assert diff_line_count(generated, broken) >= 1

    def test_snapshot_is_reproducible(self) -> None:
        """同一份代码**两次生成 MUST 逐字节相同**（差异字节数 == 0）。"""
        first = _render()
        second = _render()
        assert first == second
        assert len(first.encode("utf-8")) - len(second.encode("utf-8")) == 0


# ── T022 · 更新入口默认不生效 + 幂等 + 自检三例（SC-005）──────────────


class TestUpdateEntryPoint:
    """``--update-api-snapshot`` —— **默认关闭**、显式开启则幂等。"""

    def test_update_option_defaults_to_off(self, request: pytest.FixtureRequest) -> None:
        """开关的**缺省值** MUST 是「关闭」——常规跑 pytest 绝不改快照文件。"""
        from . import conftest as facade_conftest

        assert facade_conftest.UPDATE_OPTION_DEFAULT is False
        # 显式带上开关时为 True；没带时为 False（由子进程探针另行验证）。
        assert request.config.getoption("--update-api-snapshot") in (True, False)

    def test_update_entry_point_is_off_by_default(
        self, repo_root: Path, src_dir: Path, tmp_path: Path
    ) -> None:
        """**默认不生效** —— 常规执行 pytest **不改动**快照文件。

        两半断言：

        ① 写入入口在「未开启」时**不写盘**（纯函数层面）；
        ② **子进程**跑一次常规 pytest ⇒ 入库快照**逐字节不变**。
        """
        target = tmp_path / "snapshot.txt"
        target.write_bytes(SNAPSHOT_PATH.read_bytes())
        before = target.read_bytes()
        _write_snapshot(target, enabled=False)
        assert target.read_bytes() == before, "未开启开关时写入口仍然改了文件"

        if os.environ.get(_PROBE_ENV) == "1":
            # 子进程内的嵌套执行 ⇒ 只做 ①，避免无限递归。
            return

        committed = SNAPSHOT_PATH.read_bytes()
        env = {**os.environ, _PROBE_ENV: "1", "PYTHONPATH": str(src_dir)}
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/facade/test_api_snapshot.py",
                "-q",
                "-p",
                "no:cacheprovider",
            ],
            env=env,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert proc.returncode == 0, (
            f"常规执行 pytest 失败：\n{proc.stdout}\n{proc.stderr}"
        )
        assert SNAPSHOT_PATH.read_bytes() == committed, (
            "常规执行 pytest 改动了入库快照文件——更新入口 MUST 默认不生效"
            "（FR-011 ①）"
        )

    def test_explicit_update_is_idempotent(self, tmp_path: Path) -> None:
        """**显式更新幂等** —— 代码未变时两次更新产出**相同文本**。"""
        target = tmp_path / "snapshot.txt"
        _write_snapshot(target, enabled=True)
        first = target.read_bytes()
        _write_snapshot(target, enabled=True)
        assert target.read_bytes() == first
        assert first == _render().encode("utf-8")

    def test_snapshot_file_is_updated_only_when_requested(
        self, request: pytest.FixtureRequest
    ) -> None:
        """**入库** —— 仅在显式带上 ``--update-api-snapshot`` 时写盘。"""
        if not request.config.getoption("--update-api-snapshot"):
            pytest.skip("未开启 --update-api-snapshot（默认关闭 · FR-011 ①）")
        _write_snapshot(SNAPSHOT_PATH, enabled=True)
        assert SNAPSHOT_PATH.read_bytes() == _render().encode("utf-8")


class TestSnapshotSelfCheck:
    """**自检三例**（research D-23）—— 快照确实能抓出漂移。

    三例 MUST **走真实的比对路径**：把比对对象指向 ``tmp_path`` 下一份
    **被改动过**的快照文件，断言比对**确实失败**且 **diff 非空**。
    """

    @staticmethod
    def _run_self_check(tmp_path: Path, mutate: Any, expect_token: str) -> None:
        """跑一遍「改坏入库快照 ⇒ 比对确实失败」的自检流程。"""
        target = tmp_path / "mutated-snapshot.txt"
        original = _render()
        target.write_text(original, encoding="utf-8", newline="\n")
        mutated = mutate(original)
        assert mutated != original, "自检用的「改动」没有真的改动快照"
        target.write_text(mutated, encoding="utf-8", newline="\n")

        ok, diff = _compare(target, _render())
        assert not ok, "比对未能抓出漂移——比对路径坏了（门禁形同虚设）"
        assert diff.strip(), "diff 为空——比对路径抓不出差异"
        assert diff_line_count(original, mutated) >= 1
        assert expect_token in diff, f"diff 未指出改动处（期望包含 {expect_token!r}）"

    def test_selfcheck_detects_a_renamed_parameter(self, tmp_path: Path) -> None:
        """① 某方法的**参数改名** ⇒ 比对确实失败。"""
        self._run_self_check(
            tmp_path,
            lambda text: text.replace(
                "[method] add_node(self, node: str | Callable[..., Any],",
                "[method] add_node(self, node_name: str | Callable[..., Any],",
            ),
            "node_name",
        )

    def test_selfcheck_detects_a_changed_annotation(self, tmp_path: Path) -> None:
        """② **参数 / 返回注解**被改动 ⇒ 比对确实失败（Q3「全冻」的核心收益）。"""
        self._run_self_check(
            tmp_path,
            lambda text: text.replace(
                "[method] add_edge(self, start_key: str | list[str], end_key: str) -> Self",
                "[method] add_edge(self, start_key: str | list[str], end_key: str) -> Any",
            ),
            "-> Any",
        )

    def test_selfcheck_detects_a_new_public_attribute(self, tmp_path: Path) -> None:
        """③ **新增一个公开属性** ⇒ 比对确实失败（Q6 专门立的口径）。"""
        self._run_self_check(
            tmp_path,
            lambda text: text.replace(
                "[class] StateGraph\n",
                "[class] StateGraph\n"
                "    [attribute] extra: str = 'x' (readonly)\n",
            ),
            "extra",
        )


# ── T023 · 快照文本合规（SC-006）──────────────────────────────────────


class TestSnapshotTextCompliance:
    """快照**文本层**合规（``contracts/snapshot-format.md`` §3 / §5）。"""

    def test_file_is_utf8_without_bom(self) -> None:
        """编码 MUST 是 **UTF-8**（**无 BOM**）。"""
        raw = SNAPSHOT_PATH.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), "快照文件带 BOM"
        raw.decode("utf-8")

    def test_line_endings_are_lf(self) -> None:
        """换行 MUST 是 **LF**（**不** CRLF）。"""
        raw = SNAPSHOT_PATH.read_bytes()
        assert b"\r\n" not in raw, "快照文件含 CRLF"

    def test_last_line_has_a_trailing_newline(self) -> None:
        """**末行带换行**（文件以 ``\\n`` 结尾）。"""
        raw = SNAPSHOT_PATH.read_bytes()
        assert raw.endswith(b"\n"), "快照文件未以换行结尾"

    def test_text_contains_no_non_deterministic_content(self) -> None:
        """MUST NOT 含时间戳 / 绝对路径 / Python 版本号 / 内存地址。"""
        text = SNAPSHOT_PATH.read_text(encoding="utf-8")
        assert not re.search(r"0x[0-9a-fA-F]{6,}", text), "快照含内存地址"
        assert not re.search(r"\bobject at\b", text), "快照含 repr 形态的对象"
        assert not re.search(r"\d{4}-\d{2}-\d{2}", text), "快照含日期"
        assert not re.search(r"\b\d{1,2}:\d{2}:\d{2}\b", text), "快照含时刻"
        assert not re.search(r"(?m)^\s*/", text), "快照含绝对路径"
        assert sys.version.split()[0] not in text, "快照含 Python 版本号"
        for token in ("/home/", "/Users/", "C:\\"):
            assert token not in text, f"快照含绝对路径片段 {token!r}"

    def test_top_level_entries_match_the_current_export_surface(self) -> None:
        """顶级条目集合 MUST == 门面**当前**的导出面集合（随 US3 增长而增长）。"""
        text = SNAPSHOT_PATH.read_text(encoding="utf-8")
        names = {
            match.group(1)
            for match in re.finditer(r"(?m)^\[\w+\] (\w+)", text)
        }
        import freegraph.graph as graph

        assert names == set(graph.__all__), (
            f"快照的顶级条目集合与门面导出面不一致："
            f"{names ^ set(graph.__all__)}（对称差）"
        )

    def test_no_comment_lines_between_entries(self) -> None:
        """注释头 MUST **只**出现在文件**顶部**（T-8）。"""
        lines = SNAPSHOT_PATH.read_text(encoding="utf-8").splitlines()
        seen_entry = False
        for line in lines:
            if line.startswith("["):
                seen_entry = True
                continue
            if line.startswith("#"):
                assert not seen_entry, f"条目之间出现注释行：{line!r}"
