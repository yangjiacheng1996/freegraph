# 功能块 Specification: B5F1 · Channel 抽象 + `LastValue` + `BinaryOperatorAggregate` + `EphemeralValue`

**Feature Branch**: `b5f1-channels`（**未创建分支** —— 本仓库无 `.specify/extensions.yml`
⇒ 无 `before_specify` 钩子；既有 5 个 feature（B1F1 / B2F1 / B2F2 / B3F1 / B4F1）同样在 `main` 上开发）

**Created**: 2026-11-08

**Status**: Draft

**Input**: User description: "B5F1 · Channel 抽象 + `LastValue` + `BinaryOperatorAggregate` + `EphemeralValue`"
—— 完整提示词正文见 `harness/features/B5F1_Channel抽象与三类通道.md`。要点：交付 freegraph 的**通道抽象**
与三类通道实现 —— **无归约器 → 覆盖**（`LastValue`）、**有归约器 → 归约**（`BinaryOperatorAggregate`）、
**每 super-step 清空**（`EphemeralValue`，供路由通道使用）；通道是状态的**唯一读写单元**，
让「覆盖 vs 归约」这条语义只有**一个**实现点。本 feature **只交付通道层**：
稀疏状态读取属 **B5F2**，调度循环属 **B7F1**，`StateGraph` 构建器属 **B6F1**。

---

## 澄清与裁定

> 本节记录本 feature 的**裁定**（提示词未逐字规定、或与仓库既有冻结面 / 上游行为存在张力处的取舍）。
> 全部裁定均已闭合，正文**无未闭合的澄清标记残留**。

### Session 2026-11-08

> 本节含**四轮澄清**：**第一轮 Q1–Q3**（初稿阶段）· **第二轮 Q4–Q8**（`/speckit.clarify` 第一轮）·
> **第三轮 Q9–Q13**（`/speckit.clarify` 第二轮）· **第四轮 Q14–Q15**（`/speckit.analyze` 阶段 ·
> 裁定 15 / 16）· 每条含**背景 / 候选项 / 选定项 / 理由 / 落点**。
> **📌 轮次记法**：每条问答的括注标的是「**该轮澄清在本 feature 内的序号**」（Q4–Q8 = 第二轮、
> Q9–Q13 = 第三轮）⇒ 与上方总表的「澄清轮次」一一对应（裁定 17 为本轮 `/speckit.analyze` 补充）。

- **Q1（通道的「写入」接口形态 · 同一步内多值写入怎么办）** → **A（镜像上游：批量写入 + 冲突显式报错）** ——
  通道的写入操作接收「**本步的写入序列**」；`LastValue` / `EphemeralValue` 在**一次写入调用**中收到多于一个值时
  **显式失败**（抛 `InvalidChannelUpdateError`）；`BinaryOperatorAggregate` 把序列**逐个归约**。
  **候选**：A 批量 + 冲突报错（选定）· B 批量 + 静默取末值 · C 单值写入 + 冲突判定归 B7F1。
  **理由**：① 提示词 §2 与宪法原则 II 都要求「状态语义 MUST 与 LangGraph 行为等价」，而上游
  `LastValue.update` 在一步内多值时**显式报错**（`langgraph/channels/last_value.py:56-67`）——
  A 是**唯一**与上游同构的选项；② 提示词 §1 的核心价值是「**收敛**」——若一步内多值冲突的判定被推给
  调度层（C），则「写入语义」重新散落到两处，收敛目标落空；③ B 的「静默取末值」会让
  「两个节点同时写同一个 key」这一**用户错误**被静默吞掉 —— 与本仓库「非法输入 MUST 显式失败」的既有
  立场一致（B4F1 裁定 1：「抛错，绝不静默降级」）；④ 代价（新增 1 个 L2 错误类型 + 冲突用例）可控，
  且错误类型落在 L2 ⇒ 公开面零变更（与 B4F1 裁定 2 同构）。
  **落点**：FR-001 · FR-002 · FR-004 · FR-010 · FR-017 · 裁定 1 · 裁定 2 · SC-006 · Edge Cases。

- **Q2（`BinaryOperatorAggregate` 的「空值」与首次写入语义）** → **A（上游等价：按类型推导空值）** ——
  构造时按通道的**值类型**推导「空值」（可实例化 ⇒ 初始即「有值」且值为空值；不可实例化 ⇒ 初始「无值」）；
  首次写入：通道**有值** ⇒ `reducer(空值, new)`；通道**无值** ⇒ **直存 `new`、不调归约器**。
  **候选**：A 上游等价（选定）· B 首次一律直存 · C 首次一律以空值参与归约（推导失败则报错）。
  **理由**：① 提示词 §10 把这条列为**首要风险**（「首次写入时 `current` 取什么」选错 ⇒ `operator.add` 的结果
  与上游差一个前缀元素）⇒ 必须逐字对齐上游，容不得「差不多」；② 上游是**两个分支**
  （`langgraph/channels/binop.py:89-92` 的空值推导 + `:126-128` 的「无值 ⇒ 首值直存」），
  任何「统一成一种」的简化（B / C）都会在某一类类型上与上游不等价；③ 证据侧的硬要求：
  Q8 契约 C4 行的实测证据是「`NODE_INPUT_KEYS: ['messages']`」——
  `messages`（BinOp · `operator.add`）**从一开始就出现在节点入参里**（值为空列表），
  而 `llm_calls`（LastValue）**不出现** ⇒ 这条实测直接锁定「BinOp 通道自始有值」的口径
  （B / C 两种口径都会让 `messages` 缺席 ⇒ 与上游实测矛盾）。
  **落点**：FR-005 · FR-006 · FR-007 · FR-008 · 裁定 3 · 裁定 4 · SC-002 · SC-007 · Edge Cases。

- **Q3（「有值 / 无值」的可判定区分用什么形态表达）** → **A（布尔判定 + 读取抛错）** ——
  通道提供布尔型「有无值」判定；读取在无值时抛**显式错误**（`EmptyChannelError`）；
  「值为 `None`」与「无值」**严格可区分**。
  **候选**：A 判定 + 抛错（选定）· B 读取带默认值参数 · C 读取返回专有哨兵对象。
  **理由**：① 上游是「`is_available()` + `get()` 抛 `EmptyChannelError`」
  （`langgraph/channels/last_value.py:69-75`；`langgraph/pregel/_io.py:38-53` 的
  `read_channels` 正是靠捕获 `EmptyChannelError` 来实现 C4 的稀疏入参）⇒ A 与上游同构，
  B5F2 直接照搬该读取口径即可；② 提示词 SC-003 明写「**不是 `None` 冒充有值**」⇒ B 与 C 都要求调用方
  额外区分「默认值恰好是 `None`」的情形，A 用**两个正交信号**（判定 + 抛错）把这件事彻底消歧；
  ③ B5F2 的读取层（「读到无值的 key 时返回什么」）是**读取层**的责任（提示词 §7 口径提醒），
  本 feature 只负责「如实表达有值 / 无值」⇒ A 恰好停在这条边界上。
  **落点**：FR-011 · FR-017 · 裁定 5 · SC-003 · SC-004 · Edge Cases。

### 裁定（17 条 · 与提示词 / 上游 / 仓库既有冻结面之间的取舍）

- **裁定 1（通道抽象 = 一个抽象基类 + 三类操作 · 名字逐字冻结）**：
  通道抽象 MUST 提供**四**个操作（**三类语义**：写入 / 读取 / 清空 + 一个判定）：
  `update(values)` / `get()` / `is_available()` / `clear()`（详见 FR-002）。
  三类通道 MUST 承自该抽象，MUST NOT 另立读写路径 —— 这是提示词 §1「收敛」的**唯一实现点**。
  抽象基类的**类名**冻结为 `Channel`（freegraph 命名风格：不加 `Base` 前缀 · 与 B4F1 的
  `ChannelSpec` / `SchemaSpec` 同族）；三个实现类名沿用提示词字面：`LastValue` /
  `BinaryOperatorAggregate` / `EphemeralValue`。
  **理由**：① 名字是**跨 feature 契约**（B5F2 读取层 / B7F1 调度层 / B8F1 路由层都要 import）⇒
  逐字冻结，避免三个 feature 各写各的；② 仓库既有先例支持（B1F1 四个核心类型 / B2F1 五个协议与五个
  纯数据类 / B4F1 六个字段名 **全部逐字冻结**）。
  **落点**：FR-001 · FR-002 · Key Entities「通道（抽象）」。

- **裁定 2（一步内多值冲突 = 显式失败 · 新增 `InvalidChannelUpdateError`）**：
  `LastValue` / `EphemeralValue` 在**一次** `update` 调用中收到多于一个值时 MUST 抛
  `InvalidChannelUpdateError`（继承 `FreegraphError` **且**继承 `ValueError` · 落在 L2）。
  `BinaryOperatorAggregate` 不冲突 —— 它把序列**逐个归约**。
  **上游对照**：`last_value.py:56-67`（`LastValue`）· `ephemeral_value.py:62-65`（`EphemeralValue` 的 guard）
  · `binop.py:123-144`（`BinaryOperatorAggregate` 逐个归约）。
  **落点**：FR-004 · FR-010 · FR-017 · SC-006。

- **裁定 3（BinOp 的空值推导 = 按类型推导 · 不可实例化 ⇒ 初始无值）**：
  空值推导 MUST 走「剥离 typing 包装 → 抽象容器映射到具体类型 → 尝试构造空实例」三步；
  **构造失败 MUST NOT 让通道构造失败**，而是让该通道**初始为「无值」**。
  **上游对照**：`binop.py:82-92`（`Sequence/MutableSequence → list` · `Set/MutableSet → set` ·
  `Mapping/MutableMapping → dict` · `try: self.value = typ() except Exception: self.value = MISSING`）。
  **落点**：FR-006 · SC-007。

- **裁定 4（BinOp 首次写入的 `current` = 分支口径 · 上游 `binop.py:126-128`）**：
  ① 通道**有值**（含初始空值）⇒ `current` = 通道当前值，保存 `reducer(current, new)`；
  ② 通道**无值** ⇒ **直存 `new`**，MUST NOT 调用归约器（**单值**写入时归约器调用次数 == **0**）。
  **这是提示词 §10 风险点的正面回答**：freegraph MUST 与上游**逐条同构**，MUST NOT 自造「统一语义」。
  **落点**：FR-007 · SC-002 · SC-007。

- **裁定 5（「有值 / 无值」= 判定 + 抛错两个正交信号）**：
  `is_available()` 恒不抛错；`get()` 在无值时抛 `EmptyChannelError`；
  **写入 `None` 后 `is_available()` MUST 为真**（「值为 `None`」≠「无值」）。
  **上游对照**：`last_value.py:69-75` · `binop.py:146-152` · `ephemeral_value.py:70-76` ·
  `langgraph/checkpoint/base/__init__.py:745-749`（`EmptyChannelError` 定义）·
  `langgraph/pregel/_io.py:38-53`（C4 稀疏入参靠捕获该错误实现）。
  **落点**：FR-011 · FR-017 · SC-003 · SC-004。

- **裁定 6（清空 = 显式 `clear()` 操作；`update([])` 对三类通道一律是无操作）**：
  通道抽象的「清空」是一个**独立操作** `clear()`（默认实现 = 无操作、返回 `False`），
  **三类通道全部覆写**它（清空 ⇒ 「无值」· FR-009 · **裁定 17 ①** 收敛）。
  **与上游的机制差异（登记）**：上游靠「对本步未更新的通道调用 `update(EMPTY_SEQ)`」
  （`langgraph/pregel/_algo.py:326-334`）来让 `EphemeralValue` 在步末清空（`ephemeral_value.py:55-60`）；
  freegraph 改为**显式 `clear()`**（由调度层在步末调用）。
  **可观察语义等价**（值同样不跨步残留），但**机制不同** ⇒ 登记为差异项，不进兼容矩阵新增行
  （本 feature 零新增公开 API）。
  **落点**：FR-009 · FR-002 · 引文差异说明 ③ · **裁定 17 ① ②**（本轮分析轮补充：三类通道对
  `update([])` 的上游反应**各不相同** ⇒ 等价落点是「步末调用哪些通道」）。

- **裁定 7（错误类型落 L2 · 捕获走基类 · 结构化字段 · 不进公开面）**：
  `EmptyChannelError`（继承 `FreegraphError`）与 `InvalidChannelUpdateError`
  （继承 `FreegraphError` **且** `ValueError`）MUST 定义在 **L2**（`src/freegraph/runtime/`），
  MUST NOT 进入契约层 18 符号面 / 门面 7 符号面 ⇒ **公开面零变更**；
  用户侧 `except FreegraphError` MUST 捕获到二者；需要读结构化字段的上层 MAY 从
  `freegraph.runtime` import 具体子类（**L2 子包** · 与 B4F1 裁定 14 同一口径）。
  **落点**：FR-017 · SC-018 · Assumptions「冻结面零改动」。

- **裁定 8（schema → 通道的映射规则）**：
  ① 通道规格标注「有归约器」⇒ `BinaryOperatorAggregate`（归约器 = 规格里的**同一引用** · 身份判定）；
  ② 通道规格标注「无归约器」⇒ `LastValue`；
  ③ **路由通道 ⇒ `EphemeralValue`，但 MUST NOT 由 schema 推导** —— 路由通道**不是 schema key**
  （它承载的是「条件边的判定结果」· C7 / C8）⇒ MUST 支持**显式请求**创建；
  ④ 映射 MUST **保序**（按 schema 的 key 顺序），每个 key 恰产出一个通道。
  **上游对照**：`langgraph/graph/state.py:1850-1873`（`_get_channel`：先剥 `Required`/`NotRequired`
  → 有归约器走 `_is_field_binop` → 否则 `LastValue` 兜底 `:1871-1873`）。
  **落点**：FR-012 · SC-008。

- **裁定 9（通道只持纯数据 + 归约器引用）**：
  通道 MUST 只持有：**schema key** / **值类型** / **当前值** / **归约器引用**。
  MUST NOT 持有或感知：节点、图结构、运行配置、调度信息、时钟、文件句柄、连接、协程、锁。
  **落点**：FR-013 · SC-009。

- **裁定 10（归约器按引用持有）**：
  归约器 MUST 按引用持有（MUST NOT 包装 / 复制 / 部分应用）⇒ `channel.reducer is operator.add` MUST 成立。
  **落点**：FR-014 · SC-010。

- **裁定 11（依赖与 I/O 纪律 · 零副作用）**：
  只依赖**标准库**；MUST NOT import `langchain` / `langchain-core` / `langgraph*` / `langsmith` /
  `pydantic` / `typing_extensions`；MUST NOT 读环境变量；零出站、零文件 I/O；
  导入本模块 MUST NOT 产生 import 副作用（`sys.modules` 增量中非标准库条目数 == 0）。
  **落点**：FR-015 · SC-005。

