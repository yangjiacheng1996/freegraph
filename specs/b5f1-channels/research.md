# Research: B5F1 · Channel 抽象 + 三类通道

**Feature**: `B5F1` · 通道抽象 + `LastValue` + `BinaryOperatorAggregate` + `EphemeralValue`
**Spec**: [spec.md](./spec.md) · **核实环境**: CPython **3.12.3**（`python3 -V`）· 上游 `langgraph` **1.2.11**
（`…/site-packages/langgraph/channels/`）· 全部实测命令可复制（见各条的「实测」行）

> **本文件的纪律**（宪法原则 VIII）：每条决策 MUST 附**实测命令 + 真实输出**，或明确标注
> 「源码阅读」并给出 `路径:行号`；**MUST NOT** 用推测填充。
> **口径提醒**：本 feature 的上游对照**只做语义等价**，**MUST NOT** import 上游
> （`langgraph` 不进依赖声明、不进 CI —— 沿用 B4F1 澄清 Q5 的口径）。

---

## 0. 实测取样（原始输出 · 可复制）

### 0.1 空值推导的构造行为（`exp1`）

```text
== 直接构造 ==
  list                                       -> OK   [] (list)
  int                                        -> OK   0 (int)
  str                                        -> OK   '' (str)
  dict                                       -> OK   {} (dict)
  set                                        -> OK   set() (set)
  tuple                                      -> OK   () (tuple)
  list[AnyMessage]                           -> OK   [] (list)
  dict[str, int]                             -> OK   {} (dict)
  tuple[int, ...]                            -> OK   () (tuple)
== 抽象容器 ==
  collections.abc.Sequence                   -> RAISE TypeError: Can't instantiate abstract class Sequence ...
  collections.abc.MutableSequence            -> RAISE TypeError: Can't instantiate abstract class MutableSequence ...
  collections.abc.Set                        -> RAISE TypeError: Can't instantiate abstract class Set ...
  collections.abc.Mapping                    -> RAISE TypeError: Can't instantiate abstract class Mapping ...
== typing 形态 ==
  Annotated[list, 'x']                       -> OK   [] (list)
  Required[list]                             -> RAISE TypeError: Cannot instantiate typing.Required
  NotRequired[list]                          -> RAISE TypeError: Cannot instantiate typing.NotRequired
  typing.Any                                 -> RAISE TypeError: Any cannot be instantiated
  Union[int, str]                            -> RAISE TypeError: Cannot instantiate typing.Union
  list | None                                -> RAISE TypeError: 'types.UnionType' object is not callable
== 上游 _strip_extras 口径 ==
  typing.Annotated[list, 'x']   __origin__=<class 'list'>      strip-> <class 'list'>
  typing.Required[list]         __origin__=typing.Required    strip-> <class 'list'>
  list[dict]                    __origin__=<class 'list'>      strip-> <class 'list'>
  dict[str, int]                __origin__=<class 'dict'>      strip-> <class 'dict'>
  <class 'collections.abc.Sequence'> __origin__=None           strip-> <class 'collections.abc.Sequence'>
  typing.Union[int, str]        __origin__=typing.Union       strip-> typing.Union
  typing.Any                    __origin__=None               strip-> typing.Any
```

### 0.2 抽象类 / 只读属性 / `__slots__` / 规模探针（`exp2`）

```text
== ABC 抽象性 ==
  实例化抽象类 -> TypeError: Can't instantiate abstract class Ch without an implementation
                  for abstract methods 'get', 'update'
  子类实例化 -> Impl
== 只读属性 ==
  赋值 -> AttributeError: property 'value' of 'Impl' object has no setter
== __slots__ 生效 ==
  新增属性 -> AttributeError: 'Impl' object has no attribute 'other'
== 规模口径探针：gc.get_referents ==
  N=1     通道直接引用数=4  映射规模=1
  N=100   通道直接引用数=4  映射规模=100
  N=1000  通道直接引用数=4  映射规模=1000
  ⇒ 通道的直接引用数与 key 数无关 ⇒ 结构上不可能遍历全体 key
  ⚠️ 该「=4」是 exp2 原型（**4 槽**）的实测值；**具体数值随实现而变**（4 槽 + ABC + 实例化子类
     实测为 5~6）⇒ 判据是「**相等**」而非某个数字（裁定 17 ③ · 见 §0.3）
== 归约器不可调用 ==
  callable(3) = False ⇒ 构造期可判定
```

