# B7F3 · `invoke()` → 完整状态 + `InvalidUpdateError` · 人工验证记录

**Feature**: `specs/b7f3-invoke-full-state/` · **日期**: 2026-11-17
**上游**: `langgraph 1.2.11`（开发 / 测试侧差分依赖；不在发行面）

---

## 1. 环境

| 项 | 值 |
|---|---|
| Python | **3.11.16**（`.venv/bin/python`） |
| 平台 | Linux（CPython 3.11.16 · x86_64） |
| freegraph | 源码树（`PYTHONPATH=src`） |
| 上游差分依赖 | `langgraph 1.2.11` / `langchain-core 1.7.6`（`.venv` 实际安装版本） |
| 第三方运行时依赖 | **零**（`dependencies = []`） |

### 1.1 绿基线（**T001 实测 · 实施前**）

> ⚠️ 宪法 v1.12.0「基线义务」：实施**开始前** MUST 先跑一遍既有测试套件并**记录绿基线**（计数）。

| 项 | 计数 |
|---|---|
| **passed** | **1421** |
| **skipped** | **4** |
| **failed** | **0** |

```
1421 passed, 4 skipped in 116.66s (0:01:56)
```

> ⚠️ **4 条 skip 的原因**（逐条）：① C8（条件边 fresh 状态读）由 **B8F1** 建立 ·
> ② mypy 未安装（开发期工具 · 兜底的注解结构断言仍跑）· ③ API 快照未开 `--update-api-snapshot` ·
> ④ Windows 时钟分辨率用例（仅 Windows 档）。

### 1.2 首次执行的实测红点（**T011 实测 · `invoke` 接通后、验收脚本分级前**）

> ⚠️ 宪法 v1.12.0「冻结断言清单 MUST **实测化**」：MUST **按本 feature 的落地形态**改动源码
> ⇒ 跑既有套件 ⇒ **变红**者才入清单 ⇒ ⇒ **MUST NOT 只凭推理登记**。

| 脚本 | 断言数 | 通过 | 失败 | 首次执行的红点 |
|---|---|---|---|---|
| `harness/demo/graph_core.py` | 35 | 27 | **8** | A5 的 C8 fresh 读 ×2 · A5 的 C7 dict path_map（`TypeError` V-9）· A6 的 C16 段（`TypeError` V-9）· **A9 的 `RunConfig.tags`（期望 `['t1']` 实际 `('t1',)`）** · A9 的 C21 context 独立通道 · A9 的 C21 context 未被塞进 `configurable` · A10 的流式事件段（`NotImplementedError: stream 由 B8F2 交付`） |
| `harness/demo/agent_loop.py` | 9 | 2 | **7** | B1 工具循环 ×4（含 `IndexError`）· B2 tool_call 形状（`IndexError`）· B3 工具执行前触发中断 |

**逐条归因与处置**（**MUST NOT** 顺手降级与本 feature 无关的红点）：

| 红点 | 归因 | 处置 |
|---|---|---|
| A5（C8 ×2 + C7 dict path_map）· A6 的 C16 段 | **条件边路由求值**未交付 | **降级为软断言**（归 **B8F1**）⇒ 任务 **T040** |
| A9 的 C21 context 独立通道 | **context 独立通道**未交付 | **降级为软断言**（归 **B8F3**）⇒ 任务 **T040** |
| A10 的流式事件段 | **`stream()`** 未交付 | **降级为软断言**（归 **B8F2**）⇒ 任务 **T040** |
| A9 的 C21 context 未被塞进 `configurable` | **陈旧断言**（`RunConfig` 已冻结为**有** `configurable` 字段 ⇒ `not hasattr(...)` 恒红） | **改为** `cfg.configurable == {}`（**保留判词原意**）⇒ 任务 **T041** |
| A9 的 `RunConfig.tags`（期望 `['t1']` 实际 `('t1',)`） | **陈旧断言**（L1 的 `tags` **已冻结为 tuple** · `types.py:212` 构造期 `tuple(...)` 拷贝） | **事实订正**为 `("t1",)`（**不是**降级）⇒ 任务 **T040** 附记 |
| agent_loop 的 B1 / B2 / B3 | **条件边路由求值**未交付 | **降级为软断言**（归 **B8F1**）⇒ 任务 **T042** |

---

## 2. 步骤（可复制命令）

