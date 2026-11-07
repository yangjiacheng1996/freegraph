# API 快照格式契约（snapshot-format.md）

**功能块**: B2F2 · 公开 API 门面 + API 签名快照 · **Date**: 2026-11-07
**权威来源**: [spec.md](../spec.md)（FR-010 / FR-011 · SC-005 / SC-006 · 裁定 8 · Q3 / Q4 / Q6 / Q8）·
[data-model.md](../data-model.md) §1.2 / §1.3 / §3 · [research.md](../research.md) D-04…D-10
**契约性质**: **冻结面** —— 快照的**文本格式**一经落地即为机器比对的事实标准；改格式 = 改冻结面

> **配套文件**：
> - `facade-api.md` §0 —— **导出面清单**（哪些符号算公开；**手写**，门禁 G15 的期望值来源）
> - `public-api-snapshot.txt` —— **签名记录**（每个符号长什么样；**机器生成**，入库比对）
>
> **两者分工**：清单管「**哪些**」，快照管「**长什么样**」——
> 故门禁 G15 的判定**非循环**（research D-07）。

---

## 1. 记录什么

| 类别 | 记录内容 | 排除 |
|---|---|---|
| **导出符号** | 名字 + 类别（`class` / `function` / `constant`） | 门面**未导出**的内部模块（如 `_stategraph`） |
| **常量** | 名字 + **字面值** | — |
| **函数** | 名字 + **完整调用签名**（参数名 / 缺省值 / `*` 关键字-only 标记 / 参数注解 / 返回注解） | 函数体 |
| **类** | 名字（成员以下一级缩进列出） | 私有成员（`_` 前缀） |
| **方法** | 名字 + **完整调用签名** | dunder（`__eq__` / `__hash__` / `__repr__` …）——**但记录 `__init__`** |
| **属性** | 名字 + 注解 + 缺省值 + **只读 / 可写**标注 | 同上 |

- **「公开」的口径**：名字**不**以下划线开头；`__init__` 例外（构造签名是用户可见的调用面）。
- **dataclass 字段**算属性；**`property`** 算属性；**`ClassVar`** 算属性（如 `Command.PARENT`）。
- **必填参数**（无缺省值）记作 `= <required>`（占位符，逐字固定）——否则
  `Send(node, arg)` 与 `Send(node=None, arg=None)` 的快照会长得一样。

### 1.1 dataclass 属性的取数规则（**D-21 · 逐字冻结**）

> **⚠️ 这四条是必需的，不是可选的**：本 feature 的 7 个符号里有 **3 个是 dataclass**
> （`Send` / `Command` / `RunConfig`），而它们的**属性取数**若不写死，
> **不同实现者会产出不同快照文本** ⇒ 冻结面不可复现（SC-006「两次生成逐字节相同」失效）。

| # | 规则 | 判据 | 理由（实测依据） |
|---|---|---|---|
| **D-21-1** | **缺省值**取自 `dataclasses.fields(cls)`：`.default` 非 `MISSING` ⇒ 取该值；`.default_factory` 非 `MISSING` ⇒ 取 `default_factory()` 的返回值；**两者皆 `MISSING` ⇒ 记 `<required>`** | **MUST NOT** 用 `getattr(cls, name)` 取缺省值 | `slots=True` 时 `getattr(Send, "node")` 返回 `member_descriptor`，其 `repr` = `<member 'node' of 'Send' objects>` —— 是**实现细节**，违反 §5「不得含任何实现细节」 |
| **D-21-2** | **`ClassVar`** 属性取自 `cls.__annotations__`（`dataclasses.fields()` **不含** `ClassVar`） | `ClassVar` 按定义**有**类级默认值 ⇒ 用 `getattr(cls, name)` 取其类级值 | `dataclasses.fields(Command)` 只返回 `('goto',)`，**不含** `PARENT` |
| **D-21-3** | **只读 / 可写**的判定：dataclass 为 `frozen=True` ⇒ 其字段**一律 `(readonly)`**；非 frozen ⇒ `(writable)`；`property` 的 `fset is None` ⇒ `(readonly)`，否则 `(writable)` | 判据可从 `cls.__dataclass_params__.frozen` 与 `property.fset` 直接读出 | `Send` / `Command` / `RunConfig` 均为 `frozen=True` ⇒ 字段一律只读 |
| **D-21-4** | **注解**取自 `dataclasses.fields(cls)[i].type`（`ClassVar` 取自 `cls.__annotations__[name]`） | 若该值为**字符串**（模块用了 `from __future__ import annotations`）⇒ 按 **N-1** 去外层引号 | 契约层**未**使用 future import（D-03）⇒ 取到的通常是**求值对象**；N-1 兜住字符串形态 |

