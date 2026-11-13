# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**L2 内部 API 的导出面清单**（``freegraph.runtime.__all__``）—— **B10F1**。

**为什么有这份清单**（宪法 v1.8.0「破冻结面的三条」第 ① 条 · **拆分而不删**）：

* ``freegraph.runtime.__all__`` 的**符号面**是**冻结面** ⇒ ⇒ 本 feature
  （B10F1）**增**了 3 个符号（``InterruptError`` / ``InterruptResult`` /
  ``run_graph`）⇒ ⇒ **既有**的冻结断言（**硬编码数字 20**）**必红**
  ⇒ ⇒ MUST **回溯修订**；
* ⚠️ **判据零放宽** —— 原判据是「**符号面 == 某份清单**」⇒ ⇒ 修订后**仍是**
  「**符号面 == 某份清单**」⇒ ⇒ 只把「**硬编码数字**」换成「**清单**」
  ⇒ ⇒ **不是**「≥ 20」；
* ⚠️ **单一事实源** —— 三处既有断言（``test_command_purity`` /
  ``test_read_contract`` / ``test_superstep_concurrency`` /
  ``test_superstep_purity``）**共用**本清单 ⇒ ⇒ **不**在三处各抄一份
  ⇒ ⇒ **不**会漂移。

**清单的权威**：``specs/b10f1-interrupt-resume/contracts/interrupt-resume-contract.md``
§1（``freegraph.runtime.__all__``：20 → 23）⇒ ⇒ 本模块是该契约的**可执行镜像**。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

#: ``freegraph.runtime.__all__`` 的**完整清单**（**集合** · **不硬编码数字**）。
#:
#: ⚠️ **L2 内部 API** ⇒ **不进** API 兼容矩阵（B4F1 裁定 6 ③）⇒ ⇒
#: **不**受门禁 G8 / G19 的「门面 7 符号」约束。
RUNTIME_EXPORT_SYMBOLS: frozenset[str] = frozenset(
    {
        "BinaryOperatorAggregate",
        "Channel",
        "ChannelSpec",
        "EmptyChannelError",
        "EphemeralValue",
        "GraphSpec",
        "InterruptError",
        "InterruptResult",
        "InvalidChannelUpdateError",
        "InvalidSchemaError",
        "LastValue",
        "NodeSpec",
        "SchedulerState",
        "SchemaSpec",
        "SuperStepResult",
        "build_channel",
        "build_channels",
        "local_read",
        "parse_state_schema",
        "read_channels",
        "run_graph",
        "run_super_step",
        "run_super_steps",
    }
)

#: ``freegraph.runtime.superstep.__all__`` 的**完整清单**（**集合**）。
#:
#: ⚠️ **与** :data:`RUNTIME_EXPORT_SYMBOLS` **不同** —— 前者是**包**的导出面
#: （``freegraph.runtime.__all__``）· 后者是**模块**的导出面
#: （``freegraph.runtime.superstep.__all__``）⇒ ⇒ **两处**都要断言
#: （**既有**的两条冻结断言守的正是这两个面）。
SUPERSTEP_EXPORT_SYMBOLS: frozenset[str] = frozenset(
    {
        "GraphSpec",
        "InterruptError",
        "InterruptResult",
        "NodeSpec",
        "SchedulerState",
        "SuperStepResult",
        "run_graph",
        "run_super_step",
        "run_super_steps",
    }
)

#: ``freegraph.runtime.errors.__all__`` 的**完整清单**（**集合**）。
#:
#: ⚠️ **B10F1 增**了 ``InterruptError``（**必须**写进 ``errors.__all__``
#: ⇒ 7 → 8）⇒ ⇒ 期望集合 = **7 + InterruptError**。
ERROR_EXPORT_SYMBOLS: frozenset[str] = frozenset(
    {
        "EmptyChannelError",
        "InterruptError",
        "InvalidChannelUpdateError",
        "InvalidSchemaError",
        "REASON_ANNOTATION_UNRESOLVABLE",
        "REASON_NOT_A_STATE_SCHEMA",
        "REASON_REDUCER_NOT_BINARY",
        "SCHEMA_ERROR_REASONS",
    }
)

#: ``freegraph.runtime.errors`` 里 **``FreegraphError`` 的子类**（**集合**）。
#:
#: ⚠️ **B10F1 增**了 ``InterruptError``（**必须**是 ``FreegraphError`` 的子类
#: ⇒ ⇒ L1 的「捕获基类即可兜住全部内核错误」的冻结承诺**不被破坏**）。
ERROR_CLASS_NAMES: frozenset[str] = frozenset(
    {
        "EmptyChannelError",
        "InterruptError",
        "InvalidChannelUpdateError",
        "InvalidSchemaError",
    }
)
