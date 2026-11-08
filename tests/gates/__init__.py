# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""B3F1 的**门禁测试包**（G21–G30 的正向断言 + 反向用例）。

本包**自带** ``__init__.py`` ⇒ 目录名 ``tests.gates`` 成为一个**包** ⇒ pytest 收集到的
模块名带**包前缀**（``tests.gates.test_gates``）⇒ **不会**触发 pytest 的
``import file mismatch``（本仓库的 ``tests/contracts/`` 与 ``tests/facade/`` 各有一个
同族的 ``test_*.py`` 文件）。

命名上与既有的 ``tests/facade/_gatesupport.py`` **刻意错开**（共享判定库叫
``harness/scripts/gates/_gatekit.py``）⇒ 避免「两份不同内容的 ``_gatesupport``」
共存导致人与 AI 代理误 import（plan.md「Structure Decision」）。
"""

__all__: list[str] = []
