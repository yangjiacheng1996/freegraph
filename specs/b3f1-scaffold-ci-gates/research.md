# Phase 0 · Research: B3F1 · 项目脚手架 + extras 划分 + CI 门禁

**Date**: 2026-11-07 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

> **证据纪律**（宪法原则 VIII）：本文件的每条**事实性结论**都附**可复现的来源标记**——
> ① 实测命令 + 关键输出（`本地路径:行号` 或 PyPI JSON 字段）；② 宪法 / 立项书的**条款定位**。
> 凡**无法核实**者标 `[未验证]`。
>
> **本轮 research 的性质**：本 feature 的绝大多数「未知」**不是**技术选型，而是**实测既有事实**——
> 既有门禁 G3 的行为、PyPI 上真实包的许可证标识、既有 CI 配置。
> 因此本文件以**实测证据**为主，而非「最佳实践」综述。

---

## D-01 · 门禁的载体形态 = 10 个薄壳 + 1 个共享判定库（落在 `harness/scripts/gates/`）

**Decision**

```
harness/scripts/gates/
├── _gatekit.py              # 共享判定库（AST 扫描 / 许可证证据链 / SPDX 表达式 / 出站归因 / 报告格式）
├── gate_G21_dependencies.py     # … 每条门禁一个薄壳：argparse → 调判定 → 打印报告 → 退出码
├── …
└── gate_G30_attribution.py
```

**Rationale**

- spec **FR-016**：「每条门禁 MUST 以**可独立执行**的检查交付（本地可跑、**退出码即判定**），
  并由 CI **逐条调用**；CI MUST NOT 只跑一条聚合命令而使失败条目不可定位」。
  ⇒ 形态上必须是「**一条门禁 = 一个可独立调用的入口**」。
- 但 10 份判据**互有重叠**（G21/G23 都读依赖元数据；G24/G26 都是 AST 扫描；G25 也用 AST），
  ⇒ 重活必须**共享**，否则出现「一处判据两处实现」（裁定 8 的第三条理由：B2F1 / B2F2 已在 G5/G20 上吃过这个亏）。
- **落点选 `harness/scripts/gates/` 而非 `src/freegraph/`**：门禁是**跨层单元**（层 = 「—」·
  立项书 §5.1 的跨层单元清单含「工程设施」），且**发行产物只允许含 `src/freegraph/` + 必要元数据**
  （宪法「发布门禁」第 1 条 · `harness/scripts/check_dist_purity.py` 已断言）⇒ 门禁代码**必须**在 `harness/` 内。
- **沿用仓库既有惯例**：`harness/scripts/check_dist_purity.py` 就是「一个可独立执行 + 退出码即判定」的检查
  （其 docstring：「退出码 0 = 干净」）⇒ 本决策与它**同构**。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 单一 `gate.py --gate G21` 调度器 | 满足「逐条调用」，但 10 条门禁的判据挤在一个文件里（预估 700+ 行），**可读性与可测性**显著下降；且「一条门禁一个文件」与仓库既有 `check_dist_purity.py` 惯例不同构 |
| 全部写成 **pytest 测试**，CI 只跑 `pytest` | **违反 FR-016**（「CI MUST NOT 只跑一条聚合命令」）——pytest 的聚合退出码**无法定位**是哪条门禁失败；且 spec 要求「本地可跑、退出码即判定」的**独立入口** |
| 门禁放进 `tests/` 内 | 门禁是**工程设施**不是测试；且 `tests/` 不进发行包但**也不该**承载「本地独立可跑的检查」 |

---

## D-02 · extras 的四个后端选定 —— 全部经**实测**通过严格白名单

**Decision**

```toml
[project.optional-dependencies]
pydantic  = ["pydantic>=2.0"]
checkpoint = ["ormsgpack>=1.0"]
otel      = ["opentelemetry-api>=1.20", "opentelemetry-sdk>=1.20"]
png       = ["playwright>=1.40"]
```

**Rationale（实测证据 · 2026-11-07）**

白名单 = **{MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, PSF-2.0}**（裁定 18）。
四个 extra 的**完整递归闭包**（不含任何 extra 变体）与**许可证证据**实测如下
（命令：`python3` 走 PyPI JSON API 的 `info.requires_dist` + `info.license_expression` +
`info.classifiers` + `info.license`；见 D-05 的证据链定义）：

| 包 | 闭包（递归，不含 extra） | 每个成员的许可证证据 | 判定 |
|---|---|---|---|
| `pydantic` | `annotated-types` · `pydantic-core` · `typing-extensions` · `typing-inspection` | `MIT` · `MIT` · `PSF-2.0` · `MIT` | ✅ 全绿 |
| `ormsgpack` | **（空）** | `Apache-2.0 OR MIT`（表达式，两叶皆白名单） | ✅ 全绿 |
| `opentelemetry-api` | `typing-extensions` | `PSF-2.0` | ✅ 全绿 |
| `opentelemetry-sdk` | `opentelemetry-api` · `opentelemetry-semantic-conventions` · `typing-extensions` | `Apache-2.0` · `Apache-2.0` · `PSF-2.0` | ✅ 全绿 |
| `playwright` | `greenlet` · `pyee` · `typing-extensions` | `MIT AND PSF-2.0` · `MIT` · `PSF-2.0` | ✅ 全绿 |

**两个关键的表达式事实**（实测）：
- `greenlet` 的 `license_expression` = **`MIT AND PSF-2.0`** ⇒ SPDX 表达式**两个叶子都在白名单** ⇒ 放行；
- `ormsgpack` 的 `license_expression` = **`Apache-2.0 OR MIT`** ⇒ 同上 ⇒ 放行。
  ⇒ **「表达式逐叶子判定」不是理论要求，是真实存在的判定需求**（D-05）。

**Alternatives considered**

