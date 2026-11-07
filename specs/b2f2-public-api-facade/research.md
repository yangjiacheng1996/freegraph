# Research · B2F2 公开 API 门面 + API 签名快照

**feature**: `B2F2`（M0 地基 · 31 个 feature 中的第 3 个）
**规格来源**: [`spec.md`](./spec.md)（19 FR / 18 SC · **12 条裁定 + 12 条澄清问答 Q1–Q12**）
**核实环境**: `langgraph 1.2.11` / `langchain-core 1.6.3`（本机已装，逐条实测）· CPython **3.12.3**
**本文件性质**: `/speckit.plan` 的 **Phase 0 输出** —— 设计决策台账。每条决策给出「决策 / 理由 / 备选与否决理由」。

> **口径**：spec 的**冻结面内容一字未动**；本文件只决定**如何实现**与**如何判定**。
> 凡与 spec 冲突处，一律以 spec 为准并回头修正本文件。

---

## 0. 决策索引

| # | 决策 | 影响面 |
|---|---|---|
| D-01 | 门面 + 外壳的**模块落位**（3 个模块） | 项目结构 · G14 · 快照生成器 |
| D-02 | 门面**不使用** `from __future__ import annotations` | G15（公开名恰 7 个） |
| D-03 | 外壳模块**不使用** future import（注解保持求值对象） | 快照渲染的同构性 |
| D-04 | 快照的**注解规范化规则**（6 条） | 快照格式契约 |
| D-05 | 快照**条目语法**（`[kind] name` · 2 空格缩进） | 快照格式契约 |
| D-06 | 快照**覆盖 7 个符号全部**（含契约层转出类型） | 快照内容 |
| D-07 | **清单**（手写）与**快照**（生成）分离 | G15 非循环判定 |
| D-08 | 快照文件**不叫** `public-api.md` | G12 唯一权威门禁 |
| D-09 | 更新入口 = `pytest --update-api-snapshot` | FR-011 ① |
| D-10 | 快照渲染器 = **纯函数**（喂命名空间） | 自检用例的实现 |
| D-11 | `StateGraph` 外壳**不暴露公开属性** | 快照内容 · B6F1 的自由度 |
| D-12 | `StateGraph` 四个方法的**返回注解 = `Self`** | FR-008 · 快照内容 |
| D-13 | `Send` = frozen dataclass，**不用 `kw_only`** | FR-005 · Q7 |
| D-14 | `interrupt` = 模块级函数，直接抛未接线异常 | FR-005 ② · FR-009 |
| D-15 | 未接线异常的**统一文案格式** | FR-009 · SC-011 |
| D-16 | 门禁测试文件**不叫** `test_architecture.py` | pytest 收集（import file mismatch） |
| D-17 | 兼容矩阵 5 行的**逐字文案** | FR-012 · SC-012 |
| D-18 | `harness/demo/graph_core.py` **不改** | FR-016 |
| D-19 | 性能预算：`import freegraph.graph` < 120 ms | 技术上下文 · FR-019 / SC-018 |
| D-20 | `pyproject.toml` / `THIRD_PARTY_NOTICES` **不动** | 零新增依赖 |
| D-21 | 快照的 **dataclass 属性取数规则**（4 条） | 快照格式契约 · 快照可复现性 |
| D-22 | 门禁 **G17** 的依赖卫生判据改**两档制** | G17 · `architecture-gates.md` |
| D-23 | 快照**自检增强**到真实比对路径 | FR-011 ② · SC-005 |

---

## 1. 模块落位与命名（D-01 · D-02 · D-03）

### D-01 决策

```
src/freegraph/
├── __init__.py          # 既有 · 顶层包惰性（只暴露 __version__）—— 本 feature 不动
├── py.typed             # 既有 · PEP 561 —— 不动
├── graph.py             # ★ 门面（唯一公开入口 · 零实现体）
├── _stategraph.py       # ★ StateGraph 外壳（未来 L3 · B6F1 接线）
├── _primitives.py       # ★ Send / interrupt 外壳（未来 L2 · B11F1 / B10F1 接线）
└── contracts/           # 既有（B1F1 / B2F1）—— 本 feature 逐字不动
```

**理由**：

1. **门面必须是 `src/freegraph/graph.py` 一个模块**——spec FR-001 与交付物口径逐字要求；
   把它做成包（`freegraph/graph/__init__.py`）会让 `freegraph.contracts.graph`（B2F1 的图结构数据类）
   与 `freegraph.graph` 的**心智模型**进一步混淆（两者同名不同义，B2F1 已在 docstring 里互相注明）。
2. **外壳模块一律下划线前缀**——FR-001 说门面是「唯一公开入口」；若外壳放在 `freegraph/builder.py`
   这类无前缀路径，用户就能 `from freegraph.builder import StateGraph` 绕过门面 ⇒ 出现**第二套入口**
   （spec User Story 3 明令禁止）。下划线前缀是 Python 生态对「私有」的既有约定。
