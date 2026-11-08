# 依赖门禁契约（dependency-gate.md）

**功能块**: B3F1 · 项目脚手架 + extras 划分 + CI 门禁 · **Date**: 2026-11-07
**权威来源**: [spec.md](../spec.md)（FR-001 · FR-004 · FR-005 · FR-006 · FR-018 · 裁定 1 · 裁定 6 · 裁定 11 · 裁定 17 · 裁定 18）·
[architecture-gates.md](./architecture-gates.md)（G21 / G22 / G23）· [research.md](../research.md)（D-02 ~ D-06）
**契约性质**: **冻结面** —— 本文件定义**依赖红线的可判定口径**；改口径 = 改冻结面

> **作用域（D12 · 裁定 6）**：本契约约束的对象是 **freegraph 自己**——
> 它的**依赖声明**、它的 **import**、它的**网络行为**；
> **不**约束用户脚本装了什么。
> ⇒ 门禁需要**三个可判定环境、两套断言**（§1）。

---

## 1. 三个可判定环境、两套断言

| 环境 | 装什么 | 断言 | 门禁 |
|---|---|---|---|
| ① **依赖断言环境** | **7/7 全装环境**（基础包 **+ 四个 extras 的传递依赖已安装** —— 否则 G21 的递归展开**无法取证**）<br>**⚠️ v1.0（裁定 26）**：装的是「**v2.0 预验证依赖**」，**不是** v1.0 的依赖（v1.0 发行元数据零依赖）；判据对象 = `contracts/extras-v2.toml` | 递归展开 freegraph 自身 `Requires-Dist`（**含全部 extras 变体**）无 `langsmith` / `langchain*` / `langgraph*` / `deepagents`；`import freegraph` 后 `sys.modules` 中无 `langsmith` / `langchain_core` / `langgraph` | **G21** · **G23** |
| ② **隔离环境** | **只装基础包的隔离 venv**（零必装依赖 · 不装任何 extra） | 第三方依赖闭包 **== 空集** + `import freegraph` 后 `sys.modules` 无 langchain 家族（SC-002 · FR-005 ②） | **G22** |
| ③ **验收环境** | freegraph + **脚本自带的** `langchain` 系 | **反向断言**：freegraph **运行期从不** import `langchain` / `langchain_core`；freegraph 自身**零出站** | **G25**（导入图）· **G27**（零出站） |

> **为什么必须有独立的验收环境**：若只在一个「装了 langchain」的环境里断言「环境里没有 langchain」，
> 断言会**自我实现**（把用户的依赖当成 freegraph 的依赖）⇒ 测不出真问题。
> 环境 ③ 的断言是**反向**的：**有** `langchain` 在场，**但 freegraph 不碰它**。
> **⚠️ 「两套断言」vs「三个环境」（2026-11-08 分析轮订正 · 已拍板 · 与 spec 裁定 6 / FR-005 ①② 逐字一致）**：
> **两套断言** = ① 的**声明级闭包断言** + ③ 的**运行期反向断言**（立项书 D12 原义**不变**）；
> **② 隔离环境**是把 ① 的取证前提**分离**出来（只装基础包 ⇒ 断言基础闭包为空集），
> **不是第三套断言**、**不新增口径** ⇒ 故「三个环境、两套断言」。
>
> **📌 G21 与 G22 的环境 MUST NOT 合并（2026-11-08 分析轮订正 · H3）**：
> 原表把 **G21 / G22 一起映射到「环境 ①（隔离 venv）· 只装 freegraph 基础包」** ⇒ 与
> `architecture-gates.md` G21「**未安装 ⇒ 判失败**」**互斥**（传递依赖**必须已安装**才能完成递归取证）
> ⇒ 且 `ci-matrix.md` 已要求**全部 7 个作业**装齐四个 extras 的依赖 ⇒ **上表已拆成两行**：
> **G21 = 7/7 全装环境** · **G22 = 只装基础包的隔离 venv**（它断言的正是「基础安装闭包 == 空集」）。
> **G21 在 Linux 与非 Linux 作业 MUST 同口径**（只是**门禁集合**的子集差异，**不是环境差异**——
> 两者都跑在「7/7 全装」的环境里）。

---

## 2. extras 变体的枚举语义

### 2.1 extras 的划分（FR-001 · FR-004 · **适用版本 = v2.0**）