> **「公开属性」的集合口径**（与 D-21 正交）：`dataclasses.fields()` 的**全部**字段 ＋
> `cls.__annotations__` 中的 **`ClassVar`** ＋ 类上的 `property` —— 取其**名字不以下划线开头**者
> （`R-11` / `R-10` 的口径），dunder **不记**。

---

## 2. 注解的规范化（D-04 · 逐字冻结）

| # | 规则 | 示例 |
|---|---|---|
| N-1 | 去掉字符串注解的**外层引号** | `'RunConfig'` → `RunConfig` |
| N-2 | 去掉 `typing.` / `collections.abc.` **限定前缀** | `typing.Any` → `Any`；`collections.abc.Sequence[str]` → `Sequence[str]` |
| N-3 | `Optional[X]` → `X \| None`；`Union[X, Y]` → `X \| Y`（**保持原成员顺序**） | `Optional[str]` → `str \| None` |
| N-4 | `NoneType` → `None` | `type(None)` → `None` |
| N-5 | 参数注解与缺省值两侧空白归一为单空格；缺省值用 `repr` 形态 | `ignore_unknown=False` |
| N-6 | 返回注解写成 `-> <注解>`；无返回注解记 `-> None` | — |

**为何要 N-2 / N-3**：`typing` 的渲染形态在 Python 小版本间有差异（`typing.Any` vs `Any`、
`Optional[X]` vs `X | None`），而快照是**入库文件**——一旦在 CI 的 3.11 档与开发机的 3.12 档
渲染不同 ⇒ 快照比对**恒红**。规范化把差异源收敛掉。

**跨版本稳定性的边界**：规范化吸收了**已知**差异源；快照文本**不包含**任何版本信息
（Python 版本、路径、时间戳）⇒ 换版本时若仍出现差异，只能来自 `typing` 的**新**差异源
⇒ 届时按「变更快照格式」流程走（人工确认 diff）。

---

## 3. 文本层规则

| # | 规则 |
|---|---|
| T-1 | 编码 **UTF-8**（无 BOM） |
| T-2 | 换行 **LF**（**不** CRLF） |
| T-3 | **末行带换行**（文件以 `\n` 结尾） |
| T-4 | 顶级条目**无缩进**；类内条目**缩进 2 空格** |
| T-5 | 顶级条目与类内条目**均按名字排序**（**字典序**） |
| T-6 | **参数顺序逐字保留**（顺序是**语义**，不排序）——与「方法集按集合相等」（B2F1 G11）**不同**，此处必须顺序断言 |
| T-7 | 缺省值用 `repr` 形态；空容器记 `{}` / `()`；必填记 `<required>` |
| T-8 | 注释头（`#` 开头）**只允许**出现在文件**顶部**（生成器写入），**不得**出现在条目之间 |

### 语法

```
<kind> <name><payload>
```

`kind ∈ {constant, function, class, method, attribute}`。

### 形态示例（**示意**，非入库快照的逐字内容）

