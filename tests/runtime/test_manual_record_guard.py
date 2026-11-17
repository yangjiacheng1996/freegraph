# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""**人工验证记录**的**文档守卫断言** —— 属 **B8F1**（tasks T068）。

**为什么要有它**（宪法原则 VI **v1.11.0 + v1.13.0**）：「**人工门禁类 SC**」
（**SC-019** 追认留痕 · **SC-020** 人工验证记录 · **SC-026** fake 轮的实测输出）
⇒ ⇒ ⇒ 其判据**MUST** 由**可自动核验的文档守卫断言**承担 ⇒ ⇒ ⇒
「**写记录**」与「**追认**」类任务**产出产物**但**不**构成判定覆盖 ⇒ ⇒ ⇒
本文件就是那层**判定覆盖**。

**四条断言**（**FR-042**）：

① 记录**存在**且**正文非空**（且含**五段式**的结构）；
② **两轮**各有一段**非空**的实测输出 —— 「**fake 模型轮**」MUST 有**真实的
   实测输出**（**MUST NOT** 只写「符合预期」）；「**真实模型轮**」若因**环境**
   不具备而无法完成 ⇒ MUST 出现**已登记的环境偏离**声明（宪法 v1.6.0 ��
   **MUST NOT** 用「未验证」替代）⇒ ⇒ ⇒ 两种形态**都算**通过；
③ 含「**追认**」文字且**逐条**列出**破面全集 7 类**（唯一事实源 =
   ``spec.md``「Assumptions」的「破面全集 7 类」）；
④ 本守卫**MUST NOT** 与契约守卫（``T018`` · §7 的 I-1…I-14）混在同一处
   ⇒ ⇒ ⇒ 本文件**只管文档**。

⚠️ **时序**（**MUST NOT** 造成「永久红的 CI」）：本守卫 MUST 在**记录写就之后**
才转绿 ⇒ ⇒ ⇒ 故它落在 **Phase 9**（tasks **T068**）⇒ ⇒ ⇒ **Phase 2 的契约
守卫（T018）不受本文件影响**。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

#: 仓库根目录（记录的定位基准）。
REPO_ROOT = Path(__file__).resolve().parents[2]

#: **人工验证记录**的落点（**五段式** + 来源覆盖表 + 两轮实测输出 + 追认文字）。
RECORD_RELPATH = "harness/verification/B8F1/manual-verification.md"

#: **破面全集 7 类**的**逐条**标识（唯一事实源 = ``spec.md``「Assumptions」）。
BREAK_UNIVERSE_MARKERS = (
    "T-1",
    "冻结断言 ①",
    "冻结断言 ②",
    "冻结断言 ④",
    "T-5",
    "T-6",
    "T-7",
)

#: 「**符合预期**」这类**空洞表述**（**MUST NOT** 充当实测输出）。
VACUOUS_MARKERS = ("符合预期", "符合设计预期", "行为正常")


def _record_text() -> str:
    """读取人工验证记录的全文。"""
    return (REPO_ROOT / RECORD_RELPATH).read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    """取出某个小节的正文（**不含**小节标题本身）。

    ⚠️ 以**同级或更高级**的下一个标题为界 ⇒ ⇒ ⇒ 小节边界**确定** ⇒ ⇒ ⇒
    「该小节有非空内容」是**可判定**的；**更低级别**的子小节（``###``）**属**本小节。
    """
    lines = text.splitlines()
    collected: list[str] = []
    inside = False
    level = 0
    for line in lines:
        match = re.match(r"^(#+)\s", line)
        if match:
            this_level = len(match.group(1))
            if line.startswith(heading):
                inside = True
                level = this_level
                continue
            if inside:
                if this_level <= level:
                    inside = False
                continue
        if inside:
            collected.append(line)
    return "\n".join(collected)


def _code_blocks(text: str) -> list[str]:
    """取出正文里的**全部**围栏代码块（**内容非空**的那些）。"""
    blocks: list[str] = []
    current: list[str] | None = None
    for line in text.splitlines():
        if line.strip().startswith("```"):
            if current is None:
                current = []
            else:
                blocks.append("\n".join(current))
                current = None
            continue
        if current is not None:
            current.append(line)
    return [block for block in blocks if block.strip()]


# ── ① 记录存在且正文非空 ───────────────────────────────────────────────