3. **三个外壳分两个模块**（而非合成一个）——`StateGraph` 未来归 **L3**（B6F1 / B7F2），
   `Send` / `interrupt` 未来归 **L2**（B11F1 / B10F1）：下游归属不同、目标层不同，
   分开可让 B6F1 与 B10F1 / B11F1 各自演进时**不争抢同一文件**。
4. **不把 `Send` / `interrupt` 放进契约层**——B2F1 冻结记录 §5 第 14 条明确「契约层不导出
   `Send` / `interrupt`」；`StateGraph` 属 L3 更不属于 L1 契约层。

**备选与否决**：

| 备选 | 否决理由 |
|---|---|
| 三个外壳合并进一个 `src/freegraph/_facade.py` | B6F1 / B10F1 / B11F1 三方争抢同一文件；L2 与 L3 的目标层混在一处 |
| 门面做成包 `freegraph/graph/__init__.py` + `state.py` | 与 FR-001 的「门面文件 `freegraph/graph.py`」冲突；且与 `freegraph.contracts.graph` 更易混淆 |
| 外壳放进 `freegraph/contracts/` 的子模块（不进 `__all__`） | 契约层是 L1，而 `StateGraph` 是 L3；且 B2F1 的冻结记录明写契约层不承载 `Send` / `interrupt` |
| 外壳放在无前缀路径（`freegraph/builder.py`） | 产生第二套公开入口，违反 FR-001 与 User Story 3 |

> **B6F1 / B7F2 / B10F1 / B11F1 的迁移义务**：这三个 feature 可把外壳**搬到各自的目标层模块**
> （如 `freegraph/runtime/` / `freegraph/graphbuilder/`），只需改门面的 **import 行**；
> **门面导出面 MUST NOT 改变**（spec FR-006 明文）。搬迁后旧模块删除，同步更新门禁的扫描路径清单。

### D-02 决策：门面**不**使用 `from __future__ import annotations`

**实测证据**：

```python
>>> ns = {}
>>> exec("from __future__ import annotations", ns)
>>> [k for k in ns if not k.startswith("_")]
['annotations']
```

`from __future__ import annotations` 会在模块命名空间里留下一个**名为 `annotations` 的公开绑定**
（`__future__._Feature` 实例）。它不以 `_` 开头 ⇒ 被 FR-002 ② 的「不以下划线开头的公开名」
判据计入门面 ⇒ 公开名变成 **8** 个 ⇒ G15 恒红。

**理由**：门面自身**零注解**（只有 import + 两个常量 + `__all__`），本就不需要 future import。

**备选与否决**：备选「G15 的公开名判据里排除 `annotations`」——否决：判据一旦开例外，
就会变成「以后还可以再排除几个」的滑坡；让门面不使用 future import 更干净。

### D-03 决策：外壳模块**不**使用 future import（注解保持「求值对象」）

**实测证据**（契约层 `types.py` / `protocols.py` 均**未**使用 future import）：

```
>>> inspect.signature(Command.__init__)
(self, *, goto: str | collections.abc.Sequence[str] | None = None,
 update: dict[str, typing.Any] | None = None, resume: typing.Any | None = None) -> None
>>> inspect.signature(RunConfig.from_dict)
(d: collections.abc.Mapping[str, typing.Any], *, ignore_unknown: bool = False) -> 'RunConfig'
```

**理由**：若外壳用 future import，其注解在运行时是**源码字符串**，而契约层转出类型的注解是
**求值对象** ⇒ 快照里两种渲染形态并存（`str | Sequence[str] | None` vs
`str | collections.abc.Sequence[str] | None`），同构性被破坏、规范化规则要多写一套。
统一为「求值对象 + `inspect.signature` 字符串形态 + 规范化」⇒ **一套规则通吃**。

**备选与否决**：备选「外壳用 future import + 渲染时统一 eval」——否决：`eval` 注解字符串
需要在快照生成器里建求值命名空间，既慢又引入「求值失败即快照失败」的脆弱面；
`typing.get_type_hints` 亦然（且对 `Self` 这类特殊形式不友好）。

---

## 2. 快照格式（D-04 · D-05 · D-06 · D-07 · D-08 · D-09 · D-10 · D-21 · D-23）

### D-04 决策：注解规范化规则（**6 条**，逐字冻结）

