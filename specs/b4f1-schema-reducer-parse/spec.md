# 功能块 Specification: B4F1 · 状态 schema 解析 + 归约器提取（`TypedDict` + `Annotated` → 通道规格）

**Feature Branch**: `b4f1-schema-reducer-parse`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`
⇒ 无 `before_specify` 钩子；既有 4 个 feature（B1F1 / B2F1 / B2F2 / B3F1）同样在 `main` 上开发）

**Created**: 2026-11-08

**Status**: Draft

**Input**: User description: "B4F1 · schema 解析 + 归约器提取" —— 完整提示词正文见
`harness/features/B4F1_schema解析与归约器提取.md`。要点：把用户写的**标准 `TypedDict` 状态 schema**
翻译成**通道规格**（schema 的每一个 key 一条），并从 `Annotated` 元数据中**提取二元归约器**；
核心判定 = `Annotated[list[AnyMessage], operator.add]` MUST 被识别为**二元归约器**（而不是被当成
普通注解忽略）。本 feature **只解析、不执行**：通道实现属 **B5F1**，稀疏状态读取属 **B5F2**，
`StateGraph` 构建器属 **B6F1**。

---

## 澄清与裁定

> 本节记录本 feature 的**裁定**（提示词未逐字规定、或与仓库既有冻结面 / 上游行为存在张力处的取舍）。
> 全部裁定均已闭合，正文**无未闭合的澄清标记残留**。

### Session 2026-11-08

> 本节含**两轮澄清 + 一轮分析**：**第一轮 Q1–Q5**（数据契约 / 必填性 / 报错方式 / 错误落位 / 上游依赖）·
> **第二轮 Q6–Q10**（候选归约器范围 / 错误结构化字段 / 字段名冻结 / 判定表覆盖面 / 投影标识规则）·
> **分析轮**（2026-11-08 · `/speckit.analyze` 的 13 项发现 ⇒ 裁定 14 与措辞收敛）。
> 全部**逐条落回正文**，正文**无未闭合的澄清标记残留**。

- **Q1（通道规格的「类型信息」存什么）** → **A** —— **只存基类型 `T`**：
  `Annotated[list[AnyMessage], operator.add]` → 类型信息为 `list[AnyMessage]`；无 `Annotated` 时即该 key 的类型。
  **理由**：基类型正是「这个 key 到底存什么」的唯一答案；把原始注解（解析的**输入**）留在解析**产物**里，
  会诱使下游二次解析元数据，反而多一处分歧点。
  **落点**：FR-002（追加「类型信息 = 归约前的基类型」定义）· FR-020 ①（追加「MUST NOT 保留 `Annotated` 包装 /
  原始注解对象」）· Key Entities「通道规格」· 追溯表（FR-002 → SC-001 / SC-008 口径不变）。

- **Q2（可选 key · `total=False` / `NotRequired[...]` 支持到什么程度）** → **A** —— **记录但不执行**：
  解析 `__required_keys__` / `__optional_keys__`，在通道规格里带一个「必选 / 可选」标记；
  本 feature **不执行任何必填性校验**（校验归 B7F3），也**不因 key 可选而拒绝 schema**。
  **理由**：① 必填性是 B7F3（调用入参校验）迟早要用的信息，现在记录成本近乎为零，
  将来 B7F3 不必回头改本 feature 已冻结的数据契约；② 「记录但不执行」让本 feature 守住
  「只解析」的边界；③ Option B（直接报错）会在用户最常见的 `total=False` 写法上直接拒绝，
  代价大而收益为零；④ Option C（不记录）会让 B7F3 拿不到必填性，只能重新解析一遍。
  **实测依据**：`__required_keys__` / `__optional_keys__` 在 `typing.TypedDict` 与
  `typing_extensions.TypedDict` 上均可用（CPython 3.11 / 3.12 实测）；
  但在 `from __future__ import annotations` 下，CPython **识别不出**字符串里的
  `Required` / `NotRequired`（全部记为必选）⇒ 标记 MUST **照抄**、MUST NOT 自造判定逻辑。
  **落点**：**新增 FR-021**（必填性只记录不执行）· FR-020 ①（字段清单追加「必选/可选标记」）·
  **新增 SC-016** · Edge Cases 追加 2 条 · Key Entities 追加「必选/可选标记」· 追溯表追加 FR-021 行。

- **Q3（一份 schema 有多个问题时怎么报错）** → **A** —— **快速失败**：按 key 的解析顺序逐个检查，
  发现**第一个**问题即抛出，MUST NOT 汇总多个问题后一次抛。
  **理由**：① 与上游 LangGraph 行为一致（上游逐个 key 判定，命中即抛）；② 实现最简单、
  错误定位最直接（一个错误 ⇒ 一个 key ⇒ 一处修改）；③ 汇总的收益有限 —— 用户的 schema
  通常只有一两个问题，汇总反而让错误对象变复杂、且要设计「多问题」的结构化字段；
  ④ Option C（部分成功、不抛异常）会让一个 key 被静默漏掉 ⇒ 状态丢失风险，不采用。
  **落点**：FR-007 ④（新增「MUST 快速失败」）· SC-006（追加「多问题 schema 抛错次数 == 1」）·
  Edge Cases 追加 1 条。

- **Q4（「schema 非法」错误类型放哪、用户怎么捕获）** → **A** —— **放在 L2、靠基类捕获**：
  错误类型定义在内核层，**不进入**契约层 18 符号面、**不进入**门面 7 符号面；
  用户侧 `except FreegraphError`（`freegraph.contracts` 导出的内核异常基类）或
  `except ValueError` **均**能捕获到它，MUST NOT 要求用户 import 具体的错误子类。
  **理由**：① 与仓库既有异常体系一致（`InvalidUpdateError` 同样只从基类捕获，
  上层「只捕获基类即可兜住全部内核错误」是既有设计意图）；② 契约层 18 符号面与门面 7 符号面
  是**冻结面**（G7 / G15 / G19），加一个错误类型会连带要改公开面文档、门禁、API 快照与兼容矩阵
  —— 代价与收益不成比例；③ Option C（直接抛内置 `ValueError`）会让 schema 错误**脱离**内核异常家族，
  与仓库既有体系不一致。
  **落点**：FR-007 ⑤（新增「捕获路径」）· 裁定 2 追加「捕获路径」段 · SC-006（追加捕获成功率 == 100%）。

- **Q5（A2 的上游实时对照要不要在本 feature 就装 `langgraph` / 进 CI）** → **A** ——
  **本 feature 零依赖声明、CI 不装 `langgraph`**：仓库的 `dependencies` /
  `[project.optional-dependencies]` / `[dependency-groups]` **三处均不出现** `langgraph`；
  CI 作业内**不安装**它；「上游在场时的实时对照」**不落进本 feature 的 CI**，
  留给 **B5F2 / B8F1** 的差分夹具（立项书已在那里预留 dev/test 依赖位）。
  **开发者本机临时装一份 `langgraph` 当参考读物 / 对照工具**（核实判定表用）是**允许**的
  —— 它**不写进仓库**，用完即弃 ⇒ 既拿到了「对着上游核实」的好处，又不让项目对上游产生依赖。
  **理由**：① CI 需要的是**可复现的断言**，不是每次都去跑一遍上游 —— 判定表是上游行为的
  **固化快照**，上游升级**不会**让本 feature 的 CI 变红；② Option B 会把上游变成 CI 的
  硬依赖：7 个作业都要装（含 3.14 档 —— `langgraph` 声明 `Requires-Python: >=3.10` 无上界，
  但它拖的 `pydantic-core` 是编译轮子，能否装成功**未实测**），风险与收益不成比例；
  ③ Option C 虽然 CI 不跑，但仍把上游写进依赖声明，等于给「以后有人加进 CI」留了个口子。
  **落点**：FR-016 ②③④ · 裁定 8（改写为「不进 CI」）· SC-004（改写：判定表一致率 == 100% +
  CI 安装次数 == 0 + 依赖声明出现次数 == 0）· FR-019（改为「零新增依赖声明」，含开发期依赖组）·
  Edge Cases 追加 1 条（判定表 = 快照 · 换版本须重新核实）。

- **Q6（第二轮澄清 · 末位元素是「类」或「可调用实例」时怎么判）** → **A** —— **纯机械判定**：
  候选只看「末位元素是不是 callable」+「位置参数计数」，**类与可调用实例都不特殊排除**。
  **理由**：① 与上游 `_is_field_binop`（`state.py:1904-1922`）**逐条一致** ⇒ A2 判据零差异、
  兼容矩阵**无需**登记差异；② 上游行为相同 ⇒ 不会出现「同一份 schema 在两个框架里语义不同」——
  这比「类被误当归约器」更糟；③ Option B（排除类）虽然更安全，但会在 A2 上产生**可观测的行为差异**，
  须额外登记兼容矩阵并写差异说明。
  **⚠️ 本条修正了裁定 9 的漏洞**：原表述「类在末位 ⇒ 拒绝」**只对「`__init__` 无参的类」成立**
  （实测 `signature(NoInit)` = `()`）；`class TwoArgInit`（`__init__(self, a, b)`）的签名恰是 `(a, b)`
  ⇒ 机械判据**会**把它接受为归约器（运行期 = `TwoArgInit(current, new)` 构造实例，与上游同构）。
  **落点**：裁定 9（**改写** + 补 7 条实测事实 + 修正说明）· FR-003 ③（新增「类与实例不例外」）·
  Edge Cases（原「类末位 ⇒ 拒绝」一条**改写**为 3 条：类 / 可调用实例 / partial 与绑定方法）·
  「依据」节补实测行。

- **Q7（第二轮澄清 · 错误对象要不要带结构化字段）** → **A** —— **带结构化字段**：
  错误对象上放「**出错的 key**」+「**原因码**」（取值域封闭）：
  `not_a_typed_dict` / `reducer_not_binary` / `annotation_unresolvable`（与 FR-007 的三类非法输入一一对应）；
  消息文本**只作英文摘要**（沿用仓库既有约定 `contracts/errors.py`：「缺省摘要为**英文**」），
  上层 MUST **无须解析消息**即可取到全部细节。
  **理由**：① 与仓库既有异常体系**同构**（`InvalidUpdateError` 暴露 `invalid_keys` 结构化字段，
  消息只是摘要）—— 本 feature 不应另立一套；② 上层（freechain）要按「哪个 key、什么原因」
  分支处理，解析消息文本会把措辞变成 API 契约（改一次文案就崩）；③ Option B（只给消息）
  违背仓库既有约定；④ Option C（再带「期望 / 实测签名」）信息更全，但会把「实测签名文本」
  也变成冻结面，而它随上游版本漂移 —— 记在**人工验证记录**里更合适。
  **落点**：FR-007 ⑥（新增「结构化字段」+ 原因码取值表）· Key Entities 新增「解析错误」·
  **新增 SC-017** · Q7 记注。

- **Q8（第二轮澄清 · 字段名要不要现在冻结）** → **A** —— **全部现在冻结**：
  `ChannelSpec` = `key` / `value_type` / `reducer` / `has_reducer` / `semantics` / `required`；
  `SchemaSpec` = `channels`（保序映射）/ `keys`（有序序列）。
  **理由**：① 本 feature 的产物是 **B5F1 → B6F1** 之间的**跨 feature 契约**（不是内部实现细节）——
  字段名若不冻结，三个 feature 各写各的，等于没有共同契约，发现不一致时已各改一遍；
  ② 仓库既有先例支持：B1F1（四个核心类型）/ B2F1（五个协议与五个纯数据类）都**逐字冻结**了字段名；
  ③ 冻结后改名要走评审 —— 这正是「冻结面」应有的分量；
  ④ 只冻结**字段名与取值域**，**实现形态**（dataclass / NamedTuple）与**解析入口函数名**仍留给 plan。
  **落点**：FR-020（**改写**为含字段名的表格 + 实现形态留给 plan）· Key Entities 两条（补字段名）·
  澄清记录 Q8。

- **Q9（第二轮澄清 · 判定表的最低覆盖面）** → **B** —— 判定表 MUST 覆盖
  **「二元性判定」≥ 14 类形态**（**实际落 16 类** · 见 FR-016 ①-a 与 `contracts/binary-criterion.md` §2；
  位置专用 2 参 / 位置或关键字 2 参 / 3 参 / 1 参 / `a,*args` /
  `a,b,*args` / `a,b,*,c` / `*,a,b` / 类（`__init__` 无参 · 1 参 · 2 参）/ 可调用实例（`__call__` 2 参 ·
  keyword-only）/ `functools.partial` / 绑定方法 / 签名不可取）+ **「归约器提取」≥ 2 类形态**
  （末位非 callable / 多条目元数据）。
  **理由**：① 这些形态**恰好对应上游判据的每一个分支**（末位 callable 检查 → 签名计数 → 计数 ≠ 2 抛错）
  ⇒ 覆盖它 = 覆盖上游的全部分支，缺口归零；② 判定表是 A2 的**唯一自动化载体**（Q5 已定 CI 不装
  `langgraph`）⇒ 覆盖面不足 = 上游行为漂移与自身判据错误都测不出来；③ Option A（最小 4 类）
  漏掉类 / 实例 / `*args` / keyword-only / 签名不可取等分支 —— 恰好是**最易写错**的几类；
  ④ Option C（不设下限）等于把覆盖面交给实施者，结果不可核对。
  **落点**：FR-016 ①-a（**形态清单** 16 类 · **判定表本体只在 `contracts/binary-criterion.md` §2** ——
  spec **不复制表格** · 2026-11-08 分析轮修订）/ ①-b（提取形态 2 类）· SC-004（追加
  「缺失条数 == 0」+「覆盖面下限 16 类」· 对应任务 T046 的**行数断言**）· 澄清记录 Q9。

- **Q10（第二轮澄清 · 投影里归约器的可读标识规则）** → **A** —— **模块名 + 限定名**
  （`operator.add` / `myapp.reducers.merge`）；取不到时退回 `__name__`，再取不到才用 `repr`。
  **落点细化（由本次决策连带补齐的两处漏洞）**：
  ① **可调用实例**（无 `__qualname__`，但 Q6 已判定它可以是归约器）⇒ 标识取**其类型**的
  模块名 + 限定名，否则会落到带地址的 `repr` ⇒ 快照假红；
  ② **兜底 `repr`** MUST **抹除内存地址形态**（`0x…` → 固定占位）⇒ 满足 SC-005 的
  「两次投影逐字一致」。
  **理由**：① 「模块名 + 限定名」既稳定又可定位（能直接定位到源码位置）；
  ② `repr` 对 lambda 会给出 `<function <lambda> at 0x7f...>` ⇒ **含地址** ⇒ 快照必假红；
  ③ 只用 `__name__` 分不清 `a.add` 与 `b.add`；④ Option D（用户自定义标识）要新增 API 面，
  与「本 feature 零新增公开 API」相悖。
  **落点**：FR-011（**改写**：标识规则 4 级 + 不含地址）· SC-005（追加「含地址条目数 == 0」）·
  Edge Cases 追加 2 条（lambda 标识 / 可调用实例标识）· 澄清记录 Q10。

- **裁定 1（非法 schema 与「非二元 callable」= 抛错 · 绝不静默降级）**：
  提示词 FR-006 要求「抛错**或**降级为无归约器」二选一并「在 spec 中写死」——
  本 spec 选**抛错（fail-fast）**，落在 FR-007。
  **依据**：① **A2** 要求二元性判据与 LangGraph 一致 —— 上游在「末位可调用但位置参数数 ≠ 2」时
  **raise `ValueError`**（`langgraph/graph/state.py:1917-1921`），并非降级；
  ② 提示词 §10 的风险提示（「判据错误**只在运行期暴露**」）⇒ 解析期抛错是**唯一**能提前暴露的时机；
  ③ 「静默降级为无归约器」会把用户的**追加**语义偷换成**覆盖**语义 —— 这是**静默改变用户意图**，
  比报错坏得多（提示词 P1 的价值直接被摧毁）。
  **与 SC-003 的口径对齐**：SC-003 说「位置参数数 ≠ 2 时 100% 不被当作归约器」——
  在抛错口径下，该 callable **100% 不会被接受为归约器**，且**整次解析失败**
  （MUST NOT 静默当作无归约器）。二者不冲突，已在 SC-003 中逐字写死。

- **裁定 2（异常类型 = `InvalidSchemaError`，双重继承 `FreegraphError` + `ValueError`）**：
  新增异常类型 `InvalidSchemaError`，MUST 继承 **L1 契约层既有的 `FreegraphError`**（仓库异常体系）
  **且**继承 **`ValueError`**（上游抛 `ValueError`）⇒ ① 与仓库既有异常体系一致；
  ② 用户既有的 `except ValueError` 代码在 freegraph 上继续有效；③ A2 的比对口径是
  **判定结果**（接受 / 拒绝）**而非异常类型逐字相同**。
  `InvalidSchemaError` MUST **定义在 L2**（`src/freegraph/runtime/`）——
  契约层 18 符号面是冻结面（G7），MUST NOT 因本 feature 扩容。
  **捕获路径（澄清 Q4）**：用户侧 `except FreegraphError`（`freegraph.contracts` 的导出基类）
  与 `except ValueError` **均**能捕获到它；具体子类**不进入**任何公开符号面
  ⇒ 契约层 18 符号面与门面 7 符号面**零改动**。

- **裁定 3（`TypedDict` 的判定 MUST 用鸭子口径 —— `typing.is_typeddict` 认不出 `typing_extensions.TypedDict`）**：
  **实测**（CPython 3.11.16 + typing_extensions 4.16.0）：`typing.is_typeddict(typing_extensions.TypedDict(...))`
  **返回 `False`**（而 `typing.is_typeddict(typing.TypedDict(...))` 为 `True`）。
  ⇒ 只用 `typing.is_typeddict` 会把 `harness/demo/target.py:59-61` 用的 schema
  （`from typing_extensions import TypedDict`）判成「非 TypedDict」⇒ **验收基准直接不可用**。
  ⇒ 判定口径冻结为 **`typing.is_typeddict(x)` 为真，或 `x` 同时满足「是类 + 是 `dict` 的子类 +
  有 `__annotations__` + 有 `__total__`」**（鸭子判定，覆盖 `typing_extensions` 及其它实现的 TypedDict）。
  内核 MUST NOT import `typing_extensions`（零第三方依赖 · 宪法原则 II / 包层白名单 v1.7.0）
  ⇒ 只能走鸭子口径。

- **裁定 4（`Required` / `NotRequired` 包装 MUST 先剥离，否则归约器会被漏掉）**：
  **实测**：`typing.get_type_hints(S, include_extras=True)` 对 `Required[Annotated[list, operator.add]]`
  返回 `Required[Annotated[list, operator.add]]` —— 包装**保留**，且 `__metadata__` **不在顶层**
  （顶层 `__metadata__` 为 `None`）⇒ 不剥离就**必然漏掉** `Required` 包裹的归约器。
  上游做法 = **先剥离、再判二元**（`langgraph/graph/state.py:1853-1858`）⇒ freegraph MUST 同序。
  ⇒ FR-008。`Required` / `NotRequired` 是 **Python 3.11** 就有的构件（PEP 655），在 typing 构件上限内。

- **裁定 5（注解 MUST 解析，MUST NOT 照抄 `__annotations__`）**：
  MUST 以**保留 `Annotated` 附加信息**的方式解析注解（等价于 `get_type_hints(..., include_extras=True)`）
  —— 否则 ① 字符串注解（`from __future__ import annotations`）与前向引用无法解析；
  ② `Annotated` 元数据会被剥掉（`include_extras=False` 时元数据直接消失）⇒ 归约器**必然丢失**。
  解析失败（不可解析的前向引用）MUST 抛 `InvalidSchemaError`，
  MUST NOT 静默退回原始 `__annotations__`（那会得到一份「看起来能跑、实际丢掉归约器」的规格）。
  ⇒ FR-007 ③ / FR-009。

- **裁定 6（通道规格的落位与「不是公开 API」）**：
  `ChannelSpec` / `SchemaSpec` 落在 **L2**（`src/freegraph/runtime/`）⇒
  ① **不进**契约层 18 符号面（G7 冻结）；② **不进**门面 7 符号面（G15 / G19 冻结）⇒
  **对用户不是公开 API**，由 B5F1 / B6F1 **内部消费**。
  ③ **「公开面」的判定口径**（2026-11-08 分析轮澄清）：**公开面 = 契约层 18 个符号 + 门面 7 个符号**
  ⇒ `freegraph.runtime` 的 4 个导出（`parse_state_schema` / `ChannelSpec` / `SchemaSpec` /
  `InvalidSchemaError`）属 **L2 内部 API**（用户**MAY** import，但**不承诺稳定**）
  ⇒ **不进 API 兼容矩阵**（README 的兼容矩阵**零新增行**）。
  **层注册表零改动**：`specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md` 已登记
  `src/freegraph/runtime/` = **L2**（B4F1 起）⇒ 本 feature MUST NOT 改动该冻结面。

- **裁定 7（Pydantic schema 在 v1.0 明确不支持）**：
  宪法 **v1.7.0** 已把四个 optional extra（含 `[pydantic]`）**移入 v2.0 范围** ⇒ v1.0 的
  `pyproject.toml` MUST NOT 含 `[project.optional-dependencies]` ⇒ 本 feature **只支持 `TypedDict`**。
  Pydantic 模型（`BaseModel` 子类）MUST 被**显式拒绝**（抛 `InvalidSchemaError`），
  MUST NOT 静默接受、也 MUST NOT 因此引入 `pydantic` 依赖。
  **依据**：立项书 **D15** 已把「B4F1 / B5F1（schema 校验）」在 v1.0 定位为
  「**降级为标准库 / 自研替代**」⇒ 本裁定与上位文档同向，不构成偏离。

- **裁定 8（A2 的比对方式 = 自包含判定表；上游实时对照不进本 feature 的 CI）**：
  `langgraph` 是**仅 dev/test** 依赖（立项书 §5.2 B5F2 行：「`langgraph` **仅作 dev/test 依赖**，
  不入 `Requires-Dist`」）⇒ A2 的比对 MUST 有一份**自包含**的判定表
  （每条用例写明上游语义 + 来源 `路径:行号`）作为回归基线；
  判定表是**上游行为的固化快照** ⇒ 上游升级**不会**让本 feature 的 CI 变红。
  **本 feature MUST 零依赖声明、CI MUST NOT 安装 `langgraph`**（澄清 Q5）；
  「上游在场时的实时对照」留给 **B5F2 / B8F1** 的差分夹具（那里已按立项书预留 dev/test 依赖位）。

- **裁定 9（候选归约器的范围 = 任何 callable · 类与实例不例外 · 「签名不可取」= 拒绝）**：
  候选判据是「**末位元素是 callable**」—— **类**与**可调用对象实例**都**不**被特殊排除，
  完全按 `inspect.signature` 的**位置参数计数**机械判定（澄清 **Q6**）。
  **实测事实**（CPython 3.12.3 · 类名已统一为契约 §4 的**夹具名**）：
  `class ClassNoInit`（`__init__` 无参）⇒ pos=**0** ⇒ 拒绝；
  `class ClassTwoArgInit`（`__init__(self, a, b)`）⇒ pos=**2** ⇒ **接受为归约器**
  （运行期语义 = `ClassTwoArgInit(current, new)`，即构造实例 —— 与上游**同构**）；
  `class ClassOneArgInit` ⇒ pos=1 ⇒ 拒绝；自定义 `__call__(self, a, b)` 的实例 ⇒ pos=2 ⇒ 接受；
  `__call__(self, *, a, b)` 的实例 ⇒ pos=0 ⇒ 拒绝；`functools.partial(add, 1)` ⇒ 签名 `(b, /)` ⇒ pos=1 ⇒ 拒绝；
  绑定方法 ⇒ pos=1（`self` 已绑定）⇒ 拒绝。
  **签名取不到**（如内置 `max` / `str` —— `inspect.signature` 抛 `ValueError`）⇒ 判为**非二元** ⇒ 拒绝。
  上游**同构**（`state.py:1904-1922` 只看 `callable(meta[-1])` + 位置参数计数）⇒ **与上游零差异**，
  兼容矩阵**无需**登记差异。
  > **📌 修正说明（2026-11-08 第二轮澄清 Q6）**：本裁定原表述为「类在末位 ⇒ 拒绝」，
  > 该表述**只对「`__init__` 无参的类」成立**（`signature(NoInit)` = `()`）⇒ 已按 Q6 改写为
  > 「不特殊处理 + 机械判定」，并补齐上列实测事实。

- **裁定 10（归约器按引用持有 · 身份判定）**：
  归约器 MUST **按引用**持有（MUST NOT 包装 / 复制 / 部分应用）⇒
  `spec.reducer is operator.add` 成立（SC-001 的身份判定，不是相等判定）。
  二元性判定 MUST 依据**该 callable 自身**的签名，MUST NOT 依据其返回值、
  MUST NOT 在解析期**调用**它（调用会产生用户副作用）。

- **裁定 11（「纯数据」的形态 + 可序列化投影）**：
  解析结果 MUST 是**不可变**的纯数据；除归约器引用外，MUST 提供一份
  **可 JSON 序列化**的投影（key / 类型的可读文本 / 有无归约器 / 语义标记 / 归约器的可读标识）
  ⇒ 满足 SC-005「可序列化 / 可比较」，且便于快照 / 记录 / 直接断言。

- **裁定 12（继承键 MUST 合并 · `__slots__` 伪键 MUST 跳过）**：
  TypedDict 的**继承链**上的注解 MUST 一并解析（父类的 key 不许丢）⇒ 规格条数 == 解析出的 key 数；
  名为 `__slots__` 的伪 key MUST 被跳过（上游同做法，`langgraph/graph/state.py:1829-1832`）。

- **裁定 13（`Annotated` 的「通道注解」形态在 v1.0 不支持）**：
  LangGraph 支持 `Annotated[T, SomeChannel]`（把通道类型直接塞进元数据，`state.py:1876-1902`）
  —— 那是 LangGraph **特有**的通道注入机制，freegraph v1.0 的通道由 **B5F1** 按
  「有无归约器」**推导**（`LastValue` / `BinaryOperatorAggregate`），不需要用户指定通道类。
  ⇒ 该形态在本 feature **不被支持**；由于「类」是末位可调用项，按 FR-007 ② **显式报错**
  （MUST NOT 静默忽略）⇒ 这是**有意的失败**，不是遗漏。

- **裁定 14（「捕获路径」与「读结构化字段的路径」分开 · 调和澄清 **Q4** 与 **Q7** · 2026-11-08 分析轮）**：
  澄清 **Q4** 定了「错误类型不进契约层 / 门面公开面 ⇒ 用户按**基类**捕获」；
  澄清 **Q7** 又定了「错误 MUST 带结构化字段 `key` / `reason`，上层 MUST NOT 解析消息」——
  **两条合在一起有缝隙**：基类 `FreegraphError` 上**没有**这两个属性 ⇒ 只靠基类捕获时，
  读结构化字段在**类型检查**下不可用（运行时靠鸭子类型可用，但 mypy 会报错）。
  ⇒ **裁定**：把两条路径**分开写死** ——
  ① **捕获**：MUST NOT 要求用户 import 具体子类（`except FreegraphError` / `except ValueError` 均可）
  ⇒ **Q4 的原意不变**；
  ② **读字段**：上层 MAY 从 **`freegraph.runtime`** import 具体子类（**L2 子包**）⇒
  门面 7 符号面与契约层 18 符号面**均不变**（**零冻结面变更** · 与「`freegraph.contracts`
  也是用户可见路径」的仓库惯例同构）。
  **落点**：FR-007 ⑤⑥ · SC-017 · `contracts/schema-parse-contract.md` §4 · research D-08 ·
  tasks T006 / T013。

### 引文差异说明（与引文的逐条差异 · 供人工评审核对）

| # | 引文表述 | 本 spec 的口径 | 理由 |
|---|---|---|---|
| ① | FR-006「抛错**或**降级为无归约器」 | **抛错** | 裁定 1（A2 上游同行为 + 提示词 §10 风险 + 禁静默改语义） |
| ② | SC-003「callable 位置参数数 ≠ 2 时 100% 不被当作归约器」 | 逐字保留，并补一句「**且解析失败**（MUST NOT 静默降级）」 | 裁定 1（SC 与 FR 口径一致化） |
| ③ | §2「Pydantic 路径若纳入须在 spec 中写明支持到什么程度」 | **不纳入**（v1.0 无 `[pydantic]` extra） | 裁定 7（宪法 v1.7.0 + 立项书 D15） |
| ④ | §7「通道规格（`ChannelSpec`）」 | 冻结为 `ChannelSpec`（单 key）+ `SchemaSpec`（整体）两个纯数据类型 | 裁定 6 / FR-002 / FR-010 |
| ⑤ | §5 SC-004「解析结果不产生任何 import 副作用」 | 判据具体化为「解析前后 `sys.modules` 增量 == 0（标准库 typing / inspect 等除外）+ 环境变量读取次数 == 0 + 出站连接数 == 0」 | 可判定化（SC-007） |
| ⑥ | §9「本层只允许标准库」 | 逐字保留，并补「MUST NOT import `typing_extensions`」 | 裁定 3（`typing_extensions` 不在内核依赖面） |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 追加语义被正确识别（Priority: P1）

作为 freechain 开发者，我用 `Annotated[list[AnyMessage], operator.add]` 声明消息通道时，
希望 freegraph 知道这个 key 是**追加**而不是**覆盖**——以便多次节点写入的消息能累积成
完整对话历史，而不是每次写入都把历史冲掉。

**Why this priority**: 这是本 feature 的**小目标本体**（立项书 §5.2 的 B4F1 行：
「`Annotated[list, operator.add]` 被正确识别为二元归约器」）⇒ 不成立则整个 B4 功能块不成立。
且它是 `harness/demo/target.py:59-61` 的 schema 形态 —— 验收基准的消息累积循环依赖它。

**Independent Test**: 解析一份只含 `messages: Annotated[list, operator.add]` 的 schema
（与立项书 §5.2 的 B4F1 小目标同形），
断言产出的通道规格里归约器**就是** `operator.add` **本身**（身份判定）、`has_reducer` 为真、
语义标记为 `reduce`、类型信息为**归约前的基类型 `T`**（本例即 `list`）。

**Acceptance Scenarios**:

1. **Given** 一份 `TypedDict` schema，其 `messages` 键为 `Annotated[list, operator.add]`，
   **When** 解析该 schema，**Then** 该键的通道规格里归约器与 `operator.add` **是同一对象**，
   且「有归约器」标记为真、语义标记为「归约」。
2. **Given** 同一份 schema，**When** 检查二元性，**Then** 归约器被判为**二元**（被接受为归约器）。
   > **📌 二元性不落字段**（FR-020 ①）⇒ 其可判定形式 = **「非二元 ⇒ 抛
   > `InvalidSchemaError`」**（FR-007 ②）+ **判定表逐条比对**（SC-004）。
   > 位置参数计数口径 = 仅计位置专用 + 位置或关键字两类（FR-004）。
3. **Given** 一份 schema，其中 `messages` 键的元数据为 `Annotated[list, "对话历史", operator.add]`，
   **When** 解析，**Then** 只有**末位**的 `operator.add` 被当作归约器，
   中间的字符串条目**不产生任何影响**。
4. **Given** 同一份 schema 解析两次，**When** 比较两次的解析结果，**Then** 两者**相等**
   （同一 key 的归约器引用是同一对象，语义标记一致）。

---

### User Story 2 - 计数型 key 走默认覆盖（Priority: P2）

作为 freechain 开发者，我声明 `llm_calls: int` 这类**计数型** key 时，希望每次节点写入都**覆盖**
上一次的值，而不是累加——以便 `llm_calls` 真的是「调用了几次」这个计数，而不是一个越滚越大的总数。

**Why this priority**: 「无归约器 ⇒ 覆盖」是状态语义的**另一半**（C3），
且是 `target.py:81` 的 `state.get('llm_calls', 0)` 能工作的前提之一。
只做 P1 而不做 P2，等于只学会了「追加」、没学会「覆盖」。

**Independent Test**: 解析一份含 `llm_calls: int`（无 `Annotated`）的 schema，
断言该键的通道规格标记为「无归约器 / 默认覆盖」。

**Acceptance Scenarios**:

1. **Given** 一份 schema 含 `llm_calls: int`（**无** `Annotated`），
   **When** 解析，**Then** 该键的通道规格中归约器为**空**、语义标记为「覆盖」。
2. **Given** 同一份 schema，**When** 统计产出的通道规格条数，**Then** 条数 **==** schema 的 key 数
   （每个 key 恰一条，不多不少）。
3. **Given** 一份 schema 同时含「带归约器的 key」与「不带归约器的 key」，
   **When** 解析，**Then** 两类 key 的语义标记**互不相同且互不串扰**
   （带归约者标「归约」，不带者标「覆盖」）。
4. **Given** 一份含「继承而来的 key」的 schema，**When** 解析，
   **Then** 父类的 key 也**出现在**结果中，且同样参与规格条数统计。

---

### User Story 3 - 别的 `Annotated` 用法不被误判（Priority: P3）

作为用户，我的 schema 里可能有**别的** `Annotated` 用法（例如 `Annotated[int, "说明文字"]`、
或者元数据里塞了一堆文档字符串 / 标记），希望它们**不会**被误当成归约器——
以便一个「说明文字」不会让我的状态语义从「覆盖」悄悄变成「累加」。

**Why this priority**: 误判方向是**危险的那一侧** —— 把说明文字当归约器，
会让覆盖语义静默变成累加语义（消息重复、计数虚高），而且**运行期才暴露**。

**Independent Test**: 解析一份含 `Annotated[int, "说明文字"]` 的 schema，
断言该键被判为「无归约器 / 默认覆盖」。

**Acceptance Scenarios**:

1. **Given** 一份 schema 含 `note: Annotated[int, "说明文字"]`，
   **When** 解析，**Then** 该键被判为**无归约器**、语义标记为「覆盖」。
2. **Given** 一份 schema 含 `note: Annotated[int, "说明文字"]`，
   **When** 解析，**Then** 解析**成功**（不抛错）——「末位不是可调用项」是**合法**情形，不是错误。
3. **Given** 一份 schema 含 `note: Annotated[int, "说明文字", SomeMarkerClass]`（**标记类**在末位，
   其 `__init__` **无 2 个位置参数**），
   **When** 解析，**Then** 解析**失败**并抛出明确的 schema 错误（指名 key）——
   类是可调用项但不是二元函数 ⇒ MUST NOT 被静默接受、也 MUST NOT 被静默忽略。
4. **Given** 任意一份 schema，**When** 解析全过程，**Then** 归约器**从未被调用过**
   （解析只做签名判定，不产生用户副作用）。

---

### User Story 4 - 写错的 schema 在解析期就报错（Priority: P4）

作为用户，我希望我的 schema 写错时**立刻**收到一条能定位到具体 key 的错误，
而不是等到图跑起来、消息开始重复了才发现——以便把「归约器写错」这类问题拦在建图之前。

**Why this priority**: 提示词 §10 的风险提示明说：二元性判据若写错，**错误只在运行期暴露**
（表现为归约调用参数数不符）⇒ 「提前报错」是本 feature 的**风险对冲手段**，
也是 FR-006 要求「行为须明确」的落点。

**Independent Test**: 拿一份含 3 参函数的 schema 去解析，断言抛出明确的 schema 错误
（指名 key 与实际签名），而不是静默降级或运行期才炸。

**Acceptance Scenarios**:

1. **Given** 一份 schema 含 `bad: Annotated[int, lambda a, b, c: None]`（**3 个位置参数**），
   **When** 解析，**Then** 解析**失败**并抛出明确的 schema 错误，错误消息**指名**该 key
   与「期望 2 个位置参数」的事实。
2. **Given** 同一份 schema，**When** 解析，**Then** **不存在**「静默当作无归约器」的路径
   （覆盖语义降级次数 == 0）。
3. **Given** 一个**不是** `TypedDict` 的对象（普通 `dict` / `dict[str, int]` / 模型实例），
   **When** 拿它当 schema 解析，**Then** 解析**失败**并抛出明确的 schema 错误
   （消息说明「需要 `TypedDict`」），MUST NOT 抛裸 `TypeError`。
4. **Given** 一份含不可解析前向引用的 schema，**When** 解析，**Then** 解析**失败**并给出
   可定位的错误，MUST NOT 静默退回「看起来能跑但丢了归约器」的解析结果。

---

### Edge Cases

- **`Annotated[list[AnyMessage], operator.add]`**：归约器 MUST 是 `operator.add` **本身**（身份判定，
  非相等判定）—— 任何包装 / 复制都会让 SC-001 失败。
- **`Annotated[list, "描述", operator.add]`**：只认**末位**可调用项；前面的条目 MUST NOT 影响判定
  （FR-005）。
- **`Annotated[int, "说明文字"]`**：末位**非**可调用项 ⇒ 无归约器 / 默认覆盖，**不报错**（P3）。
- **`Annotated[int, SomeClass]`（类在末位）**：MUST **不特殊处理** —— 完全按签名机械判定（澄清 Q6）：
  `class ClassNoInit`（`__init__` 无参）⇒ 0 个位置参数 ⇒ **拒绝并报错**；
  `class ClassOneArgInit` ⇒ 1 个 ⇒ **拒绝并报错**；
  `class ClassTwoArgInit`（`__init__(self, a, b)`）⇒ **2 个 ⇒ 接受为归约器**
  （运行期语义 = `ClassTwoArgInit(current, new)` 构造实例 —— 与上游**同构**，非 freegraph 的取舍）。
  （类名逐字统一为 `contracts/binary-criterion.md` §4 的**夹具名** · 2026-11-08 分析轮）
- **末位元素是「可调用对象实例」**：同按签名机械判定 —— `__call__(self, a, b)` ⇒ 2 个 ⇒ 接受；
  `__call__(self, *, a, b)` ⇒ 0 个 ⇒ 拒绝。
- **`functools.partial(add, 1)` / 绑定方法**：签名分别是 `(b, /)`（pos=1）与 `(b)`（`self` 已绑定 · pos=1）
  ⇒ 均**拒绝**。
- **`Annotated[int, str]`（内置类型在末位）**：签名**取不到**（`inspect.signature` 抛 `ValueError`）
  ⇒ **拒绝并报错**（裁定 9）。
- **`Annotated[int, lambda a, b, c: ...]`（3 参）**：拒绝并报错。
- **`Annotated[int, lambda a: ...]`（1 参）**：拒绝并报错。
- **`Annotated[int, lambda a, *args: ...]`**：`a` 计 1 个位置参数、`*args` **不计入** ⇒ 只有 1 个 ⇒ 拒绝。
- **`Annotated[int, lambda a, b, *args: ...]`**：位置参数**恰为 2** ⇒ **接受**（`*args` 不计入）——
  与上游同口径（`state.py:1910-1916` 的计数式）。
- **`Annotated[int, lambda a, b, *, c=None: ...]`**：keyword-only 参数**不计入** ⇒ 位置参数恰为 2
  ⇒ **接受**（与上游同口径）。
- **`Annotated[int, lambda *, a, b: ...]`**：位置参数 0 个 ⇒ 拒绝。
- **`Required[Annotated[list, operator.add]]` / `NotRequired[Annotated[int, "d"]]`**：
  包装**必须先剥离**（裁定 4）⇒ 否则 `Required` 包裹的归约器会被**漏掉**（实测顶层 `__metadata__` 为空）。
- **`Annotated[Required[list], operator.add]`（`Required` 在 `Annotated` 的**内层**）**：
  FR-008 只规定剥离**顶层**的 `Required` / `NotRequired` 包装 ⇒ 本 feature **只剥离顶层**
  ⇒ 该 key 的**类型信息** = `Required[list]`（**不是** `list`），MUST NOT 递归剥离
  （递归剥离 = 另一套口径，会与 FR-008 冲突）。
  > **📌 登记（DR-9）**：该形态下 freegraph 与上游是否**逐字一致**，留待 **B5F2** 的差分夹具核实
  > （上游 `_get_channel` 的剥离亦为顶层 · `state.py:1850-1874`）⇒ 本 feature **不**据此加判据。
- **TypedDict 继承**：父类的 key MUST 出现在结果里；子类覆盖父类同名 key 时以子类的注解为准。
- **`total=False` / `NotRequired[...]`（可选 key）**：MUST **照常解析**（不得因此拒绝 schema），
  且 MUST 标记为「可选」（澄清 Q2 · FR-021）；「必选 / 可选」的**执行**校验归 B7F3。
- **字符串注解下的 `Required` / `NotRequired`**（`from __future__ import annotations`）：
  CPython 的 TypedDict 机制**识别不出**（实测 3.11 / 3.12 一致 ⇒ 全部记为「必选」）⇒
  freegraph MUST **照抄**该结果，MUST NOT 自造判定逻辑（FR-021 ③）。
- **`from __future__ import annotations`（字符串注解）**：MUST 仍能解析出归约器（裁定 5）。
- **不可解析的前向引用**（如 `Annotated[list[Missing], operator.add]`）：MUST 报错，
  MUST NOT 静默退回原始 `__annotations__`（那会丢掉归约器）。
- **非 `TypedDict` 输入**（普通 `dict` / `dict[str, int]` / 模型实例 / Pydantic 模型）：
  MUST 报错并说明「需要 `TypedDict`」；MUST NOT 抛裸 `TypeError` / `AttributeError`。
- **一份 schema 有多个问题**：MUST **只报第一个**（按 key 的解析顺序），
  MUST NOT 汇总多个问题（澄清 Q3 · FR-007 ④）⇒ 用户按报错逐个修即可。
- **空 TypedDict（零个 key）**：合法 ⇒ 产出**零**条通道规格（不是错误）。
- **名为 `__slots__` 的伪 key**：MUST 被跳过（裁定 12）。
- **同一个 callable 被两个 key 共用**：两条规格各自持有**同一引用**（不复制、不共享可变状态）。
- **有状态的归约器**（闭包 / 可变默认参数）：按引用持有，MUST NOT 复制、 MUST NOT 重置其状态
  （状态归用户负责）；本 feature **不调用**它。
- **归约器是 lambda**：投影里的标识为 `"{模块名}.<lambda>"`（**无内存地址**）⇒ 两次投影逐字一致。
- **归约器是可调用实例**（无 `__qualname__`）：投影标识取**其类型**的模块名 + 限定名；
  MUST NOT 落到带地址的 `repr`（否则快照假红）。
- **归约器返回值 / 副作用**：解析期 MUST NOT 调用归约器（只读签名）⇒ 解析是**纯函数**。
- **元数据里的非归约器条目是类 / 实例**：只要**末位**不是二元可调用项，就按 FR-007 处理；
  中间条目一律忽略。
- **上游版本漂移**：本 spec 引用的上游行号核实环境为 **`langgraph 1.2.11`**
  （实测于 CPython 3.12.3）⇒ 换版本后行号 MUST 重新核实，MUST NOT 凭记忆沿用（宪法原则 VIII）。
  判定表是**上游行为的固化快照** ⇒ 上游升级**不会**让 CI 变红；但**换上游版本时 MUST 重新核实判定表**
  （人工动作 · 澄清 Q5）。

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001（输入面 · 标准 `TypedDict`）**：系统 MUST 接受**标准 `TypedDict`** 作为状态 schema；
  MUST NOT 要求用户继承任何 freegraph 基类（C1）；MUST NOT 要求用户安装任何第三方包
  （用户的 schema 用标准库 `typing` 构造即可）。
  ① 判定口径 MUST 为：**`typing.is_typeddict(x)` 为真**，**或** `x` 同时满足
  「是一个类」+「是 `dict` 的子类」+「有 `__annotations__`」+「有 `__total__`」
  ⇒ 覆盖 `typing_extensions.TypedDict`（裁定 3 · 实测 `typing.is_typeddict` 对其返回 `False`）。
  ② MUST NOT import `typing_extensions`（内核只允许标准库）。

- **FR-002（每 key 一条通道规格）**：系统 MUST 为 schema 的**每一个** key 产出一条通道规格，
  产出的规格集合 MUST **保序**（声明顺序；继承链的 key 按解析出的顺序追加）。
  每条通道规格 MUST 承载的**字段构成与字段名**见 **FR-020 ①**（逐字冻结 · 本条不重复列举）——
  本条只管「**每 key 恰一条**」与「**保序**」。
  其中「类型信息」= 冻结字段 **`value_type`** = 归约前的基类型 `T`
  （`Annotated[T, ...]` 的 `T`；无 `Annotated` 时即该 key 的类型）
  —— MUST **只存基类型**，MUST NOT 保留 `Annotated` 包装或原始注解对象（澄清 **Q1**）。

- **FR-003（归约器提取 · 取元数据末位）**：系统 MUST 从 `Annotated[T, ...]` 的元数据中提取归约器：
  **取元数据的末位元素**；且**当且仅当**该元素是「**恰好接受 2 个位置参数**」的 callable 时，
  才认定为归约器（C2）。
  ① 末位**不是** callable ⇒ 该 key **无归约器**（走 FR-006）；
  ② 末位是 callable 但**不是**二元 ⇒ MUST 按 FR-007 ② **报错**（MUST NOT 降级）。
  ③ 候选的判定只看「**是不是 callable**」+「位置参数计数」——
  **类**与**可调用对象实例**均**不**被特殊排除（澄清 **Q6** · 裁定 9）。

- **FR-004（二元性判据的精确定义）**：「恰好 2 个位置参数」的计数口径 MUST 为：
  **位置专用（positional-only）+ 位置或关键字（positional-or-keyword）** 两类参数之和 **== 2**；
  **可变位置参数（`*args`）、可变关键字参数（`**kwargs`）、仅关键字参数（keyword-only）一律不计入**。
  ① 签名**取不到**（如内置类型）⇒ 判为**非二元**（MUST 按 FR-007 ② 报错）；
  ② 该口径 MUST 与上游 `langgraph/graph/state.py:1910-1916` **逐条一致**（FR-016）。

- **FR-005（多条目元数据）**：系统 MUST 支持元数据中含**多个非归约器条目**
  （如 `Annotated[list, "描述", operator.add]`）—— 只把**末位**的可调用项当归约器；
  前面的条目 MUST NOT 影响判定（MUST NOT 被当作归约器、MUST NOT 被当作类型的一部分）。

- **FR-006（无归约器 ⇒ 默认覆盖语义）**：系统 MUST 对**无归约器**的 key 标记「**默认覆盖**」语义（C3）。
  ① 本 feature **只产出该事实**（语义标记 = `overwrite`），MUST NOT 执行覆盖
  （覆盖的执行属 **B5F1** 的 `LastValue` 通道）；
  ② 有归约器的 key MUST 标记为 `reduce`。

- **FR-007（非法 schema · 显式失败 · 绝不静默降级）**：系统 MUST **显式失败**（抛出
  `InvalidSchemaError`），MUST NOT 静默降级为「无归约器」，覆盖以下三类：
  ① **schema 不是 `TypedDict`**（普通 `dict` / `dict[str, int]` / 模型实例 / Pydantic 模型等）；
  ② **末位元素是 callable 但位置参数数 ≠ 2**（含**类**、内置类型、`*args` 形态、单参 / 三参函数等）；
  ③ **注解解析失败**（不可解析的前向引用等）。
  异常 MUST 继承 `FreegraphError` **且**继承 `ValueError`（裁定 2）；异常消息 MUST 指名
  **出错的 key**（可定位到具体通道）与**失败原因**；MUST NOT 抛裸 `TypeError` / `NameError` /
  `AttributeError`。
  ④ **MUST 快速失败**：按 key 的解析顺序逐个检查，发现**第一个**问题即抛出
  （MUST NOT 收集齐全部问题后再一次性抛出 —— 澄清 Q3；与上游行为一致）。
  ⑤ **捕获路径**：该错误类型 MUST **不进入**契约层 18 符号面、也 MUST **不进入**门面 7 符号面
  （澄清 Q4）⇒ 用户侧 `except FreegraphError`（`freegraph.contracts` 导出的内核异常基类）
  与 `except ValueError` **均** MUST 能捕获到它 ⇒ **捕获** MUST NOT 要求用户 import 具体的错误子类。
  ⑥ **结构化字段**（澄清 Q7 · 与仓库既有异常体系一致）：错误对象 MUST 暴露
  ① **出错的 key**（schema 级错误 —— 非 `TypedDict` —— 时可为空）；
  ② **原因码**（机器可读、取值域**封闭**，见下表）。
  **读结构化字段的路径（裁定 14 · 分析轮调和 Q4 与 Q7）**：需要读取 `key` / `reason` 的上层 MAY 从
  **`freegraph.runtime`** import 具体子类（**L2 子包** ⇒ 门面 7 符号面与契约层 18 符号面**均不变**）；
  **捕获**仍用基类即可 —— 理由：基类上**没有**这两个属性 ⇒ 若不给具体类型的路径，
  SC-017 的「只读结构化字段、不解析消息」在**类型检查**下不可用。
  消息文本**只是给人看的摘要**（沿用仓库既有约定：**英文摘要** + 点名 key）⇒
  上层 MUST **无须解析消息文本**即可取到全部细节。
  | 原因码 | 触发条件 | 出错的 key |
  |---|---|---|
  | `not_a_typed_dict` | schema 不是 `TypedDict`（含 Pydantic 模型 / 普通 dict / 实例） | **空**（schema 级错误） |
  | `reducer_not_binary` | 末位元素是 callable 但位置参数数 ≠ 2（含类 / 实例 / 签名不可取） | 有（该 key 名） |
  | `annotation_unresolvable` | 注解解析失败（如不可解析的前向引用） | 有（该 key 名） |

- **FR-008（`Required` / `NotRequired` 剥离）**：系统 MUST 在检查 `Annotated` 元数据**之前**，
  剥离**顶层**的 `Required[...]` / `NotRequired[...]` 包装（PEP 655 · Python 3.11）
  ⇒ 其包裹的归约器 MUST NOT 被漏掉（裁定 4 · 实测不剥离则顶层 `__metadata__` 为空）。

- **FR-009（注解解析方式）**：系统 MUST 以**保留 `Annotated` 附加信息**的方式解析注解
  （等价于 `get_type_hints(..., include_extras=True)`）；MUST 合并**继承链**上的注解
  （子类同名 key 覆盖父类）；MUST 跳过名为 `__slots__` 的**伪 key**（裁定 5 / 裁定 12）。

- **FR-010（纯数据 · 不可变）**：解析结果 MUST 是**纯数据**且**不可变**；
  MUST NOT 夹带任何运行期对象（通道实例、协程、锁、文件句柄、连接等）；
  **归约器引用是唯一的例外**（它是用户提供的 callable，按引用持有 —— FR-012）。

- **FR-011（可序列化投影）**：系统 MUST 提供一份**可 JSON 序列化**的投影
  （key / 类型的可读文本 / 有无归约器 / 语义标记 / 必选标记 / 归约器的可读标识）⇒ 满足 SC-005，
  并便于快照、记录与直接断言。投影的字段构成 MUST 稳定且**确定性**（同一 schema 两次投影逐字一致）。
  **归约器标识规则（MUST 按序取第一个可得者 · 澄清 Q10）**：
  ① **模块名 + 限定名** —— 对象自身有 `__module__` 与 `__qualname__` 时取
  `"{__module__}.{__qualname__}"`（函数 / 类 / lambda 皆适用，如 `operator.add`、
  `tests.test_schema.<lambda>`）；
  ② 对象**无** `__qualname__`（可调用实例）时，取**其类型**的模块名 + 限定名
  （如 `myapp.reducers.Merger`）；
  ③ 再取不到时退回 `__name__`；
  ④ 最后兜底 `repr(obj)`，且 MUST **抹除内存地址形态**（`0x…` 一律替换为固定占位）。
  ⇒ 投影 MUST NOT 含内存地址（否则快照测试假红）；标识 MUST NOT 含时间戳 / 随机成分。

- **FR-012（归约器按引用持有）**：归约器 MUST **按引用**持有 ——
  MUST NOT 包装、复制、部分应用或以任何方式替换 ⇒ `spec.reducer is operator.add` MUST 成立
  （SC-001 的**身份**判定）。二进制性判定 MUST 依据**该 callable 自身**的签名。

- **FR-013（依赖与 I/O 纪律）**：本层 MUST 只依赖**标准库**；
  MUST NOT import `langchain` / `langchain-core` / `langgraph*` / `langsmith` / `pydantic` /
  `typing_extensions`；MUST NOT 读取**任何**环境变量；MUST **零出站**、零文件 I/O；
  解析 MUST 是**纯函数**（MUST NOT 调用用户的归约器）。
  > **📌 空断言标注（2026-11-08 分析轮 · A9）**：`pydantic` 在 v1.0 **根本不存在**
  > （宪法 v1.7.0 · 四个 extra 移入 v2.0 清单）⇒ 对它的禁令**恒真**（空断言）——
  > 保留是作为 **v2.0 的前置防线**（届时 `[pydantic]` extra 存在），
  > 但 MUST NOT 被读作「已实测验证」。

- **FR-014（层纪律 · ARCH-1）**：本 feature 属 **L2 执行内核层**；
  新增代码 MUST 落在**已登记**的 L2 路径（层注册表已登记 `src/freegraph/runtime/` = L2）
  ⇒ 层注册表 MUST **零改动**；L2 MUST 只向下依赖 **L1 契约层**，
  MUST NOT import L3 / L4 / L5。

- **FR-015（不越界）**：本 feature MUST NOT 实现通道本身（`LastValue` /
  `BinaryOperatorAggregate` / `EphemeralValue`——**B5F1**）、MUST NOT 实现稀疏状态读取
  （**B5F2**）、MUST NOT 实现调度循环（**B7F1**）、MUST NOT 实现 `StateGraph` 构建器
  （**B6F1**）；MUST NOT 改动契约层 18 符号面（G7）、MUST NOT 改动门面 7 符号面（G15 / G19）。

- **FR-016（A2 · 与上游判据一致）**：二元性判据 MUST 与上游 `_is_field_binop`
  （`langgraph/graph/state.py:1904-1922`）的**判定结果**一致（**接受 / 拒绝**），
  异常类型不要求逐字相同。
  ① MUST 落一份**自包含**的判定表（每条用例写明：输入形态 / 上游语义 / 来源 `路径:行号`）
  作为回归基线；
  ①-a **判定表 MUST 覆盖下列「二元性判定」形态（16 类 · 澄清 Q9）**——
  每类对应上游判据的一个分支，**缺失条数 == 0**：
  **位置专用 2 参 / 位置或关键字 2 参 / 3 参 / 1 参 / `a,*args` / `a,b,*args` /
  `a,b,*,c` / `*,a,b` / 类（`__init__` 无参 · 1 参 · 2 参）/
  可调用实例（`__call__` 2 参 · keyword-only） / `functools.partial` / 绑定方法 /
  内置类型（签名不可取）**。

  > **📌 判定表的**唯一权威** = `contracts/binary-criterion.md` §2（`<!-- authority: yes -->`）**——
  > **本 spec 不复制该表**（只列形态清单 + 指向权威）⇒ **无双份表格、无漂移风险**
  > （与 plan 的 Structure Decision 同一口径）。**形态清单的逐条形态、期望判定与上游
  > `路径:行号` 以权威文件 §2 为准**；本条只规定**覆盖面**：**恰 16 类**（历史下限 ≥ 14 已达成）。
  > **本清单与 §2 的行序对应**（清单为**摘要**，增删与逐条形态**一律以 §2 为准**）：
  > 本清单的「类（`__init__` 无参 · 1 参 · 2 参）」一项 = §2 第 **9–11** 行、
  > 「可调用实例（`__call__` 2 参 · keyword-only）」一项 = §2 第 **12–13** 行。

  ①-b 判定表 MUST 另覆盖**归约器提取**形态（2 类）：**末位非 callable**（如字符串元数据 ⇒
  **无归约器 / 覆盖**，**不报错**）与**多条目元数据**（末位为 callable、前序条目非 callable ⇒
  只认末位）；来源 `state.py:1905-1907`；
  ② **本 feature MUST 零依赖声明** —— `langgraph` MUST NOT 出现在 `dependencies` /
  `[project.optional-dependencies]` / `[dependency-groups]` **任何一处**；
  ③ **CI MUST NOT 安装 `langgraph`**（CI 作业内 `langgraph` 的安装次数 == 0）——
  「上游在场时的实时对照」**不落进本 feature 的 CI**，留给 **B5F2 / B8F1** 的差分夹具
  （那里已按立项书预留 `langgraph` 的 dev/test 依赖位）；
  ④ 开发者在**本机临时安装**一份 `langgraph` 作为**参考读物 / 对照工具**、用于核实判定表，
  是允许的（**不写进仓库**，用完即弃）—— 澄清 Q5。

- **FR-017（负向用例 · 提示词 §10 的硬要求）**：测试 MUST 覆盖「**非二元 callable 被拒绝**」
  这一负向用例，且至少覆盖：**3 参函数 / 1 参函数 / 类（`__init__` **非 2 个位置参数**者）/ 内置类型 /
  `*args` 形态**
  ⇒ 每一例 MUST 断言「抛错」而非「静默降级」。

- **FR-018（人工门禁 + 证据门禁）**：本 feature MUST 产出人工验证记录，
  落 **`harness/verification/B4F1/manual-verification.md`**，逐条核对 **A1–A3** 三项验收判据并给出结论；
  记录 MUST 采用仓库既有的**五段式**结构（环境 / 步骤 / 实际输出 / 结论 / 遗留问题，
  见 `harness/verification/README.md`），第 3 节 MUST 粘贴**真实输出**，
  未实跑的项 MUST 显式记入「遗留问题」（MUST NOT 伪造输出）；
  记录 MUST 含**来源覆盖表**（宪法原则 VIII）——每条判据标注来源
  （上游 `路径:行号` + 核实版本 / Q8 条号 / 宪法条款号）。

- **FR-019（署名头 · 零新增依赖）**：本 feature 新建的**每一个源文件** MUST 携带署名头
  （`# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph`）
  且模块 docstring 为首个语句（宪法原则 X）；MUST **零新增依赖声明**
  （运行时 / 发行元数据 / **开发期依赖组**三处均零新增 · 澄清 Q5）
  ⇒ `THIRD_PARTY_NOTICES` **无需新增登记**；MUST 沿用 **Python ≥ 3.11** 基线与
  typing 构件上限（禁 3.12+ / 3.13+ 构件）。

