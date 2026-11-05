# Feature Specification: 契约层骨架（四个核心类型 + 异常体系）

**Feature Branch**: `001-p01-contracts-core`

**Created**: 2026-11-05

**Status**: Draft

**Input**: User description: "F1P1 · 契约层骨架（`contracts/` 包 + 四个核心类型 + 异常体系）" —— 完整提示词正文见 `harness/features/F1P1_契约层骨架.md`。要点：交付 freegraph 的唯一数据与类型契约层（状态字典 / 命令原语 / 状态快照 / 运行配置 + 统一异常体系），本 Phase 不交付任何运行时行为。

## Clarifications

### Session 2026-11-05

- Q: 命令原语的三个语义位（跳转、写入、恢复）应该遵守什么样的填写规则？ → A: 至少填一个：三个都为空（None）时构造即抛 `FreegraphError`；填了哪个生效哪个，三者可任意组合（含「跳转 + 写入」同填、「恢复 + 跳转」同填）。
- Q: 状态字典 `StateDict` 要不要支持 `StateDict[我的Schema]` 这种带参数的写法，好让编辑器能补全具体字段名？ → A: 不支持参数化。`StateDict` 保持与 `dict[str, Any]` 兼容的类型别名；需要字段补全的用户改用自己的 `TypedDict` 标注节点签名（状态形状本就是用户定义的，内核按鸭子类型不校验注解一致性）。
- Q: 用户手上的裸 dict 配置该用哪种方式转成运行配置 `RunConfig`，遇到 dict 里多出来的陌生键又该怎么处理？ → A: 提供 `RunConfig.from_dict(d)` 工厂：默认严格——未知键抛 `FreegraphError`（暴露拼写错误）；另提供 `ignore_unknown=True` 开关走宽松，供运行入口将来容忍 JSON 整包透传。
- Q: 状态快照 `StateSnapshot` 的七个字段各自应该是什么类型？尤其是时间戳用什么形式表示、`next` 用元组还是列表、`config` 是不是就是 `RunConfig`。 → A: `values: StateDict`、`next: tuple[str, ...]`、`config: RunConfig`、`metadata: Mapping[str, Any]`（初稿记为 `dict[str, Any]`，后按本会话「metadata 一律只读映射」的决策统一）、`created_at: str`（UTC 的 ISO-8601 字符串，必填）、`tasks: tuple[Any, ...]`、`interrupts: tuple[Any, ...]`。
- Q: 三个具名异常各自要携带哪些信息，好让上层捕获之后还能知道到底发生了什么？ → A: 三个异常各暴露结构化属性——`InvalidUpdateError` 给出「不认识的 key」列表、`GraphRecursionError` 给出「递归上限」与「已达步数」、`GraphInterrupt` 给出中断载荷（按契约 C17 带 `.value` 与 `.id`）；错误消息只是给人看的摘要。
- Q: `Command.PARENT` 这个常量应该是什么值、什么类型？ → A: 字符串哨兵 `"__parent__"`（与 LangGraph 同构：`PARENT: ClassVar[Literal["__parent__"]]`），类型简单、JSON 友好。
- Q: `goto` 字段应该接受什么？ → A: `goto: str | Sequence[str] | None`——单个目标用节点名字符串，一组目标用任意序列（元组、列表都收）；命令原语只在进程内节点间传递，不强制单一容器形态。
- Q: 三个异常的结构化属性应该叫什么名字？ → A: `InvalidUpdateError.invalid_keys`（未知 key 列表）、`GraphRecursionError.recursion_limit` + `.current_step`、`GraphInterrupt.payload`（中断载荷**对象**，按契约 C17 带 `.value` 与 `.id`——保持对象形态，将来载荷加字段不必改异常的 API）。
- Q: 状态快照的 `metadata` 字段类型最终取哪一个？ → A: 一律 `Mapping[str, Any]`（只读映射），与 `RunConfig` 统一；实现时持有 `dict` 实例，对外注解一律为 `Mapping`。
- Q: 容器防御性拷贝覆盖哪些字段？ → A: `StateSnapshot` **只拷 `metadata`**；`RunConfig` **拷 `metadata` + `tags`**；拷贝为**浅拷贝**（嵌套容器仍与调用方共享同一对象）。
- Q: 契约层的静态导入扫描是否允许包内相对导入？ → A: 允许——`freegraph.contracts` **内部**的相对导入（`from .types import ...`）合法；禁止指向顶层 `freegraph` 与任何包外 `freegraph.*`。
- Q: 源文件署名头是否覆盖测试文件？ → A: 覆盖——本仓库新增的**每一个** `.py`（含 `tests/` 下的测试文件）MUST 携带署名头；`py.typed` 与 `harness/demo/target.py` 按宪法例外清单处理。
- Q: 原则 IX 要求的「独立实现、非 LangChain Inc. 产品」声明何时补？ → A: 本 Phase 随 API 兼容矩阵一并补入 `README.md`（FR-016）。
- Q: 契约层在构造时应该对传入的值做多少运行时校验？ → A: 只保留两条已冻结的构造规则（`Command()` 三语义位全空抛错、`RunConfig.from_dict` 遇未知键抛错），其余一律**只做类型注解、不在构造期校验值**——`created_at` 的 UTC ISO-8601 格式由生产者（各持久化后端）保证，不因格式不符而在构造期抛错。
- Q: 三个异常在未显式传入 `message` 时自动生成的那句摘要，应该用中文还是英文？ → A: **摘要用英文**（面向下游消费者与上游报错的逐条对照），**docstring 用中文**（沿用项目现有的文档惯例）——两者分开，避免对外文案与内部文档互相迁就。