| 替代 | 否决理由（实测） |
|---|---|
| `[otel]` 含 `opentelemetry-exporter-otlp`（**spec FR-001 原文**） | 其闭包含 **`requests` → `certifi`（`MPL-2.0`）** ⇒ MPL-2.0 **不在**白名单 ⇒ **被拒**。另含 `protobuf`，其 `License` 字段是散文式 **`3-Clause BSD License`**（非 SPDX id）⇒ 在「精确 id」口径下**无法归一** ⇒ 双重不合规。⇒ 见 **D-03** |
| `[png]` = `cairosvg` | `LGPL-3.0-or-later` ⇒ **传染性 / 限制性**（宪法原则 IX）⇒ 被拒；且其闭包含 `pillow` |
| `[png]` = `svglib` | `LGPL-3.0-or-later` ⇒ 被拒 |
| `[png]` = `pycairo` | `LGPL-2.1-only OR MPL-1.1` ⇒ 被拒 |
| `[png]` = `pillow` | `license_expression` = **`MIT-CMU`**（PyPI）/ `HPND`（本地已装版）⇒ **变体标识符**，裁定 18 明确**不放行** ⇒ 被拒 |
| `[png]` = `matplotlib` | 闭包含 `pillow`（`MIT-CMU` ✗）**且** `numpy` 的表达式 = `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` ⇒ `0BSD` / `Zlib` / `CC0-1.0` **不在**白名单 ⇒ 被拒 |
| `[png]` = `pymupdf` | `Dual Licensed - GNU AFFERO GPL 3.0 or ...` ⇒ **AGPL** ⇒ 被拒（宪法原则 IX 明令） |
| `[png]` = `pikepdf` | `MPL-2.0` ⇒ 被拒 |
| `[png]` = `resvg-py` | **无任何许可证信息**（`license_expression` / `classifier` / `license` 三者皆空）⇒ 四级证据链全无 ⇒ FR-006 ② 判**失败**并指名 ⇒ 被拒 |
| `[png]` = `kaleido` | `license` 字段是 **MIT 全文**（无 SPDX id、无 `license_expression`、无分类器）⇒ 只能靠「授权文件原文识别」⇒ 判定**脆弱**（依赖散文式识别）⇒ 放弃 |
| `[png]` = `weasyprint` | 闭包含 `pillow`（`MIT-CMU` ✗）⇒ 被拒 |
| `[png]` = `pyvips` | Python 包本身 `MIT` ✓，但依赖 **libvips 系统库（LGPL）** ⇒ 引入系统级 LGPL ⇒ 不可接受 |
| **`[png]` = `playwright`（采用）** | ✅ 唯一「纯 Python 闭包全绿」的成熟方案。**代价**：浏览器二进制由用户**显式**执行 `playwright install chromium` 获取（安装期下载，**运行期零出站** —— Chromium 本地渲染）。⇒ 写入契约 |

> **📖 `[png]` 与宪法措辞的关系（2026-11-07 分析轮补入 · **2026-11-08 分析轮订正**）**：
> 宪法「依赖白名单」曾把 `[png]` 写作「**mermaid 相关**（`[png]`，默认关闭）」——
> **引文原话 ·已被宪法 v1.5.0 取代**（那是**能力**描述而非包名清单 ⇒ **不可判定**：
> 无法核验许可证、无法枚举闭包、无法写入门禁白名单）。
> ⇒ **宪法 v1.5.0（2026-11-08 · MINOR）已收敛为确切包名 `playwright`**（Apache-2.0 · 本地 Chromium 渲染）
> 并追加三条硬约束 (a) 默认关闭 / (b) 依赖闭包全部落在许可证白名单内 / (c) 运行期零出站。
> ⇒ 本 feature 的 `[png]` **规范表述一律为 `playwright`**；plan 只**核验**许可证与零出站，**MUST NOT** 另选后端。
>
> **⚠️ 与 spec 的一处偏离（**已于 2026-11-07 闭合** · 落 B3F1 spec **裁定 21**）**：spec **FR-001**（引文原文）写 `[otel]` 含 `opentelemetry-exporter-otlp`。
> 实测该组合**必然**被白名单拒绝 ⇒ **B3F1 取宪法依赖白名单原文所列**的
> `opentelemetry-api` / `opentelemetry-sdk`（宪法「依赖白名单 / 黑名单」· 包层白名单条：
> 「可选 extra：… `opentelemetry-api` / `opentelemetry-sdk`（`[otel]`）」）。
> **权威顺序**（spec Assumptions · 宪法 Governance）：宪法 > 立项书 > 提示词初稿 ⇒ 取宪法值。
> exporter 归 **B21F1**（「OTLP 导出插件与后端对接」）—— 那正是它该被解决的地方（见 D-03）。
> **登记**：立项书 §5.5 已于 2026-11-07 同步（**D14**）· B23F1 的提示词初稿同步改为「两段式」。

---

## D-03 · `opentelemetry-exporter-otlp` 的处置 —— 归 **B21F1**，本 feature 不含

**Decision**

`[otel]` extra **不含**任何 exporter；`opentelemetry-exporter-otlp` **不进**本 feature 的 `pyproject.toml`。
**登记**为 B21F1（OTLP 导出插件与后端对接）的**前置技术债**，并写入 `contracts/dependency-gate.md` §5。

**Rationale（实测）**

- `opentelemetry-exporter-otlp` 的完整闭包（18 个包）含 **`certifi`（`MPL-2.0`）**（经 `requests` 引入）
  ⇒ **不在**白名单 ⇒ G23 会**拒绝**该 extra ⇒ 违反 FR-001（extra 存在）+ FR-004 ①（extra 独立可选且可用）。
- 另一条被 `certifi` 污染的路径：`opentelemetry-exporter-otlp-proto-http` 闭包同样含 `certifi`。
- **唯一不含 `certifi` 的 exporter 路径**是 `opentelemetry-exporter-otlp-proto-grpc`
  （闭包：`googleapis-common-protos` · `grpcio` · `opentelemetry-api` · `opentelemetry-exporter-otlp-common` ·
  `opentelemetry-exporter-otlp-proto-common` · `opentelemetry-proto` · `opentelemetry-sdk` ·
  `opentelemetry-semantic-conventions` · `protobuf` · `typing-extensions`）⇒ **但**其中 `protobuf` 的
  `License` 字段是散文式 **`3-Clause BSD License`**（**非** SPDX id `BSD-3-Clause`）⇒ 在裁定 18 的
  「精确 id」口径下**无法归一** ⇒ 仍不合规。
- ⇒ **本 feature 不可能同时满足**「`[otel]` 含 exporter」与「白名单严格」。**取舍：保住白名单**（宪法原则 IX
  为 NON-NEGOTIABLE · FR-018 明令不得放宽）。
