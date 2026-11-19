# Feature Specification: B23F1 · `draw_mermaid_png()`：离线不阻断 ★

**Feature Branch**: `b23f1-draw-mermaid-png-offline`

**Created**: 2026-11-20

**Status**: Draft

**Input**: User description: "B23F1 · `draw_mermaid_png()`：离线不阻断 —— 交付 `draw_mermaid_png()`：**方法名必须与 LangGraph 同名**（否则固定脚本第 163 行必须改），且在**离线**环境下**不得抛阻断性异常**，返回的字节**必须是可被 `IPython.display.Image` 接受的合法 PNG**。v1 只交付占位 PNG（标准库最小 PNG 编码器，零依赖、零出站），真实图形渲染归 v2 / 可选 `[png]` extra。前置依赖 **B22F1**（已交付）。"

> **MVP 定位**：本 feature 是固定脚本 `harness/demo/target.py` 所需 **6 项**中的**最后一项**。
> `target.py:163` 的 `get_graph(xray=True).draw_mermaid_png()` 位于 `target.py:168` 的
> `invoke()` **之前** ⇒ 本 feature 未就绪 ⇒ 脚本在到达验收点之前中断。六项齐备即 **MVP 达成**。
> **本 feature 只交付 PNG 字节导出**；mermaid 文本口径以 **B22F1** 契约 §5 为准，MUST NOT 改写。

> **v1 口径（立项书 §5.5 · D14 / D15 · 宪法 v1.7.0）**：v1.0 的发行元数据**不含任何 extra**
> ⇒ B23F1 在 v1.0 **只交付占位 PNG（方案 C）**；本地真实 PNG 渲染（方案 D · `playwright`
> 本地 Chromium）**随 `[png]` extra 归 v2.0**，本 feature MUST NOT 实现，且 MUST NOT 在
> `pyproject.toml` 中新增 `[project.optional-dependencies]`。

---

## 承接条款（上游 feature → 本 feature）

> 宪法「跨 feature 承接的接线通则」：上游 feature 指名本 feature 的跨 feature 义务
> MUST 在本 spec 落成 **FR + 裁定**；**只接线 · MUST NOT 新增门禁编号 · MUST NOT 放宽判据**。

| # | 承接方 | 里程碑 | 动作 | 来源 | 本 spec 落点 |
|---|---|---|---|---|---|
| **H-1** | **B22F1 → B23F1** | **M2** | **PNG 的文本前置**：`Graph.draw_mermaid()` 返回的**合法 mermaid 文本**是 `draw_mermaid_png()` 的**唯一图源**；本 feature MUST 复用该文本与既有转义口径，MUST NOT 另写一套 mermaid 生成器；PNG 路径 MUST NOT 访问 `mermaid.ink` 或任何外部域名。 | `specs/b22f1-get-graph-mermaid/contracts/graph-export-contract.md` §5 / §8 · B22F1 spec D-1 | FR-012 · FR-013 · 裁定 5 |
| **H-2** | **B22F1 → B23F1** | **M2** | **条件边与节点声明边的可见性**：`draw_mermaid_png()` MUST 以 B22F1 的**完整 `draw_mermaid()` 文本**为唯一图源 ⇒ MUST NOT 只取静态边、MUST NOT 另算 / 过滤条件边、节点声明边、join 边或终结 `END` 边。**v1 占位图标不反映真实拓扑**；**v2 真实渲染 MUST 保留全部这些边**。 | B22F1 spec D-2 · 契约 §8 | FR-012 · FR-013 · 裁定 5 |
| **H-3** | **B7F3 → B23F1** | **M2** | **就绪顺序**：只读基准脚本的调用顺序是「**先** `get_graph(...).draw_mermaid_png()`，**后** `invoke(...)`」⇒ 本 feature MUST 先于固定脚本端到端轮（**EV-4**）就绪；MUST 做到**任何运行之前** PNG 导出即可用。 | `specs/b7f3-invoke-full-state/spec.md` 下游承接 **D-3** · 契约 **CF-03** | FR-016 · SC-009 |
| **H-4** | **B8F1 → B23F1** | **M2** | **图导出里的条件边**：PNG 路径 MUST 复用 B8F1 的 `targets` / `route_channels` 口径（条件边载荷的**恰 5 键**）⇒ MUST NOT 另算一份目标集合；条件边的路由通道（`branch:to:<target>`）**只作声明载体**（**从不被写入**）⇒ MUST NOT 把它当成「已写入的通道」或图节点。 | `specs/b8f1-conditional-edges-fresh-read/spec.md` 下游承接 **D-4** · `conditional-edge-contract.md` §2.1 | FR-012 · FR-013 · 裁定 5 |
| **H-5** | **B8F2 → B23F1** | **M2** | **图导出与流式互不影响**：`draw_mermaid_png` MUST NOT 依赖 `stream()` 的副作用；`stream()` MUST NOT 调用 PNG 导出。两者只在「同一张编译产物」上共享只读规格（`_spec` / 条件边载荷）。 | `specs/b8f2-stream-modes/spec.md` 下游承接 **D-4** | FR-013 · SC-014 |
| **H-6** | **B7F1 / B3F1 → B23F1** | **M2** | **门禁 3 的固定脚本**：宪法质量门禁 3「`harness/demo/target.py` 原样可跑」在本 feature 与 B22F1 等前置齐备前物理不可达成 ⇒ 本 feature MUST 交付其中的「PNG 导出」环节，**MUST NOT** 改动固定脚本的**任何一行**（`target.py` 是**只读基准**）。 | `specs/b3f1-scaffold-ci-gates/spec.md` 裁定 22 · 立项书 §6.2 | FR-018 · SC-009 |
| **H-7** | **B2F1 / B2F2 → B23F1** | **M1** | **自有类型与门面冻结**：`Graph` 的类型名与导入路径已在 B2F1 冻结（`freegraph.contracts.graph`）；`freegraph.graph` 的公开符号面由 B2F2 冻结 ⇒ 本 feature MUST **仅追加** `Graph.draw_mermaid_png()` 方法，MUST NOT 改字段 / 构造签名 / 不可哈希 / `__all__`，MUST NOT 新增公开顶层符号。 | `specs/b2f1-contracts-protocols/contracts/public-api.md` §6 / §8 · B2F1 T-5 | FR-015 · SC-015 · 破面 **T-1** |
| **H-8** | **B3F1 / 立项书 D14 / D15 → B23F1** | **M2** | **v1 只交付占位 PNG**：v1.0 发行元数据不含 extra ⇒ 本 feature MUST NOT 引入 `playwright` / `mermaid-cli` / `pillow` / `cairosvg` 等任何渲染依赖；真实渲染（方案 D）归 **v2.0**；基础安装的**零第三方运行时依赖**承诺不变。 | 立项书 §5.5 · 宪法 v1.7.0 依赖白名单条 · `contracts/extras-v2.toml` | FR-009 · SC-004 · Out of Scope |

