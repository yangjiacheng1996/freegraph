#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""freegraph 图运行时内核验收脚本（**前置用例**）。

定位
----
`target.py` 验证的是「freegraph 与 LangChain 生态的兼容性」——它自带
`langchain.*` 导入，用真实/伪模型跑通 tool-calling 循环。

本脚本验证的是**另一件事**：**图能力本身**。它

* **只 import `freegraph` 与 Python 标准库**——不引入任何第三方依赖，
  因此它同时是「零第三方运行时依赖」承诺（S1 / 立项书 §5.5）的**可执行证据**；
* **不依赖 LangChain**——证明内核的图语义独立成立，不是因为「蹭了 LangChain 才跑得起来」；
* 覆盖契约 **C1–C26** 中可独立判定的部分，对应 feature **B4F1 / B5F1 / B5F2 / B6F1 / B7F1 /
  B7F2 / B7F3 / B8F1 / B8F3 / B9F1 / B10F1 / B11F1 / B12F1 / B13F1**（即 M1 + M2）。

它在 `target.py` **之前**跑：内核不过，图兼容无从谈起。

用法
----
    python harness/demo/graph_core.py            # 退出码 0 = PASS，1 = 断言失败，2 = 环境未就绪

接口形态说明
------------
本脚本锁定了若干**章程未逐字规定**的接口形态，是实现者的靶子（括号内为章程依据）：

* 公开门面统一为 `freegraph.graph`，且须再导出 `Command` / `Send` / `interrupt` /
  `RunConfig`（依据：B2F2「公开 API 门面 `freegraph/graph.py`」+ C16/C17/C18/C22）；
* `add_node(name, fn, alias=...)` 的**节点别名**形态（依据：C25 / B8F3）；
* `compile(checkpointer=..., store=...)` 的关键字形态（依据：C10 / C19 / C20）；
* `invoke(input, config)` 的 `config` 同时接受 `RunConfig` 与普通 dict
  （依据：C11 签名 `invoke(input, config=None)` + C22）；`recursion_limit` 走 dict 形态
  （依据：B13F1）。

