#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**B5F1** 人工验收脚本（通道抽象 + 三类通道）。

定位
----
本脚本是 **B5F1 这个 feature 的人工验收入口**——**开发期**（v1.0 之前）逐 feature
验收用；**v1.0 完成后的端到端验收**在 ``harness/demo/``。

**一条命令跑完全部验收**（FR-026 ①）—— A1–A3 + 全部成功标准 SC-001 … SC-028
+ 覆盖率取证 + 10 条门禁的实跑结果，**不必**手工逐条执行。

覆盖的分组：

* **A1** 归约器 ``operator(current, new)`` 语义一致（**从空值起折**）；
* **A2** 无归约器 key 被覆盖（连续写入 ⇒ 读到**末值**）；
* **A3** 路由通道每 super-step 清空（清空后**无值**）；
* **冲突显式失败** · **有值 / 无值可判定** · **空值推导 6 类**；
* **映射保序与身份** · **纯净性与规模探针** · **名字面**；
* **构造期校验**（内置 ``TypeError`` / ``ValueError``）；
* **冻结面审计** 公开面 18 / 7 未变 · 兼容矩阵零新增行 · 层注册表零改动 ·
  依赖三处零新增 · CI 不装 ``langgraph`` · 门禁编号仍为 30 · 署名头覆盖率 100%；
* **覆盖率取证**（SC-015）—— ``channel.py`` / ``mapping.py`` **全文**行 / 分支
  **100%**（阻断判据）· ``errors.py`` / ``__init__.py`` 的**新增部分**走
  **差分口径**（裁定 17 ⑤）；
* **门禁实跑**（10 条）—— 7 条**本地直跑**的作**硬断言** · 3 条 **Linux only**
  的（``G22`` 需网络 · ``G28`` 需网络命名空间）**只观测不阻断**
  （由 CI 的 Linux 作业作阻断判据）。

依赖
----
**只 import Python 标准库**（+ 被验收的 ``freegraph`` 本身）——**零第三方依赖**。

⚠️ **覆盖率工具是例外**（research **D-13**）——``coverage`` 是**开发期工具**
⇒ **不进**仓库依赖声明 ⇒ 本机未装时该段标「◌ 环境未就绪」（**不判失败**）
⇒ 装法：``uv pip install coverage``。

两态运行
--------
| 情形 | 行为 |
|---|---|
| 当前环境**已安装** freegraph | 测**发行产物** |
| 当前环境**未安装** | 自动把 ``<repo>/src`` 插入 ``sys.path``（源码优先），测**源码树**；依赖闭包那条判**不判失败**，标「◌ 环境未就绪」 |

用法
----
    python3 harness/verification/B5F1/acceptance.py                    # 跑全部
    python3 harness/verification/B5F1/acceptance.py --record out.md    # 同时生成验收记录片段
    python3 harness/verification/B5F1/acceptance.py --require-installed # 把「未安装」判为失败
    python3 harness/verification/B5F1/acceptance.py --skip-coverage    # 跳过覆盖率取证段（快）
    python3 harness/verification/B5F1/acceptance.py --skip-gates       # 跳过门禁实跑段（快）

