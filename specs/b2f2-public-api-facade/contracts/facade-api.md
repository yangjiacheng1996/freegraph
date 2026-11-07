<!-- authority: facade -->

# 门面导出面清单（facade-api.md）

**功能块**: B2F2 · 公开 API 门面 `freegraph/graph.py` + API 签名快照 · **Date**: 2026-11-07
**权威来源**: [spec.md](../spec.md)（FR-001…FR-019 · SC-001…SC-018 · **12 条裁定 + 12 条澄清问答 Q1–Q12**）·
[data-model.md](../data-model.md)（§2 逐符号冻结规格）· [research.md](../research.md)（D-01…D-23）·
[architecture-gates.md](./architecture-gates.md)（门禁 G14–G20）
**契约性质**: **冻结面** —— 本文件 §0 的符号清单一经落地，后续 30 个 feature 全部引用

> **📌 为什么本文件不叫 `public-api.md`**：既有门禁 **G12** 扫的是 `**/public-api.md` 并读取
> `<!-- authority: yes|no -->` 标记，断言「自称权威的公开符号清单文件数 == 1」。
> 若本 feature 也产出 `public-api.md` 并标 `authority: yes`，**G12 恒红**。
> 故本文件用 `facade-api.md` + `<!-- authority: facade -->` 标记（**该标记不参与 G12 判定**——
> G12 只扫 `public-api.md` 这一个文件名）。
>
> **两个权威各管一面，不构成重复**：
>
> | 面 | 权威 | 性质 |
> |---|---|---|
> | **契约层的 18 个公开符号** | `specs/b2f1-contracts-protocols/contracts/public-api.md`（既有，G12 认定的那一个） | 手写清单 |
> | **门面的 7 个导出符号** | **本文件 §0** | 手写清单（**导出面清单的唯一手写权威** · 裁定 10） |
> | **门面每个符号的完整签名** | `public-api-snapshot.txt`（**机器生成**） | 生成记录（**唯一入库 / 比对点** · 裁定 10） |
>
> **层归属（2026-11-07 发起者裁定）**：门面是**跨层单元**（层 =「—」）——
> 它的导出面按定义横跨 **L1–L3**（`Command` / `RunConfig` 属 L1 契约层 ·
> `Send` / `interrupt` 属 L2 执行内核层 · `StateGraph` 属 L3 图定义层），
> 故它是 **ARCH-1 的唯一例外**（可 import L1–L3，仍**不得** import L4 持久化 / L5 可观测）。
> 例外条款登记于**立项书 §5.1 的 ARCH-1 条目**与 **§5.2 的 B2F2 行**（层列 →「—」、
> 跨层列 →`✔（公开 API）`）。

---

## 0. 门面导出面（**恰 7 个** · 手动维护点）

```python
from freegraph.graph import (
    # ── 门面自有的 5 个（本 feature 冻结）──
    StateGraph,             # 构建器外壳（构造可成功 · 行为在 B6F1 / B7F2）
    START,                  # 常量 '__start__'（C9）
    END,                    # 常量 '__end__'（C9）
    Send,                   # 原语类型（不可变记录 · 行为在 B11F1）
    interrupt,              # 原语函数（未接线 · 行为在 B10F1）
    # ── 契约层转出的 2 个（原样转出 · 形状权威仍是 contracts/public-api.md）──
    Command,                # 命令原语（行为在 B9F1）
    RunConfig,              # 运行配置（C22 · 行为在 B8F3）
)
```

**恰好 7 个**。不多、不少：

> **本节是**门面**导出面清单**的唯一**手写**维护点** —— spec / plan / tasks / `data-model.md` /
> `README.md` 兼容矩阵中的同款清单均以本节为准（spec FR-002）。
> **「调用签名」不在本节的管辖范围** —— 它由**机器生成**的 `public-api-snapshot.txt` 记录
> （**唯一入库 / 比对点** · 裁定 10）。两者**各管一面、不重复**。

- `__all__` **集合相等**断言为这 7 个名字（**两处口径同时成立**：见门禁 **G15**）。
- 门面模块内**所有不以下划线开头的名字** MUST **恰为**这 7 个（抓「导出了但没进 `__all__`」）。
- `CompiledGraph` / `Graph` / `Node` / `Edge` / `Span` / `TraceQuery` **MUST NOT** 出现在门面导出面
  （它们属契约层，由 `freegraph.contracts` 进入）。
