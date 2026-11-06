# feature 0 · 设计决策台账（research.md）

**功能块**: B1F1 · 契约层骨架（四个核心类型 + 异常体系）
**Branch**: `b1f1-contracts-core` · **Date**: 2026-11-05
**输入**: [spec.md](./spec.md)（含 18 条澄清记录）

> 本文是 `/speckit.plan` 的 feature 0 产出：把 spec 里「已冻结但未定实现形态」的部分，
> 逐条落成**可执行的决策**，并记录被否掉的备选与理由。
> 依据纪律：每条决策的「依据」列给出来源标记（`本地路径:行号` / 契约编号 / 上游源码核实），
> 满足宪法原则 VIII。

---

## D-01 · 契约层的文件切分

- **决策**：拆 3 个文件 —— `contracts/__init__.py`（再导出 + `__all__`）、`contracts/types.py`（四个类型）、`contracts/errors.py`（四个异常）。
- **理由**：异常体系与类型定义是两类关注点，分开后 B2F1 新增 4 类协议（`Node` / `Checkpointer` / `TraceSink` / `Store`）时可另起 `protocols.py`，不与本层纠缠；`__init__.py` 只做门面，公开符号面一目了然。
- **被否的备选**：① 单文件 `contracts/__init__.py` 全塞 —— 后续 B2F1 扩容时该文件会迅速膨胀，且「类型 / 异常」两族混排降低可读性；② 每个类型一个文件（4 个）—— 文件过碎，且异常族被拆散。
- **依据**：spec FR-015（公开符号面 = 四类型 + 异常体系）；SC-006「契约层自身的子模块不受 `sys.modules` 判定限制」；立项书 §5.2 B1F1 行「900 行」规模估算。

## D-02 · 「不可变类」的实现机制

- **决策**：用 `@dataclass(frozen=True, slots=True, kw_only=True)` 实现 `Command` / `StateSnapshot` / `RunConfig`。
- **理由**：`frozen=True` 直接给出「构造后字段不可改」；`eq=True`（默认）给出「字段级相等语义」；`repr` 由 dataclass 自动生成（spec FR-014 要求「具 repr」）；`slots=True` 免去实例 `__dict__`，省内存且防止随手挂属性；`kw_only=True` 让「哪个字段是哪个」一目了然，也避免将来加字段破坏位置参数调用。
- **注意**：`frozen=True` 会自动生成 `__hash__`，但 `RunConfig.metadata` / `Command.update` 装的是 `dict`（不可哈希）——**哈希这些对象会抛 `TypeError`**。这是可接受的（不可变记录通常按值比较而非按哈希存入集合），但必须在 docstring 中写明，避免使用者误用。
- **被否的备选**：① `NamedTuple`（LangGraph 的 `StateSnapshot` 就是 NamedTuple）—— 字段不可变且可哈希，但**带默认值的字段受限**（`defaults` 必须最后连续排列），而 `RunConfig` 四个字段全部要有默认值，直接被排除；② `attrs` / `pydantic` —— 前者是新依赖（违反 FR-007），后者是可选 extra 的依赖（不得拉成必装）；③ 纯手写 `__init__` + `__slots__` —— 要自己实现 `__eq__` / `__repr__`，样板代码多且易漏。
- **依据**：spec FR-014；LangGraph 1.2.19 源码核实 `langgraph/types.py:833-855`（`Command` = `@dataclass(kw_only=True, slots=True, frozen=True)`，`PARENT: ClassVar[Literal["__parent__"]] = "__parent__"`）。

## D-03 · `StateDict` 的写法

- **决策**：`StateDict: TypeAlias = dict[str, Any]`（`TypeAlias` 取自标准库 `typing`，Python 3.10 已有 —— 最低版本抬至 3.11 后仍成立）。
- **理由**：spec FR-002 要求「与 `dict[str, Any]` 兼容」且「不造并行状态类型体系」；用别名则节点函数注解 `state: StateDict` 收到普通 `dict` 时类型检查直接通过，无需任何转换或继承。
- **被否的备选**：① `class StateDict(dict[str, Any])` —— 自造了并行类型体系，且用户注解收到普通 dict 时**类型检查不通过**（普通 dict 不是该子类的实例），直接违反 FR-002；② `class StateDict(TypedDict, total=False)` —— TypedDict 无法表达「任意 key」，只能声明固定字段集，与「用户 schema 由用户自己的 `TypedDict` 表达」冲突；③ 泛型别名 `StateDict[MySchema]` —— spec 澄清已明确**不支持参数化**（并因此不需要 PEP 695 `type` 语句或 `TypeAliasType`，避开 Python 3.12+ 语法兼容问题）。
- **依据**：spec FR-002 + 澄清第 2 条；宪法原则 II「不得自带一套并行状态类型体系」。

