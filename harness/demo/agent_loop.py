#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""freegraph Agent 工具循环验收脚本（人工验收目标）。

定位
----
`target.py` 用 **LangChain 的** `init_chat_model` / `@tool` 跑通 tool-calling 循环，
证明的是**生态兼容性**。

本脚本用**纯 Python 写的鸭子类型**（假模型 + 假工具）跑**同一个循环**，
证明的是：**内核的图能力足以独立支撑一个 agent 循环，不依赖 LangChain 也能成立**。

它同时是 `target.py` 的**零依赖等价物**——两条路径应当给出**逐字段一致**的
最终状态（`messages` 长度、`llm_calls` 计数、工具结果）。

覆盖契约：C4（稀疏状态）、C7/C8（路由与 fresh 读）、C11（完整状态）、
C16（Command）、C17（中断恢复）；对应 Phase **F7P3 / F8P1 / F8P2 / F9P1 / F10P1**。

依赖：**只 import `freegraph` 与 Python 标准库**。

用法
----
    python harness/demo/agent_loop.py        # 退出码 0 = PASS，1 = 断言失败，2 = 环境未就绪
"""

from __future__ import annotations

import sys
from typing import Annotated, Any, TypedDict

try:
    from freegraph.graph import (
        END,
        START,
        Command,
        StateGraph,
        interrupt,
    )
except ImportError as exc:  # pragma: no cover - 环境未就绪路径
    print(f"[环境未就绪] 无法导入 freegraph：{exc}")
    print("→ freegraph 尚未实现（内核自 F1P1 起），或当前环境未安装本仓库。")
    raise SystemExit(2) from exc


# ─────────────────────────────────────────────────────────────────────────────
# 极简断言框架（刻意内联：每个脚本都能单文件独立运行，只依赖 freegraph + 标准库）
# ─────────────────────────────────────────────────────────────────────────────
_CHECKS = 0
_FAILED: list[str] = []
_SOFT: list[str] = []
_SECTION = ""


def section(title: str) -> None:
    global _SECTION
    _SECTION = title
    print(f"\n[{title}]")


def check(cond: Any, label: str, detail: str = "") -> bool:
    global _CHECKS
    _CHECKS += 1
    ok = bool(cond)
    if not ok:
        _FAILED.append(f"{_SECTION} · {label}" + (f" — {detail}" if detail else ""))
    print(f"  {'✔' if ok else '✘'} {label}" + (f"  ({detail})" if detail and not ok else ""))
    return ok


def soft(cond: Any, label: str, note: str = "") -> bool:
    """**章程未锁定形态**的检查：不判失败，只标注「待锁定」。"""
    global _CHECKS
    _CHECKS += 1
    ok = bool(cond)
    if not ok:
        _SOFT.append(f"{_SECTION} · {label}" + (f" — {note}" if note else ""))
    print(f"  {'✔' if ok else '◌'} {label}" + (f"  ({note})" if note else ""))
    return ok


def eq(actual: Any, expected: Any, label: str) -> bool:
    return check(actual == expected, label, f"期望 {expected!r}，实际 {actual!r}")


def finish(title: str) -> int:
    print(f"\n── {title} 汇总 ──")
    print(f"断言 {_CHECKS} 条 · 通过 {_CHECKS - len(_FAILED)} · 失败 {len(_FAILED)}")
    for item in _FAILED:
        print(f"  ✘ {item}")
    if _SOFT:
        print(f"待锁定形态 {len(_SOFT)} 条（不判失败）：")
        for item in _SOFT:
            print(f"  ◌ {item}")
    print("结论：" + ("PASS" if not _FAILED else "FAIL"))
    return 0 if not _FAILED else 1


# ─────────────────────────────────────────────────────────────────────────────
# 鸭子类型：消息 / 模型 / 工具（模拟 LangChain 的最小结构，freegraph 不应依赖它）
# ─────────────────────────────────────────────────────────────────────────────
class FakeMessage:
    """最小消息对象：只需 content + tool_calls 两个属性。"""

    def __init__(self, content: str = "", tool_calls: list | None = None) -> None:
        self.content = content
        self.tool_calls = tool_calls or []

    def __repr__(self) -> str:  # pragma: no cover - 仅用于输出
        return f"FakeMessage({self.content!r}, tool_calls={self.tool_calls!r})"


class FakeToolCall(dict):
    """OpenAI 风格 tool_call 结构：{"name","args","id","type"}。"""


class FakeModel:
    """最小模型接口：可 bind_tools，返回自身；invoke 产出预置消息序列。"""

    def __init__(self, responses: list) -> None:
        self._responses = list(responses)
        self._i = 0
        self.calls = 0

    def bind_tools(self, tools: list) -> "FakeModel":
        return self

    def invoke(self, messages: list) -> FakeMessage:
        self.calls += 1
        msg = self._responses[min(self._i, len(self._responses) - 1)]
        self._i += 1
        return msg


def make_tool(name: str, fn):
    """最小工具对象：name + invoke(args)。"""

    class _Tool:
        def __init__(self) -> None:
            self.name = name

        def invoke(self, args: dict) -> Any:
            return fn(**args)

    return _Tool()


# ─────────────────────────────────────────────────────────────────────────────
# 状态 schema
# ─────────────────────────────────────────────────────────────────────────────
def operator_add(current: list, new: list) -> list:
    """C2 二元归约器（与 `operator.add` 等价，用函数形态以显式表达「恰好 2 个位置参数」）。"""
    return current + new


class AgentState(TypedDict, total=False):
    messages: Annotated[list, operator_add]
    llm_calls: int


# ─────────────────────────────────────────────────────────────────────────────
# B1 · 基本工具循环
# ─────────────────────────────────────────────────────────────────────────────
def build_agent_graph(model: FakeModel, tools: dict):
    """搭出与 target.py 同构的 agent ⇄ tool 循环。"""

    def agent(state: AgentState) -> dict:
        # C4：稀疏状态 —— llm_calls 未写入时 .get(k, 0) 必须是 0 而不是 None
        calls = state.get("llm_calls", 0)
        msgs = list(state.get("messages", []))
        resp = model.invoke(msgs)
        return {"messages": [resp], "llm_calls": calls + 1}

    def should_continue(state: AgentState) -> str:
        # C8：路由函数看到 agent 刚写入的 messages（fresh 读）
        msgs = state.get("messages", [])
        last = msgs[-1] if msgs else None
        if last is not None and getattr(last, "tool_calls", None):
            return "tools"
        return END

    def tool_node(state: AgentState) -> dict:
        msgs = state.get("messages", [])
        last = msgs[-1]
        results = []
        for call in last.tool_calls:
            tool = tools[call["name"]]
            observation = tool.invoke(call["args"])
            results.append(FakeMessage(content=str(observation)))
        return {"messages": results}

    g = StateGraph(AgentState)
    g.add_node("agent", agent)
    g.add_node("tools", tool_node)
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", should_continue, ["tools", END])
    g.add_edge("tools", "agent")
    return g


def case_tool_loop() -> None:
    section("B1 工具循环 · C4 / C7 / C8 / C11")

    call = FakeToolCall(name="add", args={"a": 3, "b": 4}, id="call_1", type="tool")
    responses = [
        FakeMessage("", tool_calls=[call]),   # 第 1 轮：请求调用工具
        FakeMessage("7"),                     # 第 2 轮：给出最终答案
    ]
    model = FakeModel(responses)
    tools = {"add": make_tool("add", lambda a, b: a + b)}

    g = build_agent_graph(model, tools)
    out = g.compile().invoke({"messages": [FakeMessage("Add 3 and 4.")], "llm_calls": 0})

    msgs = out.get("messages", [])
    eq(model.calls, 2, "模型被调用 2 次（工具循环走了一轮）")
    eq(out.get("llm_calls"), 2, "C3/C11 llm_calls 覆盖语义：最终为 2")
    # messages：入参 1 条 + AIMessage(tool_call) 1 条 + ToolMessage 1 条 + AIMessage 1 条
    eq(len(msgs), 4, "messages 长度 = 4（入参 + 助手 + 工具结果 + 助手）")
    eq(msgs[-1].content, "7", "最终答案是 '7'")
    eq(msgs[2].content, "7", "工具结果为 7（add(3,4)）")
    check(
        getattr(msgs[1], "tool_calls", None) == [call],
        "工具调用请求原样保留在 messages 中",
    )


def case_tool_call_shape() -> None:
    section("B2 tool_calls 结构与鸭子类型读取")

    call = FakeToolCall(name="add", args={"a": 3, "b": 4}, id="call_1", type="tool")
    model = FakeModel([FakeMessage("", tool_calls=[call]), FakeMessage("done")])
    tools = {"add": make_tool("add", lambda a, b: a + b)}
    g = build_agent_graph(model, tools)
    out = g.compile().invoke({"messages": [], "llm_calls": 0})

    msgs = out.get("messages", [])
    tc = getattr(msgs[1], "tool_calls", None)
    check(bool(tc), "tool_calls 为非空 list")
    if tc:
        eq(sorted(tc[0].keys()), ["args", "id", "name", "type"], "tool_call 结构为 name/args/id/type")
        eq(tc[0]["name"], "add", "tool_call.name 可读")
        eq(tc[0]["args"], {"a": 3, "b": 4}, "tool_call.args 可读")


def case_interrupt_in_loop() -> None:
    section("B3 人工审批插入工具循环 · C17")

    call = FakeToolCall(name="risky", args={}, id="call_r", type="tool")
    model = FakeModel([FakeMessage("", tool_calls=[call]), FakeMessage("approved")])

    def risky() -> str:
        approval = interrupt("approve risky tool?")
        return f"risky:{approval}"

    tools = {"risky": make_tool("risky", risky)}

    g = build_agent_graph(model, tools)
    app = g.compile()

    try:
        result = app.invoke({"messages": [], "llm_calls": 0})
    except Exception as exc:  # noqa: BLE001
        result = {"__interrupt__": (exc,)}
    check(result.get("__interrupt__") is not None, "工具执行前触发中断")
    if result.get("__interrupt__") is not None:
        itr = result["__interrupt__"]
        first = itr[0] if isinstance(itr, (tuple, list)) else itr
        eq(getattr(first, "value", None), "approve risky tool?", "中断载荷可读")

    # 「从节点起点重跑」是 C17 的语义；**恢复是否依赖 checkpointer**（C19 的实现细节）
    # 章程未锁定，故本项为软断言——若实现要求 checkpointer，此处标注待锁定而不判失败。
    try:
        out = app.invoke(Command(resume="yes"))
    except Exception as exc:  # noqa: BLE001
        soft(False, "Command(resume=) 后工具带审批结果继续执行",
             f"恢复需 checkpointer 支持（{type(exc).__name__}: {exc}）——载体待 F14P1 锁定")
        return
    msgs = out.get("messages", [])
    check(
        any("risky:yes" in str(m.content) for m in msgs),
        "Command(resume=) 后工具带审批结果继续执行",
        f"实际 messages={msgs!r}",
    )


def case_command_update_from_tool() -> None:
    section("B4 工具节点直接更新状态 · C16")

    def tool_node_cmd(state: AgentState) -> Command:
        return Command(update={"messages": [FakeMessage("from-command")]})

    g = StateGraph(AgentState)
    g.add_node("cmd", tool_node_cmd)
    g.add_edge(START, "cmd")
    g.add_edge("cmd", END)
    out = g.compile().invoke({"messages": [], "llm_calls": 0})
    msgs = out.get("messages", [])
    check(
        any(getattr(m, "content", "") == "from-command" for m in msgs),
        "C16 工具节点用 Command(update=) 直接写入状态",
        f"实际 messages={msgs!r}",
    )


def main() -> int:
    print("══ agent_loop · freegraph Agent 工具循环验收（零依赖等价物）══")
    print(f"Python {sys.version.split()[0]} · 只依赖 freegraph + 标准库")

    for case in (
        case_tool_loop,
        case_tool_call_shape,
        case_interrupt_in_loop,
        case_command_update_from_tool,
    ):
        try:
            case()
        except Exception as exc:  # noqa: BLE001
            check(False, f"用例组 {case.__name__} 未抛异常即完成", f"{type(exc).__name__}: {exc}")

    return finish("agent_loop")


if __name__ == "__main__":
    raise SystemExit(main())
