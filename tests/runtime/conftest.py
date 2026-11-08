# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B4F1 的**共享夹具** —— 子进程执行器 + 二元性判定表取样。

三组能力：

1. **路径基线**（``repo_root`` / ``src_dir`` / ``criterion_path``）
   —— 沿用 ``tests/contracts/conftest.py`` 的路径基线口径；
2. **子进程执行器**（``run_in_subprocess``）—— 在**子进程**里执行一段
   Python 并回传 JSON（SC-007 的 ``sys.modules`` 增量 / 环境变量读取 /
   出站连接三断言**必须在子进程**执行：测试进程自身已导入 pytest ⇒
   同进程 ``sys.modules`` 不可用 · 沿用 B1F1 / B3F1 的既有口径）；
3. **判定表取样**（``binary_criterion_rows`` /
   ``binary_criterion_fixture_names`` / ``binary_criterion_namespace``）
   —— 解析 ``specs/b4f1-schema-reducer-parse/contracts/binary-criterion.md``
   的 §2（16 类二元性形态）/ §3（2 类提取形态）/ §4（夹具清单）
   ⇒ **判据与用例天然分离**（research D-03 · 与既有门禁 G25 解析
   ``layer-registry.md`` 同构）⇒ **MUST NOT** 在测试里另抄一份表。

**计数口径 MUST 写死**（否则「次数 == 0」不可判定）：

* **环境变量** —— 同时覆盖 ``os.environ.__getitem__`` /
  ``os.environ.get`` / ``os.getenv`` **三条**读取路径；
* **出站** —— 同时覆盖 ``socket.socket.connect`` /
  ``socket.create_connection`` **两个**入口；
* **``sys.modules``** —— 「非标准库」判定 = 名字**不在**
  ``sys.stdlib_module_names`` 中**且**不是 ``freegraph`` 自身模块
  （SC-007 的字面口径）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import functools
import importlib
import json
import operator
import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
CRITERION_PATH = (
    REPO_ROOT
    / "specs"
    / "b4f1-schema-reducer-parse"
    / "contracts"
    / "binary-criterion.md"
)

# §2 的行数（FR-016 ①-a · SC-004「缺失条数 == 0」）· §3 的行数（FR-016 ①-b）。
BINARY_CRITERION_ROW_COUNT = 16
EXTRACTION_CRITERION_ROW_COUNT = 2


# ── 子进程执行器（SC-007）────────────────────────────────────────────────

_SUBPROCESS_PRELUDE = r'''
import json as _json
import os as _os
import socket as _socket
import sys as _sys

COUNTERS = {"env": 0, "egress": 0}

# ── ① 环境变量读取：覆盖 os.environ.__getitem__ / os.environ.get / os.getenv
#    **三条**读取路径（计数口径 MUST 写死 —— 否则「次数 == 0」不可判定）。
_Environ = type(_os.environ)
_orig_environ_getitem = _Environ.__getitem__
_orig_environ_get = _Environ.get
_orig_getenv = _os.getenv


def _patched_environ_getitem(self, key):
    COUNTERS["env"] += 1
    return _orig_environ_getitem(self, key)


def _patched_environ_get(self, key, default=None):
    COUNTERS["env"] += 1
    return _orig_environ_get(self, key, default)


def _patched_getenv(key, default=None):
    # 直接走**原始**的类方法 ⇒ 不重复计数（``os.getenv`` 内部亦调 ``environ.get``）。
    COUNTERS["env"] += 1
    return _orig_environ_get(_os.environ, key, default)


_os.environ.__getitem__ = _patched_environ_getitem
_os.environ.get = _patched_environ_get
_os.getenv = _patched_getenv

# ── ② 出站：覆盖 socket.socket.connect / socket.create_connection **两个**入口。
_orig_socket_connect = _socket.socket.connect
_orig_create_connection = _socket.create_connection


def _patched_socket_connect(self, address):
    COUNTERS["egress"] += 1
    return _orig_socket_connect(self, address)


def _patched_create_connection(address, *args, **kwargs):
    COUNTERS["egress"] += 1
    return _orig_create_connection(address, *args, **kwargs)


_socket.socket.connect = _patched_socket_connect
_socket.create_connection = _patched_create_connection


def snapshot_modules():
    """当前 ``sys.modules`` 的快照（用于增量比对）。"""
    return set(_sys.modules)


def non_stdlib_delta(before):
    """``sys.modules`` 增量中的**非标准库**条目（SC-007 的字面口径）。

    「非标准库」= 名字**不在** ``sys.stdlib_module_names`` 中**且**
    **不是** ``freegraph`` 自身模块 ⇒ ``typing_extensions`` / ``pydantic``
    等 site-packages 包**计入**。
    """
    stdlib = set(_sys.stdlib_module_names)
    return sorted(
        name
        for name in set(_sys.modules) - set(before)
        if name.split(".")[0] not in stdlib and not name.startswith("freegraph")
    )


def third_party_modules():
    """``sys.modules`` 中的**第三方 / 准第三方**模块名（SC-011 的字面口径）。"""
    prefixes = ("langchain", "langgraph", "langsmith", "pydantic", "typing_extensions")
    return sorted(
        name
        for name in _sys.modules
        if any(name == prefix or name.startswith(prefix) for prefix in prefixes)
    )
'''


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """仓库根目录（判定表 / 人工验证记录的定位基准）。"""
    return REPO_ROOT


