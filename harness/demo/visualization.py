#!/usr/bin/env python3
"""freegraph 图导出与可视化验收脚本（人工验收目标）。

定位
----
验证 §5.8.1 承诺的**图结构导出 / mermaid / PNG** 三项能力，以及
§5.8.1 的**流式事件**（C12）。

这一组是 `target.py` **第 144 行**（`agent.get_graph(xray=True).draw_mermaid_png()`）
的**前置与放大版**：`target.py` 只要求「不抛阻断性异常」，本脚本把判据写细：

* `draw_mermaid()` 纯本地必成功，且内容含节点名（C14）；
* `draw_mermaid_png()` 离线不抛异常，且返回的字节**必须是可被
  `IPython.display.Image` 接受的合法 PNG**（最小合法 PNG 头即可）——
  非法字节会在 `Image()` 构造阶段就抛错，同样会中断脚本（§9.2 约束 6）。

覆盖契约：**C12**（流式）、**C13**（图结构导出）、**C14**（mermaid 导出）、
**C15**（PNG 渲染）、**C26**（子图 v1 仅签名兼容）；
对应 Phase **F8P2 / F22P1 / F23P1**。

依赖：**只 import `freegraph` 与 Python 标准库**。

用法
----
    python harness/demo/visualization.py     # 退出码 0 = PASS，1 = 断言失败，2 = 环境未就绪
"""

from __future__ import annotations

import sys
from typing import Any, TypedDict

