# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""测试套件的**根** conftest —— 提供一条 **CI 诊断通道**。

**为什么需要**：pytest 的失败详情只出现在**步骤日志**里，而 GitHub 的
「下载作业日志」接口**需要 admin 权限** ⇒ 失败时**外部**（CI 看板 / 告警 /
REST API 的消费者）**定位不到具体用例**。

⇒ 本钩子把每条失败 / 错误**再输出一次**为 **GitHub Actions 的注解**
（`::error title=…::…` 工作流命令）⇒ GitHub 把它渲染成 **annotation**
⇒ 可经 REST API 的 `check-runs` **直接读到**（**无需日志、无需令牌**）。

**不改变任何判据**：本文件**只**多打印一行工作流命令；断言与门禁逻辑**一字未动**。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

from typing import Any

#: 注解里允许的**标题**（GitHub 的 `::error title=…::` 语法）。
_ANNOTATION_TITLE = "pytest failure"

#: 单条注解的最大长度（GitHub 截断很长的注解 ⇒ 保留可诊断的前缀即可）。
_MAX_MESSAGE = 900


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
