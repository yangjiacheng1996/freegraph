---

description: "B3F1 · 项目脚手架 + extras 划分 + CI 门禁 —— 任务清单（G21–G30 十条新门禁 + 7 作业 CI 矩阵）"
---

# Tasks: B3F1 · 项目脚手架（extras 划分 + `src/` 布局 + 类型标记）+ 7 项质量门禁的自动化落地

**Input**: Design documents from `/specs/b3f1-scaffold-ci-gates/`

**Prerequisites**: plan.md（必读 · 含 **Constitution Check 的唯一例外** · **Structure Decision**）、
spec.md（必读 · 含 **25 条裁定** + **13 条澄清问答** · FR-001 ~ FR-021 · SC-001 ~ SC-016）、
research.md（必读 · **15 条决策 D-01…D-15** · 全部附**实测证据**）、
data-model.md（12 个静态工件实体 + 9 条跨实体不变量）、
contracts/architecture-gates.md（**G21–G30 的判据细则** + 与既有门禁的分工表）、
contracts/dependency-gate.md（依赖红线口径 · 黑名单 / 四级证据链 / 5 个精确 SPDX id / extras 变体语义）、
contracts/layer-registry.md（**层归属的唯一权威** · 机器可读）、
contracts/ci-matrix.md（7 作业矩阵 · 步骤 · 分支保护设置项）、
quickstart.md（**可照抄**的验证手册）

**Tests**: **含**测试任务 —— 本 feature 的需求本体就是**门禁判据**
（**8 条强制反向用例** · SC-009 · 裁定 14），
测试是**交付面的一部分**，不是可选项。

**Organization**: 任务按用户故事分组，每个故事可**独立实现、独立测试、独立交付**。

**本 feature 的可测判据总表**（**21 FR + 18 SC ↔ 57 条任务**）：
追溯见文末「**附录 · 任务 ↔ spec 追溯表**」——
**每个 FR 与每个 SC 均至少被一条任务映射**（**FR 21/21 · SC 18/18**），
其中 **SC-009**（8 条强制反向用例）由 **T015–T021 + T042** 八条任务共同承载，
**FR-021 / SC-016**（第三方品牌资产）由 **T021 + T028** 承载，
**T057**（**三条**宪法质量门禁缺口的发起者追认 · 门禁 3 的 C4/C8 + 门禁 4 的 fake 轮 + 门禁 5 的真实模型轮）是**新增的第 57 条任务**（**2026-11-08 分析轮订正** ·
**MUST NOT** 改变 FR / SC 的条数：**FR 仍为 21 条 · SC 仍为 18 条**）。

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**：可并行（**不同文件**且无未完成依赖）——同一文件内的后续任务**不标** `[P]`
- **[Story]**：所属用户故事（US1…US4）
- 每条任务都带**确切文件路径**；冻结面的**逐字内容**在 `contracts/` 与 `data-model.md` 中，本文件**只引用不复制**
- **逐条追溯**：每条任务对应的 **FR / SC** 见文末「**附录 · 任务 ↔ spec 追溯表**」
  （宪法原则 VI：「tasks MUST 逐条勾选、**可追溯到 spec 条目**」）

## Path Conventions

- 单项目：`src/` · `tests/` 在仓库根
- 门禁代码：`harness/scripts/gates/`（**跨层单元 · 工程设施** ⇒ **不进发行包** —— 宪法「发布门禁」第 1 条）
- 门禁测试：`tests/gates/`（**不叫** `test_architecture.py` —— `tests/contracts/` 与 `tests/facade/` **各有一个** `test_*.py` 同族文件；本目录**自带 `__init__.py`**（T005）⇒ 模块名带包前缀 ⇒ 不会触发 pytest 的 `import file mismatch`；命名再错开以免**人**读混）
- 门禁契约：`specs/b3f1-scaffold-ci-gates/contracts/`
- CI：`.github/workflows/ci.yml`（**新增**；`publish.yml` **零改动**）—— **CI 的解释器 MUST 用跨平台写法**
  （T030 建的 venv · ci-matrix §2 步骤 3.5 · §2.0）：**命令串里只出现 venv 目录 `.venv`**
  （安装 `uv pip install --python .venv …` · 调用 `uv run --no-project --python .venv python …`），
  **MUST NOT** 出现任何平台专属的解释器路径（POSIX 的 `bin/` 布局或 Windows 的 `Scripts\` 布局）——
  否则 `windows-2025` 的 2 个作业**每一条命令**路径失效 ⇒ **必红**（违反 PR-4）。
- 人工验证记录：`harness/verification/B3F1/manual-verification.md`
- **隔离副本**（T014 的 `isolated_copy`）：**MUST 含** `pyproject.toml` + `src/` + **`README.md`** + **`LICENSE`** —— 后两者是 `pyproject.toml` 的硬引用，缺一即构建失败（ci-matrix §3.1）

> **⚠️ 落地顺序提示**：extras 一旦声明，**既有门禁 G3 立即变红**（**实测**：实际变红的是「**白名单子集断言**」——
> 旧枚举语义下 extras 闭包实测 **20** 个包，其中 **8** 个不在 4 个占位包名内；
> 「许可证断言」实为 **`pytest.skip`**（这 8 个包**均未安装** ⇒ 落入 G3 既有的 `missing` 分支）⇒ **不构成变红原因**；
> 且 **`dnspython` 不在闭包内**（它是 `email-validator` 的依赖，而 `email-validator` 未安装 ⇒ 递归到此即止））
> ⇒ **T002（声明 extras）与 T003（填 G3 占位）MUST 同一个提交落地**，MUST NOT 分两次提交（否则中间态 CI 必红）。
> **（2026-11-08 分析轮订正 · H9⑥）**：原写「`email-validator`(Unlicense) / `dnspython`(ISC) 被 G3 的过度近似拉进闭包」
> ⇒ 旧说法**不成立**（`dnspython` **不在**闭包内）⇒ 现统一为订正后的表述。
> **这正是新门禁 G23「fail-on-missing」不可省略的理由**。
>
> **⚠️ 唯一例外提示**：T003 是**对裁定 8 的唯一一处例外**（plan.md「Constitution Check」）——
> **判据句逐字不动**，只填 B2F1 自己**预告过**的占位常量 + 修正枚举语义，**净效果是变严**。
> **T049** 是该例外的**发起者追认**（阻断合入）。
>
> **⚠️ 白名单的版本敏感性**：T003 的 12 名白名单是**当前解析结果**的快照（`pydantic` 解析到 2.13.x）；
> 因 extras 的版本约束是**开区间**（`pydantic>=2.0`），上游**新增一个传递依赖**即会让闭包多出一个包名 ⇒ 白名单失配 ⇒ CI 变红。
> ⇒ **复核的双触发点（2026-11-08 发起者决议 · MUST 照此执行）**：① **extras 的版本约束变更**
> （`pyproject.toml` 的 `[project.optional-dependencies]` 任一条变更）· ② **CI 因闭包失配而红**
> （G3 的白名单子集断言失败）—— 二者**任一**发生即 MUST **重跑 research D-02 的闭包实测** ⇒
> **重新实测闭包 + 追认更新白名单**（仍须发起者追认 · T049），
> **MUST NOT** 以「放宽白名单让它变绿」的方式绕过（那会把未复核的包名直接放行 · FR-018），
> **白名单的扩充只能走宪法修订**（裁定 18）。**保持开区间是已决事项**（不收紧版本上界）。
>
> **⚠️ 签名头提示**：T004 MUST 在 **G30 上线前**完成 —— **实测（2026-11-07 分析轮复核修正）**：全仓
> 37 个受版本控制的 `.py` 中**仅 1 个**缺头（`harness/scripts/audit_feature_drafts.py`），
> 其余 **35 个已合规**（**26** 个在首行 + **9** 个在 **shebang 之后** ⇒ **本就符合**宪法原则 X），
> `harness/demo/target.py` 为只读基准 · 具名例外 ⇒ **G30 上线不会红**。
> **补头位置 MUST 分两种**：首行是 shebang ⇒ 头在 **shebang 之后**、docstring 之前；无 shebang ⇒ 头在**首行**。
> **MUST NOT** 给已合规的文件**重复**加头。

---

## Phase 1: Setup（共享基础设施）

**Purpose**：把**脚手架**与**存量债**一次性清干净，不产出任何用户可见能力。

- [X] T001 [P] 在 `pyproject.toml` 新增 ① `[tool.pytest.ini_options]`：`testpaths = ["tests"]`（把 pytest 收集范围**钉死**在 `tests/` ⇒ 裁定 16 的「核心用例 = 全量测试套件」有确定含义）、`addopts = "-ra"`、`xfail_strict = true`（research D-15）；② **注册两个 marker**：`markers = ["linux_only: 需 Linux 隔离环境 / 网络命名空间", "full_install: 需装齐四个 extras 的完整安装环境"]`（**H3** · 平台专属用例的过滤依据 —— 非 Linux 作业的 pytest 步骤用 `-m "not linux_only and not full_install"` 排除；**MUST NOT** 漏注册，否则 pytest 报 `PytestUnknownMarkWarning` · 与本任务同文件 ⇒ 同提交）。
  **⚠️ `[dependency-groups] dev` 已存在（2026-11-08 分析轮订正 · M1）**：工作树的 `pyproject.toml` **已含**
  `[dependency-groups] dev = ["pytest>=7.4", "packaging>=24.2"]`（**未提交**）⇒ 本任务**只补**
  `[tool.pytest.ini_options]` 与两个 marker 的注册，**MUST NOT** 再写一份 `[dependency-groups]` ——
  **重复的 TOML 表会让 `tomllib.loads` 直接报错**、闸口 **A1** 的检查命令失败。
  **⚠️ `full_install` marker 的现状（2026-11-08 分析轮订正 · M5 · **2026-11-08 二轮复核订正**）**：该 marker **在本任务中注册、但当前无任何用例使用**（**实测**：`pyproject.toml` 尚**无** `[tool.pytest.ini_options]` 段 ⇒ 两个 marker 目前**均未注册**；本任务负责把该段连同两个 marker 一次性建起）
  —— 因为**全部 7 个作业都装齐四个 extras 的依赖**（FR-015 ⑤）⇒ 没有用例需要按「完整安装环境」这一维度过滤
  ⇒ 本任务**保留**该 marker 作为**预留**（MUST NOT 擅自删除）；过滤表达式
  `-m "not linux_only and not full_install"` 在当前**等价于** `-m "not linux_only"`
  ⇒ **`ci-matrix.md` §1 / §2 的过滤表达式 MUST 与此保持一致**（**MUST NOT** 单边改动）。
  **开发期依赖组的纪律（沿用）**：`[dependency-groups] dev` **不进发行包**（hatchling 不把 dependency-groups 写进元数据
  ⇒ 发行纯度门禁不受影响）· **不进 `Requires-Dist`** ⇒ 基础闭包仍为空集（G3 不受影响）· 安装方式 `uv pip install --python .venv --group dev`
  （**实测 uv 0.12.7 支持** · **跨平台写法** · ci-matrix §2 步骤 4）。
- [X] T002 在 `pyproject.toml` 新增 `[project.optional-dependencies]`，**恰好四个 extra**：`pydantic = ["pydantic>=2.0"]`、`checkpoint = ["ormsgpack>=1.0"]`、`otel = ["opentelemetry-api>=1.20", "opentelemetry-sdk>=1.20"]`、`png = ["playwright>=1.40"]`（research D-02 / D-03 / D-04；**MUST NOT** 含 `opentelemetry-exporter-otlp` —— 其闭包含 `certifi`(MPL-2.0)，不在白名单）；**`[png]` 的后端 = `playwright`**（**宪法 v1.5.0 · Apache-2.0 · 本地 Chromium 渲染** —— 宪法包层白名单条里「mermaid 相关」这一**类别式**表述**已被宪法 v1.5.0 取代**为确切包名 ⇒ 本任务**只核验**许可证标识 ∈ 白名单与**运行期零出站**，MUST NOT 另选后端）
- [X] T003 在 `tests/contracts/test_architecture.py` 填既有门禁 **G3** 的两处占位（**判据句逐字不动** · plan.md「唯一一处例外」）：① `CONSTITUTION_DEPENDENCY_WHITELIST` 由 4 个占位包名改为**恰好 12 个确切包名** —— `"annotated-types"` · `"greenlet"` · `"opentelemetry-api"` · `"opentelemetry-sdk"` · `"opentelemetry-semantic-conventions"` · `"ormsgpack"` · `"playwright"` · `"pydantic"` · `"pydantic-core"` · `"pyee"` · `"typing-extensions"` · `"typing-inspection"`（**无通配符 · 无前缀匹配**）；② `dependency_closure(..., with_extras=True)` 的枚举语义由「无差别剥离/保留 extras marker」改为「**只枚举 freegraph 自身的 extras 变体**（传递依赖只展开其**基础**依赖，不展开传递依赖自己的 extras）」（research D-06 · dependency-gate.md §2.3）
- [X] T004 [P] 为 `harness/scripts/audit_feature_drafts.py` 补上署名头（**只加这一行，不改逻辑内容**）——署名头**逐字**为 `# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph`，插在**首行之前**（该文件首行是**模块 docstring** ⇒ 补头后 docstring 仍是**首个语句** · 宪法原则 X · FR-013 ②⑤ · 裁定 5）；**⚠️ 实测（2026-11-07 分析轮复核修正）**：全仓 37 个受版本控制的 `.py` 中**仅此 1 个**缺头 —— 其余 **35 个已合规**（**26** 个在首行 + **9** 个在 **shebang 之后**）⇒ **MUST NOT** 给那 9 个文件**重复**加头（会污染文件）；`harness/demo/target.py` 为只读基准（宪法原则 III）· **不在**补齐清单内
- [X] T005 [P] 创建 `tests/gates/__init__.py`（署名头 + docstring + `__all__ = []`）—— 使 `tests/gates/` 可被绝对导入
- [X] T006 [P] 创建 `tests/gates/data/offline_exclusions.txt`（断网排除清单初版）：首行注释写明**判据**（「仅两类可排除：(a) 断网任务自身；(b) 语义上必须能建立连接的用例 —— 含 (b1) 验证用户出站归因的用例 · (b2) 需联网安装 / 解析依赖的用例（如隔离 venv 一族）」），其后每行格式 `用例标识 :: 排除理由`（research D-09 · FR-010 ④⑤）。**⚠️ 用例标识 MUST 用 pytest node ID**（`tests/gates/test_gates.py::<函数名>`）—— 它被 G28 逐条转成 `--deselect` 参数（`contracts/ci-matrix.md` §3.2 · T038 / T039）⇒ 标识形式不一致 ⇒ 清单与 `--deselect` 展开式**漂移** ⇒ 断网任务**假红**（SC-004 · **2026-11-08 分析轮订正 · A5**）
- [X] T007 [P] 创建 `harness/verification/B3F1/manual-verification.md` 骨架（**五段式 · 仓库既有约定**（`harness/verification/README.md` + 宪法原则 V「验证环境 / 验证步骤 / 实际输出 / 结论 / 遗留问题」+ B1F1 / B2F1 / B2F2 的同名记录）：① 环境 ② 步骤 ③ 实际输出 ④ 结论 ⑤ 遗留问题；**可选第 ⑥ 段「移交后续 feature」**（B2F2 的记录有此段 · 同口径））：③ 实际输出内预留**零出站证据** · **断网全绿证据** · **M0 三 feature 补检结论** · **分支保护设置步骤与状态取证**四个小节 + **来源覆盖表**（宪法原则 VIII）

