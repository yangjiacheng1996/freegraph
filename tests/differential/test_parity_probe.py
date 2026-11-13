# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""**差分探针**的 pytest 包装 —— 让「与上游同款」成为**CI 里真跑**的判据。

为什么需要它
------------
仓库此前只有 **B5F2 一家**的差分用例（``tests/differential/test_differential.py``
· 线性单链 + 三个投影）⇒ 后续 feature（B4F1 / B5F2 / B9F1）若与上游分叉，
**没有任何自动化装置会发现** ⇒ 三处分叉都是在人工回改（P3）**之前**长期保持绿色的。

⇒ 本文件把「**同场景 · 上游 ↔ freegraph 对跑**」的**场景集**（``parity_probe.py``）
接进 pytest ⇒ ⇒ **CI 的 Linux 全量档装了上游差分组 ⇒ 这里真跑**（其它档 skip ·
**非失败** · 沿用 B5F2 的「缺席即 skip」纪律）。

**与 B5F2 既有差分装置的关系**：
* **不改动** B5F2 的 ``spec_builder`` / ``runner``（**冻结面零改动**）⇒
  本文件是**并列**的**第二个**差分场景集；
* **判据只有一处** ⇒ 场景与判定逻辑都在 ``parity_probe.py`` ⇒
  ``harness/scripts/diff_parity.py``（人工跑）与本文件（CI 跑）**同源**。

**未注册 marker** ⇒ 沿用 B5F2 的纪律：**靠 fixture 的「缺席即 skip」**判定
（``pytestmark`` 不设 marker ⇒ 无 ``PytestUnknownMarkWarning``）⇒ CI 的非 Linux
全量档自动 skip（**非失败**）。

**判词三态**（见 ``parity_probe.Scenario.verdict``）：
* ``SAME`` —— 必须逐字一致（不一致 ⇒ 判据失败 ⇒ 测试红）；
* ``STRICTER`` —— freegraph **刻意更严**（允许「上游成功、freegraph 失败」），
  但**绝不允许**「上游失败、freegraph 成功」（那是**漏网**）；
* ``DIFF`` —— **已知且已登记**的结构差异（必须带理由 ⇒ 理由缺失即判据失败）。
"""
from __future__ import annotations

import pytest

from . import parity_probe


@pytest.fixture(scope="module")
def upstream_version() -> str:
    """上游 ``langgraph`` 的**已安装版本**（**缺席 ⇒ skip**）。

    ⚠️ 沿用 B5F2 的「缺席即 skip」纪律（``conftest.py``）：上游缺席 ⇒ **skip**
    （**不是失败**）⇒ CI 的非 Linux 全量档不受影响。
    """
    pytest.importorskip("langgraph")
    import importlib.metadata

    return importlib.metadata.version("langgraph")


def test_every_parity_scenario_meets_its_verdict(upstream_version: str) -> None:
    """**全部差分场景 MUST 符合各自判词** —— 一条红即判据失败。

    ⇒ 这条用例就是「**地基与上游同款**」的**常驻门禁**：
    任何 feature 让地基与上游分叉 ⇒ 这里**立刻红**（不再依赖人工回改轮次发现）。
    """
    results = parity_probe.run_all()

    assert results, "差分场景集为空 ⇒ 判据失效（场景被误删？）"
    failures = [r for r in results if not r.ok]
    detail = "\n".join(f"  ✘ {r.name}：{r.detail}" for r in failures)
    assert not failures, f"差分场景未达判词（{len(failures)}/{len(results)}）：\n{detail}"


def test_the_verdict_vocabulary_is_closed(upstream_version: str) -> None:
    """**判词取值域 MUST 封闭** —— 只允许 ``SAME`` / ``STRICTER`` / ``DIFF``。

    ⇒ 新增判词 MUST 显式改本断言（⇒ 防止「随手加一个宽容判词」把门禁稀释掉）。
    """
    allowed = {"SAME", "STRICTER", "DIFF"}

    for scenario in parity_probe._scenarios():
        assert scenario.verdict in allowed, (
            f"场景 {scenario.name!r} 的判词 {scenario.verdict!r} 不在封闭取值域 {sorted(allowed)}"
        )
        if scenario.verdict in {"STRICTER", "DIFF"}:
            assert scenario.note, (
                f"场景 {scenario.name!r} 的判词 {scenario.verdict!r} MUST 带理由（note）"
            )


@pytest.mark.parametrize(
    ("barrier_shape", "channel_kind", "reachability"),
    parity_probe.d24_parameter_space(),
    ids=lambda value: value,
)
def test_d24_parameterized_barrier_scenarios_match_the_upstream(
    barrier_shape: str,
    channel_kind: str,
    reachability: str,
    upstream_version: str,
) -> None:
    """**D-24**（判词 **SAME**）—— **参数化**（**屏障形态 × 通道类型 × 源可达性**）。

    ⇒ 断言两侧的**节点序列 + 最终状态**逐字一致 ⇒ ⇒ 兑现**承接条款 H-6** /
    立项书 §4.2 **S5 ③** 的「**B7F4 起逐个补**」的**最小增量**
    ⇒ ⇒ **MUST NOT** 一次性铺开 **S5 ③** 的**全量**枚举（归后续 feature）。

    ⚠️ 上游缺席即 **skip**（沿用 B5F2 的「缺席即 skip」纪律）⇒ ⇒ **不是失败**。
    """
    scenario = parity_probe.d24_scenario(barrier_shape, channel_kind, reachability)

    fg_kind, fg_state, _, _ = parity_probe.run_freegraph(scenario)
    scenario.clear()
    up_kind, up_state, _, _ = parity_probe.run_upstream(scenario)

    label = f"{barrier_shape} × {channel_kind} × {reachability}"
    assert fg_kind == up_kind, (
        f"D-24 参数化场景 {label} 的「成功 / 失败」不一致："
        f"freegraph={fg_kind} · upstream={up_kind}"
    )
    if fg_kind == "OK":
        assert fg_state == up_state, (
            f"D-24 参数化场景 {label} 的最终状态不一致："
            f"freegraph={fg_state} · upstream={up_state}"
        )
