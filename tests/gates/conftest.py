# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""门禁测试的**共享夹具** —— 路径基线 + socket 监测 + 隔离副本。

三组能力：

1. **路径基线**（``repo_root`` / ``src_dir`` / ``gates_dir`` / ``spec_dir``）
   —— 沿用 `tests/contracts/conftest.py` 的路径基线口径；
2. **隔离副本**（``isolated_copy``）—— 负向验证的**被检树副本**；
   **MUST 复用** `harness/scripts/gates/_gatekit.py` 的 `make_isolated_copy()`
   ⇒ MUST NOT 在夹具里另写一份拷贝逻辑（否则与门禁脚本的
   ``--self-test-negative`` 漂移 ⇒ 一处拷 ``README.md`` / ``LICENSE``、
   一处不拷 ⇒ 门禁在**构建阶段**而非**断言阶段**失败）；
3. **socket 监测**（``egress_recorder``）—— **只包装**
   ``socket.connect`` / ``socket.create_connection``，**记录**目标与调用栈、
   **放行**全部连接（FR-009 ② · 裁定 7）；
   **MUST 复用** `_gatekit` 里的**同一实现**（归因 + 同一 socket 包装）
   ⇒ MUST NOT 在夹具里另写一份（「两个入口 · 同一实现」· G27）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
GATES_DIR = REPO_ROOT / "harness" / "scripts" / "gates"
SPEC_DIR = REPO_ROOT / "specs" / "b3f1-scaffold-ci-gates"
EXCLUSIONS_PATH = Path(__file__).resolve().parent / "data" / "offline_exclusions.txt"

# 把门禁的共享判定库插入 ``sys.path`` ⇒ 测试可直接 ``import _gatekit``。
if str(GATES_DIR) not in sys.path:
    sys.path.insert(0, str(GATES_DIR))

import _gatekit  # noqa: E402 —— 必须在 sys.path 调整之后导入


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """仓库根目录（被检树 / 层注册表 / 人工验证记录的定位基准）。"""
    return REPO_ROOT


@pytest.fixture(scope="session")
def src_dir() -> Path:
    """``<repo>/src``（源码树根）。"""
    return SRC_DIR


@pytest.fixture(scope="session")
def gates_dir() -> Path:
    """``<repo>/harness/scripts/gates``（十条门禁的落点）。"""
    return GATES_DIR


@pytest.fixture(scope="session")
def spec_dir() -> Path:
    """``<repo>/specs/b3f1-scaffold-ci-gates``（本 feature 的规格目录）。"""
    return SPEC_DIR


@pytest.fixture(scope="session")
def exclusions_path() -> Path:
    """断网排除清单（``tests/gates/data/offline_exclusions.txt``）。"""
    return EXCLUSIONS_PATH


@pytest.fixture()
def isolated_copy(tmp_path: Path) -> Path:
    """负向验证的**被检树隔离副本**（可构建 · 含 README.md / LICENSE）。

    **MUST 复用** `_gatekit.make_isolated_copy()`（T008）⇒ 本夹具**不**含
    任何拷贝逻辑。
    """
    return _gatekit.make_isolated_copy(REPO_ROOT, dest=tmp_path)


@pytest.fixture()
def egress_recorder() -> list[_gatekit.EgressRecord]:
    """socket 监测（**只观测不阻断**）—— 产出本次用例的**出站记录**清单。

    **MUST 复用** `_gatekit.record_egress()`（T013 的归因 + 同一 socket 包装）
    ⇒ 与 G27 的独立入口**同一实现**。
    """
    records: list[_gatekit.EgressRecord] = []
    with _gatekit.record_egress(records):
        yield records