### Session 2026-11-05（实现阶段 · 依赖剥离与最低版本上调）

> 本轮澄清发生在**实现阶段**（F1P1 编码期间）——起因是发起者复核依赖策略时
> 指出「依赖 `typing-extensions` 令人不爽」，遂展开评估。三条结论已回写 spec。

- Q: freegraph 是否真的需要 `typing-extensions`？最低 Python 版本该定多少？ → A: **不需要，且可以完全剥离**。实测（真 Python 3.10.21）：31 份 Phase 提示词用到的 typing 构造只有 `Annotated` / `Protocol` / `TypedDict` / `runtime_checkable` / `get_type_hints`，**全部是 3.10 标准库成员**；`Self` / `NotRequired` / `TypeVarTuple` / `Unpack` / `LiteralString` / `dataclass_transform` / `asyncio.TaskGroup` / `ExceptionGroup` 出现 **0 次**（F12P1 FR-008 明写 v1 不引入 async）。缺口可用标准库惯用法闭合（`Self` → `TypeVar` bound 惯用法、`assert_never` → `NoReturn`、`Required`/`NotRequired` → 结构化识别）。→ **最低 Python 版本抬至 3.11**（3.11 一次性补齐 7 项 typing 构件，而 3.12 / 3.13 各只补 2 项，性价比最高），`typing-extensions` 从基础安装**剥离**，依赖闭包变为**空集**。
- Q: 剥离 `typing-extensions` 后，原先依赖它的最低版本理由（`Self` 在 3.10 可用）还成立吗？ → A: **不成立**——`typing.Self` 是 **3.11** 才进入标准库的（实测 3.10.21 无 `Self`）。立项书 §5.4（E18 / 第 190 行）当初把最低版本定为 ≥3.10 的理由写作「`typing.Protocol` / `TypeAlias` / `Self` 在 3.10 起可用」，该前提**经实测不成立**；且同一行本已写明「`typing-extensions` 只需兜底少数新特性，**不作为最低版本约束**」。
- Q: 抬高最低 Python 版本会缩小兼容面吗？与上游 LangGraph 的关系如何？ → A: **会窄一档**——LangGraph 要求 3.10+，freegraph 抬到 3.11+ 后要求比被替代物更新，方向上是兼容性倒退。**接受该代价**，因为 ① Python 3.10 已于 **2026-10 结束安全支持**（本轮定稿于 2026-11），为一个即将 v1.0 的新项目把底线定在已停止安全支持的 Python 上是更坏的决定；② 3.11 的 typing 增量 / 兼容面损失比最佳；③ LangGraph 自身在 3.10 EOL 后亦会跟进。**已冻结的公开面（8 个符号 / 字段名 / 字段注解 / 行为）完全不变**——本次只改**依赖声明**与**解释器版本下限**。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 外部项目直接引用状态与运行配置类型 (Priority: P1)

作为 freechain（LangChain 替代层）的开发者，我希望能只导入 freegraph 的契约层，
直接用「状态字典」与「运行配置」这两个类型来定义节点函数的签名，并在类型检查器里
得到补全——以便我不必猜测 freegraph 的状态形状，也不必为了一个类型注解就把整个图
运行时拖进我的依赖里。

**Why this priority**: 契约层是全部 31 个 Phase 的前置地基。若这层不能被单独消费，
freechain 就被迫依赖 freegraph 的运行时实现，跨仓库分层（freegraph 内核 / freechain
框架）随之失效——这是本 Phase 存在的第一理由。

**Independent Test**: 在一个只装了 freegraph 基础包、且未安装任何 LangChain 家族包的
环境中，执行一次状态类型与运行配置类型的导入，并用它标注一个节点函数的入参与返回值；
导入成功、类型检查通过、且过程中未加载任何图运行时 / 持久化 / 可观测相关模块，即算独立交付。

**Acceptance Scenarios**:

