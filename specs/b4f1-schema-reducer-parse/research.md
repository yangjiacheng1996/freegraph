# Phase 0 · Research: B4F1 · 状态 schema 解析 + 归约器提取（`TypedDict` + `Annotated` → 通道规格）

**Date**: 2026-11-08 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

> **证据纪律**（宪法原则 VIII）：本文件的每条**事实性结论**都附**可复现的来源标记**——
> ① 实测命令 + 关键输出（`本地路径:行号` 或 CPython 版本）；② 宪法 / 立项书 / 上游源码的**条款定位**。
> 凡**无法核实**者标 `[未验证]`。
>
> **本轮 research 的性质**：本 feature 的「未知」**不是技术选型**（内核零依赖、无框架、无存储），
> 而是「**Python 类型系统与 TypedDict 的实测行为**」+「**冻结面之间的取舍**」。
> 因此本文件以**实测证据**为主，而非「最佳实践」综述。
>
> **核实环境**：CPython **3.12.3**（系统解释器）· CPython **3.11.16**（`.venv`）·
> `typing_extensions 4.16.0`（`.venv`）· 上游 `langgraph 1.2.11`
> （`/home/ctyun/.local/lib/python3.12/site-packages/langgraph/graph/state.py`）。

---

## D-01 · 解析产物的实现形态 = frozen dataclass（`slots` + `kw_only`）+ **显式不可哈希**

**Decision**

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class ChannelSpec:
    key: str
    value_type: Any          # 归约前的基类型 T
    reducer: Any = None      # 归约器引用（按引用持有）
    has_reducer: bool = False
    semantics: str = "overwrite"   # {"overwrite", "reduce"}
    required: bool = True          # 必选 / 可选
    __hash__ = None                # 显式不可哈希
```

**Rationale**

- **frozen + slots + kw_only** 是**仓库既有纪律**：契约层五个纯数据类一律
  `@dataclass(frozen=True, slots=True, kw_only=True)`（`src/freegraph/contracts/types.py:32,86,164` ·
  `contracts/graph.py:27,69,102`）⇒ 本 feature **同构**，不引入第二种数据类写法。
- **显式 `__hash__ = None`**：frozen dataclass 默认**仍会**生成 `__hash__`（仓库既有代码对此有明确注释：
  `contracts/graph.py:86-87`「dataclass **会自动生成** `__hash__` ⇒ 类体 MUST **显式**写 `__hash__ = None`」）。
  本类 MUST 显式关掉，理由是**实测的运行期风险**：
  ① `reducer` 字段可能是**可调用对象实例**（澄清 Q6 明确接受「类」与「可调用实例」为候选），
  而**可调用实例默认可哈希**（除非它自己定义了 `__hash__ = None`）⇒ 自动生成的 `__hash__`
  会在**用户数据**上抛 `TypeError` ⇒ 与「纯数据、零意外异常」的基调不合；
  ② 仓库「结构类统一不可哈希」的纪律（`Graph` / `Edge` / `Node` / `Span`）同向。
  ⇒ **实测**（CPython 3.12.3）：
  ```
  >>> hash(ChannelSpec(key="a", value_type=int))
  TypeError: unhashable type: 'ChannelSpec'
  ```
  （spec 只要求**可比较**（值相等）· SC-005，**未**要求可哈希 ⇒ 关掉不违 spec。）
- **值相等可用**：dataclass 的 `eq=True` 默认即给出**字段逐一比较** ⇒ SC-005 的
  「同一 schema 两次解析**相等**」成立（实测：`ChannelSpec(key="a", value_type=int) == ChannelSpec(key="a", value_type=int)` ⇒ `True`）。
  `reducer` 字段的比较按**身份**（callable 默认不定义 `__eq__`）⇒ `operator.add` 与自身相等、
  与别的函数不等 ⇒ SC-001 的身份语义不冲突。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| `NamedTuple` | ① `NamedTuple` **不可变但可哈希**（元组语义）⇒ 要关掉哈希得另写 `__hash__`；② **不能**表达 `channels` 的「只读映射」字段（需另设类型）；③ 仓库契约层**无** `NamedTuple` 先例（全是 dataclass）⇒ 同构性差 |
| `attrs` / `pydantic` | 违反 **FR-013**（只允许标准库）与 **FR-019**（零新增依赖声明）；`pydantic` 在 v1.0 根本不存在（宪法 v1.7.0） |
| 可变 dataclass + 调用方自觉 | 违反 **FR-010**（MUST 不可变）⇒ 冻结面失守 |

---

## D-02 · `SchemaSpec.channels` 用 `types.MappingProxyType` —— 结构性不可变

**Decision**

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class SchemaSpec:
    channels: Mapping[str, ChannelSpec]   # 构造时包成 MappingProxyType
    keys: tuple[str, ...]                  # 有序 key 序列
    __hash__ = None
    def __post_init__(self) -> None:
        object.__setattr__(self, "channels", MappingProxyType(dict(self.channels)))
```