- **裁定 12（层纪律 · ARCH-1 / ARCH-3）**：
  新增代码 MUST 落在**已登记**的 L2 路径（`src/freegraph/runtime/` · 层注册表已登记）⇒
  层注册表**零改动**；L2 MUST 只向下依赖 L1（`freegraph.contracts`），MUST NOT import L3 / L4 / L5。
  **落点**：FR-016 · SC-011。

- **裁定 13（不越界）**：
  本 feature MUST NOT 实现：稀疏状态读取（B5F2）· 调度循环 / super-step（B7F1）·
  `StateGraph` 构建器（B6F1）· checkpoint 写入与通道复制（B14F1）· `Topic` / `Barrier` 等通道类型 ·
  `add_messages` 等 LangChain 特有归约器（freechain 层）· `Overwrite` 旁路值。
  **落点**：FR-018 · Out of Scope。

- **裁定 14（纯单元可测 ⇒ 覆盖率与负向用例要求最高 · 人工门禁 + 证据门禁）**：
  本 feature **没有图可跑** ⇒ 判据 MUST 全部以单元测试落地，且覆盖率取证 MUST 达 100%（行 + 分支），
  取证 MUST 在**开发期**完成并记入人工验证记录（v1.0 依赖面为零 ⇒ MUST NOT 把覆盖率工具写进仓库依赖声明）；
  人工验证记录 MUST 落 `harness/verification/B5F1/manual-verification.md`（**五段式**），
  并含**来源覆盖表**（每条判据标注上游 `路径:行号` + 核实版本 / 澄清条号 / 宪法条款号）。
  **落点**：FR-019 · FR-020 · FR-021 · SC-013 · SC-014 · SC-015。

- **Q4（`/speckit.clarify` 第二轮 · 下游可依赖的契约冻结范围）** → **A（全冻结）** ——
  **问题**：下游的 **B5F2**（稀疏读取）· **B7F1**（调度循环）· **B8F1**（路由）三个 feature 都要直接使用
  通道类；构造签名、属性名、schema→通道的映射入口函数名，要不要现在**逐字冻结**成跨 feature 契约？
  **候选**：A 全冻结（选定）· B 只冻结四个操作（构造 / 属性 / 入口名留给 plan）·
  C 冻结构造与属性、入口名留给 plan。
  **理由**：① 这三个下游 feature **都还没开工** ⇒ 现在冻结的返工成本最低，等它们各写完再统一
  就要改三处；② 与仓库既有惯例一致（B1F1 四个核心类型 / B2F1 五个协议与五个纯数据类 /
  B4F1 六个字段名 **全部逐字冻结**）；③ 冻结发生在 **L2 内部 API** 内
  （`freegraph.runtime`）⇒ **不触碰**契约层 18 符号面与门面 7 符号面，公开面仍零变更。
  **落点**：FR-002（新增「构造签名与属性名」冻结表）· FR-012（新增「映射入口」冻结）·
  Key Entities「通道（抽象）」· **新增 SC-019** · 追溯表 FR-002 / FR-012 行。

- **Q5（`/speckit.clarify` 第二轮 · `update()` 的返回值语义）** → **A（本次写了值即真）** ——
  **问题**：写入操作 `update()` 的布尔返回值，应该表示「本次调用写了值」还是「通道的值真的变了」？
  **候选**：A 本次写了值即真（选定）· B 值真的变了才算真 · C 不返回布尔、只返回 `None`。
  **理由**：① 上游同一信号的语义是「**这次有写入**」（`last_value.py:67` · `binop.py:144` ·
  `ephemeral_value.py:68`），而上游调度层用它判断「本步通道是否被更新、要不要触发下游任务」
  （`pregel/_algo.py:319-324`）⇒ **与上游逐字同构**是唯一安全解；
  ② B 会让「写了但值相同」的通道**不触发下游任务**（静默调度差异），
  C 则把这个现成信号丢掉、把差异点留给 B7F1 自己再造一个。
  **落点**：FR-002（`update` 行返回值口径 + 📌 口径说明块）· **新增 SC-020** · 追溯表 FR-002 行。

- **Q6（`/speckit.clarify` 第二轮 · A1 的折叠基准起点）** → **A（从通道初始值（空值）起折）** ——
  **问题**：验收判据 A1 里「逐次归约」的折叠起点，应从**通道初始值（空值）**起，还是从**第一个写入值**起？
  **候选**：A 从初始值起折（选定）· B 从首值起折 · C 两条基准都要求成立。
  **理由**：① 上游的真实语义是 `operator(current, new)`，而 `current` = **写入前的通道值**
  （首次即空值）⇒ A 与上游 `binop.py:143` **逐字同构**，是唯一不会让判据本身失真的写法；
  ② 在 `operator.add` + 列表这个例子里 A 与 B **结果相同**（元素相同）⇒ 提示词 A1 的字面表述
  与 A **不冲突**；③ B 会在 `max` / `mul` 这类归约器上与上游分叉；④ C 把「哪些归约器与空值折叠等价」
  变成一道新的判断题，反而制造歧义。
  **落点**：SC-002（📌 折叠起点说明）· **新增 SC-021** · 追溯表 FR-005 行。

- **Q7（`/speckit.clarify` 第二轮 · 写入冲突错误的结构化字段）** → **A（key + received_count + expected_count）** ——
  **问题**：`InvalidChannelUpdateError` 的结构化字段该带哪些？
  **候选**：A `key` + `received_count` + `expected_count`（选定）· B 只带 `key` · C 再额外带上收到的值。
  **理由**：① B4F1 已踩过「字段太少 ⇒ 上层只能解析消息文本」的坑（消息措辞会变成事实上的 API 契约），
  故 MUST 把字段清单**逐字冻结**；② A 的三个字段恰好够上层分支处理，
  且 `expected_count`（恒为 1）让「一步只能写一个值」这条规则在错误里**自解释**；
  ③ C 会把用户数据卷进错误对象（可能含敏感内容）⇒ 明确排除；
  ④ 顺带把「继承关系」写死：`EmptyChannelError` **只**继承 `FreegraphError`
  （「读到无值」是正常信号，不应是 `ValueError`；上游亦只继承 `Exception`），
  `InvalidChannelUpdateError` 继承 `FreegraphError` **且** `ValueError`（与 B4F1 同款）。
  **落点**：FR-017（结构化字段表 + 继承关系写死）· SC-018（收紧）· 追溯表 FR-017 行。

- **Q8（`/speckit.clarify` 第二轮 · 规模 / 性能口径）** → **A（补可判定的规模口径）** ——
  **问题**：要不要给通道补一条「规模 / 性能口径」（禁止随 schema key 数线性劣化）？
  **候选**：A 补可判定的规模口径（选定）· B 不补 · C 只写定性描述。
  **理由**：① 下游 **B7F1** 的调度循环会对**每个通道**做写入与读取 ⇒ 通道一旦不小心扫整张状态表，
  性能会随 key 数线性劣化，而这种劣化在「key 少」的测试里**看不出来**；
  ② 判据 MUST 用**计数探针**（触及次数）而不是**墙钟耗时**（CI 机器快慢差异 ⇒ 假红）——
  这与仓库既有「零出站断言用 socket 监测夹具」的取样思路一致；
  ③ 结构性口径（MUST NOT 持有其它通道 / 状态表引用）比时间口径更稳：它让「遍历全体 key」
  在**结构上不可能**，而不是靠测出来；
  ④ C 的「常数级」在无人给判据时会退化成各人各解 ⇒ 不采用。
  **落点**：FR-013（新增 ②③ 规模口径 · 裁定 17 ③ 补白名单判据）· **新增 SC-022** · 追溯表 FR-013 行。

- **Q9（`/speckit.clarify` 第三轮 · 三类通道的初始状态）** → **A（按类型分三档写死）** ——
  **问题**：三类通道的初始状态（「从没写过」时算「有值」还是「无值」）统一怎么定？
  **候选**：A 按类型分三档（选定）· B 所有通道初始一律「无值」· C 所有通道初始一律「有值」。
  **理由**：① **本条同时收敛一处现存的口径冲突** —— SC-004 原写「从未写入 ⇒ 无值」，
  而 FR-006 写「归约型通道自始有值（空值）」，二者对归约型通道**互相矛盾** ⇒ 必须定一个；
  ② A 与上游**逐字同构**，并保留上一轮 Q2 的裁定与那条实测证据（Q8 契约 C4 行：
  「`NODE_INPUT_KEYS: ['messages']`」⇒ 归约型 key **自始**在节点入参里）；
  ③ B 会推翻 Q2 且改变 C4 的入参形状；C 会推翻 C3 的覆盖语义起点，且让「从未写过的 key」
  也进节点入参 ⇒ C4 失守。
  **附带定论**：`clear()` 的终态一律是「**无值**」（归约型通道清空后**不**回到初始空值）；
  v1.0 **不提供**「恢复到初始状态」的操作 —— 将来 checkpoint 回滚（**B14F1**）若需要，
  再另立**独立**操作，MUST NOT 复用 `clear()`。
  **落点**：**新增 FR-022** · SC-004（口径修正 + ③ 清空终态）· **新增 SC-023** ·
  Edge Cases +1 条（归约型通道被清空）· 追溯表 FR-011 / FR-022 行 + 反向覆盖注记。

- **Q10（`/speckit.clarify` 第三轮 · 谁能写通道 / 要不要线程安全）** → **A（只允许调度层写 · 不承诺线程安全）** ——
  **问题**：通道对象谁能写？以及要不要承诺线程安全？
  **候选**：A 只允许调度层写 + 不承诺线程安全（选定）· B 要求线程安全 · C 不写这条边界。
  **理由**：① 提示词 §1 的立意是「状态的写入**只有一条路径**」——若用户能直接抓通道来写，
  就等于**绕过**了「覆盖 / 归约 / 冲突判定」这唯一一处实现，提示词想消除的那类静默破坏
  会从后门回来 ⇒ 这条边界正是本 feature 该收敛的东西；
  ② v1 的写入只发生在**单线程**调度循环里（B7F1），加锁属**提前优化**，且会让
  「通道只能被单线程用」这条事实蒙上歧义；
  ③ 「不写」等于默认允许 ⇒ C 不采用。
  **附带定论**：通道 MUST **NOT** 引入任何同步原语（与「只持纯数据」一致）；
  通道 MUST **NOT** 出现在契约层 / 门面符号面 ⇒ 「用户直接写通道」在公开面上**不可达**。
  **落点**：**新增 FR-023** · **新增 SC-024** · Edge Cases +2 条 · 追溯表 FR-023 行。

- **Q11（`/speckit.clarify` 第三轮 · 通道存值时复制不复制）** → **A（浅引用 · 不复制）** ——
  **问题**：通道存用户写入的值时，是直接存原对象，还是复制一份？
  **候选**：A 浅引用不复制（选定）· B 容器类做浅拷贝 · C 深拷贝。
  **理由**：① 上游是**直接存原对象**（`last_value.py:66` 的 `self.value = values[-1]`；
  `binop.py:143` 存的是**归约器的返回值**）⇒ A 是与上游同构的唯一解；
  ② B / C 会让「节点返回的对象就是状态里的对象」这条直觉失效，且 C 引入
  「对象不可拷贝 ⇒ 写入失败」这种上游没有的失败模式；
  ③ A 的副作用（用户就地修改会反映到通道持有的值上）是 **Python 的常规引用语义**、
  **不是缺陷** ⇒ 写进 spec 说明即可，MUST NOT 由通道「修正」。
  **落点**：**新增 FR-024** · **新增 SC-025** · Edge Cases +2 条 · 追溯表 FR-024 行。

- **Q12（`/speckit.clarify` 第三轮 · 构造期的防御性校验）** → **A（构造期失败 · 用内置异常）** ——
  **问题**：通道构造时参数不合法（如归约器不可调用），要当场报错吗？用什么错？
  **候选**：A 构造期失败 + 内置 `TypeError` / `ValueError`（选定）· B 新增第三个 L2 错误类型 ·
  C 不校验。
  **理由**：① 上一轮冻结了构造签名 ⇒ 通道可被**直接实例化**，这条路径必须有人管；
  「非法输入 MUST 显式失败」是本仓库既有立场（B4F1 裁定 1）⇒ C 不采用；
  ② 这是「**调用方用错了 API**」的编程错误，不是运行期状态问题 ⇒ 用内置异常恰当；
  为它开一个内核错误类型会**扩大公开面**且要同步异常族文档与门禁快照 ⇒ B 不采用；
  ③ `InvalidChannelUpdateError` 的语义**只**覆盖「写入冲突」，复用会污染它 ⇒ 明确禁止复用；
  ④ 顺带定论：通道层 MUST **NOT** 重做**二元性校验**（B4F1 已做）——
  重复校验就是**第二个判定点**，违背「收敛」。
  **落点**：**新增 FR-025** · **新增 SC-026** · Edge Cases +2 条 · 追溯表 FR-025 行。

- **Q13（`/speckit.clarify` 第三轮 · 独立验收脚本）** → **A（补落 `acceptance.py`）** ——
  **问题**：要不要给本 feature 补一份独立验收脚本 `harness/verification/B5F1/acceptance.py`
  （一条命令跑完全部验收判据）？
  **候选**：A 补落（选定）· B 不落（只交 pytest + 人工记录）。
  **理由**：① `harness/verification/README.md` 标注该脚本**可选**，但同时明确记着
  **B4F1 当初被判为「不落」，是发起者要求「一条命令跑完全部验收」之后才补上的**——
  本 feature 的判据形态（纯计算 · 无图可跑 · 零第三方依赖）与 B4F1 **完全同款** ⇒ 应同样补落；
  ② 评审者不必自己拼 pytest 命令；
  ③ 该脚本**不替代** pytest 断言与门禁脚本（后者是机器门禁，前者是面向人的同口径对照）。
  **落点**：**新增 FR-026** · **新增 SC-027** · 追溯表 FR-026 行（判据 A1–A3）。