@pytest.fixture(scope="session")
def src_dir() -> Path:
    """``<repo>/src``（源码树根）。"""
    return SRC_DIR


@pytest.fixture(scope="session")
def criterion_path() -> Path:
    """二元性判据的**唯一权威**文件（``<!-- authority: yes -->``）。"""
    return CRITERION_PATH


@pytest.fixture(scope="session")
def run_in_subprocess() -> Callable[[str], dict[str, Any]]:
    """在**子进程**里执行一段 Python 并回传 JSON（SC-007 · SC-011）。

    被执行的源码 MUST 以 ``print(json.dumps(payload))`` 结束 ⇒ 返回值是
    该 payload 与两条计数器（``env_reads`` / ``egress``）的合并字典。

    前置脚本（``_SUBPROCESS_PRELUDE``）**写死**了计数口径：环境变量三条
    读取路径 · 出站两个入口 · ``sys.modules`` 的「非标准库」判定。
    """

    def _run(source: str, *, timeout: float = 120.0) -> dict[str, Any]:
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [str(SRC_DIR)]
            + [entry for entry in sys.path if entry and os.path.isdir(entry)]
        )
        completed = subprocess.run(
            [sys.executable, "-c", _SUBPROCESS_PRELUDE + "\n" + source],
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
        )
        if completed.returncode != 0:
            raise AssertionError(
                "子进程执行失败"
                f"（returncode={completed.returncode}）\n"
                f"--- stdout ---\n{completed.stdout}\n"
                f"--- stderr ---\n{completed.stderr}"
            )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise AssertionError(
                f"子进程未输出合法 JSON：{completed.stdout!r} / {completed.stderr!r}"
            ) from error
        counters = payload.pop("__counters__", {})
        return {
            **payload,
            "env_reads": counters.get("env", 0),
            "egress": counters.get("egress", 0),
        }

    return _run


# ── 判定表取样（research D-03）──────────────────────────────────────────

_BACKTICKED = re.compile(r"`([^`]+)`")


def _section_lines(lines: list[str], heading_prefix: str) -> list[str]:
    """取出某个 ``##`` 小节的正文行（**不含**小节标题本身）。"""
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
        fixture_rows.append(
            {
                "name": name,
                "definition": _backticked(cells[1]),
                "note": cells[2],
            }
        )

    return {
        "binary": binary_rows,
        "extraction": extraction_rows,
        "fixtures": fixture_rows,
    }


# ── §4 夹具清单的**实际对象**（求值命名空间 · 逐名一致）─────────────────
#
# 判定表的「输入」列**一律**是 §4 里的名字 ⇒ 求值路径**只有一套**。
# 下列定义与 §4 的「定义」列**逐字同构**。


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
#: **实例**」；§5 的实测签名 ``(a, b)`` 亦是**实例**的签名 —— 类本身的
#: 签名是 ``()``）。
callable_instance = CallableInstance()

#: §4 的 ``CallableKwOnlyInstance`` = **实例**（§2 第 13 行）。
callable_kw_only_instance = CallableKwOnlyInstance()