1. **Given** 一个仅安装了 freegraph 基础包的环境，**When** 导入状态字典类型与运行配置类型，**Then** 导入成功，且进程内已加载模块清单中不含任何图运行时、持久化、可观测相关模块。
2. **Given** 一个已写好的节点函数，**When** 用状态字典类型标注其入参、用运行配置类型标注其配置入参，**Then** 类型自省工具能完整解析这些注解且不报未定义。
3. **Given** 一个从 JSON 或环境读出的裸 dict 配置（键集为 `thread_id` / `context` / `metadata` / `tags`），**When** 需要转成运行配置类型，**Then** 存在一条明确的构造路径（`from_dict`），调用方无需逐字段搬运；默认路径在遇到四字段之外的陌生键时会明确报错，而不是悄悄丢掉。
4. **Given** 一个未安装 LangChain 家族任一包的环境，**When** 导入契约层的全部公开类型，**Then** 导入成功——契约层不因缺少 LangChain 家族而失效。
5. **Given** 一个用户自有的状态 schema（以标准 `TypedDict` 表达），**When** 把它交给图定义层使用，**Then** 用户无需继承任何 freegraph 基类即可使用。

---

### User Story 2 - 运行时实现者用统一异常语义表达失败 (Priority: P2)

作为内核实现者，我希望所有跨层失败都有统一基类与稳定名字
（`InvalidUpdateError` / `GraphRecursionError` / `GraphInterrupt`），
以便上层只捕获基类就能兜住全部内核错误——不必逐个枚举子类，
也不必担心后续补丁版本新增子类时漏捕获。

**Why this priority**: 异常体系是「基类 + 稳定子类名」的一次性冻结机会。
用户故事 1 解决「能引用类型」，用户故事 2 解决「能兜住失败」——
两者共同构成契约层的可用性下限；本 Phase 不交付运行时，故 P2 的价值完全落在
「结构约束可被自动断言」上。

**Independent Test**: 断言三个具名异常都派生自同一基类、该基类派生自内置异常基类；
再验证「只捕获基类」即可捕获全部三者；并验证「节点返回了状态 schema 中不存在的 key」
这一场景的异常消息能指明那个未知 key。

**Acceptance Scenarios**:

1. **Given** 三个具名异常类型，**When** 逐个检查继承关系，**Then** 三者都派生自同一基类，且该基类派生自内置异常基类。
2. **Given** 任意一个具名异常的实例，**When** 只捕获该基类，**Then** 捕获成功，无一漏网。
3. **Given** 一个节点返回了状态 schema 中不存在的 key，**When** 运行时抛出对应异常，**Then** 异常消息指明那个未知 key。
4. **Given** 一个发生递归超限的运行，**When** 抛出递归超限异常，**Then** 异常可被基类捕获且消息含递归上限信息。
5. **Given** 一个节点主动中断，**When** 抛出中断异常，**Then** 异常可被基类捕获，且携带可被上层读取的中断载荷。

---

### User Story 3 - 契约层可被单独审计与冻结 (Priority: P3)

作为 freechain 的打包者，我希望能只依赖契约层本身（不触发运行时 / 持久化 / 可观测
任何代码），以便契约变更能被单独审计与冻结；作为 freegraph 的维护者，我希望能用
一条静态断言把「契约层不引用内部模块」这条红线，变成流水线里的失败条件而不是
口头约定。

**Why this priority**: 可审计性是本项目的核心资产（「可审计的契约」）。
P1/P2 交付「契约存在」，P3 交付「契约不被内部实现污染」——
若契约层内部偷偷引用了运行时，后续 30 个 Phase 的分层将全部失守且无法被察觉。

**Independent Test**: 对契约层做静态扫描，断言其导入图中零条边指向 freegraph 内部模块；
再分别检查「仅导入顶层包」与「仅导入契约层」两种情况下的已加载模块清单。

**Acceptance Scenarios**:

1. **Given** 契约层已交付，**When** 扫描其全部源文件的导入关系，**Then** 没有任何一条指向 freegraph 内部模块（运行时 / 图定义 / 持久化 / 可观测等）。
2. **Given** 一个刚完成顶层包导入的进程，**When** 检查已加载模块清单，**Then** 清单中不含契约层 / 图定义 / 运行时 / 持久化 / 可观测任何子模块。
3. **Given** 一个只导入了契约层的进程，**When** 检查已加载模块清单，**Then** 清单中除顶层包与契约层外不含任何 freegraph 子模块。
4. **Given** 一次刻意引入内部模块引用的改动，**When** 流水线运行静态断言，**Then** 断言失败并阻断合入。

---

### Edge Cases