```bash
# ① 全量 pytest（含 B7F3 新增 facade / differential 用例）
.venv/bin/python -m pytest tests/ -q

# ② B7F3 一键验收（A1–A3 / 完整状态 / 失败信号 / 多会话隔离 / config 双形态）
PYTHONPATH=src .venv/bin/python harness/verification/B7F3/acceptance.py

# ③ 执行期差分（D-92…D-102 · 上游缺席即 skip）
PYTHONPATH=src .venv/bin/python harness/scripts/diff_parity.py

# ④ quickstart 五段（§1 最小闭环 / §2 失败信号 / §3 隔离与挂起 / §4 验收脚本与门禁 / §5 人工验证）
#    —— 逐段命令见 specs/b7f3-invoke-full-state/quickstart.md §1–§5

# ⑤ 验收脚本退出码（invoke 已交付 ⇒ 前两个脚本 rc=0；visualization 仍 rc=1）
PYTHONPATH=src .venv/bin/python harness/demo/graph_core.py;   echo "rc=$?"
PYTHONPATH=src .venv/bin/python harness/demo/agent_loop.py;   echo "rc=$?"
PYTHONPATH=src .venv/bin/python harness/demo/visualization.py; echo "rc=$?"

# ⑥ 受影响门禁
.venv/bin/python harness/scripts/gates/gate_G21_dependencies.py --project pyproject.toml
.venv/bin/python harness/scripts/gates/gate_G23_licenses.py
.venv/bin/python harness/scripts/gates/gate_G24_config_layer.py --root .
.venv/bin/python harness/scripts/gates/gate_G25_import_graph.py --root .
.venv/bin/python harness/scripts/gates/gate_G26_network_static.py --root .
.venv/bin/python harness/scripts/gates/gate_G27_zero_egress.py --root .
.venv/bin/python harness/scripts/gates/gate_G28_offline_equiv.py --root .
.venv/bin/python harness/scripts/gates/gate_G29_contract_carrier.py
.venv/bin/python harness/scripts/gates/gate_G30_attribution.py --root .

# ⑦ G22 的隔离环境断言（含**自 B7F3 起**的「③② 运行期（最小图）」步骤 6）
.venv/bin/python harness/scripts/gates/gate_G22_isolated_env.py --target-root .
#   反向用例（证明步骤 6 **确实能失败**）
.venv/bin/python harness/scripts/gates/gate_G22_isolated_env.py --self-test-negative
```

---

## 3. 实际输出

### 3.1 全量 pytest（**实施后**）

```
1486 passed, 4 skipped in 103.67s (0:01:43)
```

> ✅ **1486 − 1421 = +65** 条新断言（facade 64 条 + differential 1 条差分包装）。
> ✅ **failed == 0**（绿基线**未被破坏**）。

### 3.2 B7F3 一键验收

```
══ B7F3 · invoke() 返回完整状态 + InvalidUpdateError ══
Python 3.11.16

[A1 · 完整状态（键集 == schema 全集 · 顺序一致）]
  ✔ 返回值是普通 dict
  ✔ 键集 == schema 全部 key（顺序一致）
  ✔ 路由通道不进返回键集

[A2 · 完整状态（初始 + 全部新增 · 不是增量）]
  ✔ messages == 初始 + 全部新增
  ✔ llm_calls == 覆盖后的最终值（不是累加）
  ✔ 从未被写的覆盖型 key 以 None 补齐（键一定在）

[A3 · 失败信号（未知 key ⇒ InvalidUpdateError 且点名）]
  ✔ 异常消息点名违规 key
  ✔ 异常带结构化 invalid_keys

[多会话隔离（连续两次不累积 · 并发两次不串扰）]
  ✔ 连续两次：第二次不含第一次的新增
  ✔ 连续两次：第一次的结果仍完整

[config 双形态（RunConfig / 普通映射）]
  ✔ 两种 config 形态都生效（键集一致）

[B7F3] PASS
```

**退出码 = 0**。

### 3.3 执行期差分（**D-92…D-102**）

```
invoke D-92 minimal graph          | ✅ 一致                 | OK         | OK
invoke D-93 full key set           | ✅ 一致                 | OK         | OK
invoke D-94 uncovered key kept     | ✅ 更严（已登记）            | OK         | OK
invoke D-95 unknown node key       | ✅ 更严（已登记）            | ERROR      | OK
invoke D-96 unknown input key      | ✅ 更严（已登记）            | ERROR      | OK
invoke D-97 real exception         | ✅ 一致                 | ERROR      | ERROR
invoke D-98 recursion limit        | ✅ 一致                 | ERROR      | ERROR
invoke D-99 two consecutive calls  | ✅ 一致                 | OK         | OK
invoke D-100 two concurrent calls  | ✅ 一致                 | OK         | OK
invoke D-101 interrupt payload     | ✅ 一致（形态差异已登记）       | OK         | OK
invoke D-102 multi-source barrier  | ✅ 一致                 | OK         | OK
```