- **Q14（`/speckit.analyze` 轮 · 覆盖率判据的**范围**）** → **A（只管本 feature 新增代码）** ——
  **问题**：SC-015 的「行 / 分支覆盖 100%」到底管多大范围？
  **候选**：A 只管本 feature 新增/修改的代码（选定）· B 整个 `runtime/` 包必须 100% ·
  C 先给 B4F1 补基线再谈本 feature。
  **理由**：① **实测事实**：B4F1 **从未设过**行/分支覆盖判据、**无 100% 基线**
  （grep 其 spec / tasks 无「行覆盖」）⇒ 按 B 的口径，B5F1 会被前一个 feature 的历史债**阻断**；
  ② 「本 feature 交付到位没有」本就该只看**本 feature 的代码**；
  ③ C 会让本 feature 的判据在基线出来前**悬空** ⇒ 不采用。
  **落点**：SC-015（判据收窄 + 📌 口径边界）· FR-019 ②（同步）· `tasks.md` T036（取证命令两个数字）。

- **Q15（`/speckit.analyze` 轮 · 「持有」的判定口径 + 规模探针 + 参数化证据）** → **A（口径写死 + 探针写死 + 纳入参数化测试）** ——
  **问题（三处）**：① FR-013 / SC-009 的「通道实例**持有**的属性 ⊆ {4 项}」在实现用 `__slots__` 私有槽时**不可判定**
  （`vars()` 不存在、`dir()` 含方法与继承属性）；② SC-022 的「触及的状态条目数」**没给探针**；
  ③ 立项书 **S5 ③**「属性 / 参数化测试：枚举 reducer 类型 × 通道组合」**无承接方**。
  **候选**：① A 两个信号（公开 property 集合 + 实例槽位集合）· B 只写公开属性 · C 只写槽位；
  ② A 探针 = `len(gc.get_referents(channel))`（选定）· B 计时 · C 数行；
  ③ A 纳入 B5F1（选定）· B 登记到 B5F2/B8F1 · C 轻量抽样。
  **理由**：① 三个候选里只有 A 能**同时**表达「对外可见的 4 个属性」与「物理上只牵住 4 个槽位」
  （research D-02 的实现形态已定 `__slots__`）⇒ 断言写法唯一；
  ② 计时在 CI 上**假红**、数行**耦合实现细节** ⇒ 只有结构探针既稳又可判定（research D-12 已实测
  N=1/100/1000 恒定）；③ B5F1 是「通道 × 归约器」的**唯一落点** ⇒ S5 第三层证据 MUST 落在此；
  B 的「登记到 B5F2/B8F1」不成立（那两个 feature 的**差分夹具**是「同一张图跑两个框架」，
  **不等于**「枚举 reducer × 通道的组合」）。
  **落点**：FR-013 ① · SC-009 · SC-022 ③（探针逐字冻结）· FR-002 表（「属性 · `value`」的无值行为 +
  「抽象基类构造」行的不可实例化注）· SC-005（写死导入 `freegraph.runtime`）·
  **新增 FR-027 / SC-028**（参数化组合测试）· `tasks.md` T031（新增任务）· research **D-16**。
  > **📌 本轮分析轮的补充（裁定 17）**：① ② 的口径**已按裁定 17 收紧** ——
  > ① 追加「子类 MUST NOT 引入新槽」（否则 `__dict__` 破防）+ MRO 收集 `property` 的写法；
  > ② 追加**引用类型白名单**为主判据（计数探针**降为辅助** —— 实测其对「持有状态表」不敏感）；
  > ③ 的落点不变。

- **裁定 15（覆盖率判据的范围 = 只管本 feature 新增/修改的代码）**：
  SC-015 / FR-019 ② 的「行 / 分支覆盖 == 100%」MUST 写死为「**本 feature 新增/修改的代码**」
  （`channel.py` / `mapping.py` 全文 + `errors.py` / `__init__.py` 的**新增部分**）；
  `src/freegraph/runtime/` **整包**的覆盖率 MUST **一并记录**、但 MUST **NOT** 作为**阻断判据**。
  **依据**：① **实测事实** —— B4F1 **从未设过**行/分支覆盖判据、**无 100% 基线**
  （其 spec / tasks 无「行覆盖」字样）⇒ 若按整包判，B5F1 会被**前一个 feature 的历史债阻断**；
  ② 「本 feature 交付到位没有」本就该只看**本 feature 的代码**；
  ③ 澄清轮 **Q14** 的选定项（候选 A）。
  **落点**：SC-015（判据 + 📌 口径边界）· FR-019 ② · plan Constraints 表 · tasks **T036** ·
  quickstart §8 ③。

- **裁定 16（「持有」的口径写死 + 规模探针写死 + 立项书 S5 ③ 的落点 = 本 feature）**：
  ① **「持有」**（FR-013 / SC-009）MUST 写死为**两个**信号 —— **公开**属性（4 个 `property`）集合
  **恰为** {`key`, `value_type`, `value`, `reducer`} **且** **实例槽位**集合
  ⊆ {`_key`, `_value_type`, `_value`, `_reducer`}（实现用 `__slots__` ⇒ `vars()` 不存在、
  `dir()` 含方法与继承属性 ⇒ 二者**均不可**作判据）；
  ② **规模探针**（SC-022 ③）MUST **逐字冻结** = `len(gc.get_referents(channel))`
  （MUST **NOT** 用墙钟耗时 —— CI 假红；MUST **NOT** 数「执行了多少行」—— 耦合实现细节）；
  ③ 立项书 §4.2 **S5**「语义等价」的**第三层证据**（「属性 / 参数化测试：枚举 reducer 类型 × 通道组合」）
  **纳入本 feature** ⇒ 新增 **FR-027 / SC-028**（组合数 ≥ 12 · **MUST NOT** 用 `skip` / `xfail` 掩盖）。
  **依据**：① ①② 均为**可判定性**的补齐（其余 SC 都给了具体口径，唯独这两条没有）；
  ③ S5 第三层证据此前**无承接方**（其落点说明只把**差分夹具**指给 B5F2 / B8F1，而差分夹具是
  「同一张图跑两个框架」≠「枚举 reducer × 通道的组合」），而 B5F1 是「**通道 × 归约器**」的
  **唯一落点** ⇒ MUST 落在此；澄清轮 **Q15** 的选定项。
  **落点**：FR-013 ① · SC-009 · SC-022 ③ · **FR-027 / SC-028** · contracts I-1 / I-2 ·
  data-model I-1 / I-2 · tasks **T029 / T031** · research **D-16** · plan Constraints 表。

- **裁定 17（清空语义 = 三类一律「无值」；上游等价落在「步末调用哪些通道」· 本轮分析轮补）**：
  ① **清空语义统一**：三类通道的 `clear()` MUST **一律**把通道清到「无值」（FR-009 · FR-022 ③ ·
  SC-004 ③ · SC-023 ④ · contracts I-12）—— **覆盖型 MUST 覆写** `clear()`（此前 contract §3.1 写
  「无操作 ⇒ 值不变」，与 spec 的四处「清空后一律为无值」**互斥**，本裁定以 **spec 为上位文档**回修之）；
  ② **上游逐类实测**（research D-17）：上游**没有** `clear()`（`channels/base.py` 的 `BaseChannel`
  无该方法）⇒ 三类通道的「清空」在 freegraph 是**新增的显式操作**；上游的步末重置靠
  `update(EMPTY_SEQ)`（`pregel/_algo.py:326-334`），而**三类通道对 `update([])` 反应不同** ——
  `LastValue` no-op（`last_value.py:57-58`）· `BinOp` no-op（`binop.py:124-125`）·
  `EphemeralValue` 清空为 `MISSING`（`ephemeral_value.py:55-61`）；
  ⇒ **可观察语义等价的落点是「调度层在步末对哪些通道调用 `clear()`」**（**B7F1** 的职责）：
  步末 MUST **只**对**路由型**通道调用 `clear()`（覆盖型 / 归约型在步末**保留**其值，
  与上游 `update([])` 的 no-op 效果逐字同构）⇒ 落在 contract §7 `B-2` 与 `upstream-parity` 新增行；
  ③ **规模探针的补充判据**：SC-022 ① MUST 另以**引用类型白名单**判定（直接引用集合中 MUST NOT 出现
  `dict` / `SchemaSpec` / 其它 `Channel` 实例）—— 实测计数探针对「持有整张状态表」**不敏感**
  （N=1 与 N=1000 计数同为 6）⇒ 计数相等**降为辅助**判据；
  ④ **归约器调用次数 == 0** MUST 限定为**单值**写入（上游「无值 + 多值」时首个直存、其余仍归约 ·
  实测 `operator` 被调 1 次 · `binop.py:126-128` + `:143`）；
  ⑤ **分支覆盖 MUST 以 `--branch` 取证**（无 `--branch` 时 `coverage report` 不输出 Branch 列 ⇒
  分支覆盖无从判定）；「新增部分」MUST 以**差分口径**判定（`git diff -U0` 的新增行号 ∩
  `coverage json` 的 `executed_lines` / `executed_branches`）—— 文件级 report 无法区分既有行与新增行。
  **依据**：本轮 `/speckit.analyze` 的 20 项发现中，①②③④⑤ 均属**可判定性 / 上游等价**的补齐
  （与 Q8 / Q14 / Q15 同一性质）；**无**任何一条要求改变本 feature 的**交付面**或**语义方向**。
  **落点**：FR-002（默认实现的括注）· FR-006 ① · FR-007 ② · FR-009（重写为三类统一）· FR-012 ② ·
  FR-013 ① · FR-019 ② · SC-004 ③ · SC-007 · SC-022 ①② · SC-023 ④ · contracts §1 / §2.2 / §3.1 /
  §3.2 / §6（I-2 / I-12）/ §7（`B-2`）· upstream-parity **P-12 / S-05** · data-model §2.1 / §3.1 /
  §3.2 / §3.3 / §4（I-1 / I-2 / I-10 / I-12）· research **D-17** · tasks **T007 / T012 / T015 / T019 /
  T024 / T029 / T036** · plan Constraints 表 · quickstart §7 / §8 ③。

### 引文差异说明（与引文的逐条差异 · 供人工评审核对）

| # | 引文表述 | 本 spec 的口径 | 理由 |
|---|---|---|---|
| ① | FR-001「读取（get / read）」 | **冻结为 `get`** | 名字是跨 feature 契约（B5F2 / B7F1 / B8F1 都要 import）⇒ 只留一个（裁定 1） |
| ② | FR-003「首次写入时 `current` 取该通道的『空值』语义」 | **拆成两条分支**（可实例化 ⇒ `reducer(空值, new)`；不可实例化 ⇒ 直存 `new`） | 上游本就是两条分支（`binop.py:89-92` + `:126-128`）；「统一成一种」都会与上游不等价（Q2） |
| ③ | FR-004「每次 super-step 结束时被清空」 | **通道只提供显式 `clear()`**（三类一律 ⇒ 无值）；**步末调用哪些通道由调度层决定**（步末**只**清路由型） | 通道 MUST NOT 感知 super-step 边界（提示词 FR-006 的纪律）；上游用「`update(空序列)`」达成同一可观察效果（裁定 6 / 裁定 17 ②） |
| ④ | SC-003「不是 `None` 冒充有值」 | **「无值」= 判定为假 + 读取抛错**（两个正交信号） | 与上游同构；`None` 与「无值」严格可分（Q3 / 裁定 5） |
| ⑤ | §1「通道是状态的唯一读写单元」 | 本 feature 交付**通道层**；「唯一读写单元」在 **B7F1 调度落地**后成立 | 提示词 §8 边界：本 feature 无图可跑，调度属 B7F1 |
| ⑥ | §7「路由专用 → Ephemeral」 | 路由通道**不由 schema 推导**，MUST 支持**显式请求**创建 | 路由通道不是 schema key（C7 / C8 的判定结果是运行期产物）⇒ 裁定 8 ③ |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 计数型 key 每次被覆盖（Priority: P1）

作为用户，我的 schema 里有 `llm_calls: int`（**无归约器**）。我希望节点写 `llm_calls: 1` 之后，
下一个节点读到的是 `1` 而不是 `2`——以便 `llm_calls` 真的是「调用了几次」这个计数，
而不是一个越滚越大的累加总数。

**Why this priority**: 这是本 feature 的**小目标本体**（立项书 §5.2 的 B5F1 小目标：
「无归约器 key 被覆盖」）⇒ 不成立则整个 B5 功能块不成立。
且它是 `harness/demo/target.py:81`（`state.get('llm_calls', 0)`）能工作的前提之一。

**Independent Test**: 拿一个「无归约器」通道连续写入两个不同值（**两次独立的写入调用**），
断言读取结果是**后者**；再断言该通道**从未调用过任何归约器**。

**Acceptance Scenarios**:

1. **Given** 一个「无归约器」通道（值类型 `int`），**When** 写入 `1` 再写入 `2`，
   **Then** 读取结果 == `2`（**不是** `3`、不是 `1`）。
2. **Given** 同一通道，**When** 只写入 `1`，**Then** 读取结果 == `1`，
   且该通道的归约器**为空**（从未有过归约器被调用）。
3. **Given** 同一通道，**When** 在**一次**写入调用里给出两个值，
   **Then** MUST **显式失败**（抛出可捕获的通道更新错误），MUST NOT 静默取末值。
4. **Given** 同一通道，**When** 用**空**写入序列调用写入，**Then** 通道值**保持不变**，
   且该次写入**报告为「无变化」**。

---

### User Story 2 - 消息型 key 累积追加（Priority: P2）

作为用户，我的 schema 里有 `messages: Annotated[list, operator.add]`。我希望两个节点先后写入消息后，
读取结果是**拼接后的完整列表**——以便对话历史不会被后一次写入冲掉。

**Why this priority**: 这是本 feature 的**小目标本体**（立项书 §5.2 的 B5F1 小目标：
「归约器 `operator(current, new)` 语义一致」）⇒ 不成立则整个 B5 功能块不成立。
它同时是「有归约器 ⇒ 归约」这条契约（C2）的**唯一**载体。

**Independent Test**: 拿一个带 `operator.add` 归约器的通道写入两次，断言读取结果
**逐元素等于** `operator.add` 对同一序列的**逐次归约**结果。

**Acceptance Scenarios**:

1. **Given** 一个带 `operator.add` 归约器、值类型为 `list` 的通道，
   **When** 先写入 `[m1]` 再写入 `[m2]`，**Then** 读取结果 == `[m1, m2]`
   （**逐元素相等**，且**不含**任何多余的前缀元素）。
2. **Given** 同一通道，**When** 检查其归约器，**Then** 它**就是** `operator.add` **本身**
   （**身份**判定，不是相等判定）—— 任何包装 / 复制都会让本条失败。
3. **Given** 一个带归约器、值类型为 `int` 的通道，**When** 写入 `5` 再写入 `3`，
   **Then** 读取结果 == `8`（`reducer(5, 3)`）⇒ 归约**对累计值**同样成立，
   不是只对列表成立。
4. **Given** 一个带归约器的通道，**When** 归约器在归约过程中抛错，
   **Then** 该异常 MUST **向上传播**，且通道的值 MUST **保持不变**（失败不留半写状态）。

