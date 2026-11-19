# 与上游 LangGraph 的逐条对照（PNG 导出）

**Feature**: `B23F1` · **契约**: [png-contract.md](./png-contract.md) ·
**取证**: [../research.md](../research.md)
**核实环境**:
- 行号锚点：`langgraph 1.2.11` + `langchain-core 1.6.3`（系统 site-packages · **非仓库依赖**）
- 行为复核：`.venv` 的 `langgraph 1.2.11` + `langchain-core 1.7.6`
- CPython 3.11.16 · 取证于 **2026-11-20**

⚠️ **换上游版本后 MUST 重新核实全部行号**（宪法原则 XI）。
⚠️ **本文件是「证据」载体** ⇒ **MUST NOT** 被测试解析（测试直接断言行为）。

---

## §1 逐条对照（P-01…P-14）

| # | 语义点 | 上游（1.6.3 / 1.7.6 行号） | freegraph | 关系 | 理由 / 证据 |
|---|---|---|---|---|---|
| **P-01** | 方法挂载位置 | `graph.py:632` / `:635`（`Graph.draw_mermaid_png`）；经 `get_graph()` 返回的 `Graph` 调用 | `freegraph.contracts.graph.Graph.draw_mermaid_png()`（同名） | **SAME（挂载）** | 固定脚本与上游调用点一致；E-2 |
| **P-02** | 返回类别 | `graph.py:632` / `:635` 注解 `-> bytes` | 返回内置 `bytes` | **SAME** | C15 / `Image(...)` 输入；E-2 |
| **P-03** | 调用点在 `get_graph` 之后 | `langgraph/pregel/main.py:845`（`get_graph`）；`:919`（`self.get_graph().draw_mermaid_png()`） | `get_graph(xray=True/False)` 的返回值具备该方法；任何运行之前可用 | **SAME** | H-3；E-2 |
| **P-04** | 默认渲染方法 = 公网 API | `graph_mermaid.py:277` / `:317`；`_render_mermaid_using_api` `:405` / `:445`；默认 `https://mermaid.ink` `:422-423` / `:462-463`；`requests.get` `:461` / `:501` | **实现路径无网络代码**；MUST NOT 访问 `mermaid.ink`；离线必然成功 | **STRICTER** | 宪法原则 I；Q3 E5 实测；E-1 |
| **P-05** | 本地浏览器渲染路径 | `graph_mermaid.py:307`（`PYPPETEER`）/ `:334-342`（需 pyppeteer + 浏览器） | v1 **不采用**；真实本地渲染归 v2 的 `[png]` extra | **DIFF**（v1） | 宪法 v1.7.0：v1.0 无 extra；X-03 |
| **P-06** | 方法签名 | `graph.py:632-647` / `:635-650`：仅关键字参数族（`curve_style` / `node_colors` / `output_file_path` / `draw_method` / `background_color` / `padding` / `max_retries` / `retry_delay` / `frontmatter_config` / `base_url` / `proxies`） | `draw_mermaid_png(self) -> bytes`：**零参数**；与上游**调用点**（无参）兼容 | **DIFF** | v1 占位图无样式 / 网络 / 文件参数；X-01 |
| **P-07** | 文件输出 | `graph.py:638` / `:641`（`output_file_path`）；`graph_mermaid.py:397-399` / `:464-465`（1.6.3）、`:437-439` / `:504-505`（1.7.6）写文件 | v1 **不写文件**、无 `output_file_path` | **DIFF** | 零文件副作用；X-02 |
| **P-08** | mermaid 文本来源 | `graph.py:689-695` / `:692-698`：先 `self.draw_mermaid(...)`，再把文本交给渲染器；`graph_mermaid.py:45` / `:86`（`draw_mermaid` 纯本地） | MUST 先调用 `self.draw_mermaid()`；以其返回值为**唯一图源**；MUST NOT 另写生成器 | **SAME** | H-1 / H-2；B22F1 契约 §8 |
| **P-09** | 离线失败信号 | Q3 E5：上游离线抛 `ValueError: Failed to reach https://mermaid.ink API`（`graph_mermaid.py:484-503`（1.6.3）/ `:524-543`（1.7.6）的重试 / 失败路径） | 离线 MUST **不抛阻断性异常**；MUST NOT 以「捕获网络异常」实现 | **STRICTER** | 宪法原则 III / I；E-1 / X-05 |
| **P-10** | PNG 内容 | 上游返回真实渲染图像 | v1 返回**固定示意图标**（3 个方框 + 2 条连线）；真实图形渲染归 v2 | **DIFF** | 立项书 §5.5 方案 C；X-03 |
| **P-11** | 输出确定性 | 上游不承诺字节级确定性 | 同一 `Graph`、不同 `Graph` 之间均 **逐字节相同** | **STRICTER** | 可复现 / 可断言；E-3 / X-04 |
| **P-12** | 依赖与类型来源 | 上游依赖 `langchain-core`（PNG 路径还依赖 `requests` / 可选 `pyppeteer`） | 自有 `Graph`；只用标准库；MUST NOT import `langchain` / `langchain-core` / `langgraph` / `langsmith`；MUST NOT 读环境变量 | **DIFF** | 原则 I / II / IX；X-03 |
| **P-13** | PNG 结构合法性 | 上游字节由外部渲染服务 / 浏览器生成（通常合法） | 返回字节 MUST 满足 PNG 规范（ISO/IEC 15948），可被 `IPython.display.Image` 接受 | **SAME（判据）** | C15；E-3 |
| **P-14** | 非法渲染参数的错误信号 | `graph_mermaid.py:307-329`（1.6.3）/ `:347-369`（1.7.6）：非法 `draw_method` ⇒ `ValueError` | v1 无参数 ⇒ 无此失败面；对任何 `Graph` MUST NOT 抛异常 | **DIFF**（面收敛） | 参数面归 v2；X-01 |