- **顶层包被导入、但其子模块未被连带加载**：此时访问子模块属性会失败（明确报错），而不是静默把整个内部层拉进内存——这正是「惰性」契约的可观察后果。
- **契约层导入时环境中恰好装有 LangChain 家族包**：契约层的存在与这些包**不得**改变任何行为（不得读取其环境变量、不得触发其遥测、不得受其影响）。
- **状态字典中某 key 的值为空（`None`）**：仍属于「当前有值的 key」，必须出现在节点入参中——与「空 channel 的 key 不得出现」是两件事，不可混淆。
- **用户用宽泛的 `StateDict` 标注、还是用自己的 `TypedDict` 标注节点签名**：两者都被接受，内核不校验注解与状态 schema 是否一致（鸭子类型）——因此「稀疏入参」这一事实 MUST NOT 由内核强制纠正，只由文档与类型注解的自觉使用承担。
- **命令原语的三个语义位全部缺省**：这是**非法**输入——构造时即 MUST 抛出 `FreegraphError`（fail fast），而不是等运行到该节点才报错，也不是静默退化成空操作。
- **命令原语的语义位「显式给了但内容为空」**：合法，语义为「该位不产生动作」（例如 `update={}` 表示不写入任何状态、`goto=()` 表示不跳转）——与「未提供」（`None`）必须区分对待。
- **命令原语的「恢复」与「跳转」同时出现**：合法，两者是独立语义位，互不排斥。
- **用户把节点命名为 `__parent__`**（撞上父图哨兵值）：该名字视为**保留名**——运行时 MUST NOT 让它与「跳向父图」产生歧义（节点名校验归 **F7P2 / F9P1**，本 Phase 只冻结「该名字属保留名」这一约定）。
- **命令原语的跳转目标为空**：等同于「不跳转」（与「显式给了但内容为空」同义）。
- **快照的 `next` 为空元组**：表示该快照之后无待执行节点（运行已结束 / 等待外部输入）。
- **快照的 `created_at` 时区与格式**：MUST 一律为 UTC 的 ISO-8601 字符串且必填——避免各持久化后端各写各的格式，导致时间线排序与对比出错。
- **异常子类名单在未来版本新增**：基类名一旦冻结不得更改，上层只捕获基类即可继续工作。
- **契约层被以相对导入方式在包内引用**：行为须与绝对导入一致。
- **用户环境中恰好存在同名第三方包**：契约层的公开符号须使用绝对导入，不得被同名字符串劫持。
- **隔离环境安装 freegraph 基础包时**：不得因 extras 未安装而使契约层导入失败。
- **运行入口收到裸 dict 配置**（智能体上下文本就是 JSON，裸 dict 是常态）：须能无摩擦地转成运行配置，调用方不必逐字段搬运——这是本 Phase 冻结「裸 dict 构造路径」的直接动因。
- **裸 dict 里出现四字段之外的陌生键**：默认路径 MUST 抛出 `FreegraphError` 并在消息中点名那个键（配置拼写错误 MUST 当场暴露，而非静默吞掉）；走 `ignore_unknown=True` 宽松开关时则忽略未知键。
- **`created_at` 的格式不符不在构造期报错**：本 Phase 只冻结字段与格式约定（FR-004），契约层**不因 `created_at` 不匹配 UTC ISO-8601 而在构造期抛错**——格式合规是生产者（各持久化后端）的责任（构造期校验边界见 Assumptions）。
- **`Command(resume=None)` 与「恢复值为 `None`」不可区分**：`resume` 的缺省值即 `None`，故「恢复一个取值恰为 `None` 的中断」与「未提供恢复值」在当前冻结注解（`resume: Any | None = None`）下无法区分。本 Phase **不改该注解**（FR-003 已冻结字段类型），此限制记在案——若将来需要区分，须走**契约修订**（与宪法 §Governance 的修订流程一致：说明「变更了什么 / 为什么 / 受影响的类型与特性 / 迁移方案」），并同步更新 `contracts/public-api.md` 的冻结面速查，不得就地改型。
- **`StateSnapshot.metadata` 传入 `None`**：不属合法用法（`metadata` 必填、可为空映射）。契约层**不做值级校验**，但构造期的**容器防御性拷贝**会对 `None` 执行 `dict(metadata)` 而抛 `TypeError`——这是**拷贝的副作用**（不是契约层主动校验的值），调用方须自行保证传入合法值（边界见 Assumptions 的校验边界）。同一口径适用于 `RunConfig.metadata`。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系统 MUST 提供契约层包，导入成功且不产生任何运行时副作用——不读环境变量、不发起网络请求、不加载任何内部层模块。
- **FR-002**: 系统 MUST 定义**状态字典**类型，表示图状态的**稀疏字典**（只包含当前有值的 key）；类型上 MUST 与 `dict[str, Any]` 兼容，MUST NOT 自造并行状态类型体系，MUST NOT 要求用户继承任何 freegraph 基类。**MUST NOT 支持按 schema 参数化**（不提供 `StateDict[MySchema]` 写法）——需要具体字段补全的用户改用自己的 `TypedDict` 标注节点签名；内核 MUST NOT 校验节点注解与状态 schema 的一致性（鸭子类型）。
- **FR-003**: 系统 MUST 定义**命令原语**类型，承载 `goto` / `update` / `resume` 三个语义位（三者可同时出现），并提供「向父图跳转」的常量。**跳转目标 MUST 同时支持「单个目标」与「一组目标」两种形态，字段类型 MUST 冻结为 `goto: str | Sequence[str] | None`**——单个目标为节点名的字符串，一组目标为任意序列（元组、列表都收）；本 Phase 不导出 `Send`，故目标 MUST 是节点名。**「向父图跳转」常量 MUST 冻结为 `Command.PARENT`，其值 MUST 是字符串哨兵 `"__parent__"`**（与 LangGraph 同构），语义为「跳向最近的父图」；该节点名视为保留名。**填写规则 MUST 冻结为：三个语义位中至少要填一个——三者全为 `None`（未提供）时，构造该命令 MUST 抛出 `FreegraphError`；三者可任意组合（包括「跳转 + 写入」同填、「恢复 + 跳转」同填），各语义位互不排斥。**
- **FR-004**: 系统 MUST 定义**状态快照**类型，字段为 `values` / `next` / `config` / `metadata` / `created_at` / `tasks` / `interrupts`（七字段，字段清单即冻结面，不得增删）。**字段类型 MUST 冻结为**：`values: StateDict`（稀疏状态字典）、`next: tuple[str, ...]`（待执行节点名，空元组表示无后续节点）、`config: RunConfig`、`metadata: Mapping[str, Any]`（可为空映射）、`created_at: str`（**UTC 的 ISO-8601 字符串，必填**——各持久化后端 MUST 用同一格式）、`tasks: tuple[Any, ...]`、`interrupts: tuple[Any, ...]`（后两项的元素类型由 **F2P1** 细化，本 Phase 以宽松类型承载）。
- **FR-005**: 系统 MUST 定义**运行配置**类型，字段为 `thread_id` / `context` / `metadata` / `tags`（四字段，字段清单即冻结面）；MUST NOT 复用 LangChain 家族的运行配置类型（复用即把 `langsmith` 拖回依赖树）。**可变性约定 MUST 与状态快照统一**——`metadata` 在两个类型中一律声明为 `Mapping[str, Any]`（只读映射）、`tags` 为 `Sequence[str]`，MUST NOT 一处声明可变 `dict` 而另一处声明只读 `Mapping`。
- **FR-006**: 系统 MUST 提供统一异常体系：一个统一基类 **`FreegraphError`** + `InvalidUpdateError`（节点返回了状态 schema 中不存在的 key）+ `GraphRecursionError`（递归超限）+ `GraphInterrupt`（节点主动中断）。三个子类 MUST 全部派生自 `FreegraphError`，`FreegraphError` MUST 派生自内置异常基类。基类名 `FreegraphError` 即冻结面，不得再改。**三个异常 MUST 各自暴露结构化属性，且属性名即冻结面**（错误消息只是给人看的摘要，上层 MUST NOT 需解析消息才能取到细节）：`InvalidUpdateError.invalid_keys` MUST 给出「状态 schema 中不存在的 key」列表（实现为 `tuple[str, ...]`，顺序保持）；`GraphRecursionError.recursion_limit` 与 `GraphRecursionError.current_step` MUST 分别给出「递归上限」与「已达步数」；`GraphInterrupt.payload` MUST 给出中断载荷**对象**（按契约 **C17**，载荷带 `.value` 与 `.id`）——保持对象形态，将来载荷加字段 MUST NOT 要求改动异常的 API。**`message` 缺省时自动生成的摘要 MUST 使用英文**（面向下游消费者与上游报错的逐条对照）；而三个异常类的 docstring 沿用项目现有的中文文档惯例。
- **FR-007**: 契约层 MUST **零**第三方运行时依赖——基础安装（不含任何 extras 变体）的依赖闭包 MUST 为**空集**；MUST NOT 引入任何第三方运行时依赖。**最低 Python 版本为 3.11**（3.11 起 `Self` / `NotRequired` / `Required` / `TypeVarTuple` / `Unpack` / `LiteralString` / `dataclass_transform` 均在标准库内，故无需 `typing-extensions` 兜底；见 Clarifications 的「Session 2026-11-05（实现阶段 · 依赖剥离与最低版本上调）」）。
- **FR-008**: 契约层 MUST NOT import 任何 freegraph 内部模块（运行时 / 图定义 / 持久化 / 可观测等）。
- **FR-009**: 本层导出的全部类型 MUST 具备完整类型注解，且包 MUST 随发行产物发布 `py.typed`（PEP 561）。
- **FR-010**: 本 Phase 新建的**每一个源文件 MUST 携带署名头**（宪法原则 X）：`# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph`（模块 docstring 仍 MUST 是首个语句）。**范围含仓库内新增的测试文件**（`tests/` 下的 `.py`）——原则 X 的「仓库内的脚本」按「本仓库新增的一切 `.py` 源文件」执行；例外仅 `py.typed` 与 `harness/demo/target.py`（宪法原文的例外清单）。
- **FR-011**: 顶层包 MUST 保持惰性——MUST 只暴露 `__version__` 等元信息，MUST NOT 导入契约层 / 图定义 / 运行时 / 持久化 / 可观测任何子模块；导入顶层包 MUST NOT 连带加载内部层。
- **FR-012**: 四个核心类型与异常体系的最终定义（名称、字段、字段语义、表示形态）MUST 落盘并记入 Phase 验收记录，作为**后续 30 个 Phase**（v1 合计 31 个 Phase 中的其余 30 个）的唯一引用基准。
- **FR-013**: 契约层 MUST NOT 读取任何环境变量（`LANGSMITH_*` / `LANGCHAIN_*` / `LANGGRAPH_CLOUD_LICENSE_KEY` 一律不读），MUST NOT 发起任何出站请求。
- **FR-014**: 四个核心类型的**表示形态** MUST 冻结如下——**`StateDict`** = 与 `dict[str, Any]` 兼容的类型别名（MUST NOT 是新造类：节点函数注解 `state: StateDict` 收到普通 dict 时类型检查必须通过）；**`RunConfig` / `Command` / `StateSnapshot`** = **类**（不可变记录：具名参数构造、构造后字段不可改、具 repr 与字段级相等语义）。`Command` MUST 另提供类级常量 `Command.PARENT`（取值与类型见 FR-003：字符串哨兵 `"__parent__"`，语义为跳向最近的父图）。`RunConfig` MUST 提供**从裸 dict 构造**的路径 `RunConfig.from_dict(d)`（键集与四字段一致），以便运行入口在后续 Phase 容忍裸 dict 传入时，调用方无需改代码（智能体上下文多为 JSON，裸 dict 是常态）。**该路径 MUST 默认严格**——`d` 中出现四字段之外的键时 MUST 抛出 `FreegraphError`（当场暴露 `threadId` 这类拼写错误）；**MUST 同时提供 `ignore_unknown=True` 开关**走宽松（忽略未知键），供运行入口在容忍 JSON 整包透传时使用。MUST 与「状态字典 MUST 与 `dict[str, Any]` 兼容」及「用户 schema 用标准 `TypedDict` 表达」两条既有约束自洽。**构造期校验 MUST 仅限这两条**（`from_dict` 的未知键判定 + FR-003 的三语义位全空），其余值一律不校验（见 Assumptions）。
- **FR-015**: 契约层的公开符号面 MUST 严格等于 FR-002…FR-006 列举的四个核心类型与异常体系；本 Phase **MUST NOT** 导出 `Send` 与 `interrupt`（二者归 **F2P1** 协议范畴），MUST NOT 导出任何其他占位符号。「预留类型位」仅指设计上留出扩展位置，不指本 Phase 定义实体。（该清单的**唯一手工维护点** = `contracts/public-api.md` §0；spec / plan / tasks / 兼容矩阵中的同款清单均以其为准。）
- **FR-016**: 系统 MUST 落两份**活文档**：① 仓库根的 `THIRD_PARTY_NOTICES`（第三方代码归属登记 + 依赖登记 + 「不构成 affiliation」声明）；② `README.md` 的「API 兼容矩阵」章节——逐个列出本层 8 个公开符号，各自标注「行为等价 / 部分等价 / 不支持」并说明差异。两份文件 MUST 覆盖本 Phase 引入的全部公开面与依赖，MUST NOT 以「后面还有 Phase 会补」为由留空；`README.md` MUST 另含**「独立实现、非 LangChain Inc. 产品」**的声明（宪法原则 IX · 第三方商标禁令），MUST NOT 仅以「不构成 affiliation」一句替代；本 Phase 只负责**建立并填入本层内容**，**补全与定稿归 F24P1**（立项书 §5.2）。