---

### User Story 3 - 路由结果不跨轮残留（Priority: P3）

作为实现者，我希望**路由通道**的判定结果在每个 super-step 结束后被清空，从而第二轮的路由
不受第一轮影响——以便「上一轮选了 A 分支」不会让「本轮本该选 B 分支」被历史污染。

**Why this priority**: 路由污染是**静默**的分支错误：图会走错分支，但没有任何报错。
它供 **B8F1**（条件边路由）使用 ⇒ 本 feature 只需交付「可清空的通道」这一件东西，
**清空时机**由调度层决定。

**Independent Test**: 往路由通道写一个值 ⇒ 触发清空 ⇒ 断言通道回到「无值」
（判定为假 + 读取抛错），且**不是**上一次的值、也**不是** `None` 冒充有值。

**Acceptance Scenarios**:

1. **Given** 一个路由通道，**When** 写入一个判定结果，**Then** 读取结果 == 该判定结果。
2. **Given** 同一通道，**When** 触发清空，**Then** 通道回到「**无值**」——
   「有值」判定为假，且读取**抛出**通道空错误（MUST NOT 返回上一次的值、MUST NOT 返回 `None`）。
3. **Given** 同一通道，**When** 清空**之后**再写入一个新值，**Then** 通道重新变为「有值」，
   且新值**就是**刚写入的那个（清空**不**留下残余状态）。
4. **Given** 同一通道，**When** 在**一次**写入调用里给出两个值，**Then** MUST **显式失败**
   （路由判定结果是单值的 ⇒ 两个值是用户错误）。

---

### User Story 4 - 状态语义只有一处实现点（Priority: P4）

作为实现者，我希望**所有**状态的写入、合并、读取都经由**同一个通道接口**，
以便「覆盖 vs 归约 vs 清空」这条语义**只有一处**实现——将来出问题时，
「归约器覆盖规则写错」这类静默破坏会被**限制在一个地方**，而不是散落在调度层、读取层、构建层。

**Why this priority**: 这是本 feature 的**架构收益**（提示词 §1「收敛」），也是 **B5F2 / B7F1 / B8F1**
能安全复用同一套语义的前提。放在 P4 是因为它**依附于** P1–P3 的三类实现：
抽象先立，三类实现再各自落位。

**Independent Test**: 写一个**只依赖通道抽象**的第三方通道实现（测试内自定义），
断言它能被同一个映射入口创建、被同一套读取 / 清空流程使用——证明抽象**真的**是可替换的实现单元。

**Acceptance Scenarios**:

1. **Given** 通道抽象的四个操作，**When** 用一个**自定义**子类实现它们，
   **Then** 该子类 MUST 能被创建、被写入、被读取、被清空，且**不需要**改动抽象或既有三类通道。
2. **Given** 任意通道实例，**When** 检查它持有的东西，**Then** 它 MUST **只**持有
   schema key、值类型、当前值、归约器引用——MUST NOT 持有节点、图结构、运行配置、时钟或句柄。
3. **Given** 一份 schema 的解析结果，**When** 按 schema key 映射到通道，
   **Then** 「有归约器」的 key ⇒ 归约型通道、「无归约器」的 key ⇒ 覆盖型通道、
   **每个 key 恰一个**通道、且映射顺序与 schema 的 key 顺序**一致**。
4. **Given** 任意通道，**When** 读取一个「无值」通道，**Then** MUST 抛**明确的通道空错误**
   （MUST NOT 静默返回 `None`）⇒ 读取方**永远**能区分「无值」与「值为 `None`」。

---

### Edge Cases

- **「无归约器」通道写入 `None`**：`None` 是**合法值** ⇒ 写入后通道「**有值**」，
  读取返回 `None`；这与「从未写入过的空通道」**严格可区分**（裁定 5 · SC-004）。
- **「无归约器」通道在一次写入调用里收到两个值**：MUST 抛 `InvalidChannelUpdateError`
  （**不**静默取末值）—— 两个节点在同一步写同一个 key 是**用户错误**，值得显式暴露（裁定 2）。
- **写入调用给出**空**序列**：一律**无操作**（返回「无变化」），通道值 MUST 保持不变。
  > **📌 机制差异登记**：上游对「本步无写入」的通道调用 `update(空序列)`
  > （`langgraph/pregel/_algo.py:326-334`）——freegraph 的 `update([])` 是**纯无操作**，
  > 清空一律走 `clear()`（裁定 6）。
- **归约型通道的值类型**不可实例化**（如 `typing.Any`、抽象类、联合类型）：
  通道**初始为「无值」**；**首次写入直存新值**（**单值**写入时归约器调用次数 == **0**）；
  第二次写入才进入归约（裁定 3 / 4）。
- **归约型通道的值类型**是抽象容器**（`collections.abc.Sequence` / `Set` / `Mapping` 及其可变版本）：
  MUST 先映射到具体类型再取空值（`Sequence → list` · `Set → set` · `Mapping → dict`）⇒
  空值分别为 `[]` / `set()` / `{}`（上游 `binop.py:83-88`）。
- **值类型带 typing 包装**（`Annotated[...]` / `Required[...]` / `NotRequired[...]`）：
  空值推导 MUST **先剥离**包装（上游 `_strip_extras` 口径 · `binop.py:22-28`）⇒
  `Required[list]` 的空值是 `[]` 而不是「无值」。
- **归约器抛错**：异常 MUST 向上传播；通道值 MUST **保持不变**（写入失败不留半写状态）。
- **归约器不是二元函数**（签名不符）：**通道不做校验** —— 二元性是 **B4F1 解析期**的责任
  （B4F1 FR-004 / FR-007 ②）⇒ 运行期只表现为调用时的 `TypeError`（向上传播）。
  > **📌 口径**：通道 MUST NOT 自造一套二元性校验（会形成第二处判定点，违背「收敛」）。
- **归约器返回值是 `None`**：通道值变为 `None`，但通道仍「**有值**」。
- **两个归约型通道的值类型相同**：各自的空值 MUST 是**独立实例**（两个 `list` 型通道 MUST NOT
  共享同一个空列表）⇒ 一个通道的归约 MUST NOT 污染另一个（FR-006 ④）。
- **归约器有状态**（闭包 / 可变默认参数）：按引用持有并**按序**调用；状态归用户负责，
  通道 MUST NOT 复制 / 重置归约器状态。
- **同一个归约器被两个 key 共用**：两条通道各自持有**同一引用**。
- **归约型通道被清空**：清空后 MUST 停在「**无值**」，**不回到**初始空值
  （v1.0 无「恢复到初始状态」的操作 —— FR-022 ③）；此后写入按 FR-007 的情形 ① 处理
  （此时通道**无值** ⇒ 首次写入**直存新值**（**单值**写入时归约器调用次数 == **0**））。
- **覆盖型通道被清空**：清空后 MUST 停在「**无值**」（FR-009 · 三类一律），
  且**不回到**「写入前那个值」——`clear()` 不是「撤销最后一次写入」。
- **路由通道连续清空两次**：第二次 MUST 报告「无变化」（幂等 · 不抛错）。
- **路由通道清空后立即写入**：新值生效，通道恢复「有值」——清空**不**留下残余状态。
- **路由通道在一次写入调用里收到两个值**：MUST 抛 `InvalidChannelUpdateError`。
- **通道的 key 为空串**：合法（内部通道可以没有 schema key）⇒ 错误消息里的 key 名可能为空串，
  但错误对象 MUST 仍带结构化字段（key + 原因）。
- **通道不感知运行期**：通道实例 MUST NOT 持有节点 / 图 / 运行配置 / 时钟 / 句柄（裁定 9）。
- **有人绕过通道直接改状态**：MUST **无路可走** —— 通道不是公开 API（不在契约层 / 门面符号面），
  且写入入口只有 `update()` 一个（澄清轮 Q10）⇒ 「绕过通道的写入路径」不存在。
- **两个线程同时写同一个通道**：**不被支持**（通道不承诺线程安全）⇒ v1 内核的调度循环
  MUST 保持**单线程**写入（FR-023 ②）。
- **用户就地修改了写入的那个对象**（例如 `state["messages"].append(x)`）：
  通道持有的值**会跟着变**（浅引用 · FR-024 ①）—— Python 的常规语义，MUST NOT 被通道「修正」。
- **写入一个不可拷贝的对象**：MUST **不抛错**（通道不做深拷贝 ⇒ 不存在「拷贝失败」这种失败模式）。
- **构造时传入不可调用的归约器**（如 `3`）：MUST 在**构造点**抛 `TypeError`
  （MUST NOT 拖到第一次写入才炸 · FR-025 ①）。
- **构造时传入「不是二元」的归约器**（如 `lambda a: a`）：MUST **NOT** 在构造期报错 ——
  二元性由 **B4F1** 判定，通道层不重复校验（FR-025 ④）；运行期表现为调用时的 `TypeError`。
- **上游版本漂移**：本 spec 引用的上游行号核实环境为 **`langgraph 1.2.11`**
  （实测于 CPython 3.12.3）⇒ 换版本后行号 MUST 重新核实，MUST NOT 凭记忆沿用（宪法原则 VIII）。

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001（通道抽象 · 唯一读写单元 · 可替换）**：系统 MUST 提供统一的**通道抽象**，
  作为状态读写的**唯一**实现单元；抽象 MUST 至少包含三类语义的操作 ——
  **写入**（把一批写入值并入通道）、**读取**（取回当前值）、**清空**（恢复到「无值」）——
  外加一个「有值 / 无值」判定。三类通道 MUST 承自该抽象，MUST NOT 各自另立一套读写路径
  （**收敛** · 提示词 §1）。抽象基类的类名 MUST 冻结为 `Channel`；三个实现类名 MUST 为
  `LastValue` / `BinaryOperatorAggregate` / `EphemeralValue`（裁定 1）。

- **FR-002（操作面 · 名字与语义逐字冻结）**：通道抽象 MUST 提供下列 **4** 个操作，
  **名字与语义逐字冻结**（跨 feature 契约 —— B5F2 / B7F1 / B8F1 据此消费）：

  | 操作 | 语义 | 返回 | 无值 / 异常行为 |
  |---|---|---|---|
  | `update(values)` | 把「本步的写入序列」并入通道 | `bool`：**本次调用是否写入了值** | 空序列 ⇒ **无操作**，返回假 |
  | `get()` | 取回通道当前值 | 当前值 | 「无值」⇒ 抛 `EmptyChannelError` |
  | `is_available()` | 判定「有值 / 无值」 | `bool` | **恒不抛错** |
  | `clear()` | 把通道恢复到「无值」 | `bool`：**是否发生状态变化** | 已是「无值」⇒ **无操作**，返回假 |

  调用方 MUST 仅凭该抽象使用通道；MUST NOT 依赖任何具体子类。
  `clear()` 的**默认实现 MUST 是无操作**（⇒ 未覆写它的**第三方自定义通道**在步末**不会**被清空）；
  但本 feature 的**三类通道 MUST 全部覆写**它（⇒ 清空后一律「无值」· FR-009）。

  > **📌 `update()` 返回值的口径（澄清轮 Q5）**：返回值 MUST 表示「**本次调用是否写入了值**」，
  > MUST **NOT** 被解释为「**通道的值是否发生了变化**」——
  > 写入序列**非空 ⇒ 恒为真**（哪怕归约后的新值与旧值**逐字相等**）；
  > **空序列 ⇒ 假**。
  > **理由**：上游的同一信号是「这次有写入」（`last_value.py:67` · `binop.py:144` ·
  > `ephemeral_value.py:68`），而上游调度层正是用它判断「本步这个通道是否被更新、
  > 要不要触发下游任务」（`langgraph/pregel/_algo.py:319-324`）⇒ 语义 MUST 与上游**逐字同构**，
  > 否则 B7F1 照抄上游用法时会出现「写了但值相同 ⇒ 不触发下游任务」的**静默调度差异**。
  > （对照：`clear()` 的返回值仍是「**状态是否真的变化**」——从「有值」清成「无值」为真，
  > 已是「无值」则为假。）

  **构造签名与属性名（同样逐字冻结 · 澄清轮 Q4）** —— 下游的 **B5F2 / B7F1 / B8F1** 都要直接使用通道类，
  故构造方式与属性名一并冻结，避免三个下游 feature 各挑一套名字：

  | 项 | 冻结内容 |
  |---|---|
  | 抽象基类构造 | `Channel(key: str, value_type: Any)` —— ⚠️ 该行冻结的是**子类**的**构造形状**；抽象基类本身**运行时不可实例化**（`abc.ABC` + `@abstractmethod`） |
  | `LastValue` 构造 | `LastValue(key: str, value_type: Any)` |
  | `BinaryOperatorAggregate` 构造 | `BinaryOperatorAggregate(key: str, value_type: Any, reducer: Callable[[Any, Any], Any])` |
  | `EphemeralValue` 构造 | `EphemeralValue(key: str, value_type: Any)` |
  | 属性 · `key` | `str` —— schema key（内部通道 MAY 为空串） |
  | 属性 · `value_type` | 值类型对象 —— **归约前的基类型 `T`**，与 B4F1 冻结的通道规格字段 `value_type` **同名同义** |
  | 属性 · `value` | 通道**当前值** —— MUST 以**只读**方式暴露（外部 MUST NOT 能改写；读取当前值一律走 `get()`）；**无值时 MUST 抛 `EmptyChannelError`**（与 `get()` **同义** —— MUST NOT 返回 `None`，否则会出现「有值 / 无值」之外的第三种语义 · SC-004） |
  | 属性 · `reducer` | 归约器**引用** —— `LastValue` / `EphemeralValue` 恒为**空**（不持有归约器） |

  ① 构造 MUST **无副作用**（MUST NOT 写日志 / 读环境变量 / 分配外部资源 / 发起 I/O）；
  ② `value_type` MUST **只**用于推导空值（FR-006）与承载类型信息，MUST NOT 用于**校验**写入值的类型
  （类型不匹配的处置属 **B7F3** 的入参校验）。

- **FR-003（`LastValue` · 覆盖语义 · C3）**：`LastValue` MUST 在写入时**覆盖**旧值
  （丢弃左值 · C3）：写入后通道的值 == 该次写入的值；读取 MUST 返回最近一次写入的值；
  MUST **从不**调用归约器（`LastValue` MUST 不持有归约器）。

- **FR-004（`LastValue` · 一步内多值 ⇒ 显式失败）**：`LastValue` 在**一次** `update` 调用中
  收到多于一个值时 MUST **显式失败**（抛 `InvalidChannelUpdateError`），
  MUST NOT 静默取末值、MUST NOT 静默丢弃多余值。空序列 MUST 是无操作（FR-002）。

