# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**差分测试夹具**（测试侧）—— 属 **B5F2**。

**契约权威**：``specs/b5f2-sparse-state-read/contracts/differential-fixture.md``
（``<!-- authority: yes -->``）。

本包 MUST **NOT** 进入 ``src/freegraph/**``（spec 裁定 6 · FR-024）⇒ 内核的
零依赖面**不受影响**；``pyproject.toml`` 的 sdist ``exclude`` 已含 ``/tests``
⇒ 夹具**不进发行包**。

**四个模块**：

* :mod:`tests.differential.spec_builder` —— 图规格的**前置校验** + **动态构造
  ``TypedDict``**（**一个** · 两侧消费**同一个对象**）；
* :mod:`tests.differential.driver` —— freegraph 侧的**规格驱动器**（**无调度
  逻辑** · 只用 B5F1 通道层 + B5F2 读取层）；
* :mod:`tests.differential.runner` —— 两侧执行 + **三项投影**归一化 + 逐字段判定；
* :mod:`tests.differential.test_differential` —— 差分用例（``langgraph`` **缺席
  ⇒ skip**）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""
