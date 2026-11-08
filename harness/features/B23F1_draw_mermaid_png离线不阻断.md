# B23F1 · `draw_mermaid_png()`：离线不阻断 ★

> **本文件是 `/speckit.specify` 的提示词初稿。** 执行 `/speckit.specify` 时，
> 把下方「提示词正文」整段作为特性描述传入。
>
> | 项 | 值 |
> |---|---|
> | feature ID | `B23F1` |
> | 所属 功能块 | B23（`draw_mermaid_png`） |
> | 架构层 | L3 图定义层 |
> | 里程碑 | M2 图定义与对外 API（第 20 个） |
> | 前置依赖 | **B22F1** |
> | 规模 | 1,080 行（实现 520 / 测试 560）· 3 人日 |
> | 建议 short-name | `b23f1-draw-mermaid-png-offline` |
> | MVP 必需（★） | **是**（固定脚本所需 6 项之一；**六项齐备 = MVP 达成**） |

---

## 提示词正文

### 1. 目标

交付 `draw_mermaid_png()`：**方法名必须与 LangGraph 同名**（否则固定脚本第 163 行
必须改），且在**离线**环境下**不得抛阻断性异常**，返回的字节**必须是可被
`IPython.display.Image` 接受的合法 PNG**。

### 2. 背景与上下文

- **为什么这是硬约束**：LangGraph 的 `draw_mermaid_png()` 默认请求公网
  `https://mermaid.ink`，Q3 实测离线必然抛
  `ValueError: Failed to reach https://mermaid.ink API`；而 `target.py:163` 的这个调用
  位于 `target.py:168` 的 `invoke()` **之前**——**脚本会在到达验收点之前中断**。
- **返回字节的合法性同样重要**：非法字节会在 `Image()` **构造阶段**就抛错
  （`target.py:163` 的 `display(Image(...))`），同样中断脚本。
- **v1 采用的方案已写死**（立项书 §5.5 · **2026-11-07 修订 · D14**）：**两段式** ——
  **方案 C（未装 `[png]` extra 时）—— 返回占位 PNG 字节**
  （自研最小 PNG 编码器，用标准库 `zlib` + `struct` 即可），零依赖、零出站、离线可用；
  **方案 D（装了 `[png]` extra 时）—— 本地真实 PNG 渲染**（后端 = `playwright` · Chromium 本地渲染 ⇒ 运行期零出站；
  浏览器二进制由用户**显式**执行 `playwright install chromium` 获取，属**安装期**动作）。
  - 方案 A（`mermaid-cli`，Node 工具链）❌ 破零依赖承诺；
  - 方案 B（调 `mermaid.ink`）❌ 破零出站承诺；
  - 方案 D 的 **v2 变体**（纯 Python 最小 SVG/PNG 渲染器）→ 仍留 **v2 / B26 可选子包**
    （目标是**摆脱浏览器依赖**，不是替换 v1 的默认行为）。
- **为何 v1 就交付真实渲染**（D14 的实测依据）：白名单严格口径（宪法原则 IX）下，**全部纯 Python
  SVG→PNG 后端实测被拒** —— `cairosvg`/`svglib`/`pycairo` = **LGPL**（传染性）· `pillow` = `MIT-CMU`/`HPND`
  （变体标识符不放行）· `matplotlib` 的闭包含 `pillow` 且 `numpy` 表达式含 `0BSD`/`Zlib`/`CC0-1.0` ·
  `pymupdf` = **AGPL** · `resvg-py` = **无任何许可证信息** ⇒ **`playwright` 是唯一闭包全绿的后端**。
- **代价（须记录）**：`[png]` 用户需另装浏览器二进制（约 300 MB）⇒ **基础安装的零依赖承诺不受影响**
  （extra 默认关闭）；「本地真实 PNG 图形渲染」**不依赖**任何远程渲染服务（`mermaid.ink` 仍在网络层黑名单内）。
- **C15（PNG 渲染）**：`draw_mermaid_png() -> bytes`；必须提供**同名方法**；
  **离线不得抛异常阻断脚本**。

### 3. 用户场景

**P1 — 断网环境也能出图**
作为内网环境的用户，我调 `draw_mermaid_png()` 期望拿到一份图，而**不是**一个
「Failed to reach https://mermaid.ink API」的异常。

- **独立验收**：断网环境下调用成功返回 `bytes`。

**P2 — 返回的字节能直接被展示**
作为用户，我（或脚本）会把返回的字节交给 `IPython.display.Image` 构造，
期望**不抛错**。

- **独立验收**：PNG 结构合法性判据通过（签名 + 块结构 + CRC 自洽）。

**P3 — 离线场景没有隐藏的兜底网络请求**
作为维护者，我希望「离线不抛异常」不是靠「捕获网络异常后返回占位」实现的
（那仍然发起了出站），而是**根本没有网络代码路径**。

- **独立验收**：静态扫描 `freegraph/**` 无 `socket` / `requests` / `httpx` /
  `urllib.request` 等网络客户端调用；socket 监测夹具「框架出站 = 0」。

### 4. 功能需求

- **FR-001**：系统 MUST 提供 `draw_mermaid_png()` 方法（**同名**），返回 `bytes`（C15）。
- **FR-002**：该方法 MUST **离线不得抛阻断性异常**；MUST NOT 因网络不可达而失败。
- **FR-003**：返回的字节 MUST 是**结构合法的 PNG**：
  - 以 PNG 魔数 `\x89PNG\r\n\x1a\n` 开头；
  - 至少包含 IHDR 块，且各块长度 / 类型 / CRC 自洽；
  - 结尾含 IEND 块。