### Key Entities

- **状态字典（`StateDict`）**: 图状态的稀疏映射，只含当前有值的 key；**表示形态 = 与 `dict[str, Any]` 兼容的类型别名（不支持按 schema 参数化）**；对应契约 C1 / C4 / C6；用户自有的状态 schema 由标准 `TypedDict`（或 Pydantic）表达，本类型只是「运行时传给节点的稀疏字典」的类型名。
- **命令原语（`Command`）**: 节点返回的命令，承载跳转 / 写入 / 恢复三个语义位（**至少填一个；三者可任意组合**）；`goto: str | Sequence[str] | None`（目标为节点名）；类级常量 `Command.PARENT` = 字符串哨兵 `"__parent__"`（跳向最近的父图）；**表示形态 = 不可变类**；对应契约 C16 / C17。
- **状态快照（`StateSnapshot`）**: 某一时刻的状态 + 待执行节点 + 任务 + 中断的完整载体；字段 `values: StateDict` / `next: tuple[str, ...]` / `config: RunConfig` / `metadata: Mapping[str, Any]`（只读映射；实现时持有 `dict`）/ `created_at: str`（UTC ISO-8601，必填）/ `tasks: tuple[Any, ...]` / `interrupts: tuple[Any, ...]`；**表示形态 = 不可变类**；对应契约 **C19**（checkpointer 协议所承载的**快照形状**——C19 本身是 checkpointer 协议，归 F2P1；本 Phase 只冻结快照的字段与格式）。
- **运行配置（`RunConfig`）**: 单次运行的配置载体；字段 `thread_id` / `context` / `metadata` / `tags`；`context` 是独立通道（不塞进 `configurable`，C21）；**表示形态 = 不可变类 + `from_dict` 裸 dict 构造路径（默认严格、未知键抛错，可切宽松）**；对应契约 C22。
- **内核异常基类（`FreegraphError`）**: 三个具名子异常的共同基类，派生自内置异常基类；上层只捕获它即可兜住全部内核错误。
- **`InvalidUpdateError`**: 节点返回了状态 schema 中不存在的 key；**结构化属性 = `invalid_keys`**（未知 key 列表）。
- **`GraphRecursionError`**: 递归超限；**结构化属性 = `recursion_limit`（递归上限）+ `current_step`（已达步数）**。
- **`GraphInterrupt`**: 节点主动中断；**结构化属性 = `payload`**（中断载荷对象，按 C17 带 `.value` 与 `.id`）。