## D-04 · `RunConfig` 的字段与 `from_dict` 实现

- **决策**：四个字段 `thread_id: str | None = None`、`context: Any = None`、`metadata: Mapping[str, Any] = field(default_factory=dict)`、`tags: Sequence[str] = field(default_factory=tuple)`；`from_dict` 为 `classmethod`，用 `dataclasses.fields(cls)` 取字段名做未知键比对。
- **理由**：`from_dict` 用**类自身的字段元数据**判定未知键，而非硬编码一份字段名清单 —— 后者一旦将来加字段就会与 dataclass 脱节（漂移）。`default_factory` 是 dataclass 对可变默认值的唯一正解（`metadata=dict` 会让所有实例共享同一个 dict）。
- **严格 / 宽松**：默认严格（未知键抛 `FreegraphError` 并点名该键），`ignore_unknown=True` 走宽松。spec 澄清第 3 条已拍板。
- **被否的备选**：① 硬编码 `{"thread_id", "context", "metadata", "tags"}` 常量 —— 与 dataclass 字段两处维护，迟早漂移；② 只提供 `RunConfig(**d)` —— 未知键由 Python 抛 `TypeError`（不是 `FreegraphError`），上层无法用统一基类兜住，且错误消息不点名「未知键」；③ 加第五个字段 `extra` 收纳未知键 —— 破坏 spec FR-005「四字段即冻结面，不得增删」。
- **依据**：spec FR-005 / FR-014 + 澄清第 3 条；立项书 §5.3.1（C22 字段清单不变，`run_id` 不进 `RunConfig`）。

## D-05 · `Command` 的构造期校验

- **决策**：校验放在 `__post_init__` —— `goto` / `update` / `resume` **三者全为 `None`** 时抛 `FreegraphError`。
- **理由**：`__post_init__` 是 dataclass 提供的构造后钩子，**在对象返回给调用方之前**执行 —— 满足 spec 要求的「构造时即抛（fail fast）」；校验规则与类型定义同处一个文件，不会漂移。
- **被否的备选**：① 运行时（调度器）校验 —— 报错点离错误源太远，栈里只剩调度帧；且 spec 澄清第 1 条明确要求构造期拦截；② `__init__` 手写 —— 要重复 dataclass 的字段赋值，样板代码多。
- **注意**：`__post_init__` 在 `frozen=True` 下**不得**给字段赋值（否则 `FrozenInstanceError`）。本 feature 的校验只读不写，无冲突。
- **依据**：spec FR-003 + 澄清第 1 条。

## D-06 · `goto` 是否在构造时归一化

- **决策**：**不归一化**。字段注解与 spec 逐字一致：`goto: str | Sequence[str] | None`，用户传元组则存元组、传列表则存列表。
- **理由**：spec FR-003 冻结的是字段**类型** `str | Sequence[str] | None`。若在 `__post_init__` 里把列表转成元组，字段的实际类型就变成了 `str | tuple[str, ...] | None` —— 与冻结的字面声明不符，且给用户「我传的是列表，属性读出来却是元组」的意外。
- **被否的备选**：归一化成元组 —— 好处是相等语义稳定（`Command(goto=["a"]) == Command(goto=("a",))`）与可哈希；坏处是与冻结注解冲突。**归一化是「更漂亮但更越界」的方案，故否决**。
- **连带事实**：`Command` 虽是「不可变类」，其 `update` / `goto` 字段可能装着可变对象（dict / list）。这是**浅不可变**，与 `RunConfig.metadata` 同理 —— 在 docstring 中写明。
- **依据**：spec FR-003 + 澄清第 2 轮第 2 题。

## D-07 · `Command.PARENT` 的实现