| # | 规则 | 理由 |
|---|---|---|
| ① | 去掉字符串注解的**外层引号**（`'RunConfig'` → `RunConfig`） | 契约层的 `from_dict` 用引号前向引用（`-> "RunConfig"`），不归一会与真实注解不同形 |
| ② | 去掉 `typing.` / `collections.abc.` **限定前缀**（`typing.Any` → `Any`、`collections.abc.Sequence[str]` → `Sequence[str]`） | 限定名是**导入写法**而非类型本身；前缀在不同文件里可能不同（`from typing import Any` vs `import typing`），去前缀后与源码写法对齐，**跨 Python 版本稳定** |
| ③ | `Optional[X]` → `X \| None`；`Union[X, Y]` → `X \| Y`（**保持原成员顺序**） | 两种写法等价；统一后快照不随书写风格抖动 |
| ④ | `NoneType` → `None` | 同上 |
| ⑤ | **参数顺序即冻结面**，逐字保留（不排序） | 与 B2F1 的「方法集按集合相等」**不同**：参数顺序影响调用语义（`add_edge(src, dst)` 换序即破坏）⇒ 必须是**顺序断言**，不能是集合断言 |
| ⑥ | 类内成员（方法 / 属性）**按名字排序** | 展示顺序无语义 ⇒ 排序保证可复现（SC-006） |

> **⚠️ 口径澄清（2026-11-07 分析轮 · 对应发现 I-10）**：本表 6 条**不是同一层**的规则 ——
> ① ② ③ ④ 是**注解规范化**（= `snapshot-format.md` §2 的 **N-1…N-4**）；
> ⑤「参数顺序逐字保留」= **文本层规则 T-6**；⑥「类内成员按名排序」= **文本层规则 T-5**。
> 另：**N-5**（空白归一 + `repr` 缺省）与 **N-6**（返回注解写法）**只在 `snapshot-format.md` §2**
> （本表未列）。⇒ **「注解规范化 6 条（N-1…N-6）」专指 `snapshot-format.md` §2 的那 6 条**，
> `tasks.md` T019 只实现那 6 条；⑤⑥ 归 T-5 / T-6（文本层）。

> **跨版本稳定性**：上述 6 条落地后，快照文本**不依赖** `typing` 的 `repr` 在不同 Python
> 小版本间的差异（限定前缀与 `Optional` 是主要差异源，均已被 ② ③ 吸收）。
> 剩余风险：`types.UnionType` 的 `repr` 形态（`str | None`）——3.10+ 稳定。

### D-05 决策：快照条目语法

```
[constant] END = '__end__'
[function] interrupt(value: Any) -> Any
[class] StateGraph
    [method] __init__(self, schema: Any) -> None
    [method] add_edge(src: str | list[str], dst: str) -> Self
```

- 顶级条目 = **导出面成员**（7 个），按**名字排序**；
- 类内条目 = 公开成员，**2 空格缩进**，按名字排序；
- `kind ∈ {constant, function, class, method, attribute}`；
- 记录**方法**时含**完整调用签名**（参数名 / 缺省值 / `*` 关键字-only 标记 / 返回注解）；
- 记录**属性**时含「名: 注解 = 缺省值」（可写属性额外标 `(writable)`，只读标 `(readonly)`）；
- 记录**常量**时含**字面值**；
- **不记录** dunder（`__eq__` / `__hash__` / `__repr__` 等语言协议），**但记录 `__init__`**
  （构造签名是用户可见的调用面）。

### D-06 决策：快照覆盖**全部 7 个符号**（含契约层转出的 `Command` / `RunConfig`）

**理由**：门面是用户的**唯一入口**——用户经 `from freegraph.graph import RunConfig` 拿到的
`RunConfig.from_dict` 签名若被悄悄改掉，用户代码会崩，而契约层**没有**签名快照测试
（B2F1 只冻结了**字段名与类型**，没有机械快照）。快照覆盖它们 ⇒ 顺带把契约层两个类型
的**调用面**也钉住。

**避免双权威的分工**（写进快照文件头）：

| 面 | 权威 | 性质 |
|---|---|---|
| **导出面清单**（哪些符号算公开） | `contracts/facade-api.md` §0（**手写**） | 需求面 |
| **签名记录**（每个符号长什么样） | `contracts/public-api-snapshot.txt`（**生成**） | 机器面 |
| `Command` / `RunConfig` 的**字段语义与契约条目归属** | B2F1 的 `contracts/public-api.md`（既有权威） | 不变 |

⇒ 三处各管一面，**不构成重复维护**。

### D-07 决策：清单（手写）与快照（生成）**分离**

**理由（关键）**：若 G15 的「期望的 7 个符号」从**生成的快照**里解析，则门禁变成
「代码 → 快照 → 快照 vs 代码」的**循环论证**，任何漂移都抓不到。
故期望值必须来自**独立于代码**的手写清单 ⇒ `contracts/facade-api.md` §0。

### D-08 决策：快照文件**命名为 `public-api-snapshot.txt`**（**不叫** `public-api.md`）

**理由**：既有门禁 **G12** 扫描 `**/public-api.md` 并读取 `<!-- authority: yes|no -->` 标记，
断言「自称权威的公开符号清单文件数 **== 1**」。若本 feature 也产出 `public-api.md` 并标
`authority: yes`，**G12 恒红**。改用 `public-api-snapshot.txt` ⇒ 既避开文件名冲突，
又用「`.txt` 后缀」表明它是**生成物**（手写清单才用 `.md`）。

### D-09 决策：更新入口 = **`pytest --update-api-snapshot`**