---

## 下游承接条款（本 feature → 下一棒）

> 本 feature 冻结「PNG 字节导出 + 离线占位语义 + 零出站证据」这组跨 feature 接口。
> **只接线 · 逐条最小改动**。

| # | 承接方 | 里程碑 | 动作 | 本 spec 落点 |
|---|---|---|---|---|
| **D-1** | **B23F1 → B25F1** | **M4** | **双跑验收**：固定脚本的 **fake 模型轮**与**真实模型轮** MUST 记录 `draw_mermaid_png()` 的实际输出（字节数 / PNG 结构判据结果 / 框架出站 = 0），MUST NOT 写「符合预期」替代实测输出；真实轮受环境限制时 MUST 登记**环境偏离**，MUST NOT 用「未验证」替代。 | FR-017 · SC-008 · SC-009 |
| **D-2** | **B23F1 → v2.0 / B26** | **v2** | **真实 PNG 渲染**：方案 D（`playwright` · 本地 Chromium · 安装期 `playwright install chromium`）与纯 Python 最小 SVG→PNG 渲染器 MUST 作为**可选 `[png]` extra**（默认关闭）落地；运行期 MUST 零出站（`mermaid.ink` 仍在网络层黑名单）；本 feature 的 `draw_mermaid_png()` **调用面**（零必需参数、返回 `bytes`）MUST NOT 被破坏。 | FR-001 · FR-009 · 裁定 1 / 9 |
| **D-3** | **B23F1 → B24F1** | **M4** | **打包与兼容矩阵**：`pyproject.toml` MUST 仍无 `[project.optional-dependencies]`；依赖闭包 MUST 仍为空集；兼容矩阵 MUST 记录「v1.0 PNG = 合法占位图（非真实图形渲染）」与 v2.0 的 `[png]` 升级路径。 | FR-009 · SC-004 · SC-015 |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 断网环境也能拿到 PNG 字节 (Priority: P1)

作为内网 / 断网环境的用户，我调用 `get_graph(xray=True).draw_mermaid_png()`，
期望拿到一份 PNG 字节，而**不是** `ValueError: Failed to reach https://mermaid.ink API`；
脚本 MUST 能继续走到 `invoke()`。

**Why this priority**: 这是 C15 的最小价值面，也是固定脚本在 `invoke()` 之前不中断的**唯一**
前提。没有 P1，后续「合法字节」与「零出站」都无从谈起。

**Independent Test**: 在**禁止出站**的环境（断网 CI 任务 / socket 监测夹具）中，对一张已编译
图调用 `draw_mermaid_png()`，断言：调用不抛异常、返回类型为 `bytes`、长度 > 0。

**Acceptance Scenarios**:

1. **Given** 一张已编译的图（含业务节点、静态边、条件边），**When** 在全部网络接口不可用的
   环境中调用 `graph.draw_mermaid_png()`，**Then** 调用成功并返回非空 `bytes`。
2. **Given** 同一张图，**When** 在任何 `invoke()` / `stream()` **之前**调用
   `get_graph(xray=True).draw_mermaid_png()`，**Then** 调用成功（固定脚本调用顺序成立）。
3. **Given** 网络被阻断且 socket 被监测，**When** 调用 `draw_mermaid_png()`，**Then**
   「框架出站 = 0」且无阻断性异常。

---

### User Story 2 - 返回的字节能直接被展示 (Priority: P2)

作为用户，我会把返回的字节交给 `IPython.display.Image` 构造，期望**不抛错**；
我也希望在**未安装 IPython** 的环境中仍能独立判定字节是否合法。

**Why this priority**: 非法字节会在 `Image()` **构造阶段**抛错，同样中断固定脚本；
「不抛异常」若不伴随「合法 PNG」，等于把失败推迟到下一行。

**Independent Test**: 用**独立于 IPython** 的 PNG 结构判据（签名 + 块结构 + CRC 自洽）
校验返回字节；在 IPython 可用的环境中额外做一次 `Image(data)` 冒烟（可选）。

**Acceptance Scenarios**:

1. **Given** `draw_mermaid_png()` 返回的字节，**When** 按 PNG 规范逐块解析，
   **Then** 签名正确、首块为 `IHDR`、每个块的长度 / 类型 / CRC 自洽、末块为 `IEND`。
2. **Given** 同一份字节，**When** 在装有 IPython 的环境构造 `IPython.display.Image(data)`，
   **Then** 构造不抛异常（本判据为**可选冒烟**，不替代结构判据）。
3. **Given** 解压 `IDAT` 数据，**When** 校验扫描行结构，**Then** 每行以合法过滤字节开头，
   解压后长度与 `IHDR` 声明的宽高 / 位深 / 颜色类型一致。
4. **Given** 两张不同的 `Graph`，**When** 分别调用 `draw_mermaid_png()` 并解码像素，
   **Then** 两次字节**逐字节相同**，且画面是**固定示意图标**（3 个方框 + 2 条连线）、
   至少 3 种颜色、非单色（不要求与真实节点 / 边对应）。

---

### User Story 3 - 离线场景没有隐藏的兜底网络请求 (Priority: P3)

作为维护者，我希望「离线不抛异常」**不是**靠「捕获网络异常后返回占位」实现的
（那仍然发起了出站），而是实现路径上**根本没有网络代码**。

**Why this priority**: 这是「零出站」承诺最容易被绕过的地方；请求已经发出再兜底，
在合规与安全意义上是失败。

**Independent Test**: 对 `src/freegraph/**` 做静态扫描（AST / 文本），断言无网络客户端调用；
在 socket 监测夹具下调用 `draw_mermaid_png()`，断言「框架出站 = 0」。

