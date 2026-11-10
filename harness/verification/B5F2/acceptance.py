#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**B5F2** 人工验收脚本（稀疏状态读取 + 差分测试夹具）。

定位
----
本脚本是 **B5F2 这个 feature 的人工验收入口**——**开发期**（v1.0 之前）逐 feature
验收用；**v1.0 完成后的端到端验收**在 ``harness/demo/``。

**一条命令跑完全部验收**（FR-039 ①）—— 验收闸口 **V1–V12** + 全部成功标准
SC-001 … SC-033 + 覆盖率取证 + 10 条门禁的实跑结果，**不必**手工逐条执行
（对照 ``specs/b5f2-sparse-state-read/quickstart.md`` 的 12 节手册）。

覆盖的分组（**逐组对应一个验收闸口**）：

* **V1** C4 稀疏状态读（**否定式**断言 · 验收判据 **A1 / A2**）；
* **V2** 挂载点接线（**C4 = landed** · **C8 = not-landed**）；
* **V3** G2 门禁（``tests/contracts/**`` 零 ``freegraph.*`` 导入）；
* **V4 / V5** 稀疏读语义（普通 ``dict`` · key 集合 / 顺序 · ``None`` 值 ·
  ``skip_empty`` 两分支 · **Edge Cases**）；
* **V6** fresh 读（视图 · **零污染** · 未知 key · 归约器抛错 ·
  **两个稀疏入口逐字相等** · **已知面**）；
* **V7 / V8** 差分夹具（**三项投影**逐字段相等 · 上游实测基线对齐 ·
  **缺席即 skip**）；
* **V9** 依赖红线（``Requires-Dist`` **整体为空** · 内核零上游导入 ·
  **依赖组的正向枚举** · CI 的 ``--group`` 白名单）；
* **V10** 全量测试 + 10 条门禁（**零新增门禁编号**）；
* **V11** 覆盖率取证（``read.py`` 行 / 分支 **100%**）；
* **V12** 冻结面审计（**18 / 7 / 14**）+ 跨 feature 接线（**五处**）。

依赖
----
**只 import Python 标准库**（+ 被验收的 ``freegraph`` 本身 + 仓库自带的
``tests/differential`` 包）——**零第三方依赖**。

⚠️ **覆盖率工具是例外**（research **D-13**）——``coverage`` 是**开发期工具**
⇒ **不进**仓库依赖声明 ⇒ 本机未装时该段标「◌ 环境未就绪」（**不判失败**）
⇒ 装法：``uv pip install coverage``。

⚠️ **上游是例外**——差分夹具需要 ``langgraph``（**PEP 735** 的 ``differential``
依赖组）⇒ 缺席时该组标「◌ 环境未就绪」（**skip ≠ fail** · FR-019）
⇒ 装法：``uv pip install --group differential``。

两态运行
--------
| 情形 | 行为 |
|---|---|
| 当前环境**已安装** freegraph | 测**发行产物** |
| 当前环境**未安装** | 自动把 ``<repo>/src`` 插入 ``sys.path``（源码优先），测**源码树**；依赖闭包那条判**不判失败**，标「◌ 环境未就绪」 |

用法
----
    python3 harness/verification/B5F2/acceptance.py                    # 跑全部
    python3 harness/verification/B5F2/acceptance.py --record out.md    # 同时生成验收记录片段
    python3 harness/verification/B5F2/acceptance.py --require-installed # 把「未安装」判为失败
    python3 harness/verification/B5F2/acceptance.py --skip-coverage    # 跳过覆盖率取证段（快）
    python3 harness/verification/B5F2/acceptance.py --skip-gates       # 跳过门禁实跑段（快）

退出码：``0`` = PASS · ``1`` = FAIL · ``2`` = 环境未就绪。
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import operator
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Annotated, Any, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_DIR = REPO_ROOT / "specs" / "b5f2-sparse-state-read"
CONTRACT_PATH = SPEC_DIR / "contracts" / "read-contract.md"
FIXTURE_CONTRACT_PATH = SPEC_DIR / "contracts" / "differential-fixture.md"
LAYER_REGISTRY = (
    REPO_ROOT / "specs" / "b3f1-scaffold-ci-gates" / "contracts" / "layer-registry.md"
)
ARCHITECTURE_GATES = (
    REPO_ROOT
    / "specs"
    / "b3f1-scaffold-ci-gates"
    / "contracts"
    / "architecture-gates.md"
)
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PYPROJECT = REPO_ROOT / "pyproject.toml"
README = REPO_ROOT / "README.md"
NOTICES = REPO_ROOT / "THIRD_PARTY_NOTICES"
MOUNT_POINT = REPO_ROOT / "tests" / "contracts" / "test_contract_regressions.py"
CONTRACT_GUARD_TEST = REPO_ROOT / "tests" / "runtime" / "test_read_contract.py"
FEATURES_DIR = REPO_ROOT / "harness" / "features"
GATES_DIR = REPO_ROOT / "harness" / "scripts" / "gates"

#: 当前解释器（提示信息用）。
INTERPRETER = sys.executable

#: 仓库自带的 ``.venv``（提示信息用 · **不存在**时退化）。
PROJECT_VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"

#: 契约层 / 门面 / L2 内部 API 的公开符号面（**冻结面** · SC-011 / SC-029）。
CONTRACT_PUBLIC_SYMBOL_COUNT = 18
FACADE_PUBLIC_SYMBOL_COUNT = 7
RUNTIME_PUBLIC_SYMBOL_COUNT = 14

#: 门禁总数（**G1–G30** 的连续性是不变量 · SC-011）。
GATE_TOTAL = 30

#: 覆盖率 MUST **100%** 的文件（**阻断判据** · SC-018 · FR-027 ②）。
FULL_COVERAGE_FILES = (
    "src/freegraph/runtime/read.py",
    "src/freegraph/runtime/__init__.py",
)

#: **本地直跑**的门禁（纯本地 · 确定性 · **无网络 / 无命名空间**依赖）⇒ **硬断言**。
LOCAL_GATES = ("G21", "G23", "G24", "G25", "G26", "G29", "G30")

#: **Linux only** 的门禁（需**网络**（G22 建隔离 venv）/ **网络命名空间**（G28）
#: / **socket 监测**（G27））⇒ 本脚本**只观测不阻断**（由 CI 的 Linux 作业作阻断判据）。
LINUX_ONLY_GATES = ("G22", "G27", "G28")

#: 上游包名（**发行面红线** · 判据 **A5**）。
UPSTREAM_PACKAGE_NAMES = (
    "langgraph",
    "langchain",
    "langsmith",
    "typing_extensions",
    "typing-extensions",
)

#: **唯一**允许声明上游包名的依赖组（PEP 735 · **测试侧**）。
UPSTREAM_ALLOWED_GROUP = "differential"

#: CI 允许出现的 ``--group`` 白名单（**可判定** · FR-037 ④）。
CI_GROUP_WHITELIST = frozenset({"dev", UPSTREAM_ALLOWED_GROUP})

#: 兼容矩阵的章节定位（**不扫全文**）。
COMPAT_MATRIX_PATTERN = re.compile(
    r"^##\s*API\s*兼容矩阵\s*$(.*?)(?=^## |\Z)", re.S | re.M
)

#: 契约 §4 冻结的**不变量编号**（**逐条** · I-1…I-11）。
EXPECTED_INVARIANTS = tuple(f"I-{index}" for index in range(1, 12))

#: 跨 feature 接线的**五处**（宪法 v1.8.0 · FR-031 · FR-036 · FR-037）。
CROSS_FEATURE_WIRINGS = (
    (
        "B7F1",
        FEATURES_DIR / "B7F1_任务准备与super-step循环.md",
        "承接条款（B5F2 → B7F1",
    ),
    (
        "B8F1",
        FEATURES_DIR / "B8F1_条件边路由与fresh读.md",
        "夹具接口口径（B5F2 → B8F1",
    ),
    (
        "B8F1 · 第五处",
        FEATURES_DIR / "B8F1_条件边路由与fresh读.md",
        "MUST 在使用 `local_read` 时显式传 `fresh=True`",
    ),
    (
        "B25F1",
        FEATURES_DIR / "B25F1_双跑验收与迁移说明.md",
        "承接条款（B5F2 → B25F1",
    ),
    (
        "B4F1",
        FEATURES_DIR / "B4F1_schema解析与归约器提取.md",
        "承接条款（B5F2 → B4F1",
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# 极简断言框架（与 harness/verification/B5F1/acceptance.py 同款：单文件可独立运行）
# ─────────────────────────────────────────────────────────────────────────────
_CHECKS = 0
_FAILED: list[str] = []
_SOFT: list[str] = []
_SECTION = ""
_CAPTURE: Any = None


def section(title: str) -> None:
    """开一个新分组（打印小节标题）。"""
    global _SECTION
    _SECTION = title
    print(f"\n[{title}]")


def check(cond: object, label: str, detail: str = "") -> bool:
    """一条**硬断言**（不成立 ⇒ 判失败）。"""
    global _CHECKS
    _CHECKS += 1
    ok = bool(cond)
    if not ok:
        _FAILED.append(f"{_SECTION} · {label}" + (f" — {detail}" if detail else ""))
    print(f"  {'✔' if ok else '✘'} {label}" + (f"  ({detail})" if detail and not ok else ""))
    return ok


def soft(cond: object, label: str, note: str = "") -> bool:
    """**环境未就绪**的检查：不判失败，只标注「待环境就绪」。"""
    global _CHECKS
    _CHECKS += 1
    ok = bool(cond)
    if not ok:
        _SOFT.append(f"{_SECTION} · {label}" + (f" — {note}" if note else ""))
    print(f"  {'✔' if ok else '◌'} {label}" + (f"  ({note})" if note and not ok else ""))
    return ok


def eq(actual: object, expected: object, label: str) -> bool:
    """等值断言（失败时打印期望与实际）。"""
    return check(actual == expected, label, f"期望 {expected!r}，实际 {actual!r}")


# ─────────────────────────────────────────────────────────────────────────────
# 加载被验对象
# ─────────────────────────────────────────────────────────────────────────────
class _EnvironmentNotReady(RuntimeError):
    """**环境未就绪** —— 被验对象既未安装、源码树也不可达（退出码 2）。"""


def _load_runtime() -> tuple[Any, str]:
    """导入 ``freegraph.runtime``，返回 ``(模块, 模式说明)``。

    两态运行（FR-039 ③）：

    * 环境**已安装** freegraph ⇒ 测**发行产物**；
    * 环境**未安装** ⇒ 自动把 ``<repo>/src`` 插入 ``sys.path`` 测**源码树**。

    ⚠️ 两者都不可达 ⇒ 抛 :class:`_EnvironmentNotReady` ⇒ 退出码 **2**
    （**环境未就绪**）—— 与「判失败」（退出码 1）**区分**。
    """
    try:
        import freegraph.runtime as runtime

        return runtime, "发行产物（当前环境已安装 freegraph）"
    except ImportError:
        src = REPO_ROOT / "src"
        if not src.is_dir():
            raise _EnvironmentNotReady(
                f"freegraph 既未安装，且源码树 {src} 不可达"
            ) from None
        sys.path.insert(0, str(src))
        try:
            import freegraph.runtime as runtime
        except ImportError as error:
            raise _EnvironmentNotReady(
                f"源码树 {src} 存在，但 freegraph.runtime 不可导入：{error}"
            ) from error
        return runtime, f"源码树（{src} 已注入 sys.path）"


def _load_differential() -> tuple[Any, str | None]:
    """导入仓库自带的 ``tests/differential`` 包 ⇒ ``(包, 上游版本 | None)``。

    ⚠️ 上游**缺席** ⇒ 返回 ``None`` 版本（**不抛错**）⇒ 差分组标「◌ 环境未就绪」
    （FR-019 · **skip ≠ fail**）。
    """
    tests_dir = REPO_ROOT / "tests"
    if str(tests_dir) not in sys.path:
        sys.path.insert(0, str(tests_dir))
    import differential.runner as runner  # noqa: PLC0415 —— 按需加载

    upstream_version: str | None
    try:
        import importlib.metadata as md

        upstream_version = md.version("langgraph")
    except Exception:  # noqa: BLE001 —— 缺席即「无版本」
        upstream_version = None
    return runner, upstream_version


def _installed() -> bool:
    """当前环境**是否已安装** freegraph。"""
    try:
        import importlib.metadata as md

        md.version("freegraph")
    except Exception:  # noqa: BLE001
        return False
    return True


def _install_hint() -> str:
    """给出「怎么装」的提示（区分**源码树**与**发行产物**两种情形）。"""
    if PROJECT_VENV_PYTHON.is_file():
        return (
            f"uv pip install --python {PROJECT_VENV_PYTHON} -e .   # 发行产物\n"
            f"      uv pip install --python {PROJECT_VENV_PYTHON} coverage   "
            "# 开发期取证工具\n"
            f"      uv pip install --python {PROJECT_VENV_PYTHON} "
            f"--group {UPSTREAM_ALLOWED_GROUP}   # 差分夹具的上游"
        )
    return (
        f"uv pip install --python {INTERPRETER} -e .\n"
        f"      uv pip install --python {INTERPRETER} coverage\n"
        f"      uv pip install --python {INTERPRETER} "
        f"--group {UPSTREAM_ALLOWED_GROUP}"
    )


def finish(title: str) -> int:
    """汇总硬断言并给出退出码（``0`` = PASS · ``1`` = FAIL）。"""
    print(f"\n── {title} 汇总 ──")
    print(f"硬断言 {_CHECKS} 条 · 通过 {_CHECKS - len(_FAILED)} · 失败 {len(_FAILED)}")
    for item in _FAILED:
        print(f"  ✘ {item}")
    if _SOFT:
        print(f"待环境就绪 {len(_SOFT)} 条（不判失败）：")
        for item in _SOFT:
            print(f"  ◌ {item}")
        print("  ⇒ **skip ≠ pass** —— 补齐环境后请重跑：")
        print(f"      {_install_hint()}")
    print("结论：" + ("PASS" if not _FAILED else "FAIL"))
    return 0 if not _FAILED else 1


# ─────────────────────────────────────────────────────────────────────────────
# 工具（**只读** · 零副作用）
# ─────────────────────────────────────────────────────────────────────────────
def _table_cells(line: str) -> list[str]:
    """把一行 Markdown 表格拆成单元格（去首尾空单元格 · 去空白）。"""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    parts = stripped.split("|")
    if parts and not parts[0].strip():
        parts = parts[1:]
    if parts and not parts[-1].strip():
        parts = parts[:-1]
    return [cell.strip() for cell in parts]


def _is_separator(cells: list[str]) -> bool:
    """判定是否表格的**分隔行**。"""
    return bool(cells) and all(set(cell) <= {"-", ":", " "} and cell for cell in cells)


def _section_body(text: str, heading: str) -> list[str]:
    """取出某个 ``## `` 小节的正文行（**不含**小节标题本身）。"""
    collected: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.startswith(heading)
            continue
        if inside:
            collected.append(line)
    return collected


def _public_symbols(path: Path) -> list[str]:
    """从源码里取 ``__all__`` 的字面内容（**不 import** ⇒ 零副作用）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            return list(ast.literal_eval(node.value))
    raise AssertionError(f"{path} 未定义 __all__")


def _dependency_text(sections: object) -> str:
    """把一段依赖声明摊平成**文本**（便于统计包名出现次数）。"""
    if isinstance(sections, dict):
        return " ".join(_dependency_text(value) for value in sections.values())
    if isinstance(sections, (list, tuple)):
        return " ".join(str(item) for item in sections)
    return str(sections)


def _mount_statuses() -> dict[str, str]:
    """解析挂载点文件里的 ``GATE-MOUNT:`` 标记 ⇒ ``{编号: status}``。"""
    found: dict[str, str] = {}
    for line in MOUNT_POINT.read_text(encoding="utf-8").splitlines():
        if "GATE-MOUNT:" not in line:
            continue
        body = line.split("GATE-MOUNT:", 1)[1]
        fields = [item.strip() for item in body.split("·")]
        ident = fields[0].strip()
        status = ""
        for field in fields[1:]:
            if field.startswith("status="):
                status = field.split("=", 1)[1].strip()
        found[ident] = status
    return found


def _contract_invariants() -> list[str]:
    """**解析**读取契约 §4 ⇒ 不变量编号列表（按出现顺序）。"""
    identifiers: list[str] = []
    for line in _section_body(CONTRACT_PATH.read_text(encoding="utf-8"), "## 4."):
        cells = _table_cells(line)
        if len(cells) < 2 or _is_separator(cells):
            continue
        match = re.fullmatch(r"\*\*(I-\d+)\*\*|(I-\d+)", cells[0])
        if match:
            identifiers.append(match.group(1) or match.group(2))
    return identifiers


def _contract_entry_signatures() -> dict[str, str]:
    """**解析**读取契约 §1 ⇒ ``{入口名: 签名文本}``。"""
    signatures: dict[str, str] = {}
    for line in _section_body(CONTRACT_PATH.read_text(encoding="utf-8"), "## 1."):
        cells = _table_cells(line)
        if len(cells) < 2 or _is_separator(cells):
            continue
        if cells[0] not in {"入口 1", "入口 2"}:
            continue
        match = re.search(r"`([^`]+)`", cells[1])
        if not match:
            continue
        text = match.group(1)
        signatures[text.split("(", 1)[0].strip()] = text
    return signatures


def _render_annotation(annotation: Any) -> str:
    """把注解渲染成**文本**（``from __future__ import annotations`` ⇒ 字符串注解）。"""
    if annotation is inspect_empty():
        return ""
    if isinstance(annotation, str):
        return annotation
    return str(annotation)


def inspect_empty() -> Any:
    """``inspect.Parameter.empty`` 的本地副本（避免顶层 import ``inspect``）。"""
    import inspect

    return inspect.Parameter.empty


def _signature_text(func: Any) -> str:
    """把函数的签名渲染成**契约同款文本**（供逐字比对）。"""
    import inspect

    signature = inspect.signature(func)
    parts: list[str] = []
    keyword_only_started = False
    for name, parameter in signature.parameters.items():
        if (
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            and not keyword_only_started
        ):
            parts.append("*")
            keyword_only_started = True
        annotation = _render_annotation(parameter.annotation)
        text = f"{name}: {annotation}" if annotation else name
        if parameter.default is not inspect.Parameter.empty:
            text += f" = {parameter.default!r}"
        parts.append(text)
    rendered = f"({', '.join(parts)})"
    returns = _render_annotation(signature.return_annotation)
    if returns:
        rendered += f" -> {returns}"
    return rendered


def _bound_invariants() -> list[str]:
    """**解析**契约守卫测试里的 ``INVARIANT_TESTS`` ⇒ 已绑定的不变量编号。

    ⚠️ 只取**键**（值是函数引用 ⇒ 不是字面量 ⇒ MUST NOT 整体 ``literal_eval``）。
    """
    tree = ast.parse(CONTRACT_GUARD_TEST.read_text(encoding="utf-8"))
    for node in tree.body:
        value_node: ast.AST | None = None
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "INVARIANT_TESTS"
            for target in node.targets
        ):
            value_node = node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "INVARIANT_TESTS"
        ):
            value_node = node.value
        if isinstance(value_node, ast.Dict):
            return sorted(
                key.value
                for key in value_node.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            )
    raise AssertionError("契约守卫测试里找不到 INVARIANT_TESTS 映射")


# ─────────────────────────────────────────────────────────────────────────────
# 用例组
# ─────────────────────────────────────────────────────────────────────────────
class _C4Schema(TypedDict):
    """被测 schema（**有归约器** + **无归约器**各一）。"""

    messages: Annotated[list, operator.add]
    llm_calls: int


def case_c4_sparse_state(runtime: Any) -> None:
    """**V1** · C4 稀疏状态读（**验收判据 A1 / A2** · SC-001 / SC-002）。

    ⚠️ **否定式**断言（FR-012）—— 若写成「节点入参包含所有 schema key」则
    **等于没有防线**。
    """
    section("V1 · C4 稀疏状态读（验收判据 A1 / A2）")
    channels = runtime.build_channels(runtime.parse_state_schema(_C4Schema))
    channels["messages"].update([["hi"]])

    node_input = runtime.read_channels(channels)

    check(type(node_input) is dict, "C4 结果是**普通 dict**（`type(...) is dict`）")
    check("llm_calls" not in node_input, "A1 `llm_calls` **不在**入参里（否定式）")
    eq(node_input.get("llm_calls", 0), 0, "A2 `.get('llm_calls', 0)` 返回 **default**")
    eq(sorted(node_input), ["messages"], "C4 入参**只含**当前有值的 key")


def case_mount_points(runtime: Any) -> None:
    """**V2** · 挂载点接线（SC-015 / SC-025）。

    * **C4** = ``landed``（本 feature 落地）；
    * **C8** = ``not-landed``（**一字未动** · 仍属 **B8F1**）。
    """
    section("V2 · 挂载点接线（C4 = landed · C8 = not-landed）")
    statuses = _mount_statuses()
    eq(statuses.get("C4"), "landed", "C4 挂载点 `status` == `landed`")
    eq(statuses.get("C8"), "not-landed", "C8 挂载点 `status` == `not-landed`（未落地）")
    check(
        MOUNT_POINT.is_file(),
        "挂载点文件在位",
        str(MOUNT_POINT),
    )


def case_g2_no_internal_import(runtime: Any) -> None:
    """**V3** · G2 门禁（``tests/contracts/**`` 零 ``freegraph.*`` 导入）。

    ⇒ 挂载点文件**只做路径扫描** ⇒ MUST **NOT** import ``freegraph.*``。
    """
    section("V3 · G2 门禁（挂载点文件零 freegraph.* 导入）")
    tree = ast.parse(MOUNT_POINT.read_text(encoding="utf-8"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        for name in names:
            if name.split(".")[0] == "freegraph":
                offenders.append(f"{node.lineno}: {name}")
    check(
        offenders == [],
        "挂载点文件**零** `freegraph.*` 导入（G2 的内部 import 档）",
        str(offenders),
    )


def case_sparse_semantics(runtime: Any) -> None:
    """**V4 / V5** · 稀疏读语义（SC-003 / SC-004 / SC-027 · 契约 §2 与 §4）。

    覆盖：结果形态（**普通 dict** · **同一对象** · **保序**）· key 集合 ==
    「``is_available()`` 为真」的集合 · 「**值为 ``None``**」**出现** ·
    ``skip_empty`` 两分支 · **Edge Cases** ①②③。
    """
    section("V4 / V5 · 稀疏读语义（结果形态 · key 集合 · None 值 · skip_empty 两分支）")

    class _Mixed(TypedDict):
        messages: Annotated[list, operator.add]
        llm_calls: int
        never_written: str

    def _channels() -> dict:
        channels = runtime.build_channels(runtime.parse_state_schema(_Mixed))
        channels["messages"].update([["hi"]])
        return channels

    channels = _channels()
    result = runtime.read_channels(channels)

    check(type(result) is dict, "结果 `type(result) is dict`（**逐字**）")
    eq(
        set(result),
        {key for key, channel in channels.items() if channel.is_available()},
        "**I-1** key 集合 == 「`is_available()` 为真」的通道集合",
    )
    eq(
        list(result),
        [key for key in channels if key in result],
        "**I-2** key 顺序 == 入参映射顺序（过滤后）",
    )
    for key in result:
        check(result[key] is channels[key].get(), f"**I-4** `{key}` 与通道当前值**同一对象**")

    # 「值为 None」的通道**出现**（I-10）
    channels = _channels()
    channels["llm_calls"].update([None])
    result = runtime.read_channels(channels)
    check("llm_calls" in result, "**I-10** 「**值为 `None`**」的通道**出现**")
    check(result.get("llm_calls") is None, "**I-10** 该通道的值**就是 `None`**")

    # skip_empty 两分支
    channels = _channels()
    try:
        runtime.read_channels(channels, skip_empty=False)
        check(False, "`skip_empty=False` 读到无值 ⇒ 抛 `EmptyChannelError`", "未抛错")
    except runtime.EmptyChannelError as error:
        check(True, "`skip_empty=False` 读到无值 ⇒ 抛 `EmptyChannelError`")
        eq(error.key, "llm_calls", "该错误的 `key` 指向那个**无值**通道")
    eq(
        runtime.read_channels(channels),
        runtime.read_channels(channels, skip_empty=True),
        "省略 `skip_empty` == 显式 `skip_empty=True`（**逐字相等**）",
    )

    # 改结果的键集合不影响通道
    channels = _channels()
    result = runtime.read_channels(channels)
    result["injected"] = 1
    del result["messages"]
    check("injected" not in channels, "改结果的**键集合**不影响通道状态")

    # Edge Case ①：空串 key
    channels = _channels()
    channels[""] = runtime.LastValue(key="", value_type=str)
    channels[""].update(["空串键的值"])
    check("" in runtime.read_channels(channels), "**Edge Case ①** 空串 key 照常出现")

    # Edge Case ②：schema 外的 key 照常读取
    channels = _channels()
    channels["outside_schema"] = runtime.LastValue(key="outside_schema", value_type=int)
    channels["outside_schema"].update([42])
    eq(
        runtime.read_channels(channels).get("outside_schema"),
        42,
        "**Edge Case ②** schema 外的 key **照常读取**",
    )

    # Edge Case ③：空映射
    empty = runtime.read_channels({})
    check(type(empty) is dict and empty == {}, "**Edge Case ③** 空映射 ⇒ 空 `dict`")

    # 非映射 ⇒ TypeError
    try:
        runtime.read_channels([("messages", "x")])  # type: ignore[arg-type]
        check(False, "入参**非映射** ⇒ 抛 `TypeError`", "未抛错")
    except TypeError:
        check(True, "入参**非映射** ⇒ 抛 `TypeError`")


def case_fresh_read(runtime: Any) -> None:
    """**V6** · fresh 读（SC-005 · **SC-033** · 契约 §3 与 §4）。

    覆盖：视图含本次写入 · 归约型视图 == 归约结果 · **零污染**（**绑定与可用性
    判定**前后**不变**）· 未知 key ⇒ **显式失败** · 归约器抛错 ⇒ **向上传播**
    且通道正式值**不变** · **两个稀疏入口的结果逐字相等**（**I-11**）·
    **就地修改型**归约器的**已知面**。
    """
    section("V6 · fresh 读（视图 · 零污染 · 显式失败 · 两个稀疏入口逐字相等）")

    class _Fresh(TypedDict):
        messages: Annotated[list, operator.add]
        llm_calls: int

    def _channels() -> dict:
        channels = runtime.build_channels(runtime.parse_state_schema(_Fresh))
        channels["messages"].update([["old"]])
        return channels

    def _snapshot(channels: dict) -> list[tuple[str, bool, object]]:
        snapshot: list[tuple[str, bool, object]] = []
        for key, channel in channels.items():
            available = channel.is_available()
            snapshot.append((key, available, channel.get() if available else None))
        return snapshot

    channels = _channels()
    view = runtime.local_read(channels, {"messages": [["new"]]}, fresh=True)
    eq(view.get("messages"), ["old", "new"], "fresh 视图**含**本次写入（归约型 == 归约结果）")

    channels = _channels()
    view = runtime.local_read(channels, {"messages": [["new"]]}, fresh=False)
    eq(view.get("messages"), ["old"], "`fresh=False` 的视图**不含**本次写入")

    channels = _channels()
    before = _snapshot(channels)
    runtime.local_read(channels, {"messages": [["new"]]}, fresh=True)
    check(
        _snapshot(channels) == before,
        "**零污染**：读取前后通道的**绑定与可用性判定不变**",
    )

    channels = _channels()
    try:
        runtime.local_read(channels, {"not_in_channels": [1]}, fresh=True)
        check(False, "未知 key ⇒ 抛 `InvalidChannelUpdateError`", "未抛错")
    except runtime.InvalidChannelUpdateError as error:
        check(True, "未知 key ⇒ 抛 `InvalidChannelUpdateError`（**零新增错误类型**）")
        eq(error.key, "not_in_channels", "该错误的 `key` 指向那个**未知** key")

    def _boom(current: list, new: list) -> list:
        if new == ["new"]:
            raise RuntimeError("归约器炸了")
        return current + new

    channels = {
        "messages": runtime.BinaryOperatorAggregate(
            key="messages", value_type=list, reducer=_boom
        ),
    }
    channels["messages"].update([["old"]])
    try:
        runtime.local_read(channels, {"messages": [["new"]]}, fresh=True)
        check(False, "归约器抛错 ⇒ **向上传播**", "未抛错")
    except RuntimeError:
        check(True, "归约器抛错 ⇒ **向上传播**")
    eq(channels["messages"].get(), ["old"], "归约器抛错后通道正式值**不变**")

    # **I-11** 两个稀疏入口逐字相等
    channels = _channels()
    direct = runtime.read_channels(channels)
    via_local = runtime.local_read(channels, {}, fresh=False)
    eq(via_local, direct, "**I-11** 两个稀疏入口的结果**逐字相等**（值层面）")
    eq(list(via_local), list(direct), "**I-11** 两个稀疏入口的 key **顺序相同**")
    check(
        all(via_local[key] is direct[key] for key in direct),
        "**I-11** 两个稀疏入口的逐 key 值**同一对象**",
    )

    # **已知面**：就地修改型归约器改写原通道的值对象（与上游同构）
    def _extend_in_place(current: list, new: list) -> list:
        current.extend(new)
        return current

    channels = {
        "messages": runtime.BinaryOperatorAggregate(
            key="messages", value_type=list, reducer=_extend_in_place
        ),
    }
    channels["messages"].update([["old"]])
    runtime.local_read(channels, {"messages": [["new"]]}, fresh=True)
    eq(
        channels["messages"].get(),
        ["old", "new"],
        "**已知面**：就地修改型归约器**改写**原通道的值对象（与上游同构 · 不修）",
    )


def case_contract_guard(runtime: Any) -> None:
    """**契约守卫**（FR-027 ② · SC-012 · SC-018）—— **解析**读取契约并逐条断言。

    * 契约 §4 的不变量编号集合 MUST 与**冻结的**集合**逐条一致**；
    * **契约守卫测试**里的 ``INVARIANT_TESTS`` MUST **逐条**绑定这些不变量；
    * 两个入口的**名字 + 签名** MUST 与契约 §1 **逐字一致**。
    """
    section("契约守卫（解析 read-contract.md · I-1…I-11 · 签名逐字一致）")
    check(
        CONTRACT_PATH.is_file(),
        "读取契约权威文件在位",
        str(CONTRACT_PATH),
    )
    eq(
        tuple(_contract_invariants()),
        EXPECTED_INVARIANTS,
        "契约 §4 的不变量编号集合 == **冻结的 I-1…I-11**",
    )
    eq(
        tuple(_bound_invariants()),
        tuple(sorted(EXPECTED_INVARIANTS)),
        "契约守卫测试的 `INVARIANT_TESTS` **逐条**绑定每条不变量",
    )

    expected = _contract_entry_signatures()
    eq(set(expected), {"read_channels", "local_read"}, "契约 §1 冻结了**两个**读取入口")
    eq(
        f"{runtime.read_channels.__name__}{_signature_text(runtime.read_channels)}",
        expected.get("read_channels"),
        "`read_channels` 的**名字 + 签名**与契约**逐字一致**",
    )
    eq(
        f"{runtime.local_read.__name__}{_signature_text(runtime.local_read)}",
        expected.get("local_read"),
        "`local_read` 的**名字 + 签名**与契约**逐字一致**",
    )


def case_differential(runtime: Any) -> None:
    """**V7 / V8** · 差分夹具（SC-006 / SC-007 / **SC-032** · SC-013 · SC-009）。

    * **三项投影**（**节点入参 / 输出状态 / 事件序列**）逐字段相等；
    * 判定记录 MUST 含**比对字段名** + **逐项结果**（FR-017 / SC-019）；
    * 上游**实测基线**逐项对齐（SC-020 · **MUST NOT** 凭记忆）；
    * 上游**缺席** ⇒ **skip 而非 fail**（FR-019）。
    """
    section("V7 / V8 · 差分夹具（三项投影逐字段相等 · 缺席即 skip）")
    runner, upstream_version = _load_differential()
    if upstream_version is None:
        soft(
            False,
            "差分夹具的真实执行（上游**在场**）",
            "本解释器**未装** `langgraph`（PEP 735 的 `differential` 组）⇒ "
            f"差分组 **skip**（**非失败** · FR-019）；装法："
            f"uv pip install --python {INTERPRETER} "
            f"--group {UPSTREAM_ALLOWED_GROUP}",
        )
        return

    from differential.driver import record_node_input  # noqa: PLC0415
    from differential.spec_builder import build_graph_spec  # noqa: PLC0415

    def _node_a(state: dict) -> dict:
        record_node_input(state)
        return {"messages": ["a"]}

    def _node_b(state: dict) -> dict:
        record_node_input(state)
        return {"llm_calls": 1, "": "空键的值"}

    def _node_empty(state: dict) -> dict:
        record_node_input(state)
        return {}

    spec = build_graph_spec(
        name="MixedState",
        schema={
            "messages": (list, operator.add),
            "llm_calls": (int, None),
            "": (str, None),
        },
        nodes=(("a", _node_a), ("b", _node_b), ("empty", _node_empty)),
        initial_input={"messages": ["old"]},
    )

    report = runner.run_differential(spec, upstream_version)
    check(report.equal, "三项投影**逐字段**相等（差异 == 0）", report.to_dict().__str__())
    check(bool(report.results), "判定记录**非空**（MUST NOT 只写「一致」）")
    check(
        all(result.field for result in report.results),
        "判定记录含**比对字段名** + **逐项结果**（FR-017 / SC-019）",
    )
    fields = [result.field for result in report.results]
    check(
        any(field.startswith("节点入参") for field in fields),
        "判定记录含**节点入参**这一项投影（**SC-032**）",
    )
    check(
        any(field.startswith("输出状态") for field in fields),
        "判定记录含**输出状态**这一项投影（SC-006）",
    )
    check(
        any(field.startswith("事件序列") for field in fields),
        "判定记录含**事件序列**这一项投影（SC-007）",
    )
    empty_updates = [
        result
        for result in report.results
        if result.field.startswith("事件序列[") and result.equal
    ]
    check(
        any(result.expected is not None and result.expected[2] is None for result in empty_updates),
        "**空更新 ⇒ 写入为 `None`**（FR-034 · SC-028 · 实测口径已冻结）",
    )
    eq(
        report.upstream_version,
        upstream_version,
        "判定记录含**上游版本**（契约 §6 · 可核对性）",
    )


def case_dependency_redlines(runtime: Any) -> None:
    """**V9** · 依赖红线（**验收判据 A5** · SC-008 / SC-010 · FR-018 / FR-037）。

    * ``Requires-Dist`` **整体为空**；
    * 内核路径对上游的导入次数 == **0**；
    * ``[dependency-groups]`` 里含上游的组 == **恰好 1 个**且为 ``differential``；
    * ``ci.yml`` 文本中上游包名字样 == **0**（**原断言逐字保留**）；
    * ``ci.yml`` 的 ``--group`` **白名单** == {``dev``, ``differential``}。
    """
    section("V9 · 依赖红线（Requires-Dist 整体为空 · 内核零上游导入）")
    import importlib.metadata as md
    import tomllib

    eq(
        md.requires("freegraph") in (None, []),
        True,
        "**A5** `Requires-Dist` **整体为空**",
    )

    offenders: list[str] = []
    for path in sorted((REPO_ROOT / "src" / "freegraph").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if name.split(".")[0] in {
                    "langgraph",
                    "langchain",
                    "langsmith",
                    "pydantic",
                    "typing_extensions",
                }:
                    offenders.append(f"{path.name}:{node.lineno}: {name}")
    check(offenders == [], "内核路径对上游的导入次数 == **0**", str(offenders))

    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    groups = data.get("dependency-groups", {})
    upstream_groups = sorted(
        name
        for name, entries in groups.items()
        if any(
            package in entry.lower()
            for entry in entries
            for package in UPSTREAM_PACKAGE_NAMES
        )
    )
    eq(
        upstream_groups,
        [UPSTREAM_ALLOWED_GROUP],
        "`[dependency-groups]` 含上游的组 == **恰好 1 个**且为 `differential`",
    )
    check(
        "optional-dependencies" not in data.get("project", {}),
        "`pyproject.toml` **无** `[project].optional-dependencies`（宪法 v1.7.0）",
    )

    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    eq(
        workflow.lower().count("langgraph"),
        0,
        "`ci.yml` 文本中上游包名的字样 == **0**（**原断言逐字保留**）",
    )
    used_groups = sorted(set(re.findall(r"--group[= ]+([A-Za-z0-9._-]+)", workflow)))
    check(bool(used_groups), "`ci.yml` 至少有一处 `--group` 安装步骤")
    check(
        set(used_groups) <= CI_GROUP_WHITELIST,
        f"`ci.yml` 的 `--group` **白名单** == {sorted(CI_GROUP_WHITELIST)}",
        str(used_groups),
    )
    check(
        "--group differential" in workflow,
        "`ci.yml` 装了 `differential` 组（**步骤 5.6**）",
    )
    check(
        workflow.find("--group differential")
        < workflow.find("-m pytest tests/"),
        "**步骤 5.6** 位于**步骤 6（全量测试套件）之前**（裁定 30 · SC-014 可达）",
    )


def case_frozen_surface(runtime: Any) -> None:
    """**V12** · 冻结面审计（SC-011 / SC-012 / SC-029 · FR-021 / FR-026）。

    * 契约层 **18** 个 · 门面 **7** 个 · ``freegraph.runtime`` **14** 个
      （含两个读取入口）；
    * **兼容矩阵零新增行**（符号集合 == 契约层 18 + 门面 7）；
    * 层注册表把 ``src/freegraph/runtime/`` 登记为 **L2**（**零改动**）；
    * 门禁编号总数仍为 **30** 且**连续**；
    * ``THIRD_PARTY_NOTICES`` 的第三方运行时依赖表**无数据行**。
    """
    section("V12 · 冻结面审计（18 / 7 / 14 · 兼容矩阵零新增行 · 门禁编号 30）")
    contract_symbols = _public_symbols(
        REPO_ROOT / "src" / "freegraph" / "contracts" / "__init__.py"
    )
    facade_symbols = _public_symbols(REPO_ROOT / "src" / "freegraph" / "graph.py")
    runtime_symbols = _public_symbols(
        REPO_ROOT / "src" / "freegraph" / "runtime" / "__init__.py"
    )
    eq(len(contract_symbols), CONTRACT_PUBLIC_SYMBOL_COUNT, "契约层符号数 == **18**")
    eq(len(facade_symbols), FACADE_PUBLIC_SYMBOL_COUNT, "门面符号数 == **7**")
    eq(len(runtime_symbols), RUNTIME_PUBLIC_SYMBOL_COUNT, "`freegraph.runtime` == **14**")
    check(
        "read_channels" in runtime_symbols and "local_read" in runtime_symbols,
        "`freegraph.runtime.__all__` 含两个读取入口",
    )

    readme = README.read_text(encoding="utf-8")
    section_match = COMPAT_MATRIX_PATTERN.search(readme)
    check(bool(section_match), "README 含「## API 兼容矩阵」章节")
    names = {
        match.group(1)
        for match in re.finditer(
            r"^\|\s*`([A-Za-z_][A-Za-z0-9_]*)`\s*\|", section_match.group(1), re.M
        )
    } if section_match else set()
    expected = set(contract_symbols) | set(facade_symbols)
    check(
        names == expected,
        "兼容矩阵的符号集合 == 契约层 18 + 门面 7（**零新增行**）",
        f"多出 {sorted(names - expected)} · 缺少 {sorted(expected - names)}",
    )

    registry = LAYER_REGISTRY.read_text(encoding="utf-8")
    check(
        bool(re.search(r"\|\s*`src/freegraph/runtime/`\s*\|\s*`L2`\s*\|", registry)),
        "层注册表把 `src/freegraph/runtime/` 登记为 **L2**（零改动）",
    )

    contract_text = ARCHITECTURE_GATES.read_text(encoding="utf-8")
    overview = re.search(r"^##\s*0\..*?(?=^##\s|\Z)", contract_text, re.S | re.M)
    check(bool(overview), "architecture-gates.md 含「## 0. 门禁总览」章节")
    identifiers = (
        re.findall(r"\|\s*\*\*G(\d+)\*\*\s*\|", overview.group(0)) if overview else []
    )
    eq(
        identifiers,
        [str(number) for number in range(1, GATE_TOTAL + 1)],
        f"门禁编号**连续**且总数 == **{GATE_TOTAL}**（**零新增门禁编号**）",
    )

    notices = NOTICES.read_text(encoding="utf-8")
    section_match = re.search(r"^##\s*2\..*?(?=^##\s|\Z)", notices, re.S | re.M)
    rows = [
        line.strip()
        for line in (section_match.group(0) if section_match else "").splitlines()
        if line.strip().startswith("|")
        and not re.match(r"^\|[\s\-|:]+\|$", line.strip())
        and not line.strip().startswith("| 包 ")
        and "（暂无条目）" not in line
    ]
    check(rows == [], "`THIRD_PARTY_NOTICES` 的第三方运行时依赖表**无数据行**", str(rows))


def case_cross_feature_wiring(runtime: Any) -> None:
    """**V12** · 跨 feature 接线复核（宪法 **v1.8.0** · FR-031 / FR-036 / FR-037）。

    ⇒ **五处**承接条款**在位**（B7F1 / B8F1 ×2 / B25F1 / B4F1）⇒
    ⇒ B4F1 的措辞与**裁定 27**一致（「**取样范围拆分**」命中 ≥ 1 ·
    「**判据收窄**」命中 == 0）。
    """
    section("V12 · 跨 feature 接线复核（五处承接条款在位）")
    for label, path, needle in CROSS_FEATURE_WIRINGS:
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        check(
            needle in text,
            f"{label} 的承接条款**在位**",
            f"未在 {path.name} 中找到「{needle}」",
        )
    b4f1 = (FEATURES_DIR / "B4F1_schema解析与归约器提取.md").read_text(encoding="utf-8")
    check(
        b4f1.count("取样范围拆分") >= 1,
        "B4F1 的措辞含「**取样范围拆分**」（裁定 27）",
    )
    check(
        b4f1.count("判据收窄") == 0,
        "B4F1 的措辞**不含**「判据收窄」（**未**援引宪法 v1.6.0）",
    )


def case_coverage_evidence(runtime: Any) -> None:
    """**V11** · 覆盖率取证（SC-018 · FR-027 ②）。

    * **阻断判据**：``read.py`` / ``__init__.py`` 的**行覆盖与分支覆盖**
      MUST 均为 **100%**；
    * **整包**覆盖率**记录但 MUST NOT 阻断**。

    ⚠️ ``coverage`` 是**开发期工具**（**不进**仓库依赖声明）⇒ 未安装时标
    「◌ 环境未就绪」（**不判失败**）。
    """
    section("V11 · 覆盖率取证（read.py 行 / 分支 100%）")
    probe = subprocess.run(
        [INTERPRETER, "-c", "import coverage"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    if probe.returncode != 0:
        soft(
            False,
            "SC-018 覆盖率取证（行 / 分支 100%）",
            f"本解释器（{INTERPRETER}）**未装** `coverage` ⇒ "
            "**skip ≠ pass**；装法：uv pip install --python "
            f"{INTERPRETER} coverage",
        )
        return

    with tempfile.TemporaryDirectory(prefix="freegraph-b5f2-cov-") as tmp:
        data_file = Path(tmp) / "cov.json"
        env = dict(os.environ)
        env["COVERAGE_FILE"] = str(Path(tmp) / ".coverage")
        run = subprocess.run(
            [
                INTERPRETER,
                "-m",
                "coverage",
                "run",
                "--branch",
                "-m",
                "pytest",
                "-q",
                "tests/runtime",
                "tests/differential",
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
        )
        if run.returncode != 0:
            check(
                False,
                "SC-018 覆盖率跑测（`coverage run --branch -m pytest …`）",
                run.stdout.strip().splitlines()[-1] if run.stdout.strip() else "",
            )
            return
        export = subprocess.run(
            [INTERPRETER, "-m", "coverage", "json", "-o", str(data_file)],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
        )
        if export.returncode != 0 or not data_file.is_file():
            check(False, "SC-018 导出 `coverage json`", export.stderr.strip()[:200])
            return
        payload = json.loads(data_file.read_text(encoding="utf-8"))

    files = payload.get("files", {})
    for relative_path in FULL_COVERAGE_FILES:
        entry = files.get(relative_path)
        if entry is None:
            check(False, f"SC-018 `{relative_path}` 在覆盖率报告中")
            continue
        missing_lines = entry.get("missing_lines", [])
        missing_branches = entry.get("missing_branches", [])
        check(
            missing_lines == [],
            f"SC-018 `{relative_path}` **行覆盖 == 100%**",
            f"未覆盖行 {missing_lines}",
        )
        check(
            missing_branches == [],
            f"SC-018 `{relative_path}` **分支覆盖 == 100%**",
            f"未覆盖分支 {missing_branches}",
        )
    summary = payload.get("totals", {})
    soft(
        True,
        "整包覆盖率（**记录但不阻断**）",
        f"行 {summary.get('percent_covered_display', '?')}",
    )


def case_gates(runtime: Any, installed: bool) -> None:
    """**V10** · 门禁实跑（10 条 · SC-011 / SC-012）。

    * **本地直跑**的 7 条 ⇒ **硬断言**（退出码 == 0）；
    * **Linux only** 的 3 条（``G22`` 需网络 · ``G27`` 需 socket 监测 ·
      ``G28`` 需网络命名空间）⇒ **只观测不阻断**（由 CI 的 Linux 作业作阻断判据）。
    """
    section("V10 · 门禁实跑（10 条 · 零新增门禁编号）")
    extras = [
        "--project",
        "specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml",
    ]
    for gate in LOCAL_GATES:
        matches = sorted(GATES_DIR.glob(f"gate_{gate}_*.py"))
        if not matches:
            check(False, f"门禁 {gate} 的脚本在位", str(GATES_DIR))
            continue
        command = [INTERPRETER, str(matches[0])]
        if gate in {"G21", "G23"}:
            command.extend(extras)
        completed = subprocess.run(
            command, capture_output=True, text=True, cwd=str(REPO_ROOT)
        )
        check(
            completed.returncode == 0,
            f"门禁 {gate} 通过（退出码 0）",
            (completed.stdout + completed.stderr).strip().splitlines()[-1]
            if (completed.stdout + completed.stderr).strip()
            else "",
        )
    for gate in LINUX_ONLY_GATES:
        matches = sorted(GATES_DIR.glob(f"gate_{gate}_*.py"))
        if not matches:
            soft(False, f"门禁 {gate} 的脚本在位", str(matches))
            continue
        completed = subprocess.run(
            [INTERPRETER, str(matches[0])],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        soft(
            completed.returncode == 0,
            f"门禁 {gate} 通过（**Linux only** · 只观测不阻断）",
            (completed.stdout + completed.stderr).strip().splitlines()[-1]
            if (completed.stdout + completed.stderr).strip()
            else "",
        )


# ─────────────────────────────────────────────────────────────────────────────
# 验收记录片段
# ─────────────────────────────────────────────────────────────────────────────
def build_record(mode: str, verdict: str, rc: int) -> str:
    """产出**五段式**的验收记录片段（可直接并入 ``manual-verification.md``）。"""
    out: list[str] = []
    out.append(
        "# B5F2 验收记录（由 `harness/verification/B5F2/acceptance.py` 生成）"
    )
    out.append("")
    out.append("## 1. 环境")
    out.append("")
    out.append("| 项 | 内容 |")
    out.append("|---|---|")
    out.append(
        f"| 操作系统 | {platform.system()} {platform.release()} ({platform.machine()}) |"
    )
    out.append(f"| Python | {sys.version.split()[0]}（`{sys.executable}`） |")
    out.append(f"| 运行模式 | {mode} |")
    out.append(f"| 工作目录 | `{os.getcwd()}` |")
    out.append("| 依赖 | 本脚本**仅** Python 标准库（零第三方） |")
    out.append("")
    out.append("## 2. 步骤")
    out.append("")
    out.append("```bash")
    out.append("python3 harness/verification/B5F2/acceptance.py")
    out.append("```")
    out.append("")
    out.append("## 3. 实际输出")
    out.append("")
    out.append("```text")
    out.append(_CAPTURE.getvalue().rstrip() or "（无输出）")
    out.append("```")
    out.append("")
    out.append("## 4. 结论")
    out.append("")
    out.append(f"**验收结论：{verdict}**（退出码 {rc}）")
    out.append("")
    out.append("## 5. 遗留问题")
    out.append("")
    out.append("⬜ 待填")
    out.append("")
    return "\n".join(out)


# ─────────────────────────────────────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────────────────────────────────────
def main() -> int:
    """入口（两态运行 · 退出码 0 / 1 / 2）。"""
    parser = argparse.ArgumentParser(
        description="B5F2 人工验收脚本（一条命令跑完全部验收闸口 V1–V12）"
    )
    parser.add_argument("--record", help="把验收记录片段写到该路径")
    parser.add_argument(
        "--require-installed",
        action="store_true",
        help="要求当前环境**已安装** freegraph（否则判失败）",
    )
    parser.add_argument(
        "--skip-coverage",
        action="store_true",
        help="跳过**覆盖率取证**段（需 `coverage` · 开发期工具）",
    )
    parser.add_argument(
        "--skip-gates",
        action="store_true",
        help="跳过**门禁实跑**段（10 条门禁脚本）",
    )
    args = parser.parse_args()

    global _CAPTURE
    _CAPTURE = io.StringIO()
    _real_stdout = sys.stdout

    class _Tee:
        def write(self, text: str) -> int:
            _real_stdout.write(text)
            _CAPTURE.write(text)
            return len(text)

        def flush(self) -> None:
            _real_stdout.flush()

    sys.stdout = _Tee()

    print("══ acceptance · B5F2 稀疏状态读取 + 差分测试夹具 ══")
    try:
        runtime, mode = _load_runtime()
    except _EnvironmentNotReady as error:
        sys.stdout = _real_stdout
        print(f"◌ 环境未就绪：{error}")
        print("结论：SKIP（退出码 2）")
        return 2
    installed = _installed()
    section("运行环境")
    if not installed:
        if args.require_installed:
            check(
                False,
                "当前环境**已安装** freegraph（--require-installed）",
                "未安装",
            )
        else:
            soft(
                False,
                "当前环境**已安装** freegraph（发行产物可导入）",
                f"本解释器（{INTERPRETER}）**未安装** ⇒ 已自动把 <repo>/src 注入 "
                "sys.path 测**源码树**（不判失败）；" + _install_hint(),
            )
    started = time.monotonic()

    cases = (
        ("case_c4_sparse_state", lambda: case_c4_sparse_state(runtime)),
        ("case_mount_points", lambda: case_mount_points(runtime)),
        ("case_g2_no_internal_import", lambda: case_g2_no_internal_import(runtime)),
        ("case_sparse_semantics", lambda: case_sparse_semantics(runtime)),
        ("case_fresh_read", lambda: case_fresh_read(runtime)),
        ("case_contract_guard", lambda: case_contract_guard(runtime)),
        ("case_differential", lambda: case_differential(runtime)),
        ("case_dependency_redlines", lambda: case_dependency_redlines(runtime)),
        ("case_frozen_surface", lambda: case_frozen_surface(runtime)),
        ("case_cross_feature_wiring", lambda: case_cross_feature_wiring(runtime)),
    )
    if not args.skip_coverage:
        cases = cases + (
            ("case_coverage_evidence", lambda: case_coverage_evidence(runtime)),
        )
    if not args.skip_gates:
        cases = cases + (("case_gates", lambda: case_gates(runtime, installed)),)
    for name, case in cases:
        try:
            case()
        except Exception as exc:  # noqa: BLE001
            check(False, f"用例组 {name} 未抛异常即完成", f"{type(exc).__name__}: {exc}")

    rc = finish("B5F2 人工验收")
    print(f"  · 耗时 {time.monotonic() - started:.1f}s")
    sys.stdout = _real_stdout

    if args.record:
        path = Path(args.record)
        path.parent.mkdir(parents=True, exist_ok=True)
        verdict = "PASS" if rc == 0 else "FAIL"
        path.write_text(build_record(mode, verdict, rc), encoding="utf-8")
        print(f"验收记录片段已写入：{path}")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