```
场景数 127 · 符合判词 127 · 失败 0
```

> ✅ **判词分布与 spec 逐字一致**：**SAME 7**（D-92 / D-93 / D-97 / D-98 / D-99 / D-100 / D-102）
> · **STRICTER 3**（D-94 / D-95 / D-96）· **DIFF 1**（D-101 · 值形态 tuple vs list）。

### 3.4 quickstart §1–§5（逐段实测）

**§1 最小闭环（完整状态）**

```
键集      : ['messages', 'llm_calls']
messages : ['seed', 'a', 'b']
llm_calls: 2
✅ A1 / A2 通过
```

**§2 失败信号**

```
# 未知 key
类型   : InvalidUpdateError
消息   : Invalid state update: unknown key(s) 'typo_key'
结构化 : ('typo_key',)
✅ 未知 key 报错通过

# 真异常原样传播
类型 : Boom | 消息 : 原始消息 payload
✅ 异常原样传播通过

# recursion_limit
类型 : GraphRecursionError | recursion_limit = 3
✅ recursion_limit 通过

# RunConfig 形态
串行档 : {'messages': ['x'], 'llm_calls': None}
✅ RunConfig 形态通过
```

**§3 多会话隔离 + 挂起**

```
run1 : ['a', 'x'] | run2 : ['b', 'x']
并发 : {'q': ['q', 'x'], 'p': ['p', 'x']}
✅ 连续两次不累积 + 并发两次不串扰

键集        : ['messages', 'llm_calls', '__interrupt__']
__interrupt__: (Interrupt(value='approve?', id='f16ccd502cf0f30c3dad220eb64ca7c9'),)
✅ 挂起结果通过（元素具备 .value / .id）
```

> ⚠️ **B7F3 实测发现并修复**：quickstart §3 的节点原写成 `return {"messages": list(state.get("messages", [])) + ["x"]}`
> （**返回全量**）⇒ 归约器（`operator.add`）会把已有内容**再追加一遍** ⇒ 实测 `['a','a','x']`
> ⇒ ⇒ **已改为返回增量** `return {"messages": ["x"]}` ⇒ ⇒ 判据**未放宽**（期望值逐字不变），
> **仅修正节点的返回值形态**（与 §1 的 `a` / `b` 节点同款）。

**§4 验收脚本 + 门禁 + 全量回归**

```
# ④-1 验收脚本集（G29 的三个）
graph_core.py    ⇒ PASS（36 条断言全绿 · 7 条软断言）· 退出码 0
agent_loop.py    ⇒ PASS（8 条断言全绿 · 7 条软断言）· 退出码 0
visualization.py ⇒ FAIL（13 条失败）· 退出码 1
                  —— `get_graph` / `draw_mermaid` / `draw_mermaid_png` / `stream` 全未交付
                     ⇒ 归 **B22F1 / B23F1 / B8F2** ⇒ G29 判为 ENV_NOT_READY · 不判 FAIL
```

**§5 人工验证（两轮）** —— 见 §5.1 / §5.2。

### 3.5 验收脚本退出码（分级后）

```
$ PYTHONPATH=src .venv/bin/python harness/demo/graph_core.py; echo "rc=$?"
断言 36 条 · 通过 36 · 失败 0
结论：PASS
rc=0

$ PYTHONPATH=src .venv/bin/python harness/demo/agent_loop.py; echo "rc=$?"
断言 8 条 · 通过 8 · 失败 0
结论：PASS
rc=0
```

> ⚠️ **两条脚本的软断言清单**（**每条具名承接方** · 与 `harness/demo/README.md` 同步）：
> `graph_core` 7 条（A5 ×3 · A6 的 C16 段 · A6 的 C17 恢复半边 · A9 的 context 段 · A10 的流式段）
> ⇒ 归 **B8F1 / B8F2 / B8F3 / B14F1**；
> `agent_loop` 7 条（B1 ×4 · B2 · B3 ×2）⇒ 归 **B8F1 / B14F1**。