- **决策**：`PARENT: ClassVar[Literal["__parent__"]] = "__parent__"`。
- **理由**：与 LangGraph **逐字同构**（`langgraph/types.py:882`），符合 freegraph「API 同名对齐 LangGraph」的定位，也让从 LangGraph 迁移的代码不必改写；`Literal` 让类型检查器把 `Command.PARENT` 收窄为字面量类型；`ClassVar` 表明它是类属性而非实例字段（dataclass 不会把它当字段，`slots=True` 也不会为它留槽位）。
- **被否的备选**：① 专属对象哨兵（专用类型的单例实例）—— 绝不撞名，但 `goto` 的类型要多一个分支（`str | ParentSentinel | Sequence[...]`），且该对象不可 JSON 序列化；② 换名 `"__freegraph_parent__"` —— 不与 LangGraph 同形，迁移时需转换，违反「同名对齐」定位。
- **连带约定**：节点名 `__parent__` 视为**保留名**，运行时不得与「跳向父图」产生歧义（节点名校验归 B7F2 / B9F1）。
- **依据**：spec FR-003 + 澄清第 2 轮第 1 题；LangGraph 1.2.19 源码 `langgraph/types.py:882`。

## D-08 · 异常的构造签名与属性

- **决策**：
  - `FreegraphError` —— **不自定义 `__init__`**，直接继承 `Exception`（只作为统一基类与类型锚点）。
  - `InvalidUpdateError(invalid_keys: Iterable[str], *, message: str | None = None)` → 属性 `invalid_keys: tuple[str, ...]`。
  - `GraphRecursionError(recursion_limit: int, current_step: int, *, message: str | None = None)` → 属性 `recursion_limit: int` / `current_step: int`。
  - `GraphInterrupt(payload: Any, *, message: str | None = None)` → 属性 `payload: Any`。
- **理由**：结构化属性**以位置参数**传入（它们是主要信息，不该藏在 kwargs 里）；`message` 作为**可选关键字**覆盖（默认由属性自动生成摘要消息）—— 兼顾「上层要结构化数据」与「日志里要一句人话」。`invalid_keys` 内部存为 `tuple` 以保证不可变且可哈希。
- **消息语言**（2026-11-05 澄清确认）：自动生成的摘要用**英文**（面向下游消费者与上游报错的逐条对照），而类与方法的 docstring 沿用项目现有的**中文**文档惯例；默认摘要 MUST 点名关键值（如 `InvalidUpdateError` 的未知 key）。
- **被否的备选**：① 只接 `message: str` —— 回到「上层要解析字符串」的窘境（spec 澄清第 5 条已否决）；② 用一个统一的 `details: dict` 口袋 —— 属性名本身失去类型保护，拼写错误无法被类型检查发现，等于又造了一层消息解析；③ 加 `to_dict()` 序列化助手 —— 有用，但属**额外**便利 API 而非契约必需；本 feature 不加（可在 B18F1「span 必带字段」落地时按需再加，届时属性名已冻结，加方法不破坏契约）。
- **依据**：spec FR-006 + 澄清第 5 题与第 2 轮第 3 题。

## D-09 · `GraphInterrupt.payload` 的类型

- **决策**：本 feature 标注为 `Any`（宽松），并在 docstring 中写明结构约定：**载荷对象须带 `.value` 与 `.id`**（契约 C17）。
- **理由**：`Send` 与 `interrupt` 的**实体**属 B2F1（spec FR-015 明确本 feature 不得导出这两个符号），因此此刻**不存在**可标注的具体载荷类型；若现在自造一个 `InterruptPayload` 类，就等于在契约层新增一个公开符号，**违反 FR-015**。故此处只能宽松承载。
- **代价与缓解**：属性**名**（`payload`）与载荷**结构**（`.value` / `.id`）已冻结，B2F1 落地时只收紧**注解**，不构成契约破坏（spec Assumptions 已授权注解层面的无痛细化）。
- **被否的备选**：① 本 feature 定义并导出 `InterruptPayload` —— 违反 FR-015 的公开符号面约束；② 用 `Mapping[str, Any]` 标注 —— 载荷是**对象**（带属性访问），不是字典，标注会误导使用者用 `payload["value"]`。
- **依据**：spec FR-006 / FR-015 / Assumptions（`tasks` / `interrupts` 元素类型归 B2F1）；Q8 §3.4 C17。

## D-10 · `created_at` 的生成方式

- **决策**：格式为 `datetime.now(timezone.utc).isoformat()`（例：`2026-11-05T10:20:30.123456+00:00`），**必填**。
- **理由**：带显式 `+00:00` 偏移的 ISO-8601 字符串**人类可读**、**可按字典序排序**（同一偏移下字典序 == 时序），且**JSON 友好**（无需自定义编码器）。spec FR-004 已冻结「UTC 的 ISO-8601 字符串，必填」。
- **被否的备选**：① `float` Unix 时间戳 —— 比较排序最直接，但人读不友好、JSON 里是裸数字、丢失「这是个时刻」的语义；② `datetime` 对象 —— 类型最严谨，但快照要落盘就必须配自定义编码器，且带时区的 `datetime` 跨进程传递易出错；③ `Z` 结尾（`...T10:20:30Z`）—— 更短，但 `isoformat()` 不产出该形式，需手工拼接，反而多一处出错点。
- **附带决策**：本 feature **只定义字段与格式**，不提供「生成快照」的功能（那是运行时的活）——故 `created_at` 的**取值来源**由 B7F3 / B14F1 负责。
- **依据**：spec FR-004 + 澄清第 4 题。