**Rationale**

- **frozen dataclass 只冻结「字段的重新赋值」，不冻结字段**指向的**内容** ⇒ 若 `channels` 是普通 `dict`，
  `spec.channels["x"] = ...` 仍能改 ⇒ **FR-010 的「不可变」失守**。
  **实测**（CPython 3.12.3）：包成 `MappingProxyType` 后写操作抛
  `TypeError: 'mappingproxy' object does not support item assignment` ✓。
- **保序**：`dict` 保插入序 ⇒ `MappingProxyType` 亦然 ⇒ FR-002 的「保序」与 SC-008 的「条数 == key 数」成立。
- **`keys` 用 `tuple`**：不可变 + 可哈希（元素是 `str`）⇒ 与 `channels` 的键集合**互为校验**。
- **`SchemaSpec` 也显式不可哈希**：`MappingProxyType` **不可哈希** ⇒ 自动生成的 `__hash__`
  会在 `hash(spec)` 时抛 `TypeError` ⇒ 显式关掉（与 D-01 同理）。
  ⚠️ `ChannelSpec` 作为**字典的值**不受影响（dict 的值不要求可哈希）✓。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| `channels` 存 `tuple[tuple[str, ChannelSpec], ...]` | ① 取单条规格要**线性查找**（B5F1 / B6F1 每个 key 都要查）⇒ O(n²)；② FR-020 ② 明确写的是「**映射**」 |
| `channels` 存普通 `dict` | **实测可写** ⇒ 违反 FR-010 的不可变要求 |
| `frozenset` / `tuple` of specs + 另建索引 dict | 索引 dict 同样可变 ⇒ 同样的漏洞；且**两份表示**要保持一致 ⇒ 漂移风险 |

---

## D-03 · 判定表的**单一权威载体** = `contracts/binary-criterion.md`（机器可读 Markdown）· 测试解析它

**Decision**

```
specs/b4f1-schema-reducer-parse/contracts/binary-criterion.md
  <!-- authority: yes -->
  | # | 形态 | 期望 | 上游来源 |
  |---|------|------|----------|
  | 1 | operator.add（位置专用 2 参） | 接受 | langgraph/graph/state.py:1908-1916 |
  …（16 类二元性形态 + 2 类提取形态）
```

测试**解析该 Markdown 表格**取样比对（**不是**在测试里内联一份副本）。

> **📌 唯一权威的边界（2026-11-08 分析轮补记）**：本文件 §2 是**判定的唯一权威**；
> **`spec.md` FR-016 ①-a 只列「形态清单 + 指向本文件」，不复制表格** ⇒ **无双份表格**
> （D-03 的 Alternatives 一栏「契约 Markdown + 测试内联副本 ⇒ 双份权威」同理适用于「spec + 契约」）。
> 本文件 §5 的**实测取样表**是 §2 的**证据镜像**（同一判据的实测值）⇒
> **判定权威只在 §2**；§5 MUST NOT 被独立于 §2 修改。

**Rationale**

- **仓库既有先例**：层注册表 `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md` 就是
  **机器可读 Markdown**（`<!-- authority: yes -->` 标记 + 固定列管道表），
  且既有门禁 **G25** **直接解析它**（`contracts/architecture-gates.md` G25 §4）⇒ **完全同构**。