def test_the_manual_verification_record_exists_and_is_not_empty() -> None:
    """① 记录 MUST **存在**且**正文非空**（FR-042 ①）。"""
    path = REPO_ROOT / RECORD_RELPATH
    assert path.is_file(), f"缺人工验证记录：{RECORD_RELPATH}"
    text = path.read_text(encoding="utf-8")
    assert text.strip(), f"{RECORD_RELPATH} 的正文为空"
    # 五段式（环境 / 步骤 / 实际输出 / 结论 / 遗留问题）+ 两轮 + 追认
    for heading in (
        "## 1. 环境",
        "## 2. 步骤",
        "## 3. 实际输出",
        "## 4. 结论",
        "## 5. 人工验证的两轮",
        "## 7. 破冻结面的**发起者追认**",
        "## 8. 遗留问题",
    ):
        assert heading in text, f"{RECORD_RELPATH} 缺小节：{heading}"
    assert "### 来源覆盖" in text, f"{RECORD_RELPATH} 缺「来源覆盖表」"


# ── ② 两轮各有一段非空的实测输出 ─────────────────────────────────────────


def test_the_fake_model_round_has_a_real_measured_output() -> None:
    """② 「**fake 模型轮**」MUST 有**真实的实测输出**（**MUST NOT** 只写「符合预期」）。

    ⇒ ⇒ ⇒ 本轮**本 feature 可达**（MUST 真跑并记录 · 裁定 19）⇒ ⇒ ⇒
    ⇒ ⇒ ⇒ 实测输出 MUST 含**条件边路由的可观察结果**（路由目标 · 目标节点执行次数 · fresh 视图）。
    """
    section = _section(_record_text(), "### 5.1 ")
    assert section.strip(), "「fake 模型轮」小节为空"
    blocks = _code_blocks(section)
    assert blocks, "「fake 模型轮」小节没有实测输出代码块"
    output = "\n".join(blocks)
    for marker in ("fresh 视图", "路由目标", "执行次数"):
        assert marker in output, f"「fake 模型轮」的实测输出缺「{marker}」"
    for vacuous in VACUOUS_MARKERS:
        assert vacuous not in output, (
            f"「fake 模型轮」的实测输出出现空洞表述「{vacuous}」"
        )


def test_the_real_model_round_is_measured_or_registered_as_an_environment_deviation() -> None:
    """② 「**真实模型轮**」MUST 有实测输出，**或** 已**登记的环境偏离**（FR-042 ②）。

    ⚠️ 宪法 v1.6.0：环境不具备时 MUST **登记为环境偏离**并写明 ⇒ ⇒ ⇒
    **MUST NOT** 用「未验证」替代 ⇒ ⇒ ⇒ 两种形态**都算**通过 ⇒ ⇒ ⇒
    **MUST NOT** 让本守卫**永久红**（红线：MUST NOT 写永久红的 CI）。
    """
    section = _section(_record_text(), "### 5.2 ")
    assert section.strip(), "「真实模型轮」小节为空"
    blocks = _code_blocks(section)
    measured = any(block.strip() for block in blocks)
    registered = "环境偏离" in section and "未落地" in section
    assert measured or registered, (
        "「真实模型轮」既没有实测输出，也没有已登记的环境偏离声明"
    )
    for vacuous in VACUOUS_MARKERS:
        assert vacuous not in section, (
            f"「真实模型轮」出现空洞表述「{vacuous}」"
        )


# ── ③ 追认文字 + 破面全集 7 类 ─────────────────────────────────────────


def test_the_record_contains_the_ratification_text() -> None:
    """③ 记录 MUST 含「**追认**」文字（FR-042 ③）。"""
    text = _record_text()
    assert "追认" in text, f"{RECORD_RELPATH} 缺「追认」文字"
    section = _section(text, "## 7. ")
    assert section.strip(), "「追认」小节为空"
    assert "追认次数" in section, "「追认」小节缺「追认次数」的声明"


@pytest.mark.parametrize("marker", BREAK_UNIVERSE_MARKERS)
def test_the_record_lists_every_break_of_the_frozen_surface(marker: str) -> None:
    """③ 追认文字 MUST **逐条**列出**破面全集 7 类**（唯一事实源 = spec 的 Assumptions）。"""
    text = _record_text()
    assert marker in text, f"{RECORD_RELPATH} 的追认文字缺破面项「{marker}」"


def test_the_break_universe_has_exactly_seven_entries() -> None:
    """③ **破面全集 == 7 类**（**数量**也 MUST 与 spec 一致 ⇒ 不得多列 / 少列）。"""
    assert len(BREAK_UNIVERSE_MARKERS) == 7
    section = _section(_record_text(), "### 7.1 ")
    rows = [
        line
        for line in section.splitlines()
        if re.match(r"^\|\s*\*\*[①②③④⑤⑥⑦]\*\*\s*\|", line)
    ]
    assert len(rows) == 7, f"破面清单的条目数 == {len(rows)}（期望 7）"