## D-11 · 惰性 / 依赖断言的执行方式

- **决策**：所有「已加载模块清单」类断言（SC-006）**在子进程中执行** —— `subprocess.run([sys.executable, "-c", "<内联脚本>"])`，检查子进程的 `sys.modules` 快照。
- **理由**：测试进程自身已导入 pytest（以及 pytest 拉进来的几十个模块），**同进程的 `sys.modules` 必然含无关模块**，无法作为判定依据；只有**全新的解释器进程**才能干净地回答「导入 `freegraph` 到底连带加载了什么」。
- **实现细节**：子进程必须能定位到 `src/` —— 用 `env={**os.environ, "PYTHONPATH": str(SRC)}` 显式注入，不依赖当前工作目录，也不要求先 `pip install`。
- **被否的备选**：① 同进程断言 —— 必然误报；② `importlib` 的 `find_spec` 探测 —— 只能证明「可被发现」，不能证明「已被加载」，而 SC-006 问的正是后者。
- **依据**：spec SC-006（`sys.modules` 判定）；宪法 ARCH-2。

## D-12 · AST 依赖扫描的实现

- **决策**：用标准库 `ast` 解析 `src/freegraph/contracts/**/*.py`，收集 `Import` 与 `ImportFrom` 的模块名，断言其中**不存在**指向 freegraph 内部层的目标。
- **理由**：`ast` 是标准库（不引依赖，符合 FR-007）；且**静态**扫描比运行时观测更严格 —— 运行时探测只能发现「本次导入真的发生了」，静态扫描能发现「代码里写了但当前路径没走到」的隐患，正好对应 spec FR-008「MUST NOT import 任何 freegraph 内部模块」。
- **「内部模块」的判定口径**：目标模块名以 `freegraph.` 开头且**不属于** `freegraph.contracts` 自身者，即为内部模块引用。（`freegraph` 顶层包本身也不在允许清单内 —— 契约层连顶层包的 `__version__` 都不该引，避免顶层包将来被加进东西时形成回边。）
- **相对导入如何处理**（2026-11-05 澄清确认）：`ImportFrom.level == 0`（绝对导入）⇒ 模块名直接参与比对；`level == 1` ⇒ 相对导入，解析后落在 `freegraph.contracts` 内 ⇒ **合法**（`contracts/__init__.py` 的再导出**必须**用它）；`level >= 2`（跳到包外，如 `from ..runtime import X`）⇒ **违规**。
- **被否的备选**：① 运行时 `sys.modules` 观测 —— 见 D-11，只覆盖已执行路径；② 用 `import-linter` / `grimp` 等工具 —— 那是**新依赖**（违反 FR-007），且本 feature 的门禁规则很简单，自写 30 行足够。
- **依据**：spec FR-008 / SC-003；宪法 ARCH-2。

## D-13 · `py.typed` 的落点

- **决策**：**不新建** `contracts/py.typed`，复用顶层既有的 `src/freegraph/py.typed`。
- **理由**：PEP 561 规定，`py.typed` 标记在**顶层包**即覆盖其全部子包 —— 顶层已有该文件，子包类型信息自动生效。为子包再放一个 `py.typed` 是冗余（且部分工具会误报）。
- **判定方式**：架构断言直接检查 `src/freegraph/py.typed` 存在且**内容为空**（PEP 561 要求为空文件）。
- **依据**：spec FR-009；PEP 561；仓库既有文件 `src/freegraph/py.typed`。

## D-14 · 依赖闭包的检查口径

- **决策**：用 `importlib.metadata.requires("freegraph")` 取本包的直接依赖声明，递归展开各依赖的 `requires()`，比对白名单。
  **2026-11-05 更新**：白名单由 `{typing-extensions}` 改为**空集**——基础安装零第三方运行时依赖，
  故**基础安装闭包 MUST 为空集**（见 D-21）。extras 变体闭包另比对宪法依赖白名单。