### Out of Scope

- 不实现任何运行时行为：无调度、无 channel、无状态读写。
- 不实现 `invoke` 入口「容忍裸 dict 配置」这一运行时行为本身（属 **F7P3**）——本 Phase 只冻结 `RunConfig` 提供了裸 dict 构造路径，使该行为将来落地时无需改动已冻结的类型形状。
- 不定义节点函数协议与 4 类协议（`Node` / `Checkpointer` / `TraceSink` / `Store`）——属 **F2P1**。
  - 注：`Store` 协议（**C20**）虽**仍冻结**，但 v1 无实现（F17 已砍，2026-11-05）——契约层保留它是为了 freechain 的设计输入不被破坏。
- 不定义公开 API 门面 `freegraph/graph.py`——属 **F2P2**。
- 不搭建 `pyproject.toml` 的 **extras 划分** / CI 门禁——属 **F3P1**（本 Phase 只按 Clarifications「Session 2026-11-05（实现阶段 · 依赖剥离与最低版本上调）」把依赖白名单改为**空**并把 `requires-python` 抬至 3.11，**MUST NOT** 新增 extras、**MUST NOT** 新增第二发行包）。
- 不实现 `Send` / `interrupt` 的具体运行时语义，且本 Phase **不导出**这两个符号（FR-015 · 归 F2P1）。
- **不补全也不定稿** API 兼容矩阵与 `THIRD_PARTY_NOTICES` —— 本 Phase 只建立两份活文档并填入本层内容（FR-016），补全与定稿归 **F24P1**（立项书 §5.2）。
- 不新增第二个发行包（D1 已拍板 2026-11-04：契约层 = 主发行包内的子模块）——`pyproject.toml` 保持单一发行包 `freegraph` + extras。
- 不为 freegraph 之外的项目实现任何 LangChain 替代能力（属 freechain 仓库）。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 在隔离环境（只安装 freegraph 基础包）执行契约层导入成功，且该导入的耗时与一次普通本地模块导入同量级（无网络往返、无磁盘上的额外加载动作）。
- **SC-002**: 递归展开 freegraph 自身声明的依赖后，**基础安装（不含任何 extras 变体）**的依赖闭包为**空集**——无 `langsmith` / `langchain*` / `langgraph*`，亦无 `typing-extensions`。（**extras 变体的闭包另按宪法依赖白名单校验**——只允许白名单内的包；extras 由 **F3P1** 引入，本 Phase 尚无 extras。）
- **SC-003**: 静态扫描断言：契约层模块的导入图中**零**条指向 freegraph 内部模块的边（违反即流水线失败）。
- **SC-004**: 四个核心类型的字段与注解 **100%** 覆盖，可由标准类型自省工具完整解析（不出现未解析的字符串注解）。
- **SC-005**: 异常体系满足「三子异常同基类、基类派生自内置异常基类」的结构约束，且基类可被单独捕获（三者无一漏网）；构造「三个语义位全缺省」的命令原语时抛出的错误同样可被基类捕获；三个异常的结构化属性（`invalid_keys` / `recursion_limit` 与 `current_step` / `payload`）MUST 可直接读取，无须解析错误消息。
- **SC-006**: **顶层包惰性**——导入顶层包后已加载模块清单中**不含**契约层 / 图定义 / 运行时 / 持久化 / 可观测；导入契约层后，已加载模块清单中**不含任何 freegraph 内部层模块**（契约层自身的子模块——如类型模块、异常模块——不受此限；另加标准库）。
- **SC-007**: 本 Phase 新建的源文件 **100%** 携带署名头，且模块 docstring 为首个语句（静态扫描可判定）。
- **SC-008**: 四个核心类型与异常体系的冻结记录（名称 / 字段 / 字段语义 / 表示形态）写入 Phase 验收记录，后续 Phase 引用时零歧义。

