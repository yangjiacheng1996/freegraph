# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""门禁 **G21–G30** 的**正向断言 + 反向用例**（B3F1）。

本文件的**需求本体就是门禁判据** —— 8 条**强制**反向用例（SC-009）：
G21 · G22 · G23 · G24 · G25 · G26 · G29 · G30 ⇒ 每条都 MUST 在**隔离副本**上
注入违规并断言门禁**失败且指名** ⇒ 否则「恰好没触发」与「判据有效」不可区分。

**纪律**：

* 反向用例 MUST 以 ``--root <isolated_copy>``（及 G25 的 ``--registry``、
  G29 的 ``--baseline``）**指向隔离副本** ⇒ 否则注入不可见 ⇒ **用例空转**；
* MUST NOT 修改**冻结面**（层注册表 ⇒ 用**副本**）；
* 工作树 MUST **逐字不变**（裁定 9 · SC-010）⇒ 用 ``git status --porcelain``
  的**前后对比**判定（工作树本来就可能有未提交改动 ⇒ 「干净」不是判据）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import _gatekit


# ── 工具 ──────────────────────────────────────────────────────────────────


def run_gate(
    script: str, *args: str, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """调用一个门禁脚本（**可独立执行**的入口）⇒ 退出码 + 输出。"""
    gates_dir = Path(__file__).resolve().parents[2] / "harness" / "scripts" / "gates"
    return subprocess.run(
        [sys.executable, str(gates_dir / script), *args],
        capture_output=True,
        text=True,
        timeout=1800,
        cwd=str(cwd) if cwd else None,
        check=False,
    )


def git_status(repo_root: Path) -> str:
    """工作树的 ``git status --porcelain``（**前后对比** ⇒ 判定「逐字不变」）。"""
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain"],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return proc.stdout


def inject_dependency(project: Path, requirement: str) -> None:
    """往副本的 ``pyproject.toml`` 基础依赖里注入一条声明（负向验证用）。"""
    text = project.read_text(encoding="utf-8")
    marker = "dependencies = []"
    assert marker in text, "副本的 dependencies 段形态与预期不符"
    project.write_text(
        text.replace(marker, f'dependencies = ["{requirement}"]', 1), encoding="utf-8"
    )


def remove_dependency(project: Path) -> None:
    """撤销注入（恢复基础依赖为空集）。"""
    text = project.read_text(encoding="utf-8")
    text = text.replace('dependencies = ["langchain-core>=0.3"]', "dependencies = []")
    text = text.replace('dependencies = ["langsmith>=0.1"]', "dependencies = []")
    text = text.replace('dependencies = ["langgraph-checkpoint>=2.0"]', "dependencies = []")
    text = text.replace('dependencies = ["langgraph-api>=0.1"]', "dependencies = []")
    text = text.replace('dependencies = ["deepagents>=0.1"]', "dependencies = []")
    project.write_text(text, encoding="utf-8")


def write_dist_info(root: Path, name: str, version: str, body: str) -> Path:
    """造一份**假元数据**（``<name>-<version>.dist-info/METADATA``）。

    **必填四个头**：``Metadata-Version`` / ``Name`` / ``Version`` /
    ``License-Expression``；且 ``Name`` / ``Version`` MUST 与目录名一致 ⇒ 否则
    解析不出合法 distribution ⇒ 用例**空转**。
    """
    directory = root / f"{name}-{version}.dist-info"
    directory.mkdir(parents=True, exist_ok=True)
    metadata = directory / "METADATA"
    metadata.write_text(
        "Metadata-Version: 2.4\n"
        f"Name: {name}\n"
        f"Version: {version}\n" + body,
        encoding="utf-8",
    )
    return metadata


# ── G21 · 依赖闭包黑名单（反向用例 · SC-009 之一）─────────────────────────


@pytest.mark.parametrize(
    ("requirement", "package"),
    [
        ("langchain-core>=0.3", "langchain-core"),
        ("langsmith>=0.1", "langsmith"),
        ("langgraph-checkpoint>=2.0", "langgraph-checkpoint"),
        ("langgraph-api>=0.1", "langgraph-api"),
        ("deepagents>=0.1", "deepagents"),
    ],
)
def test_g21_rejects_blacklisted_dependency(
    requirement: str, package: str, isolated_copy: Path
) -> None:
    """G21 · 黑名单命中 ⇒ **失败**并输出**包名 + 规则编号 + 修复指引**。"""
    project = isolated_copy / "pyproject.toml"
    inject_dependency(project, requirement)
    result = run_gate(
        "gate_G21_dependencies.py", "--project", str(project), cwd=isolated_copy
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"注入 {package} 后门禁仍通过：\n{output}"
    assert package in output, f"输出未点名 {package}：\n{output}"
    assert "规则编号" in output and "G21-" in output, f"输出缺规则编号：\n{output}"
    assert "修复指引" in output, f"输出缺修复指引：\n{output}"
    remove_dependency(project)
    reverted = run_gate(
        "gate_G21_dependencies.py", "--project", str(project), cwd=isolated_copy
    )
    assert reverted.returncode == 0, f"撤销后门禁仍失败：\n{reverted.stdout}"


# ── G23 · 许可证白名单（反向用例 · SC-009 之一）───────────────────────────


def test_g23_rejects_agpl_license(isolated_copy: Path) -> None:
    """G23 · ``AGPL-3.0-or-later`` ⇒ **失败并指名**（禁用清单）。"""
    write_dist_info(
        isolated_copy, "agpl-pkg", "1.0.0", "License-Expression: AGPL-3.0-or-later\n"
    )
    result = run_gate("gate_G23_licenses.py", "--root", str(isolated_copy))
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"AGPL 元数据未被拒：\n{output}"
    assert "agpl-pkg" in output, f"输出未点名 agpl-pkg：\n{output}"
    assert "AGPL" in output, f"输出未点名禁用清单族：\n{output}"


def test_g23_rejects_license_variant(isolated_copy: Path) -> None:
    """G23 · ``MIT-CMU``（变体标识符）⇒ **被拒**（裁定 18「变体不放行」）。"""
    write_dist_info(
        isolated_copy, "variant-pkg", "1.0.0", "License-Expression: MIT-CMU\n"
    )
    result = run_gate("gate_G23_licenses.py", "--root", str(isolated_copy))
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"MIT-CMU 变体未被拒：\n{output}"
    assert "variant-pkg" in output, f"输出未点名 variant-pkg：\n{output}"
    assert "MIT-CMU" in output, f"输出未点名实测到的标识：\n{output}"


def test_g23_rejects_missing_evidence(isolated_copy: Path) -> None:
    """G23 · 四级证据链**全无** ⇒ **失败并指名**（FR-006 ② · MUST NOT skip）。"""
    write_dist_info(isolated_copy, "bare-pkg", "1.0.0", "Summary: 无任何许可信息\n")
    result = run_gate("gate_G23_licenses.py", "--root", str(isolated_copy))
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"取不到许可证明时未被拒：\n{output}"
    assert "bare-pkg" in output, f"输出未点名 bare-pkg：\n{output}"


def test_g23_is_not_an_empty_gate(isolated_copy: Path) -> None:
    """G23 · **正常路径**下被检查的包数 > 0 ⇒ **非空门禁**（违宪防护）。"""
    result = run_gate("gate_G23_licenses.py", "--root", str(isolated_copy))
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"正常路径不该失败：\n{output}"
    assert "被检查的包数 = 0" not in output, f"G23 退化为空门禁：\n{output}"


# ── G24 · 配置层（反向用例 · SC-009 之一）─────────────────────────────────


def test_g24_rejects_config_layer_env_read(isolated_copy: Path) -> None:
    """G24 · 读取 ``LANGSMITH_*`` ⇒ **失败并指名文件 + 行号**。"""
    probe = isolated_copy / "src" / "freegraph" / "_probe.py"
    probe.write_text(
        "import os\n" "\n" "def read_key() -> str:\n"
        '    return os.environ["LANGSMITH_API_KEY"]\n',
        encoding="utf-8",
    )
    result = run_gate("gate_G24_config_layer.py", "--root", str(isolated_copy))
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"配置层读取未被拦：\n{output}"
    assert "src/freegraph/_probe.py" in output, f"输出未指名文件：\n{output}"
    assert "LANGSMITH_API_KEY" in output, f"输出未点名被读的变量：\n{output}"


def test_g24_rejects_any_env_read(isolated_copy: Path) -> None:
    """G24 · ``os.getenv("ANYTHING")`` ⇒ **同样失败**（内核零环境变量读取）。"""
    probe = isolated_copy / "src" / "freegraph" / "_probe.py"
    probe.write_text(
        "import os\n" "\n" "def read_any() -> str:\n"
        '    return os.getenv("ANYTHING")\n',
        encoding="utf-8",
    )
    result = run_gate("gate_G24_config_layer.py", "--root", str(isolated_copy))
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"任意环境变量读取未被拦：\n{output}"
    assert "src/freegraph/_probe.py" in output, f"输出未指名文件：\n{output}"


def test_g24_rejects_imported_environ(isolated_copy: Path) -> None:
    """G24 · ``from os import getenv`` ⇒ **同样失败**（导入形态不可绕过）。"""
    probe = isolated_copy / "src" / "freegraph" / "_probe.py"
    probe.write_text(
        "from os import getenv\n" "\n" "def read_any() -> str:\n"
        '    return getenv("ANYTHING")\n',
        encoding="utf-8",
    )
    result = run_gate("gate_G24_config_layer.py", "--root", str(isolated_copy))
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"导入形态的环境变量读取未被拦：\n{output}"
    assert "src/freegraph/_probe.py" in output, f"输出未指名文件：\n{output}"


# ── G25 · 导入图单向（反向用例 · SC-009 之一）─────────────────────────────


def _registry_with(entries: list[tuple[str, str]]) -> str:
    """造一份**层注册表副本**（追加条目）⇒ MUST NOT 改动冻结面。"""
    source = (
        Path(__file__).resolve().parents[2]
        / "specs"
        / "b3f1-scaffold-ci-gates"
        / "contracts"
        / "layer-registry.md"
    )
    text = source.read_text(encoding="utf-8")
    extra = ["| 路径 | 层 | 例外 | 说明 |", "|---|---|---|---|"]
    for path, layer in entries:
        extra.append(f"| `{path}` | `{layer}` | — | 反向用例注入 |")
    return text + "\n" + "\n".join(extra) + "\n"


def _g25_on(
    copy: Path, entries: list[tuple[str, str]], probes: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """在隔离副本上跑 G25（注册表用**副本**）。"""
    registry = copy / "layer-registry.md"
    registry.write_text(_registry_with(entries), encoding="utf-8")
    for name, source in probes.items():
        target = copy / "src" / "freegraph" / name
        target.write_text(source, encoding="utf-8")
    return run_gate(
        "gate_G25_import_graph.py",
        "--root",
        str(copy),
        "--registry",
        str(registry),
        cwd=copy,
    )


def test_g25_rejects_reverse_import(isolated_copy: Path) -> None:
    """G25 · **L1 import L3** ⇒ **失败**（反向 import）。"""
    result = _g25_on(
        isolated_copy,
        [("src/freegraph/_probe_l1.py", "L1")],
        {
            "_probe_l1.py": (
                "from ._stategraph import StateGraph\n"
                "\n"
                "__all__ = [\"StateGraph\"]\n"
            )
        },
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"反向 import 未被拦：\n{output}"
    assert "_probe_l1.py" in output, f"输出未指名违规文件：\n{output}"
    assert "G25-" in output, f"输出缺规则编号：\n{output}"


def test_g25_rejects_cross_layer_import_of_l2(isolated_copy: Path) -> None:
    """G25 · **跨层单元 import L2** ⇒ **失败**（跨层只可 import L1 与更低层）。"""
    result = _g25_on(
        isolated_copy,
        [("src/freegraph/_probe_cross.py", "—")],
        {
            "_probe_cross.py": (
                "from ._primitives import Send\n" "\n" "__all__ = [\"Send\"]\n"
            )
        },
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"跨层 import L2 未被拦：\n{output}"
    assert "_probe_cross.py" in output, f"输出未指名违规文件：\n{output}"


def test_g25_rejects_l2_to_l2_same_layer(isolated_copy: Path) -> None:
    """G25 · **L2 → L2 同层** ⇒ **失败**（L2–L5 之间禁止横向依赖）。"""
    result = _g25_on(
        isolated_copy,
        [
            ("src/freegraph/_probe_l2a.py", "L2"),
            ("src/freegraph/_probe_l2b.py", "L2"),
        ],
        {
            "_probe_l2a.py": (
                "from ._probe_l2b import helper\n" "\n" "__all__ = [\"helper\"]\n"
            ),
            "_probe_l2b.py": "def helper() -> int:\n    return 1\n",
        },
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"L2 → L2 同层未被拦：\n{output}"
    assert "_probe_l2a.py" in output, f"输出未指名违规文件：\n{output}"


def test_g25_allows_l1_to_l1_same_layer(isolated_copy: Path) -> None:
    """G25 · **L1 → L1 同层** ⇒ **通过**（契约层内部 · 已冻结的既有形态）。"""
    result = _g25_on(
        isolated_copy,
        [
            ("src/freegraph/_probe_l1a.py", "L1"),
            ("src/freegraph/_probe_l1b.py", "L1"),
        ],
        {
            "_probe_l1a.py": (
                "from ._probe_l1b import helper\n" "\n" "__all__ = [\"helper\"]\n"
            ),
            "_probe_l1b.py": "def helper() -> int:\n    return 1\n",
        },
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"L1 → L1 同层被误判为违规：\n{output}"


def test_g25_allows_l6_to_l6_same_layer(isolated_copy: Path) -> None:
    """G25 · **L6 → L6 同层** ⇒ **通过**（应用层内部 · 铁律 4）。"""
    result = _g25_on(
        isolated_copy,
        [
            ("src/freegraph/_probe_l6a.py", "L6"),
            ("src/freegraph/_probe_l6b.py", "L6"),
        ],
        {
            "_probe_l6a.py": (
                "from ._probe_l6b import helper\n" "\n" "__all__ = [\"helper\"]\n"
            ),
            "_probe_l6b.py": "def helper() -> int:\n    return 1\n",
        },
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"L6 → L6 同层被误判为违规：\n{output}"


def test_g25_rejects_top_level_package_import(isolated_copy: Path) -> None:
    """G25 · 顶层包 import 内部层 ⇒ **失败**（注册表 §0.3 **L-1**）。"""
    init = isolated_copy / "src" / "freegraph" / "__init__.py"
    init.write_text(
        "from .contracts import StateDict\n" "\n" "__all__ = [\"StateDict\"]\n",
        encoding="utf-8",
    )
    result = run_gate(
        "gate_G25_import_graph.py",
        "--root",
        str(isolated_copy),
        "--registry",
        str(
            Path(__file__).resolve().parents[2]
            / "specs"
            / "b3f1-scaffold-ci-gates"
            / "contracts"
            / "layer-registry.md"
        ),
        cwd=isolated_copy,
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"顶层包的内部 import 未被拦：\n{output}"
    assert "__init__.py" in output, f"输出未指名顶层包：\n{output}"


# ── G26 · 网络静态扫描（反向用例 · SC-009 之一）───────────────────────────


def test_g26_rejects_network_client(isolated_copy: Path) -> None:
    """G26 · ``import socket`` ⇒ **失败并指名文件 + 行号**。"""
    probe = isolated_copy / "src" / "freegraph" / "_probe.py"
    probe.write_text("import socket\n" "\n" "__all__ = []\n", encoding="utf-8")
    result = run_gate("gate_G26_network_static.py", "--root", str(isolated_copy))
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"网络客户端未被拦：\n{output}"
    assert "src/freegraph/_probe.py" in output, f"输出未指名文件：\n{output}"
    assert "socket" in output, f"输出未点名网络客户端：\n{output}"


# ── G29 · 契约门禁载体（反向用例 · SC-009 之一）───────────────────────────


def test_g29_rejects_modified_baseline(isolated_copy: Path) -> None:
    """G29 · 只读基准被改动一个字 ⇒ **失败并给出 diff**。"""
    target = isolated_copy / "harness" / "demo" / "target.py"
    text = target.read_text(encoding="utf-8")
    target.write_text(text.replace("llm_calls", "llm_calls_", 1), encoding="utf-8")
    result = run_gate(
        "gate_G29_contract_carrier.py",
        "--root",
        str(isolated_copy),
        "--baseline",
        "HEAD",
        cwd=isolated_copy,
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"只读基准被改动却未失败：\n{output}"
    assert "diff" in output.lower(), f"输出未给出 diff：\n{output}"
    assert "target.py" in output, f"输出未指名基准文件：\n{output}"


def test_g29_detects_real_assertion_failure(isolated_copy: Path) -> None:
    """G29 · 退出码 1 且失败**非**源于 ``NotImplementedError`` ⇒ **真断言失败**。"""
    script = isolated_copy / "harness" / "demo" / "graph_core.py"
    script.write_text(
        "print('  ✘ A1 某某 · 用例组 case_x 未抛异常即完成 — ValueError: boom')\n"
        "raise SystemExit(1)\n",
        encoding="utf-8",
    )
    result = run_gate(
        "gate_G29_contract_carrier.py", "--root", str(isolated_copy), cwd=isolated_copy
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"真断言失败未被拦：\n{output}"
    assert "真断言失败" in output, f"输出未区分真断言失败：\n{output}"


def test_g29_reports_environment_not_ready(isolated_copy: Path) -> None:
    """G29 · 退出码 1 且失败**全部**源于 ``NotImplementedError`` ⇒ **环境未就绪**（绿）。"""
    script = isolated_copy / "harness" / "demo" / "graph_core.py"
    script.write_text(
        "print('  ✘ A1 某某 · 用例组 case_x 未抛异常即完成 — "
        "NotImplementedError: add_node 尚未接线')\n"
        "raise SystemExit(1)\n",
        encoding="utf-8",
    )
    result = run_gate(
        "gate_G29_contract_carrier.py", "--root", str(isolated_copy), cwd=isolated_copy
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"环境未就绪被误判为真断言失败：\n{output}"
    assert "ENV_NOT_READY" in output, f"输出未标出环境未就绪：\n{output}"


def test_g29_check_compat_reports_not_landed(repo_root: Path) -> None:
    """G29 · ``--check-compat``：``COMPAT.md`` 不存在 ⇒ 报告「未落地」且**退出码 0**。"""
    result = run_gate("gate_G29_contract_carrier.py", "--check-compat", cwd=repo_root)
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"「未落地」不应阻断：\n{output}"
    assert "未落地" in output, f"输出未报告「未落地」：\n{output}"


# ── G30 · 署名头 + 第三方品牌资产（反向用例 · SC-009 之一）───────────────


def test_g30_rejects_missing_signature_header(isolated_copy: Path) -> None:
    """G30 · 删掉署名头 ⇒ **失败并指名该文件**。"""
    target = isolated_copy / "src" / "freegraph" / "_primitives.py"
    lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
    target.write_text("".join(lines[1:]), encoding="utf-8")
    result = run_gate("gate_G30_attribution.py", "--root", str(isolated_copy))
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"缺署名头未被拦：\n{output}"
    assert "_primitives.py" in output, f"输出未指名该文件：\n{output}"


def test_g30_rejects_third_party_brand_asset(isolated_copy: Path) -> None:
    """G30 · 第三方品牌资产（``.svg``）⇒ **失败并指名该文件**（FR-021 · SC-016）。"""
    asset = isolated_copy / "src" / "freegraph" / "third-party-logo.svg"
    asset.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><text>third party</text></svg>\n',
        encoding="utf-8",
    )
    result = run_gate("gate_G30_attribution.py", "--root", str(isolated_copy))
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"第三方品牌资产未被拦：\n{output}"
    assert "third-party-logo.svg" in output, f"输出未指名该文件：\n{output}"


# ── 负向验证的端到端用例（验收判据 A1 · SC-001 / SC-010）─────────────────


def test_g21_self_test_negative_end_to_end(repo_root: Path) -> None:
    """**负向验证**（端到端）—— 门禁**失败** + 撤销后**通过** + 工作树**逐字不变**。"""
    before = git_status(repo_root)
    result = run_gate(
        "gate_G21_dependencies.py", "--self-test-negative", cwd=repo_root
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"自检失败（自检通过 ⇒ 退出码 0）：\n{output}"
    assert "langchain-core" in output, f"自检输出未点名 langchain-core：\n{output}"
    after = git_status(repo_root)
    assert before == after, "负向验证改动了工作树（SC-010 · 裁定 9）"


def test_worktree_is_unchanged_after_negative_verification(
    repo_root: Path, isolated_copy: Path
) -> None:
    """负向验证后**原工作树逐字不变**（SC-010）。"""
    before = git_status(repo_root)
    project = isolated_copy / "pyproject.toml"
    inject_dependency(project, "langchain-core>=0.3")
    run_gate(
        "gate_G21_dependencies.py", "--project", str(project), cwd=isolated_copy
    )
    assert git_status(repo_root) == before, "负向验证改动了原工作树"


# ── G27 · 零出站归因（合成调用栈 · 四种形态）───────────────────────────────


def test_egress_attribution_four_stack_shapes() -> None:
    """归因函数的**四种栈形态**（**合成调用栈** · MUST NOT 依赖真实出网）。"""
    framework = _gatekit.StackFrame(module="freegraph.graph", path="freegraph/graph.py")
    stdlib = _gatekit.StackFrame(module="socket", path="socket.py")
    user_tool = _gatekit.StackFrame(module="user_tools", path="/tmp/user_tools.py")
    user_script = _gatekit.StackFrame(module="__main__", path="/tmp/script.py")
    # ① freegraph 内部模块直接联网 ⇒ 框架出站
    assert _gatekit.attribute_egress([stdlib, framework]) == "framework"
    # ② 用户工具函数联网（freegraph 只是调用方）⇒ 用户出站
    assert (
        _gatekit.attribute_egress([stdlib, user_tool, framework]) == "user"
    ), "用户工具函数联网不得被误判为框架出站（裁定 19）"
    # ③ 用户脚本直接联网 ⇒ 用户出站
    assert _gatekit.attribute_egress([stdlib, user_script]) == "user"
    # ④ freegraph 直接使用 socket ⇒ 框架出站
    assert (
        _gatekit.attribute_egress([stdlib, _gatekit.StackFrame(module="freegraph", path="freegraph/__init__.py")])
        == "framework"
    )
    # 全是标准库帧 ⇒ 用户出站
    assert _gatekit.attribute_egress([stdlib]) == "user"


def test_egress_attribution_records_user_egress(egress_recorder) -> None:
    """**真实**发起一次用户出站 ⇒ 被归因为「**用户出站**」（SC-006 双向可验证）。

    **该连接在 CI 上必然失败**（无监听端口 ⇒ ``ConnectionRefusedError``）⇒
    夹具 MUST **先记录再放行**（记录发生在 connect 之前）⇒ 用例 MUST **捕获**
    该异常 ⇒ 否则未捕获异常 ⇒ 用例失败 ⇒ 7/7 作业必红。
    ⇒ 该用例 MUST 进**断网排除清单**（断网下连接必然失败 · 属**假红**）。
    """
    import socket

    with pytest.raises(OSError):
        socket.create_connection(("127.0.0.1", 9), timeout=0.5)
    assert egress_recorder, "出站记录为空 ⇒ 夹具没有记录到连接"
    assert egress_recorder[0].attribution == "user", (
        f"用户出站被误判为 {egress_recorder[0].attribution}"
    )


def test_framework_egress_is_zero(egress_recorder) -> None:
    """「**框架出站**」条目数 == 0（SC-006 · 不变量 6）。"""
    framework = [record for record in egress_recorder if record.attribution == "framework"]
    assert framework == [], f"出现了框架出站：{framework}"


# ── G22 · 隔离环境断言（Linux 专属）───────────────────────────────────────


@pytest.mark.linux_only
def test_g22_isolated_env_closure_is_empty(repo_root: Path) -> None:
    """G22 · 隔离 venv 里**基础安装的第三方依赖闭包 == 空集**（SC-002）。"""
    result = run_gate(
        "gate_G22_isolated_env.py", "--target-root", str(repo_root), cwd=repo_root
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"隔离环境断言失败：\n{output}"
    assert "第三方包数 == 0" in output, f"输出未给出闭包为空集的证据：\n{output}"
    assert "sys.modules 无 langchain 家族" in output, f"输出未给出加载面证据：\n{output}"


@pytest.mark.linux_only
def test_g22_isolated_env_negative_case(isolated_copy: Path) -> None:
    """G22 · 反向用例 —— 注入 ``langchain-core`` ⇒ 场景② **失败**并指名。

    **注入的模块名 MUST 是 ``langchain_core``**（不是 ``langchain`` ——
    ``langchain-core`` 只提供顶层包 ``langchain_core``、**不提供** ``langchain``
    ⇒ 注入 ``import langchain`` 会抛 ``ModuleNotFoundError``（**导入崩溃**，
    而非「sys.modules 中出现了 langchain 家族」）⇒ 该反向用例验证的是
    **另一件事**、且掩盖了本应验证的断言）。

    **探针 MUST 落在副本的 ``src/freegraph/__init__.py``** —— 顶层包是**惰性
    空壳** ⇒ 新建的 ``_probe.py`` **永不被加载** ⇒ 注入落在其上会**空转**。
    """
    init = isolated_copy / "src" / "freegraph" / "__init__.py"
    init.write_text(
        "import langchain_core\n" "\n" '__version__ = "0.0.3"\n', encoding="utf-8"
    )
    result = run_gate(
        "gate_G22_isolated_env.py", "--target-root", str(isolated_copy),
        cwd=isolated_copy,
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"注入 langchain_core 后场景② 仍通过：\n{output}"
    assert "langchain_core" in output, f"输出未指名 langchain_core：\n{output}"


# ── 脚手架断言（FR-001 / FR-002 / FR-003 / FR-004）─────────────────────────


def test_scaffold_base_install_closure_is_empty(repo_root: Path) -> None:
    """**基础安装**的依赖闭包 MUST 为空集 —— 判据 = **无 ``extra ==`` 标记**的
    ``Requires-Dist`` 条目数 == 0（声明 extras 后 ``Requires-Dist`` **非** ``None``）。
    """
    import importlib.metadata as metadata

    requires = metadata.requires("freegraph") or []
    base = [item for item in requires if "extra ==" not in item]
    assert base == [], f"基础安装拉起了 {base}"


def test_scaffold_extras_are_independently_optional(repo_root: Path) -> None:
    """四个 extra **各自独立可选**（不装即不拉起其依赖）。"""
    import tomllib

    data = tomllib.loads(
        (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    )
    extras = data["project"]["optional-dependencies"]
    assert set(extras) == {"pydantic", "checkpoint", "otel", "png"}, extras
    assert extras["otel"] == [
        "opentelemetry-api>=1.20",
        "opentelemetry-sdk>=1.20",
    ], "〔otel〕MUST 恰为 api + sdk（MUST NOT 含任何 exporter · 裁定 21）"
    assert extras["png"] == ["playwright>=1.40"], "〔png〕的后端 = playwright（宪法 v1.5.0）"


def test_scaffold_py_typed_is_empty(repo_root: Path) -> None:
    """``py.typed`` MUST 存在且**大小 == 0**（PEP 561 · FR-002）。"""
    marker = repo_root / "src" / "freegraph" / "py.typed"
    assert marker.is_file(), "py.typed 不存在"
    assert marker.stat().st_size == 0, "py.typed MUST 为空"


def test_scaffold_requires_python_has_no_upper_bound(repo_root: Path) -> None:
    """``requires-python`` MUST 为 ``>=3.11`` 且**无任何 ``<`` 上界**（FR-003）。"""
    import tomllib

    data = tomllib.loads(
        (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    )
    requires_python = data["project"]["requires-python"]
    assert requires_python == ">=3.11", requires_python
    assert "<" not in requires_python, requires_python


# ── 质量门禁 ① 的存在性检查（SC-003 ①）────────────────────────────────────


def test_quality_gate_artifact_existence(repo_root: Path) -> None:
    """**规格门禁 / 人工门禁 / 证据门禁**三道**人工评审**门禁的**存在性**检查。

    **MUST NOT** 断言「内容已填」—— 内容复核由**人工**承担（T055）⇒ 否则
    Phase 1–6 的中间态必红（违反 PR-4）。
    """
    spec = repo_root / "specs" / "b3f1-scaffold-ci-gates" / "spec.md"
    assert spec.is_file() and spec.stat().st_size > 0, "规格门禁的工件缺失或为空"
    record = (
        repo_root / "harness" / "verification" / "B3F1" / "manual-verification.md"
    )
    assert record.is_file(), "人工门禁的记录缺失"
    text = record.read_text(encoding="utf-8")
    for section in ("## 1. 环境", "## 2. 步骤", "## 3. 实际输出", "## 4. 结论", "## 5. 遗留问题"):
        assert section in text, f"人工验证记录缺小节：{section}"
    assert "来源覆盖表" in text, "证据门禁的「来源覆盖表」缺失（宪法原则 VIII）"
    assert "三" in text and "门禁" in text, "缺「宪法质量门禁缺口」的登记小节"