**Checkpoint**：`pytest tests/ -ra` 仍全绿；`python3 -c "import tomllib,pathlib;print(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['optional-dependencies'])"` 打印出四个 extra

---

## Phase 2: Foundational（阻塞性前置）

**Purpose**：门禁的**共享判定库** + **测试脚手架** —— 十条门禁的重活全在这里，**门禁脚本本身只是薄壳**。

- [X] T008 创建 `harness/scripts/gates/_gatekit.py`（署名头 + docstring）：**统一报告格式**（data-model.md §7）—— `report(violations, gate_id, rule_text) -> int` 输出**违规条目**（包名 或 `文件路径:行号`）+ **命中的规则编号** + **修复指引**（三者**缺一不可** · FR-016 ①），返回退出码（0 = 通过 · 非 0 = 失败，**MUST NOT 吞掉失败**）；并提供 `run_gate(fn)` 包装（`try/except` ⇒ 判失败而非崩溃）；**并提供共享的隔离副本构造器 `make_isolated_copy(root) -> Path`**（MUST 含 `pyproject.toml` + `src/` + **`README.md`** + **`LICENSE`** —— 后两者是 `pyproject.toml` 的硬引用，缺一即构建失败）⇒ **pytest 夹具（T014）与门禁脚本的 `--self-test-negative`（T029）MUST 共用它**，**MUST NOT** 各写一份拷贝逻辑（避免「一处拷 `README.md`、一处不拷 ⇒ G22 在**构建阶段**而非断言阶段失败」· 裁定 8 第三条理由「避免同一判据两处实现」）
- [X] T009 `harness/scripts/gates/_gatekit.py` 加**层注册表解析器** `load_layer_registry(repo_root) -> list[LayerEntry]`：解析 `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md` 的表格（**4 列**：路径 / 层 / 例外 / 说明）；**最长前缀优先**、目录前缀匹配 + 文件精确匹配；**未匹配到任何条目 ⇒ 判失败并指名**（MUST NOT 静默放行 · FR-008 ②）；**MUST NOT** 在本文件里硬编码任何层归属（层归属的**唯一权威** = 该注册表 · research D-07）。**⚠️ MUST 同时解析该注册表 §0.3 的「可判定的声明」表（2026-11-08 分析轮订正 · M10）** —— 解析器 MUST 读出 **L-1**（顶层包 `src/freegraph/__init__.py` MUST NOT import 任何内部层 · **含同层 L1** ⇒ **具名例外** · 优先于「L1 与 L6 允许同层 import」）与 **L-2**（契约层内部零内部层 import · **由既有 G2 承担 · G25 不重复判**）⇒ 否则 §0.3 的声明**在实现中不可判定**（等于没写）
- [X] T010 `harness/scripts/gates/_gatekit.py` 加 **AST 扫描工具**：① `scan_imports(path) -> list[ImportEdge]`（解析 `import X` / `import X.Y` / `from X import ...` / `from . import ...`；**相对导入**按包的层级解析；第三方 import **不**产生层边）；② `scan_env_reads(path) -> list[(行号, 标识)]`（**四种形态全须覆盖**：`os.environ` / `os.getenv` / `os.environb` 的**属性链**形态 **+** `from os import environ` / `getenv` / `environb` 的**导入形态** —— 与既有 `tests/facade/_gatesupport.py` 的 `env_and_io_violations` **同口径**（既有实现已明确覆盖导入形态并写进 docstring）；**漏掉导入形态 ⇒ G24 可被 `from os import getenv` 绕过** · FR-007）；③ `scan_network_calls(path) -> list[(行号, 模块名)]`（网络客户端清单见 architecture-gates.md G26）；④ **标准库判定用 `sys.stdlib_module_names`**（与既有 G2 同款口径 · research D-11）
- [X] T011 `harness/scripts/gates/_gatekit.py` 加**许可证据链 + SPDX 表达式解析**（dependency-gate.md §3 / §4）：① `license_evidence(pkg) -> (来源, 标识)` —— **四级有序、取到即止**：`License-Expression`（PEP 639）→ `License` 字段 → `License ::` 分类器 → `dist-info/licenses/` 授权文件原文；**四级全无 ⇒ 返回 `None`**（调用方**判失败并指名** · FR-006 ② · **MUST NOT skip**）；② `spdx_leaves(expr) -> set[str]` —— 用 **`packaging>=24.2`** 的 `packaging.licenses.canonicalize_license_expression` 解析后取**叶子**。**⚠️ 叶子的取法（2026-11-07 分析轮订正 · MUST 照此实现）**：`packaging.licenses` 的**公开面**只有 `canonicalize_license_expression` / `InvalidLicenseExpression` / `NormalizedLicenseExpression`（**实测 24.2 / 25.0 / 26.3 三个版本皆然**）—— **不存在** `LicenseExpression` 类、**不存在**任何公开的树 / 叶子迭代 API（该函数返回的是**普通 `str`**，不是表达式树）⇒ 故叶子 MUST 取自**规范化输出**：对返回值**按空白分词**、剔除 `AND` / `OR` / `WITH` / `(` / `)` 后取剩余 token（**实测**：`'MIT AND PSF-2.0'` → `{MIT, PSF-2.0}`；`'Apache-2.0 OR MIT'` → `{Apache-2.0, MIT}`）。**MUST NOT** 对**原始标识**做字符级切分（`re.split(r"[|&()]")` 会把 `MIT AND PSF-2.0` 误切成 1 个 token · research D-05 已实测否决）—— 该禁令针对**原始标识**，**不**适用于**规范化输出**；**MUST NOT** 引入等价标识符对照表 / 家族判定（裁定 18）；③ 白名单常量 = **恰好 5 个** id：`MIT` · `Apache-2.0` · `BSD-2-Clause` · `BSD-3-Clause` · `PSF-2.0`（**MUST NOT** 有等价对照表 / 家族判定 / 豁免入口 / 子串匹配 · 裁定 18）
- [X] T012 `harness/scripts/gates/_gatekit.py` 加 **extras 变体枚举 + 依赖闭包展开**：① `read_requires_dist(pyproject_path) -> list[str]`（读 `[project]` 的 `dependencies` + `[project.optional-dependencies]` 的各 extra，**带 marker**）；② `enumerate_variants(pyproject_path) -> list[Variant]`（**6 个变体**：基础 + **4 个 extra 各自单独** + 全部同时 —— dependency-gate.md §2.2）；③ `evaluate_variant(requires, variant) -> set[str]`（按 marker 求值，`extra == "X"` 当且仅当 `X ∈ variant`，其他 marker 如 `python_version` **必须求值**）；④ `closure(variant) -> set[str]`（递归展开，**传递依赖只展开其基础依赖** · 不展开传递依赖自己的 extras · dependency-gate.md §2.3）——**递归 MUST 走到闭包末端**（未安装的依赖 ⇒ MUST 显式报「未安装 ⇒ 无法取证」**失败**，MUST NOT 静默跳过）
- [X] T013 `harness/scripts/gates/_gatekit.py` 加**出站归因函数** `attribute_egress(frames) -> "framework" | "user"`：从栈顶（最靠近连接发生处）向下遍历，**跳过全部标准库帧**（用 `sys.stdlib_module_names`），遇到的**第一个非标准库帧**在 `freegraph/` 包内 ⇒ `"framework"`，否则 ⇒ `"user"`；全标准库帧 ⇒ `"user"`（research D-11 · 裁定 19）
- [X] T014 创建 `tests/gates/conftest.py`（署名头 + docstring）：① fixture `repo_root` / `src_dir` / `gates_dir` / `spec_dir`（沿用 `tests/contracts/conftest.py` 的路径基线口径）；② 把 `harness/scripts/gates/` 插入 `sys.path`（供测试直接 `import _gatekit`）；③ fixture `isolated_copy`（**MUST 复用 `_gatekit.make_isolated_copy()`（T008）** ⇒ MUST NOT 在夹具里另写一份拷贝逻辑 —— 避免与门禁脚本的 `--self-test-negative`（T029）漂移 ⇒ `tempfile.TemporaryDirectory` 里拷 **`pyproject.toml` + `src/` + `README.md` + `LICENSE`** ⇒ **负向验证的工作树隔离副本** · research D-12）。**⚠️ `README.md` 与 `LICENSE` MUST 一并拷贝（2026-11-07 分析轮补入）**：`pyproject.toml` 的 `readme = "README.md"` 与 `license-files = ["LICENSE"]` 是**硬引用** ⇒ 缺任一即构建失败（**实测**：`OSError: Readme file does not exist: README.md`）⇒ 只拷 `pyproject.toml` + `src/` 的副本会让 **G22 的 `uv pip install <target-root>` 在构建阶段就失败**（反向用例 T042 会在**构建阶段**而非**断言阶段**失败）；④ fixture `egress_recorder`（**只包装** `socket.connect` / `socket.create_connection` 以记录目标与调用栈，**放行**全部连接 · FR-009 ② · 裁定 7）——**MUST 复用 `_gatekit` 里的同一实现**（T013 的归因 + 同一 socket 包装），**MUST NOT** 在夹具里另写一份（G27 的「两个入口 · 同一实现」· architecture-gates.md G27）

**Checkpoint**：`python3 -c "import sys; sys.path.insert(0,'harness/scripts/gates'); import _gatekit; print('ok')"` 无错；`pytest tests/ -ra` 全绿

---

## Phase 3: User Story 1 - 破坏红线会立刻被拦住（Priority: P1）🎯 MVP

**Goal**：十条门禁里与「红线」直接相关的 **7 条**（G21 / G23 / G24 / G25 / G26 / G29 / G30）落地，
每条带**反向用例**，并由 **CI 逐条调用** + **分支保护**把「红了合不进去」接通。
**本 Phase 的 7 条反向用例**（T015–T021）属 **SC-009** 的 **8 条**之一部分 —— 第 8 条（G22）在 **Phase 5**（T042）。

**Independent Test**：在依赖声明里故意加入 `langchain-core` ⇒ G21 **必须失败**并输出违规条目（包名 + 规则编号 + 修复指引）；
撤销后**恢复通过**；且**工作树逐字不变**（spec SC-001 / **验收判据 A1**（引文 §6 · 门禁生效 = 负向验证 · 对应**执行闸口 A2**）· SC-010）。

### Tests for User Story 1（反向用例 · 8 条中的 7 条 · MUST 先写且 MUST 先失败）

> **NOTE**：这些反向用例 MUST 先写、**先确认失败**（门禁尚未实现 ⇒ 用例应当红），再实现门禁。