- `tests/facade/conftest.py` 的 `pytest_addoption` 注册该开关；
- 生成器（`render_api_snapshot`）与比对器（测试）**同处一个模块** ⇒ 不存在「脚本一份、
  测试一份」的实现漂移；
- 默认跑 pytest **绝不**改文件（FR-011 ① · SC-005）。

**备选与否决**：`harness/scripts/update_api_snapshot.py` 独立脚本——否决：生成逻辑会与
测试侧分叉（改了一边忘了另一边 ⇒ 快照永不匹配）。

### D-10 决策：快照渲染器是**纯函数** `render_api_snapshot(namespace: Mapping[str, Any]) -> str`

**理由**：自检用例（FR-011 ②「故意改动某个参数名 ⇒ 断言该测试确实失败」）若需要真的改源码，
就会污染工作树、且无法在只读环境下跑。把渲染器做成「输入一个命名空间 ⇒ 输出文本」的纯函数，
自检就能**喂给它一个人造的改名签名**，断言「产出与入库快照不同、且 diff 非空」——
**零副作用、可在任意环境跑**。

### D-21 决策：快照的 **dataclass 属性取数规则**（4 条，逐字冻结）

**问题（2026-11-07 分析轮 · 对应发现 **U-2**）**：本 feature 的 7 个符号里有 **3 个是
dataclass**（`Send` / `Command` / `RunConfig`），而 `snapshot-format.md` §1 只写了
「属性 = 名字 + 注解 + 缺省值 + 只读 / 可写」，**未规定缺省值怎么取** ⇒ 不同实现者会
产出**不同**的快照文本 ⇒ SC-006「两次生成逐字节相同」的冻结面失效。

**实测依据**（CPython 3.12.3）：

| 现象 | 实测 |
|---|---|
| `slots=True` ⇒ 类级字段属性**不是**字段缺省值 | `getattr(Send, "node")` → `<member 'node' of 'Send' objects>`（`member_descriptor`） |
| `dataclasses.fields()` **不含** `ClassVar` | `fields(Command)` → `('goto',)`（**无** `PARENT`） |
| `frozen=True` 的 dataclass **仍会**生成 `__hash__` | `Send.__dict__["__hash__"]` 非 `None`，除非显式 `__hash__ = None` |
| 必填字段的缺省是哨兵 | `fields(Send)[0].default is dataclasses.MISSING` → `True` |

**决策（4 条 · 权威在 `contracts/snapshot-format.md` §1.1）**：

1. **D-21-1 缺省值**取自 `dataclasses.fields(cls)`：`.default` 非 `MISSING` ⇒ 取该值；
   `.default_factory` 非 `MISSING` ⇒ 取 `default_factory()` 的返回值；两者皆 `MISSING`
   ⇒ 记 `<required>`。**MUST NOT** 用 `getattr(cls, name)` 取缺省值（会写入实现细节）。
2. **D-21-2 `ClassVar`** 取自 `cls.__annotations__`（`fields()` 不含）⇒ `Command.PARENT` 走这条。
3. **D-21-3 只读 / 可写**：dataclass `frozen=True` ⇒ 字段一律 `(readonly)`；非 frozen ⇒
   `(writable)`；`property` 的 `fset is None` ⇒ `(readonly)`，否则 `(writable)`。
4. **D-21-4 注解**取自 `dataclasses.fields(cls)[i].type`（`ClassVar` 取自
   `cls.__annotations__[name]`）；若为**字符串** ⇒ 按 N-1 去外层引号。

**备选与否决**：备选「只用 `inspect.getmembers` + `getattr`」——否决：`slots=True` 下拿到
的是 `member_descriptor`，其 `repr` 是实现细节，会把 `<member 'node' of 'Send' objects>`
写进入库快照，违反 `snapshot-format.md` §5「不得含任何实现细节」。

---

### D-23 决策：快照**自检增强到真实比对路径**

**问题（2026-11-07 分析轮 · 对应发现 **I-3**）**：SC-005 字面要求「故意把门面中任一方法的
参数改名 ⇒ **该测试失败**且输出 diff」，但原计划（T022）的自检是「喂人造命名空间 ⇒ 断言
**渲染结果 ≠ 入库文本**」—— 这只验证了**渲染器**，**没有验证比对路径本身**；若比对逻辑
坏掉（比错了对象 / diff 恒为空），自检**仍会「通过」** ⇒ 门禁形同虚设。

**决策**：自检 MUST **走真实的比对路径**——把比对对象指向 `tmp_path` 下一份
**被改动过**的快照文件，断言比对**确实失败**且 **diff 非空**。**三例**：
① 某方法的**参数改名**；② **改动某方法的参数注解或返回注解**（Q3「全冻」的核心收益——
缺它则注解漂移仍会悄悄溜过）；③ **新增一个公开属性**（Q6 专门立的口径，
缺它属性漂移仍会悄悄溜过）。