- **B21F1 的可行方向**（登记，不在本 feature 解决）：① 只用 gRPC 传输路径（避开 `requests`/`certifi`）；
  ② 为 `protobuf` 等散文式标识建立**权威 SPDX 归一**通道（见 D-05 的边界说明）；
  ③ 换用无 Python 依赖的 exporter 形态。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 把 `MPL-2.0` / `BSD-3-Clause`（散文式）加进白名单 | **违反裁定 18**（白名单恰好 5 个 id · 不得引入等价对照表 / 家族判定） |
| 声明 `[otel]` 含 exporter，但把 G23 的扫描域排除 exporter | **违反 FR-018 ①**（例外机制必须是「已写死的、具名的」例外，且此处是**新增**例外）⇒ 不可行 |
| 声明 `[otel]` 但**不写**任何依赖（空 extra） | 违反 FR-004（extra 的**内容**须具备实际能力 · 且宪法已列明 `[otel]` 的内容） |

---

## D-04 · `[png]` extra 的**运行期零出站**语义 —— 浏览器二进制属安装期动作

**Decision**

`[png]` = `playwright>=1.40`。**契约写明**：Python 包由 `pip install freegraph[png]` 安装；
**浏览器二进制**由用户**显式**执行 `playwright install chromium` 获取（**安装期**下载）；
**运行期** freegraph MUST **零出站**（Chromium **本地**渲染，图片不外传）。

**Rationale**

- 宪法「网络层黑名单」约束的是 **freegraph 自身的运行期出站**；包管理器下载依赖（任何依赖都会发生）
  与「用户显式安装浏览器」**不是** freegraph 的出站行为。
- 运行时 `draw_mermaid_png()` MUST **不**访问 `mermaid.ink`（宪法明令它在网络层黑名单内）⇒ 必须本地渲染。
- 这是白名单严格口径下**唯一**可行的方案（D-02 的实测已排除全部替代）。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 让 `[png]` 直接调远程渲染服务 | `mermaid.ink` 在**网络层黑名单**内 ⇒ 宪法红线 |
| `[png]` 为空 extra（渲染后端留待 B23F1 决定） | 违反 FR-004 ②（extra 的**内容**与约束须在脚手架层就位）· 且会留下一个「装了但不能用」的 extra |

---

## D-05 · SPDX 表达式的解析方式 = `packaging.licenses`（开发期依赖）+ **逐叶子**判定

**Decision**

- 判定规则：**证据链取到的标识 MUST 先被解析为 SPDX 表达式**；
  **表达式的每一个叶子标识符都 MUST ∈ {MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, PSF-2.0}**。
- 解析器用 **`packaging.licenses`**（`canonicalize_license_expression`）—— **开发期依赖**，不进发行包（门禁代码本身在 `harness/` 内，不进发行包）。
- **⚠️ 叶子的取法（2026-11-07 分析轮订正 · 必读）**：**`packaging.licenses` 的公开面没有表达式树 / 叶子迭代 API** ——
  **实测 24.2 / 25.0 / 26.3 三个版本**：公开名仅 `InvalidLicenseExpression` · `NormalizedLicenseExpression`（`str` 的 NewType）·
  `canonicalize_license_expression`（返回**普通 `str`**，非表达式树）；**不存在** `LicenseExpression` 类、
  **不存在**任何公开的树 / 叶子 API（`packaging.licenses._spdx` 是**私有**模块，且只含 `LICENSES` 字典、无解析器）。
  ⇒ 故叶子 MUST 取自**规范化输出**：对返回值**按空白分词**、剔除 `AND` / `OR` / `WITH` / `(` / `)` 后取剩余 token。
  **该分词是安全的**（规范化输出保证算子与括号两侧必有空格、标识符内不含空格）——
  **实测**：`'MIT AND PSF-2.0'` → `{MIT, PSF-2.0}`；`'Apache-2.0 OR MIT'` → `{Apache-2.0, MIT}`；
  `'BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0'` → 5 个叶子全对。
  **MUST NOT** 对**原始标识**做字符级切分（`re.split(r"[|&()]")` 会把 `MIT AND PSF-2.0` 误切成 **1** 个 token ——
  见下方「Alternatives considered」的实测否决）—— 该禁令针对**原始标识**，**不**适用于**规范化输出**。
- **版本下限 MUST 为 `packaging>=24.2`** —— `packaging.licenses` 模块自 **24.2** 才存在
  （**实测**：本机 `packaging 24.0` ⇒ `import packaging.licenses` **失败** `ModuleNotFoundError`）。

**实测验证（2026-11-07 · `packaging 26.3` · `uv run --with 'packaging>=24.2'`）**——
解析器行为与本决策的预测**逐条一致**：

| 输入 | `canonicalize_license_expression` | 说明 |
|---|---|---|
| `MIT AND PSF-2.0` | `MIT AND PSF-2.0` | 两叶皆白名单 ⇒ **放行**（`greenlet`） |
| `Apache-2.0 OR MIT` | `Apache-2.0 OR MIT` | 同上（`ormsgpack`） |
| `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` | 原样 | **解析通过** ⇒ 须由**叶子判定**拦下（`numpy`）⇒ 证实「解析」与「叶子判定」**必须两段** |
| `3-Clause BSD License` | **抛 `InvalidLicenseExpression`** | 散文式名称**无法归一** ⇒ **判失败**（`protobuf`）⇒ 证实裁定 18 的「不放行变体」在实现上**可达成**，且**无需**任何自制映射表 |
| `MPL-2.0` | `MPL-2.0` | 解析通过 ⇒ 由叶子判定拦下（`certifi`） |
| `MIT-CMU` | `MIT-CMU` | **解析通过**（它是合法 SPDX 标识符）⇒ 被拒**不是因为解析失败**，而是因为**不在白名单**（`MIT-CMU` ≠ `MIT`）⇒ 判据落点在**白名单比对** |
| `HPND` / `MIT-0` | 原样 | 同上（`HPND` / `MIT-0` 均能解析）⇒ 靠白名单比对拒 |
| `Apache-2.0 WITH LLVM-exception` | 原样 | 解析通过 ⇒ 含 `LLVM-exception` 叶子 ⇒ 拒 |
| `PSF` | **抛 `InvalidLicenseException`** | **非** `PSF-2.0` 的写法**解析即失败** ⇒ 拒 |

