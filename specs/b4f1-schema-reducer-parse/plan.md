# Implementation Plan: B4F1 · 状态 schema 解析 + 归约器提取（`TypedDict` + `Annotated` → 通道规格）

**Branch**: `b4f1-schema-reducer-parse` | **Date**: 2026-11-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/b4f1-schema-reducer-parse/spec.md`

**feature ID**: `B4F1`（**M1 运行时内核**的第 5 个 feature · 前置 **B2F2** · 后续解锁 **B5F1**）

---

## Summary

把用户写的**标准 `TypedDict` 状态 schema** 翻译成**通道规格集**：schema 的**每一个 key** 产出一条
`ChannelSpec`（key / 类型 / 归约器引用 / 有无归约器 / 语义标记 / 必选标记），并从 `Annotated`
的**末位元数据**中提取**二元归约器**（`reducer(current, new) -> value`）。

技术方案（全部**标准库**，零第三方依赖）：

| 环节 | 手段 | 依据 |
|---|---|---|
| 注解解析 | `typing.get_type_hints(schema, include_extras=True)` —— **保留 PEP 593 元数据** | spec FR-009 / 裁定 5 |
| `Required` / `NotRequired` 剥离 | 检查 `annotation.__origin__ in (Required, NotRequired)` → 取 `__args__[0]` | spec FR-008 / 裁定 4 |
| 归约器提取 | `typ.__metadata__[-1]` + `callable(...)` | spec FR-003 |
| 二元性判定 | `inspect.signature(...)` 的**位置专用 + 位置或关键字**参数计数 **== 2** | spec FR-004 / 裁定 9 |
| 产物形态 | `@dataclass(frozen=True, slots=True, kw_only=True)` + `types.MappingProxyType` | research D-01 / D-02 |
| 错误 | L2 的 `InvalidSchemaError`（结构化字段 `key` + `reason`，继承 `FreegraphError` + `ValueError`） | spec FR-007 ⑤⑥ / 裁定 2 |

**零新增依赖、零新增公开 API、零新增门禁编号**：
契约层 18 符号面与门面 7 符号面**一字不动**（G7 / G15 / G19 恒成立）；
`langgraph` **不写进任何依赖声明、CI 也不装**（澄清 Q5）⇒ A2 的判据由**自包含判定表**承载。

**五处「实测发现的、与引文直觉不一致」的事实**（详见 [research.md](./research.md)）：

1. **`typing.is_typeddict` 认不出 `typing_extensions.TypedDict`**（实测 CPython 3.11.16 +
   typing_extensions 4.16.0 ⇒ 返回 `False`）⇒ 判定 MUST 用**鸭子口径**
   （「类 + `dict` 子类 + 有 `__annotations__` + 有 `__total__`」）——
   否则 `harness/demo/target.py:59-61` 的 schema 会被判为「非 TypedDict」。
2. **`Required[Annotated[list, operator.add]]` 的 `__metadata__` 不在顶层**（实测为 `None`）
   ⇒ 不先剥离包装就**必然漏掉**归约器。
3. **类（`__init__` 恰 2 参）会被机械判据接受为归约器**（实测 `signature` = `(a, b)`）⇒
   裁定 9 已在澄清 Q6 中改写为「**不特殊处理**」——**与上游同构**。
4. **`str(int)` == `"<class 'int'>"`**（实测）⇒ 「类型的可读文本」**不能**直接用 `str()`
   ⇒ 规范化口径见 research D-05。
5. **未来注解（`from __future__ import annotations`）下 TypedDict 识别不出 `Required` / `NotRequired`**
   （实测 3.11 / 3.12 一致 ⇒ 全部记为「必选」）⇒ 必填性标记 MUST **照抄**、MUST NOT 自造判定逻辑。

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（`pyproject.toml` 的 `requires-python = ">=3.11"`）；
**typing 构件上限 = 3.11**（宪法「运行时环境基线」）——本 feature 用到的 typing 构件**全部 ≤ 3.11**：
`Required` / `NotRequired`（PEP 655 · 3.11）· `get_type_hints(include_extras=…)` ·
`Annotated`（PEP 593）· `dataclass(frozen=True, slots=True, kw_only=True)`（3.10+）。
**MUST NOT** 使用 `TypeAliasType`(3.12) / `override`(3.12) / `ReadOnly`(3.13) / `TypeIs`(3.13)
或 PEP 695 `type` 语句。**主判定 = CI 矩阵最低档 3.11 跑全量测试**（含本 feature 的新测试目录）。

**Primary Dependencies**: **运行时零第三方依赖**（`dependencies = []` · 沿用现状）。
**开发期**：`pytest`（既有 `[dependency-groups] dev`）—— **零新增**。
**本 feature MUST NOT 把 `langgraph` 写进任何依赖声明**（澄清 Q5）⇒ 判定表是上游行为的
**固化快照**；上游在场时的实时对照留给 **B5F2 / B8F1** 的差分夹具。

**Storage**: N/A —— 本 feature 无运行时持久化。
**仓库内的权威工件** = **纯文本 Markdown 契约**（`contracts/binary-criterion.md` 的判定表），
入库比对（沿用 B3F1 的层注册表先例：机器可读 Markdown + `<!-- authority: yes -->` 标记）。

**Testing**: pytest + 标准库 `typing` / `inspect` / `dataclasses` / `types` / `subprocess`。
**需要子进程的断言**（SC-007 的「解析前后 `sys.modules` 增量 == 0」·「环境变量读取次数 == 0」·
「出站连接次数 == 0」）**必须在子进程中执行** —— 测试进程自身已导入 pytest，
同进程 `sys.modules` 不可用（沿用 B1F1 / B3F1 的既有口径）。

**Target Platform**: 任意 CPython 3.11+ 平台（Linux / macOS / Windows）。
CI 的 `testpaths = ["tests"]` ⇒ 新增 `tests/runtime/` **自动被收集**，**CI 配置零改动**。

**Project Type**: library（Python 库；发行名 = 导入名 = `freegraph`；D1 决议：不拆独立发行包）。

**Performance Goals**: **N/A（不设预算）** —— 解析是**纯计算**（无 I/O、无网络、无锁），
输入规模是「一个 schema 的若干个 key」（典型 2–20 个）⇒ 无热路径。
**登记**：spec 的 Deferred 项「新增模块的导入开销预算」**不在本 feature 立项**
（`src/freegraph/runtime/` 只在 `import freegraph.runtime` 时加载；顶层包惰性由 G1 保证 ⇒
`import freegraph` 的开销**不变**）⇒ 若要立预算，归 **B5F1**（与通道实现一起测）。

**Constraints**（**主要**来自 spec 的 MUST 条目；未逐条列出的 FR 见 `tasks.md` 的追溯表）：

| 约束 | spec 条目 |
|---|---|
| 只依赖**标准库**；MUST NOT import `langchain*` / `langgraph*` / `langsmith` / `pydantic` / `typing_extensions` | FR-001 ② · FR-013 |
| `TypedDict` 判定 MUST 用**鸭子口径** ⇒ `typing_extensions.TypedDict` 的 schema MUST 被**接受**（验收基准同构形态） | FR-001 ① · SC-018 |
| MUST NOT 读取**任何**环境变量；零出站；零文件 I/O | FR-013 |
| 归约器**恰好 2 个位置参数**（`*args` / `**kwargs` / keyword-only **不计入**） | FR-004 |
| 非二元 callable ⇒ **显式失败**，MUST NOT 静默降级为「覆盖」 | FR-007 ② · SC-003 |
| 错误**快速失败**（只报第一个问题）+ **结构化字段**（`key` + 封闭取值域的 `reason`） | FR-007 ④⑥ · SC-006 · SC-017 |
| 归约器**按引用**持有（MUST NOT 包装 / 复制） | FR-012 · SC-009 |
| 解析结果**不可变**的纯数据；**可 JSON 序列化**的投影；投影 MUST NOT 含内存地址 | FR-010 · FR-011 · SC-005 |
| 必填性**只记录不执行**（校验归 B7F3） | FR-021 · SC-016 |
| 判定表 MUST 覆盖 **16 类二元性形态 + 2 类提取形态**（≥ 14 为覆盖面下限），每条带上游 `路径:行号` | FR-016 ①-a·①-b · SC-004 |
| **零新增依赖声明**（运行时 / 发行元数据 / 开发期依赖组三处）；CI MUST NOT 装 `langgraph` | FR-016 ②③ · FR-019 |
| L2 MUST 只向下依赖 L1；MUST NOT import L3/L4/L5；**层注册表零改动** | FR-014 · SC-012 |
| 零新增公开 API（契约层 **18** 个 / 门面 **7** 个） | FR-015 · SC-015 |
| 新建源文件 MUST 带**署名头**且 docstring 为首个语句 | FR-019 · SC-012 |
| 人工验证记录（五段式 + 来源覆盖表）落 `harness/verification/B4F1/` | FR-018 · SC-013 |

**Scale/Scope**: 一个 schema 的 **key 数**：典型 **2–20**（`target.py` = 2 个；`StateGraph` 的
用户 schema 常见 3–10 个）。**实现 ≈ 480 行 / 测试 ≈ 460 行**（立项书 §5.2 的估算，作为 plan 的输入）。
本 feature **零新增公开 API** ⇒ 兼容矩阵**零新增行**。

**投影的「类型可读文本」口径**（spec Assumptions 明写「由 plan 定」⇒ 落定于此 · research **D-05**）：
`value_type` 的可读文本 = ① `isinstance(value_type, type)` ⇒ 取 `value_type.__name__`（`int` / `MyState`）；
② 否则 ⇒ `str(value_type).replace("typing.", "")`（`list[int]` → `"list[int]"` · `typing.List[str]` → `"List[str]"`）。
⚠️ 该口径 MUST **稳定且确定性**（同一 schema 两次投影逐字一致 · SC-005）。

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 通过项（逐条）

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| 原则 I（零 LangSmith 依赖 · 自身零出站 · 零环境变量） | FR-013 · 既有 **G24**（配置层扫描 `src/freegraph/**`）· **G26**（网络静态扫描）· **G27**（零出站动态） | ✅ |
| 原则 II（内核纯净 · **不自带并行状态类型体系**） | FR-001（只用**标准** `TypedDict`）· FR-013 · **G21 / G22**（依赖黑名单 + 隔离环境 `sys.modules`） | ✅ |
| 原则 III（验收契约优先 · `target.py` 只读） | 本 feature **零改动** `target.py`；其 schema（`typing_extensions.TypedDict` + `Annotated[list[AnyMessage], operator.add]`）**必须可解析** ⇒ 裁定 3 的鸭子判定 | ✅ |
| 原则 IV（可诊断性） | N/A（本 feature **无运行期可观测面**；诊断靠 FR-007 的结构化错误字段） | ✅ 边界内 |
| 原则 V（人工验收是最终验收标准） | FR-018（`harness/verification/B4F1/manual-verification.md` · 五段式 + 来源覆盖表） | ⚠️ **门禁 5 的「真实模型一轮」不适用** ⇒ 见**登记项 R-1** |
| 原则 VI（规格驱动 · tasks 可逐条勾选） | 本 plan + `tasks.md`（含 FR ↔ SC 追溯表） | ✅ |
| 原则 VII（职责边界与内核契约 C1–C27） | FR-002 / FR-003 / FR-006 = **C1 / C2 / C3** 的解析侧落地；C4 / C8 的**执行**侧归 B5F2 / B8F1 | ⚠️ **门禁 3 的 C4 / C8 两条独立回归**不在本 feature ⇒ 见**登记项 R-1** |
| 原则 VIII（证据与术语纪律） | `research.md` 每条结论附**实测命令 + 输出**；上游引用标 `路径:行号` + 核实版本 `langgraph 1.2.11` | ✅ |
| 原则 IX（许可证与商标红线 · NON-NEGOTIABLE） | **零新增依赖**（FR-019）⇒ `THIRD_PARTY_NOTICES` 无需变更；**零品牌资产** | ✅ |
| 原则 X（文档合规 + 源文件署名头） | FR-019（署名头 · 既有 **G30** 全仓扫描自动覆盖新文件）· 兼容矩阵**零新增行**（须在人工记录中显式记「无新增」） | ✅ |
| 运行时环境基线（Python 3.11 · typing 上限 3.11） | 本 feature 只用 ≤ 3.11 构件（Technical Context 已逐项列出）· 最低档 3.11 跑全量测试 | ✅ |
| 依赖白名单 / 黑名单（包层 · 配置层 · 网络层） | 零新增依赖 ⇒ **G21 / G23 / G24 / G26 / G27** 恒绿 | ✅ |
| 质量门禁 1 / 2 / 6 / 7 | ① 规格 + tasks 可勾选 ② 依赖零新增 ⑥ 证据（research + 来源覆盖表）⑦ 文档合规（署名头 + 兼容矩阵零新增） | ✅ |
| 质量门禁 3 / 4 / 5 的**内核运行时相关部分** | ⚠️ **物理不可达成** ⇒ **登记项 R-1**（偏离登记 + 发起者追认） | ⚠️ **见 R-1** |
| 发布门禁（发行产物纯度） | 本 feature **不接入**（B24F1）· 新增代码在 `src/freegraph/` 内 ⇒ **不污染**产物纯度 | ✅ 边界内 |

### ⚠️ 登记项 R-1（宪法「质量门禁 3 / 4 / 5」的偏离登记 · 需发起者追认）

**依据**：宪法 **v1.7.0**「质量门禁的分阶段落地与发起者追认」（该条于 **v1.6.0** 引入 · **窄口径**通则 · 首次适用 = B3F1）。

| # | 被偏离的**具体门禁项** | 不可达成的根因（含里程碑依据） | 判据未被放宽的论证 | 承接方（feature ID + 里程碑） | 承接机制 |
|---|---|---|---|---|---|
| ① | **门禁 3** 的「**C4**（稀疏状态）+ **C8**（条件边 fresh 状态）两条**独立回归测试**」 | 二者都要求**通道与状态读取**存在；B4F1 属 **M1**，但通道实现归 **B5F1**、稀疏读取归 **B5F2**、fresh 读归 **B8F1**（立项书 §6.2 的 M1/M2 切分）⇒ 本 feature **按里程碑不交付其前置能力** | 本 feature 交付的是**解析侧**（C1 / C2 / C3 的事实提取）；C4 / C8 的**判据一字未改** | **B5F2**（C4 · M1）· **B8F1**（C8 · M2） | **挂载点已存在**（B3F1 落）⇒ 本 feature **零改动**该文件：`tests/contracts/test_contract_regressions.py:28-29` 的 `GATE-MOUNT: C4/C8 · status=not-landed · owner=B5F2/B8F1`（由既有门禁 **G29 ③** 逐条解析）⚠️ 本 feature **MUST NOT** 把 `status` 改成 `landed`（C4 / C8 未由本 feature 落地）⇒ 只需在**本 feature 的人工验证记录**中**再次登记 + 追认**（承接方与里程碑**未变**） |
| ② | **门禁 4** 的「**fake 模型跑通验收基线的一轮**」 | 验收基线跑通需要**完整内核运行时**（编译 + 执行），属 **B7F2 / B7F3**（M1 尾 / M2）⇒ B4F1 **无图可跑** | CI **不写**一条永久红的断言（违宪 PR-4）；本 feature 只落**挂载点**并在人工记录中标记「未落地」 | **B7F2 + B7F3**（M1 / M2） | **已就位**：B3F1 的裁定 22 已把「fake 轮」的承接条款写入 B7F2 / B7F3 的提示词初稿（`harness/features/B7F2_compile编译.md` / `B7F3_invoke返回完整状态.md`） |
| ③ | **门禁 5** + 原则 V 的「人工验证记录含**真实模型一轮**」 | 无图可跑 ⇒ 无从接真实模型 | **五段式记录 + 来源覆盖表照常落地**（FR-018）；被延后的只是「真实模型一轮」这一**部分** | **B7F3 / B25F1**（M2 / M4） | **已就位**：B25F1（双跑验收）的提示词初稿承接 fake 轮 |

**红线（未被触碰）**：依赖红线（`langsmith` / `langchain*` / `langgraph*`）· 许可证红线 · 商标红线 ·
零出站红线 —— **全部在本 feature 照常执行**（FR-013 / FR-019 + G21 / G23 / G24 / G26 / G27）。

**⇒ 请发起者在合入前追认此登记项**（落点：`tasks.md` 的一条**阻断合入**的追认任务 ·
追认文字 MUST 落在 `harness/verification/B4F1/manual-verification.md`）。

### 门禁编号纪律

**本 feature MUST NOT 新增门禁编号** —— 既有 **G1–G30** 的编号连续性是 B3F1 data-model 的不变量
（「门禁总数 == 30 · 编号连续」）⇒ 新模块由**既有门禁自动覆盖**：

| 既有门禁 | 对本 feature 的覆盖 |
|---|---|
| **G25**（导入图单向 · ARCH-1） | 新增的 `src/freegraph/runtime/**` = **L2**（层注册表已登记）⇒ 自动纳入扫描；L2 → L3/L4/L5 的边数 == 0 即 SC-012 |
| **G30**（全仓署名头） | 新建源文件的署名头覆盖率 == 100%（SC-012）⇒ **无需**扩 G5 / G20 的硬编码清单 |
| **G4 / G24 / G26 / G27** | 零环境变量 / 零出站（FR-013） |
| **G21 / G22 / G23** | 零新增依赖 ⇒ 依赖闭包 / 隔离环境 / 许可证断言恒绿；**`ci.yml` 的安装步骤亦不含 `langgraph`**（FR-016 ③ 的**第 4 处**声明位 · tasks T049） |

**⇒ 门禁编号总数仍为 30**（layer-registry.md 与 data-model 的不变量**零改动**）。

---

## Project Structure

### Documentation (this feature)

```text
specs/b4f1-schema-reducer-parse/
├── plan.md                          # This file (/speckit.plan command output)
├── research.md                      # Phase 0 output —— D-01..D-13 决策 + 实测证据 + 遗留登记
├── data-model.md                    # Phase 1 output —— 解析产物的实体模型与不变量
├── quickstart.md                    # Phase 1 output —— 可照抄的验证手册
├── spec.md                          # 规格（两轮澄清 · **14 条裁定** + 10 条澄清问答 Q1–Q10）
├── checklists/
│   └── requirements.md              # 规格质量清单（16/16）
├── contracts/
│   ├── schema-parse-contract.md     # 解析契约（输入 / 输出 / 错误 / 不变量）—— **唯一权威**
│   └── binary-criterion.md          # 二元性判据的**权威判定表**（`<!-- authority: yes -->`）
└── tasks.md                         # Phase 2 output（/speckit.tasks —— 本命令不生成）
```

### Source Code (repository root)

```text
src/freegraph/
├── __init__.py                      # 既有 · **零改动**（顶层包惰性 · G1 / L-1）
├── graph.py                         # 既有 · **零改动**（门面 7 符号面 · G15 / G19）
├── _stategraph.py                   # 既有 · **零改动**
├── _primitives.py                   # 既有 · **零改动**（L2 外壳）
├── py.typed                         # 既有 · **零改动**（PEP 561）
├── contracts/                       # L1 契约层 · **零改动**（18 符号面 · G7 / G8）
│   └── ...
└── runtime/                         # ★ 新增 —— L2 执行内核层（层注册表**已登记** · 零改动）
    ├── __init__.py                  #   包声明 + L2 内部 API 的导出（**不是**公开门面）
    ├── errors.py                    #   InvalidSchemaError（结构化字段 key + reason）
    ├── reducer.py                   #   二元性判定 + 归约器提取（_is_binary / _extract_reducer）
    └── schema.py                    #   ChannelSpec / SchemaSpec / parse_state_schema
                                     #   （+ 投影方法 `to_dict()` · FR-020 ④ 把**命名**留给 plan）

tests/
├── conftest.py                      # 既有 · **零改动**
├── contracts/                       # 既有（G1–G13）· **零改动**
├── facade/                          # 既有（G14–G20）· **零改动**
├── gates/                           # 既有（G21–G30）· **零改动**
└── runtime/                         # ★ 新增 —— 本 feature 的测试
    ├── __init__.py
    ├── conftest.py                  #   ① 子进程夹具（sys.modules 增量 / 环境变量 / 出站）
    │                                #   ② 判定表夹具（解析 binary-criterion.md + 按名字求值 §4）
    ├── test_schema_parse.py         #   解析主路径（FR-001~FR-012 · FR-021）
    ├── test_future_annotations.py   #   ★ 未来注解形态的**隔离模块**（T016 / T024 的未来注解子用例）
    ├── test_binary_criterion.py     #   判定表逐条比对（FR-016 ①-a·①-b · SC-004）
    ├── test_parse_contract.py       #   契约守卫（错误契约 / 投影 / 不可变性 · SC-005·006·017）
    └── test_typed_dict_variants.py  #   ★ `typing_extensions.TypedDict` 正面路径（SC-018）
                                     #     —— **独立文件**：避免污染 test_parse_contract.py 的
                                     #     `sys.modules` 断言（pytest 收集期即 import · SC-011）

harness/verification/B4F1/
└── manual-verification.md           # ★ 新增 —— 人工验证记录（五段式 + 来源覆盖表）
```

**Structure Decision**:

- **落 `src/freegraph/runtime/`** —— 层注册表**已登记**该路径为 **L2**（B4F1 起）⇒
  **层注册表零改动**（spec FR-014）；该目录**尚不存在**，本 feature 是它的**首次创建**。
- **四个模块的切分**（`errors` / `reducer` / `schema` / `__init__`）：
  ① `errors.py` 独立 ⇒ 错误类型**不与解析逻辑纠缠**、可被 B5F1 / B6F1 单独 import；
  ② `reducer.py` 承载**二元性判定**这一**最易写错**的判据（spec §10 风险提示）⇒ 单独成文件，
  便于判定表逐条比对测试**只针对它**；
  ③ `schema.py` 承载数据类型与解析主流程（含投影方法 `to_dict()` —— FR-020 ④ 把**命名**留给 plan，
  此处落定；契约 §3.3 与 `data-model.md` §8 已按此名引用）；
  ④ `__init__.py` 只做导出（`parse_state_schema` / `ChannelSpec` / `SchemaSpec` /
  `InvalidSchemaError`）—— **L2 内部 API**，**不是**公开门面 ⇒ 门面 7 符号面**零改动**（G15 / G19）。
  ⚠️ `src/freegraph/runtime/__init__.py` **MUST NOT** 被 `src/freegraph/__init__.py` import
  ⇒ 顶层包惰性（G1 / L-1）**恒成立**。
- **测试落 `tests/runtime/`** —— 与既有的 `tests/contracts/` · `tests/facade/` · `tests/gates/`
  **平级**（沿用仓库「一层一个测试目录 + `conftest.py` 提供夹具」惯例）；
  `pyproject.toml` 的 `testpaths = ["tests"]` ⇒ **CI 零改动**即被收集。
  ⚠️ **两个**隔离测试模块**的落位理由**（2026-11-08 分析轮）：
  ① `test_future_annotations.py` —— `from __future__ import annotations` 会让**整份文件**的注解
  变成字符串 ⇒ MUST 与其它用例**物理隔离**（tasks T016 / T024）；
  ② `test_typed_dict_variants.py` —— pytest 的**收集期**即 `import` 该模块 ⇒ 进程内 `sys.modules`
  必含 `typing_extensions` ⇒ 与 T048 的「导入后无 `typing_extensions`」断言**必须分文件**
  （否则同进程**必假红**）。
- **判定表的单一权威 = `contracts/binary-criterion.md`**（机器可读 Markdown 表格 +
  `<!-- authority: yes -->` 标记）—— 测试**解析该文件**取样（沿用 **G25 解析
  `layer-registry.md`** 的既有手法）⇒ **无双份表格**、无漂移风险。
  ⚠️ **边界**（2026-11-08 分析轮补记）：**`spec.md` FR-016 ①-a 亦只列「形态清单 + 指向本文件」**，
  **不复制表格** ⇒ 判定表在仓库内**只有一份**（权威文件 §2）；该权威文件 §5 的
  **实测取样表**是 §2 的**证据镜像**（判定权威只在 §2）。
  ⚠️ 该表**不进发行包**（在 `specs/` 下）⇒ 不污染产物纯度。
- **`InvalidSchemaError` 落 L2 而非契约层** —— 契约层 18 符号面是**冻结面**（G7）
  ⇒ 加一个错误类型会连带要改公开面文档 / 门禁 / API 快照 / 兼容矩阵；
  用户侧 `except FreegraphError` / `except ValueError` **均**可捕获（spec FR-007 ⑤）。
  ⚠️ 登记：`src/freegraph/contracts/errors.py` 的 docstring 称其为「内核异常族的**唯一定义处**」，
  但同一 docstring 也写明「后续**可新增子类**」⇒ 本 feature 在 L2 新增子类属该表述的允许范围；
  **本 feature 不改该文件**（契约层零改动）⇒ 登记为措辞口径的澄清，**不改判据**（见 research D-08）。
- **错误类型的「两条路径」分开写死**（裁定 14 · 分析轮调和澄清 **Q4** 与 **Q7**）：
  **捕获**用基类 `FreegraphError` / `ValueError` 即可（**MUST NOT** 要求用户 import 具体子类才能捕获）；
  **读结构化字段**（`key` / `reason`）时 MAY 从 **`freegraph.runtime`** import 具体子类
  —— **L2 子包** ⇒ 门面 7 符号面与契约层 18 符号面**均不变**（零冻结面变更）。
  理由：基类上没有这两个属性 ⇒ 若不给具体类型的路径，spec SC-017 的「只读结构化字段」
  在类型检查下不可用。

---

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **宪法「质量门禁 3 / 4 / 5」的三部分在本 feature 物理不可达成**（C4 回归 · C8 回归 · fake 模型轮 · 真实模型轮） | 四者**共享同一根因**：它们都要求**通道 / 状态读取 / 完整内核运行时**存在，而 B4F1 按立项书 §5.2 / §6.2 只交付**解析侧**（通道 = B5F1 · 稀疏读取 = B5F2 · fresh 读 = B8F1 · 编译与执行 = B7F2 / B7F3）⇒ **任何 spec 设计都无法在本 feature 满足这四条** ⇒ 依宪法 **v1.6.0** 的窄口径通则处置（偏离登记 + 发起者追认 + 具名承接方） | **替代方案 A：硬写进 CI**（例如让验收脚本在「无图可跑」时判通过而不登记）⇒ **静默稀释宪法** + 门禁语义被扭曲 ⇒ **不可行**。<br>**替代方案 B：写一条永久红的 CI** ⇒ 违反「feature 必须能独立通过门禁」· PR-4 ⇒ **不可行**。<br>**替代方案 C：改宪法正文**（把这几条写成「内核未落地时免检」）⇒ 违反「**MUST NOT** 以本条删改宪法正文」⇒ **不可行**。<br>**替代方案 D：把 B4F1 扩成「通道 + 读取 + 运行时」** ⇒ 越过立项书的 feature 边界（B5F1 / B5F2 / B7F2 / B7F3 各自独立立项）⇒ 规模与里程碑口径失控 ⇒ **不可行**。<br>**采用的处置**：**偏离登记（R-1）+ 发起者追认（`tasks.md` 的阻断合入任务）+ 承接条款已在目标 feature 的提示词初稿中既有**（B5F2 FR-004 · B8F1 FR-007 · B7F2 / B7F3 · B25F1）⇒ **红线判据一律不放宽**（依赖 / 许可证 / 商标 / 零出站四条红线在本 feature 照常执行）。 |
| **判定表用「机器可读 Markdown」承载，并由测试解析它**（而非 JSON / TOML / Python 常量） | ① 仓库**既有先例**：层注册表 `contracts/layer-registry.md` 就是机器可读 Markdown + `<!-- authority: yes -->` 标记，且既有门禁 **G25** 直接解析它 ⇒ **同构**、不引入第二种载体风格；② 判定表**必须带人类可读的证据**（每条形态对应上游 `路径:行号` + 中文说明）⇒ 二进制/纯数据格式承载不了「来源标注」这一半 | **替代方案 A：JSON / TOML 载体** ⇒ ① 需要**额外**维护一份「人读说明 + 来源标注」的文档 ⇒ **双份权威 ⇒ 漂移风险**；② 仓库无 JSON/TOML 契约的既有惯例（`extras-v2.toml` 是**被门禁读取的清单**，不是判据表）⇒ 引入新风格。<br>**替代方案 B：把表写成测试里的 Python 常量** ⇒ 判据与用例**同处** ⇒ 改判据会顺手改用例（**自证**）⇒ **不可行**（判据必须与实现分离）。<br>**替代方案 C：测试内联一份副本 + 契约文档一份** ⇒ **双份权威** ⇒ 迟早漂移（仓库已因「G5 / G20 署名头分两处维护」吃过这个亏）⇒ **不可行**。<br>**采用的处置**：**单一权威 + 测试解析它**（与 G25 同构）⇒ 判据与用例**天然分离**，且改表必然改测试同提交可见。 |
| **`InvalidSchemaError` 定义在 L2 而非契约层的「唯一定义处」** | 契约层 18 符号面是**冻结面**（G7 / G8 / 快照）⇒ 加一个导出符号要连带改公开面文档、门禁、API 快照与兼容矩阵 ⇒ 代价与收益严重不成比例；而用户侧按 `except FreegraphError` / `except ValueError` 捕获**完全够用**（spec FR-007 ⑤ · Q4） | **替代方案 A：加进契约层 `__all__`**（18 → 19）⇒ **破坏冻结面**（G7 恒红）⇒ 需发起者追认 + 改 4 处工件 ⇒ **不可行**。<br>**替代方案 B：不新增错误类型，直接抛内置 `ValueError`** ⇒ 错误**脱离**内核异常家族，与仓库既有体系（`InvalidUpdateError` 等 4 个子类均从 `FreegraphError` 派生）不一致 ⇒ 上层无法用统一基类兜住 ⇒ **不可行**。<br>**替代方案 C：在契约层定义但**不**导出** ⇒ 既破坏「唯一定义处」的公开面语义，又制造「模块内可 import、公开面不可见」的**双重权威** ⇒ **不可行**。<br>**采用的处置**：L2 内定义 + **双重继承**（`FreegraphError` + `ValueError`）⇒ 既归入内核异常家族，又与上游的 `ValueError` 兼容；**登记**：`contracts/errors.py` 的「唯一定义处」措辞指**基类与既有子类**（其同一 docstring 已写明「后续可新增子类」）⇒ 本 feature **不改**该文件。 |