- [X] T015 [P] [US1] 在 `tests/gates/test_gates.py` 写 G21 的**反向用例**：把 `langchain-core>=0.3` 注入 `isolated_copy` 的 `pyproject.toml` ⇒ 断言门禁**失败**且输出含**包名 `langchain-core`** + **规则编号** + **修复指引**；再断言撤销后**通过**（裁定 8 的黑名单三族 + 点名名单各一例 · FR-014 ①）
- [X] T016 [P] [US1] 在 `tests/gates/test_gates.py` 写 G23 的**反向用例**：造一份 `License-Expression: AGPL-3.0-or-later` 的假元数据 ⇒ 断言**失败并指名**；再造一份 `MIT-CMU` ⇒ 断言**被拒**（裁定 18 的「变体不放行」）；再造一份四级证据链**全无**的 ⇒ 断言**失败并指名**（FR-006 ②）。**⚠️ MUST 以 `--root <isolated_copy>` 调用 G23**（architecture-gates §2.1 · **2026-11-08 分析轮订正 · H2** —— CLI 表原**缺 G23 的作用域参数**）—— G23 的 `--root` = **许可证据的取证作用域**（**并集口径** · spec **裁定 25** / architecture-gates G23 📌 块：被检查包集合 =（闭包包集）∪（`<root>` 下扫到的 `*.dist-info` / `*.egg-info`）；证据**先**取 `<root>` 下元数据、**后**回落已安装元数据）⇒ 不指明则注入不可见 ⇒ 用例**空转**。**⚠️ 假元数据的落点 MUST 写死（2026-11-08 分析轮订正 · C4）**：MUST 落成 **`<isolated_copy>/<name>-<version>.dist-info/METADATA`**（**必填四个头**：`Metadata-Version` / `Name` / `Version` / `License-Expression`；且 `Name` / `Version` MUST 与目录名 `<name>-<version>` **一致** —— 否则 `importlib.metadata` 解析不出合法 distribution ⇒ 用例**空转**）⇒ 注入落在 `<root>` 下 ⇒ **必然进入被检查集** ⇒ 取到 `AGPL-3.0-or-later` ⇒ G23 失败并指名。**MUST NOT** 把假元数据放进**已安装的 site-packages 内**（那会污染环境、并掩盖「取证作用域」这条判据本身）。
- [X] T017 [P] [US1] 在 `tests/gates/test_gates.py` 写 G24 的**反向用例**：在 `isolated_copy` 的 `src/freegraph/_probe.py` 写 `os.environ["LANGSMITH_API_KEY"]` ⇒ 断言**失败并指名文件 + 行号**；再写 `os.getenv("ANYTHING")` ⇒ 同样失败（内核零环境变量读取 · FR-007）。**⚠️ MUST 以 `--root <isolated_copy>` 调用 G24**（architecture-gates §2.1）—— 否则 G24 扫的是**仓库根**下的 `src/freegraph/**`，注入**不可见** ⇒ 用例**空转**
- [X] T018 [P] [US1] 在 `tests/gates/test_gates.py` 写 G25 的**反向用例**：造一个登记为 **L1** 的模块去 import **L3** ⇒ 断言**失败**（反向 import）；再断言**跨层单元** import L2 ⇒ **失败**（跨层只可 import L1 与更低层 · FR-008）。**⚠️ MUST 以 `--root <isolated_copy>` + `--registry <isolated_copy>/layer-registry.md` 调用 G25**（architecture-gates §2.1）—— **MUST NOT** 改动**冻结面** `contracts/layer-registry.md`（其 §3「改动须走评审」）⇒ 须用**副本**注册表；只传 `--root` 时 G25 仍读仓库根的注册表 ⇒ 注入**不可见** ⇒ 用例**空转**。**⚠️ 同层方向 MUST 双向覆盖（2026-11-08 分析轮订正 · C2）**：**L2–L5 之间的同层 import**（如登记为 L4 的模块 import 另一个 L4 模块）⇒ MUST **失败**；而 **L1 → L1**（契约层内部 · 仓库现状既有）与 **L6 → L6** ⇒ MUST **通过** ⇒ **反向用例 MUST NOT** 用「L1 → L1」构造（否则会把**已冻结的契约层**判红 · 违反 PR-4）
- [X] T019 [P] [US1] 在 `tests/gates/test_gates.py` 写 G26 的**反向用例**：在 `isolated_copy` 的 `src/freegraph/_probe.py` 写 `import socket` ⇒ 断言**失败并指名文件 + 行号**（FR-009 ①）。**⚠️ MUST 以 `--root <isolated_copy>` 调用 G26**（architecture-gates §2.1）—— 否则注入不可见 ⇒ 用例**空转**
- [X] T020 [P] [US1] 在 `tests/gates/test_gates.py` 写 G29 的**反向用例**：把 `harness/demo/target.py` 的**副本**改一个字 ⇒ 断言**失败并给出 diff**（FR-011 ① · 只读基准不得修改 ⇒ 只读副本）。**⚠️ MUST 以 `--root <isolated_copy>` + `--baseline HEAD` 调用 G29**（architecture-gates §2.1 —— **2026-11-08 分析轮订正 · H2**：CLI 表原**缺 G29 的 `--root`**；`--root` = **被检树根**（被检侧）· `--baseline` = **基准侧**（`git show` 的 ref）⇒ **两者 MUST 成对使用**）—— 基准默认取 `HEAD:harness/demo/target.py`（**仓库内无第二份基准副本**）⇒ 只改副本而不指明被检根，diff 仍比对仓库根的文件 ⇒ 注入**不可见**；**② 退出码约定的反向用例**：把 `harness/demo/graph_core.py` 的**副本**改成抛**非** `NotImplementedError` 的异常 ⇒ 断言 G29 判为**真断言失败**（退出码 1 且失败来源**非** `NotImplementedError` ⇒ 门禁**红**）；**③ 环境未就绪的反向用例**：副本**保持原样**（freegraph 可导入 ⇒ 用例体因 `NotImplementedError` 全失败）⇒ 断言 G29 判为**环境未就绪**（退出码 1 但失败**全部**源于 `NotImplementedError` ⇒ 门禁**绿**）—— 立项书 §9.2 的 0/1/2 语义「内核未开工时 CI 应显示『环境未就绪』而非『验收失败』」的可判定实现
- [X] T021 [P] [US1] 在 `tests/gates/test_gates.py` 写 G30 的**反向用例**：把某文件副本的**首行署名头删掉** ⇒ 断言**失败并指名该文件**（FR-013 ③）；**② 第三方品牌资产的反向用例**：在 `isolated_copy` 放一个第三方 logo 的 `.svg` ⇒ 断言 G30 **失败**并指名该文件（宪法原则 IX 第三条 · spec **FR-021** / SC-016 · 立项书 §9.1 门禁 2 · 契约 G30 **判定第 6 项**）。**⚠️ MUST 以 `--root <isolated_copy>` 调用 G30**（architecture-gates §2.1）—— 否则注入不可见 ⇒ 用例**空转**。**⚠️ 三个子域的负向验证覆盖面（2026-11-08 分析轮订正 · 与 spec SC-016 限定语一致）**：**图像资产**子域 MUST 有负向用例（上文 `.svg`）⇒ 强制；**品牌色值 / "Approved copy" 文案**两个子域在各自的具名清单为**空集**时**无法**构造可判定负向用例 ⇒ **MUST NOT** 记作「已通过」⇒ 在人工验证记录中标注「**待取证**」（spec FR-021 ①「判定分工」）。

### Implementation for User Story 1