**Rationale**

- spec **FR-006 ④** 已写明「许可证表达式中含多个标识符时**逐个判定**」⇒ 判定对象是**叶子**。
- 实测证明**必须**用真正的 SPDX 解析器（**规范化**）后再取叶子，朴素切分会出错：
  - `greenlet` = `MIT AND PSF-2.0` —— 朴素 `split(" AND ")` 会把 `AND` 当成叶子 ⇒ 误拒；
  - `ormsgpack` = `Apache-2.0 OR MIT` —— 同理。
  - ⇒ 故取叶子 MUST **先规范化、后分词、剔算子**（见上方「叶子的取法」）。
    ⚠️ **「朴素切分」的否决针对的是对*原始标识*的字符级切分**（`re.split(r"[|&()]")` 之类）——
    它在 `MIT AND PSF-2.0` 上误判（实测：切出 **1** 个 token `MIT AND PSF-2.0`）；
    **规范化输出上的空白分词**是**另一回事**（实测正确）⇒ 二者 MUST NOT 混淆。
- `packaging` 的许可证为 `Apache-2.0 OR BSD-2-Clause`（两叶皆白名单）⇒ **门禁工具链本身**也不违反白名单。
- **边界（必须写进契约）**：`packaging.licenses` 的 `canonicalize_license_expression` 会把
  **非** SPDX 的散文式名称**抛异常**（`InvalidLicenseExpression`）⇒ 这正是我们要的：
  `protobuf` 的 `3-Clause BSD License` **无法归一** ⇒ 被拒（与裁定 18 的意图一致）。
  ⇒ **不得**为此引入「散文名 → SPDX id」的手工映射表（裁定 18 禁止「等价标识符对照表」）。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 朴素字符串切分（`re.split(r"[\|&()]")`） | 实测在 `MIT AND PSF-2.0` / `Apache-2.0 OR MIT` 上**误判**（切出 **1** 个 token）⇒ **MUST NOT** 用于**原始标识**（⚠️ **不**适用于**规范化输出**上的空白分词 —— 那是本决策**采用**的做法） |
| 自写 SPDX 表达式解析器 | `packaging` 已有**权威**实现且许可证合规 ⇒ 自写 = 重复造轮子 + 多一处可能出错的地方 |
| 只比对「标识符字符串完全相等」 | `MIT AND PSF-2.0` ≠ `MIT` ⇒ 会把 `greenlet`（合规）**误拒** ⇒ 违反 FR-006 ④ 的「逐个判定」 |
| 引入「散文名 → SPDX id」映射表 | **违反裁定 18**（禁止等价对照表） |

---

## D-06 · 既有门禁 **G3** 的占位填充 —— **裁定 8 的唯一一处例外**

**Decision**

1. `CONSTITUTION_DEPENDENCY_WHITELIST`：从 4 个占位包名 → **四个 extra 的真实闭包确切包名集合**
   （有限集合 · 逐个列名 · **无通配符 · 无前缀匹配**）。
2. extras 变体枚举：从「无差别剥离 / 保留 extras marker」→ **只枚举 freegraph 自身的 extras 变体**
   （传递依赖按其**基础依赖**展开）。
3. G3 的**判据句**与**许可证取值方式**（两条来源 + skip-on-missing）**零改动**；
   4 级证据链 + fail-on-missing 由**新门禁 G23** 独立承担。

**Rationale（实测）**

- **G3 自己的 docstring 预告了这件事**（`tests/contracts/test_architecture.py:924-931`）：
  「extras **由 B3F1 引入**——本 feature 无 extras，该条**为空断言**」·
  「它在 **B3F1 引入 extras** 后立即变为**实质断言**」⇒ **填充时机就是 B3F1**。
- **不动它的必然失败（实测推导 · 2026-11-07 复核订正）**：G3 的 `dependency_closure(..., with_extras=True)`
  （`tests/contracts/test_architecture.py:844-861`）在 `with_extras=True` 时**不剥离** extras marker，
  且把该标志**递归传下去** ⇒ `pydantic` 自己的 `email` extra 被展开 ⇒ 闭包被**过近似**。
  **实测（真实安装四个 extras 后跑 G3 的真实代码）**：
  - **实际变红的是「白名单子集断言」**：旧语义下 extras 闭包为 **20** 个包，其中 **8** 个不在 4 个占位包名内 ——
    `email-validator` · `furo` · `objgraph` · `opentelemetry-configuration` · `psutil` · `setuptools` ·
    `sphinx` · `tzdata` ⇒ `extras <= WHITELIST` **必然失败**。
  - **「许可证断言」实为 `pytest.skip` 而非变红**：那 8 个包**均未安装**（`email-validator` 等只是 `pydantic` 的
    `email` extra 的成员，CI 未装该 extra）⇒ `_license_of()` 返回 `None` ⇒ 落入 G3 既有的 `missing` 分支
    ⇒ 整条许可证断言被**跳过**（G3 既有语义 · skip-on-missing）⇒ **不构成变红原因**。
    **这正是新门禁 G23（4 级证据链 + fail-on-missing）不可省略的理由**。
  - **`dnspython` 不在闭包内**（它是 `email-validator` 的依赖，而 `email-validator` 本身未安装
    ⇒ 递归到 `email-validator` 时即取不到元数据）—— 故「`email-validator`（`Unlicense`）与 `dnspython`（`ISC`）二者」
    这一表述**不成立**（**只有前者**进闭包）。
  - **修正后的枚举语义可实测复现**：按「只枚举 freegraph 自身的 extras 变体、传递依赖只展开其**基础**依赖」
    实测，extras 闭包**恰为** 12 个包名 ⇒ 与 12 名白名单**逐一命中**、子集断言**绿**。
- 同时 `CONSTITUTION_DEPENDENCY_WHITELIST`（4 个包）也**必然**失败于
  `extras <= WHITELIST`（真实闭包含 `annotated-types` / `pydantic-core` / `typing-extensions` /
  `typing-inspection` / `opentelemetry-semantic-conventions` / `greenlet` / `pyee` …）。