### 0.3 `/speckit.analyze` 轮的实测证据（裁定 17 的依据 · 2026-11-09）

```text
== 上游的清空机制：BaseChannel 无 clear() 方法 ==
  hasattr(BaseChannel, 'clear') -> False
  grep -n "def clear" langgraph/channels/*.py -> （无命中）
  ⇒ 上游**没有** clear()；步末重置靠 update(EMPTY_SEQ)

== 上游三类通道对 update([]) 的反应各不相同（langgraph 1.2.11）==
  LastValue      update([]) -> False   值 5 -> 5    is_available=True   （no-op · last_value.py:56-58）
  BinOp          update([]) -> False   值 [] -> []  is_available=True   （no-op · binop.py:123-125）
  EphemeralValue update([]) -> True    值 7 -> None is_available=False  （清空为 MISSING · ephemeral_value.py:55-61）
  ⇒ 可观察语义等价的落点 = 「步末调用哪些通道」⇒ 步末**只**清路由型（B7F1 · 裁定 17 ②）

== 上游「无值 + 多值首写」：首个直存、其余仍归约（binop.py:126-128 + :143）==
  MISSING + update(['a','b']) -> operator 被调用 1 次，调用参数 ('a','b')，最终值 'ab'
  ⇒ 「归约器调用次数 == 0」**仅对单值写入成立**（裁定 17 ④）

== 子类未声明 __slots__ ⇒ 实例自带 __dict__（可持 4 项之外的数据）==
  class LastValue(Channel):        # 未写 __slots__
      ...
  ch = LastValue('k', int)
  '__dict__' in dir(ch) -> True
  ch.arbitrary = 42  -> 成功
  ⇒ FR-013 / SC-009② / I-1 失守 ⇒ 子类 MUST 声明 __slots__ = ()（裁定 17 ①）

== 公开属性必须沿 MRO 收集（type(ch).__dict__ 只含该类自身定义的属性）==
  type(ch).__dict__ 中的 property -> []          （属性定义在基类 Channel 上时取到空集）
  沿 type(ch).__mro__ 收集 -> ['key', 'value_type', 'value', 'reducer']
  ⇒ 断言 MUST 用 MRO 口径（裁定 17 ①）

== 计数探针对「持有状态表」不敏感（SC-022① 需另加白名单判据）==
  违规实现（额外持有整张状态表 dict）：
    N=1     通道直接引用数=6   含 dict? True
    N=1000  通道直接引用数=6   含 dict? True
  ⇒ 计数**相等**（6 == 6）但引用了状态表 ⇒ 计数探针**检不出**违规 ⇒ 降为辅助判据（裁定 17 ③）

== coverage：无 --branch 时 report 不输出 Branch 列 ⇒ 分支覆盖无从判定 ==
  python -m coverage run     run.py  ->  report: Name Stmts Miss Cover      （无 Branch / BrPart 列）
  python -m coverage run --branch run.py  ->  report: Name Stmts Miss Branch BrPart Cover
  ⇒ 分支覆盖 MUST 以 --branch 取证（裁定 17 ⑤）

== 差分口径可行：新增行号 ∩ coverage json 的 executed_lines / executed_branches ==
  git diff -U0 HEAD -- <file>  -> 新增行号集合 = [5, 6, 7, 8]
  coverage json -> files[...]['executed_lines'] / ['missing_lines'] / ['executed_branches']
  ⇒ 未覆盖的新增行 = added ∩ missing_lines（示例：新增行 [5,6,7,8] ⇒ 已覆盖 [5] · 未覆盖 [6,7,8]）
  ⇒ 文件级 coverage report **无法**区分既有行与新增行 ⇒ MUST NOT 单独作判据（裁定 17 ⑤）
```