> **补第三例（2026-11-07 分析轮 · 第二轮）**：本条原定「**两例**」，
> 但 **SC-005** 字面要求**三种**「故意改动」都触发失败（参数改名 / **注解改动** /
> 新增公开属性）⇒ 原「两例」漏掉「注解改动」这一例，Q3「全冻」的收益无自检保护
> ⇒ 补为**三例**，`tasks.md` T022 同步。

**零副作用**：三例 MUST **不碰真源码**、只在 `tmp_path` 下操作 ⇒ 可在只读环境跑
（沿用 D-10 的「纯函数」思路，把「比对对象」从真文件改为临时文件）。

**备选与否决**：备选「保留纯函数自检即可」——否决：那守不住「**比对逻辑本身没坏**」
这条失效模式。

---

---

## 3. 外壳的形状（D-11 · D-12 · D-13 · D-14 · D-15）

### D-11 决策：`StateGraph` 外壳**不暴露任何公开属性**

`schema` 私有存放（`self._schema`）⇒ M0 的快照里 `StateGraph` **无 `[attribute]` 条目**。
B6F1 若要公开 `schema`（或任何新属性），快照会 **diff** ⇒ 需人工确认——正是 Q6 立这条规矩的用意。

### D-12 决策：四个方法的返回注解 = **`Self`**（逐字镜像上游）

| 方法 | 冻结签名（进入快照） | 依据 |
|---|---|---|
| `__init__` | `(self, schema: Any) -> None` | 裁定 4（参数名 `schema`）+ C1 的 schema 类型体系归 **B4F1** |
| `add_node` | `(self, name: str, fn: NodeFunc, *, alias: str \| None = None) -> Self` | 宪法原则 III 第 3 项 + C25 |
| `add_edge` | `(self, src: str \| list[str], dst: str) -> Self` | 宪法原则 III 第 4 项 |
| `add_conditional_edges` | `(self, src: str, path_fn: Callable[..., str \| list[str]], path_map: list[str] \| dict[str, str]) -> Self` | 宪法原则 III 第 5 项（C7 路由契约归 **B8F1**） |
| `compile` | `(self, *, checkpointer: Checkpointer \| None = None, store: Store \| None = None) -> CompiledGraph` | 裁定 6 + C10 / C19 / C20 |

- `Self` 取自 `typing.Self`（**3.11+** ⇒ 合规 G9 的 typing 构件上限；上游同形
  `langgraph/graph/state.py:667` / `:928` / `:982`）。
- `fn` 的注解直接用契约层**已有**的 `NodeFunc` 协议 ⇒ **不新造类型**（原则 VII）。
- `compile` 的返回注解用契约层**已有**的 `CompiledGraph` 协议（**不导出**，仅作注解）。
- `path_map` **无缺省值**（三参数齐备）——宪法原则 III 第 5 项写作 `add_conditional_edges(src, path_fn, path_map)`。

### D-13 决策：`Send` = `@dataclass(frozen=True, slots=True)`，**不用 `kw_only=True`**

**关键冲突与化解**：契约层的五个数据类**一律** `kw_only=True`（B2F1 的口径），
但 `Send` **必须**接受位置参数——

- `harness/demo/graph_core.py:48-56` 的 import 段之后，脚本用 `Send("worker", {"n": 1})`
  **位置调用**；
- 上游 `langgraph/types.py:704` 的 `Send.__init__(self, /, node: str, arg: Any, *, timeout=None)`
  同样接受位置参数。

⇒ `Send` **刻意不**用 `kw_only=True`（否则位置调用直接 `TypeError`）。
这是本 feature 中**唯一**与契约层 dataclass 惯例不同的地方，**在快照与本文档中显式登记**。

- 显式 `__hash__ = None` ⇒ 不可哈希（与 `Node` / `Edge` / `Graph` / `Span` 的「统一不可哈希」
  纪律同构）；`arg` 常为 dict，本就不可哈希。
- **不可变**（Q7）：改属性抛 `FrozenInstanceError`；上游 `Send` **可变** ⇒ 差异入兼容矩阵。

### D-14 决策：`interrupt` = 模块级函数

```python
def interrupt(value: Any) -> Any:
    """…未接线（B10F1 交付）…"""
    raise NotImplementedError(...)
```

**理由**：上游 `langgraph/types.py:851` 同形（模块级函数）；「函数体只有一行 raise」保证
零副作用、零 I/O（FR-014 ③）。

### D-15 决策：未接线异常的**统一文案**

```
NotImplementedError("<方法名> 尚未接线（由 <feature> 交付）")
```

**理由**：FR-009 要求「消息 MUST 点明『尚未接线』并指名归属 feature」；统一模板让门禁可以
**正则断言**消息形态（而不只是断言异常类型）。

| 抛点 | 归属 feature |
|---|---|
| `StateGraph.add_node` / `add_edge` / `add_conditional_edges` | **B6F1** |
| `StateGraph.compile` | **B7F2** |
| `interrupt(...)` | **B10F1** |

---