- **FR-020（解析结果的形状冻结 · 含字段名）**：通道规格与规格集的**字段构成与字段名** MUST 冻结为：
  ① **单键规格 `ChannelSpec`** 承载 6 个字段（名字**逐字冻结** · 澄清 Q8）：

  | 字段名 | 取值 | 语义 |
  |---|---|---|
  | `key` | `str` | schema 中的 key 名 |
  | `value_type` | 类型对象 | **归约前的基类型 `T`**（`Annotated[T, ...]` 的 `T`）；MUST NOT 保留 `Annotated` 包装 / 原始注解对象（澄清 Q1） |
  | `reducer` | 可调用对象或**空** | 归约器**引用**（按引用持有 · FR-012）；无归约器时为**空** |
  | `has_reducer` | `bool` | 是否带归约器 |
  | `semantics` | `str` | 语义标记，取值域**恰为** `{"overwrite", "reduce"}` |
  | `required` | `bool` | 必选 / 可选标记（澄清 Q2 · 只记录不执行 · FR-021） |

  ② **规格集 `SchemaSpec`** 承载 2 个字段：
  `channels`（保序的「key → `ChannelSpec`」映射）+ `keys`（**有序**的 key 序列）；
  ③ 二者 MUST 为**不可变**（FR-010）；
  ④ **解析入口的函数名**与**实现形态**（dataclass / NamedTuple 等）由 plan 定
  —— 本 spec 只冻结**数据契约**（字段名 / 取值域 / 不可变性）。