---

## 1. 决策（D-01 … D-17）

- **D-01（通道抽象的形态 = `abc.ABC` + `@abstractmethod`）** ——
  **决策**：抽象基类用 **`abc.ABC`**（`update` / `get` / `is_available` 为抽象方法，
  `clear()` 给出**默认无操作**实现）；MUST NOT 用 `typing.Protocol`。
  **实测**：`exp2` ⇒ 实例化抽象类 → `TypeError: Can't instantiate abstract class Ch …`。
  **理由**：① 「唯一实现点」需要一条**运行时可判定**的继承关系 —— `Protocol` 只在**类型检查期**生效，
  运行期 `Channel("k", int)` 仍可实例化 ⇒ 「抽象」会名存实亡；
  ② `ABC` 天然支持「**默认实现**」 ⇒ `clear()` 的默认无操作（spec FR-002）不必在三个子类里重复；
  ③ `Protocol` 会引入**第二个**「通道长什么样」的判定点（结构化子类型 vs 运行时继承）⇒ 违背「收敛」。
  **替代方案**：A `Protocol`（运行时不可约束）✗ · B 鸭子类型（无抽象、无默认实现、三处重复）✗ ·
  C `ABCMeta` 手写元类（与 `abc.ABC` 等价，无额外收益）✗。

- **D-02（属性只读 = `__slots__` + `@property`）** ——
  **决策**：通道用 `__slots__` 持有**私有**槽位（`_key` / `_value_type` / `_value` / `_reducer`），
  公开 **4 个只读 `property`**（`key` / `value_type` / `value` / `reducer`）；`value` **无 setter**。
  **实测**：`exp2` ⇒ `i.value = 5` → `AttributeError: property 'value' … has no setter`；
  `i.other = 1` → `AttributeError: 'Impl' object has no attribute 'other'`（⇒ `__slots__` 生效）。
  **理由**：① spec FR-002 冻结 `value` 为**只读**属性 ⇒ 必须用 property；
  ② `__slots__` 让「通道只持 4 项」（FR-013 / SC-009）成为**结构性事实**而不是约定；
  ③ 私有槽位带下划线前缀 ⇒ 与 4 个公开属性名不冲突。
  **替代方案**：A 公开可写属性 ✗（违反 FR-002「外部 MUST NOT 能改写」）·
  B `__setattr__` 全面拦截 ✗（更重、且拦不住内部状态变更）✗。

- **D-03（「无值」的内部表示 = 模块私有 sentinel，MUST NOT 用 `None`）** ——
  **决策**：模块内定义 `_MISSING = object()`；通道的「无值」= `_value is _MISSING`。
  **理由**：spec FR-011 ③ 要求「值为 `None`」与「无值」**严格可区分** ⇒ `None` 不能兼任「无值」标记；
  用**模块私有** sentinel（而非公开常量）⇒ 用户无法误把它当合法值写入。
  **实测**：`object()` 的恒等判定天然与 `None` 不同（无需额外实验）。
  **上游对照**：上游用 `langgraph/_internal/_typing.py` 的 `MISSING = object()`（同思路）。

- **D-04（`value` 属性在「无值」时抛 `EmptyChannelError`，与 `get()` 同义）** ——
  **决策**：`value` property 在通道「无值」时**抛 `EmptyChannelError`**（与 `get()` 完全同义）。
  **理由**：spec SC-004 要求「有值 / 无值」**不存在第三种模糊状态** ⇒ 若 `value` 在无值时返回 `None`，
  就会出现「`get()` 抛错、但 `value` 返回 `None`」的**第三种语义** ⇒ 与 FR-011 ③ 冲突。
  **替代方案**：A `value` 在无值时返回 `None` ✗（制造第三种语义 + 与「值为 `None`」混淆）·
  B `value` 在无值时返回内部 sentinel ✗（把私有对象泄漏给用户）✗。