- **⚠️ 白名单的版本敏感性（2026-11-07 实测补记）**：12 名白名单是**当前解析结果**的快照（`pydantic` 解析到 2.13.x）；
  extras 的版本约束是**开区间**（`pydantic>=2.0`）⇒ 上游**新增一个传递依赖**即会让闭包多出一个包名 ⇒ 白名单失配 ⇒ CI 变红。
  ⇒ 处置 = **重新实测闭包并追认更新白名单**（**MUST NOT** 以「放宽白名单让它变绿」绕过 · FR-018）。
- **净效果 = 变严**（不是变松）：白名单从 4 个**宽泛占位**变成 **12 个确切包名**；
  枚举从**过近似**变成**精确变体**；**无一处放宽** ⇒ 符合 FR-018。
  > **📌 2026-11-08 分析轮订正（H9⑤）**：本条**原写**「白名单从 4 个**宽泛占位**变成 **7+ 个**确切包名」
  > ⇒ 与**全链路的 12 个**不一致 ⇒ 现统一为 **12 个确切包名**（与上文的实测闭包逐一命中）。
- **待追认**：见 plan.md「唯一一处例外」+ `tasks.md` 的追认项。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 不动 G3，让 CI 长期红 | 违反 PR-4「feature 必须能独立通过门禁」；且 **CI 永久红 ⇒ 门禁被当成噪声 ⇒ 与本 feature 的立意直接冲突** |
| 把 `ISC` / `Unlicense` 加进 G3 的白名单 | **直接违反 FR-018 + 宪法原则 IX（NON-NEGOTIABLE）** |
| 删掉 G3 的 extras 断言 | **削弱既有判据** ⇒ 违反裁定 8 的**本意**（虽字面上是「删」）⇒ 不可接受 |
| 放弃 extras | 违反 FR-001 / FR-004 |

---

## D-07 · 层注册表的载体 = `contracts/layer-registry.md`（机器可读 + 机器标记）

**Decision**

层归属的**唯一权威** = `specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md`，
一张**带机器标记**（`<!-- authority: yes -->`）的表格；G25 解析它。

**Rationale**

- spec **FR-008 ②**：「层归属 MUST 由**可机读的注册表**判定，MUST NOT 靠路径前缀的猜测；
  注册表 MUST 覆盖「跨层单元」这一类」⇒ 必须有**一张表**。
- 沿用仓库**既有的机器标记惯例**：G12（`test_architecture.py:1550` 起的
  `test_exactly_one_authoritative_manifest`）扫描 `**/public-api.md` 的
  `<!-- authority: yes|no -->` 标记来定位**唯一权威** ⇒ 本注册表**同构**，
  不发明新机制。
- **不放在代码里**（如 `harness/scripts/gates/_gatekit.py` 里的常量）：代码常量无法被
  `specs/` 文档引用，评审时看不到「层」与 feature 归属的关系；且 G12 的既有权威在 `specs/` 下。
- **注册表还须承载「跨层单元内部」的判定行（2026-11-08 分析轮订正 · C3）**：
  spec **FR-008 ④** 规定「**同一跨层单元内部**的模块互相 import ⇒ **不产生层边** ⇒ **不构成违规**」，
  并给出**模块定位口径**（import 目标先定位到具体路径 ⇒ 落在**同一注册表条目**下 ⇒ 单元内部引用；
  落在其它条目下 ⇒ 按层间方向判定；无法解析到仓库内路径 ⇒ 第三方 ⇒ 不产生层边）。
  ⇒ **这是注册表必须承载的第四条规则**，否则 G25 会把 10 个门禁脚本（它们 MUST 复用
  `harness/scripts/gates/_gatekit.py` ⇒ `import _gatekit`）判红 ⇒ 违反 PR-4。
  ⇒ 落点四处口径一致：spec FR-008 ④ · `layer-registry.md` §0.2 规则 3 · `data-model.md` §5.2 · `architecture-gates.md` G25 第 4 条。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 放在 `_gatekit.py` 的 Python 常量里 | 权威落在**代码**里 ⇒ 与仓库既有「权威清单在 `specs/<feature>/contracts/`」的惯例不符；评审不可读 |
| 放在 `pyproject.toml` 的 `[tool.freegraph.layers]` | 同上；且改 `pyproject.toml` 会与「发行元数据」混在一起 |

---

## D-08 · CI 矩阵的作业划分与断网任务的实现

**Decision**

- **7 个作业**（spec FR-015 ④ / SC-012）：
  `ubuntu-24.04` × {3.11, 3.14} · `macos-15` × {3.11, 3.14} · `windows-2025` × {3.11, 3.14}
  · **`ubuntu-24.04-arm` × 3.11**（arm64 最低档）。
- **runner 标签 MUST 钉死到具体镜像**（FR-015 ④③）⇒ 用 `ubuntu-24.04` / `macos-15` / `windows-2025`
  这类**带版本**的标签，MUST NOT 用 `ubuntu-latest` / `macos-latest` / `windows-latest`。
  > **📌 2026-11-08 分析轮订正（H9①）**：本决策**原写** `ubuntu-latest` / `macos-latest` / `windows-latest`
  > （**浮动标签**）⇒ 与 FR-015 ④③ **及其自身下一行**（「MUST NOT 用浮动标签」）**自相矛盾**
  > ⇒ 现统一为与 `contracts/ci-matrix.md` §1 **完全一致**的**钉死标签**。
- **每个作业**（**2026-11-08 分析轮订正 · H9② · 补齐三步**）：
  `checkout`（钉版本）→ `setup-python`（钉版本 + 钉 `python-version`）→ `setup-uv`（钉版本）→
  **建 venv**（`uv venv --python <矩阵档位>`）→ **装 dev 组**（`uv pip install --python .venv --group dev`）→
  **装发行形态**（`uv pip install --python .venv -e .`，`FREEGRAPH_TEST_INSTALLED=1`）→
  **装四个 extras 的依赖**（`uv pip install --python .venv -e ".[pydantic,checkpoint,otel,png]"`）→
  `pytest`（全量）→ **逐条**门禁调用。
  > **补齐的理由**：原列表**缺**「建 venv」「装 dev 组」「装四个 extras 的依赖」三步 ⇒
  > ① 无 venv ⇒ `uv pip install` 直接失败（`No virtual environment found`，退出码 2）；
  > ② 无 dev 组 ⇒ `pytest` 不存在；③ 无 extras ⇒ G21 / G23 / G3 **不可判定**（必红）。
  > ⇒ 现与 `contracts/ci-matrix.md` §2 **步骤 3.5 / 4 / 5 / 5.5** 逐条一致。