---

## §2 偏离登记（X-01…X-05）

| # | 类别 | 偏离点 | freegraph 口径 | 上游 | 理由 / 追认 |
|---|---|---|---|---|---|
| **X-01** | 自研区（DIFF） | 关键字参数族（P-06） | 零参数 | 完整关键字参数族 | v1 占位图无样式 / 网络 / 文件语义；避免误导性 `draw_method=API`；B23F1 · M2 |
| **X-02** | 自研区（DIFF） | `output_file_path` 文件写入（P-07） | 不写文件 | 可写文件 | v1 零文件副作用；归 v2；B23F1 · M2 |
| **X-03** | 自研区（DIFF） | 真实渲染 / 浏览器 / 公网 API（P-04 / P-05 / P-10 / P-12） | 固定占位图（标准库） | 公网 API / pyppeteer | 宪法 v1.7.0：v1.0 零依赖、无 extra；方案 D 归 v2；B23F1 · M2 |
| **X-04** | 更严的输出约束（STRICTER） | 确定性（P-11） | 同图 / 异图逐字节相同 | 不承诺 | 可复现 / 可断言 / 零外部状态；B23F1 · M2 |
| **X-05** | 更严的失败信号（STRICTER） | 离线失败信号（P-09） | 成功返回合法 PNG | 抛 `ValueError` | 「捕获网络异常后返回占位」不算合规；无网络代码路径；B23F1 · M2 |

**X ↔ P 对应**：X-01↔P-06 · X-02↔P-07 · X-03↔P-04/P-05/P-10/P-12 ·
X-04↔P-11 · X-05↔P-04/P-09。

---

## §3 差分场景组（D-01…D-10）

> 落点：`tests/differential/parity_probe.py` 的 `_run_png_scenarios` +
> `tests/differential/test_parity_probe.py`；上游缺席 / 网络缺席即 skip
> （沿用 B5F2 纪律）。**不断言** PNG 像素 / 字节与上游相等；**不断言**行号。