## 4. 门禁与测试落位（D-16 · D-22）

### D-16 决策：门禁测试文件**不叫** `test_architecture.py`

**理由（pytest 机制）**：`tests/` 下**没有** `__init__.py` ⇒ pytest 按**根目录相对路径**为
测试模块生成模块名。两个目录下**同名**的测试文件（`tests/contracts/test_architecture.py` 与
`tests/facade/test_architecture.py`）⇒ 第二个被导入时抛
`import file mismatch: imported module 'test_architecture' has this __file__ attribute ...`
⇒ **收集期直接报错**。

⇒ 门面门禁文件命名 **`tests/facade/test_facade_gates.py`**（全仓唯一的 basename）。

### 测试文件清单（本 feature 新增）

> **本 feature 新建 10 个 `.py`**（与门禁 **G20** 的扫描清单**逐字一致**）：
> `src/freegraph/graph.py` / `_stategraph.py` / `_primitives.py` + `tests/facade/` 下 7 个。

| 文件 | 内容 |
|---|---|
| `src/freegraph/graph.py` | 公开 API 门面（**零实现体** · 只做导出 + 两个常量 + `__all__`） |
| `src/freegraph/_stategraph.py` | `StateGraph` 外壳（构造成功 · 四方法未接线） |
| `src/freegraph/_primitives.py` | `Send`（frozen dataclass · 不可哈希）· `interrupt`（未接线） |
| `tests/facade/__init__.py` | 空占位（使 `tests/facade/` 可被绝对导入） |
| `tests/facade/conftest.py` | `sys.path` 注入（沿用 `tests/contracts/conftest.py` 口径 + `FREEGRAPH_TEST_INSTALLED` 开关）+ `--update-api-snapshot` 选项 + `repo_root` / `src_dir` / `spec_dir` fixture |
| `tests/facade/_gatesupport.py` | 门禁共享辅助：AST 扫描 · 子进程 `sys.modules` 快照 · `facade-api.md` §0 清单解析 |
| `tests/facade/_snapshot_tools.py` | `normalize_annotation`（N-1…N-6）· `render_api_snapshot`（纯函数 · D-10） |
| `tests/facade/test_facade.py` | 导出面两处相等 · `START` / `END` 取值 · 转出对象的**同一性** · `StateGraph` 构造与未接线语义 · `Send` 不可变 / **不可哈希** 与关键字形态 · `interrupt` 未接线 |
| `tests/facade/test_api_snapshot.py` | 快照渲染（纯函数）· 入库快照比对 · 两次生成逐字节相同 · 更新入口（默认不生效）· **自检三例**（D-23） |
| `tests/facade/test_facade_gates.py` | 门禁 **G14–G20** 及其 **8 条自检**（7 条门禁，G15 两段各一条；故意造违规 ⇒ 门禁确实报出） |

### D-22 决策：门禁 **G17** 的依赖卫生判据改**两档制**

**问题（2026-11-07 分析轮 · 对应发现 **U-1**）**：G17 的第三方档写作「**任何非标准库顶层包**」，
但门面**必须** import `freegraph.contracts`（`Command` / `RunConfig` 原样转出 ＋
`NodeFunc` / `Checkpointer` / `Store` / `CompiledGraph` 的注解），而 `freegraph`
**不是标准库** ⇒ 按字面执行，该门禁会对本 feature 的**必需代码恒红**。

**判例**：B2F1 的 **G2** 已就同一类缺陷留下结论——「若把『任何非标准库顶层包』一刀切，
门禁会因 `import pytest` **恒失败**」（B2F1 第二轮复核发现的口径缺陷）。

**决策**：G17 改为**两档**（与 G2 同构）——
① **内部档**：禁 **L4 / L5**（持久化 / 可观测）的 import（**与 FR-014 ④ 同口径**）；
**`freegraph.contracts`（L1）、门面包内私有模块、以及 L2 / L3 的 import 合法**——
门面是 **ARCH-1 的唯一例外**（可 import L1–L3 · 裁定 9），B6F1 / B10F1 / B11F1
接线后**必须** import L2（`Send` / `interrupt` 归 L2）与 L3（`StateGraph` 归 L3）
⇒ 禁 L2 / L3 会让后续 feature **必然假红**；
② **第三方档**：禁 `langchain*` / `langgraph*` / `langsmith` / `pydantic` /
`typing_extensions`；**标准库**用 `sys.stdlib_module_names` 判（Python 3.10+ ⇒ 合 3.11 基线），
**`freegraph.*` 属内部档**、不在本档。

**关键**：**spec 的 FR-014 ① 一字未动**——本条改的是「**判据**」，不是「**规范**」。