- **FR-021（必填性 · 只记录不执行）**：系统 MUST 为每个 key 记录**必选 / 可选**标记，
  取值来源 MUST 为 TypedDict 的类属性 **`__required_keys__` / `__optional_keys__`**
  （`total=False` ⇒ 全部可选；`NotRequired[...]` ⇒ 可选；`Required[...]` ⇒ 必选）。
  ① **MUST NOT** 因「key 是可选的」而拒绝该 schema（可选 key 是**合法**输入）；
  ② 本 feature MUST **不执行任何必填性校验**（缺必填 key 的校验归 **B7F3**）；
  ③ 标记 MUST **照抄** TypedDict 给出的集合，MUST NOT 自造判定逻辑
  —— 当注解是**字符串形态**（`from __future__ import annotations`）时，CPython 的 TypedDict 机制
  **无法**识别其中的 `Required` / `NotRequired` ⇒ 此类 key 一律记为「必选」
  （实测 CPython 3.11 / 3.12 行为一致；属**上游行为**，非 freegraph 的取舍）。

### 需求 ↔ 成功标准 追溯表

> **A1–A3 的定义**（= 立项书 §5.2 的 B4F1 小目标 · 下表「主要判据」列一律指**验收判据** A1–A3）：
> **A1** `Annotated[list, operator.add]` 被正确识别为二元归约器 ·
> **A2** 二元性判据与 LangGraph 一致 ·
> **A3** 无归约器 key 走覆盖语义。
>
> **A1–A3 的 Q8 条号映射**（FR-018 要求人工验证记录的「来源覆盖表」标 **Q8 条号** ⇒ 本表提供该映射）：
> **A1** → **Q8 §3.4 C1（状态 schema）+ §3.4 C2（归约器机制）** ·
> **A2** → **Q8 §3.2.1（归约器提取机制）+ §3.4 C2** ·
> **A3** → **Q8 §3.4 C3（默认归约语义）**。
> （其余 SC 属**本 feature 的内部判据**，无独立 Q8 条号 ⇒ 来源标「本 spec FR-xxx / 契约 §n」+ 宪法条款号。）
>
> ⚠️ **编号多义提示（**四套**编号 · 同名不同义 · 2026-11-08 分析轮）**：
> ① **验收判据 A1–A3**（本 spec / 引文 §6 / 立项书 §5.2）·
> ② **执行闸口 A1–A5**（`tasks.md`）·
> ③ **quickstart 验收闸口 V1–V9**（`quickstart.md` §10 —— 原编号 A1–A9 **已改名**为 V1–V9 以免撞名）·
> ④ **宪法门禁 G1–G30**（`harness/scripts/gates/`）—— **V** 前缀的选定即为此（`G` 已被门禁占用）
> ⇒ 引用时 MUST 带限定语（「验收判据 A1」/「执行闸口 A1」/「quickstart 闸口 V1」）。
> 另：立项书 §5.2 的**领域列**用 A1–A8（`A2 状态模型` = 本 feature 的领域）⇒ 与上述四套**再次不同义**。