- **FR-005（`BinaryOperatorAggregate` · 归约语义 · C2）**：`BinaryOperatorAggregate` MUST 在每次写入时
  计算 `new_value = reducer(current, new)` 并把 **`new_value`**（不是 `new`）作为通道的新值保存；
  `current` MUST 取**写入前**通道的值。归约 MUST **按序**进行（序列中的值依次与当前值归约）。

- **FR-006（`BinaryOperatorAggregate` · 空值推导）**：`BinaryOperatorAggregate` MUST 在构造时按其
  **值类型**推导「空值」，顺序 MUST 为：
  ① **剥离** `Annotated` / `Required` / `NotRequired` 包装（逐层剥到实类型）；
     > **📌 剥离的适用范围（澄清轮 Q15 补 · research D-05 / D-17）**：剥离**仅**发生在**空值推导**
     > （`_derive_empty_value`）内部；通道暴露的 `value_type` 属性 MUST **原样**等于 B4F1 的
     > `ChannelSpec.value_type`（实测 `Annotated[Required[list], op]` ⇒ B4F1 给出
     > `typing.Required[list]` —— **顶层** `Required` 不递归剥离 · research DR-9）⇒
     > 二者的**区别仅在「推导用实类型」vs「暴露原样类型」**，MUST NOT 把暴露值也剥掉。
  ② **抽象容器映射**：`collections.abc.Sequence` / `MutableSequence` → `list`；
     `Set` / `MutableSet` → `set`；`Mapping` / `MutableMapping` → `dict`；
  ③ **尝试构造空实例**：成功 ⇒ 该通道的**初始值** = 该空实例（且通道自始「**有值**」）；
     失败（抛任何异常）⇒ 该通道**初始为「无值」**。
  空值推导失败 MUST **NOT** 让通道构造失败（构造 MUST NOT 抛错）。
  ④ 空值 MUST 是**每次构造新建的独立实例**（MUST NOT 跨通道共享同一个可变对象）——
     否则两个归约型通道会共享同一个空列表，一个通道的归约结果会污染另一个
     （上游同为每实例新建：`binop.py:89-92` 的 `typ()` 每次调用都产生新对象）。

- **FR-007（`BinaryOperatorAggregate` · 首次写入的 `current`）**：`BinaryOperatorAggregate` 的写入
  MUST 分两种情形：
  ① 通道**有值**（含 FR-006 推导出的初始空值）⇒ `current` = 通道当前值 ⇒ 保存 `reducer(current, new)`；
  ② 通道**无值**（值类型不可实例化 ⇒ 首次写入）⇒ MUST **直接保存 `new`**，
     MUST **NOT** 调用归约器（**单值**写入时归约器调用次数 == **0**）；此后写入回到情形 ①。
  > **📌 多值写入的限定（research D-17 实测 · 上游 `binop.py:126-128` + `:143`）**：
  > 上游在「无值 + 一次收到多个值」时**只把首个值直存**，**其余值仍逐个归约**
  > （实测 `update(['a','b'])` ⇒ `operator` 被调用 **1** 次）⇒
  > **「调用次数 == 0」仅对单值写入成立**；多值写入的调用次数 == **值数 − 1**，
  > 且**首个值不参与归约**（与上游逐字同构 · data-model §3.3 的对应行）。
  > **📌 这是提示词 §10 风险点的正面回答**：MUST 与上游**逐条同构**
  > （`langgraph/channels/binop.py:89-92` + `:126-128`），MUST NOT 自造「统一语义」。

- **FR-008（`BinaryOperatorAggregate` · 归约失败不得污染状态）**：归约器抛错时，异常 MUST **向上传播**，
  且通道的值 MUST **保持不变**（写入失败 MUST NOT 留下半写状态）。

- **FR-009（`clear()` 的清空语义 · 三类通道统一）**：三类通道的 `clear()` MUST **一律**把通道清到「**无值**」
  （`is_available()` 为假、`get()` 抛 `EmptyChannelError`；已是「无值」⇒ **无操作**、返回**假** · FR-002）：
  - `LastValue`（覆盖型）MUST **覆写** `clear()` ⇒ 清空后为「无值」；
  - `BinaryOperatorAggregate`（归约型）MUST **覆写** `clear()` ⇒ 清空后为「无值」，且 **NOT** 回到初始空值
    （FR-022 ③）；
  - `EphemeralValue`（路由型）MUST **覆写** `clear()` ⇒ 清空后为「无值」。
  清空 MUST NOT 影响其它通道；**清空时机由调用方（调度层）决定** —— 通道 MUST NOT 自行感知
  super-step 边界（MUST NOT 持有时钟 / 步计数器）。
  > **📌 与上游的逐类对照（research D-17 实测 · 澄清轮 Q15 补）**：上游**没有** `clear()` 方法
  > （`langgraph/channels/base.py` 的 `BaseChannel` 无该方法）⇒ 三类通道的「清空」在 freegraph 是
  > **新增的显式操作**；上游的步末重置靠 `update(EMPTY_SEQ)`
  > （`langgraph/pregel/_algo.py:326-334`），而**三类通道对 `update([])` 的反应各不相同**：
  > `LastValue` ⇒ **无操作**（`last_value.py:57-58`）· `BinaryOperatorAggregate` ⇒ **无操作**
  > （`binop.py:124-125`）· `EphemeralValue` ⇒ **清空为 `MISSING`**（`ephemeral_value.py:55-61`）。
  > ⇒ **可观察语义等价的落点是「调度层在步末调用 `clear()` 的通道集合」**（B7F1 的职责）：
  > 步末 MUST **只**对**路由型**通道调用 `clear()`（覆盖型 / 归约型在步末**保留**其值，
  > 与上游 `update([])` 的 no-op 效果逐字同构）—— 本 feature 只**冻结 `clear()` 的语义**
  > （三类一律 ⇒ 无值），**步末调用范围**归 **B7F1**（见 contract §7 `B-2`）。

- **FR-010（`EphemeralValue` · 写入语义）**：`EphemeralValue` 的写入 MUST 把通道值**覆盖**为最新写入值；
  在**一次** `update` 调用中收到多于一个值时 MUST **显式失败**（抛 `InvalidChannelUpdateError`）；
  空序列 MUST 是无操作（FR-002）。

- **FR-011（有值 / 无值的可判定区分 · C4 的基础）**：系统 MUST 提供「通道无值」与「通道有值」的
  **完全可判定**区分（不存在第三种模糊状态）：
  ① `is_available()` 在「有值」时为真、在「无值」时为假，MUST **恒不抛错**；
  ② `get()` 在「无值」时 MUST 抛 `EmptyChannelError`，MUST **NOT** 返回 `None` 冒充有值；
  ③ 「值为 `None`」MUST 与「无值」**严格可区分** —— 写入 `None` 后 `is_available()` MUST 为真。

- **FR-012（schema → 通道的映射规则）**：B4F1 的解析结果 MUST 能**按 schema key 映射到通道类型**，
  映射 MUST 由**单一入口**完成（接受一个通道规格 ⇒ 返回一个通道实例），
  MUST NOT 由调用方各自拼装通道类：
  ① 通道规格标注「**有归约器**」⇒ MUST 产出 `BinaryOperatorAggregate`，其归约器 MUST 是规格里的
     **同一引用**（**身份**判定），其值类型 MUST 是规格里的值类型；
  ② 通道规格标注「**无归约器**」⇒ MUST 产出 `LastValue`；
  ③ **路由通道** MUST 产出 `EphemeralValue`，但 MUST **NOT** 由 schema 推导
     （路由通道不是 schema key）⇒ MUST 支持**显式请求**创建；
  ④ 映射 MUST **保序**（按 schema 的 key 顺序）；每个 key MUST **恰**产出一个通道。
  > **📌 与 B4F1 的冻结字段对接**：通道规格的字段名（`key` / `value_type` / `reducer` / `has_reducer` /
  > `semantics` / `required`）已由 **B4F1 FR-020** 逐字冻结 ⇒ 本 feature MUST 按该形状消费，
  > MUST NOT 另立一套字段名。

  **映射入口（名字逐字冻结 · 澄清轮 Q4）**：schema → 通道的派生 MUST 只经由下列两个入口
  （都在 `freegraph.runtime` 的导出面）：
  ① `build_channel(spec) -> Channel` —— 接受**一个**通道规格，返回**一个**通道实例；
  ② `build_channels(schema_spec) -> dict[str, Channel]` —— 接受**一份**规格集，返回
     「key → 通道」的**保序**映射（**可变** `dict` · 下游 B5F2 / B7F1 要在其上**增补内部通道**
     · research D-14 · 契约 §4）。
  路由通道（`EphemeralValue`）**不属于** schema 派生 ⇒ MUST 支持直接实例化（FR-002 的构造签名）。

- **FR-013（通道只持纯数据 + 归约器引用）**：通道 MUST **只**持有：schema key、值类型、当前值、
  归约器引用；MUST **NOT** 持有或感知：节点、图结构、运行配置、调度信息、时钟、文件句柄、连接、
  协程、锁（提示词 FR-006 · 裁定 9）。
  ① **「持有」的判定口径（澄清轮 Q15）**：MUST 写死为**两个**信号 ——
     **公开**属性（4 个 `property`）集合 **恰为** {`key`, `value_type`, `value`, `reducer`}，
     且**实例槽位**集合 ⊆ {`_key`, `_value_type`, `_value`, `_reducer`}（`__slots__` 私有槽 · 名字逐字冻结）；
     MUST NOT 以 `dir()` 全集或 `vars()` 判定（前者含方法与继承属性、后者在 `__slots__` 下不存在）。
     > **📌 补充（research D-17 实测）**：**子类 MUST NOT 引入新槽**（⇒ 子类 MUST 声明
     > `__slots__ = ()`）—— 否则子类实例会自带 `__dict__`，实测可写入**任意属性**
     > （`ch.arbitrary = 42` 成功）⇒ 通道**可持有** 4 项之外的数据 ⇒ ①② 均失守。
     > **公开属性的收集口径**：MUST 沿 **MRO** 收集 `property`（`type(ch).__dict__` **只**含该类自身
     > 定义的属性 —— 属性定义在基类时取到的是**空集** ⇒ 断言 MUST 用
     > `{n for c in type(ch).__mro__ for n, v in c.__dict__.items() if isinstance(v, property)}`）。
  ② **规模口径（澄清轮 Q8）**：通道 MUST **NOT** 持有**其它通道**或**状态表**的引用 ——
     ⇒ 结构上**不可能**遍历全体 key；单通道的写入 / 读取 / 清空 MUST 只触及**该通道自身**的状态；
  ③ 由此派生的可判定形式：「schema 有 N 个 key」与「schema 只有 1 个 key」两种情形下，
     **单通道**的写入 / 读取 / 清空所触及的状态条目数 MUST **相同**（**不随 key 数增长**）——
     判定 MUST 用**计数探针**（触及次数 / 访问次数），MUST **NOT** 用**墙钟耗时**（CI 上会假红）。

- **FR-014（归约器按引用持有）**：归约器 MUST **按引用**持有 —— MUST NOT 包装、复制、部分应用或以任何
  方式替换 ⇒ `channel.reducer is operator.add` MUST 成立（**身份**判定）。

- **FR-015（依赖与 I/O 纪律 · 零副作用）**：本层 MUST 只依赖**标准库**；
  MUST **NOT** import `langchain` / `langchain-core` / `langgraph*` / `langsmith` / `pydantic` /
  `typing_extensions`；MUST **NOT** 读取**任何**环境变量；MUST **零出站**、零文件 I/O；
  导入本 feature 的模块 MUST **NOT** 产生 import 副作用。

- **FR-016（层纪律 · ARCH-1 / ARCH-3）**：本 feature 属 **L2 执行内核层**；新增代码 MUST 落在
  **已登记**的 L2 路径（层注册表已登记 `src/freegraph/runtime/` = L2）⇒ 层注册表 MUST **零改动**；
  L2 MUST 只向下依赖 **L1 契约层**，MUST NOT import L3 / L4 / L5。

- **FR-017（错误类型 · 落 L2 · 捕获走基类 · 结构化字段）**：本 feature MUST 新增两个错误类型，
  MUST **定义在 L2**（`src/freegraph/runtime/`），MUST **NOT** 进入契约层 18 符号面 /
  门面 7 符号面（**公开面零变更**）：
  ① `EmptyChannelError` —— 读取「无值」通道时抛出；MUST 继承 `FreegraphError`；
  ② `InvalidChannelUpdateError` —— 一次写入调用中收到多于一个值时抛出；
     MUST 继承 `FreegraphError` **且**继承 `ValueError`；
  ③ 用户侧 `except FreegraphError` MUST 能捕获到二者；需要读结构化字段的上层 MAY 从
     **`freegraph.runtime`** import 具体子类（L2 子包 · 与 B4F1 裁定 14 同一口径）；
  ④ 错误对象 MUST 暴露**结构化字段**，字段清单**逐字冻结**（澄清轮 Q7）：

  | 错误类型 | 字段 | 含义 |
  |---|---|---|
  | `EmptyChannelError` | `key` | 出错通道的 key |
  | `InvalidChannelUpdateError` | `key` | 出错通道的 key |
  | `InvalidChannelUpdateError` | `received_count` | 本次写入调用收到的**值个数** |
  | `InvalidChannelUpdateError` | `expected_count` | 期望的值个数（**恒为 1**） |

  ⑤ 消息文本只是**英文摘要**，上层 MUST **无须解析消息**即可取到全部细节；
  ⑥ 错误对象 MUST **NOT** 携带用户写入的**值本身**（只带计数与 key）——
  错误类型不是数据通道，不得把用户数据卷进错误对象；
  ⑦ `EmptyChannelError` MUST **只**继承 `FreegraphError`（MUST **NOT** 继承 `ValueError`）——
  「读到无值」是稀疏状态下的**正常信号**（上游 `EmptyChannelError` 亦只继承 `Exception`），
  若它是 `ValueError`，用户既有的 `except ValueError` 会把它一并吞掉。
  `InvalidChannelUpdateError` MUST 继承 `FreegraphError` **且**继承 `ValueError`
  （与 B4F1 的 `InvalidSchemaError` 同款：既是内核错误，也是「传进来的东西不对」）。

- **FR-018（不越界）**：本 feature MUST **NOT** 实现：稀疏状态读取（B5F2）·
  调度循环 / super-step（B7F1）· `StateGraph` 构建器（B6F1）· checkpoint 写入与通道复制（B14F1）·
  `Topic` / `Barrier` 等通道类型 · `add_messages` 等 LangChain 特有归约器（freechain 层）·
  `Overwrite` 旁路值。