- **⚠️ 解释器路径 MUST 跨平台（2026-11-08 分析轮订正 · C1）**：命令串**只出现 venv 目录 `.venv`**
> —— 安装用 `uv pip install --python .venv …`（**实测 uv 0.12.7 接受 venv 目录路径**），
> 调用用 `uv run --no-project --python .venv python …`（`--no-project` ⇒ **不同步环境**
> ⇒ MUST NOT 让它把已装的四个 extras 依赖卸掉）⇒ **三个平台逐字相同**
> ⇒ `windows-2025` 的 2 个作业**不会**因路径不存在而必红。
- **断网任务（G28）** = Linux 作业内的一个**独立 step**：`unshare --net --map-root-user …`
  （网络命名空间 ⇒ 无任何网络接口，**不需要特权**）⇒ **MUST 显式施加断网排除清单**
  （`tests/gates/data/offline_exclusions.txt` · **单文件** · **逐条带理由** ⇒ G28 脚本读它并逐条转成
  `--deselect` 参数 · **2026-11-08 分析轮订正 · H7** —— 不施加排除 ⇒ 照抄的裸 `pytest tests/ -ra`
  必然在被排除的用例上**假红** ⇒ **SC-004 必假红**）。
- **G22（隔离 venv）** = Linux 作业内的独立 step（`uv venv` + `uv pip install` + 子进程断言）。

**Rationale**

- spec **裁定 10**：断网任务 MUST 在 Linux；「网络命名空间隔离即可」⇒ `unshare --net` 是**无特权**方案
  （`--map-root-user` 免 `CAP_SYS_ADMIN` 的用户命名组映射）⇒ 不引入特权依赖。
- `unshare --net` 会把**回环也置为 DOWN** ⇒ 满足 FR-010「全部网络接口置为不可用」；
  本地回环用例 MUST 进排除清单（FR-010 ④）。
- **`FREEGRAPH_TEST_INSTALLED=1`**：仓库的 `tests/contracts/conftest.py` 与 `tests/facade/conftest.py`
  **已为此预留开关**（其 docstring 明确写着「供 **B3F1** 的 CI『先 `pip install .` 再跑 pytest』用」）⇒
  沿用既有约定，零改动。
- **runner 钉死**：FR-015 ④③ 要求「MUST NOT 用浮动标签」⇒ 上游 runner 升级不得引入不可复现的行为差异。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| `ip link set all down` | 需要 **root / 特权** ⇒ 引入特权依赖（裁定 10 的理由） |
| 用 `pytest-socket` 等第三方插件阻断网络 | ① 引入第三方依赖（须过白名单）；② 它是**阻断式**的 ⇒ **违背** FR-009 ③（「不得安装任何出网拦截机制」的产品立场） |
| 断网任务单列为独立 **job** | 会使作业数 **> 7** ⇒ 违反 SC-012（作业总数 == 7） |
| `macos-latest` / `windows-latest` 浮动标签 | 违反 FR-015 ④③ |

---

## D-09 · 断网排除清单的载体 = `tests/gates/data/offline_exclusions.txt`

**Decision**

排除清单 = **纯文本文件**（每行一条：**用例标识** + **排除理由**），
落 `tests/gates/data/offline_exclusions.txt`；**同址于测试** ⇒ 改清单必然改测试同提交。

**Rationale**

- spec **FR-010 ④**：「排除项 MUST 落成**可机读的清单文件**，**逐条**写明**排除理由**；
  MUST NOT 靠临时跳过 / 运行时打桩；清单内容变更 MUST 与代码**同提交可见**」。
- 放 `tests/gates/data/` 而非 `specs/`：它是**执行期**输入（pytest 要读它），
  不是**判据**（判据在 `contracts/`）⇒ 与 `tests/` 同址最自然，且满足「同提交可见」。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 写进 `pyproject.toml` | 把「测试范围」混入**发行元数据** ⇒ 污染发行包 |
| 写进 `conftest.py` 的 Python 常量 | 清单**不可机读**为独立工件；且「逐条理由」会退化成代码注释 |
| 用 pytest marker（`@pytest.mark.offline_excluded`） | marker **不带理由** ⇒ 违反 FR-010 ④「逐条写明排除理由」；且理由藏在代码里不易审计 |

---

## D-10 · 分支保护设置步骤的载体 = `harness/verification/B3F1/manual-verification.md`

**Decision**

「可照抄的设置步骤」写进**人工验证记录**（`harness/verification/B3F1/manual-verification.md`），
并在其后附**启用后的状态取证**（截图或 `curl` 的 API 响应摘要）。

**Rationale**

- spec **FR-020 ②**：「本 feature MUST 产出**可照抄的设置步骤**，至少写明：**勾选哪些 job 为必过检查**、
  **保护哪些分支**、**是否启用「必须先通过检查才能合并」**；步骤 MUST **记入人工验证记录**」。
- spec **FR-020 ①**：本环境**无 `gh` 命令、无 GitHub 令牌**（实测：`env` 无 `GH_*` / `GITHUB_*`；
  git 无 `credential.helper`）⇒ **只能由发起者执行** ⇒ 步骤必须**可照抄**（不能依赖本仓库的脚本）。
- **FR-020 ⑤**：README / 贡献指南写「合入前 CI 必须全绿」作为**人工兜底**（分支保护未启用期间）。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 本 feature 自动调用 GitHub API 设置 | **无令牌**（实测）⇒ 不可行；且 spec FR-020 ① 明令 MUST NOT 声称已代为设置 |
| 把步骤放进 `contracts/ci-matrix.md` | FR-020 ② 要求**记入人工验证记录** ⇒ 必须落在那里；`ci-matrix.md` 放**矩阵契约**，设置步骤在人工记录里**引用**它 |

---

## D-11 · 出站归因函数的实现 = 「第一个非标准库帧」

**Decision**