- **理由**：与宪法质量门禁第 2 条规定的口径一致（「递归展开 `importlib.metadata.requires()` + 许可证白名单校验」）。
- **前置条件**：该检查要求 freegraph **已安装**（有 dist-info 元数据）。故它属于**隔离环境验收**（`quickstart.md` 的第 2 步），而非本地单测；在未安装时该断言应 `skip` 而非失败。
- **被否的备选**：① 解析 `pyproject.toml` —— 那是**声明**，不是**闭包**；真正要拦的是传递依赖；② `pipdeptree` —— 外部工具，且需要额外安装。
- **依据**：spec SC-002；宪法质量门禁第 2 条。

## D-15 · 测试的运行方式

- **决策**：测试放 `tests/contracts/`，配一个 `conftest.py` 把 `src/` 注入 `sys.path`（`sys.path.insert(0, str(SRC))`），使**开发期免安装**即可 `pytest`；同时 `quickstart.md` 另给「隔离 venv 安装后验证」的路径。
- **理由**：仓库当前**未安装** freegraph（`pip show freegraph` → 未找到），若不注入 `sys.path`，本地测试直接 `ModuleNotFoundError`；而「隔离 venv 安装后验证」是 SC-001 / SC-002 的前提，属**验收**环节，不该成为**开发**环节的摩擦。
- **被否的备选**：① 只支持「先 `pip install -e .`」—— 开发期每次改代码都要重装，摩擦大；② 只支持 `PYTHONPATH=src pytest` —— 依赖调用者记得设环境变量，CI 里容易漏；`conftest.py` 两种方式都兼容（装了包也不冲突，因为已安装版本会先命中——**注意**：为避免「装了旧版却测了源码」的困惑，`conftest.py` 的注入置于**最前**，源码优先）。
- **依据**：spec SC-001 / SC-002；仓库现状（`pip show freegraph` 未安装；`pyproject.toml` 无 pytest 配置）。

## D-16 · SC-001「同量级」的可判定阈值

- **决策**：把 spec 的「与一次普通本地模块导入同量级」落成**数值阈值**：隔离 venv 中 `python -c "import freegraph.contracts"` 的墙钟 **< 300 ms**（含解释器冷启动）。
- **理由**：本机实测基线 —— 解释器启动 ≈ 30 ms。取 300 ms 留约 10 倍余量，既能正常通过，又能拦住「契约层偷偷拉起重量级依赖」的退化。**不设更紧的阈值**：CI 机器性能差异大，过紧会造成假失败。（**基础安装零依赖后不再有 `import typing_extensions` 的 ≈ 90 ms 开销**。）
- **被否的备选**：① 相对比较（「导入契约层的耗时 ≤ 导入某重型模块的 3 倍」）—— 表述复杂、跨机器不稳；② 只断言「无网络访问」而不设时间阈值 —— 拦不住「拉起重量级本地依赖」这类退化。
- **依据**：spec SC-001；本机实测基线。

## D-17 · 公开符号面的断言方式

- **决策**：断言 `freegraph.contracts.__all__` **恰好**等于 8 个符号名构成的集合（集合相等，不看顺序），且每个名字都能从 `freegraph.contracts` 直接取到（`getattr` 成功）。
- **理由**：spec FR-015 要求「公开符号面 MUST 严格等于 FR-002…FR-006 列举的四个核心类型与异常体系」。用**集合相等**断言，才能真正抓住「偷偷多导出了一个符号」（如提前导出了 `Send`）——只断言「这 8 个都在」会漏掉多出来的。
- **补充断言**：契约层模块内**不得**出现名为 `Send` / `interrupt` 的公开符号（防止有人提前加占位）。
- **依据**：spec FR-015。

## D-18 · `metadata` 的可变性约定统一为 `Mapping`

- **决策**：状态快照与运行配置的 `metadata` **一律**声明为 `Mapping[str, Any]`，`tags` 一律为 `Sequence[str]`。
- **理由**：两个类型都是**不可变记录**，只读映射是与其自洽的声明；原写法里快照用可变 `dict`、配置用只读 `Mapping`，同一层出现两套约定，实现者无从判断该用哪个。
- **代价**：快照的 `metadata` 若需新增键，调用方必须重建对象而非就地修改 —— 这是不可变语义的应有之义。
- **依据**：spec FR-004 / FR-005。

## D-19 · 容器的防御性拷贝