- `draw_mermaid` / `draw_mermaid_png` **MUST NOT** 出现在门面导出面（属 `Graph` 对象 · B22F1 / B23F1）。
- `import freegraph.graph` **MUST NOT** 连带加载 `freegraph.runtime` / `freegraph.persistence` /
  `freegraph.observability`（门面不横向依赖 L4 / L5 · 门禁 G18）。

### §0 的解析规则（门禁 G15 / G16 的期望值来源）

从上面的 `python` 代码块中提取符号名：

1. 只取 **`from ... import (`** 与其配对 `)` **之间**的行；
2. **跳过**以 `#` 开头的**注释行**（含缩进注释行）；
3. 每行取**第一个逗号之前**的标识符（`strip()` 后）；空行跳过；
4. 结果为**集合**（顺序不作判据 —— 与 B2F1 的 G7 同口径）。

> **为何期望值来自本文件而不是快照文件**：若从**生成的**快照解析期望值，门禁就成了
> 「代码 → 快照 → 快照 vs 代码」的**循环论证**，任何漂移都抓不到（research D-07）。

---

## 1. 逐符号速查

| 符号 | 类别 | 定义位置 | 契约条目 | 行为归属 | 转出？ |
|---|---|---|---|---|---|
| `StateGraph` | class | `freegraph._stategraph` | C1 / C9 / C10 / C25 | **B6F1**（构建）/ **B7F2**（编译） | 否 |
| `START` | constant | `freegraph.graph` | **C9** | — | 否 |
| `END` | constant | `freegraph.graph` | **C9** | — | 否 |
| `Send` | class | `freegraph._primitives` | **C18** | **B11F1** | 否 |
| `interrupt` | function | `freegraph._primitives` | **C17** | **B10F1** | 否 |
| `Command` | class | `freegraph.contracts.types` | **C16** | **B9F1** | **是**（原样转出） |
| `RunConfig` | class | `freegraph.contracts.types` | **C22** / C21 | **B8F3** | **是**（原样转出） |

**转出的含义**（FR-004）：`freegraph.graph.Command is freegraph.contracts.Command` ⇒ **True**
（**同一对象**，非副本 / 非子类 / 非包装）；`RunConfig` 同理。门面**不得**改动其字段清单。

**ARCH-3 的逐符号判定**（「跨层只经由 `Protocol` + 纯数据类」）：

| 符号 | 跨层交互形态 | 判定 |
|---|---|---|
| `Command` / `RunConfig` | 契约层**纯数据类**（B1F1 冻结） | ✅ 符合 |
| `StateGraph` | **构建器**（不参与跨层交互；`compile()` 的返回类型是**协议** `CompiledGraph`） | ✅ 符合 |
| `Send` | **纯载荷型数据类**——`arg` 装的是**用户载荷**，**不是**跨层契约载体；它只在 L2 / L3 内部流转 | ✅ 符合（**显式登记**：不是「跨层契约」的一部分） |

---

## 2. 冻结的调用形态（逐字）

> 完整签名见 [`data-model.md`](../data-model.md) §2.1；此处为**速查**。
>
> **⚠️ 参数名的冻结口径（2026-11-07 复核澄清）**：下表是 **freegraph 侧**的**冻结名**
> （`schema` / `name` / `fn` / `src` / `dst` / `path_fn` / `path_map`），**逐字对齐宪法原则 III
> 第 2–5 项**。立项书 §4.3「freegraph 义务」列里出现的 `node` / `action` / `start_key` /
> `end_key` / `source` / `path` 是**上游 LangGraph 的参数名**（该列描述的是上游形状），
> **不是** freegraph 的冻结面 —— 两者**不冲突**，差异登记在兼容矩阵的 `StateGraph` 行。