| FR | 主题 | 对应 SC | 主要判据 |
|---|---|---|---|
| FR-001 | 接受标准 `TypedDict`（鸭子判定 · 不 import typing_extensions） | SC-006 / SC-011 / **SC-018** | 验收判据 A1 |
| FR-002 | 每 key 一条保序通道规格 | SC-008 | 验收判据 A1 / A3 |
| FR-003 | 归约器提取（取末位） | SC-001 / SC-003 | 验收判据 A1 |
| FR-004 | 二元性判据的精确定义（计数口径） | SC-001 / SC-004 | 验收判据 A1 / A2 |
| FR-005 | 多条目元数据只认末位 | SC-001 / SC-003 | 验收判据 A1 |
| FR-006 | 无归约器 ⇒ 默认覆盖（C3 标记） | SC-002 | 验收判据 A3 |
| FR-007 | 非法 schema 显式失败（·不降级 · 快速失败 · 结构化字段） | SC-003 / SC-006 / SC-017 | 验收判据 A2 |
| FR-008 | `Required` / `NotRequired` 先剥离 | SC-010 | 验收判据 A1 |
| FR-009 | 保留 `Annotated` 的注解解析 + 继承合并 + 跳过 `__slots__` | SC-001 / SC-008 | 验收判据 A1 / A3 |
| FR-010 | 纯数据 · 不可变 | SC-005 | — |
| FR-011 | 可 JSON 序列化投影 | SC-005 | — |
| FR-012 | 归约器按引用持有（身份判定） | SC-001 / SC-009 | 验收判据 A1 |
| FR-013 | 零第三方依赖 · 零环境变量 · 零出站 · 纯函数 | SC-007 / SC-011 | — |
| FR-014 | L2 层纪律 · 层注册表零改动 | SC-012 | — |
| FR-015 | 不越界（通道 / 读取 / 调度 / 构建器） | SC-015 | — |
| FR-016 | A2 判据一致（自包含基线 · **上游实时对照不进 CI**） | SC-004 | 验收判据 A2 |
| FR-017 | 负向用例（非二元 callable 被拒绝） | SC-014 | 验收判据 A2 |
| FR-018 | 人工验证记录 + 来源覆盖表 | SC-013 | 验收判据 A1 / A2 / A3 |
| FR-019 | 署名头 · 零新增依赖 | SC-011 | — |
| FR-020 | 解析结果的形状冻结（字段与取值域） | SC-001 / SC-002 / SC-005 / SC-008 | 验收判据 A1 / A3 |
| FR-021 | 必填性只记录不执行（`__required_keys__` / `__optional_keys__`） | SC-016 | — |