**Acceptance Scenarios**:

1. **Given** `src/freegraph/**` 的源码，**When** 扫描网络客户端（`socket` / `http.client` /
   `urllib.request` / `requests` / `httpx` / `aiohttp` 等）与域名 `mermaid.ink`，
   **Then** 命中数为 0。
2. **Given** 父进程设置了诱导出站的环境变量（如 `HTTP_PROXY` / `HTTPS_PROXY`），
   **When** 调用 `draw_mermaid_png()`，**Then** 框架不读取任何环境变量且仍成功。
3. **Given** socket 监测夹具（只观测、不阻断），**When** 调用 `draw_mermaid_png()`，
   **Then** 调用栈归因于 `freegraph/` 的出站连接数为 0。

---

### Edge Cases

- **空图**：`Graph()` 无节点无边时 MUST 仍返回**合法** PNG（非空字节），MUST NOT 抛异常。
- **仅含 `__start__` / `__end__` 的退化图**：MUST 返回合法 PNG。
- **节点名含引号 / 换行 / 反斜杠 / 花括号 / 非 ASCII / emoji**：PNG 导出 MUST 成功；
  MUST NOT 因标签字符而失败（文本转义归 B22F1）。
- **含条件边 / 节点声明动态边 / join 边 / 终结 `END` 边**：PNG 路径 MUST 不丢边、不重算、
  不另造边集合；MUST 以完整 `draw_mermaid()` 文本为唯一图源。
- **`draw_mermaid()` 返回特殊文本**（空图头部、极长文本、含 `#` / `&` / `|`）：
  `draw_mermaid_png()` MUST 仍返回合法 PNG；MUST NOT 因文本内容而改变合法性。
- **在 `invoke()` / `stream()` 之前调用**：MUST 成功（静态导出，无运行依赖）。
- **在 `invoke()` / `stream()` 之后调用**：MUST 成功，且结果与运行次数无关（确定性）。
- **`stream()` 运行期间并发调用**：MUST 成功且不读取流式副作用；MUST NOT 因并发而失败。
- **多次重复调用**：同一张图 MUST 返回**逐字节相同**的 PNG（确定性）。
- **未安装 IPython**：MUST 仍成功返回合法 PNG；IPython 不是 freegraph 的依赖。
- **安装了 IPython**：`Image(data)` 构造 MUST 接受该字节（可选冒烟）。
- **无 `[png]` extra（v1.0 的默认与唯一形态）**：MUST 返回占位 PNG；MUST NOT 尝试导入
  `playwright` 或调用任何浏览器 / 外部进程。
- **`pyproject.toml` 无 extra**：MUST NOT 因缺少可选依赖而失败或降级为异常。
- **调用方要求文件名 / 输出路径**：v1 **无此参数**；调用方 MUST 使用无参形式
  （或 v2 的 `[png]` 能力），本 feature MUST NOT 隐式写文件。
- **重复导入 / 重载**：MUST NOT 产生全局可变状态或残留临时文件。

---

## Upstream Parity *(mandatory — 宪法原则 XI「上游优先」)*

**Upstream version**: `langgraph` **1.2.11** + `langchain-core` **1.6.3**（行号取证于
2026-11-20 · 用户 site-packages · 非仓库依赖）+ `langchain-core` **1.7.6**（`.venv`
差分组 · 行为复核）。换版本 MUST 重新核实全部行号与差分断言。