> **⚠️ 2026-11-08 · 裁定 26 · 宪法 v1.7.0**：**v1.0 的发行元数据 MUST NOT 出现任何
> 依赖包名** ⇒ v1.0 的 `pyproject.toml` **MUST NOT** 含
> `[project.optional-dependencies]` ⇒ 下表**移入 v2.0 范围**，其声明落在
> **`contracts/extras-v2.toml`**（**不进发行包** · **刻意采用 `pyproject` 的同构形态**
> ⇒ 门禁的解析器零改动即可消费）⇒ **G21 / G23 的判据对象 = 该清单**。

```toml
# contracts/extras-v2.toml（v2.0 的 extras 声明 · 不进发行包）
[project.optional-dependencies]
pydantic  = ["pydantic>=2.0"]
checkpoint = ["ormsgpack>=1.0"]
otel      = ["opentelemetry-api>=1.20", "opentelemetry-sdk>=1.20"]
png       = ["playwright>=1.40"]
```

> **📌 `[png]` 的渲染后端方向留待 v2.0 专项调研后决策**（2026-11-08 发起者决议）：
> 上表登记的是**唯一实测可行**的白名单内后端 `playwright`（research D-02）⇒
> 但**真 PNG 渲染**的方向（`playwright` 需另装浏览器二进制 vs 自研最小渲染器 vs
> 继续只出占位 PNG）**MUST 在 v2.0 专项调研后决策** ⇒ 调研完成前
> **MUST NOT** 把上表当作「已定的方案」。

- **基础安装的 `dependencies` MUST 为空列表**（零第三方运行时依赖 · 宪法 v1.2.0）⇒ 基础闭包 **== 空集**。
- 每个 extra **独立可选**：不装即不可用；基础安装 MUST NOT 拉起任何 extra 的依赖（FR-004 ①）。
- **各 extra 的内容 MUST 取自宪法「依赖白名单 / 黑名单」· 包层白名单条原文所列**——
  `[otel]` = `opentelemetry-api` + `opentelemetry-sdk`（**MUST NOT** 含任何 exporter · 裁定 21）·
  `[png]` = **`playwright`**（**宪法 v1.5.0 已列明** · 确切包名 + 三条硬约束 (a) 默认关闭 / (b) 许可证白名单 / (c) 零出站）。
  > **📌 2026-11-08 分析轮订正（H10 · 宪法 v1.5.0）**：本契约原先对 `[png]` 只写「具体渲染后端由 plan 决定」
  > ⇒ **宪法 v1.5.0 已收敛为 `playwright`**（包层白名单条里的「mermaid 相关」这一**类别式**表述**已被宪法 v1.5.0 取代**）
  > ⇒ `[png]` 的**规范表述一律为 `playwright`**；plan 阶段只**核验**其许可证标识 ∈ 白名单与**运行期零出站**，
  > MUST NOT 另选后端（那将是白名单之外的包 ⇒ 违反 FR-001 / FR-018）。

### 2.2 「extras 变体」的定义（FR-004 · Assumptions）

**变体集合** = { 基础安装 } ∪ { 每个 extra 单独启用 } ∪ { 全部 extra 同时启用 }
⇒ 本项目的 **6 个变体**（基础 1 + 单独 4 + 全部同时 1）。
> **口径修正（2026-11-07 分析轮）**：此前写作「5 个」是**算术错误**（四个 extra ⇒ 1 + 4 + 1 = 6）——
> 若按 5 枚举，实现方可能漏掉**某个单独 extra**（例如 `[png]` ⇒ `playwright` 永不被判）⇒ 已统一为 **6**。

### 2.3 变体求值规则（**关键** · 与 G3 的修正同源）

对某个变体 `V`：

1. freegraph 的每条 `Requires-Dist` 按其 marker 求值：
   - 无 marker ⇒ **恒成立**（基础依赖）；
   - `extra == "X"` ⇒ 当且仅当 `X ∈ V` 时成立；
   - 其他 marker（如 `python_version < "3.12"`）⇒ **按该条件求值**（**必须求值**，不得忽略）。
2. 对成立的直接依赖，**递归展开其基础依赖**：
   **传递依赖的 extras 一律不展开**（只取其**基础**依赖）。
   ⇒ **理由**：extra 是「**freegraph 对用户的承诺**」，不是「传递依赖的私有细节」。
   传递依赖的 optional extra（如 `pydantic[email]` → `email-validator`）**不在** freegraph 的闭包里。