- **FR-019（纯单元可测 · 覆盖率与负向用例）**：本 feature 的判据 MUST **全部**以**单元测试**落地
  （无图可跑 ⇒ 不得以「跑图通过」替代）：
  ① MUST 覆盖三类通道的**正向**路径与**负向**路径 —— 负向至少含：一步内多值冲突（`LastValue` /
     `EphemeralValue`）、读取「无值」通道、归约器抛错、空值推导失败（类型不可实例化）；
  ② **本 feature 新增/修改的代码**（`channel.py` / `mapping.py` 全文 + `errors.py` / `__init__.py` 的
     **新增部分**）的**行覆盖与分支覆盖 MUST 均为 100%**（本 feature 无「可跑图」兜底 ⇒ 覆盖率要求最高），
     **整包** `src/freegraph/runtime/` 的覆盖率 MUST **记录但 MUST NOT 阻断**（澄清轮 **Q14** · B4F1 无基线），
     取证 MUST 在**开发期**完成并**记入人工验证记录**（v1.0 依赖面为零 ⇒ MUST NOT 把覆盖率工具
     写进仓库的依赖声明）；
     > **📌 取证口径（research D-17 实测 · 澄清轮 Q14 补）**：**分支覆盖 MUST 以 `--branch` 取证**
     > （实测：无 `--branch` 时 `coverage report` **不输出 Branch 列** ⇒ 分支覆盖**无从判定**）；
     > `errors.py` / `__init__.py` 的「**新增部分**」MUST 以**差分口径**判定 ——
     > 用 `git diff -U0` 取**新增行号集合**，与 `coverage json` 的 `executed_lines` /
     > `executed_branches` 求交（未覆盖的新增行 / 新增分支数 MUST == **0**）；
     > **文件级** `coverage report` **无法**区分「既有行」与「新增行」⇒ MUST NOT 以它单独作判据。
  ③ MUST 存在**一个**「只依赖通道抽象」的自定义通道实现用例，以证明抽象**真的**可替换（US4）。

- **FR-020（人工门禁 + 证据门禁）**：本 feature MUST 产出人工验证记录，落
  **`harness/verification/B5F1/manual-verification.md`**，逐条核对 **A1–A3** 三项验收判据并给出结论；
  记录 MUST 采用仓库既有的**五段式**结构（环境 / 步骤 / 实际输出 / 结论 / 遗留问题，
  见 `harness/verification/README.md`），第 3 节 MUST 粘贴**真实输出**，未实跑的项 MUST 显式记入
  「遗留问题」（MUST NOT 伪造输出）；记录 MUST 含**来源覆盖表**（宪法原则 VIII）——
  每条判据标注来源（上游 `路径:行号` + 核实版本 / 澄清条号 / 宪法条款号）。

- **FR-021（与上游的语义对应 · 证据门禁的具体化）**：三类通道的每条语义 MUST 标注上游**源码行号**
  （核实环境 **`langgraph 1.2.11`**）：覆盖语义、一步内多值冲突、空值推导、首次写入的 `current`、
  清空语义、「有值 / 无值」判定 —— 缺标注项数 == **0**；换上游版本后 MUST 重新核实，
  MUST NOT 凭记忆沿用（宪法原则 VIII）。

- **FR-022（通道的初始状态 · 三档写死）**：通道 MUST 在构造完成后处于下列**初始状态**之一
  （澄清轮 Q9 —— 收敛 SC-004 与 FR-006 之间的口径冲突）：
  ① **覆盖型**（`LastValue`）与**路由型**（`EphemeralValue`）⇒ 初始「**无值**」
     （`is_available()` 为假、`get()` 抛 `EmptyChannelError`）；
  ② **归约型**（`BinaryOperatorAggregate`）⇒ 初始「**有值**」，其值 = FR-006 推导出的**空值**；
     **仅当**值类型**不可实例化**时才是「无值」（FR-006 ③）；
  ③ **清空后的状态**一律为「**无值**」⇒ 清空后的归约型通道**不回到**其初始状态；
     v1.0 **不提供**「恢复到初始状态」的操作 —— 将来若 checkpoint 回滚需要它（**B14F1**），
     再另立**独立**操作，MUST **NOT** 复用 `clear()`。

- **FR-023（写入权限与并发 · 澄清轮 Q10）**：
  ① **写入只有一条路径**：通道的写入 MUST **只**由调度层发起（下游 **B7F1**）；
     用户代码 MUST **NOT** 直接持有 / 写入通道对象 —— 通道属 **L2 内部 API**，
     不是用户可获得的对象；绕过通道的写入路径 MUST **NOT** 存在
     （否则「覆盖 vs 归约」的唯一实现点会被绕开 · 提示词 §1 的「收敛」目标落空）。
  ② **不承诺线程安全**：通道 MUST **NOT** 提供锁 / 原子性保证；并发访问 MUST 被禁止 ——
     v1 内核的写入只发生在**单线程**的调度循环里。通道 MUST NOT 引入任何同步原语
     （与 FR-006 / FR-013 的「只持纯数据」一致）。

- **FR-024（值的引用语义 · 澄清轮 Q11）**：通道 MUST **直接持有**用户写入的对象 ——
  MUST **NOT** 复制、转换、冻结或包装它（归约型通道持有的是**归约器返回的那个对象**）。
  ① 因此「用户就地修改该对象」**会**反映到通道持有的值上 —— 这是 Python 的**常规引用语义**，
     不是缺陷，MUST NOT 被通道「修正」；
  ② 通道 MUST **NOT** 因「值不可拷贝」而让写入失败（MUST NOT 做深拷贝 ⇒ 无此失败模式）；
  ③ 通道 MUST **NOT** 校验写入值的**类型**（`value_type` 只用于推导空值与承载类型信息 ·
     FR-002 ②）。

- **FR-025（构造期的防御性校验 · 澄清轮 Q12）**：通道 MUST 在**构造时**对**明显非法**的参数
  **显式失败**（MUST NOT 把错误拖到第一次写入才暴露）：
  ① 归约器**不是可调用对象** ⇒ MUST 抛内置 `TypeError`；
  ② 参数缺失 / 自相矛盾（如「标注有归约器但归约器为空」）⇒ MUST 抛内置 `ValueError`；
  ③ MUST **NOT** 新增 L2 错误类型来承载它（不扩大公开面）——
     这是「**调用方用错了 API**」的编程错误，不是运行期状态问题；
     `InvalidChannelUpdateError` 的语义**只**覆盖「写入冲突」（FR-017），MUST NOT 被复用；
  ④ MUST **NOT** 重做**归约器二元性**校验（那是 **B4F1** 的职责 · B4F1 FR-004 / FR-007 ②）——
     通道层重复校验就是**第二个判定点**，违背「收敛」；
  ⑤ MUST **NOT** 校验写入值的**类型**（FR-024 ③）。

- **FR-026（独立验收脚本 · 澄清轮 Q13）**：本 feature MUST 产出**独立验收脚本**
  `harness/verification/B5F1/acceptance.py`：
  ① MUST **零第三方依赖**（只 import 标准库 + 被验收的 freegraph 本身）· **单文件** ·
     **一条命令**跑完全部验收判据（A1–A3 + 本 feature 的内部 SC）；
  ② MUST 支持 `--record <file>`，产出**五段式**（环境 / 步骤 / 实际输出 / 结论 / 遗留问题）
     的 markdown 片段，MUST 可直接并入 `manual-verification.md`；
  ③ MUST 采用仓库既有的**两态运行**约定（环境已安装 freegraph ⇒ 测发行产物；
     未安装 ⇒ 自动把 `<repo>/src` 插入 `sys.path` 测源码树）与退出码约定
  （`0` = PASS · `1` = FAIL · `2` = 环境未就绪）；
  ④ MUST **NOT** 替代 pytest 断言与门禁脚本（两者是**机器门禁**，本脚本是**面向人**的同口径对照）；
  ⑤ 人工验证记录 `manual-verification.md` 仍是**必落**件（宪法原则 V / 门禁 5）。

- **FR-027（参数化组合测试 · 立项书 S5 ③）**：系统 MUST 提供一组**参数化组合测试**
  （`pytest.mark.parametrize`），枚举「**归约器类型** × **通道类型**」的组合 ——
  ① 归约器：`operator.add` / `max` / 一个**自定义**二元函数；通道：`LastValue` /
  `BinaryOperatorAggregate` / `EphemeralValue` ⇒ 组合数 **≥ 12**；
  ② 每组 MUST 自带**相容的值类型**（`operator.add`+`list` · `max`+`int` · 自定义+`tuple`）——
     归约器与值类型**不得**配成不兼容组合（否则断言的是「归约器报错」而非「语义恒成立」）；
  ③ MUST 断言四条语义在**所有组合**下恒成立：覆盖型写入 ⇒ 读到**末值**；归约型写入序列 ==
     **从初始值起**的逐次归约（基准按该组的 `value_type` 推导）；路由型清空后 ⇒ **无值**；
     一步内多值 ⇒ **显式失败**且**值不变**；
  ④ MUST **NOT** 用 `skip` / `xfail` 掩盖组合（**被跳过的组合数 == 0**）。
  **理由**：立项书 §4.2 **S5**「语义等价」的**第三层证据**（「属性 / 参数化测试：枚举 reducer 类型 ×
  通道组合」）在本 feature 之前**无承接方**（其落点说明只把**差分夹具**指给 B5F2 / B8F1），
  而 B5F1 正是「**通道 × 归约器**」的**唯一落点** ⇒ 该层证据 MUST 落在此（澄清轮 **Q15** ③）。

### 需求 ↔ 成功标准 追溯表

> **A1–A3 的定义**（= 立项书 §5.2 的 B5F1 小目标 · 下表「主要判据」列一律指**验收判据** A1–A3）：
> **A1** 归约器 `operator(current, new)` 语义一致 ·
> **A2** 无归约器 key 被覆盖 ·
> **A3** 路由通道每 super-step 清空。
>
> **A1–A3 的 Q8 条号映射**（FR-020 要求人工验证记录的「来源覆盖表」标 **Q8 条号** ⇒ 本表提供该映射）：
> **A1** → **Q8 §3.4 C2（归约器机制）** ·
> **A2** → **Q8 §3.4 C3（默认归约语义）** ·
> **A3** → **Q8 §3.4 C7（路由函数契约）+ C8（条件边读状态）**。
> （其余 SC 属**本 feature 的内部判据** ⇒ 来源标「本 spec FR-xxx」+ 宪法条款号。）
>
> ⚠️ **编号多义提示（**四套**编号 · 同名不同义）**：
> ① **验收判据 A1–A3**（本 spec / 引文 §6 / 立项书 §5.2）·
> ② **执行闸口 A1–A5**（`tasks.md`）·
> ③ **quickstart 验收闸口 V1–V9**（`quickstart.md`）·
> ④ **宪法门禁 G1–G30**（`harness/scripts/gates/`）
> ⇒ 引用时 MUST 带限定语（「验收判据 A1」/「执行闸口 A1」/「quickstart 闸口 V1」/「门禁 G21」）。

| FR | 主题 | 对应 SC | 主要判据 |
|---|---|---|---|
| FR-001 | 通道抽象（唯一读写单元 · 可替换） | SC-017 / SC-009 | — |
| FR-002 | 操作面（4 个操作 + 构造签名 + 属性名 **逐字冻结** · 澄清轮 Q4） | SC-001 / SC-003 / SC-004 / SC-006 / **SC-019** / **SC-020** | 验收判据 A2 / A3 |
| FR-003 | `LastValue` 覆盖语义（C3） | SC-001 | **验收判据 A2** |
| FR-004 | `LastValue` 一步内多值 ⇒ 显式失败 | SC-006 | 验收判据 A2 |
| FR-005 | `BinaryOperatorAggregate` 归约语义（C2） | SC-002 / **SC-021** | **验收判据 A1** |
| FR-006 | BinOp 空值推导（剥离 / 抽象容器 / 实例化） | SC-007 | 验收判据 A1 |
| FR-007 | BinOp 首次写入的 `current`（两分支） | SC-002 / SC-007 | **验收判据 A1** |
| FR-008 | 归约失败不得污染状态 | SC-006 / SC-016 | 验收判据 A1 |
| FR-009 | `EphemeralValue` 清空语义 | SC-003 | **验收判据 A3** |
| FR-010 | `EphemeralValue` 写入语义 | SC-003 / SC-006 | 验收判据 A3 |
| FR-011 | 有值 / 无值的可判定区分（C4 基础） | SC-003 / SC-004 / **SC-023** | — |
| FR-012 | schema → 通道的映射规则（+ **映射入口名冻结** · 澄清轮 Q4） | SC-008 / **SC-019** | — |
| FR-013 | 通道只持纯数据 + 归约器引用（+ **规模口径** · 澄清轮 Q8） | SC-009 / **SC-022** | — |
| FR-014 | 归约器按引用持有 | SC-010 | 验收判据 A1 |
| FR-015 | 依赖与 I/O 纪律 · 零副作用 | SC-005 | — |
| FR-016 | 层纪律（ARCH-1 / ARCH-3） | SC-011 | — |
| FR-017 | 错误类型（落 L2 · 捕获走基类 · 结构化字段**逐字冻结** · 澄清轮 Q7） | SC-018 | — |
| FR-018 | 不越界 | SC-012 | — |
| FR-019 | 纯单元可测 · 覆盖率与负向用例 | SC-015 / SC-017 | 验收判据 A1 / A2 / A3 |
| FR-020 | 人工验证记录 + 来源覆盖表 | SC-013 | 验收判据 A1 / A2 / A3 |
| FR-021 | 与上游的语义对应（行号标注） | SC-014 | 验收判据 A1 / A2 / A3 |
| FR-022 | 通道的初始状态（三档写死 · 澄清轮 Q9） | SC-004 / **SC-023** | — |
| FR-023 | 写入权限与并发（只允许调度层写 · 不承诺线程安全 · 澄清轮 Q10） | **SC-024** | — |
| FR-024 | 值的引用语义（浅引用 · 不复制 · 不校验类型 · 澄清轮 Q11） | **SC-025** | — |
| FR-025 | 构造期的防御性校验（当场失败 · 内置异常 · 不重做二元性 · 澄清轮 Q12） | **SC-026** | — |
| FR-026 | 独立验收脚本（`acceptance.py` · 零依赖 · 一条命令跑完 · 澄清轮 Q13） | **SC-027** | 验收判据 A1 / A2 / A3 |
| FR-027 | **参数化组合测试**（归约器 × 通道 · 立项书 S5 ③ · 澄清轮 Q15） | **SC-028** | 验收判据 A1 / A2 |