- **判据必须与用例分离**：若表写在测试里（Python 常量），改判据会顺手改用例 ⇒ **自证**；
  表写在契约文档、测试解析它 ⇒ 改表**必然**改测试同提交可见（diff 里一眼看出「判据变了、断言跟着变了」）。
- **「来源标注」这一半只有 Markdown 能自然承载**：spec FR-016 ① 要求每条形态写明
  「上游语义 + 来源 `路径:行号`」⇒ JSON / TOML 承载不了「人读的证据链」。
- **不进发行包**（在 `specs/` 下）⇒ 不污染产物纯度（发布门禁第 1 项）。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| JSON / TOML 载体 | ① 需要**额外**一份「人读说明 + 来源标注」文档 ⇒ **双份权威**；② 引入仓库没有的第三种契约载体风格 |
| 测试内联 Python 常量 | 判据与用例同处 ⇒ **自证**（改判据顺手改断言） |
| 契约 Markdown + 测试内联副本 | **双份权威** ⇒ 迟早漂移（仓库已因「G5 / G20 署名头分两处维护」吃过这个亏） |

---

## D-04 · 注解解析失败时**指名 key** 的手段 = 全量解析失败后**逐 key 探针**（仅错误路径）

**Decision**

1. 主路径：`typing.get_type_hints(schema, include_extras=True)`；
2. 抛 `NameError` 时进入**错误路径**：按 `schema.__annotations__` 的键序逐个构造
   **单键探针** `TypedDict("_Probe", {key: ann})` 并 `get_type_hints(probe, include_extras=True)`
   ⇒ 命中第一个失败者 ⇒ 抛 `InvalidSchemaError(key=该 key, reason="annotation_unresolvable")`。

**Rationale**

- spec FR-007 ③ + SC-006 要求错误**指名出错 key**；而 `get_type_hints` 的 `NameError`
  **只说哪个名字不存在、不说是哪个键** ⇒ 必须自己定位。
- **只影响错误路径**：主路径只有一次 `get_type_hints` 调用（O(1) 次类型求值）；
  探针循环**只在解析失败时**执行 ⇒ 正常路径零开销。
- **实测**（CPython 3.12.3 与 3.11.16 行为一致）：
  ```
  全量解析 NameError: name 'Missing' is not defined
  逐 key 定位: ('bad', "name 'Missing' is not defined")
  ```
   ⚠️ **实测前提**：`Annotated[list[Missing], …]` 在**非**未来注解下会在**类定义时**就抛
   `NameError`（`Annotated[...]` 是立即求值的表达式）⇒ 「不可解析的前向引用」这一形态
   **必须**用**字符串注解**（`from __future__ import annotations` 或显式引号）才能构造出来
   ⇒ **测试用例必须用未来注解**才能覆盖该分支。
   （未来注解下 `schema.__annotations__` 的值是 `ForwardRef`，探针可正常接收 ✓ 实测同。）
- **探针遍历的是 `schema.__annotations__`，而它**已经**是继承链的**合并结果**
  （CPython `_TypedDictMeta` 在建类时把基类的注解合并进来 · 实测
  `class P(TypedDict): bad: …` + `class C(P): ok2: int` ⇒ `C.__annotations__` = `['bad', 'ok', 'ok2']`
  ⇒ **父类上的坏注解同样能被探针指名** ✓）⇒ 无需另做 MRO 遍历，也**不会**漏掉继承来的 key。
- **探针 MUST NOT 手工 `eval` 注解字符串**（见 Alternatives 一栏）⇒ 命名空间解析规则与
  `get_type_hints` 完全一致（`ForwardRef` 自带 `module` 信息 ⇒ 在**用户模块**的全局命名空间中求值）。


**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 直接 `eval` 每个注解字符串 | ① 绕过 `get_type_hints` 的**全局/局部命名空间**解析 ⇒ 解析结果与上游不一致；② 手工 eval 有**安全与语义**风险（用户注解里的名字解析规则会漂移） |
| 逐键 `get_type_hints`（不用全量） | ① 丢失**继承链合并**语义（FR-009）⇒ 父类 key 会丢；② N 次调用比 1 次慢 |
| 报错时不指名 key（只给 `NameError` 文本） | 违反 FR-007 / SC-006 的「点名 key」硬要求 |