- **决策**：`StateSnapshot` 在构造时**只拷 `metadata`**；`RunConfig` 拷 `metadata` + `tags`——各自**浅拷贝**为自身持有的新容器（`dict(...)` / `tuple(...)`）。`StateSnapshot` **没有** `tags` 字段，故不存在该拷贝。
- **理由**：否则 `cfg = RunConfig.from_dict(d)` 之后调用方改 `d["metadata"]["x"]`，会**静默改到已构造的 `RunConfig`** —— 与「不可变记录」的心智模型直接冲突，且这类 bug 极难查。
- **边界**：拷贝**仅覆盖** `metadata` / `tags`；`StateSnapshot.values`、`Command.update`、`Command.goto` 按「浅不可变」口径**不拷贝**（见 D-06）；拷贝为**浅拷贝**——嵌套容器仍与调用方共享同一对象。
- **副作用（已知且可接受）**：拷贝对 `None` 不成立——`dict(metadata)` / `tuple(tags)` 遇 `None` 会抛 `TypeError`。这是**拷贝的副作用**（不是契约层主动做的值级校验），spec Edge Cases 已按此口径写明。
- **依据**：spec Assumptions「容器防御性拷贝」。

## D-20 · 文档合规门禁的落盘位置与时机（宪法原则 X）

- **决策**：本 feature **建立**两份活文档 —— 仓库根的 `THIRD_PARTY_NOTICES`、以及 `README.md` 的「API 兼容矩阵」章节 —— 并填入本层的 8 个公开符号与依赖登记；**补全与定稿归 B24F1**。
- **理由**：宪法原则 X 要求「每个特性合入前 MUST 全部通过」质量门禁第 7 条（`THIRD_PARTY_NOTICES` 已登记、API 兼容矩阵已更新），且「MUST NOT 在清单缺项的情况下宣布该特性完成」；而立项书 §5.2 把这两份清单的**创建**放在 B24F1（离本 feature 还有 23 个）。若等到 B24F1 才建，「哪些同名符号行为等价」这个判断会被推迟 23 个 feature 后再回忆 —— 而本层恰好定义了 5 个与 LangGraph **同名**的符号（`Command` / `StateSnapshot` / `InvalidUpdateError` / `GraphRecursionError` / `GraphInterrupt`），它们「等价到什么程度」必须在定义当场判定。
- **为什么放 README 而不是独立文件**：README 是 sdist 的既有内容（`pyproject.toml` 的 `only-include` 已含 `README.md`），放进去就随发行包分发，**无需改 `pyproject.toml`**（本 feature 不得改依赖白名单与打包配置）。
- **可自动判定**：门禁 G8 —— 断言 `README.md` 的兼容矩阵章节覆盖了契约层的全部 8 个公开符号（按「第一列反引号符号名」解析），使「文档合规门禁」从人工评审变成**可执行断言**。
- **依据**：宪法原则 X；立项书 §5.2 / §9.1 门禁 7；LangGraph 1.2.19 源码核实（`langgraph/types.py:711`、`:833`；`langgraph/errors.py:51`、`:68`、`:91`、`:103`；`langchain_core/runnables/config.py:57`）。

---

## D-21 · 剥离 `typing-extensions`，最低 Python 版本抬至 3.11

> **本决策发生于实现阶段**（2026-11-05）——起因是发起者复核依赖策略时指出
> 「依赖 `typing-extensions` 令人不爽」，遂展开评估。**已获发起者批准**，
> 并已按《项目宪法》Governance 流程记为**修订记录 v1.2.0**。

- **决策**：① **基础安装零第三方运行时依赖**（`pyproject.toml` 的 `dependencies = []`）——
  `typing-extensions` **剥离**；② **最低 Python 版本由 `>=3.10` 抬至 `>=3.11`**
  （`requires-python`）；③ 契约层**零改动**——已冻结的 8 个公开符号、字段名、
  字段注解与行为**完全不变**。