| # | 语义点 | 上游实现（版本 + `路径:行号`） | freegraph 口径 | 关系 | 理由 |
|---|---|---|---|---|---|
| P-01 | `draw_mermaid_png` 的挂载位置 | `langchain_core/runnables/graph.py:632`（1.6.3）/ `:635`（1.7.6）（`Graph.draw_mermaid_png`）；经 `get_graph()` 返回的 `Graph` 调用 | `freegraph.contracts.graph.Graph.draw_mermaid_png()`（**同名**，挂在自有 `Graph` 上） | **SAME（挂载）** | 固定脚本与上游调用点一致；自有类型约束见 P-12 |
| P-02 | 返回类别 | `graph.py:632`（1.6.3）/ `:635`（1.7.6）注解 `-> bytes` | 返回内置 `bytes`（非 `bytearray` / `str`） | **SAME** | C15 与固定脚本 `Image(...)` 的输入要求 |
| P-03 | 调用点在 `get_graph` 之后 | `langgraph/pregel/main.py:845`（`get_graph`）；`:919`（`self.get_graph().draw_mermaid_png()`） | `get_graph(xray=True/False)` 的返回值 MUST 具备该方法；**任何运行之前**可用 | **SAME** | H-3 / 固定脚本顺序 |
| P-04 | 默认渲染方法 = 公网 API | `langchain_core/runnables/graph_mermaid.py:277`（1.6.3）/ `:317`（1.7.6）（`draw_mermaid_png`）；`:405` / `:445`（`_render_mermaid_using_api`）；`:422-423` / `:462-463` 默认 `https://mermaid.ink`；`:461` / `:501` `requests.get` | **实现路径无网络代码**；MUST NOT 访问 `mermaid.ink`；离线必然成功 | **STRICTER** | 宪法原则 I 明文点名 `mermaid.ink` 为网络层黑名单；Q3 E5 实测离线必抛 `ValueError` |
| P-05 | 本地浏览器渲染路径 | `graph_mermaid.py:307`（`MermaidDrawMethod.PYPPETEER`）；`:334-342`（`_render_mermaid_using_pyppeteer`，需 pyppeteer + 浏览器） | v1 **不采用**；真实本地渲染归 v2 的 `[png]` extra；v1 的基础安装 MUST NOT 拉起浏览器依赖 | **DIFF**（v1） | 宪法 v1.7.0：v1.0 无 extra；`playwright` 等归 v2；X-03 |
| P-06 | 方法签名 | `graph.py:632-647`（1.6.3）/ `:635-650`（1.7.6）：仅关键字参数族（`curve_style` / `node_colors` / `output_file_path` / `draw_method` / `background_color` / `padding` / `max_retries` / `retry_delay` / `frontmatter_config` / `base_url` / `proxies`） | `draw_mermaid_png(self) -> bytes`：**零必需参数、零可选参数**；与上游**调用点**（无参）兼容 | **DIFF** | v1 占位渲染无样式 / 网络 / 文件参数；避免暴露 `draw_method=API` 等**误导性**入口；X-01 |
| P-07 | 文件输出 | `graph.py:638`（1.6.3）/ `:641`（1.7.6）（`output_file_path`）；`graph_mermaid.py:397-399` / `:464-465`（1.6.3）、`:437-439` / `:504-505`（1.7.6）写文件 | v1 **不写文件**、无 `output_file_path`；MUST NOT 产生临时文件 | **DIFF** | 零副作用 / 确定性；文件输出归 v2；X-02 |
| P-08 | mermaid 文本来源 | `graph.py:689-695`（1.6.3）/ `:692-698`（1.7.6）：先 `self.draw_mermaid(...)`，再把文本交给渲染器；`graph_mermaid.py:45`（1.6.3）/ `:86`（1.7.6）（`draw_mermaid` 纯本地） | MUST 先调用 `self.draw_mermaid()`，以其返回值为**唯一图源**；MUST NOT 另写生成器 | **SAME** | H-1 / H-2；B22F1 契约 §8 |
| P-09 | 离线失败信号 | Q3 E5：上游离线抛 `ValueError: Failed to reach https://mermaid.ink API`（`graph_mermaid.py:484-503`（1.6.3）/ `:524-543`（1.7.6）的重试 / 失败路径） | 离线 MUST **不抛阻断性异常**；MUST NOT 以「捕获网络异常」实现 | **STRICTER** | 宪法原则 III / I；固定脚本必须越过第 163 行 |
| P-10 | PNG 内容 | 上游返回真实渲染图像（真实图形） | v1 返回**固定示意图标**（3 个方框 + 2 条连线）；真实图形渲染归 v2 | **DIFF** | 立项书 §5.5 方案 C；宪法 v1.7.0；X-03 |
| P-11 | 输出确定性 | 上游不承诺字节级确定性（渲染服务 / 浏览器可能变化） | 同一 `Graph` 重复调用、以及不同 `Graph` 之间 MUST 返回**逐字节相同**的 PNG | **STRICTER** | 可复现 / 可断言 / 零外部状态 |
| P-12 | 依赖与类型来源 | 上游依赖 `langchain-core`（PNG 路径还依赖 `requests` / 可选 `pyppeteer`） | 自有 `Graph`；只用标准库；MUST NOT import `langchain` / `langchain-core` / `langgraph` / `langsmith`；MUST NOT 读环境变量 | **DIFF** | 原则 I / II / IX；零第三方运行时依赖 |
| P-13 | PNG 结构合法性 | 上游返回的字节由外部渲染服务 / 浏览器生成（通常为合法 PNG） | 返回字节 MUST 满足 PNG 规范（ISO/IEC 15948），可被 `IPython.display.Image` 接受 | **SAME（判据）** | C15 / 固定脚本 `display(Image(...))` |
| P-14 | 非法渲染参数的错误信号 | `graph_mermaid.py:307-329`（1.6.3）/ `:347-369`（1.7.6）：非法 `draw_method` ⇒ `ValueError` | v1 无参数 ⇒ 无此失败面；对任何 `Graph` MUST NOT 抛异常 | **DIFF**（面收敛） | 参数面归 v2；v1 只保留「永不阻断」 |

### 差分场景组 *(mandatory)*

> **落点**：`tests/differential/parity_probe.py` ⇒ **CI 的 Linux 全量档真跑**
> （上游缺席即 skip · 上游或网络缺席时对应断言 skip · 沿用 B5F2 的「缺席即 skip」纪律）。
> 上游对照只断言**可判定的结构 / 类别**；MUST NOT 断言 PNG 像素或字节与上游相等。

| # | 场景 | 断言（可判定） | 判词 |
|---|---|---|---|
| D-01 | 方法存在性 | 两侧 `get_graph()` 返回对象的类型都有 `draw_mermaid_png`，且可无参调用 | SAME |
| D-02 | 返回类别 | freegraph 返回 `bytes`；上游（有网络时）返回 `bytes` | SAME |
| D-03 | 固定脚本调用点 | 两侧 `get_graph(xray=True).draw_mermaid_png()` 均可完成（freegraph 离线；上游需网络，离线即跳过对照） | SAME |
| D-04 | 离线行为 | 网络不可用时：上游抛 `ValueError`（文档化 DIFF）；freegraph 成功返回合法 PNG | DIFF（P-04 / P-09） |
| D-05 | PNG 结构 | freegraph 的字节通过签名 + `IHDR` + 块 CRC + `IEND` 判据；上游字节（若可得）亦通过 | SAME（判据） |
| D-06 | 空图 | 两侧对空图均返回 `bytes`（上游需网络，离线即跳过对照） | SAME |
| D-07 | 确定性 | freegraph 连续两次调用逐字节相等，且不同 `Graph` 之间亦相等（固定图标）；MUST NOT 要求上游相等 | STRICTER |
| D-08 | 签名差异 | 上游接受 `draw_method` / `output_file_path` 等关键字；freegraph v1 只接受零参数 | DIFF（P-06 / P-07） |
| D-09 | 零出站 | freegraph 调用全过程框架出站 = 0；上游默认 API 路径出站 ≥ 1（文档化 DIFF） | STRICTER / DIFF |
| D-10 | 类型来源 | freegraph 的 `Graph` 模块路径为 `freegraph.contracts.graph`；上游为 `langchain_core.runnables.graph` | DIFF（P-12） |

### 偏离登记 *(仅限三类 · 其余一律照抄)*

| # | 类别 | 被偏离的判据 | 理由 | 承接方 / 追认 |
|---|---|---|---|---|
| **X-01** | 自研区（DIFF） | 上游 `draw_mermaid_png` 的关键字参数族（P-06） | v1 占位渲染无样式 / 主题 / 网络 / 文件语义；暴露 `draw_method=API` 会与零出站承诺冲突；保持零必需参数的调用面 | B23F1 · M2（v2 追加可选参数） |
| **X-02** | 自研区（DIFF） | 上游 `output_file_path` 文件写入（P-07） | v1 MUST 零文件副作用；文件输出归 v2 | B23F1 · M2（v2） |
| **X-03** | 自研区（DIFF） | 上游真实渲染 / 浏览器后端 / 公网 API（P-04 / P-05 / P-10） | 宪法 v1.7.0：v1.0 零依赖、无 extra；方案 C 是 v1 唯一交付形态；方案 D 归 v2 | B23F1 · M2 · v2 / B26 |
| **X-04** | 更严的输出约束（STRICTER） | 输出确定性（P-11） | 同图同字节 ⇒ 可复现、可断言、零外部状态 | B23F1 · M2 |
| **X-05** | 更严的失败信号（STRICTER） | 离线失败信号（P-09） | 「捕获网络异常后返回占位」**不算合规**（请求已发出）；MUST 无网络代码路径 | B23F1 · M2 |