#: ``functools.partial(add, 1)``（§2 第 14 行）⇒ 签名 ``(b, /)`` ⇒ 1 个 ⇒ 拒绝。
partial_add_one = functools.partial(operator.add, 1)

#: 绑定方法（``self`` 已绑定 · §2 第 15 行）⇒ 签名 ``(b)`` ⇒ 1 个 ⇒ 拒绝。
bound_method = two_positional.__get__(object())

#: 元数据元组 · 末位**非** callable（§3 E-1）⇒ 无归约器 · **不报错**。
meta_non_callable = ("说明文字",)

#: 元数据元组 · 末位才是 callable（§3 E-2）⇒ 只认**末位**。
meta_multi_entry = ("描述", operator.add)


def _build_namespace() -> dict[str, Any]:
    """构造 §4 夹具清单的**求值命名空间**（**逐名一致**）。

    ⚠️ 键名 MUST 与 §4 的「名字」列**逐字一致**（含 ``operator.add`` 这个
    带点的名字）⇒ 命名空间**恰为** §4 的 18 个名字。
    """
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
        "partial_add_one": partial_add_one,
        "bound_method": bound_method,
        "str": str,
        "meta_non_callable": meta_non_callable,
        "meta_multi_entry": meta_multi_entry,
    }


#: 判定表的**模块级**快照（解析权威文件一次）——供 ``pytest_generate_tests``
#: 做**逐条**参数化（collection 期 MUST 已有数据 ⇒ 不能只靠夹具）。
CRITERION_TABLES: dict[str, list[dict[str, str]]] = _parse_criterion_tables(
    CRITERION_PATH.read_text(encoding="utf-8")
)

#: §2 + §3 的**全部**行（判定表的逐条比对对象）。
CRITERION_ROWS: list[dict[str, str]] = [
    *CRITERION_TABLES["binary"],
    *CRITERION_TABLES["extraction"],
]

#: §4 夹具清单的**求值命名空间**（模块级快照）。
CRITERION_NAMESPACE: dict[str, Any] = _build_namespace()


def resolve_criterion_input(name: str) -> Any:
    """按**名字**取 §4 夹具清单里的**实际对象**（求值路径**只有一套**）。

    ① 直接命中命名空间（§2 / §3 的「输入」列**一律**是 §4 里的名字）；
    ② 带点的名字（形如 ``pkg.mod.attr``）⇒ 取首段模块的顶层属性。

    ⚠️ **MUST NOT** 在测试里另抄一份夹具（research D-03）。
    """
    if name in CRITERION_NAMESPACE:
        return CRITERION_NAMESPACE[name]
    head, _, tail = name.partition(".")
    if head and tail:
        module = importlib.import_module(head)
        return getattr(module, tail)
    raise KeyError(name)


@pytest.fixture(scope="session")
def binary_criterion_tables(criterion_path: Path) -> dict[str, list[dict[str, str]]]:
    """判定表的三张表（§2 形态 / §3 提取 / §4 夹具清单）——**解析**权威文件。"""
    return _parse_criterion_tables(criterion_path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def binary_criterion_rows(
    binary_criterion_tables: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    """§2（16 类二元性形态）+ §3（2 类提取形态）的**全部**行。"""
    return [*binary_criterion_tables["binary"], *binary_criterion_tables["extraction"]]


@pytest.fixture(scope="session")
def binary_criterion_fixture_names(
    binary_criterion_tables: dict[str, list[dict[str, str]]],
) -> list[str]:
    """§4 夹具清单的**全部**名字（判定表「输入」列的唯一命名空间）。"""
    return [row["name"] for row in binary_criterion_tables["fixtures"]]


@pytest.fixture(scope="session")
def binary_criterion_namespace() -> dict[str, Any]:
    """§4 夹具清单的**求值命名空间**（逐名一致）。"""
    return _build_namespace()


@pytest.fixture(scope="session")
def criterion_evaluator(
    binary_criterion_namespace: dict[str, Any],
) -> Callable[[str], Any]:
    """按**名字**求值判定表「输入」列的表达式（求值路径**只有一套**）。"""

    def _evaluate(expression: str) -> Any:
        return resolve_criterion_input(expression)

    return _evaluate