- [X] T022 [US1] 创建 `harness/scripts/gates/gate_G21_dependencies.py`（署名头 + docstring）：声明级判黑名单 —— 枚举 **6 个 extras 变体**（T012）⇒ 逐变体展开闭包 ⇒ 命中黑名单（`langsmith` 精确名 + `langsmith-*` · 前缀 `langchain` · 前缀 `langgraph` · 精确 `deepagents`）⇒ 失败；**点名名单** `langgraph-api` / `langgraph-runtime-inmem` / `phoenix` **额外拦截**（ELv2 · FR-006 ①）；报错 MUST 含**包名** + **出现在哪个变体**（architecture-gates.md G21）；**CLI 契约**：MUST 支持 `--project <pyproject 路径>`（指向被检的 `pyproject.toml`，默认当前仓库根）—— 否则 quickstart §2.4 的手工复现跑不通
- [X] T023 [US1] 创建 `harness/scripts/gates/gate_G23_licenses.py`（署名头 + docstring）：对**全部 extras 变体的闭包并集**逐包判许可证 ⇒ **被检查包集合 =（闭包并集）∪（`--root` 下扫到的 `*.dist-info` / `*.egg-info` 所对应的包）**（**并集口径** · spec **裁定 25** / architecture-gates G23 📌 块）⇒ 许可证据**先**取 `--root` 下元数据、**后**回落**已安装**元数据；**MUST NOT** 只查 `--root`（正常路径一个包都查不到 ⇒ **空门禁 ⇒ 违宪**），也 **MUST NOT** 只查已安装包（反向用例**空转**）—— 四级证据链取标识（T011）⇒ SPDX 叶子判定（T011）⇒ **每个叶子都须 ∈ 5 个白名单 id**；命中禁用清单（Elastic-2.0 / AGPL / SSPL / BUSL / GPL-2 / GPL-3 / MPL-2.0 / LGPL）⇒ 失败并**点名**；**取不到证明 ⇒ 失败并指名**（MUST NOT skip · architecture-gates.md G23）
- [X] T024 [US1] 创建 `harness/scripts/gates/gate_G24_config_layer.py`（署名头 + docstring）：AST 扫描 `src/freegraph/**` ⇒ 断言**零** `LANGSMITH_*` / `LANGCHAIN_*` / `LANGGRAPH_CLOUD_LICENSE_KEY` / `LANGGRAPH_AUTH*` 读取，**且零**任何环境变量读取；**扫描域 MUST 限于 `src/freegraph/**`**（MUST NOT 扫门禁脚本 / 测试夹具 / CI 配置 —— 否则门禁把自己判红 · FR-007 ①）
- [X] T025 [US1] 创建 `harness/scripts/gates/gate_G26_network_static.py`（署名头 + docstring）：AST 扫描 `src/freegraph/**` ⇒ 断言**零**网络客户端调用（清单见 architecture-gates.md G26）；例外名单（可选 OTLP exporter 模块）**当前为空**，MUST 以**显式名单**表达，MUST NOT 放宽扫描域（FR-009 ① · FR-018 ①）
- [X] T026 [US1] 创建 `harness/scripts/gates/gate_G25_import_graph.py`（署名头 + docstring）：读层注册表（T009）+ AST 扫描 import（T010）⇒ 断言层间方向**单向**（L1→L6 递增）；跨层单元只可 import L1 及更低、且 MUST NOT 被 L2–L5 import；**承认** `facade-L1-L3` 例外（由注册表声明，MUST NOT 硬编码在实现里 · FR-008 ①）
- [X] T027 [US1] 创建 `harness/scripts/gates/gate_G29_contract_carrier.py`（署名头 + docstring）：① 用 `difflib` 断言 `harness/demo/target.py` 与**入库基准**逐字相同 ⇒ 改动即失败（**不设「已批准豁免」通道**）；**基准载体 MUST 明确**：`git show <--baseline ref>:harness/demo/target.py`（默认 `HEAD`）—— **仓库内无第二份基准副本**（MUST NOT 依赖「仓库内另一份文件」）；② 断言 **C4 / C8 两条回归测试的挂载点存在**且**明确标记为「未落地」**（MUST NOT 伪装成「已通过」 · FR-011 ②）；③ `--check-compat` 模式：**只**负责 `COMPAT.md` 的**分层判定** —— `COMPAT.md` **存在** ⇒ **严格比对并阻断**（退出码非 0，并指名**哪一行、哪一个符号** · FR-012 ②③④）；`COMPAT.md` **不存在** ⇒ 输出「**未落地**」且**退出码 0**（非阻断 · MUST NOT 静默跳过 · 裁定 13 · research D-14）；⇒「**自动转为严格比对**」由**文件是否存在**驱动，**同一套判据、无需改门禁实现**（FR-012 ②）。**README.md「API 兼容矩阵」章节的严格比对由既有门禁 G8 / G19 承担**（pytest 步骤已跑）⇒ 本模式 MUST **引用**其判据来源、MUST NOT **重复实现**（裁定 8 第三条理由：避免「同一判据两处实现」）；④ **验收脚本集退出码断言**（立项书 §9.1 门禁 3 的「原样可跑」半边）：跑 `harness/demo/{graph_core,agent_loop,visualization}.py` ⇒ 断言退出码 ∈ **{0, 1, 2}**。**⚠️ 退出码 MUST 按「失败来源」细分（2026-11-07 分析轮定案 · MUST 照此实现）**：CI 中 freegraph **已安装** ⇒ 三个脚本 import 成功 ⇒ 退出码 **2** 的分支（`except ImportError`）**不触发** ⇒ 脚本走到用例体并因 `NotImplementedError` 被记为**断言失败** ⇒ **退出码为 1**（**实测**：freegraph 可导入时三者退出码**全为 1**；不可导入时才是 2）⇒ 故：**1 且全部失败均源于 `NotImplementedError`** ⇒ 判为**环境未就绪**（**通过**）；**1 且存在非 `NotImplementedError` 的失败** ⇒ 判为**真断言失败** ⇒ **CI 失败**。落地时 MUST **解析脚本输出**以区分失败来源（**MUST NOT 只看退出码**）—— 这即 立项书 §9.2「内核未开工时 CI 应显示『环境未就绪』而非『验收失败』」的可判定实现（**原「∈ {0, 2}」口径在 CI 条件下必然失败 ⇒ 7/7 作业全红，违反 PR-4**）。**⚠️ 脚本集合的边界（2026-11-08 分析轮订正 · M10）**：本条只断言 **3 个**脚本（`graph_core` / `agent_loop` / `visualization`）—— `harness/demo/` 下另有两个 `.py`：**`target.py`**（只读基准 · 需 fake / 真实模型注入 ⇒ 归 **B25F1**）与 **`acceptance.py`**（人工验收编排器 · 其退出码断言**归 B25F1**（双跑验收））⇒ 本 feature **只登记不判定** ⇒ **MUST NOT** 把它们算进本条的退出码集合或反向用例
- [X] T028 [US1] 创建 `harness/scripts/gates/gate_G30_attribution.py`（署名头 + docstring）：用 `git ls-files '*.py'` 取全仓受版本控制的 `.py`（`src/` + `tests/` + `harness/`，**无例外目录**）⇒ 逐文件断言**顶部**署名头**逐字相等**——**首行**；**首行是 shebang 时取第二行**（宪法原则 X · FR-013 ② · 与契约 architecture-gates.md G30 §1.4 逐字一致）；**两个具名例外**：`py.typed` · `harness/demo/target.py`；缺失文件 MUST **逐个指名**（MUST NOT 只报总数 · FR-013 ③④）；**② 第三方品牌资产断言**（宪法原则 IX 第三条 · spec **FR-021** / **SC-016** · 立项书 §9.1 门禁 2 · 契约 G30 **判定第 6 项**）：断言仓库内**无第三方品牌资产** —— 三类扫描域（FR-021 ①）：**图像资产**（`.svg` / `.png` / `.ico` / `.jpg` / `.jpeg` / `.webp` / `.gif` 等）、**品牌色定义**（样式文件与文档中的第三方品牌色值）、**官方 "Approved copy" 描述文案**。**⚠️ 前置动作（2026-11-08 分析轮定案）**：MUST 先按契约 G30 **判定第 6 项**的**两份具名清单**实现判定（**禁止色值清单** + **禁止文案指纹清单**）—— **禁止文案指纹清单的 3 条**已由 `harness/reports/Q7-开源边界地图与许可证合规.md` §3.3.3（来源 **D10** · `https://www.langchain.com/brand-assets` · as-of **2026-11-01**）提供指纹片段，可直接落入契约；**禁止色值清单**当前为**空集**（官方品牌色值**尚未逐字取证**）⇒ **MUST NOT** 凭记忆写入 hex（原则 VIII）⇒ 该子域按「清单为空 ⇒ 天然成立，但 MUST NOT 记作『已自动判定』」处理，并在人工验证记录中标注「**待取证**」。**扫描域**：图像资产按扩展名全量；两个清单子域扫受版本控制的 **`.md` 文档** + **`.css` / `.scss`**。**⚠️ 白名单口径 MUST 用 FR-021 ② 的正确口径（2026-11-07 分析轮定案）**：= **禁止第三方品牌资产**；**自有资产**（项目自有 logo / 架构图 / 演示截图）MUST 登记在**已具名的「自有品牌资产白名单」**中（**当前为空集** —— **实测**：仓库内无任何受版本控制的图像 / 样式文件，README 无第三方品牌色值与官方 Approved copy 文案 ⇒ 「白名单外图像文件数 == 0」当前**天然成立**）⇒ **MUST NOT** 采用「白名单为空 ⇒ 禁止一切图像」的过宽口径（那会连**自有** logo 一并禁掉，**超出**宪法原则 IX 第三条范围）；违例 MUST **逐个指名**（文件路径）。**③ 与既有 G8 的分工**：原则 IX 第三条第 ③ 项（README / 文档 MUST 声明「独立实现、非 LangChain Inc. 产品」）**已由既有 G8 覆盖**（`INDEPENDENCE_STATEMENT` 断言 + `test_compat_matrix_declares_no_affiliation`）⇒ 本门禁 **MUST NOT** 重复实现该条（FR-021 ③）
- [X] T029 [US1] 在 `tests/gates/test_gates.py` 写**负向验证的端到端用例**（本 feature 的**验收判据 A1**（引文 §6 · 门禁生效 = 负向验证 · 对应**执行闸口 A2**）· SC-001）：在 `isolated_copy`（T014）里注入 `langchain-core` ⇒ 断言 G21 **失败**且输出含违规条目 ⇒ 撤销后断言**通过** ⇒ 断言**原工作树 `git status` 干净**（逐字不变 · 裁定 9 · SC-010）；**CLI 契约**：G21 MUST 支持 `--self-test-negative`（内置跑一遍负向验证并以退出码表态）—— 否则 quickstart §2.4 跑不通；**副本构造 MUST 复用 `_gatekit.make_isolated_copy()`（T008）** —— MUST NOT 另写一份拷贝逻辑（否则与 pytest 夹具 T014 漂移：一处拷 `README.md`/`LICENSE`、一处不拷 ⇒ G22 在构建阶段失败）；**退出码语义（必须写死 · 2026-11-07 分析轮补入）**：**自检通过 ⇒ 退出码 0**（其内部断言的是「门禁**必须**失败」）；**自检失败 ⇒ 退出码非 0** ⇒ 该模式可安全地作为 CI 的一步（否则「非 0 = 失败」的 CI 语义会把它判红）
- [X] T030 [US1] 创建 `.github/workflows/ci.yml`：**7 个作业**（`ubuntu-24.04` × {3.11, 3.14} · `macos-15` × {3.11, 3.14} · `windows-2025` × {3.11, 3.14} · `ubuntu-24.04-arm` × 3.11）—— **runner 标签 MUST 钉死**（MUST NOT 用 `latest` 等浮动标签 · FR-015 ④③）；**每个 job 的 `name:` MUST 逐字等于 contracts/ci-matrix.md §4.1 的 7 个检查名**（`gates (<runner>, <Python>)`）—— GitHub 的 required check 按 job 名**精确匹配** ⇒ 名字不符则分支保护**静默失效**（FR-020③ 的「已启用」名存实亡）；**既有门禁 G9**（typing 构件上限静态断言）**随 pytest 步骤在 7/7 作业执行**（**FR-017** · 只接线 · 判据零改动）；每作业步骤顺序照 contracts/ci-matrix.md §2：`checkout@v7` → `setup-python@v5` → `setup-uv@v10.3.3` → **`uv venv --python <矩阵档位>`** → **`uv pip install --python .venv --group dev`** → **`uv pip install --python .venv -e .`** → **`uv pip install --python .venv -e ".[pydantic,checkpoint,otel,png]"`** → **`uv run --no-project --python .venv python -m pytest tests/ -ra`** → **逐条**门禁调用（`uv run --no-project --python .venv python harness/scripts/gates/gate_GNN_*.py`）→ 兼容矩阵分层报告。**⚠️ 四项必做约束（2026-11-08 分析轮补入 / 订正）**：① **MUST 建 venv** —— `uv pip install` 在**无活动虚拟环境**时报 `No virtual environment found` 并以**退出码 2** 失败（**实测**）⇒ 无 venv 步骤则**步骤 4 在 7/7 作业上直接失败**；② **解释器路径 MUST 跨平台（2026-11-08 分析轮订正 · C1）** —— 命令串**只出现 venv 目录 `.venv`**（安装用 `uv pip install --python .venv …`、调用用 `uv run --no-project --python .venv python …`；`--no-project` ⇒ uv **不解析项目、不同步环境** ⇒ MUST NOT 让它把已装的四个 extras 依赖卸掉）⇒ **MUST NOT** 出现任何平台专属的解释器路径（POSIX 的 `bin/` 布局 / Windows 的 `Scripts\` 布局）—— 否则 `windows-2025` 的 2 个作业**每一条命令**路径失效 ⇒ **必红**（违反 PR-4）；`FREEGRAPH_TEST_INSTALLED=1` MUST 写在 job 的 `env:` 段（三个平台通用），MUST NOT 用平台专属的变量前缀语法；③ **四个 extras 的依赖 MUST 在全部 7 个作业上安装**（**不再仅限 Linux 全量作业** · **FR-015 ⑤**）—— 否则非 Linux 作业的 G21 因「未安装 ⇒ 判失败」而**必红**（**实测**：仅装基础包时 `importlib.metadata.requires('pydantic')` 抛 `PackageNotFoundError`）；`playwright` **只装 Python 包、不装浏览器二进制**；④ **既有门禁 G9 MUST 随 pytest 步骤在 7/7 作业执行**（FR-017 · 静态断言在 3.11 档给出「你用了 3.12+ 的 X」的可读报错 · 辅判定）；**⑤ 步骤 6 的「按平台条件追加 marker 过滤」MUST 用矩阵变量承载**（`matrix.pytest_args`）—— 配方见 `contracts/ci-matrix.md` §2 步骤 6 的「📌 实现配方」：Linux 三档 = **空串**（**不过滤** ⇒ `linux_only` 用例在 Linux 上必须真的跑）、非 Linux 四档 = `-m "not linux_only and not full_install"` ⇒ **MUST NOT** 把过滤条件写进 `pyproject.toml` 的 `addopts`（否则 Linux 档也过滤 ⇒ G22 的 pytest 断言永不执行 ⇒ 门禁静默失效）；触发条件 = `push` 到 `main` + `pull_request` + `workflow_dispatch`
- [X] T031 [US1] 在 `.github/workflows/ci.yml` 加**逐条门禁调用**段（= ci-matrix §2 **步骤 7**）：**步骤 7 的调用集合 = 7 条**（**G21 · G23 · G24 · G25 · G26 · G29 · G30**）—— **三个平台逐字相同**；**Linux 作业的「全量门禁」= 步骤 7 的 7 条 ＋ 步骤 9 的 3 条（G22 · G27 · G28）= 10 条**（步骤 9 见 **T040 / T044**）；非 Linux 作业调**同一组子集** = **G21 · G23 · G24 · G25 · G26 · G29 · G30**（**2026-11-08 分析轮订正 · H6**：**G23 已纳入子集** —— 其判据是**纯元数据读取**、跨平台无差异；原以「须完整安装环境才能取到许可证据」为由排除的理由**已随 extras 7/7 装齐而失效** ⇒ **被排除的只剩 G22（隔离 venv）· G27 的独立可执行入口（socket 夹具）· G28（断网 · Linux 专属）**）；每条 MUST **独立调用 + 独立退出码**（MUST NOT 只跑一条聚合命令 · FR-016）；**MUST 另加一步** `gate_G29_contract_carrier.py --check-compat`（当前退出码 0 + 明确的「`COMPAT.md` **未落地**」输出行）⇒ SC-011 的「非阻断报告」才真正出现在 CI 输出里；**当 `COMPAT.md` 存在时该步骤 MUST 自动转为严格比对**：**有不一致** ⇒ 以非 0 退出并指名**哪一行、哪一个符号**；**一致** ⇒ 退出码 0（**MUST NOT** 仅因「文件存在」而非 0 —— 否则后续 feature 建出 `COMPAT.md` 后该步骤**永久红**，违宪 v1.6.0 红线「MUST NOT 写永久红的 CI」· FR-012 ② · architecture-gates §2.1 CLI 表）；**⚠️ 步骤 7 MUST NOT 含 G22 / G27 / G28**（**2026-11-08 分析轮订正 · M4**）—— 它们在**步骤 9**（Linux only）⇒ 否则 Linux 作业上 G22 / G28 会被**跑两遍**；**⚠️ G27 的平台分工 MUST 写死（2026-11-08 分析轮订正 · M5）**：**G27 的独立可执行入口 = Linux only**（步骤 9）· **G27 的 pytest 夹具断言 = 全平台**（步骤 6 的测试套件内 ⇒ **MUST NOT** 打 `@pytest.mark.linux_only`）；**⚠️ 非 Linux 作业的 pytest 步骤 MUST 同步带标记过滤**（`-m "not linux_only and not full_install"`）—— G22 的用例在 `tests/gates/test_gates.py` 内，而「子集」的定义**只管门禁脚本调用、管不到 pytest 内的用例** ⇒ 不加过滤则 macOS / Windows 作业会执行隔离 venv 用例（需联网安装）⇒ **非 Linux 必红**（与 `contracts/ci-matrix.md` §1 的「子集」定义直接冲突）；**⚠️ 调用 MUST 用跨平台写法** `uv run --no-project --python .venv python …`（与 T030 的 venv 一致 · **MUST NOT** 出现平台专属的解释器路径）；**⚠️ 既有门禁 G9 MUST 随 pytest 步骤在 7/7 作业执行**（FR-017）
- [X] T032 [US1] 在 `.github/workflows/ci.yml` 加**发行产物纯度先行检查**步骤：先 `uv build` 生成产物，再跑 `uv run --no-project --python .venv python harness/scripts/check_dist_purity.py dist/` ⇒ 断言产物**不含** `harness/` / `.specify/` / `.opencode/` / `specs/` / `tests/` 等仓库内容（spec SC-005 · 宪法「发布门禁」第 1 条）—— **MUST NOT** 改动 `.github/workflows/publish.yml`（发布流水线的最终拦截归 B24F1）
- [X] T033 [US1] 在 `README.md`（或 `CONTRIBUTING.md`）加**文档兜底句**：「合入前 CI 必须全绿」—— 作为**分支保护未启用期间**的人工保障，MUST NOT 替代 T034 的设置步骤（FR-020 ⑤）
- [X] T034 [US1] 在 `harness/verification/B3F1/manual-verification.md` 写入**分支保护的可照抄设置步骤**：必过检查的 **7 个 job 名** + 保护分支 `main` + 「必须先通过检查才能合并」+ 「要求分支保持最新」+ 「管理员也必须遵守」（清单**回指** contracts/ci-matrix.md §4.1 · **MUST NOT** 另抄一份 —— 两份一旦漂移，分支保护即失效 · FR-020 ②；**MUST NOT** 声称已代为设置 —— 本环境无 `gh` CLI、无 GitHub 令牌 · FR-020 ①）

**Checkpoint**：负向验证通过（门禁失败 + 工作树不变）· 7 条门禁退出码全 0 · `pytest tests/ -ra` 全绿

---

## Phase 4: User Story 2 - freegraph 自己不偷偷联网（Priority: P2）

**Goal**：零出站的**动态**判定（G27）与**断网等价性**（G28）落地，且**只观测不阻断**、按**第一个非标准库帧**归因。

**Independent Test**：运行门禁时，socket 监测夹具记录的「**框架出站**」条目数为 **0**；
用户代码主动发出的连接被**记录在案但不判失败**；全部网络接口不可用后**核心用例全绿**（spec SC-006 / SC-004）。

### Tests for User Story 2

- [X] T035 [P] [US2] 在 `tests/gates/test_gates.py` 写**归因函数的四种栈形态单元断言**（**合成调用栈**驱动，MUST NOT 依赖真实出网 · FR-009 ②③）：① freegraph 内部模块直接联网 ⇒ `framework`；② 用户工具函数联网、freegraph 只是调用方 ⇒ **`user`**（**不得**误判为 framework —— 否则用户正常用 AI 工具访问外网会每次把门禁打红 · 裁定 19）；③ 用户脚本直接联网 ⇒ `user`；④ freegraph 直接使用 socket ⇒ `framework`
- [X] T036 [P] [US2] 在 `tests/gates/test_gates.py` 写 G27 的**正向断言**：① 在**干净仓库**上跑 G27 ⇒ 断言「**框架出站 == 0**」（SC-006）；② **真实发起一次用户出站**（如连 `127.0.0.1` 的本地端口）⇒ 断言该条被归因为 「**用户出站**」而非「框架出站」（SC-006 的双向可验证）—— **⚠️ 该连接在 CI 上必然失败**（无监听端口 ⇒ `ConnectionRefusedError`）⇒ 夹具 MUST **先记录再放行**（记录发生在 connect 之前）⇒ 用例 MUST **捕获该异常**（`pytest.raises` / `contextlib.suppress`）⇒ **否则未捕获异常 ⇒ 用例失败 ⇒ 7/7 作业必红**—— **该用例 MUST 进断网排除清单**（断网下连接必然失败 · 属**假红**，非 freegraph 缺陷 · FR-010 ③(b)）。**⚠️ 用例函数名 MUST 逐字为 `test_egress_attribution_records_user_egress`**（**2026-11-08 分析轮订正 · A5**）—— 该 node ID 被 `contracts/ci-matrix.md` §3.2 的 `--deselect` 展开式与 `tests/gates/data/offline_exclusions.txt`（T006 / T039）**逐字引用** ⇒ 改名 ⇒ 清单 deselect 落空 ⇒ **断网任务假红**（SC-004）

### Implementation for User Story 2

- [X] T037 [US2] 创建 `harness/scripts/gates/gate_G27_zero_egress.py`（署名头 + docstring）：作为**独立可执行入口**（FR-016 · 退出码即判定 · CI 可逐条调用）调用 `_gatekit` 里的**共享实现**（T013 的 `attribute_egress` + 同一 socket 包装上下文管理器）⇒ 断言「**框架出站**」条目数 **== 0**；「**用户出站**」**记录在案但不判失败**；**MUST NOT** 安装任何出网拦截机制（只包装 `socket.connect` / `socket.create_connection` 并**放行**全部连接 · FR-009 ②③ · 裁定 7）；**MUST NOT** 在本脚本里另写一份归因 / 包装逻辑（「两个入口 · 同一实现」· architecture-gates.md G27）；**⚠️ 被观测面的契约**：本入口的观测面 MUST **非空且显式声明** —— **B3F1 的观测面 = 「在 egress 监测下跑整个测试套件」**（`pytest tests/`，夹具全程监测 · 裁定 7），输出 MUST 同时打印「**当前观测面：测试套件执行期（尚不含内核运行时 —— 运行期待 M2）**」—— MUST NOT 让一个**空断言 / 极窄观测面**被误读为「零出站已被证明」；**SC-006 的双向可验证**（注入一次用户出站 ⇒ 归因为『用户出站』）由 **pytest 夹具路径**承担（T036 · T014 的 `egress_recorder`），本入口**不**承担该反向验证
- [X] T038 [US2] 创建 `harness/scripts/gates/gate_G28_offline_equiv.py`（署名头 + docstring）：读 `tests/gates/data/offline_exclusions.txt`（T006）⇒ 重跑**全量测试套件**（`pytest tests/`）⇒ 断言**通过率 == 100%**；排除项**仅限两类**（断网任务自身 · 必须能建立连接的用例 —— 含 (b1) 用户出站归因 / (b2) 需联网安装的用例），且**逐条有理由**（无理由者 == 0 · SC-004）；**Linux 专属**（FR-010 ① · 裁定 10）。**⚠️ 命名空间的归属（2026-11-08 分析轮订正 · M9 · MUST 照此实现）**：**G28 脚本自身 MUST NOT 调用 `unshare` / MUST NOT 创建网络命名空间** —— 命名空间由**外层**施加（CI 步骤：`unshare --net --map-root-user uv run … gate_G28_offline_equiv.py` · 或人工复现命令 · `contracts/ci-matrix.md` §3.2）⇒ 脚本在**已断网**的环境内只负责：读清单 → 逐条转 `--deselect` → 跑 `pytest tests/` → 断言通过率 == 100%。**⚠️ 排除清单 MUST 自校验（2026-11-08 分析轮订正 · 关闭 A5 的失败模式）**：**实测 pytest 7.4.4 与 9.2.0 对「指向不存在 node id 的 `--deselect`」均不报错（静默忽略 · 退出码 0）** ⇒ 清单与用例名一旦漂移 ⇒ 排除**静默失效** ⇒ 被排除的用例在断网下**假红**（原因被误判为「断网等价性失败」）⇒ 本脚本 MUST **逐条比对清单标识与实际收集到的 node ID 全集**：不存在 ⇒ **判失败并指名该条**；存在 ⇒ 确认它**确实被排除**（architecture-gates G28 §5）。**MUST NOT** 自行嵌套 `unshare`（否则语义含糊，且 macOS / Windows 上不可用）
- [X] T039 [US2] 定稿 `tests/gates/data/offline_exclusions.txt`：把 T036 里「必须能建立连接」的用例（真实用户出站那条 · FR-010 ③(b1)）**与** G22 隔离 venv 一族用例（**T041 / T042** —— `uv venv` + `uv pip install` 需联网 ⇒ 断网下必假红 · FR-010 ③(b2)）**逐条**登记（`用例标识 :: 理由`），并写明**新测试的入册判据**（FR-010 ⑤）—— MUST NOT 靠临时跳过 / 运行时打桩。**⚠️ 排除的施加方式 MUST 与 `contracts/ci-matrix.md` §3.2 逐字一致（2026-11-08 分析轮订正 · H7）**：**排除清单 = 单文件**（`tests/gates/data/offline_exclusions.txt` · **逐条带理由**）⇒ **G28 门禁脚本 MUST 读它并逐条转成 pytest 的 `--deselect` 参数**；**MUST NOT** 另立第二份清单、**MUST NOT** 用未注册的 marker 过滤（否则两处口径漂移）⇒ **MUST NOT** 照抄「不带排除清单的裸 `pytest tests/ -ra`」——那会在被排除的用例上**假红** ⇒ **SC-004 必假红**。**⚠️ 清单条目数 MUST 恰为 3 条（2026-11-08 分析轮订正 · M8）**：T036 的用户出站用例 + T041 + T042 —— **T043 是门禁脚本 `gate_G22_isolated_env.py` 的创建任务 · 不是 pytest 用例** ⇒ **无法 `--deselect`** ⇒ **MUST NOT** 登记进清单（与 `contracts/ci-matrix.md` §3.2 的手工展开式**逐条一致**：3 条）。**⚠️ 三条标识 MUST 与下述 node ID 逐字一致（2026-11-08 分析轮订正 · A5）**：`tests/gates/test_gates.py::test_egress_attribution_records_user_egress`（T036）· `tests/gates/test_gates.py::test_g22_isolated_env_closure_is_empty`（T041）· `tests/gates/test_gates.py::test_g22_isolated_env_negative_case`（T042）—— 与 `contracts/ci-matrix.md` §3.2 的 `--deselect` 展开式**逐字相同** ⇒ 改名即漂移 ⇒ **断网任务假红**（SC-004）
- [X] T040 [US2] 在 `.github/workflows/ci.yml` 加 **G27 / G28 的 Linux 专属步骤**：G28 用 `unshare --net --map-root-user`（**无特权** · 网络命名空间 ⇒ 全部网络接口不可用 · research D-08）且**MUST 显式施加断网排除清单**（调 `gate_G28_offline_equiv.py`（脚本内部读清单并逐条转 `--deselect`）**或** 直接传等价的 `--deselect` 展开式 —— 二者**取其一**且**MUST 与 `contracts/ci-matrix.md` §3.2 逐字一致**）；G27 的**独立可执行入口**在测试执行期间监测；**非 Linux 作业 MUST NOT** 含这两条。**⚠️ G27 的平台分工 MUST 写死（2026-11-08 分析轮订正 · M5）**：**G27 的独立可执行入口 = Linux only**（本步骤）· **G27 的 pytest 夹具断言 = 全平台**（在 §2 步骤 6 的测试套件内执行 ⇒ **MUST NOT** 打 `@pytest.mark.linux_only`）⇒ 二者**不是**同一条命令

**Checkpoint**：G27 报「框架出站 = 0」；`unshare --net --map-root-user` 下 `pytest tests/` 全绿；排除清单每条都有理由

---

## Phase 5: User Story 3 - 基础安装足够轻（Priority: P3）

**Goal**：**隔离环境**断言（G22）落地 —— 证明基础安装真的零第三方依赖，且 `import freegraph` 不带进任何 langchain 家族。

**Independent Test**：隔离 venv 中只装基础包后，第三方依赖闭包 **== 空集**，且 `sys.modules` 中无 `langsmith` / `langchain_core` / `langgraph`（spec SC-002 / FR-005 ②）。

### Tests for User Story 3

- [X] T041 [P] [US3] 在 `tests/gates/test_gates.py` 写 G22 的**正向断言**（**须打 `@pytest.mark.linux_only`** —— G22 需隔离 venv + 联网安装 ⇒ 非 Linux 作业 MUST 跳过 · **H3**）：隔离 venv 中装基础包 ⇒ 断言第三方依赖闭包 **== 空集**；`import freegraph` 后断言 `sys.modules` 中**无** `langsmith` / `langchain_core` / `langgraph`（FR-005 ② · SC-002）。**⚠️ 用例函数名 MUST 逐字为 `test_g22_isolated_env_closure_is_empty`**（**2026-11-08 分析轮订正 · A5**）—— 与 `contracts/ci-matrix.md` §3.2 的 `--deselect` 展开式及 `tests/gates/data/offline_exclusions.txt` 逐字一致

### Implementation for User Story 3

- [X] T042 [P] [US3] 在 `tests/gates/test_gates.py` 写 G22 的**反向用例**（**须打 `@pytest.mark.linux_only`** —— G22 需隔离 venv + 联网安装 ⇒ 非 Linux 作业 MUST 跳过 · **H3**）：**① 声明级**：在 `isolated_copy` 的 `pyproject.toml` 注入 `langchain-core` ⇒ 以 `--target-root <isolated_copy>` 调用 G22 ⇒ 断言 G22 **失败**并指名该包（§8 条强制反向用例的最后一条 · FR-014 ② · SC-009）；**② 环境② 场景的反向用例（FR-005 ③① · 裁定 22）**：**MUST NOT** 新建 `src/freegraph/_probe.py` —— 顶层包是**惰性空壳**（只暴露 `__version__`，不导入任何子模块）⇒ `_probe.py` **永不被加载** ⇒ 注入落在其上会**空转**；**MUST** 改写副本的 `src/freegraph/__init__.py` ⇒ 以 `--target-root <isolated_copy>` 调用 G22 ⇒ 断言场景② **失败**（证明该断言**不是空转**）。**⚠️ 用例函数名 MUST 逐字为 `test_g22_isolated_env_negative_case`**（**2026-11-08 分析轮订正 · A5**）—— 与 `contracts/ci-matrix.md` §3.2 的 `--deselect` 展开式及 `tests/gates/data/offline_exclusions.txt` 逐字一致。**⚠️ 注入的模块名 MUST 是 `langchain_core`（不是 `langchain` · 2026-11-07 分析轮订正）**：场景② 的 venv 只装了 `langchain-core` —— **实测**：`langchain-core` 只提供顶层包 `langchain_core`、**不提供** `langchain` ⇒ 注入 `import langchain` 会抛 `ModuleNotFoundError`（**导入崩溃**，而非「sys.modules 中出现了 langchain 家族」）⇒ 该反向用例验证的是**另一件事**、且掩盖了本应验证的断言 ⇒ MUST 注入 `import langchain_core`（该模块**确实已安装**）⇒ `sys.modules` 中出现 `langchain_core` ⇒ 断言真正被触发
- [X] T043 [US3] 创建 `harness/scripts/gates/gate_G22_isolated_env.py`（署名头 + docstring）：**CLI 契约** —— MUST 支持 `--target-root <路径>`（被检的源码根，**默认仓库根**）与 `--project <pyproject 路径>`（**默认 `<target-root>/pyproject.toml`**）⇒ 否则 `isolated_copy` 的注入**无法被本门禁观察到**（T042 ① · **H5**）；用 `uv venv` 在临时目录建**全新虚拟环境** ⇒ `uv pip install <target-root>`（**只装基础包**，不装任何 extra）⇒ 断言**第三方依赖闭包 == 空集** ⇒ 在该环境跑子进程 `import freegraph` 并断言 `sys.modules` 无 langchain 家族（**MUST 在子进程执行** —— 测试进程自身已装 pytest · FR-005 ②）；**② 环境② 场景（FR-005 ③① · 立项书 §9.2 断言③ · 裁定 22）**：在**同一** venv 里**额外** `uv pip install langchain-core` ⇒ 断言 ① freegraph 自身 `Requires-Dist` **无** `langchain*` / `langsmith` / `langgraph*`；② `import freegraph` **及** `import freegraph.graph`（公开 API 门面）后 `sys.modules` 中**从未**出现 `langchain` / `langchain_core` / `langgraph`（运行环境里有 ≠ 被 freegraph 引入）**且零出站**（复用 G27 的归因函数，框架出站 == 0）；**③ FR-005 ③②（运行期 · 最小图）本 feature MUST NOT 实现** —— 待 B6F1（建图）/ B7F2（compile）/ B7F3（invoke）交付内核运行时后由 **M2** 承接（**裁定 22** · 里程碑依据 立项书 §6.2）
- [X] T044 [US3] 在 `.github/workflows/ci.yml` 加 **G22 的 Linux 专属步骤**（独立 step，独占超时预算）—— 非 Linux 作业不含此条（ci-matrix.md §1 的「子集」定义）
- [X] T045 [US3] 在 `tests/gates/test_gates.py` 写**脚手架断言**：**基础安装的闭包为空集** —— 断言 `importlib.metadata.requires("freegraph")` 中**没有任何不带 `extra ==` 标记的条目**（即**基础安装**不拉起任何 extra 的依赖）。（**⚠️ 口径订正 · 2026-11-07 实测**：断言「`Requires-Dist` 为 `None`」**不成立** —— 声明 4 个 extras 后 `requires()` 返回**带 `extra ==` 标记的 5 个条目**（`pydantic` / `ormsgpack` / `opentelemetry-api` / `opentelemetry-sdk` / `playwright`）；`None` 只在**完全没有任何 `Requires-Dist`** 时出现 ⇒ 该断言须按**「无 marker 的条目 == 0」**表达，**MUST NOT** 写成 `requires() is None`）；四个 extra **各自独立可选**（不装即不拉起其依赖 · FR-004 ①）；`src/freegraph/py.typed` **存在且大小 == 0**（PEP 561 · FR-002）；`requires-python` **恰为** `>=3.11` 且**无任何 `<` 上界**（FR-001 · FR-003 · 裁定 1）

**Checkpoint**：隔离 venv 里第三方包数 == 0；`import freegraph` 的 `sys.modules` 干净

---

## Phase 6: User Story 4 - M0 三个 feature 的补检（Priority: P4）

**Goal**：M0 的三个 feature（B1F1 / B2F1 / B2F2）**从未被门禁守护过** —— 本 feature 给它们补一次人工复核，并把结论写进人工验证记录。

**Independent Test**：人工复核三者的依赖声明与 import 图，得出「无违规」或「已列出具体违规项并给出处置」的结论，并写入 `harness/verification/B3F1/manual-verification.md`（spec US4）。

### Implementation for User Story 4

- [X] T046 [US4] 补检 **M0 三个 feature 的依赖声明**：逐个核对 `src/freegraph/contracts/**`（B1F1 / B2F1）与 `src/freegraph/graph.py` / `_stategraph.py` / `_primitives.py`（B2F2）的 import 面 —— **零** langchain 家族、**零**第三方 import、**零**环境变量读取（既有 G2 / G4 / G17 的范围）⇒ 结论写入 `harness/verification/B3F1/manual-verification.md`
- [X] T047 [US4] 补检 **M0 三个 feature 的 import 图**：对照 `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md` 逐模块核层归属与方向 ⇒ 若发现**反向 import** ⇒ MUST 在本 feature 内修正且**MUST NOT** 改变任何**已冻结的公开面**（C1–C27 / 门面 7 符号）；若修正**必然**触及冻结面 ⇒ 如实登记为**待回溯修正**并**具名**（MUST NOT 引入豁免 · FR-018）⇒ 结论写入人工验证记录
- [X] T048 [US4] 回填 `harness/verification/B3F1/manual-verification.md`（**五段式** · T007 的骨架）：**第 ③ 段「实际输出」** 写 ① **零出站证据**（「框架出站 = 0」的实测输出 · **⚠️ MUST 取自 `_gatekit` 的口径**（裁定 19 · 第一个非标准库帧）⇒ **MUST NOT** 引用 `harness/demo/acceptance.py` 的 `EgressProbe` 结果 —— 它用的是**已被裁定 19 否决**的旧口径「栈里有 `freegraph/` 即框架出站」· 已登记为**已知判据重叠**（plan.md「已登记的判据重叠」表）· 统一到 `_gatekit` 归 **B25F1**）② **断网全绿证据**（`unshare --net` 下的通过率）③ **M0 三 feature 补检结论**（T046 / T047）④ **分支保护设置步骤 + 启用后的状态取证**（FR-020 ②③）⑤ **来源覆盖表**（宪法原则 VIII：每条结论附来源标记）⑥ **⚠️ 三条宪法质量门禁缺口（门禁 3 的 C4/C8 · 门禁 4 的 fake 轮 · 门禁 5 的真实模型轮）的登记与追认状态**（2026-11-08 分析轮订正 · C1 / H6 —— 记录「本 feature 不适用」的理由 + 承接方 **B7F2 / B25F1** + **T057** 的追认状态）；**第 ④ 段「结论」** 写总体结论；**第 ⑤ 段「遗留问题」** 写未决项（**含 T049 与 T057 的追认状态**）；**第 ⑥ 段「移交后续 feature」**（可选 · 同 B2F2）写移交清单

**Checkpoint**：人工验证记录六段齐全 ⇒ 质量门禁第 5 项（人工门禁）可判定

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**：跨故事的收口、合规同步与最终验证。

- [X] T049 **【阻断合入】** 在 `harness/verification/B3F1/manual-verification.md` 记录**发起者对 T003（G3 占位填充 · 裁定 8 的唯一例外）的追认**：追认文字 + 发起者确认 + 日期 —— 未追认前 **MUST NOT 合入**（plan.md「唯一一处例外」· Complexity Tracking）
  > **📌 实现轮状态（2026-11-08）**：发起者人工验收通过 ⇒ **追认已作出**（追认文字 + 发起者确认 + 日期，见 `harness/verification/B3F1/manual-verification.md` §5.1）⇒ 本条**已勾选**。
  > **⚠️ 签名的时序**：追认由**发起者**先作出，实现者**只负责转录与勾选** ⇒ MUST NOT 预签（MUST NOT 由实现者代签 · 宪法 v1.6.0）。
- [X] T050 [P] 同步 `THIRD_PARTY_NOTICES` 文件的 §2「第三方运行时依赖」表的**说明文字**：基础安装依赖闭包**仍为空集**；四个 extra 的依赖为**可选**，各自的许可证 ∈ 白名单（列出**逐包**实测标识：`pydantic` = `MIT` · `pydantic-core` = `MIT` · `annotated-types` = `MIT` · `typing-inspection` = `MIT` · `typing-extensions` = `PSF-2.0`；`ormsgpack` = `Apache-2.0 OR MIT`（两叶皆白名单）；`opentelemetry-api` = `Apache-2.0` · `opentelemetry-sdk` = `Apache-2.0` · `opentelemetry-semantic-conventions` = `Apache-2.0` · `typing-extensions` = `PSF-2.0`；`playwright` = `Apache-2.0` · `greenlet` = `MIT AND PSF-2.0`（两叶皆白名单）· `pyee` = `MIT` · `typing-extensions` = `PSF-2.0`）—— **MUST NOT** 把 extra 依赖登记成**必装**依赖（宪法原则 X）
- [X] T051 [P] 同步 `README.md`：新增/更新「可选依赖（extras）」章节（四个 extra 的用途 + `[png]` = **`playwright`**（**宪法 v1.5.0 已列明** · 本地 Chromium 渲染 · 许可证 `Apache-2.0`）+ **浏览器二进制需用户显式执行 `playwright install chromium`**（属**安装期**动作）+ **运行期零出站**（Chromium **本地**渲染 ⇒ 图片不外传）· research D-04；**MUST NOT** 把「mermaid 相关」这一**已被宪法 v1.5.0 取代**的类别式表述写成 `[png]` 的规范表述）；**兼容矩阵章节保持 23 行逐字不动**（由既有 G8 / G19 判）
- [X] T052 **双档验证**：在 **CPython 3.11**（最低档）与 **3.14**（最高档）各跑一次 `FREEGRAPH_TEST_INSTALLED=1 pytest tests/ -ra` ⇒ 两档**全绿**（3.11 档是「typing 构件上限 = 3.11」的**主判定** · FR-015 ① · SC-002b）；把两档的实际命令与输出记入 `harness/verification/B3F1/manual-verification.md`
- [X] T053 **走查 `quickstart.md` 的全部 10 节**（§1 脚手架 · §2 依赖门禁含★负向验证 · §3 静态门禁 · §4 运行时门禁 · §5 全量测试 · §6 矩阵模拟 · §7 分支保护 · §8 兼容矩阵分层 · §9 常见失败处置 · §10 完工检查表）⇒ 逐条记录实测输出到 `harness/verification/B3F1/manual-verification.md`
- [X] T054 回填**实现后行数实测**到 `specs/b3f1-scaffold-ci-gates/plan.md` 的「Scale/Scope」小节（实现行数 / 测试行数 / 文档行数三项），并与立项书 §5.2 的「1,100 行」估算对照 —— **登记，不改立项书**（沿用 B2F2 的「行数口径」做法）
- [X] T055 复核**质量门禁 7 项**在 CI 中的落地并写入 `harness/verification/B3F1/manual-verification.md`（SC-003）：① 规格门禁 —— `specs/b3f1-scaffold-ci-gates/spec.md` + 本文件可逐条勾选；② 依赖门禁 —— G21 / G23 / G24；③ 契约门禁 —— G29（**⚠️ 其中「MUST 包含 C4 与 C8」在本 feature 不适用** ⇒ 只落挂载点并标「未落地」⇒ **偏离登记 · T057 追认** · 2026-11-08 分析轮订正 C1 / H6）；④ 自动门禁 —— CI 全绿 + 零出站（G27）（**⚠️ 其中「fake 模型跑通验收基线的一轮」在本 feature 不适用** ⇒ 以 G29 ② 的退出码细分**部分落地** ⇒ **偏离登记 · T057 追认**）；⑤ 人工门禁 —— T048 的记录存在且非空（**⚠️ 其中「含真实模型一轮」在本 feature 不适用**（无图可跑）⇒ 以五段式记录 + 零出站 / 断网全绿证据覆盖 ⇒ **偏离登记 · T057 追认**）；⑥ 证据门禁 —— 来源标记；⑦ 文档合规门禁 —— T050 / T051 + 既有 G8 / G19 ⇒ 逐条写明**对应断言**与**是否全自动**（**⚠️ ③④⑤ 三项 MUST 逐条写明「本 feature 不适用 + 偏离登记 + T057 追认状态」** ⇒ 复核 MUST NOT 把它们记成「已通过」）
- [X] T056 [P] 在 `tests/gates/test_gates.py` 写 **SC-003 ① 的「存在性检查」断言**（**不新增门禁编号** —— 保住 data-model 不变量 4「门禁总数 == 30 · 编号连续」· 裁定 4）：断言下列三份工件**存在且非空** —— ① `specs/b3f1-scaffold-ci-gates/spec.md`（规格门禁）；② `harness/verification/B3F1/manual-verification.md`（人工门禁 · **五段式小节齐全**：① 环境 ② 步骤 ③ 实际输出 ④ 结论 ⑤ 遗留问题）；③ **来源覆盖表**（证据门禁 · 宪法原则 VIII —— manual-verification.md 内的一节，断言其**存在且非空**）⇒ 人工 / 规格 / 证据三道**人工评审**门禁被静默跳过时 **CI 变红**（SC-003 ① · 门禁 1 / 5 / 6 的存在性检查自动化）；**MUST NOT** 断言「内容已填」—— 内容复核由 **T055** 人工承担（否则 Phase 1–6 的中间态必红，违反 PR-4）
- [X] T057 **【阻断合入】** 在 `harness/verification/B3F1/manual-verification.md` 记录**发起者对三条宪法质量门禁缺口的追认**（**2026-11-08 分析轮订正 · C1 / H6 · 已拍板 · 三条并案**）：三条缺口**共享同一根因** —— 「MVP 验收基线的跑通需要**内核运行时**，而内核运行时按 立项书 §6.2 属 **M2**（固定脚本最小交付集 = B6F1 / B7F2 / B7F3 / B8F1 / B22F1 / B23F1）；本 feature 是 **M0 地基** feature、**不交付内核功能**」⇒
  > **📌 实现轮状态（2026-11-08）**：**偏离登记已写入**（`harness/verification/B3F1/manual-verification.md` §3.6 的 ①②③ 三行 + §4 的质量门禁复核表 + §5 遗留 #3）⇒ 发起者人工验收通过 ⇒ **追认已作出**（追认文字 + 发起者确认 + 日期，见同文件 §3.6）⇒ 本条**已勾选**。
  > **⚠️ 签名的时序**：追认由**发起者**先作出，实现者**只负责转录与勾选** ⇒ MUST NOT 预签（MUST NOT 由实现者代签 · 宪法 v1.6.0）。
  - **① 宪法「质量门禁 3」的「MUST 包含 C4 与 C8 两条独立回归测试」** —— 本 feature **不适用**（C4 → M1/B5F2 · C8 → M2/B8F1）⇒ 只落**挂载点**并**明确标记为「未落地」**（FR-011 ② · 契约 G29 ③）；
  - **② 宪法「质量门禁 4」的「fake 模型跑通验收基线的一轮」** —— 本 feature **不适用**（内核运行时未接线 · `StateGraph` 的四个方法一律 `raise NotImplementedError`）⇒ 以 **G29 ②** 的「退出码 ∈ {0,1,2} 且退出码 1 且失败全部源于 `NotImplementedError` ⇒ 判为**环境未就绪**」**部分落地**；
  - **③ 宪法「质量门禁 5」+ 原则 V 的「人工验证记录含**真实模型一轮**」** —— 本 feature **不适用**（无图可跑）⇒ 以 T048 的**五段式记录** + 零出站 / 断网全绿的实测证据覆盖；
  ⇒ **追认文字 + 发起者确认 + 日期** —— 未追认前 **MUST NOT 合入**；承接方 **B7F2 / B25F1**。
  > **📌 2026-11-08 分析轮订正（C3 / C1 / H6 · 已拍板）**：本任务是本轮**唯一新增**的任务（任务数 **56 → 57**）⇒
  > **MUST NOT** 改动宪法正文、**MUST NOT** 写一条永久红的 CI（那正是本偏离登记的目的）⇒
  > **偏离登记 + 发起者追认**是本条唯一的处置方式（与 T049 的 G3 例外追认**同级**）。
  > **⚠️ 宪法层面的结构性张力（已由宪法 v1.6.0 消解 · 2026-11-08 发起者批准）**：宪法「每个特性在合入前 MUST 全部通过」与
  > 「M0 feature 不具备跑验收基线的能力」之间的张力，**已由宪法 v1.6.0 新增的「质量门禁的分阶段落地与发起者追认」章节确立通则**
  > （窄口径适用范围 + 「偏离登记 + 发起者追认」双要件 + 四条红线 + 登记与复核）
  > ⇒ 本任务即依该通则执行（**追认文字 + 发起者确认 + 日期** · 落 `manual-verification.md` · **未追认前 MUST NOT 合入**）
  > ⇒ **「宪法尚无通则 ⇒ 需另起一次 MINOR 修订」这一登记项已消解**
  > ⇒ **门禁 3 / 4 / 5 的判据本身一字未改**（v1.6.0 只新增流程性条款，未削弱任何红线）。

---

## Dependencies & Execution Order

> **⚠️ 执行策略（2026-11-07 分析轮定案 · 实现阶段 MUST 遵循）**：**不逐任务人工确认**，改为
> **「批量执行 + Phase 闸口」**——每个 Phase 结束 MUST 跑一次可机读的闸口验证，闸口全绿才进
> 下一 Phase。理由：① 门禁类任务的判据是**退出码**而非「人读结论」，天然适合批量执行 + 机器判定；
> ② tasks.md 已给出编号 / 分组 / 依赖 / 并行关系，调度信息不应靠人工逐条重建；③ 但**每个 Phase
> 的闸口不能省**——它替代「逐任务确认」的位置。**折中**：**Phase 3 / 4 / 5 批量执行**、
> **Phase 1 / 2 / 6 / 7 逐任务过**（Phase 1–2 是地基，extras 声明错了后面全错；Phase 6–7 是
> 人工验证记录与合规同步，本质是人工活）。

### 执行闸口（Phase 闸口 · 每道 MUST 全绿才进下一 Phase）

| 闸口 | 触发点 | MUST 验证 | 关联判据 |
|---|---|---|---|
| **A1** | Phase 1–2 结束 | extras 声明落地 · freegraph 自身 `Requires-Dist` 中**无 `extra ==` 标记的条目 == 0**（**基础安装闭包为空集** —— **口径订正 · 2026-11-07 实测**：声明 4 个 extras 后 `requires()` 返回**带 marker 的 5 个条目**、**非 `None`**；`None` 只在**完全没有 `Requires-Dist`** 时出现）· 四个 extra 的闭包**恰好 12 个包**且与 G3 白名单逐一命中 · `pytest` 与 `packaging` 装得上 · **venv 可建**（`uv venv --python <档位>`） | FR-001/004 · SC-002 |
| **A2** | Phase 3 结束（7 条红线门禁） | **故意注入 `langchain-core` ⇒ CI 必红并指名规则编号 + 修复指引** · 撤销后工作树**逐字未变** · **G29 的退出码按失败来源细分**（`NotImplementedError` ⇒ 环境未就绪 ⇒ 绿；其它失败 ⇒ 红） | FR-014 · SC-001 · SC-009 · SC-010 |
| **A3** | Phase 4–5 结束 | 「框架出站」== **0** · 断网任务全绿 · **隔离 venv 闭包为空集** · 验收环境 `sys.modules` 无 langchain 家族（**③① 声明级 + 导入级** · 裁定 22） | FR-005 ①②③① · FR-009 · FR-010 · SC-002c · SC-006 |
| **A4** | Phase 6–7 结束（**最关键**） | **Linux 全量作业口径的 7 个 CI 作业全绿** ⇒ 满足 PR-4「每个 feature 必须能独立通过门禁」 | FR-015 ④ · SC-012 |
| **A5** | 收官 | **T049 发起者追认**（G3 占位填充 · 裁定 8 唯一例外 · **阻断合入**）· **T057 发起者追认**（**三条**宪法质量门禁缺口：门禁 3 的 C4/C8 · 门禁 4 的 fake 轮 · 门禁 5 的真实模型轮 · **阻断合入**）· FR-020 分支保护的「可照抄的设置步骤」已交付 | FR-016 ② · FR-020 ②③ · SC-015 |

> **📌 编号说明（2026-11-08 分析轮订正 · Q3）**：本表的 **A1–A5 是「执行闸口」**（Phase 闸口 · A1 = Phase 1–2 结束）——
> 而 spec / plan 中的「**验收判据 A1**」是**引文 §6**（= 立项书 §5.2 B3F1 小目标）的编号：
> A1 门禁生效 / A2 依赖闭包干净 / A3 零出站可判定 / A4 导入图单向 / A5 源文件署名头齐备；
> ⇒ **两套编号同名不同义** ⇒ 「**验收判据 A1**」（= 门禁生效 = 负向验证）对应本表的**执行闸口 A2**（Phase 3 结束）
> ⇒ **引用时 MUST 带限定语**（「验收判据 A1（引文 §6）」），MUST NOT 把「验收判据 A1」读成「闸口 A1」。

### 三个 MUST 由发起者亲自出面的闸口（实现阶段只能「备料」，不得代劳）

- **T049 —— G3 占位填充的追认**：净效果变严、判据句逐字未动，但仍是「改既有门禁」⇒ 宪法要求
  **发起者追认留证**（人工验证记录中留证）⇒ 实现 MUST **停下来等追认**，MUST NOT 代签。
- **T057 —— 三条宪法质量门禁缺口的追认（2026-11-08 分析轮新增 + 扩范围 · 与 T049 同级）**：门禁 **3** 的「MUST 包含 C4 与 C8」· 门禁 **4** 的「fake 模型跑通验收基线的一轮」· 门禁 **5** + 原则 V 的「人工记录含**真实模型一轮**」—— 三者**共享同一根因**（验收基线跑通需要**内核运行时**，内核运行时按 立项书 §6.2 属 **M2**；本 feature 属 **M0 地基**、**不交付内核功能**）⇒ 在本 feature **均不适用** ⇒ 以**偏离登记 + 发起者追认**处置 ⇒ 实现 MUST **停下来等追认**，MUST NOT 代签（**MUST NOT** 改宪法正文、**MUST NOT** 写一条永久红的 CI）。
- **FR-020 —— 分支保护**：本机**无 `gh` CLI、无 GitHub 令牌**（已实测）⇒ 只能交付「可照抄的
  设置步骤」；**未启用前该项在人工验证记录中标「未完成」**，MUST NOT 记为通过（FR-020 ③）。

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - US1 → US2 → US3 → US4 **可并行**（文件不重叠，除 T045 依赖 T002 的 extras 声明）
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - 依赖 **T013** 的出站归因函数（Phase 2）
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - 依赖 T002 的 extras 声明（Phase 1）；**T044**（G22 的 CI 接线）依赖 **T043**（G22 实现）的结论；**T045**（脚手架断言）依赖 **T002** 的 extras 声明
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) - 依赖 **T046 / T047** 的补检结论（Phase 6 内）；**T048** 依赖 T034（分支保护设置步骤）与 T036 / T038 的实测输出

### Within Each User Story

- **反向用例 MUST 先写并确认失败**，再实现门禁
- 共享库（`_gatekit.py`）先于门禁脚本；门禁脚本先于 CI 接线
- 门禁脚本先于 CI 接线；CI 接线先于人工取证
- Story complete before moving to next priority

### Parallel Opportunities

- T001 / T004 / T005 / T006 / T007 可并行（不同文件）
- T015 – T021（7 条反向用例）可并行（同一文件 `tests/gates/test_gates.py` ⇒ **实现时须串行合并**，但**编写**可并行）
- T022 – T028（7 个门禁脚本）可并行（不同文件）
- T035 / T036 / T041 / T042 可并行（不同故事）
- T050 / T051 可并行（不同文件）
- **⚠️ 顺序约束（2026-11-07 分析轮补入 · 非并行项）**：**T030 与 T031 MUST 串行**（同文件 `ci.yml` ⇒ **不同文件**方可并行 · 本文件 `[P]` 定义）——
  **T014 MUST 先于 T015–T021 / T042 完成** ——
  `isolated_copy` fixture（MUST 含 `README.md` + `LICENSE`）是那些反向用例的**前提**；
  **T011 MUST 先于 T023**（G23 的叶子判定依赖 T011 的 `spdx_leaves`）；
  **T012 MUST 先于 T022**（G21 的 6 变体枚举依赖 T012）。

---

## Parallel Example: User Story 1

```bash
# 7 条反向用例（编写可并行，落盘同文件须串行）
Task: "在 tests/gates/test_gates.py 写 G21 的反向用例（注入 langchain-core）"
Task: "在 tests/gates/test_gates.py 写 G23 的反向用例（AGPL 假元数据 / MIT-CMU 变体 / 四级皆无）"
Task: "在 tests/gates/test_gates.py 写 G24 的反向用例（LANGSMITH_* / os.getenv）"
Task: "在 tests/gates/test_gates.py 写 G25 的反向用例（L1 反向 import L3 / 跨层 import L2）"
Task: "在 tests/gates/test_gates.py 写 G26 的反向用例（import socket）"
Task: "在 tests/gates/test_gates.py 写 G29 的反向用例（target.py 副本改一字）"
Task: "在 tests/gates/test_gates.py 写 G30 的反向用例（删首行署名头）"

# 7 个门禁脚本（不同文件 ⇒ 真并行）
Task: "创建 harness/scripts/gates/gate_G21_dependencies.py"
Task: "创建 harness/scripts/gates/gate_G23_licenses.py"
Task: "创建 harness/scripts/gates/gate_G24_config_layer.py"
Task: "创建 harness/scripts/gates/gate_G25_import_graph.py"
Task: "创建 harness/scripts/gates/gate_G26_network_static.py"
Task: "创建 harness/scripts/gates/gate_G29_contract_carrier.py"
Task: "创建 harness/scripts/gates/gate_G30_attribution.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup（T001 – T007）
2. Complete Phase 2: Foundational（T008 – T014）
3. Complete Phase 3: User Story 1（T015 – T033）
4. **STOP and VALIDATE**：负向验证通过（门禁失败 + 工作树逐字不变）· 7 条门禁退出码全 0
5. **MVP = 「红线会被拦住」** —— 本 feature 的核心交付

### Incremental Delivery

1. Setup + Foundational → 门禁基础设施就位
2. + US1 → **MVP**：红线可被拦住（依赖黑名单 / 许可证 / 配置层 / 导入图 / 网络静态 / 契约载体 / 署名头）
3. + US2 → 零出站可**动态**判定 + 断网可用
4. + US3 → 基础安装零依赖可**隔离**判定
5. + US4 → M0 三个 feature 的补检留痕
6. + Polish → 合规同步 + 双档验证 + 追认

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 的门禁脚本（T022 – T028）
   - Developer B: US1 的反向用例 + 负向验证（T015 – T021 · T029）
   - Developer C: US2 / US3（T035 – T045）
3. Stories complete and integrate independently

---

## 附录 · 任务 ↔ spec 追溯表

| 任务 | FR | SC | 落点 |
|---|---|---|---|
| T001 | FR-016 | SC-002 / SC-004 | pytest 收集范围钉死（裁定 16 的「核心用例」定义）· research D-15 + **注册 `linux_only` / `full_install` 两个 marker**（H3 · 平台专属用例的过滤依据；**MUST NOT** 漏注册，否则 pytest 报 `PytestUnknownMarkWarning`）· **⚠️ 2026-11-08 订正（M1）**：`[dependency-groups] dev` **已存在**（2026-11-08 工作树已落地）⇒ 本任务**只补** `[tool.pytest.ini_options]` 与两个 marker ⇒ **MUST NOT** 写重复的 TOML 表（`tomllib.loads` 会直接报错 · 闸口 A1 失败）· **⚠️ `full_install` 当前无使用者**（M5 · **保留**为预留 marker · 过滤表达式 `-m "not linux_only and not full_install"` 与 ci-matrix §1 / §2 **MUST 保持一致**） |
| T002 | FR-001 / FR-004 / **FR-006 ①①②** | SC-002 | 四个 extra（`[project.optional-dependencies]` · research D-02 / D-03 / D-04）· **`[png]` = `playwright`**（**宪法 v1.5.0 已列明** · Apache-2.0 · 本地 Chromium 渲染 ⇒ plan 只**核验**许可证与零出站，**MUST NOT** 另选后端） |
| T003 | FR-016 ② / **FR-018** | SC-003 / SC-014 | **G3 占位填充**（既有门禁 G3 的两处占位 · 裁定 8 的唯一例外 · research D-06）· **FR-018 的承载**：白名单由 4 个占位包名改为 **12 个确切包名** + 枚举语义修正 ⇒ **净效果 = 变严** ⇒ **不构成放宽**（MUST NOT 以「放宽白名单让它变绿」绕过） |
| T004 | FR-013 ⑤ | SC-008 | **1 个**存量缺头文件补齐（`harness/scripts/audit_feature_drafts.py` · 裁定 5 · 其余 35 个已合规） |
| T005 | — | — | 测试包骨架（`tests/gates/__init__.py`） |
| T006 | FR-010 ④⑤ | SC-004 | 断网排除清单（`offline_exclusions.txt` · 裁定 16 · research D-09） |
| T007 | FR-019 | SC-003 | 人工验证记录骨架（`manual-verification.md`） |
| T008 | FR-016 ① | SC-007 | 统一报告格式（违规条目 + 规则编号 + 修复指引） |
| T009 | FR-008 ② | SC-012 | 层注册表解析器（唯一权威 · research D-07 · **含 §0.3「可判定的声明」的解析** · M10 · **层注册表本身即 CI 矩阵的「架构门禁」实现，故其可判定性计入 SC-012 的矩阵形状核对，而非 SC-002b 的 Python 版本档**） |
| T010 | FR-007 / FR-008 / FR-009 ① | SC-002c / SC-006 | AST 扫描工具（标准库判定用 `sys.stdlib_module_names`）· **环境变量读取覆盖 4 种形态**（含 `from os import environ/getenv/environb` 导入形态 · 与既有 `tests/facade/_gatesupport.py` 同口径） |
| T011 | FR-006 ③④ | SC-013 / SC-014 | 四级证据链 + SPDX 逐叶子（裁定 17 / 18 · research D-05） |
| T012 | FR-005 ① / FR-004 | SC-002 | extras 变体枚举 + 闭包展开（dependency-gate.md §2） |
| T013 | FR-009 ②① | SC-006 | 出站归因（裁定 19 · research D-11） |
| T014 | FR-005 ② / FR-009 ② | SC-006 / SC-010 | 路径基线 + socket 夹具 + 隔离副本夹具（裁定 7 / 9） |
| T015 | FR-005 ① / FR-014 ① | SC-001 / **SC-009** | G21 反向用例（**验收判据 A1**（引文 §6）· 对应执行闸口 **A2** · 8 条强制反向用例之一） |
| T016 | FR-006 ②③ / **FR-006 ⓪**（并集口径 · 裁定 25）/ **FR-018** | SC-013 / SC-014 / **SC-009** | G23 反向用例（8 条强制反向用例之一 · **经 `--root <isolated_copy>` 指向隔离副本** —— H2 · CLI 表原缺 G23 的作用域参数 ⇒ 不指明则注入不可见 ⇒ 用例空转）· **FR-018 的承载**：负向用例证明**黑名单 / 白名单判据未被放宽**（AGPL / `MIT-CMU` 变体 / 四级证据链全无 三种情形均判失败 ⇒ 判据是**严**的，不是「按需扩充」） |
| T017 | FR-007 | SC-002c / **SC-009** | G24 反向用例（8 条强制反向用例之一 · 经 `--root` 指向隔离副本） |
| T018 | FR-008 | SC-012 / **SC-009** | G25 反向用例（8 条强制反向用例之一 · 经 `--root` + `--registry` 指向隔离副本） |
| T019 | FR-009 ① | SC-002c / **SC-009** | G26 反向用例（8 条强制反向用例之一 · 经 `--root` 指向隔离副本） |
| T020 | FR-011 ① | SC-003 / **SC-009** | G29 反向用例（8 条强制反向用例之一 · **退出码按失败来源细分** · 基准经 `--baseline`） |
| T021 | FR-013 ③ / **FR-021** | SC-008 / **SC-009** / **SC-016** | G30 反向用例（8 条强制反向用例之一 · 含**第三方品牌资产**段 · 经 `--root` 指向隔离副本） |
| T022 | FR-005 ① | SC-001 | 门禁 **G21** |
| T023 | FR-006 / **FR-006 ⓪**（并集口径 · 裁定 25） | SC-013 / SC-014 | 门禁 **G23** |
| T024 | FR-007 | SC-002c | 门禁 **G24** |
| T025 | FR-009 ① | SC-002c | 门禁 **G26** |
| T026 | FR-008 | SC-012 | 门禁 **G25** |
| T027 | FR-011 / FR-012 | SC-003 / SC-011 | 门禁 **G29**（含兼容矩阵分层 · 裁定 13 · **README 矩阵比对引用既有 G8/G19、不重复实现**） |
| T028 | FR-013 ③④ / **FR-021** / **FR-018** | SC-008 / **SC-016** | 门禁 **G30**（含**第三方品牌资产**段 · **FR-021**）· **FR-018 的承载**：品牌资产白名单是**已写死的、具名的**例外（FR-021 ④）⇒ **非**「按需新增」的豁免入口 |
| T029 | FR-014 ①② | SC-001 / SC-010 | 负向验证（**验收判据 A1**（引文 §6）· 对应执行闸口 **A2** · 裁定 9） |
| T030 | FR-015 ④⑤ / **FR-017** | SC-002b / SC-012 | CI workflow（7 作业 · runner 钉死 · 裁定 15 · **job 名逐字对齐 ci-matrix §4.1**）+ **建 venv**（`uv venv --python`）+ **dev 组安装**（`uv pip install --python .venv --group dev`）+ **全部 7 个作业装齐四个 extras 的依赖**（G21 / G23 / G3 可判定的前置条件）· **FR-017 的承载**：**既有门禁 G9**（typing 构件上限静态断言）**随 pytest 步骤在 7/7 作业执行**（只接线 · 判据零改动）· **⚠️ 解释器路径跨平台**（C1 · 只出现 venv 目录 `.venv`） |
| T031 | FR-015 ② / FR-016 / **FR-017** | SC-007 / SC-012 / **SC-003 ②** | 逐条门禁调用（Linux 全量 / 其余子集 = **G21 · G23 · G24 · G25 · G26 · G29 · G30** · H6 · **G23 已纳入子集**）· **非 Linux 的 pytest 步骤按 marker 过滤平台专属用例**（`-m "not linux_only and not full_install"`）· **步骤 7 MUST NOT 含 G22 / G27 / G28**（M4）· **G27 的独立入口 = Linux only / pytest 夹具断言 = 全平台**（M5）· **FR-017 的承载**：**既有门禁 G9** 随 pytest 步骤在 7/7 作业执行 · **⚠️ 解释器路径跨平台**（C1 · `uv run --no-project --python .venv python …`） |
| T032 | — | SC-005 | 发行产物纯度**先行检查**（CI 步骤 · **不改** `publish.yml` · 对应宪法「发布门禁」第 1 条 —— 与 `requires-python`（FR-003）无关，故 FR 列留空） |
| T033 | FR-020 ⑤ | SC-015 | 文档兜底句（README / CONTRIBUTING） |
| T034 | FR-020 ①②④ | SC-015 | 分支保护设置步骤（**发起者执行** · 裁定 20 · **FR-020 ①**：本环境无 `gh` / 令牌 ⇒ MUST NOT 声称已代为设置）· **FR-020 ④**：该条**不豁免**任何门禁判据、**不**引入例外机制（它只规定「门禁红了之后的**下一步**被挡住」） |
| T035 | FR-009 ②②③ | SC-006 | 归因四形态单元断言 |
| T036 | FR-009 ② | SC-006 | G27 **正向断言**（框架出站 == 0 + 真实用户出站的归因） |
| T037 | FR-009 ②③ | SC-006 / **SC-006 ①** | 门禁 **G27**（独立入口 = **监测下跑整个测试套件** · 输出 MUST 打印观测面声明） |
| T038 | FR-010 / **FR-010 ②** | SC-004 | 门禁 **G28** |
| T039 | FR-010 ②④⑤ | SC-004 | 排除清单定稿（**单文件** · 逐条理由 · **施加方式 = `--deselect` 逐条列出** · H7 · 与 ci-matrix §3.2 逐字一致） |
| T040 | FR-015 ② / FR-010 ① | SC-004 / SC-012 | G27 / G28 的 Linux 专属接线（**G27 的独立入口 = Linux only · G27 的 pytest 夹具断言 = 全平台** · M5 · **G28 MUST 显式施加断网排除清单** · H7） |
| T041 | FR-005 ② | SC-002 | G22 的正向断言（`@pytest.mark.linux_only`） |
| T042 | FR-014 ② / FR-005 ③① | **SC-009** | G22 反向用例（§8 条强制反向用例的最后一条 · **探针落在副本的 `__init__.py`** —— 顶层包惰性 ⇒ `_probe.py` 不被加载 · 注入 `langchain_core`） |
| T043 | FR-005 ②③① | SC-002 / SC-002c / SC-010 | 门禁 **G22**（含环境② **声明级+导入级**反向断言 · **裁定 22**；③② 运行期延后至 **M2**） |
| T044 | FR-015 ② | SC-012 | G22 的 Linux 专属接线 |
| T045 | FR-002 / FR-003 / FR-004 ① | SC-002 | 脚手架断言（**基础安装闭包为空集**（无 `extra ==` 标记的 `Requires-Dist` 条目 == 0）· extras 独立可选 · `py.typed` 空 · `requires-python` 无上界） |
| T046 | FR-005 / FR-007 | SC-003 | M0 补检 · 依赖声明 |
| T047 | FR-008 | SC-012 | M0 补检 · import 图 |
| T048 | FR-019 / FR-020 ②③ | SC-003 / SC-006 / SC-015 | 人工验证记录回填（`manual-verification.md` · **五段式** · 仓库既有约定 · **含三条宪法质量门禁缺口的登记与追认状态小节** · C1） |
| T049 | FR-016 ② / **FR-020 ④** | SC-003 | **G3 例外的发起者追认**（阻断合入）· **FR-020 ④ 的可审计证据**：唯一例外**具名 + 发起者追认** ⇒ **非**「按需新增」的豁免入口（不豁免任何门禁判据） |
| T050 | FR-006 / FR-018 | SC-014 | `THIRD_PARTY_NOTICES` §2 同步（原则 X） |
| T051 | FR-004 ② | SC-002 / SC-011 | README extras 章节（**`[png]` = `playwright`**（宪法 v1.5.0 已列明）+ **浏览器二进制需用户显式 `playwright install chromium`** + **运行期零出站** · C4）+ 兼容矩阵**逐字不动** |
| T052 | FR-015 ①③ / FR-017 | SC-002b / SC-002c | 双档验证（3.11 / 3.14） |
| T053 | FR-019 | SC-003 | 走查 `quickstart.md` 全部 10 节 |
| T054 | — | — | 行数实测回填（登记，不改立项书） |
| T055 | FR-019 | SC-003 | 质量门禁 7 项落地复核（**③④⑤ 三项 MUST 写明「本 feature 不适用 + 偏离登记 + T057 追认状态」** · C1 / M6） |
| T056 | FR-019 | SC-003 / **SC-003 ①** | **SC-003 ① 的存在性检查**（规格 / 人工 / 证据三道人工评审门禁的存在性断言 · **不新增门禁编号** · **存在性 = 小节标题存在** · 内容复核由 T055 人工承担 · M6） |
| T057 | FR-019 | SC-003 | **三条宪法质量门禁缺口的发起者追认**（阻断合入 · **2026-11-08 分析轮新增 + 扩范围** · C1 / H6 · 与 T049 同级）—— ① **门禁 3** 的「MUST 包含 C4 与 C8」② **门禁 4** 的「fake 模型跑通验收基线的一轮」③ **门禁 5** + 原则 V 的「人工记录含真实模型一轮」—— 三者**共享同一根因**（验收基线跑通需要内核运行时 · 内核运行时按 立项书 §6.2 属 **M2** · 本 feature 不交付内核功能）⇒ ①②③ 在本 feature **均不适用**（② 以 G29 ② 的退出码细分**部分落地**）⇒ **MUST NOT** 改宪法正文、**MUST NOT** 写一条永久红的 CI ⇒ 追认文字 + 发起者确认 + 日期 · 承接方 **B7F2 / B25F1** · **未追认前 MUST NOT 合入** |
