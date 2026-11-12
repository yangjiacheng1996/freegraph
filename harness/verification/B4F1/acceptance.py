#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**B4F1** 人工验收脚本（状态 schema 解析 + 归约器提取）。

定位
----
本脚本是 **B4F1 这个 feature 的人工验收入口**——**开发期**（v1.0 之前）逐 feature
验收用；**v1.0 完成后的端到端验收**在 `harness/demo/`。

它把 B4F1 的验收判据 **A1–A3** 与全部成功标准 **SC-001 … SC-018** 逐条落成
**可判定的断言**，跑一遍就知道「schema 解析 + 归约器提取到底交付到位没有」。

覆盖的分组：

* **A1** `Annotated[list, operator.add]` 被识别为**二元归约器**（**身份**判定）
* **A2** 二元性判据与上游一致（**判定表 16 类二元性形态 + 2 类提取形态逐条比对**）
* **A3** 无归约器 key 走**默认覆盖**语义（C3 事实）
* **误判方向** 末位非 callable / 多条目只认末位 / 类与可调用实例的**机械判定**
* **错误契约** 三类非法输入**快速失败** + 结构化字段（`key` + 封闭取值域的 `reason`）
* **纯数据** 不可变 · 可比较 · 投影可序列化且无地址 · **显式不可哈希**
* **零副作用** `sys.modules` 增量 / 环境变量读取 / 出站连接 / 归约器调用次数
* **必填性** 只记录不执行
* **冻结面审计** 公开面 18 / 7 未变 · 兼容矩阵零新增行 · 层注册表零改动 ·
  依赖三处零新增 · CI 不装 `langgraph` · 门禁编号仍为 30 · 署名头覆盖率 100%

依赖
----
**只 import Python 标准库**（+ 被验收的 ``freegraph`` 本身）——**零第三方依赖**。

判定表**不另抄一份**：本脚本**解析**
``specs/b4f1-schema-reducer-parse/contracts/binary-criterion.md``
（``<!-- authority: yes -->`` · 判据的**唯一权威**）⇒ 判据与用例**天然分离**
（research D-03）。

两态运行
--------
| 情形 | 行为 |
|---|---|
| 当前环境**已安装** freegraph | 测**发行产物** |
| 当前环境**未安装** | 自动把 ``<repo>/src`` 插入 ``sys.path``（源码优先），测**源码树**；依赖闭包那条判**不判失败**，标「◌ 环境未就绪」 |

用法
----
    python3 harness/verification/B4F1/acceptance.py                    # 跑全部
    python3 harness/verification/B4F1/acceptance.py --record out.md    # 同时生成验收记录片段
    python3 harness/verification/B4F1/acceptance.py --require-installed # 把「未安装」判为失败

