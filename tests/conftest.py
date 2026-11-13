# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""测试套件的**根** conftest —— 提供一条 **CI 诊断通道** + 一条**时钟精度**通道。

**为什么需要（诊断通道）**：pytest 的失败详情只出现在**步骤日志**里，而 GitHub 的
「下载作业日志」接口**需要 admin 权限** ⇒ 失败时**外部**（CI 看板 / 告警 /
REST API 的消费者）**定位不到具体用例**。

⇒ 本钩子把每条失败 / 错误**再输出一次**为 **GitHub Actions 的注解**
（`::error title=…::…` 工作流命令）⇒ GitHub 把它渲染成 **annotation**
⇒ 可经 REST API 的 `check-runs` **直接读到**（**无需日志、无需令牌**）。

**不改变任何判据**：本文件**只**多打印一行工作流命令；断言与门禁逻辑**一字未动**。

**时钟精度通道**（见 :func:`_fine_grained_monotonic_clock`）—— **只修「测量」**，
**不动任何断言** ⇒ ⇒ **冻结断言文件零改动**。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import sys
import time
from typing import Any

import pytest

#: 注解里允许的**标题**（GitHub 的 `::error title=…::` 语法）。
_ANNOTATION_TITLE = "pytest failure"

#: 单条注解的最大长度（GitHub 截断很长的注解 ⇒ 保留可诊断的前缀即可）。
_MAX_MESSAGE = 900


@pytest.fixture(scope="session", autouse=True)
def _fine_grained_monotonic_clock() -> Any:
    """**Windows + CPython < 3.13**：把 ``time.monotonic`` 换成**高精度**口径。

    ⚠️ **为什么需要**（**只修「测量」· 不动任何断言**）：

    * ``time.monotonic()`` 在 **Windows + CPython < 3.13** 上走 ``GetTickCount64()``
      ⇒ 粒度 ≈ **15.6ms**；**CPython 3.13 起**改用 ``QueryPerformanceCounter()``
      ⇒ 粒度 ≈ **1µs**（**官方** What's New in 3.13 · ``time`` 段 · gh-88494）
      ⇒ ⇒ **同一份代码在 3.11 档与 3.14 档的**可测量性**不同**；
    * 「**两个节点的执行时间窗重叠**」（``tests/runtime/test_superstep_concurrency.py``）
      是一条**亚毫秒**的**时序测量**断言 ⇒ ⇒ 在 15.6ms 的刻度下会被**量化到同一
      tick** ⇒ ⇒ 算出 ``overlap == 0`` ⇒ ⇒ **假红**（语义上两个节点**确实**并行
      —— 屏障**确实**被放行）；
    * ⇒ 本夹具在 Windows 上把 ``time.monotonic`` 换成 ``time.perf_counter``
      （**后者在 Windows 上恒为 QPC**）⇒ ⇒ **与 CPython 3.13+ 的口径一致**
      ⇒ ⇒ **只修「测量」· 不动任何断言** ⇒ ⇒ **冻结断言文件零改动**
      （B7F1 / B9F1 / B12F1 的 **10 个**文件）。

    ⚠️ **零风险**：``time.monotonic`` 在本仓**只**被**测试代码**用于**测量**
    （``src/freegraph/**`` **零使用**）⇒ ⇒ **产品行为不受影响**。
    ⚠️ **其余平台 / CPython ≥ 3.13** ⇒ **本夹具是 no-op**（逐字不动时钟）。
    """
    if sys.platform != "win32" or sys.version_info >= (3, 13):
        yield
        return
    original = time.monotonic
    time.monotonic = time.perf_counter  # type: ignore[assignment]
    try:
        yield
    finally:
        time.monotonic = original  # type: ignore[assignment]


def _first_line(text: str) -> str:
    """取**第一行非空**文本（traceback 的首行通常是断言表达式）。"""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def pytest_terminal_summary(
    terminalreporter: Any, exitstatus: int, config: Any
) -> None:
    """把失败 / 错误逐条输出为 **GitHub 注解**（诊断通道）。"""
    reports = list(terminalreporter.getreports("failed"))
    reports += list(terminalreporter.getreports("error"))
    for report in reports:
        longrepr = report.longrepr
        detail = _first_line(str(longrepr)) if longrepr else ""
        message = f"{report.nodeid} — {detail}" if detail else report.nodeid
        message = message.replace("\r", " ").replace("\n", " ")[:_MAX_MESSAGE]
        # 工作流命令：**必须**独占一行且以「::error」开头。
        terminalreporter.write_line(
            f"::error title={_ANNOTATION_TITLE}::{message}"
        )