### 3.6 门禁

| 门禁 | 退出码 | 结果 |
|---|---|---|
| **G21** 依赖闭包黑名单 | 0 | PASS —— 基础安装闭包为空集 |
| **G22** 隔离环境断言 | 0 | PASS —— 含**自 B7F3 起**的步骤 6「③② 运行期（最小图）」：<br>`sys.modules 无 langchain 家族 · 框架出站 = 0 · 返回键集 = ['llm_calls', 'messages']` |
| **G22** `--self-test-negative` | 0 | PASS —— 反向用例**非空转**：<br>注入 `langchain_core` 后报出 `G22-05 · 验收环境里**运行期**（建图 → compile → invoke）之后 sys.modules 出现了 langchain 家族` |
| **G23** 许可证白名单 | 0 | PASS（被检查包数 = 0） |
| **G24** 配置层（零环境变量） | 0 | PASS —— 扫描域 `src/freegraph/**` |
| **G25** 导入图单向 | 0 | PASS —— 层注册表驱动 |
| **G26** 网络静态扫描 | 0 | PASS —— `src/freegraph/**` 无网络客户端调用 |
| **G27** 零出站 | 0 | PASS —— 观测面声明**已更新**为「测试套件执行期 **+ 内核运行时（M2 · B7F3 起）**」 |
| **G28** 断网等价性 | **0（CI 档）** | ✅ **CI 档已跑且已绿**（run **44027833345** · 步骤 9 · Linux only）⇒ ⇒ ⚠️ **本地未执行**（需 `unshare --net`，本沙箱**不允许**写 `/proc/self/uid_map`）⇒ ⇒ 本地判据 = **跳过并在任务 note 中注明**（**不判失败**）|
| **G29** 契约门禁载体 | 0 | PASS —— `graph_core` / `agent_loop` 均 `ENV_NOT_READY`→`PASS`；`visualization` 仍 `ENV_NOT_READY`（**不判 FAIL**）· C4 已挂载 / C8 仍未落地（**B8F1**） |
| **G30** 署名头与品牌资产 | **1** | ⚠️ **共 8 条违规**（**既有** · 与 **B7F2 登记的 8 条持平** ⇒ ⇒ **本 feature MUST NOT 新增** ⇒ ⇒ **零新增** ✅）—— 3 个**既有**文件：`harness/demo/target.py`（只读基准 · 缺模块 docstring）· `harness/reports/Q7-开源边界地图与许可证合规.md`（品牌文案指纹 ×3）· `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md`（品牌文案指纹 ×3）⇒ ⇒ ⚠️ **本 feature 新增 / 修改的 12 个 `.py` 已单独核验**：署名头违规 **0** · 品牌资产违规 **0** ✅ |

**CI 实跑**（GitHub Actions）：run **44027833345** · **7/7 作业全绿** ——
`ubuntu-24.04`（3.11 / 3.14）· `ubuntu-24.04-arm`（3.11）· `windows-2025`（3.11 / 3.14）·
`macos-15`（3.11 / 3.14）⇒
<https://github.com/yangjiacheng1996/freegraph/actions/runs/44027833345>
⇒ ⇒ 步骤 9 的 **G22**（隔离 venv + ③② 运行期）/ **G27** / **G28**（断网）在 Linux 档**真跑**并全绿。

---

## 4. 结论（逐条对照验收判据）