| 调用 | 形态 | 依据 |
|---|---|---|
| `StateGraph(schema)` | **恰一个**必填位置参数，参数名 `schema` | 宪法原则 III 第 2 项 · 裁定 4 |
| `StateGraph.add_node(name, fn, *, alias=None)` | 位置 `(str, Callable)` + 关键字 `alias`（**keyword-only**） | 宪法原则 III 第 3 项 · C25 |
| `StateGraph.add_edge(src, dst)` | `(str \| list[str], str)`，返回注解 `Self`（链式语义） | 宪法原则 III 第 4 项 · 裁定 5 |
| `StateGraph.add_conditional_edges(src, path_fn, path_map)` | `path_map` **同时支持 list 与 dict**；**无缺省值** | 宪法原则 III 第 5 项 · C7 |
| `StateGraph.compile(*, checkpointer=None, store=None)` | **无参可调用** + 两个 **keyword-only** 可选关键字 | 裁定 6 · C10 / C19 / C20 |
| `Send(node, arg)` | **位置或关键字皆可**；**不可变记录** | Q7 · C18 |
| `interrupt(value)` | **位置或关键字皆可** | Q7 · C17 |
| `Command` / `RunConfig` | **原样转出**（签名见契约层 `public-api.md` §1.2） | C16 / C22 |
| `invoke(input, config)` | **不属门面导出面**（属 `CompiledGraph`，B2F1 已冻结） | 裁定 7 |

---

## 3. 未接线语义（冻结）

| 调用 | 异常 | 消息 | 归属 |
|---|---|---|---|
| `add_node` / `add_edge` / `add_conditional_edges` | `NotImplementedError` | `<方法名> 尚未接线（由 B6F1 交付）` | **B6F1** |
| `compile` | `NotImplementedError` | `compile 尚未接线（由 B7F2 交付）` | **B7F2** |
| `interrupt(...)` | `NotImplementedError` | `interrupt 尚未接线（由 B10F1 交付）` | **B10F1** |

**统一约束**：异常类型 MUST 是**内置** `NotImplementedError`（**零新增公开错误类型** · Q2）；
消息 MUST 点明「尚未接线」+ 归属 feature；MUST NOT 静默成功；MUST NOT 抛意外异常。

---

## 4. 冻结记录（spec 的 12 条裁定 + 12 条澄清问答 → 本文件的落点）

| # | spec 裁定 / 问答 | 落点 |
|---|---|---|
| 裁定 1 | 导出面**恰 7 个** | §0 |
| 裁定 2 | `Send` / `interrupt` 的**类型面**在本 feature 就位；**契约层 18 符号面不变** | §0 分组注释 · SC-015 |
| 裁定 3 | 门面**零实现体**（AST 判据） | 门禁 **G14** |
| 裁定 4 | 构造参数名 = **`schema`**（单参数） | §2 |
| 裁定 5 | 三个构建方法的**返回注解 = `Self`**（链式语义；运行时归 B6F1） | §2 |
| 裁定 6 | `compile` 的两个可选关键字 **keyword-only** | §2 |
| 裁定 7 | `invoke` **不属**本冻结面 | §2 末行 |
| 裁定 8 | 快照文件的**落位**与「唯一手工维护点」 | `public-api-snapshot.txt` + `snapshot-format.md` |
| 裁定 9 | 兼容矩阵**补 5 行**（不「跳过」） | `README.md`「## API 兼容矩阵」章节 · 门禁 **G19** |
| 裁定 10 | 「**唯一维护点**」分工明确化 —— 清单=**唯一手写权威** / 快照=**唯一入库比对点** | §0 · `snapshot-format.md` §4 |
| 裁定 11 | `Send` MUST **不可哈希**（显式 `__hash__ = None`） | §2 · `data-model.md` §2.5 |
| 裁定 12 | 导入开销预算入 spec（**FR-019 / SC-018**，含唯一计时口径） | `plan.md` Performance Goals · `tasks.md` T040 |
| Q1 | 导出面判定 = **`__all__` 集合相等 且 公开名集合相等** | §0 · 门禁 **G15** |
| Q2 | 未接线异常 = 内置 **`NotImplementedError`** | §3 · 门禁配套断言 |
| Q3 | 快照**全冻**参数注解与返回注解 | `snapshot-format.md` §2 |
| Q4 | 快照的**显式更新入口**（默认不生效） | `snapshot-format.md` §4 · 门禁 **G16** |
| Q5 | 兼容矩阵 5 行的**等价程度**按当前状态如实标注 | `README.md` 矩阵 5 行 |
| Q6 | 快照**必须记录公开属性 / property** | `snapshot-format.md` §1（R-9 / R-11） |
| Q7 | `Send` / `interrupt` 参数**位置或关键字皆可**；`Send` **不可变** | §2 · `data-model.md` §2.5 |
| Q8 | 快照 **UTF-8 / LF / 末行换行** · 人工记录**五段式** · B2F1 `public-api.md` §5 加指向行 | `snapshot-format.md` §3 · `harness/verification/B2F2/manual-verification.md` · B2F1 `public-api.md` §5 |
| Q9 | 门面的**层归属** = 跨层单元（层 =「—」）+ **ARCH-1 唯一例外** | 本文件顶部「层归属」块 · `plan.md`「架构纪律核对」 |
| Q10 | 参数名的**冻结口径** = **宪法原则 III 优先**（非上游参数名） | §2「参数名的冻结口径」块 |
| Q11 | 署名头门禁的**覆盖缺口** ⇒ 门面侧另立 **G20**（不改既有 G5） | `architecture-gates.md` **G20** |
| Q12 | 快照测试「**在 CI 中**」的措辞（CI 挂载归 B3F1） | `plan.md` / `tasks.md` 的 US2 叙述 |