**X ↔ P 对应（三表一致的可判定锚点）**：X-01↔P-06 · X-02↔P-07 · X-03↔P-04/P-05/P-10 ·
X-04↔P-11 · X-05↔P-04/P-09。

### 破冻结面的回溯修订清单 *(若有)*

| # | 冻结面 | 回溯修订位置 | 冻结断言处置 | 追认 / 承接方 |
|---|---|---|---|---|
| **T-1** | B2F1：`Graph` 类型面（2 字段 · 不可哈希；B22F1 已追加 `draw_mermaid`） | **仅追加** `Graph.draw_mermaid_png() -> bytes` 方法 | **拆分而不删**：`nodes` / `edges` 字段、构造签名、不可哈希、浅不可变与 `draw_mermaid` 的既有断言全部保留；新增方法断言为**追加**；`__all__` 不变 | 授权来源：B22F1 契约 §8「下游接口（B23F1）」+ 本 feature 提示词 → B23F1 · M2 |

> **不新增公开顶层符号**：`draw_mermaid_png` 是 `Graph` 的实例方法；
> `freegraph.__all__` / `freegraph.graph.__all__` / `freegraph.contracts.__all__` /
> `freegraph.contracts.graph.__all__` 均不变。

---

## Clarifications

### Session 2026-11-20（设计裁定 · spec 阶段写死，plan 不得再翻）

> **背景**：提示词初稿已写死「同名方法 · 离线不阻断 · 合法 PNG · 零出站 · v1 占位」。
> 本节给出唯一口径；上游有答案处照抄（原则 XI），上游无答案处（占位编码器 / 零出站约束）
> 由本节裁定。

#### Q1（方法签名与调用面）

→ **A：`def draw_mermaid_png(self) -> bytes`（零参数）**。

- 方法名 MUST 与上游**同名**；固定脚本的无参调用 MUST 原样可用；
- v1 MUST NOT 暴露 `draw_method` / `output_file_path` / `base_url` / `proxies` /
  `curve_style` 等上游参数（X-01 / X-02）；它们随 v2 的 `[png]` 能力再评估；
- API 快照的判定口径 = **方法存在 + 可无参调用 + 返回 `bytes`**，**不**要求与上游
  关键字参数族逐项相等（P-06 已登记 DIFF）。

#### Q2（v1 的 PNG 内容）

→ **A：固定示意图标（方案 C）**。

- MUST 是**真实可解码的 PNG**，不是「只贴签名」的伪字节；
- 图样 MUST 为**固定示意图标**：**3 个方框 + 2 条连线**；图样 MUST NOT **反映**真实
  `Graph` 的节点 / 边；实现 MUST 仍调用 `self.draw_mermaid()`（唯一图源，FR-012），
  但该文本不参与占位图标绘制；所有 `Graph` MUST 返回相同字节（Q7）；
- 尺寸 MUST 固定为 **64×64**（实现 / 测试 MUST 采用该值）；
- 颜色 MUST ≥ 3 种（如背景 / 方框 / 连线或描边），MUST NOT 是单色；
- MUST NOT 依赖字体、外部图片或渲染服务。

#### Q3（PNG 合法性的机械判据）

→ **A：按 PNG 规范（ISO/IEC 15948）逐块校验**。

1. 8 字节签名 `89 50 4E 47 0D 0A 1A 0A`；
2. **首块** MUST 为 `IHDR`，长度 == `13`；
3. `IHDR` 的宽 / 高 MUST ≥ 1；位深 / 颜色类型 / 压缩 / 过滤 / 交织 MUST 是规范允许的组合；
4. **每个块**的长度字段与实际数据长度一致；类型字段为 4 个 ASCII 字母；
5. **每个块**的 CRC 为 `type + data` 的 CRC-32，且与块内记录值一致；
6. `IDAT` MUST 存在，且其 `zlib` 解压结果 MUST 满足扫描行约束（每行首字节为合法过滤字节，
   解压长度与 `IHDR` 声明一致）；
7. **末块** MUST 为 `IEND`，长度 == `0`，且其后无尾随字节；
8. 判据 MUST **独立于 `IPython` / `PIL`**（不得用「IPython 不报错」替代结构校验）。

#### Q4（离线实现路径）

→ **A：实现路径上 MUST NOT 存在网络代码**。

- MUST NOT import `socket` / `http` / `http.client` / `urllib.request` / `requests` /
  `httpx` / `aiohttp` 等网络客户端；
- MUST NOT 以「先请求、失败后 catch 并返回占位」实现；
- MUST NOT 调用 `mermaid.ink` 或任何外部域名；
- MUST NOT 启动子进程 / 外部浏览器 / `mermaid-cli`；
- MUST NOT 读取任何环境变量。

#### Q5（mermaid 文本的复用）

→ **A：`self.draw_mermaid()` 是唯一图源**。

- `draw_mermaid_png()` MUST 先取得 `self.draw_mermaid()` 的返回值；
- MUST NOT 另写 mermaid 生成器，MUST NOT 只取静态边、MUST NOT 过滤条件边 / 声明边；
- v1 占位图不把文本像素化，但 **文本仍是权威图源**；v2 真实渲染 MUST 直接消费该文本；
- 本 feature MUST NOT 改变 `draw_mermaid()` 的输出语义 / 转义 / 确定性。

#### Q6（失败信号）

→ **A：对任何 `Graph` MUST NOT 抛阻断性异常**。

- 空图 / 退化图 / 特殊字符节点名 / 超长文本 / 多次调用：全部成功返回 `bytes`；
- v1 无参数 ⇒ 无「非法参数」失败面；
- MUST NOT 因「未安装 `[png]` extra」而失败（v1 本来就没有 extra）；
- MUST NOT 以 catch-all 兜底**内部编码错误**：本地编码器 MUST 对任何 `Graph` 正确，
  边界由测试覆盖；未预期的实现 bug MUST 暴露，不得静默成一张假占位图（用户 2026-11-20 确认）；