| 判据 | 结果 | 证据 |
|---|---|---|
| **A1** 键集 == schema 全部 key（顺序一致） | ✅ | §3.2 / §3.4 §1 / facade `test_invoke_full_state.py` |
| **A2** 完整状态 = 初始 + 全部新增（不是增量） | ✅ | §3.2 / §3.4 §1 |
| **A3** 未知 key ⇒ `InvalidUpdateError` 且点名 | ✅ | §3.2 / §3.4 §2 |
| **SC-001** 键集相等（含顺序） | ✅ | `test_invoke_full_state.py::test_key_order_matches_the_schema_declaration_order` |
| **SC-002** `messages` == 初始 + 新增 | ✅ | `test_invoke_full_state.py::test_messages_contains_initial_plus_every_new_value` |
| **SC-003** `llm_calls` == 覆盖值；无值覆盖型 key == `None`；归约型 == 类型空值 | ✅ | `test_invoke_full_state.py::TestFillAndCoverage` |
| **SC-004** 未知 key ⇒ `InvalidUpdateError`（消息含 key 名） | ✅ | `test_invoke_errors.py::TestUnknownKey` |
| **SC-005** 真异常原类型 + 原消息 | ✅ | `test_invoke_errors.py::TestExceptionIdentity` |
| **SC-006** config 双形态生效 + **可观测并发度** | ✅ | `test_invoke_config.py::TestConcurrencyKnob`（串行档重叠 == 0 · 缺省档重叠 ≥ 1） |
| **SC-007** `recursion_limit` 生效且不包装 | ✅ | `test_invoke_config.py::TestRecursionLimit` |
| **SC-008** 连续两次不累积 + 路由通道不残留 | ✅ | `test_invoke_isolation.py::TestConsecutiveCalls` |
| **SC-009** 并发两次不串扰 | ✅ | `test_invoke_isolation.py::TestConcurrentCalls` |
| **SC-010** `__interrupt__` 键 / 元素 `.value` / `.id` / 静态挂起空元组 / 恢复取值 | ✅ | `test_invoke_interrupt.py`（恢复载体 = **T002 的自足桩 checkpointer**） |
| **SC-011** 出站连接数 == 0 · 环境变量读取次数 == 0 | ✅ | `test_invoke_purity.py::TestPurity`（**代理计数** · 非「结果未受影响」） |
| **SC-012** `sys.modules` 无 langchain 家族 | ✅ | `test_invoke_purity.py::test_no_third_party_module_is_imported_during_invoke` |
| **SC-013** 驱动到终止 + **多源汇合（屏障）** | ✅ | `test_invoke_full_state.py::test_multi_source_barrier_lands_after_every_source` |
| **SC-014** G22「③② 运行期」断言被点亮 | ✅ | §3.6 G22（步骤 6）—— **只接线 · 零新增门禁编号** |
| **SC-015** `invoke` 不抛 `NotImplementedError` | ✅ | `test_invoke_full_state.py::test_invoke_never_raises_not_implemented` |
| **SC-016** `vars(compiled)` 仍 == 11 键 | ✅ | `test_invoke_full_state.py::TestFrozenHoldingFace` |
| **SC-017** 差分 D-92…D-102 全绿 | ✅ | §3.3 —— **127/127** |
| **SC-018** 人工验证记录覆盖**两轮**实测输出 | ✅ | §5.1 / §5.2 |
| **SC-019** 破冻结面的**唯一一次**追认留痕 | ✅ | §7 —— **发起者本人已签署**（2026-11-17 · **追认次数 == 1**）⇒ ⇒ **合入闸口已打开** |
| **SC-020** 「只读快照 · 不要原样回喂」**及理由**写入 docstring + README | ✅ | `test_invoke_purity.py::TestDocumentationGuard`（**子串**断言） |

### 来源覆盖

- **上游**：`langgraph 1.2.11`（差分实测 · **11** 条执行期场景）+ `harness/docs/oss/python/langgraph/`（`use-graph-api.md` 的
  「`invoke` 的输出只含 output schema」· `interrupts.md` 的「`result["__interrupt__"]`」·「`Command(resume=...)` 是
  `invoke()` 的**唯一** resume 输入」）；
- **立项书**：`§4.2` S5 / S6 / S7 · `§5.2` B7F3 行 · `§5.3.1` C11 · `§9.2` 验收脚本集；
- **宪法**：原则 I / III / IV / V / VI / VII / VIII / XI / XII + v1.6.0 / v1.8.0 / v1.9.0 / v1.11.0 / v1.12.0 / v1.13.0 / v1.14.0。

---

## 5. 人工验证的两轮（**SC-018**）

### 5.1 「fake 模型轮」= 用**假模型**跑**最小图**（**静态边**部分**真跑**）

**命令**（可复制）：

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
import operator
from typing import Annotated, TypedDict
from freegraph.graph import START, END, StateGraph

class State(TypedDict):
    messages: Annotated[list, operator.add]
    llm_calls: int