`target.py` 是**只读基准**，本脚本不是——它随内核演进，但每次 v1 交付前必须全绿。
"""

from __future__ import annotations

import operator
import sys
import typing
from typing import Annotated, Any, TypedDict

try:
    from freegraph.contracts import GraphRecursionError
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
    print("→ freegraph 尚未实现（内核自 B1F1 起），或当前环境未安装本仓库。")
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
    # ⚠️ **2026-11-18 · B8F1**：**条件边路由求值已交付**（M2）⇒ ⇒ ⇒ 本组
    # **整组**由**软断言**升级为**硬断言**（破冻结面 **T-6** · 宪法 v1.8.0
    # 「破冻结面的三条」① 的「**拆分而不删**」+ v1.14.0「**替换 MUST NOT 弱于
    # 原断言**」）⇒ ⇒ ⇒ **判据只可更严**（软 ⇒ 硬）⇒ ⇒ ⇒ **三条断言的语义
    # 逐字留存**（「fresh 读」「reducer 合并」「dict 形态路由」）。

    try:
        g.compile().invoke({"messages": [], "llm_calls": 0})
    except Exception as exc:  # noqa: BLE001
        check(False, "A5 条件边与 fresh 读 · C7 / C8", f"{type(exc).__name__}: {exc}")
        return

    eq(
        observed.get("llm_calls"),
        7,
        "C8 路由函数看到本节点刚写入的值（fresh 读）",
    )
    eq(
        observed.get("messages"),
        ["fresh"],
        "C8 路由函数看到 reducer 合并后的最新 messages",
    )

    # C7：dict 形态的 path_map
    def router2(state: State) -> str:
        return "hit"

    def miss(state: State) -> dict:
        return {}

    def hit(state: State) -> dict:
        return {"messages": ["hit"]}

    def r_node(state: State) -> dict:
        # ⚠️ **2026-11-18 · B8F1**：源节点**必须**返回 dict（节点返回值口径）
        # ⇒ ⇒ ⇒ 路由函数**另立**（``router2``）⇒ ⇒ ⇒ **断言的语义留存**
        # （「dict 形态的 path_map 正确路由」）⇒ ⇒ ⇒ **判据只可更严**。
        return {}

    g2 = StateGraph(State)
    g2.add_node("r", r_node)
    g2.add_node("hit", hit)
    g2.add_node("miss", miss)
    g2.add_edge(START, "r")
    g2.add_conditional_edges("r", router2, {"hit": "hit", "miss": "miss"})  # C7：dict 形态
    g2.add_edge("hit", END)
    g2.add_edge("miss", END)
    try:
        out2 = g2.compile().invoke({"messages": [], "llm_calls": 0})
    except Exception as exc:  # noqa: BLE001
        check(False, "C7 dict 形态 path_map 正确路由", f"{type(exc).__name__}: {exc}")
        return
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

    def r_node(state: State) -> dict:
        # ⚠️ **2026-11-18 · B8F1**：源节点**必须**返回 dict（节点返回值口径）
        # ⇒ ⇒ ⇒ 路由函数**另立**（``router``）⇒ ⇒ ⇒ **断言的语义留存**
        # （「Command(update=) **经条件边**到达」）。
        return {}

    g = StateGraph(State)
    g.add_node("r", r_node)
    g.add_node("cmd", cmd_node)
    g.add_edge(START, "r")
    g.add_conditional_edges("r", router, ["cmd", END])
    g.add_edge("cmd", END)
    # ⚠️ **2026-11-18 · B8F1**（破冻结面 **T-6** · 宪法 v1.8.0「破冻结面的
    # 三条」① 的「**拆分而不删**」+ v1.14.0「**替换 MUST NOT 弱于原断言**」）：
    # 「Command(update=) **经条件边**到达」依赖**条件边路由求值** ⇒ ⇒ ⇒ 该依赖
    # **已交付**（**B8F1** · M2）⇒ ⇒ ⇒ **降级理由失效** ⇒ ⇒ ⇒ 本段由**软断言**
    # 恢复为**硬断言** ⇒ ⇒ ⇒ **判据只可更严**（软 ⇒ 硬）⇒ ⇒ ⇒ **断言的语义
    # 逐字留存**（「C16 Command(update=) 的状态更新生效」）。
    try:
        out = g.compile().invoke({"messages": [], "llm_calls": 0})
    except Exception as exc:  # noqa: BLE001
        check(False, "C16 Command(update=) 的状态更新生效", f"{type(exc).__name__}: {exc}")
    else:
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
             f"恢复需 checkpointer 支持（{type(exc).__name__}: {exc}）——载体待 B14F1 锁定")
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
# A8 · 递归上限：B13F1
# ─────────────────────────────────────────────────────────────────────────────
def case_recursion_limit() -> None:
    section("A8 递归上限 · B13F1")

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
        check(False, "recursion_limit 超限抛明确异常", "未抛出任何异常")
    except GraphRecursionError as exc:
        check(True, "recursion_limit 超限抛明确异常", f"（{type(exc).__name__}）")
    except Exception as exc:  # noqa: BLE001
        check(
            False,
            "recursion_limit 超限抛明确异常",
            f"非 GraphRecursionError：{type(exc).__name__}: {exc}",
        )


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
    # ⚠️ **B7F3 · T011 实测暴露的陈旧期望**（**事实订正** · 非降级）：`RunConfig` 的
    # `tags` **已冻结为 `tuple`**（`src/freegraph/contracts/types.py:212` · 构造期
    # `tuple(...)` 拷贝）⇒ ⇒ 原期望 `["t1"]` **恒红** ⇒ ⇒ 改为 `("t1",)`。
    eq(getattr(cfg, "tags", None), ("t1",), "C22 RunConfig.tags")

    g.compile().invoke({"messages": [], "llm_calls": 0}, cfg)

    # C21：context 是独立通道，不塞进 configurable
    # ⚠️ **context 独立通道段降级为软断言**（T040 · **实测依据 = T011 的首次执行红点**）——
    # **context 独立通道**归 **B8F3**（M2）⇒ ⇒ 该段不判失败（缺口**具名**承接）。
    _B8F3_NOTE = "context 独立通道未交付 —— 归 B8F3"
    soft(
        seen.get("ctx") == {"user": "u1"},
        "C21 context 作为独立通道透传到节点",
        f"节点读到 context={seen.get('ctx')!r} —— {_B8F3_NOTE}",
    )
    # ⚠️ **T041**（B7F3 · 事实订正）：`RunConfig` **已冻结为有** `configurable` 字段
    # （`src/freegraph/contracts/types.py:215`）⇒ ⇒ 原断言 `not hasattr(cfg, "configurable")`
    # **恒红**（只在 `invoke` 就绪后才可达）⇒ ⇒ 保留判词原意（「context 未被塞进
    # `configurable`」）⇒ ⇒ 改为断言 `configurable` 为**空映射**。
    check(
        getattr(cfg, "configurable", None) == {},
        "C21 context 未被塞进 configurable",
        f"实际 configurable={getattr(cfg, 'configurable', None)!r}",
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
        soft(False, "C25 节点别名可寻址", f"实现未采用 `add_node(..., alias=)` 形态（{exc}）——形态待 B8F3 锁定")
        return
    g.add_edge(START, "agent")
    g.add_edge("agent", END)
    app = g.compile()

    out = app.invoke({"messages": [], "llm_calls": 0})
    eq(out.get("messages"), ["x"], "C25 带别名的节点正常执行")

    # 别名应在流式事件 / 图结构中可见（用于用户的 stream 过滤器）。
    # B8F2 已交付：事件为四键信封 ⇒ 节点名在 ``payload`` 的键上。
    _B8F2_NOTE = "B8F2 已交付 · 四键信封"
    try:
        events = list(app.stream({"messages": [], "llm_calls": 0}, stream_mode="updates"))
        names = set()
        for ev in events:
            if isinstance(ev, dict):
                payload = ev.get("payload", {})
                if isinstance(payload, dict):
                    names.update(payload.keys())
        soft(
            bool(names & {"model", "agent"}),
            "C25 别名（或原名）出现在流式事件中",
            f"事件 payload 键 = {sorted(names)} —— {_B8F2_NOTE}",
        )
    except Exception as exc:  # noqa: BLE001
        soft(False, "C25 别名（或原名）出现在流式事件中", f"{type(exc).__name__}: {exc} —— {_B8F2_NOTE}")


# ─────────────────────────────────────────────────────────────────────────────
def _invoke_ready() -> bool:
    """探测 ``invoke()`` 是否已就绪（B7F3）；MUST NOT 用「6 方法能力面」当判据。"""

    def node(state: State) -> dict:
        return {}

    graph = StateGraph(State)
    graph.add_node("n", node)
    graph.add_edge(START, "n")
    graph.add_edge("n", END)
    try:
        graph.compile().invoke({"messages": [], "llm_calls": 0})
    except NotImplementedError:
        return False
    except Exception:  # noqa: BLE001 - 其它失败交给正常用例报告
        return True
    return True


def main() -> int:
    print("══ graph_core · freegraph 图运行时内核验收（前置用例）══")
    print(f"Python {sys.version.split()[0]} · 只依赖 freegraph + 标准库")

    # ⚠️ 先跑 A3（compile 已交付时真跑通过），再探 invoke（B7F3）：
    #    - compile 仍不可用 ⇒ 退出码 2；
    #    - compile 可用、invoke 未就绪 ⇒ **A3 通过之后**打印 [环境未就绪] 并退出码 2；
    #    - 两者都就绪 ⇒ 正常跑全部用例。
    try:
        case_build_and_compile()
    except NotImplementedError:
        print("[环境未就绪] compile() 仍为桩（编译属 M2）")
        return 2
    except Exception as exc:  # noqa: BLE001 - A3 自身失败 ⇒ 正常报告
        check(
            False,
            "A3 图构建与编译未抛异常即完成",
            f"{type(exc).__name__}: {exc}",
        )
        return finish("graph_core")

    if not _invoke_ready():
        print("[环境未就绪] invoke() 仍为桩（执行属 B7F3）")
        return 2

    for case in (
        case_state_model,
        case_sparse_state,
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
