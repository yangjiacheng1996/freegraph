# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""契约层**独立回归测试**的**挂载点**（**C4** / **C8**）—— B3F1 只落挂载点。

宪法「质量门禁第 3 项」要求：契约门禁 **MUST 包含 C4（稀疏状态读）与 C8
（条件边 fresh 状态读）两条独立回归测试**。

**⚠️ 本 feature 物理不可达成**（宪法 v1.6.0「质量门禁的分阶段落地与发起者追认」）：

* C4 / C8 都**依赖内核运行时**（内核运行时按 立项书 §6.2 属 **M2**）；
* 本 feature 是 **M0 地基** feature、**不交付内核功能**
  （``StateGraph`` 的方法一律 ``raise NotImplementedError``）；
* ⇒ **只落挂载点**，并**明确标记为「未落地」** —— **MUST NOT 伪装成「已通过」**
  （spec FR-011 ②）；
* ⇒ 该宪法缺口**登记为偏离** ⇒ 由 **B3F1 的发起者追认**（`tasks.md` **T057**，
  阻断合入）；承接方 = **B5F2**（C4 · M1）/ **B8F1**（C8 · M2）。

**机器可读标记**（门禁 **G29** ③ 逐条解析）::

    # GATE-MOUNT: <编号> · status=<not-landed|landed> · owner=<承接方> · milestone=<里程碑> · desc=<说明>

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import pytest

# GATE-MOUNT: C4 · status=not-landed · owner=B5F2 · milestone=M1 · desc=稀疏状态读
# GATE-MOUNT: C8 · status=not-landed · owner=B8F1 · milestone=M2 · desc=条件边 fresh 状态读

#: 两条回归测试的编号（与宪法质量门禁第 3 项一致）。
CONTRACT_REGRESSIONS = ("C4", "C8")


@pytest.mark.skip(reason="未落地 —— C4（稀疏状态读）由 B5F2（M1）建立")
def test_c4_sparse_state_read() -> None:
    """**C4** · 稀疏状态读 —— 节点输入**不含**未被写入的 key。

    目标形态：``"llm_calls" not in node_input`` 且
    ``node_input.get("llm_calls", 0) == 0``。
    """
    raise NotImplementedError("C4 尚未落地 —— 由 B5F2（M1）建立")


@pytest.mark.skip(reason="未落地 —— C8（条件边 fresh 状态读）由 B8F1（M2）建立")
def test_c8_conditional_edge_fresh_state_read() -> None:
    """**C8** · 条件边 fresh 状态读 —— 路由函数看到本节点**刚写入**的值。

    目标形态：条件边的路由函数读到的状态包含上游节点本轮刚写入的 key。
    """
    raise NotImplementedError("C8 尚未落地 —— 由 B8F1（M2）建立")