> **内部档范围的修订（2026-11-07 分析轮 · 第二轮）**：本条原写作「禁 L2 / L3 / L4 / L5」，
> 与 FR-014 ④（只禁 L4 / L5）**不一致**，且会在 B6F1 / B10F1 / B11F1 接线后**必然假红**
> ⇒ 修订为只禁 **L4 / L5**。
> 另：「层段」的**取法**也一并写死（首段为 `freegraph` 时取**第二段**，否则取**首段**）
> ——原表述「首段 ∈ {`runtime`, `persistence`, `observability`}」与同段的
> 「首段 = 路径第一段」定义**互斥**（`from freegraph.runtime import X` 的首段是
> `freegraph`，按字面**永不触发**）⇒ T010 的自检按字面无法通过。

**备选与否决**：备选「把 G17 的扫描范围收窄到 `graph.py`」——否决：会放弃对外壳模块的
零依赖约束（外壳是门面的一部分，用户经门面触达）。

---

---

## 5. 文档与对外承诺（D-17 · D-18 · D-19 · D-20）

### D-17 决策：兼容矩阵 5 行的**逐字文案**

`README.md` 的「## API 兼容矩阵」章节**追加** 5 行（**保持 4 列**，既有 18 行**逐字不动**）：

| freegraph 符号 | 对应上游符号 | 等价程度 | 差异说明 |
|---|---|---|---|
| `StateGraph` | `langgraph.graph.StateGraph` | 部分等价 | 构造**只接受** `schema` 一个位置参数（上游另有 `context_schema` / `input_schema` / `output_schema`）；`add_node` 的参数名为 `name` / `fn`（上游 `node` / `action`）且新增 `alias` 关键字；`compile` 只保留 `checkpointer` / `store` 两个关键字（上游另含 `cache` / `interrupt_before` / `interrupt_after` / `debug` / `name` / `transformers`）；**构建器行为待 B6F1 / B7F2 交付**；上游来源 `langgraph/graph/state.py:131`（核实环境 `langgraph 1.2.11`） |
| `START` | `langgraph.constants.START` | 行为等价 | 值与语义均一致（`'__start__'`）；上游来源 `langgraph/constants.py:30`（核实环境 `langgraph 1.2.11`） |
| `END` | `langgraph.constants.END` | 行为等价 | 值与语义均一致（`'__end__'`）；上游来源 `langgraph/constants.py:28`（核实环境 `langgraph 1.2.11`） |
| `Send` | `langgraph.types.Send` | 部分等价 | 形状等价（`node` / `arg`）；**freegraph 侧不可变**（上游可变）；**fan-out 行为待 B11F1 交付**；上游来源 `langgraph/types.py:704`（核实环境 `langgraph 1.2.11`） |
| `interrupt` | `langgraph.types.interrupt` | 部分等价 | 形状等价（`value`）；**中断 / 恢复行为待 B10F1 交付**；上游来源 `langgraph/types.py:851`（核实环境 `langgraph 1.2.11`） |

> **口径**：来源行号**写在「差异说明」单元格末尾**（沿用 B2F1 的 4 列纪律）·
> `Command` / `RunConfig` 已在矩阵中有行（既有 18 行逐字不动）⇒ 门面 7 个符号
> **全部**在矩阵中有行（SC-012）。

### D-18 决策：`harness/demo/graph_core.py` **不改**

- M0 阶段它的**用例必然全红**（`StateGraph` 未接线）⇒ 预期**退出码 1**（断言失败）
  而**非 2**（环境未就绪）——这正是 SC-011 的判据；
- FR-016 允许它演进，但**不得削弱断言口径**；本 feature 无需削弱任何断言 ⇒ 不动。

### D-19 决策：导入开销预算 = **< 120 ms**

**理由**：门面是用户的**唯一入口**，每次 `from freegraph.graph import ...` 都要付这份开销；
而 freegraph 的对外承诺之一是「**零第三方运行时依赖**」⇒ 基础安装极轻，导入开销
**必须**与之相称。新增的三个模块（门面 + 两个外壳）均为**零 I/O 的纯定义模块**
⇒ 增量应极小。

**基线实测（2026-11-07 · CPython 3.12.3 · 暖机 best-of-3）**：
`import freegraph.contracts` = **50–63 ms**
⇒ **120 ms** 留出约 **2 倍**余量。

**计时口径（唯一 · 裁定 12）**：以 `time.perf_counter()` 在 import 语句**前后**取差，
**不含解释器自身启动**、**暖机后 best-of-3**（先预热一次再取三次的最小值）、
**基准 CPython 3.11.x**（实测命令见 `tasks.md` T040）。

> **口径歧义的消解（2026-11-07 分析轮）**：本条此前只写在 `plan.md` 的「Performance Goals」，
> 且 plan 的表述（「**含解释器冷启动**」）与 `tasks.md` T040 的实测命令（**只计 import 语句**）
> **互相不一致** ⇒ 判定会随执行者取哪一个口径而漂移。已统一为后者，
> 并升格为 spec 的 **FR-019 / SC-018**（裁定 12）。