- 若未来 v2 引入可选参数，其失败信号另立契约，MUST NOT 追溯影响 v1 的零参调用。

#### Q7（确定性）

→ **A：同一 `Graph` 的重复调用 MUST 返回逐字节相同的 PNG；不同 `Graph` 之间亦 MUST 相同**。

- MUST NOT 依赖随机数 / 时间 / 进程 id / 环境变量 / 网络 / 外部文件；
- 不同 `Graph` 之间 MUST 返回相同占位字节（固定示意图标，不反映真实图结构）。

#### Q8（放置位置与公开面）

→ **A：作为 `Graph` 的实例方法，追加在 `freegraph.contracts.graph`**。

- 编码器可为**私有**助手（模块级私有函数 / 私有常量），MUST NOT 进入 `__all__`；
- MUST NOT 新增公开模块或公开顶层符号；
- MUST NOT 新增第三方依赖或 `[project.optional-dependencies]`。

#### Q9（v1 与 v2 的边界）

→ **A：本 feature 只做方案 C**。

- 方案 D（`playwright` 本地 Chromium）与纯 Python SVG→PNG 渲染器 MUST NOT 在本 feature 实现；
- `[png]` extra MUST NOT 在 v1.0 的 `pyproject.toml` 出现（宪法 v1.7.0 / D15）；
- 本 feature 的零参调用面 MUST 是 v2 的兼容基线。

#### Q10（并发 / 可重入）

→ **A：无共享可变状态**。

- 并发 / 重入调用 MUST 成功；MUST NOT 写模块级缓存 / 临时文件；
- `Graph` 的只读字段 MUST NOT 被修改。

---

### Session 2026-11-20（clarify 轮 · 用户参与）

- Q: SC-005 的「方法名与签名与 LangGraph 一致」在 v1 只交付占位图的前提下应如何判定？
  → A: **只判「同名 + 可无参调用 + 返回 bytes」的调用面兼容**；不要求镜像上游的关键字参数族
  （维持 Q1 / X-01；用户 2026-11-20 确认）。
- Q: v1 的占位 PNG 应该长什么样？
  → A: **固定示意图标：3 个方框 + 2 条连线**；图样不反映真实节点 / 边，所有 `Graph`
  MUST 返回相同字节（实现仍以 `draw_mermaid()` 为唯一图源，但占位图不把文本像素化）
  （Q2 / FR-010；用户 2026-11-20 确认）。
- Q: 「3 个方框 + 2 条连线」是指真实 start/end/节点被 edge 连接，还是整个 graph？
  → A: **都不是真实拓扑**。v1 只画**固定示意图标**（不反映真实节点 / 边）；真实 `Graph`
  的节点 / 边拓扑归 v2，MUST NOT 在 v1 实现（Q2 / Out of Scope；用户 2026-11-20 确认）。
- Q: 如何自动验证这张固定示意图标确实画对了？
  → A: **结构判据**：固定 64×64、至少 3 种颜色、非单色；再用两次调用（含不同 `Graph`）
  逐字节相等证明确定性；**不**逐字节比对 golden 哈希（避免 zlib 版本差异误报）
  （Q2 / SC-016；用户 2026-11-20 确认）。
- Q: PNG 编码器遇到预期之外的内部错误（例如未来引入的 bug）时应如何处理？
  → A: **不写 catch-all，让异常暴露**；本地编码器必须对任何 `Graph` 正确，边界靠测试覆盖，
  不得静默兜底成假占位图（Q6 / FR-011；用户 2026-11-20 确认）。

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系统 MUST 提供 `Graph.draw_mermaid_png()` 方法（**与 LangGraph 同名**），
  返回内置 `bytes`（C15）。
- **FR-002**: 该方法 MUST 可**无参调用**；固定脚本
  `get_graph(xray=True).draw_mermaid_png()` MUST 原样可用。
- **FR-003**: 在**离线**环境下调用 MUST **不抛阻断性异常**；MUST NOT 因网络不可达而失败。
- **FR-004**: 返回字节 MUST 是**结构合法的 PNG**（ISO/IEC 15948）：
  ① 8 字节签名；② 首块 `IHDR` 且长度 13；③ 每块长度 / 类型 / CRC 自洽；
  ④ `IDAT` 可 `zlib` 解压且扫描行合法；⑤ 末块 `IEND` 且长度 0、无尾随字节；
  ⑥ 宽 / 高 ≥ 1 且位深 / 颜色类型组合合法。
- **FR-005**: 返回字节 MUST 可被 `IPython.display.Image` 接受；该判定 MUST **独立于
  `IPython`**（以 PNG 结构判据为准，IPython 冒烟为可选）。
- **FR-006**: 实现 MUST 只使用**标准库**（如 `zlib` / `struct`）；MUST NOT 引入任何第三方依赖。
- **FR-007**: 实现路径 MUST **无网络代码**：MUST NOT import / 调用 `socket`、`http`、
  `urllib.request`、`requests`、`httpx`、`aiohttp` 等网络客户端；MUST NOT 访问
  `mermaid.ink` 或任何外部域名；MUST NOT 启动子进程 / 外部浏览器 / `mermaid-cli`。
- **FR-008**: 系统 MUST NOT import `langchain` / `langchain-core` / `langgraph` / `langsmith`；
  MUST NOT 读取任何环境变量。
- **FR-009**: v1 的 PNG 内容 MUST 为**占位图**；「真实图形渲染」MUST NOT 在本 feature 实现；
  MUST NOT 引入 `playwright` / `pillow` / `cairosvg` / `pymupdf` 等渲染依赖；
  `pyproject.toml` MUST NOT 新增 `[project.optional-dependencies]`。
- **FR-010**: v1 的占位图 MUST 是**真实可解码的固定示意图标**：**3 个方框 + 2 条连线**，
  图样 MUST NOT **反映**真实 `Graph` 的节点 / 边；实现 MUST 仍以 `self.draw_mermaid()` 为
  唯一图源（FR-012），但占位图不把该文本像素化；所有 `Graph` MUST 返回相同字节；
  尺寸 MUST 固定为 **64×64**、**至少 3 种颜色且非单色**；
  MUST NOT 依赖字体 / 外部图片 / 渲染服务。