try:
    from freegraph.graph import (
        END,
        START,
        StateGraph,
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


def eq(actual: Any, expected: Any, label: str) -> bool:
    return check(actual == expected, label, f"期望 {expected!r}，实际 {actual!r}")


def finish(title: str) -> int:
    print(f"\n── {title} 汇总 ──")
    print(f"断言 {_CHECKS} 条 · 通过 {_CHECKS - len(_FAILED)} · 失败 {len(_FAILED)}")
    for item in _FAILED:
        print(f"  ✘ {item}")
    print("结论：" + ("PASS" if not _FAILED else "FAIL"))
    return 0 if not _FAILED else 1


# ─────────────────────────────────────────────────────────────────────────────
# 合法 PNG 的最小判据（不依赖 PIL / IPython —— 那会引入第三方依赖）
# ─────────────────────────────────────────────────────────────────────────────
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def looks_like_png(data: bytes) -> tuple[bool, str]:
    """判定字节是否是一张**结构合法**的 PNG。

    判据取自 PNG 规范（ISO/IEC 15948）：
    1. 8 字节签名 `89 50 4E 47 0D 0A 1A 0A`；
    2. 紧随其后是 **IHDR** 块（长度 13）；
    3. 至少存在 **IEND** 块。
    只满足签名是不够的——`IPython.display.Image` 会解析 IHDR/IEND，
    仅有签名的字节在 `Image()` 构造阶段就会抛错。
    """
    if not isinstance(data, (bytes, bytearray)):
        return False, f"不是字节类型，而是 {type(data).__name__}"
    data = bytes(data)
    if len(data) < 8:
        return False, f"长度 {len(data)} < 8"
    if not data.startswith(PNG_MAGIC):
        return False, "PNG 签名不匹配"
    if b"IHDR" not in data[:32]:
        return False, "缺少 IHDR 块"
    if b"IEND" not in data[-32:]:
        return False, "缺少 IEND 块"
    return True, "签名 + IHDR + IEND 齐备"


# ─────────────────────────────────────────────────────────────────────────────
class State(TypedDict):
    value: int


def _triangle_graph():
    """一个小图：start → a → b → end，另加一条 a → end 的条件边。"""

    def a(state: State) -> dict:
        return {"value": state.get("value", 0) + 1}

    def b(state: State) -> dict:
        return {"value": state.get("value", 0) + 10}

    def route(state: State) -> str:
        return "b" if state.get("value", 0) >= 0 else END

    g = StateGraph(State)
    g.add_node("a", a)
    g.add_node("b", b)
    g.add_edge(START, "a")
    g.add_conditional_edges("a", route, ["b", END])
    g.add_edge("b", END)
    return g


# ─────────────────────────────────────────────────────────────────────────────
# V1 · 图结构导出：C13
# ─────────────────────────────────────────────────────────────────────────────
def case_get_graph() -> None:
    section("V1 图结构导出 · C13")

    app = _triangle_graph().compile()
    check(hasattr(app, "get_graph"), "编译产物具备 get_graph()")

    try:
        graph = app.get_graph()
    except Exception as exc:  # noqa: BLE001
        check(False, "get_graph() 可调用", f"{type(exc).__name__}: {exc}")
        return

    check(graph is not None, "C13 get_graph() 返回自有 Graph 对象")
    nodes = getattr(graph, "nodes", None)
    edges = getattr(graph, "edges", None)
    check(nodes is not None, "C13 Graph 含 nodes")
    check(edges is not None, "C13 Graph 含 edges")
    if nodes is not None:
        names = {getattr(n, "name", n) for n in nodes}
        check({"a", "b"} <= names, "C13 nodes 含业务节点名", f"实际 {sorted(map(str, names))}")
    if edges is not None:
        check(len(edges) > 0, "C13 edges 非空", f"实际 {len(edges)} 条")


# ─────────────────────────────────────────────────────────────────────────────
# V2 · xray 签名兼容：C13 / C26（v1 仅保证签名可用）
# ─────────────────────────────────────────────────────────────────────────────
def case_xray_signature() -> None:
    section("V2 get_graph(xray=) 签名兼容 · C13 / C26")

    app = _triangle_graph().compile()
    try:
        g1 = app.get_graph(xray=True)
        check(g1 is not None, "C13 get_graph(xray=True) 可调用（target.py 第 144 行依赖）")
    except Exception as exc:  # noqa: BLE001
        check(False, "C13 get_graph(xray=True) 可调用", f"{type(exc).__name__}: {exc}")
    try:
        app.get_graph(xray=False)
        check(True, "C13 get_graph(xray=False) 可调用")
    except Exception as exc:  # noqa: BLE001
        check(False, "C13 get_graph(xray=False) 可调用", f"{type(exc).__name__}: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# V3 · mermaid 导出：C14
# ─────────────────────────────────────────────────────────────────────────────
def case_draw_mermaid() -> None:
    section("V3 mermaid 文本导出 · C14")

    app = _triangle_graph().compile()
    graph = app.get_graph()
    check(hasattr(graph, "draw_mermaid"), "Graph 提供 draw_mermaid()")

    try:
        text = graph.draw_mermaid()
    except Exception as exc:  # noqa: BLE001
        check(False, "C14 draw_mermaid() 纯本地必成功", f"{type(exc).__name__}: {exc}")
        return

    check(isinstance(text, str), "C14 draw_mermaid() 返回 str", f"实际 {type(text).__name__}")
    if isinstance(text, str):
        check(len(text.strip()) > 0, "C14 mermaid 文本非空")
        check("a" in text and "b" in text, "C14 mermaid 文本含节点名", f"实际内容前 120 字：{text[:120]!r}")


# ─────────────────────────────────────────────────────────────────────────────
# V4 · PNG 渲染：C15（关键：必须是合法 PNG 字节）
# ─────────────────────────────────────────────────────────────────────────────
def case_draw_mermaid_png() -> None:
    section("V4 PNG 渲染 · C15（合法 PNG 字节，离线不抛异常）")

    app = _triangle_graph().compile()
    graph = app.get_graph()
    check(hasattr(graph, "draw_mermaid_png"), "Graph 提供 draw_mermaid_png()")

    try:
        data = graph.draw_mermaid_png()
    except Exception as exc:  # noqa: BLE001
        check(False, "C15 draw_mermaid_png() 离线不抛阻断性异常", f"{type(exc).__name__}: {exc}")
        return

    ok, why = looks_like_png(data)
    check(ok, "C15 返回可被 IPython.display.Image 接受的合法 PNG 字节", why)
    if ok:
        print(f"  · PNG 字节数 = {len(data)}")


# ─────────────────────────────────────────────────────────────────────────────
# V5 · 流式模式：C12
# ─────────────────────────────────────────────────────────────────────────────
def case_stream_modes() -> None:
    section("V5 流式事件 · C12")

    app = _triangle_graph().compile()
    check(hasattr(app, "stream"), "编译产物具备 stream()")

    modes = ["values", "updates", "checkpoints", "tasks", "debug", "messages", "custom"]
    for mode in modes:
        try:
            events = list(app.stream({"value": 0}, stream_mode=mode))
            check(True, f"C12 stream_mode={mode!r} 可用（产出 {len(events)} 个事件）")
        except Exception as exc:  # noqa: BLE001
            check(False, f"C12 stream_mode={mode!r} 可用", f"{type(exc).__name__}: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# V6 · target.py 第 144 行的等价复现
# ─────────────────────────────────────────────────────────────────────────────
def case_target_line_144_equivalent() -> None:
    section("V6 target.py:144 等价复现（不依赖 LangChain）")

    app = _triangle_graph().compile()
    try:
        png = app.get_graph(xray=True).draw_mermaid_png()
        ok, why = looks_like_png(png)
        check(ok, "V6 get_graph(xray=True).draw_mermaid_png() 返回合法 PNG", why)
    except Exception as exc:  # noqa: BLE001
        check(False, "V6 get_graph(xray=True).draw_mermaid_png() 可完成", f"{type(exc).__name__}: {exc}")


def main() -> int:
    print("══ visualization · freegraph 图导出与可视化验收 ══")
    print(f"Python {sys.version.split()[0]} · 只依赖 freegraph + 标准库")

    for case in (
        case_get_graph,
        case_xray_signature,
        case_draw_mermaid,
        case_draw_mermaid_png,
        case_stream_modes,
        case_target_line_144_equivalent,
    ):
        try:
            case()
        except Exception as exc:  # noqa: BLE001
            check(False, f"用例组 {case.__name__} 未抛异常即完成", f"{type(exc).__name__}: {exc}")

    return finish("visualization")


if __name__ == "__main__":
    raise SystemExit(main())