> **反向覆盖**：**SC-001 ~ SC-018 每个 SC 至少被一条 FR 映射**（SC-018 ← FR-001）·
> 逐条任务映射见 `tasks.md` 文末「附录 · 任务 ↔ spec 追溯表」。

### Key Entities

- **状态 schema（state schema）**：用户提供的**标准 `TypedDict`**；每个 key 映射到一个通道（C1）。
  MUST NOT 要求继承任何 freegraph 基类。
- **通道规格（`ChannelSpec`）**：**单键**的解析产物 —— 6 个字段（**名字逐字冻结** · 澄清 Q8）：
  `key` / `value_type`（基类型 `T`）/ `reducer`（无则为空）/ `has_reducer` / `semantics` /
  `required`；**不可变**的纯数据（FR-010 / FR-020）。
- **规格集（`SchemaSpec`）**：**整份 schema** 的解析产物 —— `channels`（保序的「key → `ChannelSpec`」
  映射）+ `keys`（有序的 key 序列）；**不可变**的纯数据。B5F1（通道实现）与 B6F1（构建器）的**输入**。
- **归约器（reducer）**：`Annotated` 元数据**末位**的**二元** callable ——
  `reducer(current, new) -> value`（C2）；**按引用**持有（MUST NOT 被包装 / 复制）。
