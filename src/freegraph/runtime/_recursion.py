# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""L2 执行内核层 · **递归上限**（``recursion_limit``）

**契约权威**：``specs/b13f1-static-interrupt-recursion-limit/contracts/
recursion-limit-contract.md``。

* 规范载体 = 普通 dict / ``RunConfig``（互斥二选一）；
* 默认值 = **10007**（硬编码 · 零环境变量）；
* 非 ``None`` 值 MUST 是 ``int`` 且不是 ``bool``，且 ``>= 1``；
* ``None`` 视为「未提供」⇒ 跳过校验，落回 ``max_steps``。

**本模块私有** ⇒ 不进 ``freegraph.runtime.__all__``。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from freegraph.contracts.types import RunConfig

__all__: list[str] = []

#: 上游 1.2.11 的有效缺省（``langgraph/_internal/_config.py:32``）；
#: freegraph **硬编码**，不读任何环境变量。
DEFAULT_RECURSION_LIMIT = 10007


def resolve_config(config: RunConfig | Mapping[str, Any] | None) -> RunConfig:
    """把 ``run_graph`` 的 ``config`` 归一为 ``RunConfig``。

    * ``None`` ⇒ 新建空配置；
    * ``RunConfig`` ⇒ 原样返回；
    * ``Mapping`` ⇒ ``RunConfig.from_dict(..., ignore_unknown=True)``
      （未知键属于其它运行期参数，宽容忽略；``thread_id`` 等既有字段保留）；
    * 其它 ⇒ ``TypeError``。
    """
    if config is None:
        return RunConfig()
    if isinstance(config, RunConfig):
        return config
    if isinstance(config, Mapping):
        return RunConfig.from_dict(config, ignore_unknown=True)
    raise TypeError(
        f"config must be a RunConfig, mapping, or None, "
        f"got {type(config).__name__}"
    )


def validate_limit(value: Any) -> int:
    """校验**非 ``None``** 的 ``recursion_limit``。

    ``bool`` 是 ``int`` 的子类 ⇒ 用 ``type(value) is not int`` 明确拒绝；
    浮点 / 字符串 / 其它类型 ⇒ ``TypeError``；``< 1`` ⇒ ``ValueError``。
    """
    if type(value) is not int:  # noqa: E721 - bool 必须被拒绝
        raise TypeError(
            f"recursion_limit must be an int, got {type(value).__name__}"
        )
    if value < 1:
        raise ValueError(f"recursion_limit must be at least 1, got {value!r}")
    return value


def resolve_limit(
    config_limit: int | None,
    max_steps: int = DEFAULT_RECURSION_LIMIT,
) -> int:
    """解析**有效上限**。

    优先级：``dict`` / ``RunConfig`` 的 ``recursion_limit``（二选一） >
    既有 ``max_steps`` > 默认 10007。

    ⚠️ ``config_limit is None`` = 未提供 ⇒ **不进入** :func:`validate_limit`
    ⇒ 直接落回 ``max_steps``（``None`` 不抛 ``TypeError``）。
    """
    if config_limit is not None:
        return validate_limit(config_limit)
    return max_steps