---

## D-05 · 「类型的可读文本」的规范化口径 = **类取 `__name__`** · 其余取 `str()` 并去 `typing.` 前缀

**Decision**

```
value_type 的可读文本：
  ① isinstance(value_type, type)  ⇒  value_type.__name__          （int / MyState）
  ② 否则                          ⇒  str(value_type).replace("typing.", "")
                                      （list[int] → "list[int]" · typing.List[str] → "List[str]"）
```

**Rationale**

- **实测**（CPython 3.12.3）：`str(int)` == `"<class 'int'>"` ⇒ **不能**直接用 `str()`
  （否则每个基本类型的可读文本都带 `<class '...'>` 噪音，投影不可读、快照难看）。
  ```
  a: raw='list[int]'                base='list[int]'            norm='list[int]'
  b: raw='typing.List[str]'         base='typing.List[str]'     norm='List[str]'
  c: raw="<class 'int'>"            base="<class 'int'>"        norm="<class 'int'>"   ← 不可接受
  d: raw="typing.Annotated[str, 'x']" base="<class 'str'>"      norm="<class 'str'>"  ← 同上
  ```
- **去 `typing.` 前缀**：让 `typing.List[str]` 与 `list[str]` 两种写法的可读文本**同形**
  ⇒ 同一语义不会因写法不同而产生两份投影。
- **`Annotated` 不出现**：`value_type` 已是**基类型**（澄清 Q1）⇒ 投影里不含 PEP 593 元数据。
- **确定性**：口径只依赖「是不是类」+ `str()` ⇒ 同一输入两次投影**逐字一致**（SC-005）。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 直接 `repr(value_type)` | 同样带 `<class 'int'>`；且 repr 的细节随版本漂移 |
| 用 `typing.get_type_hints` 的**原始**注解文本 | ① 会带回 `Annotated` 包装（违反 Q1「不保留原始注解」）② 字符串注解下拿到的是**字符串**而非类型对象 |
| 只取 `__name__`（不区分泛型） | 泛型别名没有 `__name__`（`list[int].__name__` 在 3.11 抛 `AttributeError`）⇒ 不可用 |

---

## D-06 · 归约器标识的 4 级规则（澄清 Q10）的具体实现

**Decision**

```
① obj 有 __module__ 且有 __qualname__  ⇒ f"{obj.__module__}.{obj.__qualname__}"
② obj 无 __qualname__（可调用实例）    ⇒ f"{type(obj).__module__}.{type(obj).__qualname__}"
③ 再取不到                            ⇒ obj.__name__
④ 最后兜底                            ⇒ re.sub(r"0x[0-9a-fA-F]+", "<addr>", repr(obj))
```

**Rationale**

- **①②的实测依据**（CPython 3.12.3）：函数 / 类 / lambda 都有 `__module__` 与 `__qualname__`
  （lambda 的 `__qualname__` = `"<lambda>"` ⇒ 标识为 `tests.test_x.<lambda>`，**无地址** ⇒ 快照稳定）；
  可调用实例**没有** `__qualname__` ⇒ 落到②取**其类型**的路径。
- **④的必要性**：`repr(lambda)` 含内存地址（`<function <lambda> at 0x7f…>`）⇒
  **实测**必须抹除，否则 SC-005 的「两次投影逐字一致」与快照测试都会**假红**。
  兜底用**固定占位**替换 ⇒ 仍然确定性。
- 与 spec FR-011 的 4 级规则**逐字对应**（澄清 Q10 已把规则写进 spec）。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 只用 `__name__` | 分不清 `a.add` 与 `b.add`（澄清 Q10 已否决） |
| 只用 `repr` | **含内存地址** ⇒ 快照假红（实测） |
| 用户自定义标识映射表 | 要**新增 API 面**，与「本 feature 零新增公开 API」相悖（澄清 Q10 已否决） |

---

## D-07 · 解析入口的命名与落点 = `freegraph.runtime.parse_state_schema`

**Decision**

```python
from freegraph.runtime import parse_state_schema   # L2 内部 API（非公开门面）
spec = parse_state_schema(MessagesState)            # -> SchemaSpec
```

