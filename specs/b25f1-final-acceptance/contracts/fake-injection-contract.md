# Contract: fake 注入（FakeModel / init_chat_model）

**Feature**: B25F1 · **Date**: 2026-11-25
**Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md)

> 本契约锁定 **fake 轮**的注入形态、固定输出序列、固定断言点与失败语义。
> 它是 FR-001 / FR-002 / FR-003 / H-1 的可执行判据。

---

## 1. 注入形态

| 项 | 规则 |
|---|---|
| 目标 | `langchain.chat_models.init_chat_model` |
| 返回值 | 实现 `bind_tools(tools)`（返回自身）与 `invoke(messages)` 的对象 |
| 时机 | **MUST** 在 `harness/demo/target.py:23` 的导入之前生效 |
| 主路径 | 同进程：`runpy.run_path(..., run_name="__main__")` 前猴补 |
| 等价路径 | 子进程：临时 `sitecustomize.py` + `PYTHONPATH` 启动 `target.py` |
| 位置 | 只允许在 `harness/verification/B25F1/` 与 `tests/`；**MUST NOT** 进入 `src/freegraph/` |
| `target.py` | **零改动**（双重基线；见 target-baseline-contract） |

**备选（不作主路径）**：import 后替换 `target.model` / `target.model_with_tools`。
若使用，验收记录 MUST 注明；CI 的 A1 主路径 MUST 是「导入前注入」。

---

## 2. 固定输出序列（恰好 2 轮）

### 第 1 轮

```python
AIMessage(
    content="",
    tool_calls=[{
        "name": "add",
        "args": {"a": 3, "b": 4},
        "id": "call_1",
        "type": "tool_call",
    }],
)
```

### 第 2 轮

```python
AIMessage(content="The answer is 7.")   # 文本内容可变，但 MUST 非空
```

### 第 3 次调用

**显式失败**（`RuntimeError` / `AssertionError`）：固定脚本只应调用 2 次；
多于 2 次说明工具循环或路由异常。

---

## 3. 固定断言点（A1）

| # | 断言 | 期望 | 失败语义 |
|---|---|---|---|
| 1 | `len(result["messages"])` | **4** | 退出码 1 |
| 2 | `result["llm_calls"]` | **2** | 退出码 1 |
| 3 | 工具结果（`ToolMessage.content`，**归一为 int**） | **7** | 退出码 1 |
| 4 | `result` 的键 | 含 `messages` 与 `llm_calls` | 退出码 1 |

**消息顺序**（MUST 按下表）：

| 索引 | 类型 | 来源 |
|---|---|---|
| 0 | `HumanMessage("Add 3 and 4.")` | `target.py:167` 初始输入 |
| 1 | `AIMessage`（`tool_calls` 非空） | 第 1 轮 fake |
| 2 | `ToolMessage(7, tool_call_id="call_1")` | `target.py:109-117` |
| 3 | `AIMessage`（最终文本） | 第 2 轮 fake |

> `SystemMessage` 只进入模型输入、**不进入状态**；`messages` 长度 **不是 3**。

---

## 4. 与路由函数正交（H-1 / B8F1 D-5）

- fake **只替换模型对象**；`should_continue` 仍是用户函数，读
  `state["messages"][-1].tool_calls`；
- 注入层 **MUST NOT** 改写 `should_continue` 的输入 / 返回值；
- 注入层 **MUST NOT** 只对节点生效而对条件边失效；
- 验收 MUST 覆盖「第 1 轮有 `tool_calls` ⇒ 路由到 `tool_node`；第 2 轮无 ⇒ END」。

---

## 5. fake 能力要求

| 能力 | 必须 | 说明 |
|---|---|---|
| `bind_tools(tools)` | ✅ | 返回自身（或等价对象），供 `target.py:69` |
| `invoke(messages)` | ✅ | 返回 `AIMessage`；第 1 轮含 `tool_calls` |
| `tool_calls` 非空 | ✅ 第 1 轮 | 否则 A1 退化为「单轮无工具」 |
| `tool_call.id` | ✅ | 与 `ToolMessage.tool_call_id` 对齐 |
| `content` | ✅ 第 2 轮 | 非空最终文本 |
| 消息鸭子类型 | ✅ | `tool_calls` / `content` / `pretty_print()`（`target.py:169-170`） |

---

## 6. 失败语义

| 情形 | 判定 |
|---|---|
| fake 只产出文本、无 `tool_calls` | **失败**（A1 退化） |
| fake 输出序列不足 2 轮 | **失败** |
| 第 3 次调用 | **失败**（显式抛出） |
| `tool_call.id` 缺失 / 不匹配 | **失败** |
| 工具结果 ≠ 7 | **失败** |
| `messages` 长度 ≠ 4 | **失败** |
| 缺 `messages` / `llm_calls` 键 | **失败** |
| 注入改写了路由函数 | **失败**（H-1） |
| 注入代码进入 `src/freegraph/` | **失败**（原则 II） |
| `target.py` 被修改 | **失败**（双重基线） |

---

## 7. 退出码

`harness/verification/B25F1/fake_round.py`：

| 码 | 含义 |
|---|---|
| `0` | A1 全过 |
| `1` | 断言失败 |
| `2` | 环境未就绪（缺 `freegraph` / `langchain` / `IPython`） |

最后一行 MUST 打印 `B25F1 fake round: PASS|FAIL`。