- **D-05（空值推导的「剥离」= 窄口径：只剥 `Annotated` / `Required` / `NotRequired`）** ——
  **决策**：按 spec FR-006 ① **逐层**剥离 `Annotated` / `Required` / `NotRequired` 包装，
  **保留**泛型别名（`list[dict]` **不**退化为 `list`）。
  **实测**（`exp1`）：`Required[list]()` → `TypeError` ⇒ **必须**剥，否则空值推导失败 ⇒
  通道初始变成「无值」⇒ 首次写入直存（**与上游分叉**）；`Annotated[list, 'x']()` → `[]`（可剥可不剥，
  剥了更稳）；`list[dict]()` → `[]`（保留泛型别名**结果相同**）。
  **上游对照**（`binop.py:22-28` 的 `_strip_extras`）：**无差别**剥 `__origin__`
  ⇒ `list[dict]` → `list`、`dict[str,int]` → `dict`。
  **⇒ 结论**：freegraph 的**窄口径**与上游的**宽口径**在**空值结果上完全等价**
  （`[]` / `{}` / `()` 都一样），但**机制不同** ⇒ 登记为「机制差异 · 结果等价」（与 spec 裁定 6 同类登记）。
  **理由（保留泛型别名）**：`value_type` 属性 MUST 与 B4F1 的 `ChannelSpec.value_type`
  **同名同义**（spec FR-002）⇒ 保留泛型别名才能让用户看到的类型信息与 schema 里写的一致。
  **替代方案**：A 完全照抄上游的无差别 `__origin__` 剥除 ✗（会把 `list[AnyMessage]` 悄悄变成 `list`，
  与 B4F1 的冻结字段**不等价**）· B 只剥 `Required` / `NotRequired` 不剥 `Annotated` ✗
  （`Annotated[list, op]` 的构造虽然当前可用，但依赖 `_AnnotatedAlias.__call__` 的实现细节 ⇒ 脆弱）。

- **D-06（抽象容器映射表 = 上游同款 6 项）** ——
  **决策**：`collections.abc.Sequence` / `MutableSequence` → `list`；
  `Set` / `MutableSet` → `set`；`Mapping` / `MutableMapping` → `dict`。
  **实测**（`exp1`）：四个抽象容器直接构造**全部**抛 `TypeError`（抽象方法未实现）
  ⇒ 不映射则这类 schema 的通道**永远**是「无值」⇒ 与上游分叉。
  **上游对照**：`binop.py:83-88`（同 6 项 · 逐字同构）。
  **理由**：映射后 `Sequence` → `[]`（可 `+` 拼接）⇒ 与上游的「序列可追加」直觉一致。

- **D-07（「不可实例化」的判定 = 捕获 `Exception`，不含 `BaseException`）** ——
  **决策**：空值推导时 `try: typ() except Exception: → 初始「无值」`。
  **实测**（`exp1`）：`typing.Any()` / `Union[int, str]()` / `list | None` 三类都抛 `TypeError`
  ⇒ 可作「不可实例化类型」的测试夹具（SC-007 覆盖面）。
  **上游对照**：`binop.py:89-92` 同样是 `except Exception` ⇒ 同口径。
  **理由**：捕获 `Exception` 而非 `BaseException` ⇒ `KeyboardInterrupt` / `SystemExit` 不会被吞。

- **D-08（归约型通道的写入 = 「无值 ⇒ 直存首个值；否则逐个归约」）** ——
  **决策**：`update(values)` 的实现顺序：
  ① `values` 为空 ⇒ **无操作**、返回假；
  ② 通道**无值** ⇒ 保存 `values[0]`（**不调归约器**）、其余值按 ③ 继续归约；
  ③ 通道**有值** ⇒ 依次 `self._value = reducer(self._value, v)`。
  **上游对照**：`binop.py:123-144`（`update`）—— 其中 `:126-128` 是「无值 ⇒ 取 `values[0]` 直存」。
  **理由**：与上游**逐条同构**（spec FR-007 ② / 裁定 4）。
  **实测（源码阅读）**：`self.value = self.operator(self.value, value)` 的**赋值发生在 reducer 返回之后**
  ⇒ 归约器抛错时通道值**未被改写** ⇒ 天然满足 spec FR-008「归约失败不得污染状态」。