```
# freegraph 公开 API 快照 —— 门面 `freegraph.graph`
# 本文件由 `pytest tests/facade/test_api_snapshot.py --update-api-snapshot` 生成，请勿手工编辑。
# 格式契约：specs/b2f2-public-api-facade/contracts/snapshot-format.md
# 导出面清单（哪些符号算公开）的权威是 contracts/facade-api.md §0；本文件只记录签名。
#
[constant] END = '__end__'
[constant] START = '__start__'
[class] StateGraph
    [method] __init__(self, schema: Any) -> None
    [method] add_edge(self, src: str | list[str], dst: str) -> Self
    [method] compile(self, *, checkpointer: Checkpointer | None = None, store: Store | None = None) -> CompiledGraph
[function] interrupt(value: Any) -> Any
```

---

## 4. 生成、比对与更新

| 环节 | 规定 |
|---|---|
| **生成器** | `render_api_snapshot(namespace: Mapping[str, Any]) -> str` —— **纯函数**（research D-10）：输入一个命名空间，输出快照文本。**无 I/O、无副作用** |
| **命名空间来源** | `namespace = {k: v for k, v in vars(freegraph.graph).items() if not k.startswith("_")}` —— 即**门面的公开名集合**（与 G15 的「公开名」口径**同源**）。**MUST NOT** 由测试侧另造一份符号清单（否则快照与门面**脱钩**，冻结面失效） |
| **比对** | 生成结果与 `public-api-snapshot.txt` **逐字节**比较；不一致 ⇒ 测试失败并输出 **diff** |
| **可复现** | 同一份代码**两次生成 MUST 逐字节相同**（SC-006） |
| **更新入口** | `pytest --update-api-snapshot`（`tests/facade/conftest.py` 的 `pytest_addoption` 注册）。**仅在被显式调用时**生效；**默认跑 pytest 绝不改文件**（FR-011 ① · SC-005） |
| **更新后的人工义务** | 更新产生的新快照 MUST 经**人工 review diff** 后方可提交（MUST NOT 静默自动更新） |
| **自检** | MUST 含**两例**：① 「故意改动某个参数名 ⇒ 断言比对测试**确实失败**」；② 「故意新增一个公开属性 ⇒ 同样**确实失败**」（research D-23）。两例 MUST **走真实的比对路径**（把比对指向 `tmp_path` 下一份**被改动过**的快照文件），**MUST NOT** 只断言「渲染结果 ≠ 入库文本」——否则**比对逻辑本身坏掉**时自检仍会「通过」⇒ 门禁形同虚设 |
| **自检的零副作用** | 上述两例 MUST **不碰真源码**、MUST 只在 `tmp_path` 下操作 ⇒ 可在只读环境跑（沿用 D-10 的「纯函数」思路，比对对象改为临时文件） |

**为何生成器是纯函数**：自检用例若需要真的改源码，就会污染工作树、且在只读环境下跑不了。
纯函数让「改坏 ⇒ 确实失败」可以在任意环境复现。

---

## 5. 快照**不得**包含

- 内存地址 / `id()` / `repr(obj)`；
- 集合的迭代序（**必须**排序后才输出）；
- 时间戳、日期、构建号；
- 绝对路径、用户名、主机名；
- Python 版本号或实现名；
- **任何**实现细节（函数体、内部模块路径、私有成员）。

---

## 6. 变更流程

| 场景 | 流程 |
|---|---|
| 签名**合法变更**（如 B6F1 交付后新增公开属性） | 运行 `pytest --update-api-snapshot` ⇒ **人工 review diff** ⇒ 提交快照 + 代码 |
| 快照**格式**变更 | 属**契约修订**：先改本文件（格式契约）⇒ 再重生成快照 ⇒ diff 人工确认 |
| 快照与代码**不一致**且无人认领 | 测试**失败**并输出 diff —— **MUST NOT** 用「自动更新」掩盖（FR-011） |
| 下游 feature（B6F1 等）接线后 | 快照**MUST NOT** 因「实现」而变（签名不变 ⇒ 快照不变）；若签名变了 ⇒ 走上面的「合法变更」流程 |