- **理由**：
  1. **原依赖的存在理由本身是错的**——立项书 §5.4（E18 / 第 190 行）把最低版本定为
     ≥3.10 的理由写作「`typing.Protocol` / `TypeAlias` / **`Self`** 在 3.10 起可用」，
     但 **`typing.Self` 是 3.11 才进入标准库的**（实测 Python 3.10.21：`hasattr(typing, "Self")`
     为 `False`）；且同一行本已写明「`typing-extensions` 只需兜底少数新特性，
     **不作为最低版本约束**」。
  2. **实测证明 3.10/3.11 的标准库足以支撑 v1 全部 31 个 feature**——31 份 feature 提示词
     用到的 typing 构造只有 `Annotated`(20) / `Protocol`(8) / `TypedDict`(7) /
     `runtime_checkable`(1) / `get_type_hints`(1)，**全部是标准库成员**；
     `Self` / `NotRequired` / `TypeVarTuple` / `Unpack` / `LiteralString` /
     `dataclass_transform` / `asyncio.TaskGroup` / `ExceptionGroup` 出现 **0 次**
     （B12F1 FR-008 明写「本 feature **不引入 async**（v2 范围）——并发用**线程**实现即可」）。
  3. **3.11 的 typing 增量 / 兼容面损失比最佳**——3.11 一次性补齐 **7 项**
     （`Self` / `NotRequired` / `Required` / `TypeVarTuple` / `Unpack` / `LiteralString` /
     `dataclass_transform`），而 3.12（`TypeAliasType` / `override`）与
     3.13（`ReadOnly` / `TypeIs`）**各只补 2 项**。
  4. **Python 3.10 已于 2026-10 结束安全支持**（本决策定稿于 2026-11）——
     为一个即将 v1.0 的新项目把底线定在一个**已停止安全支持**的 Python 上，
     是比「多一个依赖」更坏的决定。
- **代价（明确记录）**：**兼容面比上游 LangGraph（3.10+）窄一档**——
  一个 "drop-in replacement" 要求比被替代物**更新**的 Python，方向上是兼容性倒退。
  **接受该代价**：3.10 本月 EOL、LangGraph 自身亦会跟进；且抬高版本换来的
  「零依赖」对 README 的「零第三方运行时依赖」承诺是**字面为真**的兑现
  （此前是「只有一个包」，读起来仍像打折）。
- **3.10 缺口的闭合办法（若将来为了兼容面需要降回 3.10）**：
  `Self` → **`TypeVar` bound 惯用法**（`_T = TypeVar("_T", bound="StateGraph")`，
  `def add_node(self: _T, ...) -> _T`）；`assert_never` → `NoReturn`；
  `Required` / `NotRequired` → freegraph 自身**不需要命名**它们（鸭子类型哲学），
  确需识别时用 `get_origin()` + `__name__` 做结构化判定（不 import `typing_extensions`）；
  `TypeVarTuple` / `Unpack` / `LiteralString` / `dataclass_transform` → v1 不需要。
  **结论：技术上 3.10 可行**，本决策选 3.11 是**「typing 增量 / 兼容面」的性价比取舍**
  而非技术必需。
- **被否的备选**：
  ① **保持 `>=3.10` + 剥离依赖** —— 技术上完全可行（见上），但放弃 3.11 的 7 项 typing 构件，
     且继续支持一个**已 EOL** 的 Python；
  ② **`>=3.12` / `>=3.13`** —— 3.12 只多给 `TypeAliasType`（已被 D-03 **刻意否决**）
     与 `override`（纯类型检查器标记，**无运行时效果**），3.13 只多给 `ReadOnly` / `TypeIs`
     —— 收益极小，却要再各窄一档兼容面；
  ③ **把 `typing-extensions` 降为 optional extra** —— 等于把「一个必装依赖」换成
     「一个可选用依赖」，但**不解决**「基础安装零依赖」的承诺，且用户为拿 `Self`
     反而要多装一个包；
  ④ **继续保留 `typing-extensions` 为必装** —— 即本次变更前的状态，
     其存在理由已被实测证伪（见「理由」第 1 条）。
- **配套约束（宪法 v1.3.0）**：本决策只把**下限**抬到 3.11，
  但**没有**限制「能用什么」——开发者仍可能用上本机 3.12/3.13 才有的构件
  （`TypeAliasType` / `override` / `ReadOnly` / `TypeIs` / PEP 695 `type` 语句），
  把「3.11 是下限」在**代码里**悄悄破掉。故宪法另立「运行时环境基线」章节：
  **typing 构件上限 = 3.11**，由 **G9 静态断言** + **CI 最低档（3.11）跑全量测试**双重把关。
- **附带影响**：`pip install freegraph` 后 site-packages 里**只有 freegraph 自己**
  （实测：隔离 venv 的包清单 = `['freegraph']`）；`THIRD_PARTY_NOTICES` §2
  「第三方运行时依赖」表随之清空；导入耗时预算的基线由「解释器 30 ms + `typing_extensions` 90 ms」
  降为「解释器 30 ms」（SC-001 阈值 300 ms 不变）。