- **D-09（冲突检测在写入**之前**统一进行）** ——
  **决策**：`LastValue` / `EphemeralValue` 的 `update` 先判 `len(values) > 1` ⇒ **立即**抛
  `InvalidChannelUpdateError`；**不碰**通道状态。
  **上游对照**：`last_value.py:59-64`（抛错在 `self.value = values[-1]` **之前**）；
  `ephemeral_value.py:62-65`（guard 抛错同位置）。
  **理由**：spec SC-006「静默取末值次数 == 0」+ FR-004「MUST NOT 静默丢弃多余值」
  ⇒ 冲突必须是**原子失败**（值不变）。

- **D-10（错误类型的实现形态 = 手写 `__init__` + 结构化字段 + 英文摘要）** ——
  **决策**：`EmptyChannelError(key)` / `InvalidChannelUpdateError(key, received_count, expected_count)`
  各自手写 `__init__`，把结构化字段存成属性，消息是**英文摘要**（点名 key）。
  **理由**：仓库既有错误类（`src/freegraph/contracts/errors.py` 的 `InvalidUpdateError` /
  `GraphRecursionError` / `GraphInterrupt`）**全部**是「手写 `__init__` + 结构化属性 + 英文摘要」
  ⇒ **同构**（spec FR-017 ⑤）。
  **上游对照**：`langgraph/errors.py` 的 `InvalidUpdateError` 亦带结构化字段。
  ⚠️ 错误对象 **MUST NOT** 携带用户写入的**值本身**（spec FR-017 ⑥）⇒ 只带 `key` 与计数。

- **D-11（独立验收脚本的骨架 = 复制 B4F1 的 `acceptance.py`，退出码补 `2`）** ——
  **决策**：`harness/verification/B5F1/acceptance.py` 沿用 B4F1 脚本的骨架
  （`check` / `soft` / `eq` / `_load_runtime` / `_installed` / 两态运行 / `--record` / `--require-installed`），
  **退出码按 spec FR-026 ③ 取 `0` = PASS · `1` = FAIL · `2` = 环境未就绪**。
  **实测（源码阅读）**：`harness/verification/B4F1/acceptance.py`（**1122 行**）——
  其 docstring 写「退出码：`0` = PASS · `1` = FAIL」，而 `harness/verification/README.md`
  写的是「`0` = PASS · `1` = FAIL · `2` = 环境未就绪」⇒ **README 与 spec 一致、B4F1 脚本少一个 `2`**
  ⇒ 本 feature 以 **spec / README** 为准（补 `2`）。
  **理由**：① 同一仓库内**两套**退出码语义会让评审者踩坑 ⇒ 以 README（仓库约定）为准；
  ② B4F1 的骨架已被发起者认可（「一条命令跑完全部验收」）⇒ 复用而非另造。

- **D-12（规模口径的**可判定探针** = `gc.get_referents(channel)` 的元素数）** ——
  **决策**：spec SC-022 的「触及的状态条目数」用 **`len(gc.get_referents(channel))`**
  （通道的**直接引用**对象数）作为探针：schema 有 **1** 个 key 与有 **1000** 个 key 两种情形下，
  该数字 MUST **相等**。
  **实测**（`exp2`）：`N=1 → 4` · `N=100 → 4` · `N=1000 → 4`（恒定）。
  ⚠️ **该「4」是 exp2 原型（4 槽）的实测值**；**具体数值随实现而变**（4 槽 + `abc.ABC` + 未声明
  `__slots__` 的子类实测为 6）⇒ 判据是「**相等**」而非某个数字（裁定 17 ③ · §0.3）。
  **理由**：① 计时类断言在 CI 上**假红**（机器快慢差异）⇒ 不用墙钟；
  ② 数「执行了多少行」会**耦合实现**（重构即假红）⇒ 不用；
  ③ `gc.get_referents` 度量的是**结构**（通道牵住了多少东西）⇒ **与实现细节无关**，
  且它正是 FR-013 ②「MUST NOT 持有其它通道 / 状态表的引用」的**直接可判定形式**。
  **📌 补充（裁定 17 ③）**：③ 只在「**引用数不随 key 数增长**」这一较弱命题上成立 ——
  实测**持有整张状态表**的违规实现，其计数在 N=1 与 N=1000 时**同为 6** ⇒
  **计数相等不蕴含「未持有状态表」** ⇒ SC-022 ① MUST 另以**引用类型白名单**判定，
  计数**降为辅助**判据。