退出码：``0`` = PASS · ``1`` = FAIL。
"""

import argparse
import ast
import functools
import io
import json
import operator
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Annotated, Any, NotRequired, Required, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_DIR = REPO_ROOT / "specs" / "b4f1-schema-reducer-parse"
CRITERION_PATH = SPEC_DIR / "contracts" / "binary-criterion.md"
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
README = REPO_ROOT / "README.md"
NOTICES = REPO_ROOT / "THIRD_PARTY_NOTICES"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PYPROJECT = REPO_ROOT / "pyproject.toml"
SIGNATURE_HEADER = (
    "# Copyright (c) 2026 杨家成 · MIT License · "
    "https://github.com/yangjiacheng1996/freegraph"
)

#: 判定表的覆盖面下限（FR-016 ①-a·①-b · SC-004）。
BINARY_CRITERION_ROW_COUNT = 16
EXTRACTION_CRITERION_ROW_COUNT = 2

#: 契约层 / 门面的公开符号面（**冻结面** · SC-015）。
CONTRACT_PUBLIC_SYMBOL_COUNT = 20
FACADE_PUBLIC_SYMBOL_COUNT = 7

#: 本 feature **新建**的源文件（署名头 + docstring 复核的扫描域 · SC-012）。
NEW_SOURCE_FILES = (
    "src/freegraph/runtime/__init__.py",
    "src/freegraph/runtime/errors.py",
    "src/freegraph/runtime/reducer.py",
    "src/freegraph/runtime/schema.py",
    "tests/runtime/__init__.py",
    "tests/runtime/conftest.py",
    "tests/runtime/test_binary_criterion.py",
    "tests/runtime/test_future_annotations.py",
    "tests/runtime/test_parse_contract.py",
    "tests/runtime/test_schema_parse.py",
    "tests/runtime/test_typed_dict_variants.py",
)

#: 上层模块（L3 / L4 / L5）⇒ L2 MUST NOT import 它们（FR-014 · ARCH-1）。
UPPER_LAYER_MODULES = ("_stategraph", "persistence", "observability", "app")

class AnyMessage:
    """``langchain.messages.AnyMessage`` 的**零依赖替身**（验收基准同构形态）。"""


#: 兼容矩阵的章节定位（**不扫全文**）。
COMPAT_MATRIX_PATTERN = re.compile(
    r"^## API 兼容矩阵\s*$(.*?)(?=^## |\Z)", re.S | re.M
)

#: 内存地址形态（``0x…``）⇒ 投影 MUST NOT 含它（FR-011 ④ · SC-005）。
ADDRESS_PATTERN = re.compile(r"0x[0-9a-fA-F]+")


# ─────────────────────────────────────────────────────────────────────────────
# 极简断言框架（与 harness/verification/B2F2/acceptance.py 同款：单文件可独立运行）
# ─────────────────────────────────────────────────────────────────────────────
_CHECKS = 0
_FAILED: list[str] = []
_SOFT: list[str] = []
_SECTION = ""
_CAPTURE: Any = None


def section(title: str) -> None:
    global _SECTION
    _SECTION = title
    print(f"\n[{title}]")


def check(cond: object, label: str, detail: str = "") -> bool:
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
    return check(actual == expected, label, f"期望 {expected!r}，实际 {actual!r}")


# ─────────────────────────────────────────────────────────────────────────────
# 加载被验对象
# ─────────────────────────────────────────────────────────────────────────────
def _load_runtime() -> tuple[Any, str]:
    """导入 ``freegraph.runtime``，返回 ``(模块, 模式说明)``。"""
    try:
        import freegraph.runtime as runtime

        return runtime, "发行产物（当前环境已安装 freegraph）"
    except ImportError:
        src = REPO_ROOT / "src"
        if not src.is_dir():
            raise
        sys.path.insert(0, str(src))
        import freegraph.runtime as runtime

        return runtime, f"源码树（{src} 已注入 sys.path）"


def _installed() -> bool:
    """当前环境**是否已安装** freegraph。"""
    try:
        import importlib.metadata as md

        md.version("freegraph")
    except Exception:  # noqa: BLE001
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# 判定表（**唯一权威** = contracts/binary-criterion.md · research D-03）
# ─────────────────────────────────────────────────────────────────────────────
_BACKTICKED = re.compile(r"`([^`]+)`")


def _section_lines(lines: list[str], heading_prefix: str) -> list[str]:
    collected: list[str] = []
    inside = False
    for line in lines:
        if line.startswith("## "):
            inside = line.startswith(heading_prefix)
            continue
        if inside:
            collected.append(line)
    return collected


def _table_cells(line: str) -> list[str]:
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
    return bool(cells) and all(set(cell) <= {"-", ":", " "} and cell for cell in cells)


def _backticked(cell: str) -> str:
    match = _BACKTICKED.search(cell)
    return match.group(1).strip() if match else ""


def _parse_criterion_tables(text: str) -> dict[str, list[dict[str, str]]]:
    """解析判定表的 §2（形态）/ §3（提取）/ §4（夹具清单）三张表。"""
    lines = text.splitlines()

    binary_rows: list[dict[str, str]] = []
    for line in _section_lines(lines, "## 2."):
        cells = _table_cells(line)
        if len(cells) != 5 or _is_separator(cells) or not cells[0].isdigit():
            continue
        binary_rows.append(
            {
                "index": cells[0],
                "form": cells[1],
                "input": _backticked(cells[2]),
                "expected": cells[3],
                "upstream": _backticked(cells[4]),
            }
        )

    extraction_rows: list[dict[str, str]] = []
    for line in _section_lines(lines, "## 3."):
        cells = _table_cells(line)
        if len(cells) != 5 or _is_separator(cells) or not cells[0].startswith("E-"):
            continue
        extraction_rows.append(
            {
                "index": cells[0],
                "form": cells[1],
                "input": _backticked(cells[2]),
                "expected": cells[3],
                "upstream": _backticked(cells[4]),
            }
        )

    fixture_rows: list[dict[str, str]] = []
    for line in _section_lines(lines, "## 4."):
        cells = _table_cells(line)
        if len(cells) != 3 or _is_separator(cells) or cells[0] == "名字":
            continue
        name = _backticked(cells[0])
        if not name:
            continue
        fixture_rows.append({"name": name, "definition": _backticked(cells[1])})

    return {
        "binary": binary_rows,
        "extraction": extraction_rows,
        "fixtures": fixture_rows,
    }


# ── §4 夹具清单的**实际对象**（求值命名空间 · 逐名一致）─────────────────────


def two_positional(a, b):  # noqa: ANN001, ANN201 —— 夹具形态
    """位置或关键字 2 参（§2 第 2 行）。"""
    return a


def three_positional(a, b, c):  # noqa: ANN001, ANN201 —— 夹具形态
    """3 个位置参数（§2 第 3 行）。"""
    return a


def one_positional(a):  # noqa: ANN001, ANN201 —— 夹具形态
    """1 个位置参数（§2 第 4 行）。"""
    return a


def one_positional_varargs(a, *args):  # noqa: ANN001, ANN002, ANN201 —— 夹具形态
    """1 位置参 + ``*args``（§2 第 5 行）。"""
    return a


def two_positional_varargs(a, b, *args):  # noqa: ANN001, ANN002, ANN201 —— 夹具形态
    """2 位置参 + ``*args``（§2 第 6 行）。"""
    return a


def two_positional_kwonly(a, b, *, c=None):  # noqa: ANN001, ANN201 —— 夹具形态
    """2 位置参 + keyword-only（§2 第 7 行）。"""
    return a


def kwonly_only(*, a, b):  # noqa: ANN001, ANN201 —— 夹具形态
    """仅关键字（0 位置参 · §2 第 8 行）。"""
    return a


class ClassNoInit:
    """类 · ``__init__`` 无参（§2 第 9 行）⇒ 0 个位置参数 ⇒ 拒绝。"""


class ClassOneArgInit:
    """类 · ``__init__(self, a)``（§2 第 10 行）⇒ 1 个位置参数 ⇒ 拒绝。"""

    def __init__(self, a):  # noqa: ANN001 —— 夹具形态
        self.a = a


class ClassTwoArgInit:
    """类 · ``__init__(self, a, b)``（§2 第 11 行）⇒ 2 个 ⇒ **接受**。"""

    def __init__(self, a, b):  # noqa: ANN001 —— 夹具形态
        self.a = a
        self.b = b


class CallableInstance:
    """可调用实例的**类** · ``__call__(self, a, b)``（§2 第 12 行）。"""

    def __call__(self, a, b):  # noqa: ANN001 —— 夹具形态
        return a


class CallableKwOnlyInstance:
    """可调用实例的**类** · ``__call__(self, *, a, b)``（§2 第 13 行）。"""

    def __call__(self, *, a, b):  # noqa: ANN001 —— 夹具形态
        return a


#: §4 的 ``CallableInstance`` = **实例**（§2 第 12 行的形态列明写「可调用
#: **实例**」；§5 的实测签名 ``(a, b)`` 亦是**实例**的签名）。
callable_instance = CallableInstance()

#: §4 的 ``CallableKwOnlyInstance`` = **实例**（§2 第 13 行）。
callable_kw_only_instance = CallableKwOnlyInstance()


def _build_namespace() -> dict[str, Any]:
    """构造 §4 夹具清单的**求值命名空间**（**逐名一致**）。"""
    return {
        "operator.add": operator.add,
        "two_positional": two_positional,
        "three_positional": three_positional,
        "one_positional": one_positional,
        "one_positional_varargs": one_positional_varargs,
        "two_positional_varargs": two_positional_varargs,
        "two_positional_kwonly": two_positional_kwonly,
        "kwonly_only": kwonly_only,
        "ClassNoInit": ClassNoInit,
        "ClassOneArgInit": ClassOneArgInit,
        "ClassTwoArgInit": ClassTwoArgInit,
        "CallableInstance": callable_instance,
        "CallableKwOnlyInstance": callable_kw_only_instance,
        "partial_add_one": functools.partial(operator.add, 1),
        "bound_method": two_positional.__get__(object()),
        "str": str,
        "meta_non_callable": ("说明文字",),
        "meta_multi_entry": ("描述", operator.add),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 用例组
# ─────────────────────────────────────────────────────────────────────────────
def case_a1_reducer_identification(runtime: Any) -> None:
    """**A1** · SC-001 / SC-009 / SC-010 —— 归约器识别 + 身份判定 + 按引用持有。"""
    parse_state_schema = runtime.parse_state_schema

    class MessagesState(TypedDict):
        messages: Annotated[list, operator.add]
        llm_calls: int

    spec = parse_state_schema(MessagesState)
    messages = spec.channels["messages"]

    check(messages.reducer is operator.add, "A1/SC-001 ① 归约器是 operator.add **本身**（身份判定）")
    check(messages.has_reducer is True, "A1/SC-001 ② has_reducer is True")
    check(messages.semantics == "reduce", "A1/SC-001 ③ semantics == 'reduce'")
    # ⚠️ **2026-11-12 上游对齐 P3**：``value_type`` **保留** ``Annotated`` 原样
    # （上游 ``langgraph/graph/state.py:1862-1872``）⇒ 基类型在 ``__origin__`` 上
    check(messages.value_type.__origin__ is list,
          "A1/SC-001 ④ value_type 保留 Annotated 原样（基类型 list · 上游同款）")
    eq(spec.keys, ("messages", "llm_calls"), "SC-008 规格保序（keys）")
    check(len(spec.channels) == len(spec.keys) == 2, "SC-008 规格条数 == key 数")

    calls: list[int] = []

    def counting_reducer(current, new):  # noqa: ANN001, ANN202 —— 夹具形态
        calls.append(1)
        return current

    class CountingState(TypedDict):
        messages: Annotated[list, counting_reducer]

    counted = parse_state_schema(CountingState)
    check(counted.channels["messages"].reducer is counting_reducer, "SC-009 归约器**按引用**持有（不包装 / 不复制）")
    check(len(calls) == 0, "SC-009 解析期归约器**调用次数 == 0**")

    class RequiredState(TypedDict):
        messages: Required[Annotated[list, operator.add]]

    class NotRequiredState(TypedDict):
        messages: NotRequired[Annotated[list, operator.add]]

    check(
        parse_state_schema(RequiredState).channels["messages"].reducer is operator.add,
        "SC-010 Required[...] 包裹的归约器**不漏**",
    )
    check(
        parse_state_schema(NotRequiredState).channels["messages"].reducer is operator.add,
        "SC-010 NotRequired[...] 包裹的归约器**不漏**",
    )


def case_a2_binary_criterion(runtime: Any) -> None:
    """**A2** · SC-004 —— 判定表**逐条**比对（16 类二元性形态 + 2 类提取形态）。"""
    parse_state_schema = runtime.parse_state_schema

    tables = _parse_criterion_tables(CRITERION_PATH.read_text(encoding="utf-8"))
    binary_rows = tables["binary"]
    extraction_rows = tables["extraction"]
    fixture_names = {row["name"] for row in tables["fixtures"]}
    namespace = _build_namespace()

    eq(len(binary_rows), BINARY_CRITERION_ROW_COUNT, "SC-004 覆盖面下限：§2 行数 == 16")
    eq(len(extraction_rows), EXTRACTION_CRITERION_ROW_COUNT, "SC-004 覆盖面下限：§3 行数 == 2")
    eq(set(namespace), fixture_names, "SC-004 求值命名空间与 §4 夹具清单**逐名一致**")

    all_rows = [*binary_rows, *extraction_rows]
    missing_source = [row["index"] for row in all_rows if not row["upstream"]]
    check(not missing_source, "SC-004 每条形态 MUST 带上游 `路径:行号`（无来源项数 == 0）", str(missing_source))
    missing_name = [
        row["index"]
        for row in all_rows
        if row["input"] not in fixture_names
    ]
    check(not missing_name, "SC-004 每个「输入」名 MUST 能在 §4 夹具清单中找到（缺失条数 == 0）", str(missing_name))

    mismatches: list[str] = []
    for row in binary_rows:
        candidate = namespace[row["input"]]
        annotation = Annotated[list, candidate]
        schema = TypedDict("_Probe", {"probe": annotation})
        if row["expected"].strip() == "接受":
            try:
                channel = parse_state_schema(schema).channels["probe"]
            except Exception as exc:  # noqa: BLE001
                mismatches.append(f"§2-{row['index']} 期望接受，实得异常 {exc!r}")
                continue
            if channel.reducer is not candidate:
                mismatches.append(f"§2-{row['index']} 期望接受，实得非同一引用")
        else:
            try:
                parse_state_schema(schema)
            except runtime.InvalidSchemaError as exc:
                if exc.reason != "reducer_not_binary" or exc.key != "probe":
                    mismatches.append(f"§2-{row['index']} 拒绝但字段不合：{exc.key!r}/{exc.reason!r}")
            except Exception as exc:  # noqa: BLE001
                mismatches.append(f"§2-{row['index']} 期望拒绝 schema 错误，实得 {type(exc).__name__}")
            else:
                mismatches.append(f"§2-{row['index']} 期望拒绝，却被接受")

    for row in extraction_rows:
        metadata = namespace[row["input"]]
        annotation = Annotated[list, *metadata]
        schema = TypedDict("_Probe", {"probe": annotation})
        channel = parse_state_schema(schema).channels["probe"]
        if "无归约器" in row["expected"]:
            if channel.reducer is not None or channel.semantics != "overwrite":
                mismatches.append(f"§3-{row['index']} 期望无归约器 / overwrite")
        else:
            if channel.reducer is not operator.add or channel.semantics != "reduce":
                mismatches.append(f"§3-{row['index']} 期望只认末位（operator.add / reduce）")

    check(
        not mismatches,
        f"SC-004 判定表**逐条**比对一致（一致率 == 100% · {len(all_rows)} 条）",
        "; ".join(mismatches),
    )


def case_a3_overwrite_semantics(runtime: Any) -> None:
    """**A3** · SC-002 / SC-008 / SC-016 —— 无归约器 ⇒ 覆盖；条数与保序；必填性。"""
    parse_state_schema = runtime.parse_state_schema

    class CountState(TypedDict):
        llm_calls: int

    spec = parse_state_schema(CountState)
    channel = spec.channels["llm_calls"]
    check(channel.reducer is None, "A3/SC-002 ① 无归约器 ⇒ reducer 为**空**")
    check(channel.has_reducer is False, "A3/SC-002 ② has_reducer is False")
    check(channel.semantics == "overwrite", "A3/SC-002 ③ semantics == 'overwrite'（C3 事实）")

    class Base(TypedDict):
        b1: int
        b2: str

    class Child(Base):
        b2: int
        c1: float

    child = parse_state_schema(Child)
    eq(child.keys, ("b1", "b2", "c1"), "SC-008 保序：父类 key 在前 · 同名覆盖保持原位")
    check(len(child.channels) == 3, "SC-008 规格条数 == key 数（含继承链）")

    class WithSlots(TypedDict):
        __slots__: str
        real: int

    slotted = parse_state_schema(WithSlots)
    eq(slotted.keys, ("real",), "SC-008 名为 `__slots__` 的伪 key 不计入条数")

    class Empty(TypedDict):
        pass

    empty = parse_state_schema(Empty)
    check(empty.keys == () and len(empty.channels) == 0, "SC-008 空 TypedDict ⇒ 零条规格（合法）")

    class TotalFalse(TypedDict, total=False):
        a: int
        b: str

    class Mixed(TypedDict):
        c: int
        d: NotRequired[str]
        e: Annotated[list, operator.add]

    total_false = parse_state_schema(TotalFalse)
    check(
        all(not total_false.channels[k].required for k in total_false.keys),
        "SC-016 total=False ⇒ 全部标记为「可选」",
    )
    mixed = parse_state_schema(Mixed)
    check(mixed.channels["c"].required is True, "SC-016 默认必选 ⇒ required is True")
    check(mixed.channels["d"].required is False, "SC-016 NotRequired[...] ⇒ required is False")
    check(len(mixed.channels) == 3, "SC-016 本 feature **不执行**任何必填性校验（缺必填 key 仍解析成功）")


def case_metadata_not_misjudged(runtime: Any) -> None:
    """SC-003 / SC-005 —— 别的 `Annotated` 用法不被误判（**误判方向是危险的那一侧**）。"""
    parse_state_schema = runtime.parse_state_schema
    InvalidSchemaError = runtime.InvalidSchemaError

    class NoteState(TypedDict):
        note: Annotated[int, "说明文字"]

    note = parse_state_schema(NoteState).channels["note"]
    check(note.has_reducer is False, "SC-003 末位**非** callable ⇒ 无归约器")
    check(note.semantics == "overwrite", "SC-003 末位非 callable ⇒ 语义 overwrite")
    check(note.reducer is None, "SC-003 末位非 callable ⇒ reducer 为空")

    class MultiState(TypedDict):
        history: Annotated[list, "描述", operator.add]

    history = parse_state_schema(MultiState).channels["history"]
    check(history.reducer is operator.add, "SC-003/FR-005 多条目元数据 ⇒ **只认末位**")

    class TwoArgState(TypedDict):
        value: Annotated[list, ClassTwoArgInit]

    check(
        parse_state_schema(TwoArgState).channels["value"].reducer is ClassTwoArgInit,
        "SC-003 类（`__init__` 恰 2 位置参）按**机械判定**接受为归约器",
    )

    for name, candidate in (
        ("ClassNoInit", ClassNoInit),
        ("ClassOneArgInit", ClassOneArgInit),
        ("CallableKwOnlyInstance", callable_kw_only_instance),
        ("str", str),
    ):
        schema = TypedDict("_Probe", {"probe": Annotated[list, candidate]})
        try:
            parse_state_schema(schema)
        except InvalidSchemaError as exc:
            check(
                exc.reason == "reducer_not_binary" and exc.key == "probe",
                f"SC-014 非二元候选「{name}」⇒ 抛 schema 错误（**不静默降级**）",
                f"实得 {exc.key!r}/{exc.reason!r}",
            )
        except Exception as exc:  # noqa: BLE001
            check(False, f"SC-014 非二元候选「{name}」⇒ 抛 schema 错误", f"实得 {type(exc).__name__}")
        else:
            check(False, f"SC-014 非二元候选「{name}」⇒ 抛 schema 错误", "被静默接受")


def case_error_contract(runtime: Any) -> None:
    """SC-006 / SC-017 —— 快速失败 + 结构化字段 + 封闭原因码 + 两条捕获路径。"""
    from freegraph.contracts import FreegraphError

    parse_state_schema = runtime.parse_state_schema
    InvalidSchemaError = runtime.InvalidSchemaError

    class Bad(TypedDict):
        bad: Annotated[int, lambda a, b, c: None]

    class Unresolvable(TypedDict):
        bad: "Annotated[list[Missing], operator.add]"

    cases = [
        (Bad, "bad", "reducer_not_binary"),
        ({"a": 1}, None, "not_a_state_schema"),
        (Unresolvable, "bad", "annotation_unresolvable"),
    ]
    for schema, expected_key, expected_reason in cases:
        try:
            parse_state_schema(schema)
        except InvalidSchemaError as exc:
            check(exc.key == expected_key, f"SC-017 错误对象带**出错 key**（{expected_reason}）", f"实得 {exc.key!r}")
            check(exc.reason == expected_reason, f"SC-017 错误对象带**原因码**（{expected_reason}）", f"实得 {exc.reason!r}")
            check(isinstance(exc, ValueError), "SC-006 错误同时是 ValueError")
            check(isinstance(exc, FreegraphError), "SC-006 错误同时是 FreegraphError")
            if expected_key is not None:
                check(expected_key in str(exc), "SC-006 消息**点名**出错 key")
        except Exception as exc:  # noqa: BLE001
            check(False, f"SC-006 三类非法输入 ⇒ 抛 schema 错误（{expected_reason}）", f"实得 {type(exc).__name__}")
        else:
            check(False, f"SC-006 三类非法输入 ⇒ 抛 schema 错误（{expected_reason}）", "未抛错")

    class Multi(TypedDict):
        bad_one: Annotated[int, lambda a, b, c: None]
        bad_two: Annotated[int, lambda a: None]

    try:
        parse_state_schema(Multi)
    except InvalidSchemaError as exc:
        check(exc.key == "bad_one", "SC-006 快速失败：只报**第一个**问题", f"实得 {exc.key!r}")
    else:
        check(False, "SC-006 快速失败：只报第一个问题", "未抛错")

    class FakeModel:
        """**零依赖**的「Pydantic 形态」替身。"""

        __annotations__ = {"value": int}

    # ⚠️ **2026-11-12 上游对齐 P3**：上游的判据**只有**「是类 + 有 ``__annotations__``」
    # （上游 ``langgraph/graph/state.py:1818``）⇒ **Pydantic 形态的类**被**接受**；
    # ⇒ 被拒的是**不是类**的对象与**实例**。
    for candidate in ({}, dict[str, int], FakeModel()):
        try:
            parse_state_schema(candidate)
        except InvalidSchemaError as exc:
            check(exc.reason == "not_a_state_schema", "SC-006 非类对象 ⇒ not_a_state_schema")
        except Exception as exc:  # noqa: BLE001
            check(False, "SC-006 非类对象 ⇒ 抛 schema 错误（不抛裸 TypeError）", f"实得 {type(exc).__name__}")
        else:
            check(False, "SC-006 非类对象 ⇒ 抛 schema 错误", "未抛错")

    # **Pydantic 形态的类** ⇒ **被接受**（上游同款）
    accepted = parse_state_schema(FakeModel)
    check("value" in accepted.channels, "SC-006 Pydantic 形态的**类**被接受（上游同款）")


def case_pure_data(runtime: Any) -> None:
    """SC-005 · FR-010 / FR-011 —— 不可变 · 可比较 · 投影无地址 · 显式不可哈希。"""
    import dataclasses

    parse_state_schema = runtime.parse_state_schema

    class State(TypedDict):
        messages: Annotated[list, operator.add]
        n: int

    spec = parse_state_schema(State)
    channel = spec.channels["n"]

    try:
        channel.key = "other"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        check(True, "SC-005 通道规格**不可变**（改属性抛 FrozenInstanceError）")
    except Exception as exc:  # noqa: BLE001
        check(False, "SC-005 通道规格不可变", f"实得 {type(exc).__name__}")
    else:
        check(False, "SC-005 通道规格不可变", "属性可改")

    try:
        spec.channels["x"] = None  # type: ignore[index]
    except TypeError:
        check(True, "SC-005 channels 写操作抛 TypeError（结构性不可变）")
    else:
        check(False, "SC-005 channels 写操作抛 TypeError", "可写")

    try:
        hash(spec)
    except TypeError:
        check(True, "SC-005 SchemaSpec **显式不可哈希**")
    else:
        check(False, "SC-005 SchemaSpec 显式不可哈希", "可哈希")

    try:
        hash(channel)
    except TypeError:
        check(True, "SC-005 ChannelSpec **显式不可哈希**")
    else:
        check(False, "SC-005 ChannelSpec 显式不可哈希", "可哈希")

    eq(spec, parse_state_schema(State), "SC-005 同一 schema 两次解析**相等**")

    class SameContentA(TypedDict):
        value: int

    class SameContentB(TypedDict):
        value: int

    eq(
        parse_state_schema(SameContentA),
        parse_state_schema(SameContentB),
        "SC-005 内容相同、仅类名不同的 TypedDict 解析结果**相等**",
    )

    class OtherType(TypedDict):
        value: str

    class OtherKey(TypedDict):
        other: int

    check(
        parse_state_schema(SameContentA) != parse_state_schema(OtherType),
        "SC-005 value_type 不同 ⇒ 结果**不等**",
    )
    check(
        parse_state_schema(SameContentA) != parse_state_schema(OtherKey),
        "SC-005 键集合不同 ⇒ 结果**不等**",
    )

    payload = json.dumps(spec.to_dict(), ensure_ascii=False)
    check(bool(payload), "SC-005 投影可 JSON 序列化")
    check("0x" not in payload, "SC-005 投影**不含内存地址形态**")
    check(
        json.dumps(spec.to_dict(), ensure_ascii=False)
        == json.dumps(parse_state_schema(State).to_dict(), ensure_ascii=False),
        "SC-005 两次投影**逐字一致**（确定性）",
    )


def case_zero_side_effects(runtime: Any) -> None:
    """SC-007 / SC-009 / SC-011 —— 零导入副作用 · 零环境变量 · 零出站。"""
    source = """