- **依据**：spec Clarifications「Session 2026-11-05（实现阶段 · 依赖剥离与最低版本上调）」
  · 立项书 §5.4 E18 与第 190 行 · 宪法修订记录 **v1.2.0** ·
  实测证据：CPython 3.10.21 的 `typing` 构件清单（`Self` / `NotRequired` /
  `TypeVarTuple` / `Unpack` / `LiteralString` / `dataclass_transform` /
  `assert_never` / `TypeAliasType` / `override` / `ReadOnly` / `TypeIs` **全部不存在**，
  而 `TypeAlias` / `Protocol` / `TypeGuard` / `ParamSpec` / `Annotated` / `Final` /
  `TypeVar` / `Concatenate` / `Generic` / `NamedTuple` **存在**）。

---

## 决策索引（速查）

| # | 决策 | 影响面 |
|---|---|---|
| D-01 | 契约层拆 3 个文件 | 目录结构 |
| D-02 | `@dataclass(frozen=True, slots=True, kw_only=True)` | 三个类的语义 |
| D-03 | `StateDict` = `dict[str, Any]` 类型别名 | 状态字典 |
| D-04 | `RunConfig` 四字段 + `from_dict`（用 `dataclasses.fields` 判未知键） | 运行配置 |
| D-05 | 构造期校验放 `__post_init__` | 命令原语 |
| D-06 | `goto` **不**归一化 | 命令原语 |
| D-07 | `PARENT: ClassVar[Literal["__parent__"]]` | 命令原语 |
| D-08 | 异常签名：结构化属性为位置参数，`message` 可选关键字 | 异常体系 |
| D-09 | `GraphInterrupt.payload` 本 feature 标注 `Any` | 异常体系 |
| D-10 | `created_at` = `datetime.now(timezone.utc).isoformat()` | 状态快照 |
| D-11 | `sys.modules` 断言必须在**子进程**执行 | 门禁 |
| D-12 | `ast` 静态扫描判内部 import | 门禁 |
| D-13 | 复用顶层 `py.typed`，不新建 | 打包 |
| D-14 | 依赖闭包用 `importlib.metadata.requires()` 递归展开（基础安装闭包 = **空集**） | 门禁 |
| D-15 | `tests/conftest.py` 注入 `src/`（源码优先） | 测试 |
| D-16 | SC-001 阈值 = 300 ms | 验收 |
| D-17 | `__all__` **集合相等**断言 8 个符号 | 门禁 |
| D-18 | `metadata` 统一为 `Mapping[str, Any]` | 数据模型 |
| D-19 | 防御性拷贝：快照拷 `metadata`、配置拷 `metadata` + `tags`（均浅拷贝） | 数据模型 |
| D-20 | 兼容矩阵与 `THIRD_PARTY_NOTICES` 本 feature 建立（活文档） | 文档合规 |
| **D-21** | **剥离 `typing-extensions`（基础安装零依赖）+ 最低 Python 抬至 3.11** | **依赖声明 / 版本下限** |

---

## 未决 / 移交后续 feature

| 项 | 移交对象 | 性质 |
|---|---|---|
| `GraphInterrupt.payload` 的具体类型 | B2F1 / B10F1 | 注解收紧（属性名已冻结，非契约破坏） |
| `tasks` / `interrupts` 元素类型 | B2F1 | 同上 |
| `RunConfig` 四字段的**最终注解**（`Mapping` vs `dict` 等） | — | **已在本 feature 冻结**（字段注解随字段一并冻结）—— B4F1 / B8F3 只能**新增字段**、不得改动已有字段的注解；`tasks` / `interrupts` / `payload` 的**元素类型**另归 B2F1 |
| `invoke` 入口「容忍裸 dict」行为本身 | B7F3 | 运行时行为（本 feature 只冻结 `from_dict` 提供了构造路径） |
| 节点名 `__parent__` 的保留名校验 | B7F2 / B9F1 | 运行时行为 |
| 架构断言接入 CI 流水线 | B3F1 | 工程设施 |
| 兼容矩阵与 `THIRD_PARTY_NOTICES` 的补全与定稿 | B24F1 | 文档合规（**建立与填写**已在本 feature 完成） |
| `typing-extensions` 已在基础安装剥离；**MUST NOT** 再引入 | 全局 | 契约（D-21 · 宪法 v1.2.0）——最低 Python ≥3.11，`Self` / `NotRequired` 等均在标准库内 |
| 最低 Python 版本 **3.11**（CI 矩阵最低档、隔离验收环境档位） | B3F1 / B24F1 | 运行时环境（D-21 · 宪法 v1.2.0） |
| API 兼容矩阵与免责声明 | B24F1 | 文档合规（原则 X） |
| `THIRD_PARTY_NOTICES` 首次创建 | 首次引入第三方代码时 | 本 feature 无新增第三方代码 |