- **D-13（覆盖率取证 = 开发期临时安装 `coverage`，不进仓库依赖）** ——
  **决策**：行/分支覆盖 100% 的取证在**开发期**完成：
  `python -m coverage run -m pytest tests/runtime` → `python -m coverage report --include="src/freegraph/runtime/*"`
  ⇒ 实测输出粘进 `harness/verification/B5F1/manual-verification.md` 第 3 节。
  **理由**：v1.0 **依赖面为零**（宪法 v1.7.0 · `pyproject.toml` 的 `dependencies = []`）
  ⇒ `coverage` **MUST NOT** 写进任何依赖声明（spec FR-019 ②）；
  **替代方案**：A 把 `coverage` 写进 `[dependency-groups] dev` ✗（MUST NOT 把覆盖率工具写进仓库依赖声明）·
  B 不测覆盖率 ✗（spec SC-015 明写 100%）✗。

- **D-14（`build_channels` 的返回类型 = `dict`（保序、可变））** ——
  **决策**：`build_channels(schema_spec) -> dict[str, Channel]`（`dict` 自 3.7 起**保序**）。
  **理由**：① spec FR-012 ④ 只要求「**保序**」+ 每个 key 恰一个通道；
  ② 下游（**B5F2** 读取层 / **B7F1** 调度层）需要在这份映射之上**增补内部通道**
  （如路由通道）⇒ 可变字典省一次拷贝；
  ③ **登记（与 B4F1 的形态差异）**：B4F1 的 `SchemaSpec.channels` 是**不可变**映射
  （`MappingProxyType`）—— 那是**冻结的解析产物**；本 feature 返回的是**活的通道集合** ⇒ 形态不同、用途不同。
  **替代方案**：A `MappingProxyType`（不可变）✗（下游增补内部通道时需先拷贝，多一次心智负担）·
  B `OrderedDict` ✗（3.7 起 `dict` 已保序 ⇒ 冗余）。

- **D-15（`build_channel` 的入参 = B4F1 的 `ChannelSpec` **具体类型**）** ——
  **决策**：`build_channel(spec: ChannelSpec) -> Channel`（**直接** import B4F1 的类型，
  不另定义 Protocol / 鸭子协议）。
  **理由**：① 两者**同在 L2**（`freegraph.runtime`）⇒ 直接 import 无层间依赖问题；
  ② B4F1 已**逐字冻结**字段名（`key` / `value_type` / `reducer` / `has_reducer` / `semantics` / `required`）
  ⇒ 再定义一个 Protocol 就是**第二个**「通道规格长什么样」的判定点 ⇒ 违背「收敛」。
  **替代方案**：A 定义 `ChannelSpecLike` Protocol ✗（第二判定点）·
  B 用 `dict` 传参 ✗（丢掉类型检查，且与 B4F1 的形状脱钩）✗。

