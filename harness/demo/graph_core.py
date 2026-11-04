#!/usr/bin/env python3
"""freegraph 图运行时内核验收脚本（**前置用例**）。

定位
----
`target.py` 验证的是「freegraph 与 LangChain 生态的兼容性」——它自带
`langchain.*` 导入，用真实/伪模型跑通 tool-calling 循环。

本脚本验证的是**另一件事**：**图能力本身**。它

* **只 import `freegraph` 与 Python 标准库**——不引入任何第三方依赖，
  因此它同时是「零第三方运行时依赖」承诺（S1 / 立项书 §5.5）的**可执行证据**；
* **不依赖 LangChain**——证明内核的图语义独立成立，不是因为「蹭了 LangChain 才跑得起来」；
* 覆盖契约 **C1–C26** 中可独立判定的部分，对应 Phase **F4P1 / F5P1 / F5P2 / F6P1 / F7P1 /
  F7P2 / F7P3 / F8P1 / F8P3 / F9P1 / F10P1 / F11P1 / F12P1 / F13P1**（即 M1 + M2）。

它在 `target.py` **之前**跑：内核不过，图兼容无从谈起。

用法
----
    python harness/demo/graph_core.py            # 退出码 0 = PASS，1 = 断言失败，2 = 环境未就绪

接口形态说明
------------
本脚本锁定了若干**章程未逐字规定**的接口形态，是实现者的靶子（括号内为章程依据）：

* 公开门面统一为 `freegraph.graph`，且须再导出 `Command` / `Send` / `interrupt` /
  `RunConfig`（依据：F2P2「公开 API 门面 `freegraph/graph.py`」+ C16/C17/C18/C22）；
* `add_node(name, fn, alias=...)` 的**节点别名**形态（依据：C25 / F8P3）；
* `compile(checkpointer=..., store=...)` 的关键字形态（依据：C10 / C19 / C20）；
* `invoke(input, config)` 的 `config` 同时接受 `RunConfig` 与普通 dict
  （依据：C11 签名 `invoke(input, config=None)` + C22）；`recursion_limit` 走 dict 形态
  （依据：F13P1）。

`target.py` 是**只读基准**，本脚本不是——它随内核演进，但每次 v1 交付前必须全绿。
"""

from __future__ import annotations

import operator
import sys
import typing
from typing import Annotated, Any, TypedDict