- **二元性判据**：「恰好 2 个位置参数」的判定规则 —— 计数口径 = 位置专用 + 位置或关键字
  （`*args` / `**kwargs` / keyword-only **不计入**）；与上游 `_is_field_binop` 同口径。
- **语义标记（semantics）**：通道规格上的**取值域封闭**标记 ——
  `overwrite`（**无**归约器 ⇒ 默认覆盖 · C3）/ `reduce`（**有**归约器）。
  本 feature 只**产出**该事实，**不执行**它（执行属 B5F1）。
- **必选 / 可选标记**：通道规格上的**布尔**标记 —— 取自 TypedDict 的
  `__required_keys__` / `__optional_keys__`；本 feature **只记录、不执行**校验（澄清 Q2 · FR-021）。
- **可序列化投影**：通道规格 / 规格集的 JSON 友好投影（归约器以**可读标识**呈现）——
  供快照、记录与直接断言使用。
- **解析错误（schema 错误）**：非法 schema 的**显式失败**信号 —— 结构化字段 = **出错的 key** +
  **原因码**（取值域封闭：`not_a_typed_dict` / `reducer_not_binary` / `annotation_unresolvable`）；
  消息文本只是**英文摘要**（点名 key），上层无须解析它（澄清 Q7）。

### Out of Scope