归因函数 `attribute_egress(frames) -> "framework" | "user"`：
从栈顶（最靠近连接发生处）向下遍历，**跳过全部标准库帧**，遇到的**第一个非标准库帧**：
其文件路径在 `freegraph/` 包内 ⇒ `framework`；否则 ⇒ `user`。

**Rationale**

- spec **裁定 19** 已把规则定死（「第一个非标准库帧」），本决策只定**实现口径**：
  「标准库帧」的判据用 **`sys.stdlib_module_names`**（Python 3.10+ 的标准库成员名集合）——
  与既有门禁 G2 的第三方 import 判定**同款**（`tests/contracts/test_architecture.py:230` 附近用
  `module ∈ sys.stdlib_module_names` 判「标准库」）⇒ **一处口径，全库一致**。
- **四种栈形态 MUST 全判对**（FR-009 ②②）⇒ 用**合成调用栈**驱动单元断言（MUST NOT 依赖真实出网）。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 用 `sys.builtin_module_names` | 只含**内建**模块（`sys` / `builtins`），不含 `socket` / `urllib` ⇒ 跳过不了它们 |
| 硬编码一份「标准库模块名单」 | 随 Python 版本漂移 ⇒ `sys.stdlib_module_names` 是**标准库自己给的**名单 |

---

## D-12 · 负向验证的执行形态 = 临时目录副本（**不**用 `git worktree`）

**Decision**

负向验证在 **`tempfile.TemporaryDirectory()` 里的仓库副本**中执行：
拷贝**必要的**文件（`pyproject.toml` + `src/` + **`README.md`** + **`LICENSE`**）→ 注入违规 → 跑门禁 → 断言失败 → 删除副本。
**工作树 MUST 逐字不变**（`git status` 干净）。

> **📌 2026-11-08 分析轮订正（H9③）**：本决策**原写**「拷贝**必要的**文件（`pyproject.toml` + `src/`）」——
> **缺 `README.md` 与 `LICENSE`** ⇒ 二者是 `pyproject.toml` 的**硬引用**
> （`readme = "README.md"` / `license-files = ["LICENSE"]`）⇒ **缺一即构建失败**
> （**实测**：`OSError: Readme file does not exist: README.md`）⇒ 只拷 `pyproject.toml` + `src/` 的副本
> 会让 **G22 的 `uv pip install <target-root>` 在构建阶段就失败**（反向用例 T042 会在**构建阶段**而非
> **断言阶段**失败）⇒ 现与 `contracts/ci-matrix.md` §3.1 与 `tasks.md` **T014** 逐字一致。

**Rationale**

- spec **裁定 9**：负向验证 MUST 在**工作树的隔离副本**中执行 ⇒ 执行后工作树 MUST 逐字不变。
- **不用 `git worktree`**：① 它会在 `.git/` 下留 `worktrees/` 元数据（`git status` 虽干净但
  `.git` 被改 ⇒ 「逐字不变」的**强**口径不满足）；② 需要 `git worktree add` 的**提交态**——
  本仓库当前工作树**有未提交的新 spec 目录**，`worktree add` 会基于 `HEAD`（不含未提交内容）⇒
  负向验证的输入与被测对象不一致；③ `tempfile` 副本**更简单**、**无 git 元数据残留**。
- **只需拷贝必要文件**：门禁 G21 只读 `pyproject.toml` 的 `Requires-Dist` ⇒ 副本无需完整仓库。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| `git worktree add` | 见上三条（`.git` 被改 / 基于 HEAD / 更复杂） |
| 直接改工作树再 `git checkout --` 撤销 | **中途失败会留下污染** ⇒ 违反裁定 9 的立意 |
| 只改 `pyproject.toml` 再改回 | 同上 |

---

## D-13 · G27 / G28 的覆盖方式 = 正向断言 + 人工验证记录取证（**无反向用例**）

**Decision**

G27 / G28 **不配反向用例**（裁定 14）；二者 MUST 跑**正向断言**，
且人工验证记录 MUST 留「**框架出站 = 0**」与「**断网全绿**」两条实测证据。

**Rationale**

- 裁定 14 已定；本决策只定**补偿措施**：
  G27 的**归因判据本身**（裁定 19）另由**合成调用栈**的单元断言覆盖（FR-009 ②③）——
  这是「判据可信」与「门禁反向用例」两件事，**前者不需要真实网络** ⇒ 成本极低、覆盖充分。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 给 G27 配反向用例 | 需要让 freegraph **真的尝试出站** ⇒ 与 FR-009 ③「不得安装任何出网拦截机制」的产品立场**自相矛盾**（为测试而故意让框架出网） |
| 给 G28 配反向用例 | 需要「一个断网下会失败的功能」作为靶子 ⇒ 等于**故意制造缺陷**；而断网任务本身的**正向**全绿已是有效证据 |

---

## D-14 · 兼容矩阵的「分层判定」如何接线

**Decision**

- **已入库**（`README.md` 的「API 兼容矩阵」章节）⇒ 复用既有门禁 **G8**（契约层 18 个）·
  **G19**（门面 7 个）⇒ **只接线，判据零改动**。
- **未建全**（终版 `COMPAT.md`）⇒ 由 **G29 的载体**或一条**独立 step** 输出
  「**未落地**」提示（**非阻断**，FR-012 ②）。
- **API 快照**（B2F2 已入库）⇒ 复用既有 **G16**（快照比对）⇒ **只接线**。

**Rationale**

- 裁定 13 已定分层语义；本决策定**接线方式**。
- 「未落地」提示 MUST **非阻断**（否则 CI 因后续 feature 的交付物而长期红 ⇒ 违反 PR-4）。
- **MUST NOT 静默跳过**（FR-012 ①）⇒ 提示 MUST 出现在 CI 输出里。
- **⚠️ 「自动转为严格比对」的阻断条件（2026-11-08 分析轮订正）**：`COMPAT.md` **存在** ⇒ 该步骤转为 **严格比对** ⇒ **有不一致**时才以非 0 退出（并指名行 / 符号）；**一致 ⇒ 退出码 0**。
  ⇒ **MUST NOT** 仅因「文件存在」而非 0 —— 否则后续 feature 建出 `COMPAT.md` 后该步骤**永久红**（违宪 v1.6.0 红线「MUST NOT 写永久红的 CI」）⇒ 与本决策的「非阻断」立场同源。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 把「未落地」做成一条 pytest 断言 | pytest 的 `skip` 会显示为「跳过」而非「未落地」，且**退出码 0** ⇒ 语义丢失；应走**独立的 report 步骤**（退出码 0 + 明确的输出行） |
