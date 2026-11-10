# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""差分夹具的**共享夹具** —— 属 **B5F2**（tasks T008）。

**缺席即 skip**（FR-019 · 裁定 11）：``langgraph`` **未安装**时，差分用例被
**标记跳过**（**不是失败**）⇒ 基础安装 / 隔离环境 / 未装 ``differential`` 组
的开发者环境**不会**因差分夹具变红。

⚠️ **导入 MUST 在夹具函数体内**（延迟到用例实际运行时才 import）· MUST
**NOT** 置于 conftest **模块级** —— 否则上游及其传递依赖（``langchain-core``
→ ``langsmith``）会被导入**共享 pytest 进程** ⇒ 污染同进程的 ``sys.modules``
观测（仓库既有教训：``tests/contracts/test_architecture.py:29``「同进程
``sys.modules`` 不可作依据」）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import importlib.metadata

import pytest


@pytest.fixture(scope="session")
def upstream_version() -> str:
    """上游 ``langgraph`` 的**已安装版本**（**缺席 ⇒ skip**）。

    ⚠️ 导入 MUST 在**本函数体内**（MUST NOT 置于模块级 · 见模块 docstring）。
    ⇒ 版本取自**发行元数据**（``langgraph.__version__`` 并非上游的公开属性）。
    """
    pytest.importorskip("langgraph")
    return importlib.metadata.version("langgraph")