- **FR-011**: 对**任何** `Graph`（含空图、退化图、特殊字符节点名）MUST 成功返回 `bytes`；
  MUST NOT 抛异常；MUST NOT 以 catch-all / 静默兜底掩盖内部编码错误（未预期 bug MUST 暴露）。
- **FR-012**: `draw_mermaid_png()` MUST 以 `self.draw_mermaid()` 的返回值为**唯一图源**；
  MUST NOT 另写 mermaid 生成器；MUST NOT 只取静态边、MUST NOT 过滤 / 重算条件边、
  节点声明边、join 边或终结 `END` 边；MUST NOT 改动 `draw_mermaid()` 的输出语义。
  **v1 占位图标不反映真实拓扑**；**v2 真实渲染 MUST 保留全部条件边 / 声明边 / join 边 /
  终结 `END` 边**（不得只渲染静态边）。
- **FR-013**: PNG 导出 MUST 是**纯只读**：MUST NOT 依赖 `invoke()` / `stream()` 的副作用；
  `stream()` MUST NOT 调用 PNG 导出；MUST NOT 修改 `Graph` 或其共享内部状态。
- **FR-014**: 同一 `Graph` 重复调用 MUST 返回**逐字节相同**的 PNG；**不同 `Graph` 之间亦
  MUST 返回相同占位字节**（固定示意图标）；输出 MUST NOT 依赖随机数 / 时间 / 进程 id /
  环境变量 / 网络 / 外部文件。
- **FR-015**: 本 feature MUST **仅追加** `Graph.draw_mermaid_png()` 方法：MUST NOT 改
  `Graph` 的字段 / 构造签名 / 不可哈希 / 元组容器；MUST NOT 新增公开顶层符号或公开模块。
- **FR-016**: 该方法 MUST 在**任何运行之前**可用（`compile()` 后、`invoke()` / `stream()` 前）；
  `get_graph(xray=True)` 与 `get_graph(xray=False)` 的返回值 MUST 都具备该方法。
- **FR-017**: MUST 提供**离线等价性证据**：在「全部网络接口不可用」的 CI 任务（G28）中
  本方法仍成功；且 G27 / socket 监测夹具下「框架出站 = 0」（observe-only 归因）。
- **FR-018**: MUST NOT 改动 `harness/demo/target.py` 的**任何一行**；`target.py` diff 断言常驻；
  MUST 交付 `harness/verification/B23F1/manual-verification.md`。
- **FR-019**: 并发 / 重入调用 MUST 成功；实现 MUST NOT 使用模块级可变缓存或写临时文件。
- **FR-020**: 返回类型 MUST 精确为 `bytes`（不是 `str` / `bytearray` / memoryview）；
  长度 MUST > 0。

### Key Entities

- **`Graph.draw_mermaid_png()`**: 自有 `Graph` 上的 PNG 字节导出方法（C15）；
  零必需参数、返回 `bytes`、离线不阻断、确定性。
- **占位 PNG 编码器**: 只依赖标准库的最小 PNG 编码实现（方案 C）；
  产出签名 + `IHDR` + `IDAT` + `IEND`，每块 CRC 自洽；私有助手，不新增公开符号。
- **固定示意图标**: v1 的占位画面——**3 个方框 + 2 条连线**，所有 `Graph` 相同；
  MUST NOT **反映**真实节点 / 边；固定 **64×64**、至少 3 种颜色、非单色。
- **PNG 块结构**: 签名 / `IHDR` / `IDAT` / `IEND` 与每块「长度 + 类型 + 数据 + CRC」；
  合法性判据引用 **ISO/IEC 15948**。
- **唯一图源（mermaid 文本）**: B22F1 的 `Graph.draw_mermaid()` 输出；PNG 路径 MUST 复用它，
  MUST NOT 另算条件边 / 声明边 / join 边。
- **离线证据（socket 监测夹具 + 静态扫描）**: 「框架出站 = 0」与「零网络客户端调用」的
  可判定证据；按调用栈归因，只对 `freegraph/` 断言 0。
- **固定脚本（只读基准）**: `harness/demo/target.py`；本 feature MUST NOT 修改其任何一行。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 在禁止出站的 CI 任务中，`draw_mermaid_png()` 对一张已编译图的调用**成功率
  == 100%**，且无阻断性异常（断网任务退出码 0）。
- **SC-002**: 返回字节通过 PNG 结构判据的**比例 == 100%**（签名 + `IHDR` + 每块 CRC +
  `IDAT` 解压 + `IEND` + 无尾随字节）。
- **SC-003**: `src/freegraph/**` 静态扫描的网络客户端调用数 == **0**；G27 / socket 监测夹具下
  「框架出站 = 0」（observe-only 归因）。
- **SC-004**: freegraph 的运行时依赖闭包**仍为空集**（新增依赖 == 0；
  `pyproject.toml` 无 `[project.optional-dependencies]`）。
- **SC-005**: API 快照通过：`Graph` 上存在 `draw_mermaid_png`，可无参调用，返回 `bytes`
  （对应上游调用点 P-03；不要求与上游关键字参数族逐项相等）。
- **SC-006**: 在装有 IPython 的环境中，`IPython.display.Image(data)` 构造成功率为 100%
  （**可选冒烟**；权威判据仍是 SC-002）。
- **SC-007**: 同一 `Graph` 连续两次调用、以及**不同 `Graph` 之间**，返回**逐字节相同**的
  PNG（相等率 100%；固定示意图标不反映真实节点 / 边）。
- **SC-008**: 空图、退化图、特殊字符节点名、含条件边 / 声明边 / join 边的图，
  调用成功率均 == 100%。
- **SC-009**: 固定脚本 `target.py` 的 diff 行数 == **0**；人工验证记录存在且正文非空；
  `get_graph(xray=True).draw_mermaid_png()` 在 `invoke()` 前可完成。
- **SC-010**: `sys.modules` 中 `langchain` / `langchain_core` / `langgraph` / `langsmith`
  的出现次数 == 0；环境变量读取次数 == 0。
- **SC-011**: 并发 / 重入调用（≥ 2 个线程或 ≥ 2 次连续调用）成功率 == 100%，
  且不产生临时文件。