**Rationale**

- spec FR-020 ④ 把「解析入口的函数名」明确**留给 plan** ⇒ 本决策**提出候选**，
  **最终由 plan 的 Structure Decision 落定**（`plan.md` §Project Structure / §Structure Decision）——
  research 是 Phase 0、命名属 Phase 1 的 plan（2026-11-08 分析轮登记的阶段顺序修正）。
- **命名**：`parse_state_schema` 自述「解析的是**状态** schema」，与 C1 的术语（状态 schema）对齐；
  避免 `parse_schema` 的歧义（可能被读成「解析 JSON schema」）。
- **落点**：`freegraph.runtime`（L2 子包）⇒ 与层注册表一致；**顶层包 `freegraph/__init__.py` 不 import 它**
  ⇒ G1 / L-1 的顶层包惰性**恒成立**。
- **不是公开门面**：门面 7 符号面**零改动**（G15 / G19）⇒ 本入口属**内部 API**，
  由 **B5F1**（通道实现）与 **B6F1**（构建器）消费。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 放到 `freegraph/contracts/` | 契约层是**冻结面**（18 符号面）⇒ 违反 FR-015 |
| 放到门面 `freegraph/graph.py` | 门面 MUST **零实现体**（AST 判据 · G14）⇒ **不可行** |
| 导出门面（如 `from freegraph.graph import parse_state_schema`） | 门面导出面**恰为 7 个**（B2F2 冻结 · G15 / G19）⇒ **破坏冻结面** |

---

## D-08 · `InvalidSchemaError` 落 L2 + 与「唯一定义处」措辞的关系（**登记**）

**Decision**

```python
# src/freegraph/runtime/errors.py
class InvalidSchemaError(FreegraphError, ValueError):
    key: str | None          # 出错的 key（schema 级错误时为空）
    reason: str              # 原因码（封闭取值域）
```

**Rationale**

- **双重继承**（裁定 2 · Q4）：`FreegraphError` ⇒ 归入内核异常家族，用户 `except FreegraphError` 兜住；
  `ValueError` ⇒ 与上游 `_is_field_binop` 的 `raise ValueError` 同族，用户既有的 `except ValueError` 继续有效。
- **读结构化字段的路径（裁定 14 · 2026-11-08 分析轮调和 Q4 与 Q7）**：澄清 Q7 要求
  「上层只读结构化字段（`key` / `reason`）、不解析消息」，而基类 `FreegraphError` 上**没有**这两个属性
  ⇒ 只留基类捕获路径会让该判据在**类型检查**下不可用 ⇒ **具体子类 MAY 从 `freegraph.runtime`
  import**（**L2 子包** ⇒ 门面 7 符号面与契约层 18 符号面**均不变**；与「`freegraph.contracts`
  也是用户可见路径」的仓库惯例同构）；**捕获**仍用基类即可 ⇒ **Q4 的原意不变**。
- **不写进契约层**：契约层 18 符号面是冻结面（G7 / G8 / API 快照）⇒ 加符号要连带改 4 处工件
  ⇒ 代价与收益不成比例（详见 plan 的 Complexity Tracking）。
- **⚠️ 措辞口径的澄清（登记，不改文件）**：`src/freegraph/contracts/errors.py` 的 docstring 称
  「本文件是内核异常族的**唯一定义处**」，但**同一 docstring** 也写明
  「后续**可新增子类**，但基类名不得改」⇒ 「唯一定义处」的适用范围是
  **基类与既有子类**，而非「未来所有子类」；本 feature **不改**该文件（契约层零改动）⇒
  **登记为措辞口径的澄清**，判据一字未改。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 加进契约层 `__all__`（18 → 19） | **破坏冻结面**（G7 恒红）⇒ 需追认 + 改 4 处工件 |
| 只抛内置 `ValueError` | 脱离内核异常家族 ⇒ 上层无法用统一基类兜住（仓库既有 4 个子类的设计意图被破坏） |
| 在契约层定义但不导出 | 制造「模块内可 import、公开面不可见」的**双重权威** |

---

## D-09 · **零新增门禁编号** —— 既有 G1–G30 自动覆盖新模块