- **通道本身**（`LastValue` / `BinaryOperatorAggregate` / `EphemeralValue`）—— 属 **B5F1**。
- **稀疏状态读取**（C4 · `state.get(key, default)` 的语义）—— 属 **B5F2**。
- **调度循环 / super-step**（含「一个 super-step 内多次写入如何合并」）—— 属 **B7F1**。
- **`StateGraph` 构建器**（把本 feature 的规格集接进建图 API）—— 属 **B6F1**。
- **Pydantic schema 支持** —— v1.0 **无** `[pydantic]` extra（宪法 v1.7.0 · 立项书 D15）；
  v2.0 再议。
- **`add_messages` 这类 LangChain 特有归约器** —— 属 freechain 层。
- **`Annotated[T, SomeChannel]` 的通道注解形态**（LangGraph 特有机制）—— v1.0 不支持；
  按 FR-007 ② 显式报错（裁定 13）。
- **LangGraph 的 `Overwrite` 旁路值**（super-step 内单值覆盖）—— 不在最小契约 C1–C27 内。
- **归约器的执行语义**（`operator(current, new)` 的调用时机与合并规则）—— 属 **B5F1 / B7F1**。
- **兼容矩阵的新增行** —— 本 feature **零新增公开 API** ⇒ 兼容矩阵**零新增行**
  （须在人工验证记录中明确记「无新增」以区别于「漏更新」）。
- **CI 流水线的挂载** —— 归 **B3F1**（既有门禁 G1–G30）；本 feature 只交付 pytest 断言。
- **第三方依赖的引入** —— 本 feature MUST **零新增**第三方依赖（含 `pydantic` / `typing_extensions`）。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001（验收判据 A1）**：对 `Annotated[list, operator.add]` 解析出的通道规格 ——
  ① 归约器与 `operator.add` **是同一对象**（身份判定 `is`）；② 「有归约器」标记为真
  （`has_reducer is True`）；③ 语义标记为 `reduce`；④ **类型信息 = 归约前的基类型 `T`**
  （`Annotated[T, …]` 的 `T`；本例即 `list` · **不含** `Annotated` 包装）。四项断言的**命中率 == 100%**。
  > **📌 形态说明**：本条用 `list`（= 立项书 §5.2 小目标的字面形态）⇒ 判据**形态无关**
  > （任何 `Annotated[T, reducer]` 形态都适用）；验收基准同构形态
  > （`typing_extensions.TypedDict` + `Annotated[list[AnyMessage], operator.add]`）由 **SC-018** 承载。
  > **📌 「二元性」不落字段**（FR-020 ① 冻结的 6 个字段中**没有**「二元性」位）⇒
  > 其可判定形式 = **「非二元 ⇒ 抛 `InvalidSchemaError`」**（FR-007 ② · SC-003）
  > + **判定表逐条比对**（SC-004）⇒ 本条**不再**单列「二元性标记」断言。
- **SC-002（验收判据 A3）**：对**无** `Annotated` 的 key（如 `llm_calls: int`）——
  归约器为空、语义标记为 `overwrite` 的**命中率 == 100%**。
- **SC-003**：元数据末位**非 callable** ⇒ 判为无归约器的**命中率 == 100%**（且解析成功）；
  元数据末位为 callable 但位置参数数 ≠ 2 ⇒ **被接受为归约器的次数 == 0**，
  且「静默降级为覆盖」的次数 == **0**（该情形 MUST 抛 schema 错误）。
- **SC-004（验收判据 A2）**：二元性判据与上游 `_is_field_binop` 的**判定结果一致率 == 100%**
  （自包含判定表的每条用例逐条比对）；判定表的每条用例 MUST 带**来源 `路径:行号`**
  （无来源项数 == **0**）；判定表 MUST 覆盖 FR-016 ①-a / ①-b 规定的**全部**形态
  （**缺失条数 == 0**）；本 feature 的 **CI 作业内 `langgraph` 安装次数 == 0**、
  仓库**依赖声明**（`dependencies` / `[project.optional-dependencies]` / `[dependency-groups]`
  **三处**）中 `langgraph` 出现次数 == **0**（澄清 Q5 · FR-016 ②③）—— ⚠️ 该口径**不含**
  `pyproject.toml` 的 `keywords` 等**非依赖字段**（该处本就含 `"langgraph"` 作检索词 ·
  `pyproject.toml:15`）⇒ **MUST 按 TOML 解析三处位置**取样，MUST NOT 对文件全文扫描。
- **SC-005**：解析结果**可比较**（同一 schema 两次解析**相等**；**键集合 / `value_type` /
  `reducer` 任一不同**的两个 schema 解析结果**不等** ⇒ ⚠️ 差异源 MUST 取自**产物内容**，
  **MUST NOT** 取自「schema 的类名 / 身份」—— 两个**内容相同、仅类名不同**的 `TypedDict`
  解析结果**必然相等**），且其可序列化投影的 **JSON 序列化成功率 == 100%**、两次投影**逐字一致**；
  投影中**含内存地址形态**（`0x…`）的条目数 == **0**（澄清 Q10 · FR-011）。
- **SC-006**：三类非法输入（非 `TypedDict` / 非二元 callable / 注解解析失败）的
  **拒绝率 == 100%**，且每一例的错误消息 MUST 指名出错 key —— 消息中**不含** key 名的次数 == **0**；
  一份含**多个**问题的 schema MUST 只报**第一个**问题（快速失败 · 澄清 Q3）⇒ 抛错次数 == **1**；
  用户侧 `except FreegraphError` 与 `except ValueError` 捕获到该错误的**成功率 == 100%**
  （澄清 Q4 · FR-007 ⑤）。
- **SC-007**：一次解析的**导入副作用 == 0**（解析前后 `sys.modules` 增量中**非标准库**条目数 == **0**
  —— 「非标准库」口径 = **不在 `sys.stdlib_module_names` 中**且**不是 freegraph 自身模块**
  ⇒ `typing_extensions` / `pydantic` 等 `site-packages` 包**计入**「非标准库」）、
  **环境变量读取次数 == 0**、**出站连接次数 == 0**。
- **SC-008**：产出的通道规格**条数 == schema 的 key 数**（含继承链上的 key）；
  多一条 / 少一条都判失败；名为 `__slots__` 的伪 key **不计入**条数。
- **SC-009**：归约器的**引用保持率 == 100%**（MUST NOT 被包装 / 复制 / 部分应用）；
  解析全程对用户归约器的**调用次数 == 0**。
- **SC-010**：`Required[Annotated[...]]` / `NotRequired[Annotated[...]]` 形态的
  **归约器检出率 == 100%**（被漏检的次数 == 0）。
- **SC-011**：本 feature 新增代码的**第三方依赖数 == 0**；导入后 `sys.modules` 中
  `langchain*` / `langsmith` / `langgraph*` / `pydantic` / `typing_extensions` 的**条目数 == 0**。
- **SC-012**：本 feature 新增代码的 import 图中，**L2 → L3 / L4 / L5 的边数 == 0**
  （层注册表**零改动**）；新增源文件的**署名头覆盖率 == 100%**。
- **SC-013**：人工验证记录**存在**且五段式小节齐全（环境 / 步骤 / 实际输出 / 结论 / 遗留问题），
  **A1–A3 逐条有结论**；来源覆盖表对**全部**判据的覆盖率 == **100%**（无来源项数 == 0）。
- **SC-014**：提示词 §10 要求的「非二元 callable 被拒绝」负向用例**存在且全绿** ——
  覆盖面见 **FR-017**（五类：3 参 / 1 参 / 类（`__init__` **非 2 个位置参数**者）/ 内置类型 / `*args` 形态），
  每类都断言「抛错」（**注意**：类的 `__init__` 若恰有 2 个位置参数 ⇒ 按裁定 9 **被接受**为归约器，
  **不在**本条的负向覆盖面内）。
- **SC-015**：本 feature **零新增公开 API** ⇒ 契约层公开符号面仍**恰为 18 个**、
  门面仍**恰为 7 个**；兼容矩阵**新增行数 == 0**（并在人工验证记录中显式记「无新增」）。
  （「公开面」的判定口径见**裁定 6** ③ —— `freegraph.runtime` 的 4 个导出属 **L2 内部 API**，
  **不进**兼容矩阵。）
- **SC-016（必填性 · 澄清 Q2）**：`total=False` 声明的 key 与 `NotRequired[...]` 声明的 key
  MUST 被标记为「**可选**」，`Required[...]` 与默认全必选的 key MUST 被标记为「**必选**」
  —— 标记正确率 == **100%**；「因 key 可选而拒绝该 schema」的次数 == **0**（可选 key 是合法输入）；
  本 feature 触发的**必填性校验**次数 == **0**（校验归 B7F3）。
- **SC-017（错误契约 · 澄清 Q7）**：非法 schema 抛出的错误对象 MUST 同时具备
  「出错的 key」与「原因码」两个结构化字段 ⇒ **字段齐备率 == 100%**；
  原因码取值 MUST **全部落在**封闭集合 `{not_a_typed_dict, reducer_not_binary, annotation_unresolvable}` 内
  （集合外取值次数 == **0**）；  「上层只读结构化字段、**不解析**消息文本」即可完成分支处理的用例
  MUST **全绿**（用例数 ≥ 3，覆盖三个原因码各一）。
  **读字段的路径**：具体子类 MAY 从 **`freegraph.runtime`** import（**L2 子包** ⇒ 公开面不变），
  **捕获**用基类 `FreegraphError` 即可（裁定 14 · FR-007 ⑤⑥）。