import json
import operator
import sys
from typing import Annotated, TypedDict

import freegraph.runtime
from freegraph.runtime import parse_state_schema

calls = []


def reducer(current, new):
    calls.append(1)
    return current


class Schema(TypedDict):
    messages: Annotated[list, reducer]


before = set(sys.modules)
spec = parse_state_schema(Schema)
new = {m for m in set(sys.modules) - before if not m.startswith("freegraph")}
stdlib = set(sys.stdlib_module_names)
payload = {
    "new_non_stdlib": sorted(
        m for m in new if m.split(".")[0] not in stdlib
    ),
    "third_party": sorted(
        m
        for m in sys.modules
        if m.split(".")[0]
        in {"pydantic", "typing_extensions", "langchain", "langgraph", "langsmith"}
    ),
    "reducer_calls": len(calls),
    "reducer_is_same": spec.channels["messages"].reducer is reducer,
}
print(json.dumps(payload))
"""
    env = dict(os.environ)
    src_dir = REPO_ROOT / "src"
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = f"{src_dir}{os.pathsep}{existing}" if existing else str(src_dir)
    env["PYTHONUTF8"] = "1"
    proc = subprocess.run(
        [sys.executable, "-c", source],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        check(False, "SC-007 零副作用子进程执行", proc.stderr.strip()[:300])
        return
    payload = json.loads(proc.stdout)
    eq(payload["new_non_stdlib"], [], "SC-007 解析前后 `sys.modules` 增量的**非标准库**条目数 == 0")
    eq(payload["third_party"], [], "SC-011 import freegraph.runtime 后**无**第三方模块")
    eq(payload["reducer_calls"], 0, "SC-009 解析期归约器**调用次数 == 0**")
    check(payload["reducer_is_same"], "SC-009 归约器**按引用**保持")


def case_typing_extensions_variant(runtime: Any) -> None:
    """SC-018 · 裁定 3 —— `typing_extensions.TypedDict` 的**正面路径**。

    ⚠️ **环境依赖型**判据：`typing_extensions` **不是任何声明依赖** ⇒ 未装时
    **不判失败**，但标「◌ 环境未就绪」（**skip ≠ pass**）。
    """
    try:
        import typing_extensions
    except ImportError:
        soft(
            False,
            "SC-018 typing_extensions.TypedDict 的正面路径",
            "本环境未装 typing_extensions（非声明依赖）⇒ **skip ≠ pass**，须在人工验证记录记入遗留问题",
        )
        return

    class MessagesState(typing_extensions.TypedDict):  # type: ignore[misc]
        messages: Annotated[list[AnyMessage], operator.add]
        llm_calls: int

    try:
        spec = runtime.parse_state_schema(MessagesState)
    except Exception as exc:  # noqa: BLE001
        check(False, "SC-018 typing_extensions.TypedDict 的 schema 被**接受**", f"实得 {type(exc).__name__}: {exc}")
        return

    messages = spec.channels["messages"]
    calls = spec.channels["llm_calls"]
    check(messages.reducer is operator.add, "SC-018 messages 的归约器是 operator.add **本身**")
    check(messages.has_reducer is True, "SC-018 messages.has_reducer is True")
    check(messages.semantics == "reduce", "SC-018 messages.semantics == 'reduce'")
    check(calls.reducer is None, "SC-018 llm_calls.reducer 为**空**")
    check(calls.semantics == "overwrite", "SC-018 llm_calls.semantics == 'overwrite'")


def case_frozen_surface(runtime: Any) -> None:
    """SC-012 / SC-015 · FR-013 / FR-014 / FR-015 / FR-019 —— 冻结面与纪律审计。"""
    # 公开面
    contract_all = _public_symbols(REPO_ROOT / "src" / "freegraph" / "contracts" / "__init__.py")
    facade_all = _public_symbols(REPO_ROOT / "src" / "freegraph" / "graph.py")
    eq(len(contract_all), CONTRACT_PUBLIC_SYMBOL_COUNT, "SC-015 契约层公开符号面仍为 **20** 个（上游对齐 P3）")
    eq(len(facade_all), FACADE_PUBLIC_SYMBOL_COUNT, "SC-015 门面公开符号面仍为 **7** 个")

    # 兼容矩阵零新增行
    readme = README.read_text(encoding="utf-8")
    section_match = COMPAT_MATRIX_PATTERN.search(readme)
    if not section_match:
        check(False, "SC-015 README 有「## API 兼容矩阵」章节")
    else:
        names = {
            match.group(1)
            for match in re.finditer(
                r"^\|\s*`([A-Za-z_][A-Za-z0-9_]*)`\s*\|", section_match.group(1), re.M
            )
        }
        expected = set(contract_all) | set(facade_all)
        eq(
            names,
            expected,
            "SC-015 兼容矩阵**零新增行**（符号集合 == 契约层 20 + 门面 7）",
        )

    # 依赖三处零新增
    dependency_text = _dependency_text(PYPROJECT)
    for forbidden in ("langgraph", "langchain", "langsmith", "typing_extensions", "typing-extensions"):
        check(
            forbidden not in dependency_text.lower(),
            f"FR-016 ② 依赖三处声明**零**「{forbidden}」",
        )

    # ⚠️ **2026-11-12 补**：dev/test 的 ``differential`` 组（**差分夹具** · B5F2）按
    # 《立项书》S5 ② **允许**声明 ``langgraph``（**绝不**进 ``Requires-Dist``）⇒
    # **针对性**断言：① 该组里的上游包 MUST **钉版本**；② MUST **NOT** 出现在发行面。
    import tomllib as _tomllib

    _data = _tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    _diff = _data.get("dependency-groups", {}).get("differential", [])
    _diff_text = " ".join(str(item) for item in _diff)
    check(
        "langgraph" not in _diff_text or "==" in _diff_text,
        "dev/test 的 `differential` 组里的上游包 MUST **钉版本**（S5 ②）",
    )
    check(
        "langgraph" not in _diff_text.replace("langgraph==1.2.11", ""),
        "dev/test 的 `differential` 组 MUST 只含**已钉版本**的上游包",
    )

    # CI 不装 langgraph
    check(
        CI_WORKFLOW.read_text(encoding="utf-8").lower().count("langgraph") == 0,
        "FR-016 ③ CI 作业内 `langgraph` 安装次数 == 0",
    )

    # 层注册表零改动
    registry = LAYER_REGISTRY.read_text(encoding="utf-8")
    check(
        re.search(r"\|\s*`src/freegraph/runtime/`\s*\|\s*`L2`\s*\|", registry) is not None,
        "SC-012 层注册表把 `src/freegraph/runtime/` 登记为 **L2**（零改动）",
    )

    # L2 → L3/L4/L5 边数 == 0
    edges: list[str] = []
    runtime_dir = REPO_ROOT / "src" / "freegraph" / "runtime"
    for path in sorted(runtime_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            for name in names:
                for upper in UPPER_LAYER_MODULES:
                    if f"freegraph.{upper}" in name:
                        edges.append(f"{path.name} → {name}")
    check(not edges, "SC-012 L2 → L3 / L4 / L5 的边数 == 0", "; ".join(edges))

    # 门禁编号仍为 30 且连续
    contract = ARCHITECTURE_GATES.read_text(encoding="utf-8")
    overview = re.search(r"^##\s*0\..*?(?=^##\s|\Z)", contract, re.S | re.M)
    identifiers = (
        re.findall(r"\|\s*\*\*G(\d+)\*\*\s*\|", overview.group(0)) if overview else []
    )
    eq(identifiers, [str(n) for n in range(1, 31)], "SC-012 门禁编号总数仍为 **30** 且连续")

    # 署名头 + docstring
    bad_headers: list[str] = []
    for relative_path in NEW_SOURCE_FILES:
        path = REPO_ROOT / relative_path
        if not path.is_file():
            bad_headers.append(f"{relative_path}（缺文件）")
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines or lines[0] != SIGNATURE_HEADER:
            bad_headers.append(f"{relative_path}（署名头）")
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        body = tree.body
        if not (body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)):
            bad_headers.append(f"{relative_path}（docstring 不是首个语句）")
    check(
        not bad_headers,
        f"SC-012 新建源文件署名头 + docstring 覆盖率 == 100%（{len(NEW_SOURCE_FILES)} 个文件）",
        "; ".join(bad_headers),
    )

    # THIRD_PARTY_NOTICES 无需新增登记
    notices = NOTICES.read_text(encoding="utf-8")
    notice_section = re.search(r"^##\s*2\..*?(?=^##\s|\Z)", notices, re.S | re.M)
    rows = (
        [
            line.strip()
            for line in notice_section.group(0).splitlines()
            if line.strip().startswith("|")
            and not re.match(r"^\|[\s\-|:]+\|$", line.strip())
            and not line.strip().startswith("| 包 ")
            and "（暂无条目）" not in line
        ]
        if notice_section
        else []
    )
    check(not rows, "FR-019 THIRD_PARTY_NOTICES 的第三方运行时依赖表**无数据行**（零新增依赖）", str(rows))


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


def _dependency_text(pyproject: Path) -> str:
    """把 ``pyproject.toml`` 的**三处依赖声明**摊平成文本（按 TOML 解析）。"""
    import tomllib

    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = data.get("project", {})

    def _flat(sections: object) -> str:
        if isinstance(sections, dict):
            return " ".join(_flat(value) for value in sections.values())
        if isinstance(sections, (list, tuple)):
            return " ".join(str(item) for item in sections)
        return str(sections)

    # ⚠️ **2026-11-12 · 门禁订正（既有漂移 · 非本轮引入）**：原口径把
    # ``[dependency-groups]`` **一并**摊平 ⇒ B5F2 的**差分夹具**组
    # （``differential`` · 按《立项书》S5 ② 允许 ``langgraph`` 作为 **dev/test 依赖**）
    # ⇒ 门禁自 B5F2 起**一直红**。⇒ 本次**只**摊平**发行面**
    # （``project.dependencies`` + ``project.optional-dependencies``）⇒
    # **守住「发行依赖面零上游」这条本意**；dev/test 组另由**针对性**断言守
    # （见下方「``differential`` MUST 钉版本且 MUST NOT 出现在发行面」）。
    return " ".join(
        [
            _flat(project.get("dependencies", [])),
            _flat(project.get("optional-dependencies", {})),
        ]
    ).lower()


# ─────────────────────────────────────────────────────────────────────────────
# 汇总 + 记录
# ─────────────────────────────────────────────────────────────────────────────
def finish(title: str) -> int:
    print(f"\n── {title} 汇总 ──")
    print(f"硬断言 {_CHECKS} 条 · 通过 {_CHECKS - len(_FAILED)} · 失败 {len(_FAILED)}")
    for item in _FAILED:
        print(f"  ✘ {item}")
    if _SOFT:
        print(f"待环境就绪 {len(_SOFT)} 条（不判失败）：")
        for item in _SOFT:
            print(f"  ◌ {item}")
    print("结论：" + ("PASS" if not _FAILED else "FAIL"))
    return 0 if not _FAILED else 1


def build_record(mode: str, verdict: str, rc: int) -> str:
    out: list[str] = []
    out.append("# B4F1 验收记录（由 `harness/verification/B4F1/acceptance.py` 生成）")
    out.append("")
    out.append("## 1. 环境")
    out.append("")
    out.append("| 项 | 内容 |")
    out.append("|---|---|")
    out.append(f"| 操作系统 | {platform.system()} {platform.release()} ({platform.machine()}) |")
    out.append(f"| Python | {sys.version.split()[0]}（`{sys.executable}`） |")
    out.append(f"| 运行模式 | {mode} |")
    out.append(f"| 工作目录 | `{os.getcwd()}` |")
    out.append("| 依赖 | 本脚本**仅** Python 标准库（零第三方） |")
    out.append("")
    out.append("## 2. 步骤")
    out.append("")
    out.append("```bash")
    out.append("python3 harness/verification/B4F1/acceptance.py")
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


def main() -> int:
    parser = argparse.ArgumentParser(description="B4F1 人工验收脚本")
    parser.add_argument("--record", help="把验收记录片段写到该路径")
    parser.add_argument(
        "--require-installed",
        action="store_true",
        help="要求当前环境**已安装** freegraph（否则判失败）",
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

    print("══ acceptance · B4F1 状态 schema 解析 + 归约器提取 ══")
    runtime, mode = _load_runtime()
    if not _installed():
        if args.require_installed:
            check(False, "当前环境**已安装** freegraph（--require-installed）", "未安装")
        else:
            print("  ◌ 当前环境未安装 freegraph ⇒ 依赖闭包判据标「环境未就绪」")
    started = time.monotonic()

    cases = (
        ("case_a1_reducer_identification", lambda: case_a1_reducer_identification(runtime)),
        ("case_a2_binary_criterion", lambda: case_a2_binary_criterion(runtime)),
        ("case_a3_overwrite_semantics", lambda: case_a3_overwrite_semantics(runtime)),
        ("case_metadata_not_misjudged", lambda: case_metadata_not_misjudged(runtime)),
        ("case_error_contract", lambda: case_error_contract(runtime)),
        ("case_pure_data", lambda: case_pure_data(runtime)),
        ("case_zero_side_effects", lambda: case_zero_side_effects(runtime)),
        ("case_typing_extensions_variant", lambda: case_typing_extensions_variant(runtime)),
        ("case_frozen_surface", lambda: case_frozen_surface(runtime)),
    )
    for name, case in cases:
        try:
            case()
        except Exception as exc:  # noqa: BLE001
            check(False, f"用例组 {name} 未抛异常即完成", f"{type(exc).__name__}: {exc}")

    rc = finish("B4F1 人工验收")
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