> **反向覆盖**：**SC-001 ~ SC-028 每个 SC 至少被一条 FR 映射**（SC-016 ← FR-008 · SC-019 ← FR-002 / FR-012 · SC-020 ← FR-002 · SC-021 ← FR-005 / FR-007 · SC-022 ← FR-013 · SC-023 ← FR-011 / FR-022 · SC-024 ← FR-023 · SC-025 ← FR-024 · SC-026 ← FR-025 · SC-027 ← FR-026 · SC-028 ← FR-027）·
> 逐条任务映射见 `tasks.md` 文末「附录 · 任务 ↔ spec 追溯表」。

### Key Entities

- **通道（抽象 · `Channel`）**：状态的**唯一读写单元**；提供 4 个冻结操作
  （`update` / `get` / `is_available` / `clear`）+ 4 个冻结属性
  （`key` / `value_type` / `value` / `reducer`）；构造签名逐字冻结
  （`Channel(key, value_type)`，归约型子类多一个 `reducer` 参数）；
  **可替换**的实现单元（FR-001 / FR-002 · 裁定 1 · 澄清轮 Q4）。
- **`LastValue`**：**无归约器 ⇒ 覆盖**（C3）；只持有 key / 值类型 / 当前值；不持有归约器。
- **`BinaryOperatorAggregate`**：**有归约器 ⇒ `reducer(current, new)`**（C2）；
  持有 key / 值类型 / 当前值 / **归约器引用**；构造时按类型推导**空值**（或判定为「无值」）。
- **`EphemeralValue`**：**路由通道**，每 super-step 清空（供 **B8F1** 使用）；
  持有 key / 值类型 / 当前值；`clear()` 覆写为「清空 ⇒ 无值」。
- **值（value）**：通道持有的**纯数据**（用户写入的对象，MUST NOT 被通道复制 / 转换 / 校验类型）。
- **归约器（reducer）**：`reducer(current, new) -> value`（C2）；**按引用**持有
  （MUST NOT 被包装 / 复制）；二元性由 **B4F1** 判定，通道**不做**校验。
- **空值（empty value）**：归约型通道的**初始值** —— 按值类型推导（剥离 typing 包装 →
  抽象容器映射 → 构造空实例）；推导失败 ⇒ 通道初始「**无值**」（FR-006）。
- **有值 / 无值（availability）**：通道的**二值状态** —— 「有值」= 存在当前值（含值为 `None`）；
  「无值」= 从未写入 / 已被清空；由 `is_available()` 判定、由 `get()` 抛错表达（FR-011）。
- **通道规格（`ChannelSpec` · B4F1 的冻结产物）**：本 feature 的**映射输入** ——
  字段 `key` / `value_type` / `reducer` / `has_reducer` / `semantics` / `required`
  （B4F1 FR-020 逐字冻结）⇒ 本 feature MUST 按该形状消费。
- **通道更新错误（`InvalidChannelUpdateError`）**：一次写入调用中收到多于一个值时的**显式失败**信号
  —— 结构化字段含出错通道的 key；消息只是英文摘要。
- **通道空错误（`EmptyChannelError`）**：读取「无值」通道时的**显式失败**信号。

### Out of Scope

- **稀疏状态读取**（「读到无值的 key 时返回什么」· C4）—— 属 **B5F2**；
  本 feature 只负责**如实表达**「有值 / 无值」（提示词 §7 口径提醒）。
- **调度循环 / super-step**（含「一个 super-step 内多次写入如何合并」的落地）—— 属 **B7F1**；
  本 feature 只交付**通道侧**的多值冲突判定与清空操作。
- **`StateGraph` 构建器**（把映射规则接进建图 API）—— 属 **B6F1**。
- **checkpoint 写入 / 通道复制（`copy` / `checkpoint` / `from_checkpoint`）** —— 属 **B14F1**。
- **`Topic` / `Barrier` / `AnyValue` / `NamedBarrierValue` 等其它通道类型** —— v1.0 只需三类。
- **`add_messages` 等 LangChain 特有归约器** —— 属 freechain 层。
- **`Overwrite` 旁路值**（上游 `binop.py:31-51` 的单值覆盖旁路）—— 不在最小契约 C1–C27 内。
- **通道注解形态**（`Annotated[T, SomeChannel]` 的通道注入）—— 属 LangGraph 特有机制，v1.0 不支持
  （B4F1 裁定 13）。
- **节点入参的组装**（哪些 key 进节点入参）—— 属 **B5F2**（C4）。
- **兼容矩阵的新增行** —— 本 feature **零新增公开 API** ⇒ 兼容矩阵**零新增行**
  （须在人工验证记录中明确记「无新增」以区别于「漏更新」）。
- **CI 流水线的挂载** —— 归 **B3F1**（既有门禁 G1–G30）；本 feature 只交付 pytest 断言。
- **第三方依赖的引入** —— 本 feature MUST **零新增**（含 `pydantic` / `typing_extensions` / `langgraph`）。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001（验收判据 A2）**：无归约器通道连续两次写入（**两次独立的写入调用**）后，
  读取结果 == **最后一次**写入值的命中率 == **100%**；该通道的归约器**调用次数 == 0**
  （「无归约器 ⇒ 覆盖」不得走归约路径）。
- **SC-002（验收判据 A1）**：归约型通道写入序列的结果 == `operator.add` 对同一序列的**逐次归约**结果，
  **逐元素相等**的命中率 == **100%**；对照基准 MUST 用 `operator.add` 本身，MUST NOT 用
  「与上游实时对照」代替（上游不进本 feature 的 CI · 沿用 B4F1 澄清 Q5 的口径）。
  > **📌 折叠起点（澄清轮 Q6）**：基准 MUST 是「**从通道初始值（推导出的空值）起逐次折叠**」——
  > 即 `reducer(reducer(空值, v1), v2)`，与上游 `binop.py:143` 的 `operator(current, new)`
  > **逐字同构**（`current` = 写入前的通道值，首次即空值）。
  > 提示词 A1 的字面写法「`operator.add(first, second)`」在 `operator.add` + 列表这一**具体用例**里
  > 与它**结果相同**（元素相同）⇒ 两者**不冲突**；但对 `max` / `mul` 这类与「空值折叠」不等价的归约器
  > **会分叉** ⇒ MUST NOT 把「从首值起折」当作基准。
- **SC-003（验收判据 A3）**：路由通道清空后：「有值」判定为真的次数 == **0**、
  读取返回上一次值的次数 == **0**、读取返回 `None` 冒充有值的次数 == **0**
  （MUST 抛通道空错误）；清空后再写入 ⇒ 恢复「有值」且新值 == 刚写入的值（命中率 == **100%**）。
- **SC-004**：通道的「有值 / 无值」判定 **100% 可判定**，**不存在第三种模糊状态** ——
  ① **覆盖型 / 路由型**通道的三种输入（从未写入 / 写入 `None` / 写入非 `None`）的判定结果 MUST 分别为
     「无值 / 有值 / 有值」，读取行为 MUST 分别为「抛错 / 返回 `None` / 返回该值」；
  ② **归约型**通道的「从未写入」MUST 按 FR-006 / FR-022 走（**自始「有值」**，值为空值）——
     「无值」与「值为 `None`」被混判的次数 == **0**；
  ③ **清空后**的通道 MUST 一律判定为「无值」（**含归约型通道** —— 清空 ≠ 回到初始状态 · FR-022 ③）。
- **SC-005**：三类通道的实现对 `langchain*` / `langsmith` / `langgraph*` / `pydantic` /
  `typing_extensions` 的**引用数 == 0**；导入 **`freegraph.runtime`**（L2 入口 · **逐字冻结**）后，
  `sys.modules` 增量中
  **非标准库**条目数 == **0**（「非标准库」口径 = 不在 `sys.stdlib_module_names` 中且不是 freegraph
  自身模块）；**环境变量读取次数 == 0**；**出站连接次数 == 0**。
- **SC-006**：一步内多值写入的处置 —— `LastValue` / `EphemeralValue` **抛错率 == 100%**，
  「静默取末值」的次数 == **0**；`BinaryOperatorAggregate` 对同一批值的归约结果
  == 逐个归约结果（逐元素相等）；归约器抛错时「通道值被改变」的次数 == **0**。
- **SC-007**：空值推导的正确率 == **100%**，覆盖面至少含 6 类：
  `list → []` · `int → 0` · `str → ""` · `dict → {}` ·
  `collections.abc.Sequence → []`（抽象容器映射）· **不可实例化类型 ⇒ 初始「无值」且首次写入
  直存新值（**单值**写入时归约器调用次数 == **0**）**；
  另：**两个同类型归约型通道的空值 MUST 是不同对象**（共享次数 == 0）——
  一个通道的归约 MUST NOT 污染另一个（FR-006 ④）。
- **SC-008**：schema → 通道映射的正确率 == **100%**（含「有归约器 ⇒ 归约型通道」·
  「无归约器 ⇒ 覆盖型通道」· 「路由通道 ⇒ 路由型通道」三类各 ≥ 1 例）；
  映射产出的通道数 == schema 的 key 数；映射顺序与 schema 的 key 顺序**一致**的命中率 == **100%**；
  归约器的**引用保持率 == 100%**（`channel.reducer is operator.add`）。
- **SC-009**：通道纯净性 —— 「持有」MUST 写死为**两个**可判定口径（澄清轮 **Q15**）：
  ① **公开**属性（4 个 `property`）的集合 MUST **恰为** {`key`, `value_type`, `value`, `reducer`}
     （MUST NOT 以 `dir()` 全集判定 —— 实现用 `__slots__` 私有槽）；
  ② **实例槽位**的集合 MUST ⊆ {`_key`, `_value_type`, `_value`, `_reducer`}（私有实现细节 · 名字逐字冻结）；
  持有节点 / 图结构 / 运行配置 / 时钟 / 句柄 / 锁的通道数 == **0**。
- **SC-010**：归约器的**引用保持率 == 100%**（MUST NOT 被包装 / 复制 / 部分应用）。
- **SC-011**：本 feature 新增代码的 import 图中，**L2 → L3 / L4 / L5 的边数 == 0**
  （层注册表**零改动**）；新增源文件的**署名头覆盖率 == 100%**。
- **SC-012**：本 feature **零新增公开 API** ⇒ 契约层公开符号面仍**恰为 18 个**、门面仍**恰为 7 个**；
  兼容矩阵**新增行数 == 0**（并在人工验证记录中显式记「无新增」）。
  （「公开面」的判定口径沿用 B4F1 裁定 6 ③ —— `freegraph.runtime` 的导出属 **L2 内部 API**，
  **不进**兼容矩阵。）
- **SC-013**：人工验证记录**存在**且五段式小节齐全（环境 / 步骤 / 实际输出 / 结论 / 遗留问题），
  **A1–A3 逐条有结论**；来源覆盖表对**全部**判据的覆盖率 == **100%**（无来源项数 == 0）。
- **SC-014**：三类通道的语义与上游的对应关系 MUST 逐条标注源码行号 ——
  缺标注的语义条目数 == **0**（覆盖语义 / 一步内多值冲突 / 空值推导 / 首次写入的 `current` /
  清空语义 / 有值无值判定 **六类**，逐条标注 `路径:行号` + 核实版本）。
- **SC-015**：**本 feature 新增/修改的代码**（`channel.py` / `mapping.py` 全文 + `errors.py` / `__init__.py`
  的**新增部分**）的**行覆盖 == 100%** 且**分支覆盖 == 100%**（覆盖率实测输出 MUST 记入人工验证记录
  的第 3 节「实际输出」；MUST NOT 把覆盖率工具写进仓库依赖声明 —— v1.0 依赖面为零）。
  > **📌 口径边界（澄清轮 Q14）**：`src/freegraph/runtime/` **整包**的覆盖率 MUST **一并记录**，
  > 但 MUST **NOT** 作为本 feature 的**阻断判据** ——
  > B4F1 的既有模块（`schema.py` / `reducer.py` / `errors.py`）**从未设过覆盖率判据**、无 100% 基线
  > ⇒ 本 feature MUST **NOT** 承担其历史债。
- **SC-016**：负向用例的存在性与全绿 —— 「一步内多值冲突」·「读取无值通道」·「归约器抛错」·
  「空值推导失败」四类负向用例 MUST 存在且全绿（每类 ≥ 1 例），每例 MUST 断言**显式失败**
  （MUST NOT 断言「静默通过」）。
- **SC-017**：可替换性 —— 用**只依赖通道抽象**的自定义通道子类实现，MUST 能在**不改动**抽象与既有三类
  通道的前提下被创建 / 写入 / 读取 / 清空（用例全绿）⇒ 抽象**真的**是可替换的实现单元。
- **SC-018**：两个错误类型的**捕获成功率 == 100%**（`except FreegraphError` 均可捕获）；
  结构化字段齐备率 == **100%**（`EmptyChannelError` 带 `key`；`InvalidChannelUpdateError` 带
  `key` / `received_count` / `expected_count`，且 `expected_count` == **1**）；
  错误对象携带**用户写入的值**的次数 == **0**（澄清轮 Q7）。
- **SC-019（跨 feature 的名字面 · 澄清轮 Q4）**：本 feature 冻结的**名字面**逐字一致率 == **100%** ——
  四个操作名（`update` / `get` / `is_available` / `clear`）· 四个属性名
  （`key` / `value_type` / `value` / `reducer`）· 四个类名（`Channel` / `LastValue` /
  `BinaryOperatorAggregate` / `EphemeralValue`）· 两个映射入口名
  （`build_channel` / `build_channels`）· 两个错误类型名（`EmptyChannelError` /
  `InvalidChannelUpdateError`）；「下游 feature 能按本 spec 的名字直接 import 并调用」的用例 MUST 全绿
  （至少覆盖：按冻结构造签名建通道 · 读 `key` / `value_type` / `value` / `reducer` ·
  经 `build_channel` / `build_channels` 拿到通道）。
  > **📌 口径**：这些名字属 **L2 内部 API**（`freegraph.runtime`）⇒ **不进**兼容矩阵、
  > **不计入** SC-012 的「公开面」统计（与 B4F1 裁定 6 ③ 同一口径）。
- **SC-020（`update()` 返回值口径 · 澄清轮 Q5）**：写入操作的返回值 MUST 表示「**本次调用是否写入了值**」，
  断言 MUST 覆盖三种情形且逐条成立 —— ① 写入序列**非空** ⇒ 返回**真**
  （含「归约后新值与旧值**逐字相等**」的情形）；② 写入序列**为空** ⇒ 返回**假**且通道值不变；
  ③ 一步内多值冲突而**显式失败**时 MUST **抛出**错误（MUST NOT 以返回值「假」代替失败）。
  「返回值被误读为『值是否变化』」的用例数 == **0**。