**Decision**

本 feature **不新增**任何门禁编号（既有总数 **30** 与编号连续性**零改动**）。

**Rationale**

- B3F1 的 data-model 不变量：「门禁总数 == 30 · 编号连续」⇒ 新增编号会破坏该不变量。
- 新模块**自动**落在既有门禁的射程内（plan 的「门禁编号纪律」表已逐条列出）：
  G25（导入图 · L2 路径**已登记**）· G30（全仓署名头）· G4 / G24 / G26 / G27（零环境变量 / 零出站）·
  G21 / G22 / G23（零新增依赖 ⇒ 恒绿）。
- 既有 **G5 / G20** 的**硬编码文件清单**（B2F2 落）**刻意不扩** ⇒ 与 B3F1 的处置同构。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 新增一条「schema 解析门禁」 | 破坏「门禁总数 == 30」不变量；且本 feature 的判据**全部**可由 pytest 断言 + 既有门禁承载 |
| 扩 G5 / G20 的硬编码清单 | 需改**既有门禁实现**（B2F2 的冻结面）⇒ 与既有纪律冲突（G30 已覆盖全仓） |

---

## D-10 · 「保序」的精确定义 = `get_type_hints` 的**插入序**

**Decision**

`SchemaSpec.keys` 的顺序 = `typing.get_type_hints(schema, include_extras=True)` 返回映射的**插入序**
（= 声明顺序；继承链上**父类 key 在前**、子类新 key 在后；子类覆盖父类同名 key 时**保持原位**）。

**Rationale**

- **实测**（CPython 3.12.3）：
  ```
  Base.__annotations__  order: ['b1', 'b2']
  Child.__annotations__ order: ['b1', 'b2', 'c1']     ← 父类在前；覆盖的 'b2' 保持原位
  ```
- 该顺序**同时**满足 FR-002 的「保序（声明顺序；继承链的 key 按解析出的顺序追加）」
  与 SC-008 的「条数 == key 数」⇒ 无需另立排序规则。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 按 key 名字典序排序 | 与「**声明顺序**」不符（FR-002），且会让用户 schema 的书写顺序丢失 |
| 必选 key 在前、可选 key 在后 | 与声明顺序不符；且必填性在本 feature **只记录不执行**（FR-021）⇒ 无排序理由 |

---

## D-11 · 测试落 `tests/runtime/` + **CI 零改动**

**Decision**

```
tests/runtime/{__init__.py, conftest.py, test_schema_parse.py,
               test_binary_criterion.py, test_parse_contract.py}
```

**Rationale**

- 与既有 `tests/contracts/` · `tests/facade/` · `tests/gates/` **平级**（仓库「一层一个测试目录」惯例）。
- `pyproject.toml` 的 `testpaths = ["tests"]` ⇒ 新目录**自动被收集** ⇒
  **CI 配置零改动**（`.github/workflows/ci.yml` 的 pytest 步骤是 `pytest tests/ -ra`）。
- **子进程断言**（SC-007：`sys.modules` 增量 / 环境变量读取 / 出站）放在 `tests/runtime/conftest.py`
  的夹具里（沿用 B3F1 的 `tests/gates/conftest.py` 形态：路径基线 + 隔离副本夹具）。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 并入 `tests/contracts/` | 那是**契约层**的门禁目录（G1–G13）⇒ 语义错位 |
| 放进 `tests/facade/` | 那是**门面**的门禁目录（G14–G20）⇒ 语义错位 |
| 新增 CI 步骤 | `testpaths` 已覆盖 ⇒ 多余；且「CI 流水线挂载」按 spec 归 **B3F1**（已完成） |

---

## D-12 · 人工验证记录 = 五段式 + **来源覆盖表**（沿用 B2F2 / B3F1 形态）

**Decision**

`harness/verification/B4F1/manual-verification.md`，五段式（环境 / 步骤 / 实际输出 / 结论 / 遗留问题）
+ 一节**来源覆盖表**（每条判据 → 来源 `路径:行号` / Q8 条号 / 宪法条款号）。

**Rationale**