## Assumptions

- 状态 schema 由用户以标准 `TypedDict`（或 Pydantic）表达；freegraph 不要求用户继承任何基类（依据：C1「接受任意 schema，不要求继承任何基类」）。
- 状态字典采用**类型别名**而非新造类：这是「与 `dict[str, Any]` 兼容」的硬约束的直接推论——若它是独立类，用户节点函数注解 `state: StateDict` 收到普通 dict 时类型检查不通过。
- 自由链（freechain）侧的适配成本由发起者评估为可接受：转换发生在 freechain 边界、写一次约 5–10 行、且因字段清单在本 Phase 冻结而不必再改；freechain 的终端用户看不到本层的运行配置类型。
- `invoke(input, config=None) -> dict` 返回**完整状态**；本 Phase 只冻结「返回类型是状态字典」这一点（依据：C11）。
- `context` 是**独立通道**，不塞进 `configurable`（依据：C21）。
- `run_id` 是**运行期产物**，由运行时在每次 `invoke` / `stream` 开始时生成，用户不可指定、不可覆盖，故**不进** `RunConfig` 字段清单（依据：立项书 §5.3.1 · C22）。
- `StateSnapshot` 的 `tasks` / `interrupts` 元素类型在 F2P1 细化；本 Phase 冻结的是**字段名、字段类型与字段语义**，元素以宽松类型承载。
- **容器防御性拷贝（范围已定）**：`StateSnapshot` **只拷 `metadata`**；`RunConfig` **拷 `metadata` + `tags`**——各自拷为自身持有的新容器（`dict(...)` / `tuple(...)`），MUST NOT 与调用方传入的容器共用同一对象——否则调用方事后修改原 dict 会静默改到已构造的「不可变记录」。拷贝为**浅拷贝**：嵌套容器（如 `metadata` 里的子 dict）仍与调用方共享同一对象——本 Phase 不深拷。
- **拷贝策略的边界**：防御性拷贝**仅覆盖上列 `metadata` / `tags`**；`StateSnapshot.values`、`Command.update`、`Command.goto` 装的是可变容器，按「浅不可变」口径**不拷贝**（调用方事后修改其内容可被观察到）。
- **`metadata` 的可变性约定统一为 `Mapping[str, Any]`**（状态快照与运行配置同），`tags` 统一为 `Sequence[str]`——两个类型都是不可变记录，只读映射是与其自洽的声明；快照与配置的 `metadata` 均**只读**，需要新增键时由调用方**重建整个对象**（新快照 / 新配置），而非就地修改。
- **构造期校验边界（只两条）**：契约层在构造期**只执行两条已冻结的校验**——① `Command()` 三语义位全为 `None` ⇒ 抛 `FreegraphError`；② `RunConfig.from_dict` 遇四字段之外的未知键 ⇒ 抛 `FreegraphError`。其余一律**只做类型注解、不校验值**：`created_at` 的 UTC ISO-8601 格式、`thread_id` 的实际类型、`tags` 元素类型等**均不在构造期校验**——格式与类型由生产者与调用方保证。理由：值级守卫会与后续 30 个 Phase 的实际用法（持久化后端回读、JSON 整包透传）反复冲突，每次冲突都要动已冻结的公开面。
- `RunConfig` 四个字段的**具体注解**本 Phase 采用以下默认，并**自本 Phase 起一并冻结**：`thread_id: str | None`（缺省 `None`）、`context: Any`（缺省 `None`）、`metadata: Mapping[str, Any]`（缺省空映射）、`tags: Sequence[str]`（缺省空序列）。冻结范围 = **字段注解本身**（含 `StateSnapshot` 七字段）；F4P1 / F8P3 只能**新增字段**、不得改动已有字段的注解。**注意区分**：`tasks` / `interrupts` / `payload` 的**元素类型**仍归 **F2P1** 细化——那属「元素类型」而非「字段注解」，与本条不冲突。
- 顶层包沿用仓库既有形态（仅 `__version__` 元信息）；本 Phase 不新增任何顶层导出符号。
- 隔离安装沿用仓库既有 `pyproject.toml`，但按 Clarifications「Session 2026-11-05（实现阶段 · 依赖剥离与最低版本上调）」把**必装依赖白名单改为空**（基础安装零第三方依赖）、`requires-python` 抬至 **3.11**；本 Phase 不新增 extras、不新增发行包。
- 依赖闭包检查以 `importlib.metadata.requires()` 递归展开为准（宪法质量门禁第 2 条）。
- 「类型注解完整」的可判定口径 = 标准类型自省工具能解析出全部注解（含嵌套/继承成员），不依赖任何外部检查器；**`StateDict` 是类型别名而非类**，其可判定口径 = `typing.get_origin(StateDict) is dict` 且 `StateDict == dict[str, Any]`（**不得**用 `isinstance(x, StateDict)` 判定——参数化泛型不是合法的 `isinstance` 第二参数，会抛 `TypeError`）。

## 依据

- 立项书 §5.1（L1 契约层 · ARCH-1/2/3/4）、§5.2（F1P1 行）、§5.3（C1–C27 契约表）、§5.3.1（C22 / C23 字段级约定）、§5.4（4 类协议 + 4 种数据格式）、§5.5（依赖策略）、§9.1（7 项质量门禁）、§12 的 **D1 决议**（2026-11-04：v1 同包子模块 + 顶层包惰性约束）。
- 宪法 `.specify/memory/constitution.md`：原则 I（零 LangSmith 依赖）、原则 II（内核纯净）、原则 VI（规格驱动）、原则 VII（职责边界与内核契约）、原则 X（文档合规义务）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4（C1–C27）+ §3.4.1（C27 增补 + C22 / C23 字段约定，2026-11-05 · D11）。
- 架构与 Phase 拆解：`harness/prompts/guide.md` §2.3 / §4.3。
- 本 Phase 提示词初稿：`harness/features/F1P1_契约层骨架.md`。
