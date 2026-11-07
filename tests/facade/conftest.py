# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""pytest 共享夹具 —— 门面测试的**路径基线**与**快照更新开关**。

沿用 `tests/contracts/conftest.py` 的既有口径：

* ``FREEGRAPH_TEST_INSTALLED=1`` ⇒ **跳过** ``sys.path`` 注入
  （供 B3F1 的 CI「先 ``pip install .`` 再跑 pytest」用）；
* 否则把 ``<repo>/src`` 插入 ``sys.path`` 的**最前**位置——源码优先，
  避免测到已安装的旧版本。

另注册 ``--update-api-snapshot`` 开关（spec FR-011 ① · research D-09）：

* **默认关闭**——常规跑 pytest **绝不**改动快照文件；
* 显式带上该开关时才重新生成快照，生成物 **MUST** 经**人工 review diff**
  后方可提交（``contracts/snapshot-format.md`` §4 / §6）。

> **为何开关注册在本文件**：`pytest_addoption` 只对**初始 conftest** 生效
> ——pytest 在**启动期**加载命令行参数所指目录的 conftest，此时解析器仍可扩展。
> 故用法必须是 `pytest tests/facade/... --update-api-snapshot`
> （见 `quickstart.md` §4.2）。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
SPEC_DIR = REPO_ROOT / "specs" / "b2f2-public-api-facade"
CONTRACTS_DIR = SPEC_DIR / "contracts"

#: 门面导出面清单（**手写**权威）——门禁 G15 / G19 的期望值来源。
FACADE_MANIFEST = CONTRACTS_DIR / "facade-api.md"

#: API 签名快照（**机器生成** · 入库比对点）。
SNAPSHOT_PATH = CONTRACTS_DIR / "public-api-snapshot.txt"

#: 快照格式契约（条目语法 · 注解规范化 N-1…N-6 · 文本层规则 T-1…T-8）。
SNAPSHOT_FORMAT = CONTRACTS_DIR / "snapshot-format.md"

#: ``--update-api-snapshot`` 开关的**缺省值**——**False**（默认关闭）。
#:
#: spec FR-011 ①：常规执行 pytest MUST NOT 改动快照文件。
UPDATE_OPTION_DEFAULT = False


def _inject_src() -> None:
    """把 ``<repo>/src`` 插入 ``sys.path`` 最前（源码优先）。"""
    if os.environ.get("FREEGRAPH_TEST_INSTALLED") == "1":
        return
    src = str(SRC_DIR)
    if src not in sys.path:
        sys.path.insert(0, src)


_inject_src()


def pytest_addoption(parser: pytest.Parser) -> None:
    """注册 ``--update-api-snapshot``（**默认关闭**）。

    **默认关闭**是 spec FR-011 ① 的硬要求：常规执行 pytest MUST NOT
    改动快照文件——否则「签名漂移在测试里显式可见」这条承诺即被自身的
    「自动更新」抹掉。
    """
    parser.addoption(
        "--update-api-snapshot",
        action="store_true",
        default=UPDATE_OPTION_DEFAULT,
        help=(
            "重新生成并写入 API 签名快照（默认关闭）；"
            "生成物 MUST 经人工 review diff 后方可提交"
        ),
    )


def pytest_configure(config: pytest.Config) -> None:
    """登记本目录自有的 marker（避免 pytest 的未知 marker 告警）。"""
    config.addinivalue_line(
        "markers",
        "update_snapshot: 需显式 --update-api-snapshot 才生效的快照更新用例",
    )


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """仓库根目录（README.md / 快照文件 / 契约文件的定位基准）。"""
    return REPO_ROOT


@pytest.fixture(scope="session")
def src_dir() -> Path:
    """``<repo>/src``（源码树根，子进程 ``PYTHONPATH`` 的注入目标）。"""
    return SRC_DIR


@pytest.fixture(scope="session")
def spec_dir() -> Path:
    """``<repo>/specs/b2f2-public-api-facade``（本 feature 的规格目录）。"""
    return SPEC_DIR