| # | 场景 | 断言（可判定） | 判词 |
|---|---|---|---|
| **D-01** | 方法存在性 | 两侧 `get_graph()` 返回对象的类型都有 `draw_mermaid_png`，且可无参调用 | SAME |
| **D-02** | 返回类别 | freegraph 返回 `bytes`；上游（有网络时）返回 `bytes`（网络缺席 ⇒ skip） | SAME |
| **D-03** | 固定脚本调用点 | 两侧 `get_graph(xray=True).draw_mermaid_png()` 均可完成（freegraph 离线；上游需网络） | SAME |
| **D-04** | 离线行为 | 网络不可用时：上游抛 `ValueError`（monkeypatch `requests.get` 模拟）；freegraph 成功返回合法 PNG | DIFF（P-04 / P-09） |
| **D-05** | PNG 结构 | freegraph 字节通过签名 + `IHDR` + 块 CRC + `IDAT` + `IEND` 判据；上游字节（若可得）亦通过 | SAME（判据） |
| **D-06** | 空图 | 两侧对空图均返回 `bytes`（上游需网络，离线即 skip） | SAME |
| **D-07** | 确定性 | freegraph 连续两次调用逐字节相等，且不同 `Graph` 之间亦相等；MUST NOT 要求上游相等 | STRICTER |
| **D-08** | 签名差异 | 上游接受 `draw_method` / `output_file_path` 等关键字；freegraph v1 只接受零参数 | DIFF（P-06 / P-07） |
| **D-09** | 零出站 | freegraph 调用全过程框架出站 = 0；上游默认 API 路径出站 ≥ 1（文档化 DIFF） | STRICTER / DIFF |
| **D-10** | 类型来源 | freegraph 的 `Graph` 模块路径为 `freegraph.contracts.graph`；上游为 `langchain_core.runnables.graph` | DIFF（P-12） |

**执行口径**：

- D-01 / D-02 / D-03 / D-05 / D-06 / D-07 / D-08 / D-10 **不依赖真实网络**；
- D-04 用 `monkeypatch` 把 `requests.get` 替换为抛 `ConnectionError` 的函数，
  断言上游 `ValueError` 与 freegraph 成功（不实际建立连接）；
- D-02 / D-03 / D-06 的上游「有网络」分支为**可选**：网络不可用时 `pytest.skip`，
  不判失败；freegraph 分支始终执行。

---

## §4 实测证据（E-1…E-8）

| # | 场景 | 实测要点 |
|---|---|---|
| E-1 | 上游离线失败 | 1.6.3 与 1.7.6 均抛 `ValueError: Failed to reach https://mermaid.ink API ...` |
| E-2 | 上游挂载 / 签名 | `Graph.draw_mermaid_png` 在 `graph.py:632`（1.6.3）/ `:635`（1.7.6）；返回 `bytes`；先取 `draw_mermaid()` |
| E-3 | 占位 PNG 原型 | 173 字节 · 64×64 · `IHDR`/`IDAT`/`IEND` CRC 全绿 · 解压 12,352 字节 · 3 色 · 两次编码逐字节相同 |
| E-4 | 实施前基线 | `1700 passed, 4 skipped in 113.76s` |
| E-5 | IPython 可用性 | `.venv` 未安装 IPython ⇒ 冒烟测试 `importorskip`；结构判据权威 |
| E-6 | 离线门禁 | G26 静态扫描 + G28 `unshare --net` 断网任务；新用例无需加入排除清单 |
| E-7 | 既有断言 | `tests/contracts/test_graph.py` / `test_api_snapshot.py` / `vars(compiled)` 不应变红 |
| E-8 | README / G19 | `Graph` 行需更新；G19 需追加 B23F1 白名单（只放行 `Graph`） |

---

## §5 与 spec 的三表一致性

| 检查 | 结果 |
|---|---|
| 上游对照表（P）与偏离登记（X）逐条对应 | ✅ |
| 差分场景组（D）覆盖所有 X / STRICTER / DIFF | ✅（D-04 / D-07 / D-08 / D-09 / D-10） |
| 无「未登记的分叉」 | ✅ |
| 换版本重核义务 | 表头已写明（1.6.3 / 1.7.6） |
| 行为断言有实测支撑 | ✅（E-1…E-8） |