3. 闭包 = 所有变体的**并集**（用于白名单判定）+ **逐变体**判定（用于黑名单判定，
   便于报错时指名「出现在哪个变体」）。

> **⚠️ 未安装的依赖 = 显式失败，不静默跳过**（2026-11-07 分析轮补入）：递归展开需要读取
> **传递依赖自身的元数据**（`importlib.metadata.requires(pkg)`）⇒ 该依赖**未安装**时
> MUST **判失败并指名该包**（「未安装 ⇒ 无法取证」），**MUST NOT** 静默 `except` 跳过 ——
> 静默跳过会让「闭包只展开到第一层」伪装成「闭包干净」，使**间接引入**的黑名单包永远抓不到
> （spec Edge Case「递归展开 MUST 走到闭包末端」）。
> ⇒ 推论：**CI 必须装齐四个 extras 的依赖**（ci-matrix §2 **步骤 5.5** · **实测**：四个 extras 的完整闭包
> **恰好 12 个包**，与 G3 的白名单逐一命中）。

> ⚠️ **既有门禁 G3 的 `with_extras=True` 语义与此不同**（它把传递依赖的 extras 也展开）⇒ **本 feature 修正 G3**（见 §6）。
> **📌 失配机制订正（2026-11-08 分析轮订正 · H9⑥）**：**实际变红的是「白名单子集断言」**；
> 「许可证断言」实为 **`pytest.skip`**（那 8 个包**均未安装** ⇒ 落入 G3 既有的 `missing` 分支）
> ⇒ **不构成变红原因**；且 **`dnspython` 不在闭包内**（它是 `email-validator` 的依赖，
> 而 `email-validator` 本身未安装 ⇒ 递归到它时即取不到元数据）⇒ 只有 `email-validator`（Unlicense）进闭包。
> ⇒ 这正是新门禁 **G23**「fail-on-missing」不可省略的理由。

### 2.4 基础安装闭包 MUST 为空集（SC-002）

`dependencies = []` ⇒ 基础变体的闭包 == **空集**。
这是 README「零第三方运行时依赖」这条**对外承诺**的**可判定形式**。

> **⚠️ v1.0 的口径更强（裁定 26 · 宪法 v1.7.0）**：v1.0 **不声明任何 extra** ⇒
> 实测 `importlib.metadata.requires("freegraph")` == **`None`**（**整个为空**，
> 连 `extra ==` 标记的条目也没有）⇒ 判据 = 「**`Requires-Dist` 整个为空**」，
> 比「无 marker 的条目数 == 0」**更强**。

---

## 3. 许可证明的四级有序证据链（裁定 17）

**取到即止** —— 前一级命中即**采用**，MUST NOT 再往下取（避免多来源冲突时口径不定）。

> **📌 取证作用域 = 并集口径（2026-11-08 分析轮订正 · 与 spec 裁定 25 逐字一致）**：
> 本节规定的是「**单个包内部**读哪四个字段」；而「**判哪些包**」「**元数据从哪读**」由
> **被检查包集合 =（依赖闭包中的包）∪（取证作用域根下扫到的 `*.dist-info` / `*.egg-info` 所对应的包）**
> 与**证据读取顺序**（① 取证作用域根下的元数据 ⇒ ② 已安装元数据）共同确定
> —— 详见 `architecture-gates.md` G23 的 📌 块与 §2.1 CLI 契约。
> ⇒ **MUST NOT** 只判其中之一（只判闭包 ⇒ 反向用例空转；只判作用域根 ⇒ 空门禁 ⇒ 违宪）。

| 级 | 来源 | 说明 |
|---|---|---|
| **1** | `License-Expression` | **PEP 639**（metadata 2.4）—— **优先级最高** |
| **2** | `License` 字段 | 传统 metadata 字段 |
| **3** | `License ::` 分类器 | `License :: OSI Approved :: MIT License` 等 |
| **4** | `dist-info/licenses/` 下的**授权文件原文** | 从文件头部识别许可证标识 |

- **四级全无** ⇒ **取不到许可证明** ⇒ **判失败并指名该包**（FR-006 ②）——
  **MUST NOT 静默放行**（静默放行 == 白名单失效）。