- **D-16（参数化组合测试的落点 = 本 feature · 立项书 S5 ③）** ——
  **决策**：本 feature MUST 提供一组**参数化组合测试**（`pytest.mark.parametrize`），
  枚举「**归约器类型** × **通道类型**」（归约器：`operator.add` / `max` / 自定义二元函数；
  通道：`LastValue` / `BinaryOperatorAggregate` / `EphemeralValue`）⇒ 组合数 **≥ 12**，
  每组自带**相容的值类型**；MUST **NOT** 用 `skip` / `xfail` 掩盖组合。
  **理由**：① 立项书 §4.2 **S5**「语义等价」的**第三层证据**（「属性 / 参数化测试：枚举 reducer 类型 ×
  通道组合」）在此之前**无承接方** —— 其落点说明只把**差分夹具**指给 **B5F2 / B8F1**，
  而那两个 feature 的差分夹具是「同一张图跑两个框架」，**不等于**「枚举 reducer × 通道的组合」；
  ② B5F1 是「**通道 × 归约器**」的**唯一落点** ⇒ 该层证据 MUST 落在此；
  ③ 与本 feature 已有的「行/分支覆盖 100%」要求**同向**（组合测试天然覆盖多分支）⇒ 成本可接受。
  **落点**：spec **FR-027 / SC-028** · tasks **T031** · plan Constraints 表。

- **D-17（清空语义统一为「三类一律 ⇒ 无值」+ 规模判据补白名单 + 覆盖率取证口径 · 本轮 analyze 轮）** ——
  **决策**：① `clear()` 的语义**三类统一**（覆盖型 MUST 覆写）—— 以 spec 为上位文档回修 contract §3.1；
  ② **上游逐类实测**（§0.3）：上游**无** `clear()`，三类通道对 `update([])` 反应**各不相同**
  （覆盖型 / 归约型 no-op、路由型清空）⇒ **等价落点是「步末调用哪些通道」**（B7F1：步末只清路由型）；
  ③ 规模判据**补引用类型白名单**（计数探针**降为辅助** —— 实测其对「持有状态表」不敏感）；
  ④ 「归约器调用次数 == 0」**限定单值写入**；⑤ 分支覆盖**必须 `--branch`** 取证 + 「新增部分」用**差分口径**。
  **理由**：①②③④⑤ 均属**可判定性 / 上游等价**的补齐（与 Q8 / Q14 / Q15 同性质），
  **无**一条要求改变本 feature 的**交付面**或**语义方向**；① 的两个互斥口径中，
  contract §3.1 与 spec 的**四处**「清空后一律为无值」相悖 ⇒ 按 contract 自身的
  「冲突时以 spec 为准」规则回修 contract。
  **落点**：spec **裁定 17**（五条逐条落点）· FR-002 / FR-006① / FR-007② / FR-009 / FR-012② /
  FR-013① / FR-019② / SC-004③ / SC-007 / SC-022①② / SC-023④ · contracts §1 / §2.2 / §3.1 /
  §3.2 / §6（I-1 / I-2 / I-4 / I-5 / I-10 / I-12）/ §7（`B-2`）· upstream-parity **P-12 / S-05** ·
  data-model §2.1 / §2.2 / §2.3 / §3.1 / §3.2 / §3.3 / §4 · tasks **T007 / T012 / T015 / T019 /
  T024 / T029 / T036** · plan Constraints 表 · quickstart §7 / §8 ③。

---

## 2. 遗留登记（DR-1 … DR-6）