- **SC-021（A1 的折叠基准 · 澄清轮 Q6）**：A1 的对照基准 MUST 为「**从通道初始值起逐次折叠**」；
  用例 MUST 覆盖**两类归约器**并逐条成立 ——
  ① **与空值折叠等价**的归约器（如 `operator.add` + 列表）：通道结果 ==
     `reducer(reducer(空值, v1), v2)`，且与「从首值起折」的写法**结果相同**（二者不冲突）；
  ② **与空值折叠不等价**的归约器（如 `max`）：通道结果 == `reducer(reducer(空值, v1), v2)`，
     且与「从首值起折」的结果**允许不同**（此时 MUST 以**空值起折**为准）。
  「以『从首值起折』为基准而误判失败」的用例数 == **0**。
- **SC-022（规模口径 · 澄清轮 Q8 / Q15）**：① 持有**其它通道 / 状态表**引用的通道数 == **0**（⇒ 结构上无法遍历全体 key）；② 「schema 有 N 个 key」（N ≥ 100）与「schema 只有 1 个 key」两种情形下，**单通道**的写入 / 读取 / 清空所触及的状态条目数 MUST **相同**（差异 == 0）；③ 该判定 MUST 以**计数探针**实现 —— 探针口径 **逐字冻结** = `len(gc.get_referents(channel))`（通道的**直接引用**对象数 · research D-12），MUST **NOT** 以**墙钟耗时**实现（否则 CI 假红），MUST **NOT** 数「执行了多少行」（耦合实现细节）。
  > **📌 ① 的可判定形式（澄清轮 Q15 补 · research D-17）**：计数探针**只能**证明「引用数不随 key 数增长」，
  > **检不出**「引用了整张状态表但计数恒定」的情形（实测：持有整张 `dict` 的通道在 N=1 与 N=1000 时
  > 计数**同为 6** ⇒ 计数相等**不**蕴含「未持有状态表」）⇒ ① MUST 另以**引用类型白名单**判定 ——
  > 通道的直接引用集合中 MUST **不出现** `dict` / `SchemaSpec` / 其它 `Channel` 实例
  > （⇒ 结构上不可能遍历全体 key）· **计数相等**降为**辅助**判据（守住「不随 key 数增长」这一较弱命题）。
- **SC-023（初始状态 · 三档 · 澄清轮 Q9）**：三类通道的**初始状态**逐条成立，命中率 == **100%** ——
  ① 覆盖型 / 路由型通道构造后 `is_available()` 为假、`get()` 抛 `EmptyChannelError`；
  ② 归约型通道构造后 `is_available()` 为真、其值 == 推导出的**空值**；
  ③ 值类型**不可实例化**的归约型通道构造后 `is_available()` 为假；
  ④ 三类通道 `clear()` 之后 `is_available()` **一律**为假（**含归约型**），
     且归约型通道清空后的值 **NOT** 等于其初始空值（清空 ≠ 回到初始状态）。
- **SC-024（写入权限与并发 · 澄清轮 Q10）**：① 通道实例持有**锁 / 同步原语**的数量 == **0**
  （不承诺线程安全 ⇒ 不引入同步原语）；② 通道对外**不提供**任何绕过 `update()` 的写入入口
  （写入入口的条数 == 1 · 且只能经由 `update()`）；③ 通道 MUST **NOT** 出现在契约层 18 符号面 /
  门面 7 符号面（⇒ 用户拿不到通道对象，「直接写通道」在公开面上不可达）。
- **SC-025（值的引用语义 · 澄清轮 Q11）**：① 写入一个对象后，通道持有的值 MUST 与传入对象
  **是同一个对象**（身份判定 `is`）—— 复制次数 == **0**；② 归约型通道写入后，通道持有的值 MUST
  与**归约器的返回值**是同一对象（身份判定）；③ 写入一个**不可拷贝**的对象
  （如持有不可拷贝成员的自定义类）MUST **不抛错**（深拷贝失败模式出现次数 == **0**）；
  ④ 通道 MUST **NOT** 因写入值的类型与 `value_type` 不符而抛错（类型校验次数 == **0**）。
- **SC-026（构造期校验 · 澄清轮 Q12）**：① 归约器**不是可调用对象**时构造 MUST 抛
  **内置 `TypeError`**（抛错率 == 100%，且错误 MUST 在**构造点**抛出、MUST NOT 拖到写入时）；
  ② 「标注有归约器但归约器为空」时构造 MUST 抛**内置 `ValueError`**（抛错率 == 100%）；
  ③ 通道层执行**二元性校验**的次数 == **0**（归约器不是二元函数时，MUST **NOT** 在构造期报错 ——
     该判定属 B4F1）；④ 本 feature **新增**的 L2 错误类型数 == **2**
  （`EmptyChannelError` / `InvalidChannelUpdateError` —— 构造期校验**不新增**错误类型）。
- **SC-027（独立验收脚本 · 澄清轮 Q13）**：`harness/verification/B5F1/acceptance.py` MUST **存在**
  且可运行；其断言**全绿**（失败断言数 == 0）；`--record` 产出的片段 MUST 含**五段式**小节
  （环境 / 步骤 / 实际输出 / 结论 / 遗留问题）；脚本 MUST **零第三方依赖**
  （其 import 中非标准库且非 freegraph 自身的条目数 == 0）。

- **SC-028（参数化组合 · 立项书 S5 ③）**：FR-027 的参数化组合测试 MUST 存在且全绿 ——
  枚举的**组合数 ≥ 12**（断言 == 100% 覆盖 FR-027 列出的 3 × 3 归约器 / 通道维度）·
  **被 `skip` / `xfail` 掩盖的组合数 == 0** · 四条语义（末值覆盖 / 从初始值起归约 / 清空后无值 /
  一步内多值显式失败）在**所有组合**下**同时**成立（逐组合断言 == 100%）。

---

## Assumptions

- **权威顺序**：宪法 > 立项书 > 本 feature 提示词初稿 > 仓库现状。
  本 spec 的裁定 1–16 即按此顺序解决引文与上位文档的冲突；引文的原文本（如 FR-001 的
  「get / read」）**保留在裁定记录中**以便追溯，但**不构成规范**。
- **规模参考**：1,060 行（实现 520 / 测试 540）· 3 人日（引文表格值，作为 plan 的输入而非本 spec 的约束）。
- **spec 目录命名**：沿用仓库既有的「**feature ID 前缀**」约定（`specs/b5f1-channels`），
  与 `harness/features/B5F1_*.md` / `harness/verification/B5F1/` 的 feature ID 对齐 ——
  `.specify/init-options.json` 的 `feature_numbering: sequential` 通用算法在本仓库**未被使用**
  （既有 5 个 spec 目录均无数字前缀）⇒ **显式偏离记录**（口径：仓库一致性优先）。
- **分支**：本仓库**无** `.specify/extensions.yml` ⇒ 无 `before_specify` 钩子 ⇒ 本次**不创建 git 分支**；
  与 B1F1 / B2F1 / B2F2 / B3F1 / B4F1 一致（均在 `main` 上提交）。
- **Python 基线**：`>= 3.11`；typing 构件上限 = **3.11**
  （3.12+ 构件如 `TypeAliasType` / `override` / `ReadOnly` / `TypeIs` / PEP 695 `type` 语句禁用）。
- **内核依赖面**：**零第三方依赖**；`typing_extensions` **不在**内核依赖面；
  `langgraph` **仅本机参考读物 / 对照工具**（**不写进仓库**、**不进 CI** —— 沿用 B4F1 澄清 Q5 的口径）。
  核实环境 = **`langgraph 1.2.11`**（实测于 CPython 3.12.3，路径
  `…/site-packages/langgraph/channels/`）。
- **上游行号的引用纪律**：换版本后 MUST 重新核实，MUST NOT 凭记忆沿用（宪法原则 VIII · FR-021）。
- **代码落位**：L2 = `src/freegraph/runtime/`（层注册表**已登记**）⇒ 层注册表零改动；
  具体的模块划分（B4F1 已用 `schema.py` / `reducer.py` / `errors.py`）由 plan 定。
- **通道类的命名**：`Channel`（抽象）/ `LastValue` / `BinaryOperatorAggregate` / `EphemeralValue` ——
  **已在本 spec 冻结**（裁定 1 · FR-001）；具体构造签名与实现形态由 plan 定。
- **值的类型校验**：通道 MUST **NOT** 校验写入值的类型（值类型只用于**推导空值**）⇒
  类型不匹配的处置属运行期（`B7F1` 之后的调度层 / `B7F3` 的入参校验）。
- **既有冻结面零改动**：契约层 18 符号面（B1F1 / B2F1）、门面 7 符号面（B2F2）、
  层注册表（B3F1）—— 本 feature **一字不动**。
- **人工验证记录**：采用仓库既有的**五段式** + **来源覆盖表**（宪法原则 V / VIII）；
  未实跑的项 MUST 显式记入「遗留问题」（MUST NOT 伪造输出）。
- **覆盖率取证**：v1.0 依赖面为零 ⇒ 覆盖率工具**不进仓库依赖**；实测输出记入人工验证记录即可。
- **前置依赖**：**B4F1**（通道规格 `ChannelSpec` / `SchemaSpec` 的字段名已冻结）·
  **后续解锁**：**B5F2**（稀疏状态读取 · C4 回归测试落点）→ **B7F1**（调度循环）→ **B8F1**（条件边路由）。

---

## 依据

- 立项书 §5.1（分层 · **ARCH-1** 依赖方向铁律）· §5.2（**B5F1 行**：L2 执行内核层 / M1 /
  前置 B4F1 / 1,060 行 / 3 人日 / 小目标「归约器 `operator(current, new)` 语义一致；无归约器 key 被覆盖」）
  · §5.3（**C1** 状态 schema / **C2** 归约器机制 / **C3** 默认归约语义 / **C4** 稀疏状态 /
  **C7** 路由函数契约 / **C8** 条件边读状态）· §5.4（协议纪律）· **D15**（v1.0 依赖面为零 ⇒
  通道语义**降级为标准库 / 自研替代**）。
- 契约权威：`harness/reports/Q8-图运行时最小契约.md` §3.4 契约清单
  **C1**（每个 key 映射到一个 channel）· **C2**（`reducer(current, new)` · 恰好 2 个位置参数）·
  **C3**（无 reducer → 覆盖，左值丢弃）· **C4**（节点入参只含有值的 key）·
  **C7**（路由函数契约）· **C8**（条件边读 fresh 状态）；
  §3.2.1（归约器提取机制 · 默认归约器 = 覆盖 · `operator(current, new)` 调用语义）。
- 源码参照（**核实环境：`langgraph 1.2.11`**，实测于 CPython 3.12.3）：
  `langgraph/channels/base.py:19-121`（`BaseChannel` 抽象面：`update` / `get` / `is_available` /
  `checkpoint` / `from_checkpoint` / `copy` / `consume` / `finish`）·
  `langgraph/channels/last_value.py:20-78`（`LastValue`：初始 `MISSING` `:27-29` ·
  **一步内多值报错** `:56-67` · `get` 无值抛错 `:69-72` · `is_available` `:74-75`）·
  `langgraph/channels/binop.py:65-155`（`BinaryOperatorAggregate`：**空值推导**（抽象容器映射
  `:83-88` · `try: typ() except → MISSING` `:89-92`）· **首次写入直存 + 逐个归约** `:123-144` ·
  `get` / `is_available` `:146-152`）·
  `langgraph/channels/ephemeral_value.py:15-79`（`EphemeralValue`：**一步内多值报错（guard）**
  `:62-65` · **步末清空**（`update(空序列)`）`:55-60` · `get` / `is_available` `:70-76`）·
  `langgraph/graph/state.py:1850-1873`（`_get_channel`：先剥 `Required` / `NotRequired` →
  有归约器走 BinOp → 否则 `LastValue` 兜底 `:1871-1873`）·
  `langgraph/pregel/_algo.py:317-320`（把本步写入**批量**交给 `channel.update(vals)`）·
  `:326-334`（对本步未更新的通道调用 `update(空序列)` ⇒ `EphemeralValue` 被清空）·
  `langgraph/pregel/_io.py:38-53`（`read_channels`：捕获 `EmptyChannelError` 即跳过 ⇒
  **C4 稀疏入参的判定口径**）·
  `langgraph/checkpoint/base/__init__.py:745-749`（`EmptyChannelError` 定义）。
- 宪法 `.specify/memory/constitution.md`：**原则 I**（零环境变量 · 零出站）·
  **原则 II**（内核纯净 · 「状态 schema 使用标准 `Annotated` + 归约器表达」·
  「状态语义 MUST 与 LangGraph 行为等价」· C4 / C8 须有独立回归测试）·
  **原则 III**（验收契约优先 · `target.py` 是**只读**基准）·
  **原则 V**（人工验收是最终验收标准 · 五段式）· **原则 VI**（规格驱动开发）·
  **原则 VII**（职责边界 · C1–C27 契约清单为唯一权威）·
  **原则 VIII**（证据与术语纪律 · `本地路径:行号` 标注）·
  **原则 X**（兼容矩阵 + 署名头 + `THIRD_PARTY_NOTICES`）·
  「依赖白名单 / 黑名单」（**包层白名单 v1.7.0** · v1.0 零第三方依赖 · 核心层黑名单）·
  「运行时环境基线」（**最低版本 3.11 / typing 构件上限 3.11**）·「质量门禁」七项。
- 前置 feature 规格与契约：`specs/b4f1-schema-reducer-parse/spec.md`（`ChannelSpec` 六个字段名的
  逐字冻结 · FR-020 · 裁定 2 / 6 / 14）· `specs/b4f1-schema-reducer-parse/contracts/binary-criterion.md`
  （二元性判据的**唯一权威** —— 本 feature MUST NOT 另立判据）·
  `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md`（**`src/freegraph/runtime/` = L2** ·
  本 feature 零改动）· `specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md`（G1–G30）。
- 验收契约（**只读**）：`harness/demo/target.py:59-61`
  （`messages: Annotated[list[AnyMessage], operator.add]` · `llm_calls: int`）·
  `target.py:81`（`state.get('llm_calls', 0)`）·
  Q8 契约 C4 行的实测证据「`NODE_INPUT_KEYS: ['messages']`」
  ⇒ **BinOp 通道自始「有值」（空列表）、LastValue 通道自始「无值」** —— Q2 / 裁定 4 的实测依据。
- 本 feature 提示词初稿：`harness/features/B5F1_Channel抽象与三类通道.md`。