- **第 1 级 MUST 存在**：实测 `pydantic` 2.13.4 的 `License` 字段与 `License ::` 分类器**皆空**，
  **只有** `License-Expression: MIT` ⇒ 漏掉第 1 级会把一个**完全合规的 MIT 包判死**
  （并堵死 `[pydantic]` extra）。
- **回归基准**：`pydantic` 2.13.4（MUST 作为门禁的**回归基准**入库 · FR-006 ③④）。

---

## 4. 许可证白名单（裁定 18）

### 4.1 白名单（**恰好 5 个精确 SPDX 标识符**）

```
MIT  ·  Apache-2.0  ·  BSD-2-Clause  ·  BSD-3-Clause  ·  PSF-2.0
```

### 4.2 判定规则

1. 取到的标识 MUST 先被解析为 **SPDX 表达式**（用 `packaging>=24.2` 的 `packaging.licenses`
   —— 该模块自 24.2 才存在 · research D-05 有实测验证）；
2. 表达式的**每一个叶子标识符** MUST ∈ §4.1；
3. 表达式**解析不出来**（非 SPDX 的散文式名称）⇒ **判失败**。

**叶子的取法（2026-11-07 分析轮定案 · 关键修正）**：
`packaging.licenses` 的**公开面**只有 `canonicalize_license_expression` / `InvalidLicenseExpression` /
`NormalizedLicenseExpression`（**实测 24.2 / 25.0 / 26.3 三个版本皆然）——
**不存在** `LicenseExpression` 类、**不存在**任何公开的树 / 叶子迭代 API（`canonicalize_license_expression`
返回的是**普通 `str`**，不是表达式树）。
⇒ 故叶子 MUST 取自**规范化输出**：对 `canonicalize_license_expression(...)` 的返回值
**按空白分词**，剔除 `AND` / `OR` / `WITH` / `(` / `)` 五类算子与括号后，剩余 token 即为叶子。
**该分词是安全的**（规范化输出保证算子与括号两侧必有空格、标识符内不含空格）——
**实测**：`'MIT AND PSF-2.0'` → `{MIT, PSF-2.0}`；`'Apache-2.0 OR MIT'` → `{Apache-2.0, MIT}`；
`'BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0'` → 5 个叶子全对。
**MUST NOT** 对**原始标识**做字符级切分（如 `re.split(r"[|&()]")`）—— 那会把 `MIT AND PSF-2.0`
误切成**一个** token（research D-05 已实测否决该做法）；**MUST NOT** 引入等价标识符对照表或家族判定（§4.3）。

**实测样例**（`research.md` D-05）：

| 表达式 | 叶子 | 判定 |
|---|---|---|
| `MIT` | `MIT` | ✅ |
| `MIT AND PSF-2.0`（`greenlet`） | 两个叶子皆白名单 | ✅ |
| `Apache-2.0 OR MIT`（`ormsgpack`） | 两个叶子皆白名单 | ✅ |
| `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0`（`numpy`） | 含 `0BSD` / `Zlib` / `CC0-1.0` | ❌ |
| `3-Clause BSD License`（`protobuf`） | **散文式 · 无法解析** | ❌ |
| `MPL-2.0`（`certifi`） | 不在白名单 | ❌ |

> **变体标识符的判定（实测补充 · 2026-11-07）**：`MIT-CMU` / `HPND` / `MIT-0` **能**被
> `canonicalize_license_expression` **解析通过**（它们是合法的 SPDX 标识符）⇒ 其被拒**不是因为解析失败**，
> 而是因为**不在 §4.1 白名单**（`MIT-CMU` ≠ `MIT`）⇒ 判据落点在**白名单比对**，不在解析器。
> 同理 `Apache-2.0 WITH LLVM-exception` 可解析但含 `LLVM-exception` 叶子 ⇒ 拒。
> 而 `PSF`（**非** `PSF-2.0`）**解析即失败**（`InvalidLicenseExpression`）⇒ 拒。

### 4.3 MUST NOT（裁定 18 · FR-018）

- MUST NOT 引入**等价标识符对照表**（把 `MIT-CMU` 视同 `MIT`）；
- MUST NOT 引入**许可证家族判定**（按「属 MIT 家族」放行）；
- MUST NOT 引入任何**按需扩充白名单**的机制（豁免入口）；
- MUST NOT 用**子串包含**判定（`"MIT" in upper` 会放行 `MIT-CMU`）；
- **白名单的扩充只能走宪法修订**（原则 IX 为 NON-NEGOTIABLE）。

