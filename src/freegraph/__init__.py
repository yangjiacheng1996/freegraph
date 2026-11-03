"""freegraph — 图运行内核（Graph Runtime Kernel）。

**v0.0.1 是「占位版」（name-reservation placeholder）**：本次发布只为在 PyPI 上
锁定 ``freegraph`` 这个发行名（发行名 = 导入名），内核功能尚未实现。

三条对外承诺（见仓库内《立项书》）：

* **零账号** —— 无需 LangSmith 账号、API key 或 license key；
* **零出站** —— freegraph 自身不主动发起任何出站连接，且不阻断用户代码出网；
* **零第三方运行时依赖** —— 基础安装只有 ``typing-extensions``。

实现进度见 ``harness/proposals/立项书.md``（32 个 Phase / 96 人日 / v1.0）。
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.0.1"