---

## 5. 门禁摘要（本 feature 的增量）

| 门禁 | 内容 | 状态 |
|---|---|---|
| **G14** | 门面**零实现体**（AST：门面模块内 `class` / `def` / `async def` == 0） | **新增** |
| **G15** | 门面导出面**两处相等**（`__all__` 集合 == §0 解析结果 **且** 公开名集合 == 同一集合）——**两段落地**：子集段（始终启用）· 集合相等段（US3 交付完 7 个符号后启用） | **新增** |
| **G16** | **API 快照比对**（逐字节）+ **可复现性**（两次生成逐字节相同）+ 更新入口**默认不生效** | **新增** |
| **G17** | 门面**依赖卫生**（零 `langchain*` / `langgraph*` / `langsmith` import、零环境变量、零 I/O） | **新增** |
| **G18** | 门面的**模块加载面**（不横依赖 L4 / L5 + 顶层包惰性的门面视角） | **新增** |
| **G19** | 兼容矩阵**覆盖门面 7 个符号**（各恰有一行 + 等价程度逐符号 + 上游来源行号） | **新增** |
| **G20** | 本 feature **新建源文件**的**署名头**（门面侧覆盖，**不改**既有 G5 的硬编码清单） | **新增** |
| **G1** | 顶层包惰性 | **继承**（既有实现的口径**已是** `freegraph.*` 子模块全量 —— 恰为 `['freegraph']`） |
| **G7** | 契约层公开符号面**恰为 18 个** | **继承**（本 feature **不得**使其变红 —— SC-015） |
| **G12** | 公开符号面**唯一权威**（扫 `**/public-api.md`） | **继承**（本 feature **不产出**该文件名 ⇒ 不受影响） |

> 逐条判定细则见 [architecture-gates.md](./architecture-gates.md)；
> 与既有门禁的**分工边界**（哪些判据不重叠）见该文件 §3。

---

## 6. 移交后续 feature

| # | 事项 | 归属 | 性质 |
|---|---|---|---|
| 1 | `StateGraph` 的**构建行为**（`add_node` / `add_edge` / `add_conditional_edges`） | **B6F1** | 行为 |
| 2 | `StateGraph.compile()` 的**行为** | **B7F2** | 行为 |
| 3 | `Command` 的运行时语义（`goto` / `update`） | **B9F1** | 行为 |
| 4 | `interrupt` 的中断 / 恢复闭环 | **B10F1** | 行为 |
| 5 | `Send` 的动态 fan-out | **B11F1** | 行为 |
| 6 | 节点别名（`alias`）的运行时寻址 | **B8F3** | 行为 |
| 7 | `schema` 的注解从 `Any` 收紧（C1 的类型体系） | **B4F1** | 类型收紧（走快照 diff 流程） |
| 8 | 外壳模块**搬到目标层**（L2 / L3）时只改门面的 import 行 —— **合法**（门面是跨层单元，ARCH-1 例外允许其 import L1–L3） | B6F1 / B10F1 / B11F1 | 重构（门面导出面 MUST NOT 变） |
| 9 | API 快照检查**挂进 CI 流水线** | **B3F1** | 工程设施 |
| 10 | 兼容矩阵的**全库补全与定稿**（`COMPAT.md`） | **B24F1** | 文档 |
| 11 | `harness/demo/graph_core.py` 的**用例转绿** | M1 / M2 全部 feature | 行为 |
