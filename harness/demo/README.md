# harness/demo —— 验收脚本集

本目录是 freegraph 的**验收靶场**。两类脚本，性质完全不同：

| 脚本 | 性质 | 依赖 | 改它需要谁批准 |
|---|---|---|---|
| `target.py` | **只读基准**（LangGraph Quickstart 的机械替换版） | 自带 `langchain.*` | 不可改（宪法原则 III：只换包名、不改脚本） |
| 其余 4 个 | **可演进的验收脚本** | **只 import `freegraph` + 标准库** | 随内核演进，每次 v1 交付前必须全绿 |

## 为什么要拆成「前置 + 后置」

`target.py` 验证的是**生态兼容性**——freegraph 能不能和 LangChain 的模型 / 工具对象
一起跑。它自带 `langchain.*` 导入，因此**无法回答**「内核的图能力本身站不站得住」。

所以另立一组**零第三方依赖**的脚本，只用 `freegraph` 与 Python 标准库：

* 顺带**直接验证**「零第三方运行时依赖」这条对外承诺（立项书 §5.5 / S1）——不必只靠
  「依赖树扫描」这种间接证据；
* 证明内核的图语义**独立成立**，不是因为「蹭了 LangChain 才跑得起来」。

## 脚本清单

| 脚本 | 验证什么 | 覆盖契约 | 对应 Phase |
|---|---|---|---|
| `graph_core.py` | **图运行时内核**（前置用例） | C1–C25（**C20 = `Store` 契约已冻结、v1 不实现**——F17 已砍） | F4P1–F13P1、M1+M2 |
| `agent_loop.py` | **Agent 工具循环**——`target.py` 的零依赖等价物 | C4·C7·C8·C11·C16·C17 | F7P3·F8P1·F8P2·F9P1·F10P1 |
| `visualization.py` | **图导出与可视化**（mermaid / PNG / 流式） | C12–C15·C26 | F8P2·F22P1·F23P1 |
| `acceptance.py` | **人工验收编排器**（自身也 import 并执行 freegraph）：前置自检 + 最小图可执行 + **零出站断言** + 串跑上述三组 + 生成《人工验收记录》 | —— | F25P1 |

执行顺序（**内核在前、兼容在后**）：

```
acceptance(自检+零出站) → graph_core → agent_loop → visualization → target.py
```

## 怎么跑

```bash
python harness/demo/acceptance.py                      # 全部（推荐入口）
python harness/demo/graph_core.py                      # 单组
python harness/demo/acceptance.py --suite core,viz     # 只跑指定组
python harness/demo/acceptance.py --record harness/features/freegraph/manual-verification.md
```

**退出码约定**（CI 好用）：

| 码 | 含义 |
|---|---|
| `0` | PASS |
| `1` | **断言失败**——有契约没兑现 |
| `2` | **环境未就绪**——`freegraph` 还没实现 / 没装 |

> `2` 与 `1` 必须分开：内核还没开工时 CI 应该显示「环境未就绪」而不是「验收失败」。

## 硬断言 vs 软断言

脚本里的检查分两类，输出用不同标记：

* **✔ 硬断言** —— **章程已锁定形态**的检查，失败即判 FAIL。
  依据：§4.3 的 18 项 API 元素、C9 的 `START`/`END` 取值、C10 的 `compile()` 与
  `checkpointer=`/`store=` 关键字、C11 的 `invoke(input, config)` 与完整状态、
  C12 的 7 种 `stream_mode` 名、C13/C14/C15 的 `get_graph`/`draw_mermaid`/`draw_mermaid_png`、
  C16 的 `Command(goto=, update=, resume=)`、C17 的 `__interrupt__`、C18 的 `Send`、
  C22 的 `RunConfig` 四字段、C7 的 list/dict 两种 `path_map`。
* **◌ 软断言** —— **语义由章程规定、但调用形态尚未拍板**的检查，**不判失败**，
  只标注「待锁定」。当前两处：

  | 检查 | 待锁定的东西 | 由谁拍板 |
  |---|---|---|
  | C25 节点别名的调用形态 | `add_node(..., alias=)` 还是别的 | F8P3 |
  | `recursion_limit` 的载体 | dict / `RunConfig` / 其他 | F13P1 |

  **形态一旦拍板，这里的软断言就该升级为硬断言。**

* ✅ **已拍板（2026-11-05）——第三处软断言已关闭**：`interrupt` 恢复**必须依赖
  checkpointer**（内存态恢复不可靠；`interrupt` 的主场景是 time travel，须跨长时间 /
  跨重启可恢复；SQLite 是智能体开发的事实标准，故必须采用 checkpointer）。
  → **恢复路径 MUST NOT 有「不挂 checkpointer 也能恢复」的内存态旁路**；未挂
  checkpointer 时调用恢复 MUST 抛明确异常。
  → 该项的**形态已锁定**，待 **F14P1** 落地（`MemorySaver` 模块路径随之锁定）时，
  在 `graph_core.py` 的 `case_interrupt_resume` 中挂上真实 saver，并把
  `soft(...)` 改为 `check(...)`。**在此之前仍按软断言处理**（不判失败）。

## 断言框架是刻意内联的

每个脚本都自带一份约 40 行的断言框架（`check` / `soft` / `eq` / `section` / `finish`），
**故意不抽公共模块**——这样每个脚本都能**单文件独立运行**，且
「只 import `freegraph` 和标准库」这条约束是**字面成立**的（可被静态扫描直接证明）。

## 尚缺的验收脚本：可诊断性（M3）

**trace / checkpointer / time-travel** 的验收脚本**暂不在本目录**——
它们依赖的 API 形态章程尚未锁定：

| 待锁定的形态 | 依据 |
|---|---|
| `compile(tracer=...)` 注入 `TraceSink` | C23 只说「显式传入才生效」，未说载体 |
| 本地 trace 存储目录的参数名 | F20P1 未说参数名 |
| `MemorySaver` 的模块路径 | F14P1 未定 |
| `update_state(...)` 的签名 | F16P1 未说签名 |

**原则**：*验收脚本与它所验收的能力的 API 形态一起定*——
章程已锁形态的（M1/M2）现在就写；章程未锁形态的（M3）**随定义它的 Phase 一起写**，
否则就是在赌接口长什么样，赌错了要重写一千行。

到 M3 开工时（§5.2 的 F14P1–F20P2），按同样方式补一份 `diagnostics.py`，
届时那四个形态已在各 Phase 的 spec 里锁定，脚本照写即可。

## 与 target.py 的关系

`agent_loop.py` 是 `target.py` 的**零依赖镜像**：两条路径跑的是同一个
tool-calling 循环，**应当给出逐字段一致的最终状态**（`messages` 长度、
`llm_calls` 计数、工具结果）。两者不一致 = 有 bug。

`target.py` 的双跑（CI fake 注入 / 人工真实模型）由立项书 §9.2 驱动，
`acceptance.py` 不代跑它，只在生成的验收记录里留出位置。