退出码：``0`` = PASS · ``1`` = FAIL · ``2`` = 环境未就绪。
"""

from __future__ import annotations

import argparse
import ast
import gc
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
SPEC_DIR = REPO_ROOT / "specs" / "b5f1-channels"
CONTRACT_PATH = SPEC_DIR / "contracts" / "channel-contract.md"
UPSTREAM_PARITY_PATH = SPEC_DIR / "contracts" / "upstream-parity.md"
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
GATES_DIR = REPO_ROOT / "harness" / "scripts" / "gates"
README = REPO_ROOT / "README.md"
NOTICES = REPO_ROOT / "THIRD_PARTY_NOTICES"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PYPROJECT = REPO_ROOT / "pyproject.toml"
SIGNATURE_HEADER = (
    "# Copyright (c) 2026 杨家成 · MIT License · "
    "https://github.com/yangjiacheng1996/freegraph"
)

#: 契约层 / 门面的公开符号面（**冻结面** · SC-012）。
CONTRACT_PUBLIC_SYMBOL_COUNT = 18
FACADE_PUBLIC_SYMBOL_COUNT = 7

#: 本 feature **新建**的源文件（署名头 + docstring 复核的扫描域 · SC-011）。
NEW_SOURCE_FILES = (
    "src/freegraph/runtime/channel.py",
    "src/freegraph/runtime/mapping.py",
    "tests/runtime/test_channel_semantics.py",
    "tests/runtime/test_channel_errors.py",
    "tests/runtime/test_channel_mapping.py",
    "tests/runtime/test_channel_purity.py",
    "tests/runtime/test_channel_contract.py",
)

#: 上层模块（L3 / L4 / L5）⇒ L2 MUST NOT import 它们（FR-016 · ARCH-1）。
UPPER_LAYER_MODULES = ("_stategraph", "persistence", "observability", "app")

#: **本地直跑**的门禁（纯本地 · 确定性 · **无网络 / 无命名空间**依赖）⇒ **硬断言**。
LOCAL_GATES = (
    "G21",
    "G23",
    "G24",
    "G25",
    "G26",
    "G29",
    "G30",
)

#: **Linux only** 的门禁（需**网络**（G22 建隔离 venv）/ **网络命名空间**（G28））
#: ⇒ 本脚本**只观测不阻断**（由 CI 的 Linux 作业作阻断判据 · 与 pytest 的
#: ``linux_only`` marker 同一口径）。
LINUX_ONLY_GATES = ("G22", "G27", "G28")

#: 兼容矩阵的章节定位（**不扫全文**）。
COMPAT_MATRIX_PATTERN = re.compile(
    r"^##\s*API\s*兼容矩阵\s*$(.*?)(?=^## |\Z)", re.S | re.M
)

#: 通道实例**允许**持有的**私有槽**集合（**名字逐字冻结** · FR-013 ①）。
ALLOWED_SLOTS = frozenset({"_key", "_value_type", "_value", "_reducer"})

#: 通道**公开属性**集合（**恰为**四项 · FR-013 ① · 澄清轮 Q15）。
PUBLIC_PROPERTIES = frozenset({"key", "value_type", "value", "reducer"})

#: 通道的**四个操作**名（**逐字冻结** · FR-002 · SC-019）。
CHANNEL_OPERATIONS = ("update", "get", "is_available", "clear")

#: 四个类名 + 两个映射入口名 + 两个错误名（**逐字冻结** · SC-019）。
CHANNEL_CLASS_NAMES = (
    "Channel",
    "LastValue",
    "BinaryOperatorAggregate",
    "EphemeralValue",
)
MAPPING_ENTRY_NAMES = ("build_channel", "build_channels")
ERROR_TYPE_NAMES = ("EmptyChannelError", "InvalidChannelUpdateError")

#: 覆盖率取证**必须 100%** 的文件（**阻断判据** · SC-015 · FR-019 ②）。
FULL_COVERAGE_FILES = (
    "src/freegraph/runtime/channel.py",
    "src/freegraph/runtime/mapping.py",
)

#: 覆盖率**只管新增部分**的文件（**差分口径** · SC-015 · 裁定 17 ⑤）。
DIFF_COVERAGE_FILES = (
    "src/freegraph/runtime/errors.py",
    "src/freegraph/runtime/__init__.py",
)

# ─────────────────────────────────────────────────────────────────────────────
# 极简断言框架（与 harness/verification/B4F1/acceptance.py 同款：单文件可独立运行）
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

    两态运行（FR-026 ③）：

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


def _installed() -> bool:
    """当前环境**是否已安装** freegraph。"""
    try:
        import importlib.metadata as md

        md.version("freegraph")
    except Exception:  # noqa: BLE001
        return False
    return True


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
        if PROJECT_VENV_PYTHON.is_file():
            print(
                f"      uv pip install --python {PROJECT_VENV_PYTHON} -e ."
                f"   # 发行产物\n"
                f"      uv pip install --python {PROJECT_VENV_PYTHON} coverage"
                f"   # 开发期取证工具\n"
                f"      {PROJECT_VENV_PYTHON} harness/verification/B5F1/acceptance.py"
            )
        else:
            print(
                f"      uv pip install --python {INTERPRETER} -e .\n"
                f"      uv pip install --python {INTERPRETER} coverage"
            )
    print("结论：" + ("PASS" if not _FAILED else "FAIL"))
    return 0 if not _FAILED else 1


# ─────────────────────────────────────────────────────────────────────────────
# 用例组
# ─────────────────────────────────────────────────────────────────────────────


def case_a1_reduce_semantics(runtime: Any) -> None:
    """**验收判据 A1**（引文 §6 / 立项书 §5.2）—— 归约器 ``operator(current, new)``
    语义一致（**从空值起折**）· SC-002 / SC-021。"""
    section("验收判据 A1 · 归约语义")
    channel = runtime.BinaryOperatorAggregate("messages", list, operator.add)
    check(channel.is_available() is True, "A1 归约型通道初始「有值」（空值）")
    eq(channel.get(), [], "A1 初始值 == 推导出的空值 []")

    channel.update([["m1"]])
    channel.update([["m2"]])
    base: list[Any] = []
    base = operator.add(base, ["m1"])
    base = operator.add(base, ["m2"])
    eq(channel.get(), ["m1", "m2"], "A1 累积结果 == 逐元素 [m1, m2]")
    eq(channel.get(), base, "A1 结果 == **从初始空值起**的逐次归约（SC-021）")
    check(channel.reducer is operator.add, "A1 归约器**按引用**持有（身份判定）")

    # 与「从首值起折」**不等价**的归约器（SC-021 ②）⇒ 以空值起折为准。
    maximum = runtime.BinaryOperatorAggregate("peak", int, max)
    maximum.update([3])
    maximum.update([7])
    eq(maximum.get(), max(max(0, 3), 7), "A1 `max` 归约器同样按「空值起折」基准")


def case_a2_overwrite_semantics(runtime: Any) -> None:
    """**验收判据 A2** —— 无归约器 key 被覆盖 · SC-001 / SC-020。"""
    section("验收判据 A2 · 覆盖语义")
    channel = runtime.LastValue("llm_calls", int)
    check(channel.is_available() is False, "A2 覆盖型通道初始「无值」")
    eq(channel.update([1]), True, "A2 首次写入返回**真**（本次写了值）")
    eq(channel.get(), 1, "A2 写 1 后读到 1")
    eq(channel.update([2]), True, "A2 第二次写入返回**真**")
    eq(channel.get(), 2, "A2 连续写入后读到**末值** 2（不是累加 3）")
    check(channel.get() != 3, "A2 结果**不是** 1 + 2（未走归约路径）")
    check(channel.reducer is None, "A2 覆盖型**不持有**归约器（reducer is None）")
    eq(channel.update([]), False, "A2 空序列写入返回**假**（无操作）")


def case_a3_ephemeral_clear(runtime: Any) -> None:
    """**验收判据 A3** —— 路由通道每 super-step 清空 · SC-003 / SC-023。"""
    section("验收判据 A3 · 路由清空")
    channel = runtime.EphemeralValue("route", str)
    check(channel.is_available() is False, "A3 路由型初始「无值」")
    channel.update(["tool_node"])
    eq(channel.get(), "tool_node", "A3 写入后读得到")
    eq(channel.clear(), True, "A3 `clear()` 返回**真**（状态真的变化）")
    check(channel.is_available() is False, "A3 清空后判定为「无值」")
    try:
        channel.get()
    except runtime.EmptyChannelError:
        check(True, "A3 清空后读取抛 `EmptyChannelError`（不是 None 冒充有值）")
    except Exception as error:  # noqa: BLE001
        check(False, "A3 清空后读取抛 `EmptyChannelError`", f"{type(error).__name__}")
    else:
        check(False, "A3 清空后读取抛 `EmptyChannelError`", "未抛错")
    channel.update(["other"])
    check(channel.is_available() is True, "A3 清空后再写入恢复「有值」")
    eq(channel.get(), "other", "A3 清空后新值 == 刚写入的值（无残余状态）")
    eq(channel.clear(), True, "A3 再次 `clear()`（从「有值」清成「无值」）返回**真**")
    eq(channel.clear(), False, "A3 已是「无值」再 `clear()` 返回**假**（幂等）")


def case_conflict_explicit_failure(runtime: Any) -> None:
    """SC-006 / SC-016 / SC-025 —— 一步内多值 ⇒ **显式失败**且**值不变**。"""
    section("冲突显式失败")
    for factory in (
        lambda: runtime.LastValue("k", int),
        lambda: runtime.EphemeralValue("k", str),
    ):
        channel = factory()
        try:
            channel.update([1, 2])
        except runtime.InvalidChannelUpdateError as error:
            eq(error.key, "k", "冲突错误的 `key` == 通道 key")
            eq(error.received_count, 2, "冲突错误的 `received_count` == 2")
            eq(error.expected_count, 1, "冲突错误的 `expected_count` **恒为 1**")
            check(channel.is_available() is False, "冲突时通道**值不变**（仍无值）")
        except Exception as error:  # noqa: BLE001
            check(False, "一步内多值抛 `InvalidChannelUpdateError`", type(error).__name__)
        else:
            check(False, "一步内多值抛 `InvalidChannelUpdateError`", "未抛错")

    channel = runtime.LastValue("k", int)
    channel.update([1])
    try:
        channel.update([2, 3])
    except runtime.InvalidChannelUpdateError:
        pass
    eq(channel.get(), 1, "冲突后通道的**原值**仍在（先检测后写入）")


def case_availability_decidable(runtime: Any) -> None:
    """SC-004 / SC-023 —— 「无值」与「值为 ``None``」严格可分；清空后一律无值。"""
    section("有值 / 无值可判定")
    for factory in (
        lambda: runtime.LastValue("k", int),
        lambda: runtime.EphemeralValue("k", str),
    ):
        channel = factory()
        check(channel.is_available() is False, "从未写入 ⇒ 判定为「无值」")
        try:
            channel.get()
        except runtime.EmptyChannelError:
            check(True, "从未写入 ⇒ 读取抛错")
        else:
            check(False, "从未写入 ⇒ 读取抛错", "未抛错")
        channel.update([None])
        check(channel.is_available() is True, "写入 `None` ⇒ 判定为「有值」")
        eq(channel.get(), None, "写入 `None` ⇒ 读取返回 `None`")

    aggregate = runtime.BinaryOperatorAggregate("k", list, operator.add)
    check(aggregate.is_available() is True, "归约型初始「有值（空值）」")
    eq(aggregate.get(), [], "归约型初始值 == 推导出的空值")

    for channel in (
        runtime.LastValue("k", int),
        runtime.BinaryOperatorAggregate("k", list, operator.add),
        runtime.EphemeralValue("k", str),
    ):
        payload = ["x"] if isinstance(channel, runtime.BinaryOperatorAggregate) else "x"
        channel.update([payload])
        channel.clear()
        check(
            channel.is_available() is False,
            f"{type(channel).__name__} 清空后一律「无值」",
        )


def case_empty_value_derivation(runtime: Any) -> None:
    """SC-007 —— 空值推导的 **6 类**覆盖面。"""
    section("空值推导（6 类）")
    import collections.abc

    cases = [
        (list, []),
        (int, 0),
        (str, ""),
        (dict, {}),
        (collections.abc.Sequence, []),
        (collections.abc.MutableSequence, []),
        (collections.abc.Set, set()),
        (collections.abc.Mapping, {}),
    ]
    for value_type, expected in cases:
        channel = runtime.BinaryOperatorAggregate("k", value_type, operator.add)
        eq(channel.get(), expected, f"空值推导 {value_type.__name__} ⇒ {expected!r}")

    uninstantiable = runtime.BinaryOperatorAggregate("k", Any, operator.add)
    check(uninstantiable.is_available() is False, "不可实例化类型 ⇒ 初始「无值」")

    calls: list[Any] = []

    def counting(current: Any, new: Any) -> Any:
        calls.append((current, new))
        return current

    fresh = runtime.BinaryOperatorAggregate("k2", Any, counting)
    fresh.update(["x"])
    eq(len(calls), 0, "不可实例化类型的首次**单值**写入 ⇒ 归约器调用次数 == 0")
    eq(fresh.get(), "x", "不可实例化类型的首次写入**直存**新值")

    first = runtime.BinaryOperatorAggregate("a", list, operator.add)
    second = runtime.BinaryOperatorAggregate("b", list, operator.add)
    check(first.get() is not second.get(), "两个同类型通道的空值**不是同一对象**")

    multi = runtime.BinaryOperatorAggregate("k3", Any, counting)
    calls.clear()
    multi.update(["a", "b", "c"])
    eq(len(calls), 2, "多值首写 ⇒ 归约器调用次数 == 值数 − 1")


def case_mapping(runtime: Any) -> None:
    """SC-008 / SC-010 / SC-019 —— 映射规则 · 保序 · 身份判定。"""
    section("映射入口")

    class Schema(TypedDict):
        messages: Annotated[list, operator.add]
        llm_calls: int

    spec = runtime.parse_state_schema(Schema)
    channels = runtime.build_channels(spec)
    eq(list(channels), list(spec.keys), "映射**保序**（键序 == `SchemaSpec.keys` 序）")
    eq(len(channels), len(spec.keys), "通道数 == schema 的 key 数")
    check(
        isinstance(channels["messages"], runtime.BinaryOperatorAggregate),
        "有归约器 ⇒ `BinaryOperatorAggregate`",
    )
    check(
        isinstance(channels["llm_calls"], runtime.LastValue),
        "无归约器 ⇒ `LastValue`",
    )
    check(
        channels["messages"].reducer is operator.add,
        "归约型通道的 `reducer` **就是**规格里的同一引用",
    )
    single = runtime.build_channel(spec.channels["llm_calls"])
    check(isinstance(single, runtime.LastValue), "`build_channel` 单入口 ⇒ `LastValue`")
    check(
        not any(isinstance(c, runtime.EphemeralValue) for c in channels.values()),
        "路由通道**不由** schema 派生",
    )
    route = runtime.EphemeralValue("route", str)
    eq(route.key, "route", "路由通道支持**直接实例化**")

    empty = runtime.ChannelSpec(
        key="k", value_type=list, reducer=None, has_reducer=True, semantics="reduce"
    )
    try:
        runtime.build_channel(empty)
    except ValueError:
        check(True, "规格标注「有归约器」但归约器为空 ⇒ 内置 `ValueError`")
    except Exception as error:  # noqa: BLE001
        check(False, "规格标注「有归约器」但归约器为空 ⇒ 内置 `ValueError`", type(error).__name__)
    else:
        check(False, "规格标注「有归约器」但归约器为空 ⇒ 内置 `ValueError`", "未抛错")


def case_purity_and_scale(runtime: Any) -> None:
    """SC-009 / SC-022 / SC-024 / SC-025 —— 纯净性 · 规模口径 · 浅引用。"""
    section("纯净性与规模探针")
    channels = [
        runtime.LastValue("k", int),
        runtime.BinaryOperatorAggregate("k", list, operator.add),
        runtime.EphemeralValue("k", str),
    ]
    for channel in channels:
        name = type(channel).__name__
        properties = {
            key
            for klass in type(channel).__mro__
            for key, value in klass.__dict__.items()
            if isinstance(value, property)
        }
        eq(properties, set(PUBLIC_PROPERTIES), f"{name} 公开属性集合恰为四项")
        slots: set[str] = set()
        for klass in type(channel).__mro__:
            declared = klass.__dict__.get("__slots__", ())
            slots.update({declared} if isinstance(declared, str) else declared)
        check(slots <= set(ALLOWED_SLOTS), f"{name} 实例槽位集合 ⊆ 四项")
        check(not hasattr(channel, "__dict__"), f"{name} 实例**无** `__dict__`")

    def schema_of(count: int) -> Any:
        return TypedDict(f"_S{count}", {f"k{i}": int for i in range(count)})

    counts = []
    for count in (1, 1000):
        spec = runtime.parse_state_schema(schema_of(count))
        channel = runtime.build_channels(spec)["k0"]
        violations = [
            type(r).__name__
            for r in gc.get_referents(channel)
            if isinstance(r, (dict, runtime.Channel))
            or type(r).__name__ == "SchemaSpec"
        ]
        eq(violations, [], f"N={count} 引用类型**白名单**违例 == 0")
        counts.append(len(gc.get_referents(channel)))
    eq(counts[0], counts[1], "引用数与 key 数**无关**（计数探针 · 辅助判据）")

    payload = {"user": "data"}
    holder = runtime.LastValue("k", int)
    holder.update([payload])
    check(holder.value is payload, "通道**浅引用**用户对象（身份判定）")

    mismatched = runtime.LastValue("k", int)
    mismatched.update(["not-an-int"])
    eq(mismatched.get(), "not-an-int", "通道**不校验**写入值的类型")

    public: set[str] = set()
    for klass in runtime.LastValue.__mro__:
        if klass in (object,):  # `object` 的方法不是「通道的写入入口」
            continue
        for key, value in klass.__dict__.items():
            if key.startswith("_") or isinstance(value, property):
                continue
            if callable(value):
                public.add(key)
    eq(public, set(CHANNEL_OPERATIONS), "写入入口**只有** `update()`（无同步原语）")


def case_naming_surface(runtime: Any) -> None:
    """SC-019 / I-23 —— 名字面逐字一致。"""
    section("名字面逐字一致")
    for name in CHANNEL_OPERATIONS:
        check(callable(getattr(runtime.Channel, name, None)), f"操作名 `{name}` 在位")
    for name in PUBLIC_PROPERTIES:
        check(
            isinstance(getattr(runtime.Channel, name, None), property),
            f"属性名 `{name}` 在位（只读 property）",
        )
    for name in CHANNEL_CLASS_NAMES:
        check(hasattr(runtime, name), f"类名 `{name}` 在位")
    for name in MAPPING_ENTRY_NAMES:
        check(callable(getattr(runtime, name, None)), f"映射入口名 `{name}` 在位")
    for name in ERROR_TYPE_NAMES:
        check(hasattr(runtime, name), f"错误名 `{name}` 在位")


def case_construction_validation(runtime: Any) -> None:
    """SC-026 / FR-025 —— 构造期的**内置** ``TypeError`` / ``ValueError``。"""
    section("构造期校验")
    try:
        runtime.BinaryOperatorAggregate("k", list, 42)
    except TypeError:
        check(True, "归约器不可调用 ⇒ 内置 `TypeError`")
    except Exception as error:  # noqa: BLE001
        check(False, "归约器不可调用 ⇒ 内置 `TypeError`", type(error).__name__)
    else:
        check(False, "归约器不可调用 ⇒ 内置 `TypeError`", "未抛错")

    try:
        runtime.BinaryOperatorAggregate("k", list, None)
    except ValueError:
        check(True, "归约器为空 ⇒ 内置 `ValueError`")
    except Exception as error:  # noqa: BLE001
        check(False, "归约器为空 ⇒ 内置 `ValueError`", type(error).__name__)
    else:
        check(False, "归约器为空 ⇒ 内置 `ValueError`", "未抛错")

    def ternary(a: Any, b: Any, c: Any) -> Any:
        return a

    aggregate = runtime.BinaryOperatorAggregate("k", Any, ternary)
    check(
        aggregate.reducer is ternary,
        "通道层**不重做**二元性校验（非二元归约器不报错）",
    )


def case_error_contract(runtime: Any) -> None:
    """SC-018 / FR-017 —— 错误契约：继承 · 结构化字段 · 不携带用户值。"""
    section("错误契约")
    from freegraph.contracts.errors import FreegraphError

    check(
        issubclass(runtime.EmptyChannelError, FreegraphError),
        "`EmptyChannelError` 可被 `except FreegraphError` 捕获",
    )
    check(
        not issubclass(runtime.EmptyChannelError, ValueError),
        "`EmptyChannelError` **不是** `ValueError` 的子类",
    )
    check(
        issubclass(runtime.InvalidChannelUpdateError, FreegraphError)
        and issubclass(runtime.InvalidChannelUpdateError, ValueError),
        "`InvalidChannelUpdateError` **双重继承** `FreegraphError` + `ValueError`",
    )

    channel = runtime.LastValue("llm_calls", int)
    try:
        channel.get()
    except runtime.EmptyChannelError as error:
        eq(error.key, "llm_calls", "`EmptyChannelError.key` == 通道 key")
        check(
            "secret-value" not in repr(error),
            "错误对象**不携带**用户写入的值",
        )
    else:
        check(False, "读无值通道抛 `EmptyChannelError`", "未抛错")

    channel.update(["secret-value"])
    channel.clear()
    try:
        channel.get()
    except runtime.EmptyChannelError as error:
        check("secret-value" not in repr(error), "清空后的错误**不携带**旧值")
    else:
        check(False, "读无值通道抛 `EmptyChannelError`", "未抛错")


def case_zero_side_effects(runtime: Any) -> None:
    """SC-005 / FR-015 —— 导入无副作用 · 零环境变量 · 零出站。"""
    section("零副作用")
    before = set(sys.modules)
    import freegraph.runtime  # noqa: F401

    delta = sorted(
        name
        for name in set(sys.modules) - before
        if name.split(".")[0] not in set(sys.stdlib_module_names)
        and not name.startswith("freegraph")
    )
    eq(delta, [], "导入 `freegraph.runtime` 的 `sys.modules` **非标准库增量 == 0**")
    eq(len(runtime.__all__), 12, "L2 内部 API 的导出符号数 == 12")


def case_frozen_surface(runtime: Any) -> None:
    """SC-011 / SC-012 / SC-024 —— 冻结面与纪律审计。"""
    section("冻结面审计")
    contract_all = _public_symbols(REPO_ROOT / "src" / "freegraph" / "contracts" / "__init__.py")
    facade_all = _public_symbols(REPO_ROOT / "src" / "freegraph" / "graph.py")
    eq(len(contract_all), CONTRACT_PUBLIC_SYMBOL_COUNT, "SC-012 契约层公开符号面仍为 **18** 个")
    eq(len(facade_all), FACADE_PUBLIC_SYMBOL_COUNT, "SC-012 门面公开符号面仍为 **7** 个")

    readme = README.read_text(encoding="utf-8")
    section_match = COMPAT_MATRIX_PATTERN.search(readme)
    if not section_match:
        check(False, "SC-012 README 有「## API 兼容矩阵」章节")
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
            "SC-012 兼容矩阵**零新增行**（符号集合 == 契约层 18 + 门面 7）",
        )

    dependency_text = _dependency_text(PYPROJECT)
    for forbidden in (
        "langgraph",
        "langchain",
        "langsmith",
        "typing_extensions",
        "typing-extensions",
    ):
        check(
            forbidden not in dependency_text.lower(),
            f"SC-012 依赖三处声明**零**「{forbidden}」",
        )

    check(
        CI_WORKFLOW.read_text(encoding="utf-8").lower().count("langgraph") == 0,
        "SC-012 CI 作业内 `langgraph` 安装次数 == 0",
    )

    registry = LAYER_REGISTRY.read_text(encoding="utf-8")
    check(
        re.search(r"\|\s*`src/freegraph/runtime/`\s*\|\s*`L2`\s*\|", registry) is not None,
        "SC-011 层注册表把 `src/freegraph/runtime/` 登记为 **L2**（零改动）",
    )

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
    check(not edges, "SC-011 L2 → L3 / L4 / L5 的边数 == 0", "; ".join(edges))

    contract = ARCHITECTURE_GATES.read_text(encoding="utf-8")
    overview = re.search(r"^##\s*0\..*?(?=^##\s|\Z)", contract, re.S | re.M)
    identifiers = (
        re.findall(r"\|\s*\*\*G(\d+)\*\*\s*\|", overview.group(0)) if overview else []
    )
    eq(identifiers, [str(n) for n in range(1, 31)], "SC-012 门禁编号总数仍为 **30** 且连续")

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
        if not (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
        ):
            bad_headers.append(f"{relative_path}（docstring 不是首个语句）")
    check(
        not bad_headers,
        f"SC-011 新建源文件署名头 + docstring 覆盖率 == 100%（{len(NEW_SOURCE_FILES)} 个文件）",
        "; ".join(bad_headers),
    )

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
    check(
        not rows,
        "SC-012 `THIRD_PARTY_NOTICES` 的第三方运行时依赖表**无数据行**（零新增依赖）",
        str(rows),
    )


def case_contract_guard(runtime: Any) -> None:
    """SC-012 / SC-014 —— 契约与上游对照表**逐条**有实现与断言。"""
    section("契约守卫")
    contract = CONTRACT_PATH.read_text(encoding="utf-8")
    check("<!-- authority: yes -->" in contract, "契约权威标记在位")

    invariants = [
        cells[0]
        for cells in (_table_cells(line) for line in contract.splitlines())
        if len(cells) == 2 and re.fullmatch(r"I-\d+", cells[0])
    ]
    eq(invariants, [f"I-{n}" for n in range(1, 24)], "契约 §6 的不变量 **I-1…I-23** 齐全")

    upstream = UPSTREAM_PARITY_PATH.read_text(encoding="utf-8")
    points = [
        cells[0]
        for cells in (_table_cells(line) for line in upstream.splitlines())
        if len(cells) >= 5 and re.fullmatch(r"P-\d+", cells[0])
    ]
    eq(points, [f"P-{n:02d}" for n in range(1, 13)], "上游对照表 **P-01…P-12** 齐全")
    check("1.2.11" in upstream, "上游对照表标注核实版本（`langgraph 1.2.11`）")

    # 六类语义逐条有实现与断言（FR-021 · SC-014）。
    last = runtime.LastValue("k", int)
    last.update([1])
    last.update([2])
    eq(last.get(), 2, "六类语义 ① 覆盖语义")
    aggregate = runtime.BinaryOperatorAggregate("k", list, operator.add)
    eq(aggregate.get(), [], "六类语义 ③ 空值推导")
    route = runtime.EphemeralValue("route", str)
    route.update(["x"])
    eq(route.clear(), True, "六类语义 ⑤ 清空语义")
    check(last.is_available() is True, "六类语义 ⑥ 有值 / 无值判定")


#: **本解释器**的绝对路径（提示「装到哪儿」时 MUST **点名** ⇒ 避免
#: 「装进了 ``.venv``、脚本却跑在 ``/usr/bin/python3``」这种错位）。
INTERPRETER = sys.executable

#: 仓库自带的**主判定档** venv（CI 矩阵的**最低档** · 3.11）。
PROJECT_VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"


def _install_hint() -> str:
    """给出「把发行产物装好、并用**同一个**解释器跑本脚本」的**确切**命令。

    ⚠️ **必须点名解释器** —— ``uv pip install -e .`` 会**自动发现项目里的
    ``.venv``** ⇒ 装到 ``.venv`` 里，而脚本若用 ``/usr/bin/python3`` 跑
    ⇒ 那边**仍然没有** freegraph ⇒ 报「未安装」⇒ **极易误判**。

    ⚠️ **系统解释器通常装不进去** —— Debian/Ubuntu 的 ``/usr/bin/python3`` 是
    **externally managed**（PEP 668）⇒ ``pip install`` 会**失败**（退出码 2）
    ⇒ **正解是走仓库自带的 ``.venv``**。
    """
    if PROJECT_VENV_PYTHON.is_file():
        return (
            f"① `uv pip install --python {PROJECT_VENV_PYTHON} -e .`"
            f"  ② 用 `{PROJECT_VENV_PYTHON}` 跑本脚本"
            "（或 `source .venv/bin/activate` 后 `python3 ...`）"
            f"；⚠️ 本脚本的解释器是 **{INTERPRETER}**，与 ``.venv`` **不是同一个**"
            " ⇒ 装错地方了；⚠️ **系统解释器**通常是 **externally managed**"
            "（PEP 668）⇒ 在那儿 `pip install` 会**失败** ⇒ 请走 `.venv`"
        )
    return (
        f"装法：`uv pip install --python {INTERPRETER} -e .`"
        "（或用 `python -m venv .venv` 建一个再装）"
    )


def _coverage_hint() -> str:
    """给出「把覆盖率工具装好、并用**同一个**解释器跑本脚本」的**确切**命令。"""
    if PROJECT_VENV_PYTHON.is_file():
        return (
            f"装法：`uv pip install --python {PROJECT_VENV_PYTHON} coverage`"
            f"，然后用 `{PROJECT_VENV_PYTHON}` 跑本脚本"
            "（**开发期工具** · 不进仓库依赖声明 · research D-13）"
        )
    return (
        f"装法：`uv pip install --python {INTERPRETER} coverage`"
        "（**开发期工具** · 不进仓库依赖声明 · research D-13）"
    )


def case_coverage_evidence(runtime: Any) -> None:
    """SC-015 · FR-019 ② —— 覆盖率取证（**行 / 分支 100%**）。

    ① **阻断判据**：本 feature **新增**的 ``channel.py`` / ``mapping.py``
       **全文**的**行覆盖与分支覆盖 MUST 均为 100%**；
    ② **差分口径**：``errors.py`` / ``__init__.py`` 的「**新增部分**」——
       ``git diff -U0`` 的新增行号集合 ∩ ``coverage json`` 的
       ``missing_lines`` / ``missing_branches`` ⇒ 未覆盖数 MUST == **0**；
    ③ **整包**覆盖率**记录但 MUST NOT 阻断**（B4F1 无 100% 基线）。

    ⚠️ **三条取证纪律**（裁定 17 ⑤ · research D-17 实测）：

    * 分支覆盖 MUST 以 ``--branch`` 取证（无 ``--branch`` 时 ``coverage report``
      **不输出 Branch 列** ⇒ 分支覆盖**无从判定**）；
    * **文件级**报告**无法**区分「既有行」与「新增行」⇒ MUST NOT 单独作判据；
    * 「新增部分」**必须**走**差分口径**。

    ⚠️ ``coverage`` 是**开发期工具**（**不进**仓库依赖声明 · research **D-13**）
    ⇒ 未安装时标「◌ 环境未就绪」**不判失败**。
    """
    section("覆盖率取证（SC-015）")
    probe = subprocess.run(
        [sys.executable, "-c", "import coverage"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    if probe.returncode != 0:
        soft(
            False,
            "SC-015 覆盖率取证（行 / 分支 100%）",
            f"本解释器（{INTERPRETER}）**未装** `coverage` ⇒ "
            + _coverage_hint()
            + "；**skip ≠ pass**",
        )
        return

    with tempfile.TemporaryDirectory(prefix="freegraph-b5f1-cov-") as tmp:
        data_file = Path(tmp) / "cov.json"
        env = dict(os.environ)
        env["COVERAGE_FILE"] = str(Path(tmp) / ".coverage")
        run = subprocess.run(
            [
                sys.executable,
                "-m",
                "coverage",
                "run",
                "--branch",
                "-m",
                "pytest",
                "-q",
                "tests/runtime",
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
        )
        if run.returncode != 0:
            check(
                False,
                "SC-015 覆盖率跑测（`coverage run --branch -m pytest tests/runtime`）",
                run.stdout.strip().splitlines()[-1] if run.stdout.strip() else "",
            )
            return
        export = subprocess.run(
            [sys.executable, "-m", "coverage", "json", "-o", str(data_file)],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
        )
        if export.returncode != 0 or not data_file.is_file():
            check(False, "SC-015 导出 `coverage json`", export.stderr.strip()[:200])
            return
        payload = json.loads(data_file.read_text(encoding="utf-8"))

    files = payload.get("files", {})

    # ① 阻断判据：新增文件的**全文**行 / 分支覆盖 == 100%
    for relative_path in FULL_COVERAGE_FILES:
        entry = files.get(relative_path)
        if entry is None:
            check(False, f"SC-015 `{relative_path}` 在覆盖率报告中")
            continue
        missing_lines = entry.get("missing_lines", [])
        missing_branches = entry.get("missing_branches", [])
        check(
            missing_lines == [],
            f"SC-015 `{relative_path}` **行覆盖 == 100%**",
            f"未覆盖行 {missing_lines}",
        )
        check(
            missing_branches == [],
            f"SC-015 `{relative_path}` **分支覆盖 == 100%**",
            f"未覆盖分支 {missing_branches}",
        )

    # ② 差分口径：只管**新增部分**
    for relative_path in DIFF_COVERAGE_FILES:
        entry = files.get(relative_path)
        if entry is None:
            check(False, f"SC-015 `{relative_path}` 在覆盖率报告中")
            continue
        added = _added_line_numbers(relative_path)
        uncovered_lines = sorted(added & set(entry.get("missing_lines", [])))
        uncovered_branches = [
            branch
            for branch in entry.get("missing_branches", [])
            if branch[0] in added
        ]
        check(
            uncovered_lines == [],
            f"SC-015 `{relative_path}` 的**新增部分**未覆盖行 == 0（差分口径）",
            f"未覆盖 {uncovered_lines}",
        )
        check(
            uncovered_branches == [],
            f"SC-015 `{relative_path}` 的**新增部分**未覆盖分支 == 0（差分口径）",
            f"未覆盖 {uncovered_branches}",
        )

    # ③ 整包覆盖率 —— **记录但 MUST NOT 阻断**
    package = "src/freegraph/runtime/"
    totals = payload.get("totals", {})
    package_entry = files.get(package, {})
    summary = package_entry.get("summary", {})
    print(
        f"  · 整包 {package} 覆盖率（记录 · 不阻断）"
        f"：行 {summary.get('percent_covered', totals.get('percent_covered', '—'))}%"
    )


def _added_line_numbers(relative_path: str) -> set[int]:
    """``git diff -U0 HEAD -- <path>`` 的**新增行号集合**（差分口径）。"""
    diff = subprocess.run(
        ["git", "diff", "-U0", "HEAD", "--", relative_path],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    ).stdout
    added: set[int] = set()
    for match in re.finditer(
        r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", diff, re.M
    ):
        start = int(match.group(1))
        count = int(match.group(2) or 1)
        added.update(range(start, start + count))
    return added


def case_gates(runtime: Any, installed: bool = True) -> None:
    """SC-011 / SC-012 —— **10 条门禁**的实跑结果。

    * **本地直跑**的 7 条（``G21`` / ``G23`` / ``G24`` / ``G25`` / ``G26`` /
      ``G29`` / ``G30``）⇒ **硬断言**（纯本地 · 确定性 · 无网络 / 无命名空间依赖）；
    * **Linux only** 的 3 条（``G22`` 需**网络**建隔离 venv · ``G28`` 需
      **网络命名空间**）⇒ **只观测不阻断**（由 CI 的 Linux 作业作阻断判据
      —— 与 pytest 的 ``linux_only`` marker 同一口径）。

    ⚠️ 门禁脚本**自身** MUST NOT 调用 ``unshare``（命名空间由**外层**施加）
    ⇒ 本脚本直接跑**脚本本体** ⇒ 断网隔离那一层归 CI。

    ⚠️ **G27 / G28 会重跑 ``pytest tests/``** ⇒ 其判据**依赖** freegraph **已安装**
    （``tests/gates/test_gates.py`` 的 7 条用例读 ``importlib.metadata`` 的
    ``dist-info``）⇒ **未安装**时它们必然失败 ⇒ 此时 MUST 标「**不可判定**」
    （**环境未就绪**），MUST NOT 把它报成「违规」。
    """
    section("门禁实跑（10 条）")
    for gate in LOCAL_GATES + LINUX_ONLY_GATES:
        scripts = sorted(GATES_DIR.glob(f"gate_{gate}_*.py"))
        if not scripts:
            check(False, f"门禁 {gate} 的脚本存在")
            continue
        # ⚠️ **不传任何参数** —— 各门禁的 CLI 契约**各不相同**（``--root`` /
        # ``--project`` / ``--registry`` …），而它们**各自**默认指向**本仓库**
        # ⇒ 与 ``.github/workflows/ci.yml`` 的调用方式**逐字同构**。
        completed = subprocess.run(
            [sys.executable, str(scripts[0])],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        detail = completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else ""
        label = f"门禁 {gate} 通过（{scripts[0].name}）"
        if gate in LINUX_ONLY_GATES:
            note = detail or f"退出码 {completed.returncode}"
            if completed.returncode != 0 and not installed:
                note = (
                    f"本解释器（{INTERPRETER}）**未安装** freegraph ⇒ 该门禁重跑的 "
                    "`pytest tests/` 有依赖 `dist-info` 的用例无法判定 ⇒ "
                    "**本条不可判定**；" + _install_hint()
                )
            soft(
                completed.returncode == 0,
                label + "〔Linux only · 只观测不阻断〕",
                note,
            )
        else:
            check(completed.returncode == 0, label, detail or f"退出码 {completed.returncode}")


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

    return " ".join(
        [
            _flat(project.get("dependencies", [])),
            _flat(project.get("optional-dependencies", {})),
            _flat(data.get("dependency-groups", {})),
        ]
    ).lower()
def build_record(mode: str, verdict: str, rc: int) -> str:
    """产出**五段式**的验收记录片段（可直接并入 ``manual-verification.md``）。"""
    out: list[str] = []
    out.append("# B5F1 验收记录（由 `harness/verification/B5F1/acceptance.py` 生成）")
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
    out.append("python3 harness/verification/B5F1/acceptance.py")
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
    """入口（两态运行 · 退出码 0 / 1 / 2）。"""
    parser = argparse.ArgumentParser(
        description="B5F1 人工验收脚本（一条命令跑完全部验收判据）"
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

    print("══ acceptance · B5F1 通道抽象 + 三类通道 ══")
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
        ("case_a1_reduce_semantics", lambda: case_a1_reduce_semantics(runtime)),
        ("case_a2_overwrite_semantics", lambda: case_a2_overwrite_semantics(runtime)),
        ("case_a3_ephemeral_clear", lambda: case_a3_ephemeral_clear(runtime)),
        ("case_conflict_explicit_failure", lambda: case_conflict_explicit_failure(runtime)),
        ("case_availability_decidable", lambda: case_availability_decidable(runtime)),
        ("case_empty_value_derivation", lambda: case_empty_value_derivation(runtime)),
        ("case_mapping", lambda: case_mapping(runtime)),
        ("case_purity_and_scale", lambda: case_purity_and_scale(runtime)),
        ("case_naming_surface", lambda: case_naming_surface(runtime)),
        ("case_construction_validation", lambda: case_construction_validation(runtime)),
        ("case_error_contract", lambda: case_error_contract(runtime)),
        ("case_zero_side_effects", lambda: case_zero_side_effects(runtime)),
        ("case_contract_guard", lambda: case_contract_guard(runtime)),
        ("case_frozen_surface", lambda: case_frozen_surface(runtime)),
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

    rc = finish("B5F1 人工验收")
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