| # | 遗留项 | 影响 | 承接方 | 处置 |
|---|---|---|---|---|
| **DR-1** | 通道的**相等判定 `__eq__`** 与**可打印表示 `repr`** 未在 spec 冻结（本轮 clarify 的 Outstanding） | **低** —— v1.0 无消费者（快照 / checkpoint 尚未存在） | **B14F1**（checkpoint 落地时按需冻结） | 本 feature **不实现** `__eq__`；测试**不用**通道相等做断言（改用属性逐项断言） |
| **DR-2** | `value_type` 的**「类型可读文本」口径**未冻结（含泛型参数如何展示） | **低** —— 本 feature 只保留**类型对象**本身，不做文本投影 | **B4F1**（已有投影口径）· **B14F1** | 本 feature **不做**类型文本投影；`value_type` 直接暴露类型对象 |
| **DR-3** | 上游的 **`Overwrite` 旁路值**（`binop.py:31-51`） | **无** —— 不在最小契约 C1–C27 内 | 无（v1.0 不做） | spec FR-018 已列为 Out of Scope |
| **DR-4** | **`EphemeralValue` 的清空机制**与上游不同（freegraph = 显式 `clear()`；上游 = `update(空序列)`） | **无**（可观察语义等价） | 无 | spec 裁定 6 已登记；**不进**兼容矩阵（本 feature 零新增公开 API） |
| **DR-5** | **层注册表的一处措辞已过时**：`specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md:98` 仍写着 `src/freegraph/runtime/`「**尚未存在**」，而 B4F1 已创建该目录 | **无**（不影响判定 —— 行的**层归属（L2）**本身正确） | **B3F1**（层注册表的**权威持有者**） | 本 feature **MUST NOT** 改层注册表（spec FR-016 · 层注册表是**冻结面**）⇒ **只登记、不修改**；该措辞的刷新归 B3F1 的后续维护 |
| **DR-6** | **步末「清空哪些通道」的范围**由调度层决定（B7F1）—— 上游靠 `update(EMPTY_SEQ)` 隐式达成（覆盖型 / 归约型 no-op），freegraph 改为**显式** `clear()`（三类一律 ⇒ 无值）⇒ 若 B7F1 在步末对**全部**通道调 `clear()`，覆盖型的「末值保留」与归约型的「累积保留」会被抹掉 ⇒ **与上游分叉** | **中** —— 影响 C2 / C3 的跨步等价 | **B7F1**（调度层） | 本 feature 只**冻结 `clear()` 的语义**（三类一律 ⇒ 无值）；**步末调用范围**归 B7F1 ⇒ 已写入 contract §7 `B-2` + `upstream-parity` **P-12 / S-05** + spec 裁定 17 ② ⇒ **B7F1 的提示词 MUST 承接这条**（步末**只**清路由型） |

---

## 3. 与上游的等价性小结（供 `contracts/upstream-parity.md` 取样）

| 语义点 | freegraph | 上游（`langgraph 1.2.11`） | 行号 |
|---|---|---|---|
| 覆盖语义 | `LastValue.update` 覆盖 | `self.value = values[-1]` | `channels/last_value.py:66` |
| 一步内多值 ⇒ 失败 | `InvalidChannelUpdateError` | `InvalidUpdateError` | `channels/last_value.py:56-67` |
| 空值推导 | 剥包装 → 抽象容器映射 → 构造空实例 | 同 | `channels/binop.py:82-92` |
| 首次写入的 `current` | 有值 ⇒ 归约；无值 ⇒ 直存 | 同 | `channels/binop.py:123-144`（尤其 `:126-128`） |
| 归约调用形式 | `reducer(current, new)` | `self.operator(self.value, value)` | `channels/binop.py:143` |
| 路由通道清空 | 显式 `clear()` | `update(空序列)` | `channels/ephemeral_value.py:55-60` · `pregel/_algo.py:326-334` |
| **清空语义（三类统一）** | 三类 `clear()` **一律** ⇒ 无值 | **无 `clear()` 方法**；步末 `update(空序列)`：覆盖型 / 归约型 **no-op** · 路由型 ⇒ `MISSING` | `channels/base.py:19-121` · `channels/last_value.py:56-58` · `channels/binop.py:123-125` · `channels/ephemeral_value.py:55-61` |
| 有值 / 无值判定 | `is_available()` + `get()` 抛错 | 同 | `channels/last_value.py:69-75` |
| C4 稀疏读 | 跳过抛 `EmptyChannelError` 的通道 | 同 | `pregel/_io.py:38-53` |
| 写入批量交给通道 | `update(values)` | `channels[chan].update(vals)` | `pregel/_algo.py:317-320` |
| 映射规则 | 有归约器 ⇒ BinOp；否则 ⇒ LastValue | 同 | `graph/state.py:1850-1873` |

> ⚠️ **换上游版本后 MUST 重新核实全部行号**（宪法原则 VIII · spec FR-021）。