| 等 `COMPAT.md` 建好再接线 | 违反 FR-012（CI MUST 提供**挂载点**）⇒ 挂载点必须现在就位 |

---

## D-15 · pytest 配置 = 在 `pyproject.toml` 新增 `[tool.pytest.ini_options]`

**Decision**

在 `pyproject.toml` 新增 `[tool.pytest.ini_options]`：`testpaths = ["tests"]`、
`addopts = "-ra"`（显示 skip / xfail 摘要）、`xfail_strict = true`，
**外加注册两个 marker**：`linux_only`（需 Linux 隔离环境 / 网络命名空间）·
`full_install`（需装齐四个 extras 的完整安装环境 · **当前无用例使用 · 预留**）。

**Rationale**

- 仓库**当前无** pytest 配置（实测 `grep pytest pyproject.toml` 无命中）⇒
  `pytest` 的默认收集会从 rootdir 开始，可能收集到 `harness/` 下的脚本或 `specs/` 下的文件 ⇒
  **不可控**。
- `testpaths` 把收集范围**钉死**在 `tests/` ⇒ 门禁的「核心用例 = 全量测试套件」（裁定 16）有了确定含义。
- `xfail_strict = true` ⇒ 禁掉「预期失败但其实通过」的静默通过。
- **不影响**既有测试（既有 `tests/contracts` 与 `tests/facade` 均在 `tests/` 下 ⇒ 收集范围不变）。
- **两个 marker MUST 注册**（2026-11-08 二轮复核补入）：`linux_only` 用于**平台专属**用例
  （G22 的隔离 venv 一族 —— 需联网安装 ⇒ 非 Linux 作业 MUST 跳过）；
  `full_install` 供「需完整安装环境」维度过滤（**当前无使用者 · 预留**）。
  ⇒ **MUST NOT** 漏注册（否则 pytest 报 `PytestUnknownMarkWarning`）；
  ⇒ **MUST NOT** 把 marker 过滤写进 `addopts`（那会让 **Linux 档也过滤**
  ⇒ `linux_only` 用例在 Linux 上永不执行 ⇒ **G22 的 pytest 断言静默失效**）
  ⇒ 过滤 MUST 由 **CI 的 `-m` 参数**按平台追加（配方见 `contracts/ci-matrix.md` §2 步骤 6）。

**Alternatives considered**

| 替代 | 否决理由 |
|---|---|
| 新建 `pytest.ini` | 仓库的构建配置**统一在 `pyproject.toml`**（hatchling 同处）⇒ 不引入第二个配置文件 |
| `addopts = "--strict-markers"` | 原否决理由「与本 feature 无关」**经 2026-11-08 二轮复核推翻**——本 feature **正是**引入 marker 的那一轮 ⇒ 「无关」不成立；**仍然不采用**，但理由改为：① marker **已注册** ⇒ 本就不会出现 `PytestUnknownMarkWarning`；② `--strict-markers` 会把**任何第三方插件**的自定义 marker 也变成硬错误 ⇒ 脆性更高；③ **MUST NOT** 借 `--strict-markers` 之名把**平台过滤**塞进 `addopts`（见上）。 |

---

## 遗留与登记（不阻塞本 feature）

> **📌 ID 命名空间说明（2026-11-08 分析轮订正 · 消解 ID 撞车）**：本表的编号为 **`DR-n`**
> （**D** = 本 research 文档的**决策 / 遗留**登记项），**与 `plan.md` 的「登记项 R-n」是两个不同的序列**
> （plan 的 R-n 是 **plan 级**登记项，其中 **R-4** 已被宪法 v1.6.0 修订记录引用 ⇒ **不得改名**）⇒
> 引用时 MUST 带限定语（「plan 登记项 R-4」/「research DR-4」）。

| # | 事项 | 归属 |
|---|---|---|
| DR-1 | `opentelemetry-exporter-otlp`（含 `certifi`/MPL-2.0 与 `protobuf` 散文式标识）的合规解法 | **B21F1**（OTLP 导出插件） |
| DR-2 | 终版 `COMPAT.md` 的完整矩阵 | **B24F1** |
| DR-3 | 发行流水线的纯度断言接入 | **B24F1**（`check_dist_purity.py` 已存在） |
| DR-4 | fake 模型注入（`conftest.py` 猴补 `init_chat_model`） | **B25F1** |
| DR-5 | **分支保护的实际启用**（仓库设置） | **发起者**（spec FR-020 ①） |
| DR-6 | 既有 G3 与新 G23 的许可证口径差异（`MIT-CMU` 在 G3 通过 / 在 G23 被拒） | **已知取舍** · G23 更严 ⇒ 总体为严 |
| DR-7 | **CI 环境未装齐四个 extras 的依赖** ⇒ ① G23 取不到任何许可证据（要么必红、要么退化为**空门禁** ⇒ **违宪**：宪法原则 IX「三条 MUST NOT MUST 由 CI 断言自动校验」）② G21 的闭包只到第一层 ⇒ **间接引入**的黑名单包抓不到 ③ G3 的 12 名白名单永不触达 | **已在 ci-matrix.md §2 步骤 5.5 解决**（**全部 7 个作业** MUST 装齐 extras · **实测**完整闭包**恰好 12 个包**，与 G3 白名单逐一命中）· G23 因此**移出**非 Linux 子集（**2026-11-08 分析轮订正 · H9④**：本条**原写**「已在 ci-matrix §2 **步骤 5** 解决（**Linux 全量作业** MUST 装齐 extras）」⇒ ① 步骤号应为 **5.5**、② 适用范围应为**全部 7 个作业**）<br>**⚠️ 但 G23 的子集归属已于 2026-11-08 反转（见 ci-matrix §1）**：G23 的**判据是纯元数据读取**（跨平台无差异）⇒ **已纳入**非 Linux 子集 ⇒ R-7 的处置对 **7/7 作业**都成立 |