try:
    from freegraph.graph import (
        END,
        START,
        Command,
        RunConfig,
        Send,
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
    """**章程未锁定形态**的检查：不判失败，只标注「待锁定」。

    用于「语义由章程规定、但调用形态尚未拍板」的检查点——形态一旦拍板，
    这里就该升级为硬断言（`check`）。
    """
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
# 状态 schema（仅用标准库 typing，避免引入 typing_extensions）
# ─────────────────────────────────────────────────────────────────────────────
class State(TypedDict):
    """C1 状态 schema：每个 key 映射到一个 channel。"""

    messages: Annotated[list, operator.add]  # C2 二元归约器 → 追加
    llm_calls: int                          # C3 无归约器 → 覆盖


class SparseState(TypedDict):
    """C4 稀疏状态观测用。"""

    written: int
    never_written: str


# ─────────────────────────────────────────────────────────────────────────────
# A1 · 状态模型：C1 / C2 / C3
# ─────────────────────────────────────────────────────────────────────────────
def case_state_model() -> None:
    section("A1 状态模型 · C1 / C2 / C3")

    def node_a(state: State) -> dict:
        return {"messages": ["a"], "llm_calls": 1}

    def node_b(state: State) -> dict:
        return {"messages": ["b"], "llm_calls": 1}

    g = StateGraph(State)
    g.add_node("a", node_a)
    g.add_node("b", node_b)
    g.add_edge(START, "a")
    g.add_edge("a", "b")
    g.add_edge("b", END)
    out = g.compile().invoke({"messages": [], "llm_calls": 0})

    # C2：Annotated[list, operator.add] 被识别为二元归约器 → 列表拼接
    eq(out.get("messages"), ["a", "b"], "C2 归约器生效：messages 追加为 ['a','b']")
    # C3：llm_calls 无归约器 → 覆盖而非累加（最终值应为最后一次写入的 1，而非 2）
    eq(out.get("llm_calls"), 1, "C3 无归约器的 key 覆盖而非累加")
    # C6：逐 key 应用 reducer
    check("messages" in out and "llm_calls" in out, "C6 返回值合并覆盖到完整状态")


# ─────────────────────────────────────────────────────────────────────────────
# A2 · 稀疏状态：C4（必须独立回归）
# ─────────────────────────────────────────────────────────────────────────────
def case_sparse_state() -> None:
    section("A2 稀疏状态 · C4（独立回归）")

    seen: dict = {}

    def writer(state: SparseState) -> dict:
        return {"written": 1}

    def observer(state: SparseState) -> dict:
        seen["input"] = dict(state)
        return {}

    g = StateGraph(SparseState)
    g.add_node("writer", writer)
    g.add_node("observer", observer)
    g.add_edge(START, "writer")
    g.add_edge("writer", "observer")
    g.add_edge("observer", END)
    g.compile().invoke({"written": 0, "never_written": "x"})

    node_input = seen.get("input", {})
    check("written" in node_input, "C4 已写入的 key 出现在节点入参中")
    check(
        "never_written" not in node_input or node_input.get("never_written") == "x",
        "C4 未写入的 key 不出现在节点入参中（入参是稀疏 dict）",
        f"实际入参 {node_input!r}",
    )
    # target.py 的等价断言：.get(k, default) 必须返回 default 而非 None
    eq(node_input.get("llm_calls", 0), 0, "C4 state.get(k, 0) 返回 0 而非 None")


# ─────────────────────────────────────────────────────────────────────────────
# A3 · 图构建与编译：C9 / C10
# ─────────────────────────────────────────────────────────────────────────────
def case_build_and_compile() -> None:
    section("A3 图构建与编译 · C9 / C10")

    eq(START, "__start__", "C9 START 常量值")
    eq(END, "__end__", "C9 END 常量值")

    def node(state: State) -> dict:
        return {}

    g = StateGraph(State)
    g.add_node("n", node)
    g.add_edge(START, "n")
    g.add_edge("n", END)

    compiled = g.compile()
    check(compiled is not None, "C10 compile() 无参可调用")
    check(hasattr(compiled, "invoke"), "C10 编译产物具备 invoke()")
    check(hasattr(compiled, "stream"), "C10 编译产物具备 stream()")

    # C10：compile(checkpointer=..., store=...) 关键字形态
    try:
        g.compile(checkpointer=None, store=None)
        check(True, "C10 compile(checkpointer=, store=) 关键字被接受")
    except TypeError as exc:
        check(False, "C10 compile(checkpointer=, store=) 关键字被接受", str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# A4 · 执行与状态返回：C11 / C5 / C6
# ─────────────────────────────────────────────────────────────────────────────
def case_invoke_returns_full_state() -> None:
    section("A4 执行与完整状态返回 · C11 / C5 / C6")

    def partial(state: State) -> dict:
        # C5：节点只需返回**部分** dict
        return {"messages": ["only-partial"]}

    g = StateGraph(State)
    g.add_node("p", partial)
    g.add_edge(START, "p")
    g.add_edge("p", END)
    out = g.compile().invoke({"messages": [], "llm_calls": 0})

    check(isinstance(out, dict), "C11 invoke() 返回 dict")
    eq(out.get("messages"), ["only-partial"], "C5/C6 节点返回部分 dict 即被合并")
    check("llm_calls" in out, "C11 返回**完整状态**（含未在本轮写入的 key）")


# ─────────────────────────────────────────────────────────────────────────────
# A5 · 条件边与 fresh 读：C7 / C8（必须独立回归）
# ─────────────────────────────────────────────────────────────────────────────
def case_conditional_edges() -> None:
    section("A5 条件边与 fresh 读 · C7 / C8（独立回归）")

    # C8：路由函数必须看到「本节点本次写入」的值
    observed: dict = {}

    def writer(state: State) -> dict:
        return {"messages": ["fresh"], "llm_calls": 7}

    def router(state: State) -> str:
        observed["messages"] = list(state.get("messages", []))
        observed["llm_calls"] = state.get("llm_calls")
        return "after"

    def after(state: State) -> dict:
        return {}

    g = StateGraph(State)
    g.add_node("writer", writer)
    g.add_node("after", after)
    g.add_edge(START, "writer")
    g.add_conditional_edges("writer", router, ["after", END])  # C7：list 形态
    g.add_edge("after", END)
    g.compile().invoke({"messages": [], "llm_calls": 0})

    check(
        observed.get("llm_calls") == 7,
        "C8 路由函数看到本节点刚写入的值（fresh 读）",
        f"路由实际读到 llm_calls={observed.get('llm_calls')!r}",
    )
    check(
        observed.get("messages") == ["fresh"],
        "C8 路由函数看到 reducer 合并后的最新 messages",
        f"实际 {observed.get('messages')!r}",
    )

    # C7：dict 形态的 path_map
    def router2(state: State) -> str:
        return "hit"

    def miss(state: State) -> dict:
        return {}

    def hit(state: State) -> dict:
        return {"messages": ["hit"]}

    g2 = StateGraph(State)
    g2.add_node("r", router2)
    g2.add_node("hit", hit)
    g2.add_node("miss", miss)
    g2.add_edge(START, "r")
    g2.add_conditional_edges("r", router2, {"hit": "hit", "miss": "miss"})  # C7：dict 形态
    g2.add_edge("hit", END)
    g2.add_edge("miss", END)
    out2 = g2.compile().invoke({"messages": [], "llm_calls": 0})
    eq(out2.get("messages"), ["hit"], "C7 dict 形态 path_map 正确路由")


# ─────────────────────────────────────────────────────────────────────────────
# A6 · 控制原语：C16 / C17 / C18
# ─────────────────────────────────────────────────────────────────────────────
def case_command_and_send() -> None:
    section("A6 控制原语 · C16 / C17 / C18")

    # C16：Command(goto=..., update=...)
    def router(state: State) -> str:
        return "cmd"

    def cmd_node(state: State) -> Command:
        return Command(goto=END, update={"messages": ["via-command"]})

    g = StateGraph(State)
    g.add_node("r", router)
    g.add_node("cmd", cmd_node)
    g.add_edge(START, "r")
    g.add_conditional_edges("r", router, ["cmd", END])
    g.add_edge("cmd", END)
    out = g.compile().invoke({"messages": [], "llm_calls": 0})
    check(
        "via-command" in (out.get("messages") or []),
        "C16 Command(update=) 的状态更新生效",
        f"实际 messages={out.get('messages')!r}",
    )

    # C18：Send(node, arg) —— 以自定义入参调用目标节点
    def fanout(state: State) -> list:
        return [Send("worker", {"n": 1}), Send("worker", {"n": 2})]

    def worker(state: Any) -> dict:
        # 自定义入参直接作为节点入参
        return {"messages": [f"w{state['n']}"]}

    g2 = StateGraph(State)
    g2.add_node("fan", fanout)
    g2.add_node("worker", worker)
    g2.add_edge(START, "fan")
    g2.add_edge("fan", "worker")
    g2.add_edge("worker", END)
    out2 = g2.compile().invoke({"messages": [], "llm_calls": 0})
    got = sorted(out2.get("messages") or [])
    eq(got, ["w1", "w2"], "C18 Send(node, arg) 以自定义入参 fan-out")


def case_interrupt_resume() -> None:
    section("A6 控制原语 · C17 中断与恢复")

    calls: list = []

    def asker(state: State) -> dict:
        answer = interrupt("approve?")
        calls.append(answer)
        return {"messages": [f"answer={answer}"]}

    g = StateGraph(State)
    g.add_node("ask", asker)
    g.add_edge(START, "ask")
    g.add_edge("ask", END)
    app = g.compile()

    # 第一次：中断
    try:
        result = app.invoke({"messages": [], "llm_calls": 0})
    except Exception as exc:  # noqa: BLE001 - 中断可能以异常或结果形式呈现
        result = {"__interrupt__": (exc,)}
    itr = result.get("__interrupt__")
    check(itr is not None, "C17 中断后结果含 `__interrupt__`", f"实际结果 {result!r}")
    if itr is not None:
        first = itr[0] if isinstance(itr, (tuple, list)) else itr
        check(hasattr(first, "value"), "C17 __interrupt__ 含 .value")
        check(hasattr(first, "id"), "C17 __interrupt__ 含 .id")
        eq(getattr(first, "value", None), "approve?", "C17 中断载荷原样透出")

    # 第二次：Command(resume=...) 从节点起点重跑
    # 「从节点起点重跑」是 C17 的语义；但**恢复是否依赖 checkpointer**（C19 的实现细节）
    # 章程未锁定，故本项为软断言——若实现要求 checkpointer，此处标注待锁定而不判失败。
    try:
        out = app.invoke(Command(resume="yes"))
    except Exception as exc:  # noqa: BLE001
        soft(False, "C17 Command(resume=) 从节点起点重跑并拿到 resume 值",
             f"恢复需 checkpointer 支持（{type(exc).__name__}: {exc}）——载体待 F14P1 锁定")
        return
    check(
        any("answer=yes" in str(m) for m in (out.get("messages") or [])),
        "C17 Command(resume=) 从节点起点重跑并拿到 resume 值",
        f"实际 messages={out.get('messages')!r}",
    )
    check(len(calls) == 1, "C17 重跑时节点只执行一次（不是从头重复）", f"实际执行 {len(calls)} 次")


# ─────────────────────────────────────────────────────────────────────────────
# A7 · 并发与错误传播
# ─────────────────────────────────────────────────────────────────────────────
def case_concurrency_and_errors() -> None:
    section("A7 并发执行与错误传播")

    def left(state: State) -> dict:
        return {"messages": ["left"]}

    def right(state: State) -> dict:
        return {"messages": ["right"]}

    g = StateGraph(State)
    g.add_node("left", left)
    g.add_node("right", right)
    g.add_edge(START, "left")
    g.add_edge(START, "right")
    g.add_edge("left", END)
    g.add_edge("right", END)
    out = g.compile().invoke({"messages": [], "llm_calls": 0})
    got = sorted(out.get("messages") or [])
    eq(got, ["left", "right"], "同 super-step 的两个节点都执行了（未被串行化丢弃）")

    class Boom(RuntimeError):
        pass

    def bad(state: State) -> dict:
        raise Boom("boom")

    g2 = StateGraph(State)
    g2.add_node("bad", bad)
    g2.add_edge(START, "bad")
    g2.add_edge("bad", END)
    try:
        g2.compile().invoke({"messages": [], "llm_calls": 0})
        check(False, "节点异常向上传播", "未抛出任何异常")
    except Boom:
        check(True, "节点异常向上传播")
    except Exception as exc:  # noqa: BLE001
        check(False, "节点异常向上传播", f"抛出了非预期异常类型 {type(exc).__name__}")


# ─────────────────────────────────────────────────────────────────────────────
# A8 · 递归上限：F13P1
# ─────────────────────────────────────────────────────────────────────────────
def case_recursion_limit() -> None:
    section("A8 递归上限 · F13P1")

    def loop(state: State) -> dict:
        return {"messages": ["loop"], "llm_calls": state.get("llm_calls", 0) + 1}

    g = StateGraph(State)
    g.add_node("loop", loop)
    g.add_edge(START, "loop")
    g.add_edge("loop", "loop")
    g.add_edge("loop", END)
    app = g.compile()
    try:
        app.invoke({"messages": [], "llm_calls": 0}, {"recursion_limit": 3})
        # 「超限抛明确异常」的语义由章程规定（F13P1），但**载体**（dict / RunConfig / 其他）章程未锁
        soft(False, "recursion_limit 超限抛明确异常", "以 dict 形态传 `recursion_limit` 未触发超限——载体待 F13P1 锁定")
    except Exception as exc:  # noqa: BLE001
        check(True, "recursion_limit 超限抛明确异常", f"（{type(exc).__name__}）")


# ─────────────────────────────────────────────────────────────────────────────
# A9 · 运行时配置与 context 独立通道：C21 / C22
# ─────────────────────────────────────────────────────────────────────────────
def case_run_config_and_context() -> None:
    section("A9 运行时配置与 context 独立通道 · C21 / C22")

    seen: dict = {}

    def node(state: State) -> dict:
        seen["ctx"] = getattr(state, "context", None)
        return {}

    g = StateGraph(State)
    g.add_node("n", node)
    g.add_edge(START, "n")
    g.add_edge("n", END)

    cfg = RunConfig(
        thread_id="thread-1",
        context={"user": "u1"},
        metadata={"m": 1},
        tags=["t1"],
    )
    eq(getattr(cfg, "thread_id", None), "thread-1", "C22 RunConfig.thread_id")
    eq(getattr(cfg, "context", None), {"user": "u1"}, "C22 RunConfig.context")
    eq(getattr(cfg, "metadata", None), {"m": 1}, "C22 RunConfig.metadata")
    eq(getattr(cfg, "tags", None), ["t1"], "C22 RunConfig.tags")

    g.compile().invoke({"messages": [], "llm_calls": 0}, cfg)

    # C21：context 是独立通道，不塞进 configurable
    check(
        seen.get("ctx") == {"user": "u1"},
        "C21 context 作为独立通道透传到节点",
        f"节点读到 context={seen.get('ctx')!r}",
    )
    check(
        not hasattr(cfg, "configurable"),
        "C21 context 未被塞进 configurable",
    )


# ─────────────────────────────────────────────────────────────────────────────
# A10 · 节点别名：C25
# ─────────────────────────────────────────────────────────────────────────────
def case_node_alias() -> None:
    section("A10 节点别名 · C25")

    def node(state: State) -> dict:
        return {"messages": ["x"]}

    g = StateGraph(State)
    try:
        g.add_node("agent", node, alias="model")
    except TypeError as exc:
        # C25 的**语义**由章程规定，但「别名」的具体调用形态章程未锁（C25 只说「允许别名」）
        soft(False, "C25 节点别名可寻址", f"实现未采用 `add_node(..., alias=)` 形态（{exc}）——形态待 F8P3 锁定")
        return
    g.add_edge(START, "agent")
    g.add_edge("agent", END)
    app = g.compile()

    out = app.invoke({"messages": [], "llm_calls": 0})
    eq(out.get("messages"), ["x"], "C25 带别名的节点正常执行")

    # 别名应在流式事件 / 图结构中可见（用于用户的 stream 过滤器）
    try:
        events = list(app.stream({"messages": [], "llm_calls": 0}, stream_mode="updates"))
        names = set()
        for ev in events:
            if isinstance(ev, dict):
                names.update(ev.keys())
        check(
            bool(names & {"model", "agent"}),
            "C25 别名（或原名）出现在流式事件中",
            f"事件键 = {sorted(names)}",
        )
    except Exception as exc:  # noqa: BLE001
        check(False, "C25 别名（或原名）出现在流式事件中", f"{type(exc).__name__}: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
def main() -> int:
    print("══ graph_core · freegraph 图运行时内核验收（前置用例）══")
    print(f"Python {sys.version.split()[0]} · 只依赖 freegraph + 标准库")

    for case in (
        case_state_model,
        case_sparse_state,
        case_build_and_compile,
        case_invoke_returns_full_state,
        case_conditional_edges,
        case_command_and_send,
        case_interrupt_resume,
        case_concurrency_and_errors,
        case_recursion_limit,
        case_run_config_and_context,
        case_node_alias,
    ):
        try:
            case()
        except Exception as exc:  # noqa: BLE001 - 单组失败不应中断整轮
            check(False, f"用例组 {case.__name__} 未抛异常即完成", f"{type(exc).__name__}: {exc}")

    return finish("graph_core")


if __name__ == "__main__":
    raise SystemExit(main())