- **SC-012**: PNG 的 `IDAT` 解压后的原始扫描行长度 MUST == **12,352**（64 × (1 + 64×3)），
  且每行首字节为合法过滤字节（v1 为 0）。
- **SC-013**: PNG 路径对 `draw_mermaid()` 的调用次数 ≥ 1，且未另写 mermaid 生成器；
  `draw_mermaid()` 的输出在 PNG 调用前后**逐字相同**（文本语义未被改变）。
- **SC-014**: `stream()` 调用前后，`draw_mermaid_png()` 均成功且输出**逐字节相同**；
  `stream()` MUST NOT 调用 PNG 导出。
- **SC-015**: `freegraph.__all__` / `freegraph.graph.__all__` /
  `freegraph.contracts.__all__` / `freegraph.contracts.graph.__all__` 的符号集合**不变**；
  `Graph` 的字段数 / 构造签名 / 不可哈希断言不变。
- **SC-016**: 解码后的占位图 MUST 满足**固定示意图标的结构判据**：固定 **64×64**、
  **至少 3 种颜色且非单色**；MUST NOT 要求与真实节点 / 边对应；
  验证方式为结构判据（**不**逐字节比对 golden 哈希，避免 zlib 版本差异误报）。

### 验收判据（= 立项书 §5.2 B23F1 小目标，逐条可判定）

> 小目标原文：PNG 路径离线不抛阻断性异常

| # | 判据 | 判定方式 | 覆盖 |
|---|---|---|---|
| A1 | 离线不抛阻断性异常 | 断网 CI 任务中 `draw_mermaid_png()` 成功返回 | SC-001 |
| A2 | 返回**合法** PNG 字节 | PNG 结构判据（签名 + 块结构 + CRC 自洽 · 独立于 IPython） | SC-002 / SC-012 |
| A3 | 方法名同名 | `draw_mermaid_png` 存在于 `Graph` 对象上（API 快照） | SC-005 |
| A4 | 零出站 | 静态扫描 + socket 监测夹具「框架出站 = 0」 | SC-003 |

---

## Out of Scope

- **真实图形渲染**（方案 D）——v2.0 / 可选 `[png]` extra；本 feature MUST NOT 实现。
- **按真实 `Graph` 的节点 / 边绘制拓扑**（含**无文字标签**的简易拓扑）——v1 只画
  **固定示意图标**（3 个方框 + 2 条连线）；真实拓扑归 v2，MUST NOT 提前实现。
- **`playwright` / Chromium / `mermaid-cli` / Node 工具链**——v1 零依赖承诺。
- **`pillow` / `cairosvg` / `svglib` / `pycairo` / `matplotlib` / `pymupdf` / `resvg-py`**
  ——许可证与依赖红线；MUST NOT 引入。
- **`mermaid.ink` 或任何远程渲染服务**——永久排除（宪法原则 I 网络层黑名单）。
- **上游 `draw_mermaid_png` 的参数族**（`draw_method` / `output_file_path` / `background_color` /
  `padding` / `max_retries` / `retry_delay` / `base_url` / `proxies` / `curve_style` /
  `node_colors` / `wrap_label_n_words` / `frontmatter_config`）——v1 零参；v2 再评估。
- **PNG 文件落盘 / 输出路径**——v1 不写文件；归 v2。
- **修改 `draw_mermaid()` 的文本语义 / 转义 / 确定性**——归 B22F1，本 feature 只消费。
- **模拟执行 / 运行期跳转记录**——图导出只读静态规格；本 feature MUST NOT 依赖运行。
- **节点别名 / `context` 通道**（B8F3）——PNG 路径沿用 B22F1 的节点名口径。
- **前端 / 可视化 UI**（v2 / B26）。
- **修改 `harness/demo/target.py`**——只读基准。
- **新增公开模块 / 公开顶层符号 / 第三方依赖 / extras**。

---

## Assumptions

- **上游版本**：行号取证 = `langgraph 1.2.11` + `langchain-core 1.6.3`；
  `.venv` 差分组 = `langgraph 1.2.11` + `langchain-core 1.7.6`（离线行为已重新实测同款）；
  换版本 MUST 重新核实全部行号与差分断言（宪法原则 XI）。
- **v1.0 无 extra**：宪法 v1.7.0 / 立项书 D15 已冻结「v1.0 发行元数据不含依赖包名」
  ⇒ 本 feature 只交付方案 C；`[png]`（`playwright`）与 B26（纯 Python 渲染器）归 v2.0。
- **占位图的消费语义**：下游只要求「可被 `IPython.display.Image` 接受的合法 PNG」；
  占位图固定为**示意图标**（3 个方框 + 2 条连线，所有 `Graph` 相同），**不**承诺表达
  真实图结构。真实图形渲染是 v2 的增值能力，不是 v1 的验收判据。
- **`IPython` 属脚本自身依赖**：freegraph MUST NOT 引入 `IPython`；合法性判据 MUST 独立实现。
- **PNG 规范**：判据以 **ISO/IEC 15948**（W3C PNG 规范）为准；CRC 为 PNG 规定的 CRC-32。
- **离线 CI 的可行性**：CI 可提供「全部网络接口不可用」的任务（网络命名空间 / 防火墙）；
  socket 夹具**只观测、不阻断**、按调用栈归因（MUST NOT 用阻断式 socket 夹具替代 G27 的
  observe-only 归因）。
- **固定脚本只读**：`harness/demo/target.py` MUST NOT 被本 feature 改动；本 feature 只保证其
  「PNG 导出」环节可越过，`invoke()` 之后的行为归 B7F3 / B8F1 等已交付 feature。
- **零第三方运行时依赖**：PNG 编码只用标准库 `zlib` / `struct` / `binascii`（或等价标准库）；
  类型 / API 快照只用标准库 `inspect`。
- **证据门禁**：与上游的每条语义对应 MUST 在 `research.md` / `contracts/upstream-parity.md`
  标注版本 + `路径:行号`；行为断言 MUST 有实测支撑（禁止只读源码下断言）。
- **人工门禁**：`harness/verification/B23F1/manual-verification.md`
  MUST 写明验证环境（含断网方式）、步骤、实际输出（字节数 / 结构判据结果 / 出站计数）、
  结论与遗留问题。