> **阈值收紧（2026-11-07 分析轮 · 第二轮）**：本条原写作「`< 300 ms`」，其基线
> （154 ms / CPython 3.12.3 · 隔离 venv）在当前工作树**不可复现**——本机实测真实基线约
> **50–63 ms**（暖机 best-of-3）⇒ 300 ms 的阈值对 **3× 回归**仍然通过，判据形同虚设
> （违反原则 VIII 的证据纪律）。已收紧为 **`< 120 ms`**（≈ 基线的 2 倍），并把
> **测量环境**（CPython 3.11.x · 暖机 best-of-3）写进 FR-019 的**唯一计时口径**。

---

### D-20 决策：`pyproject.toml` / `THIRD_PARTY_NOTICES` **不动**

零新增第三方依赖 ⇒ `dependencies = []` 保持、`requires-python = ">=3.11"` 保持、
不新增 extras（D1：v1 单一发行包）；`THIRD_PARTY_NOTICES` 无新增登记（FR-017）。

---

## 6. 上游证据（本 feature 引用的全部上游位置）

**核实环境**：`langgraph 1.2.11`（`/home/ctyun/.local/lib/python3.12/site-packages/langgraph/`）
· `langchain-core 1.6.3` · CPython 3.12.3。**逐条实测命中 ✓**。

| 上游对象 | 位置 | 本 feature 的用法 |
|---|---|---|
| `START = "__start__"` | `langgraph/constants.py:30` | 门面 `START` 的取值（C9） |
| `END = "__end__"` | `langgraph/constants.py:28` | 门面 `END` 的取值（C9） |
| `class Send` | `langgraph/types.py:704` | `Send` 的形状对齐 + 兼容矩阵来源 |
| `def interrupt(value: Any) -> Any` | `langgraph/types.py:851` | `interrupt` 的形状对齐 + 兼容矩阵来源 |
| `class StateGraph` | `langgraph/graph/state.py:131` | 兼容矩阵来源 |
| `StateGraph.__init__` | `langgraph/graph/state.py:216` | 裁定 4 的**差异证据**（上游有 4 个参数） |
| `StateGraph.add_node`（→ `Self`） | `langgraph/graph/state.py:667` | 裁定 5 的**链式返回**证据 |
| `StateGraph.add_edge`（→ `Self`） | `langgraph/graph/state.py:928` | 宪法原则 III 第 4 项的链式证据 |
| `StateGraph.add_conditional_edges`（→ `Self`） | `langgraph/graph/state.py:982` | 裁定 5 的链式证据 |
| `StateGraph.compile` | `langgraph/graph/state.py:1177` | 裁定 6 的**差异证据**（上游 9 个参数） |

**实测的上游调用形态**（本 feature 的对齐基准）：

```
StateGraph.__init__(self, state_schema, context_schema=None, *, input_schema=None, output_schema=None, **kwargs) -> None
StateGraph.add_node(self, node, action=None, *, defer=False, metadata=None, ...) -> Self
StateGraph.add_edge(self, start_key: str | list[str], end_key: str) -> Self
StateGraph.add_conditional_edges(self, source, path, path_map=None) -> Self
StateGraph.compile(self, checkpointer=None, *, cache=None, store=None, ...) -> CompiledStateGraph[...]
Send.__init__(self, /, node: str, arg: Any, *, timeout=None) -> None      # Send(node='x', arg=1) 合法；可变
interrupt(value: Any) -> Any
```

---

## 7. 挂起项交接表（本 feature **不**做，移交后续）

| # | 事项 | 归属 | 性质 |
|---|---|---|---|
| 1 | `StateGraph` 的**构建行为**（`add_node` / `add_edge` / `add_conditional_edges` 真正落图） | **B6F1** | 行为 |
| 2 | `StateGraph.compile()` 的**行为** | **B7F2** | 行为 |
| 3 | `CompiledGraph.invoke()` 的**行为**（含「`config` 同时接受 `RunConfig` 与普通 dict」） | **B7F3** | 行为 |
| 4 | `Send` 的**动态 fan-out** | **B11F1** | 行为 |
| 5 | `interrupt` 的**中断 / 恢复**（含 `Command(resume=...)` 闭环） | **B10F1** | 行为 |
| 6 | `Command` 的**运行时语义**（`goto` / `update`） | **B9F1** | 行为 |
| 7 | 节点**别名行为**（`alias` 的运行时寻址） | **B8F3** | 行为 |
| 8 | `recursion_limit`（走 dict 形态） | **B13F1** | 行为 |
| 9 | `get_graph` / `draw_mermaid` / `draw_mermaid_png` | **B22F1 / B23F1** | 能力 |
| 10 | 状态 **schema 的类型体系**（C1：`schema` 注解从 `Any` 收紧） | **B4F1** | 类型收紧（走快照 diff 流程） |
| 11 | API 快照检查**挂进 CI 流水线** | **B3F1** | 工程设施 |
| 12 | 兼容矩阵的**全库补全与定稿**（`COMPAT.md`） | **B24F1** | 文档 |
| 13 | freechain 侧的**门面复用**（同一入口的用户 API） | 未来 | 跨仓库 |