### 4.4 禁用清单（传染性 / 限制性 · 宪法原则 IX）

`Elastic-2.0` · `AGPL` · `SSPL` · `BUSL` · `GPL-2` · `GPL-3` · `MPL-2.0` · `LGPL-2.1` · `LGPL-3.0`
⇒ **失败**（**点名**报出，不靠前缀猜测）。

### 4.5 点名名单（ELv2 组件 · FR-006 ①）

`langgraph-api` · `langgraph-runtime-inmem` · `phoenix`
⇒ 即使其许可证表述合规，也**必须**被拒（ELv2 明文禁止「以托管服务形式提供」，
**恰好否掉 freegraph 最可能的商业模式**）。

---

## 5. 依赖黑名单（包层 · 宪法「依赖白名单 / 黑名单」）

| 族 | 匹配规则 | 覆盖 |
|---|---|---|
| `langsmith` | 精确名 + `langsmith-*` | `langsmith` / `langsmith[otel]` / `langsmith[sandbox]` / `langsmith-sdk` |
| `langchain*` | **前缀** `langchain` | `langchain` / `-core` / `-classic` / `-protocol` / `-anthropic` / `-openai` / `-google-genai` … |
| `langgraph*` | **前缀** `langgraph` | `langgraph` / `-checkpoint` / `-sdk` / `-prebuilt` / `-cli` / `-api` / `-runtime-inmem` … |
| **全部 provider 包** | 前缀 `langchain-` | 它们会把 `langchain-core` 拉回来 |
| `deepagents` | 精确名 | 宪法包层黑名单明列 |

> **📌 与 `architecture-gates.md` G21 表的逐项一致性（2026-11-08 分析轮订正 · Q4）**：本表与
> [architecture-gates.md](./architecture-gates.md) G21 的黑名单表**逐行一致**（族 / 匹配规则 / 点名名单 / `deepagents`）
> ⇒ 两处 MUST NOT 出现「一条有、一条无」的行（否则**冻结契约比红线少一条**）。
> **ELv2 点名名单**（`langgraph-api` · `langgraph-runtime-inmem` · `phoenix`）在 §4.5 登记 ——
> 它**同属本黑名单**（ELv2 组件 · 宪法原则 IX）⇒ G21 表以「**点名名单**」行承载同一组精确名。

**已知代价**：前缀匹配**可能**误伤无关包（如 `langchainx`）。
**取舍**：**保守方向**（宁可多拦）—— 依赖黑名单**宁可错杀不可漏放**；
且 MUST NOT 因此引入豁免机制（FR-018 ①）。

---

## 6. 对既有门禁 G3 的占位填充（裁定 8 的**唯一一处例外**）

| 项 | 现状 | 本 feature 改为 | 方向 |
|---|---|---|---|
| `CONSTITUTION_DEPENDENCY_WHITELIST` | 4 个**占位**包名 | **四个 extra 的真实闭包确切包名集合**（有限 · 逐个列名 · **无通配符 · 无前缀匹配**） | **更精确** |
| extras 变体枚举 | `with_extras=True` ⇒ 传递依赖的 extras 也展开（**过近似**） | **只枚举 freegraph 自身的 extras 变体**（§2.3） | **更正确** |
| 许可证取值 | `License-Expression` → `License`（**2 级**）+ **skip-on-missing** | **不动**（判据零改动） | — |

**G23 与 G3 的差异（已知取舍 · research DR-6）**：G3 用**子串匹配**且白名单含 `"PSF"`，
G23 用**精确 id**且白名单含 `"PSF-2.0"` ⇒ `MIT-CMU` 在 G3 通过 / 在 G23 被拒。
**G23 严于 G3 ⇒ 总体门禁效果为严，不存在漏判。**

**待发起者追认**（见 plan.md 与 `tasks.md`）。

---

## 7. 登记：exporter 与白名单的冲突（归 B21F1）

`opentelemetry-exporter-otlp` 的闭包含 **`certifi`（`MPL-2.0`）** ⇒ **不在**白名单 ⇒ **不可**进 `[otel]` extra。
⇒ `[otel]` 取**宪法依赖白名单原文所列**的 `opentelemetry-api` + `opentelemetry-sdk`；
exporter 归 **B21F1**（OTLP 导出插件与后端对接）解决。
详见 [research.md](../research.md) **D-02 / D-03**。