- **SC-018（`TypedDict` 判定 · 正面路径 · 裁定 3）**：用 **`typing_extensions.TypedDict`** 构造的
  schema（**与 `harness/demo/target.py:59-61` 同构**：含 `messages: Annotated[list[AnyMessage], operator.add]`
  与 `llm_calls: int`）MUST 被**接受**（解析**成功**）⇒ **接受率 == 100%**；
  其 `messages` 键的归约器 MUST **是** `operator.add` **本身**（身份判定 `is`）、
  `has_reducer is True`、`semantics == "reduce"`；`llm_calls` 键 MUST 为
  `reducer is None` + `semantics == "overwrite"`。
  **被误判为「非 `TypedDict`」的次数 == 0**（`typing.is_typeddict` 对 `typing_extensions.TypedDict`
  返回 `False` ⇒ **只**用它判定会使验收基准的 schema 直接不可用 ⇒ 判定 MUST 用 FR-001 ① 的鸭子口径）。
  > **📌 依赖纪律**：该断言**不要求**内核 import `typing_extensions` —— 被测 schema 由
  > **测试代码**用 `typing_extensions` 构造；freegraph 侧仍 MUST NOT import 它
  > （FR-001 ② · FR-013 · SC-011）。**测试依赖 `typing_extensions` 不违反「零新增依赖声明」**
  > （FR-016 ② 禁的是 `langgraph`；FR-019 的「零新增」针对**运行时 / 发行元数据 / 开发期依赖组**
  > 三处**仓库声明**⇒ 本项只允许**测试代码**在**已装环境**中 `import typing_extensions`，
  > **MUST NOT** 把它写进 `pyproject.toml` 的任何一处）。
  > **📌 环境依赖型判据（2026-11-08 分析轮）**：`typing_extensions` **不是任何声明依赖**
  > （v1.0 依赖面 = 零 · 宪法 v1.7.0）⇒ 其在 CI 中的可得性来自**步骤 5.5 的 v2.0 预验证包的
  > 传递带入**（**偶然**可得）⇒ 本条在部分 CI 档可能 **skip** ⇒ **skip ≠ pass**：
  > 被 skip 时 MUST 记入 `harness/verification/B4F1/manual-verification.md` 的「遗留问题」节
  > （MUST NOT 读作「已验证」）。

---

## Assumptions

- **权威顺序**：宪法 > 立项书 > 本 feature 提示词初稿 > 仓库现状。
  本 spec 的裁定 1–14 即按此顺序解决引文与上位文档的冲突；引文的原文本（如 FR-006 的
  「抛错**或**降级」）**保留在裁定记录中**以便追溯，但**不构成规范**。
- **规模参考**：940 行（实现 480 / 测试 460）· 3 人日（引文表格值，作为 plan 的输入而非本 spec 的约束）。
- **spec 目录命名**：沿用仓库既有的「**feature ID 前缀**」约定（`specs/b4f1-schema-reducer-parse`），
  与 `harness/features/B4F1_*.md` / `harness/verification/B4F1/` 的 feature ID 对齐 ——
  `.specify/init-options.json` 的 `feature_numbering: sequential` 通用算法在本仓库**未被使用**
  （既有 4 个 spec 目录均无数字前缀）⇒ **显式偏离记录**（口径：仓库一致性优先）。
- **分支**：本仓库**无** `.specify/extensions.yml` ⇒ 无 `before_specify` 钩子 ⇒ 本次**不创建 git 分支**；
  与 B1F1 / B2F1 / B2F2 / B3F1 一致（均在 `main` 上提交）。
- **Python 基线**：`>= 3.11`；typing 构件上限 = **3.11**
  （`Required` / `NotRequired` 可用；3.12+ 构件如 `TypeAliasType` / `override` / `ReadOnly` /
  `TypeIs` / PEP 695 `type` 语句禁用）。
- **内核依赖面**：**零第三方依赖**；`typing_extensions` **不在**内核依赖面
  （用户的 schema 可用它构造 —— `target.py:59` —— freegraph 走鸭子判定兼容，裁定 3）。
- **`langgraph` 的角色**：**仅 dev/test 依赖**，MUST NOT 进 `Requires-Dist`；
  **本 feature 连开发期依赖组（`[dependency-groups]`）也不写它**（澄清 Q5）——
  开发者**本机临时安装**一份当参考读物 / 对照工具是允许的（不写进仓库）；
  「上游在场时的实时对照」留给 **B5F2 / B8F1** 的差分夹具。
  核实环境 = **`langgraph 1.2.11`**（本会话实测于 CPython 3.12.3，
  路径 `…/site-packages/langgraph/graph/state.py`）。
- **上游行号的引用纪律**：换版本后 MUST 重新核实，MUST NOT 凭记忆沿用（宪法原则 VIII）。
- **代码落位**：L2 = `src/freegraph/runtime/`（层注册表**已登记**）⇒ 层注册表零改动；
  具体的模块划分与函数命名由 plan 定。
- **类型可读文本**：投影里「类型的可读文本」的**规范化口径**由 plan 定，
  但 MUST **稳定**且**确定性**（同一 schema 两次投影逐字一致）。
- **既有冻结面零改动**：契约层 18 符号面（B1F1 / B2F1）、门面 7 符号面（B2F2）、
  层注册表（B3F1）—— 本 feature **一字不动**。
- **人工验证记录**：采用仓库既有的**五段式** + **来源覆盖表**（宪法原则 V / VIII）；
  未实跑的项 MUST 显式记入「遗留问题」（MUST NOT 伪造输出）。
- **A2 比对的判定面**：比对**判定结果**（接受 / 拒绝），**不**要求异常类型逐字相同
  （freegraph 统一为 `InvalidSchemaError`，裁定 2 / 裁定 9）。
- **前置依赖**：**B2F2**（门面与快照冻结面）；**后续解锁**：**B5F1**（通道实现，接收本 feature 的解析产物）。

---

## 依据

- 立项书 §5.1（分层 · **ARCH-1** 依赖方向铁律）· §5.2（**B4F1 行**：L2 执行内核层 / M1 /
  前置 B2F2 / 940 行 / 3 人日 / 小目标「`Annotated[list, operator.add]` 被正确识别为二元归约器」；
  **B5F2 行**：`langgraph` **仅作 dev/test 依赖**，不入 `Requires-Dist`）·
  §5.3（**C1** 状态 schema / **C2** 归约器机制 / **C3** 默认归约语义 / **C4** 稀疏状态 / **C8** 条件边）·
  §5.4（DF1 `StateDict`）· §9.2（fake 注入机制）· **D15**（v1.0 依赖面 ⇒ B4F1 / B5F1 的
  schema 校验**降级为标准库 / 自研替代**）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §1 摘要第 2 条
  （`Annotated[T, reducer]` + 二元函数约定 = **通用协议**，非 LangChain 特有）·
  §3.2.1（归约器提取机制 · 默认归约器 `LastValue` = 覆盖 · `operator(current, new)` 调用语义）·
  §3.4 **C1 / C2 / C3**（状态 schema / 归约器机制 / 默认归约语义）。
- 源码参照（**核实环境：`langgraph 1.2.11`**，实测于 CPython 3.12.3）：
  `langgraph/graph/state.py:1815-1836`（`_get_channels` · `get_type_hints(..., include_extras=True)` ·
  跳过 `__slots__`）· `:1850-1874`（`_get_channel` · **先剥离 `Required` / `NotRequired`**）·
  `:1876-1902`（`_is_field_channel` · LangChain/LangGraph 特有的「通道注解」形态 —— v1.0 不支持）·
  `:1904-1922`（**`_is_field_binop`** · 末位 callable + 位置参数计数 **== 2** + 否则 `raise ValueError`）·
  `langgraph/channels/binop.py:123-144`（`operator(current, new)` 的执行语义 —— 属 B5F1）。
- 宪法 `.specify/memory/constitution.md`：**原则 I**（零环境变量 · 零出站）·
  **原则 II**（内核纯净 · 「状态 schema 使用标准 `Annotated` + 归约器表达，**不得**自带一套并行状态类型体系」）·
  **原则 III**（验收契约优先 · `target.py` 是**只读基准**）· **原则 V**（人工验收是最终验收标准）·
  **原则 VIII**（证据与术语纪律 · `本地路径:行号` 标注）· **原则 X**（兼容矩阵 + 署名头 +
  `THIRD_PARTY_NOTICES`）· 「依赖白名单 / 黑名单」（**包层白名单 v1.7.0** · v1.0 零第三方依赖）·
  「运行时环境基线」（**最低版本 3.11 / typing 构件上限 3.11**）。
- 依赖现状（判据来源 · 澄清 Q5 的三层口径）：
  `pyproject.toml:43`（`dependencies = []` · **运行时零依赖**）·
  `pyproject.toml:76`（`[dependency-groups]` · PEP 735 **开发期依赖组** · **不进发行包** ·
  现含 `pytest` / `packaging`）· `pyproject.toml:49`（v1.0 **无** `[project.optional-dependencies]` ·
  宪法 v1.7.0）⇒ 本 feature 三处**均零新增**。
- 二元性判据的**实测取样**（CPython 3.12.3 · 本会话 · 澄清 Q6 的依据）：
  `class ClassNoInit` → `()`（pos=0）· `class ClassOneArgInit` → `(a)`（pos=1）·
  `class ClassTwoArgInit` → `(a, b)`（pos=**2**）· 自定义 `__call__(self, a, b)` 的实例 → `(a, b)`（pos=**2**）·
  `__call__(self, *, a, b)` 的实例 → `(*, a, b)`（pos=0）· `functools.partial(add, 1)` → `(b, /)`（pos=1）·
  绑定方法 → `(b)`（pos=1）· 内置 `max` / `str` → `inspect.signature` 抛 `ValueError`（签名不可取）。
- 验收契约（**只读**）：`harness/demo/target.py:59-61`
  （`class MessagesState(TypedDict)` · `messages: Annotated[list[AnyMessage], operator.add]` ·
  `llm_calls: int`；且 `from typing_extensions import TypedDict, Annotated` —— 裁定 3 的直接依据）·
  `target.py:81`（`state.get('llm_calls', 0)`）。
- 立项书 §5.3 的 **C1 字面写「`TypedDict` / Pydantic」**，而本 feature **只支持 `TypedDict`**
  （裁定 7）—— **二者不冲突**：立项书 **D15** 已把 B4F1 / B5F1 的「schema 校验」在 v1.0 定位为
  「**降级为标准库 / 自研替代**」（`[pydantic]` extra 在 v1.0 **不存在** · 宪法 v1.7.0）
  ⇒ 本 feature 的口径以 **D15 + 宪法 v1.7.0** 为准；C1 的字面表述属**上位文档的同步副本未更新**
  ⇒ **仅登记**（不改立项书 —— 属立项书的修订范围，不在本 feature 的变更面内）。
- 前置 feature 规格与契约：`specs/b2f2-public-api-facade/spec.md`（门面 7 符号面冻结）·
  `specs/b2f1-contracts-protocols/contracts/public-api.md`（契约层 18 符号面 · C1–C27 对照）·
  `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md`（**`src/freegraph/runtime/` = L2** ·
  本 feature 零改动）· `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md`（G1–G30）。
- 本 feature 提示词初稿：`harness/features/B4F1_schema解析与归约器提取.md`。