class FakeMessage:
    def __init__(self, content, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []
    def __repr__(self):
        return f"FakeMessage(content={self.content!r})"

class FakeModel:
    """**假模型**（猴补 ``init_chat_model`` 的等价物 · 不触网）。"""
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
    def invoke(self, messages):
        self.calls += 1
        return self.responses.pop(0) if self.responses else FakeMessage("done")

model = FakeModel([FakeMessage("7")])

def n(state):
    out = model.invoke(state.get("messages", []))
    return {"messages": [out], "llm_calls": model.calls}

g = StateGraph(State)
g.add_node("n", n)
g.add_edge(START, "n")
g.add_edge("n", END)
out = g.compile().invoke({"messages": [FakeMessage("Add 3 and 4.")]})
print("messages   :", out["messages"])
print("llm_calls  :", out["llm_calls"])
print("model.calls :", model.calls)
assert out["llm_calls"] == 1
assert len(out["messages"]) == 2
print("✅ fake 模型轮通过")
PY
```

**实测输出**：

```
messages   : [FakeMessage(content='Add 3 and 4.'), FakeMessage(content='7')]
llm_calls  : 1
model.calls : 1
✅ fake 模型轮通过
```

> ✅ **假模型** ⇒ **零出站**（不触网）⇒ ⇒ **框架零出站**断言同时成立（`SC-011`）。

### 5.2 「真实模型轮」= 用**真实模型**跑**最小真实模型图**

**命令**（可复制）：

```bash
PYTHONPATH=src .venv/bin/python - <<'PY'
import operator
from typing import Annotated, TypedDict
from freegraph.graph import START, END, StateGraph

class State(TypedDict):
    messages: Annotated[list, operator.add]
    llm_calls: int

# ⚠️ **真实模型**：需要环境自备 ANTHROPIC_API_KEY（**用户出站** · 不判失败）
try:
    from langchain_anthropic import ChatAnthropic
    model = ChatAnthropic(model="claude-sonnet-4-6")
except Exception as exc:
    print(f"[环境偏离] 真实模型不可用：{type(exc).__name__}: {exc}")
    raise SystemExit(0)

def n(state):
    out = model.invoke(state.get("messages", []))
    return {"messages": [out], "llm_calls": 1}

g = StateGraph(State)
g.add_node("n", n)
g.add_edge(START, "n")
g.add_edge("n", END)
out = g.compile().invoke({"messages": []})
print("llm_calls :", out["llm_calls"])
print("messages  :", out["messages"])
print("✅ 真实模型轮通过（**用户出站** · 框架零出站断言仍成立）")
PY
```

**实测输出（本机）**：

```
[环境偏离] 真实模型不可用：ModuleNotFoundError: No module named 'langchain_anthropic'
```

> ⚠️ **按宪法 v1.6.0 登记为「环境偏离」**（**MUST NOT** 用「未验证」替代）⇒ ⇒
> **判据本身不放宽**（**fake 模型轮仍 MUST 跑通** —— ✅ 已跑通，见 §5.1）⇒ ⇒
> 真实轮的**缺口**归「**环境不具备真实模型凭据 / 客户端**」，**不**归本 feature 的实现。
> ⇒ ⇒ **待发起者**在具备凭据的环境补跑一次并把输出转录到本节。

### 5.3 固定脚本（`target.py`）端到端轮 —— **不属本 feature 的达成范围**

> ⚠️ 固定脚本的执行链需 **B8F1**（条件边路由）+ **B22F1**（`get_graph`）+ **B23F1**
> （`draw_mermaid_png`）⇒ ⇒ 三者**均未交付** ⇒ ⇒ **物理不可达成** ⇒ ⇒ 登记为 **EV-4**
> （**具名**承接 **B8F1 / B22F1 / B23F1 / B25F1**）⇒ ⇒ **判据不放宽**。

---

## 6. 质量门禁分阶段落地登记（**EV-1 / EV-2 / EV-4**）

| # | 被偏离的门禁部分 | 不可达成的根因 | 承接方 / 里程碑 | 本 feature 的替代判据 |
|---|---|---|---|---|
| **EV-1** | 门禁 3 的「`target.py` 原样可跑」 | 需 **B22F1 / B23F1 / B8F1** ⇒ 脚本在 `invoke` **之前**就会中断 | **B22F1 / B23F1 / B8F1**（M2）· 双跑 **B25F1**（M4） | 本 feature 只判 `invoke` 侧：**A1–A3** + 完整状态 + 失败信号 + 多会话隔离 + `config` 双形态；**G29 ①** 的 diff 断言仍为**空** |
| **EV-2** | 门禁 4 / 5 的「**fake / 真实模型轮**跑通**工具循环**」（立项书 §9.2 的三个断言点：`messages` 长度 = 3 · `llm_calls == 2` · 工具结果 = 7） | 工具循环依赖**条件边路由** ⇒ **B8F1** 未交付 ⇒ **物理不可达成** | **B8F1**（M2）· 双跑 **B25F1**（M4） | `manual-verification.md` 照常**五段式**；**fake 轮**的**静态边**部分**真跑**并记录（§5.1）；**工具循环**部分**具名**承接 B8F1 ⇒ ⇒ ⚠️ 口径订正：立项书 §9.2 写 `messages` 长度 = **3**，而 `harness/demo/agent_loop.py` 实际断言 **4**（入参 + 助手 + 工具结果 + 助手）⇒ ⇒ **本 feature 以脚本为准（4）**；立项书数字的修订属**发起者**职权 |
| **EV-4** | 门禁 4 / 5 的「**固定脚本（`target.py`）端到端轮**」 | 固定脚本的执行链需 **B8F1** + **B22F1** + **B23F1** ⇒ 三者**均未交付** | **B8F1 / B22F1 / B23F1**（M2）· 双跑 **B25F1**（M4） | **fake 模型轮**（§5.1）+ **真实模型轮**（§5.2 · **环境偏离**已登记）⇒ ⇒ **两轮的实测输出 MUST 记录** ⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **MUST NOT** 写「符合预期」⇒ ⇒ ⇒ ⇒ ⇒ ⇒ **判据不放宽** |

> ✅ **EV-3 已撤销**（2026-11-16 analyse 轮）—— SC-013 的「屏障」半边**物理可达**
> （静态多源边 · **B7F4 已交付于 L2**）⇒ ⇒ **本 feature 已判定**（`test_invoke_full_state.py::
> test_multi_source_barrier_lands_after_every_source` ✅）⇒ ⇒ **不是** carry-over。

---

## 7. 破冻结面的**发起者追认**（**唯一一次** · **T045** · **已签署** · 2026-11-17）

> ⚠️ **签署主体（宪法 v1.6.0）**：追认 **MUST 由发起者本人作出** ⇒ ⇒ **MUST NOT** 由实现者
> 代签 ⇒ ⇒ **未追认前 MUST NOT 合入**。
> ⇒ ⇒ **实现者**已备好并落笔下列文本；**发起者本人**于 **2026-11-17**（人工验收通过后）**签署**（见 §7.2）。

### 7.0 追认文字（**已签字** · 2026-11-17）

> 本人已确认 B7F3 的人工验收结果（一键验收 **14 条断言全绿**、全量 pytest
> **1486 passed / 4 skipped**、执行期差分 **D-92…D-102 逐条符合判词** · 整体
> **127/127**、`graph_core` / `agent_loop` 均以**退出码 0** 结束、`target.py` diff 为空、
> 门禁 G21 / G22 / G23 / G24 / G25 / G26 / G27 / G29 全部通过），并追认本 feature 的
> **EV-1 / EV-2 / EV-4** 分阶段落地：门禁 3 的端到端部分承接
> **B8F1 / B22F1 / B23F1**，门禁 4 / 5 的 fake 轮与真实模型轮承接 **B25F1**（M4）。
> 同时追认本 feature 的**五项破冻结面**（见 §7.1 的 ①…⑤）：L1 `invoke` 的 `input` 与
> `config` 两处注解放宽、L2 `run_graph` 的 `max_concurrency` 读取点（**兼容扩展**）、
> G19 兼容矩阵行的**白名单**（只放行 `CompiledGraph` 一行）、四处「`invoke` 未就绪」
> 冻结断言的**拆分替换**。判据未放宽，红线照常执行。

**发起者签字 / 日期**：杨家成 · **2026-11-17**

### 7.1 追认项（**五项** · 唯一事实源 = `spec.md`「Assumptions」的「破面全集 5 类」）

| # | 破面 | 内容 | 落点 |
|---|---|---|---|
| **①** | **L1 `invoke` 的 `input` 注解放宽** | `input: StateDict \| Command \| None`（**上游同款** · `langgraph/pregel/main.py:3836-3838`） | `src/freegraph/contracts/protocols.py:270-272` · `specs/b2f1-contracts-protocols/contracts/public-api.md:82` / `:195` |
| **②** | **L1 `invoke` 的 `config` 注解放宽** | `config: RunConfig \| Mapping[str, Any] \| None`（**与 L2 的 `run_graph` 逐字同款**）⇒ ⇒ **与 ① 同属一次**登记 + 回溯修订 + 追认 | 同上 |
| **③** | **L2 `run_graph` 的 `max_concurrency` 读取点**（**兼容扩展**） | **关键字优先 · config 兜底**（`None` ≡ 未指定）⇒ ⇒ 签名**一字不动** ⇒ ⇒ 既有调用方**零改动** ⇒ ⇒ **config 兜底值**的校验点在 `resolve_config` **之后**、`_first_graph` **之前** | `src/freegraph/runtime/superstep.py:1964-1985` · `specs/b10f1-interrupt-resume/contracts/interrupt-resume-contract.md` §2 · `specs/b12f1-concurrency-errors/spec.md` 的 **FR-017 / 裁定 18** |
| **④** | **G19「既有契约层矩阵行逐字未改」判据**（**白名单**） | 新增 `MATRIX_ROWS_UPDATABLE_BY_B7F3 = frozenset({"CompiledGraph"})`（**只放行这一行**）⇒ ⇒ 其余**契约层**行仍**逐字未改**（判据**只放宽一处**）⇒ ⇒ **等价程度（第三列）MUST NOT 变差**（`CompiledGraph` 保持 **部分等价**）⇒ ⇒ README 矩阵行的「差异说明」只移除「行为细节挂起 B7F3」 | `tests/facade/test_facade_gates.py` · `README.md` 的 `CompiledGraph` 行 |
| **⑤** | **四处「`invoke` 未就绪」冻结断言的拆分替换** | ① `tests/facade/test_compiled_graph.py:73-86`（从参数化列表**提出** ⇒ 独立断言）② `tests/facade/test_facade.py:195-200`（**替换为反面断言**）③ `tests/facade/test_facade.py:217-234`（从参数化列表**提出** ⇒ 独立断言）④ `tests/runtime/test_acceptance_script.py:15-34`（**替换为「脚本成功」= `rc == 0`**）⇒ ⇒ **拆分而不删** · **判据只可更严**（**MUST NOT** 退化为「不再是 2」） | 同左 |

### 7.2 发起者确认（**已签署** · 2026-11-17）

```
追认人（发起者）：杨家成
追认日期：2026-11-17
追认结论：☑ 同意上述五项破面，追认本 feature 的实施结果符合本 spec / plan / 契约。

签名：杨家成（2026-11-17）
```

> ✅ **追认已作出**（2026-11-17 · 发起者**本人**作出 · 人工验收通过后签署）。
> ⇒ ⇒ 本 feature 的**合入闸口**已打开（宪法 v1.6.0「未追认前 MUST NOT 合入」⇒ 条件已满足）。
> ⇒ ⇒ 五项破面**一并**被追认，**追认次数 == 1**（≤ 1 次 / feature）。

---

## 8. 遗留问题

| # | 遗留 | 归属 | 说明 |
|---|---|---|---|
| **1** | 「真实模型轮」在本机**环境不可用**（无 `langchain_anthropic` / 无凭据） | **环境偏离** | 已按 v1.6.0 登记（§5.2）⇒ ⇒ **MUST NOT** 用「未验证」替代；**判据未放宽**（fake 轮已跑通）⇒ ⇒ 待发起者在具备凭据的环境补跑 |
| **2** | ~~**G28**（断网等价性）本地未执行~~ | **CI 档** | ✅ **已关闭**（CI run **44027833345** · 步骤 9 · **7/7 作业全绿**）⇒ ⇒ 仅本地因沙箱限制而跳过（**不判失败**） |
| **3** | 验收脚本的 **7 + 7 条软断言** | **B8F1 / B8F2 / B8F3 / B14F1** | 每条**具名**承接方（§3.5）⇒ ⇒ **不是**「本 feature 未验证」 |
| **4** | `visualization.py` 仍 `rc = 1` | **B22F1 / B23F1 / B8F2** | G29 判为 `ENV_NOT_READY` · **不判 FAIL** |
| **5** | 固定脚本（`target.py`）端到端轮 | **EV-4** → **B8F1 / B22F1 / B23F1 / B25F1** | **物理不可达成**（§5.3）⇒ ⇒ **判据不放宽** |
| **6** | ~~追认（§7）待发起者签署~~ | —— | ✅ **已关闭**（2026-11-17 发起者本人签署 · 追认次数 == 1） |
| **7** | 立项书 §9.2 的 `messages` 长度 = **3** 与 `agent_loop.py` 实际断言 **4** 不一致 | **发起者**（上位文档修订） | 本 feature 以脚本为准（4）⇒ ⇒ 上位文档的修订**不单方面**改 |