- **FR-004**：返回的字节 MUST 可被 `IPython.display.Image` 接受（**合法 PNG** 是其
  充分条件——`IPython` 属脚本自身依赖，freegraph 无需引入）。
- **FR-005**：实现 MUST 只使用**标准库**（如 `zlib` / `struct`），
  MUST NOT 引入任何第三方依赖；MUST NOT 调用 `mermaid.ink` 或任何外部服务。
- **FR-006**：v1 的 PNG 内容为**占位图**（可含图形的最小占位）；「真实图形渲染」
  MUST NOT 在本 feature 实现（v2 / 可选 `[png]` extra）。
- **FR-007**：MUST 提供**离线等价性证据**：本方法在「全部网络接口不可用」的 CI 任务中
  仍然成功。
- **FR-008**：系统 MUST NOT import `langchain` / `langchain-core`；MUST NOT 读环境变量。

### 5. 成功标准

- **SC-001**：PNG 路径**离线不抛阻断性异常**（断网任务通过）。
- **SC-002**：返回字节通过 PNG 结构合法性判据（签名 + IHDR + IEND + CRC 自洽）。
- **SC-003**：`freegraph/**` 静态扫描**零**网络客户端调用；socket 监测夹具
  「框架出站 = 0」。
- **SC-004**：freegraph 的运行时依赖闭包**仍为空集**（无新增）。
- **SC-005**：方法名与签名与 LangGraph 一致（API 快照测试通过）。

### 6. 验收判据（= 立项书 §5.2 B23F1 小目标，逐条可判定）

> 小目标原文：PNG 路径离线不抛阻断性异常

| # | 判据 | 判定方式 |
|---|---|---|
| A1 | 离线不抛阻断性异常 | 断网 CI 任务中 `draw_mermaid_png()` 成功返回 |
| A2 | 返回**合法** PNG 字节 | PNG 结构判据（`harness/demo/visualization.py` 已有 `looks_like_png`） |
| A3 | 方法名同名 | `draw_mermaid_png` 存在于 `Graph` 对象上（API 快照） |

### 7. 关键实体与契约

| 实体 | 语义 | 对应契约 |
|---|---|---|
| `draw_mermaid_png()` | PNG 字节导出（v1 = 占位图） | **C15** |
| 占位 PNG 编码器 | 标准库实现的最小合法 PNG | 立项书 §5.5 方案 C |

> **口径提醒**：C14（mermaid 文本）已在 B22F1 交付；本 feature 只加 **PNG 字节**，
> 且**不得**改 mermaid 文本的产出语义。

### 8. 边界（本 feature 明确不做）

- 不做**真实图形渲染**（v2 / B26 可选子包 + 可选 `[png]` extra）。
- 不调用 `mermaid.ink`（永久排除，见 §9）。
- 不引入 `mermaid-cli` / Node 工具链（破零依赖承诺）。
- 不引入 `pillow` / `cairosvg` 等渲染库（破零依赖承诺）。
- 不实现前端 UI（v2 / B26）。
- 不改 `harness/demo/target.py`（只读基准）。

### 9. 红线与质量门禁

- **依赖门禁（阻断，红线）**：新增依赖 = 0；`mermaid.ink` 在网络层黑名单，
  **MUST NOT** 被默认启用（宪法原则 I 明文点名）。
- **零出站**：本 feature 是「零出站」承诺最容易被绕过的地方——**「捕获网络异常后
  返回占位」不算合规**，因为请求已经发出。实现路径上 MUST NOT 存在网络代码。
- **契约门禁第 3 项**：`target.py` diff 断言常驻。
- **人工门禁**：`harness/verification/<feature>/manual-verification.md`。
- **证据门禁**：PNG 合法性判据须引用 PNG 规范（ISO/IEC 15948）。

### 10. 交付物与后续

- **交付物**：`draw_mermaid_png()` + 最小 PNG 编码器 + PNG 合法性判据测试 +
  断网任务用例 + 人工验证记录。
- **后续解锁**：**B8F3**（节点别名 + `context` 通道）→ M3 全部 feature。
- **★ MVP 达成点**：**本 feature 是六项最小交付集的最后一项**——完成即意味着
  `harness/demo/target.py` 的 **fake 模型轮**具备跑通条件（M2 里程碑的验收点，
  §5.2 行序串行口径 = 第 20 个 feature / 第 60 天）。
- **风险提示**：PNG 字节的合法性判据必须**独立于** `IPython`（不能靠「装了 IPython
  就没报错」来证明）；应按 PNG 规范自行校验签名 / 块结构 / CRC。

---

## 依据

- 立项书 §4.3（第 13 / 14 项）、§5.2（B23F1 行）、§5.3（C15）、§5.5（PNG 渲染的
  4 个候选方案与取舍）、§9.2（约束 6）、§9.1（门禁第 3 / 4 项）、§6.2（M2 验收点）。
- 事实依据：Q3 §3.5 风险 1（离线必抛 `ValueError: Failed to reach
  https://mermaid.ink API`）、Q3 §3.6 网络层（`mermaid.ink` 是隐式出站点）。
- 验收脚本：`harness/demo/visualization.py`（`case_draw_mermaid_png` +
  `looks_like_png` 判据）、`harness/demo/target.py:163`。
- 宪法 `.specify/memory/constitution.md`：原则 I（零出站 · 明文点名 `mermaid.ink`）、
  原则 III（PNG 硬约束）。