- 宪法「目录约定」明写 `harness/verification/<feature>/manual-verification.md`；
  宪法原则 V（人工验收是最终验收标准）+ 原则 VIII（证据纪律）⇒ spec FR-018 / SC-013 的落点。
- 「来源覆盖表」是 **B2F2 / B3F1 既有形态**（B3F1 的 SC-003 ① 把「来源覆盖表存在且非空」做成了 pytest 断言）
  ⇒ 本 feature **同构**，使「无来源项数 == 0」可被机器核对。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 只写五段式，不带来源覆盖表 | SC-013 要求「来源覆盖表对全部判据的覆盖率 == 100%」⇒ 必须有该节 |
| 放 `specs/<feature>/` 下 | 违反宪法「目录约定」的人工验证记录落点 |

---

## D-13 · 性能：**不设预算**（登记为 Deferred）

**Decision**

本 feature **不**引入任何性能 / 容量预算（如「解析 100 个 key 的耗时上限」）。

**Rationale**

- 解析是**纯计算**：无 I/O、无网络、无锁、无缓存；输入规模是「一个 schema 的若干个 key」。
- spec 的 Deferred 项已把「导入开销预算」显式列为**低影响** ⇒ 本 plan 采纳该口径。
- ⚠️ **不设预算 ≠ 不测**：SC-005 已断言「两次投影**逐字一致**」，SC-008 已断言「条数 == key 数」，
  ⇒ **确定性**与**规模正确性**都有判据；**耗时**没有判据 ⇒ 登记为 DR-6（归 B5F1 统一测）。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 立一个「解析 1000 个 key < 50 ms」的预算 | ① 无实测基线（本 feature 无热路径）⇒ 阈值凭空虚设；② 该预算的**真正风险面**在通道执行（B5F1）⇒ 归 B5F1 更对口 |

---

## 遗留与登记（不阻塞本 feature）

> **📌 ID 命名空间说明**：本表的编号为 **`DR-n`**（**D** = 本 research 文档的**决策 / 遗留**登记项），
> **与 `plan.md` 的「登记项 R-n」是两个不同的序列** ⇒ 引用时 MUST 带限定语
> （「plan 登记项 R-1」/「research DR-1」）。

| # | 事项 | 归属 |
|---|---|---|
| DR-1 | 上游在场时的**实时对照**差分夹具（同一份 schema 在 `langgraph` 与 `freegraph` 上比对判定结果） | **B5F2 / B8F1**（差分夹具首次建立在 B5F2 · 立项书 §5.2 B5F2 行） |
| DR-2 | Pydantic schema 支持 | **v2.0**（v1.0 无 `[pydantic]` extra · 宪法 v1.7.0 · 立项书 D15） |
| DR-3 | 终版 `COMPAT.md` 的完整兼容矩阵 | **B24F1**（本 feature 零新增公开 API ⇒ 矩阵零新增行） |
| DR-4 | fake 模型注入轮（`init_chat_model` 的 monkeypatch） | **B25F1**（见 plan 登记项 R-1 ②） |
| DR-5 | `Annotated[T, SomeChannel]` 的**通道注解**形态（LangGraph 特有） | **v2.0**（v1.0 由「有无归约器」推导通道 · 裁定 13） |
| DR-6 | **导入 / 解析开销预算**（若要立） | **B5F1**（与通道实现一起测更对口 · D-13） |
| DR-7 | `src/freegraph/contracts/errors.py` 的「内核异常族唯一定义处」措辞的**适用范围**澄清（= 基类与既有子类；未来子类可落在 L2） | **登记，不改文件**（D-08）· 本 feature **零改动**契约层 |
| DR-8 | 「类型可读文本」的规范化口径（`__name__` vs `str()` 去 `typing.` 前缀）若将来需与上游逐字对齐 | **B5F1 / B6F1**（仅影响**日志 / 快照**的可读性，不影响语义） |
| DR-9 | `Annotated[Required[T], reducer]`（`Required` 在 `Annotated` **内层**）形态下 freegraph 与上游是否**逐字一致**（本 feature 只剥离**顶层**包装 ⇒ `value_type` = `Required[T]`） | **B5F2**（差分夹具首次建立 · 立项书 §5.2 B5F2 行）—— 本 feature **不**据此加判据 |
