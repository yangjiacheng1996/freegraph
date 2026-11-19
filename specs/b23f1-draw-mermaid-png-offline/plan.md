# Implementation Plan: B23F1 · `draw_mermaid_png()`：离线不阻断 ★

**Branch**: `b23f1-draw-mermaid-png-offline`（**未创建分支** —— 本仓库无
`.specify/extensions.yml` ⇒ 无 `before_plan` 钩子；既有 feature 同样在 `main` 上开发）
| **Date**: 2026-11-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/b23f1-draw-mermaid-png-offline/spec.md`

**feature ID**: `B23F1`（M2 图定义与对外 API · **第 21 个** · 前置：**B22F1**（主）
+ B1F1 / B2F1 / B2F2 / B6F1 / B7F1 / B7F2 / B7F3 / B8F1 / B8F2 / B9F1（承接 H-1…H-8）
· 下游：**B25F1**（D-1）· **B24F1**（D-3）· **v2.0 / B26**（D-2））

---

## Summary

交付 **`Graph.draw_mermaid_png()`**（C15）：在**离线**环境返回**合法 PNG 字节**，
**永不因网络不可达而阻断固定脚本**。

1. 在 L1 `src/freegraph/contracts/graph.py` **仅追加** `Graph.draw_mermaid_png(self) -> bytes`；
2. v1 只交付**占位 PNG（方案 C）**：标准库 `zlib` + `struct` 自研最小 PNG 编码器；
   画面 = **固定示意图标**（64×64 · 3 个方框 + 2 条连线 · 3 色 · 不反映真实节点 / 边）；
3. `draw_mermaid()` 仍是**唯一图源**（调用一次；v1 不把文本像素化）；
4. **零网络代码 / 零环境变量 / 零第三方依赖 / 零文件副作用 / 零共享可变状态**；
5. 同一 `Graph` 与不同 `Graph` 均返回**逐字节相同**的 PNG（确定性）；
6. 真实图形渲染（方案 D · `playwright` / 纯 Python 渲染器）归 **v2.0 / B26**。

| 交付物 | 语义 | 关键规则 |
|---|---|---|
| **`Graph.draw_mermaid_png()`** | PNG 字节导出（C15） | 零参数 · 返回 `bytes` · 离线不阻断 · 确定性 |
| **占位 PNG 编码器** | 标准库最小 PNG | 签名 + `IHDR` + `IDAT` + `IEND` · 每块 CRC 自洽 |
| **固定示意图标** | v1 的占位画面 | 64×64 · 3 个方框 + 2 条连线 · ≥3 色 · 所有图相同 |
| **PNG 结构判据** | 独立于 IPython / PIL | 块长度 / 类型 / CRC / IDAT 解压 / IEND / 无尾随 |
| **离线证据** | 零出站的可判定形式 | 静态扫描（G26）+ G27 observe-only + socket 夹具 + G28 断网任务 |
| **差分场景组** | 与上游同场景对跑 | D-01…D-10 · 上游缺席 / 网络缺席即 skip |
| **一键验收** | `harness/verification/B23F1/acceptance.py` | 退出码 0/1/2 · pytest 真跑 |

**技术方案（关键落点）**：

| 环节 | 落点 |
|---|---|
| PNG 方法 | L1 `src/freegraph/contracts/graph.py` 的 `Graph.draw_mermaid_png`（**追加**） |
| PNG 编码器 | 同模块私有 `_png_chunk` / `_placeholder_rgb_rows` / `_encode_placeholder_png` |
| 唯一图源 | 先调用 `self.draw_mermaid()`；v1 丢弃文本，但 MUST NOT 另写生成器 |
| 占位画面 | 64×64 RGB8；3 个方框 + 2 条连线；固定调色板（见契约 §2） |
| 契约 | `contracts/png-contract.md`（冻结面） + `contracts/upstream-parity.md` |
| 差分 | `tests/differential/parity_probe.py` 新增 `_run_png_scenarios` + D-01…D-10 |
| 文档 | `README.md` 的 `Graph` 矩阵行 + B23F1 零增量注记；G19 白名单追加 `Graph` |
| 验收 | `harness/verification/B23F1/acceptance.py` + `manual-verification.md` |

**零新增**：运行时依赖 · 公开顶层符号 · 错误类型 · 文件写入 · 环境变量读取 · 门禁编号。
**破冻结面 1 类**（T-1）：`Graph` **仅追加**方法；字段 / 构造 / 不可哈希 / `__all__` 不变。

---

## Technical Context

**Language/Version**: Python **≥ 3.11**（`requires-python = ">=3.11"`）。
PNG 编码只用标准库 `zlib` / `struct`；测试解码只用标准库 `zlib` / `struct` / `binascii`。
**MUST NOT** 使用 3.12+ 专有 typing 构件。

**Primary Dependencies**: **运行时零第三方依赖**（`dependencies = []`）。
开发期：`pytest`（`.venv` · 9.2.0）· 差分：`langgraph==1.2.11`（既有 `differential` 组）。
`pyproject.toml` **零改动** ⇒ G3 / G21 / G22 / G23 恒绿；**无** `[png]` extra。

**上游取证版本（重要）**：
- 行号锚点取自系统 site-packages：`langgraph 1.2.11` + `langchain-core 1.6.3`
  （与本 spec 的 P 表一致）；
- `.venv` 的 `differential` 组解析为 `langgraph 1.2.11` + `langchain-core 1.7.6`
  ⇒ **行为已在本环境重新实测**（离线同抛 `ValueError`）；行号差异登记于
  `research.md` §0.2；**差分判据只断言行为 / 结构，不断言行号**。

**Storage**: N/A（不落盘 · 不写临时文件 · 不读 checkpointer）。

**Testing**:
- `tests/contracts/test_graph_png.py`（**新建**：PNG 结构 / 占位图 / 确定性 / IPython 冒烟）
- `tests/contracts/test_graph.py`（既有字段 / 相等 / mermaid 断言**不改**；可追加 PNG 交叉断言）
- `tests/runtime/test_graph_offline.py`（**扩展**：`draw_mermaid_png` 零出站 / 静态扫描 / 环境变量）
- `tests/runtime/test_graph_png_offline.py`（**新建**：`stream()` 隔离 / 并发 / 无临时文件）
- `tests/runtime/test_graph_png_acceptance.py`（**新建**：一键验收真跑）
- `tests/runtime/test_graph_png_manual_record_guard.py`（**新建**：人工验证记录守卫）
- `tests/facade/test_get_graph.py`（**扩展**：任何运行之前可用 / `xray=True` 同款）
- `tests/facade/test_facade_gates.py`（**扩展**：`MATRIX_ROWS_UPDATABLE_BY_B23F1 = {"Graph"}`）
- `tests/differential/parity_probe.py`（**扩展**：`_run_png_scenarios` + D-01…D-10）
- `tests/differential/test_parity_probe.py`（**扩展**：`test_png_parity_scenarios_meet_their_verdicts`）

**Target Platform**: Linux / macOS / Windows · CPython 3.11+ · **零出站**。

**Project Type**: library（发行名 = 导入名 = `freegraph`）。

**Performance Goals**: **N/A（不设墙钟预算）**。编码固定 64×64 = 12,352 字节原始扫描行，
单次 `zlib.compress`；无 I/O / 无网络。MUST NOT 用耗时做断言。

**Constraints**（主要来自 spec 的 MUST 条目）：

| 约束 | spec 条目 |
|---|---|
| 同名方法 · 零必需参数 · 返回 `bytes` | FR-001 / FR-002 / FR-020 · SC-005 |
| 离线不抛阻断性异常 | FR-003 · SC-001 |
| 合法 PNG（签名 / `IHDR` / CRC / `IDAT` / `IEND` / 无尾随） | FR-004 · SC-002 / SC-012 |
| 可被 `IPython.display.Image` 接受；判据独立于 IPython | FR-005 · SC-006 |
| 标准库 only；零第三方依赖 | FR-006 / FR-009 · SC-004 · G3 / G21 / G23 |
| 实现路径无网络代码；零环境变量 | FR-007 / FR-008 · SC-003 / SC-010 · G4 / G26 / G27 / G28 |
| 固定示意图标（64×64 · 3 方框 + 2 连线 · ≥3 色 · 非单色） | FR-010 · SC-016 |
| 对任何 `Graph` 成功；无 catch-all | FR-011 · SC-008 |
| `draw_mermaid()` 唯一图源；不另写生成器 | FR-012 / FR-013 · SC-013 / SC-014 |
| 同图 / 异图逐字节相同 | FR-014 · SC-007 |
| 仅追加方法；公开面零变化 | FR-015 · SC-015 · T-1 |
| 任何运行之前可用 | FR-016 · SC-009 |
| 离线等价性证据 | FR-017 · SC-001 / SC-003 |
| `target.py` 零改动 + 人工记录 | FR-018 · SC-009 |
| 并发 / 重入成功；无共享可变状态 | FR-019 · SC-011 |
| 新文件署名头 + docstring 首语句 | 宪法原则 X · G30 |
| 人工验证五段式 | 宪法原则 V |

---

## 绿基线记录 + 变红清单（宪法 v1.11.0 的基线义务）

### 基线（**2026-11-20 · 实施前**）

> 必须使用 **`.venv`**（Python 3.11.16 · pytest 9.2.0 · packaging 26.3）。
> 系统 `python3`（3.12）未安装 `freegraph`，不得作为基线。

| 项 | 计数 |
|---|---|
| passed | **1700** |
| skipped | **4** |
| failed | **0** |
| 耗时 | **113.76s** |

```
1700 passed, 4 skipped in 113.76s (0:01:53)
```

4 条 skip = 既有环境 / 可选工具 / Windows 专属路径；**0 failed**。

### 变红清单（**预登记** · 实测后 MUST 逐条核对）

| # | 断言位置 | 变红原因 | 处置（拆分而不删 / 只补注记） |
|---|---|---|---|
| R-01 | `README.md` 的 `Graph` 矩阵行 | B23F1 追加 `draw_mermaid_png()` | 更新「差异说明」列；**等价程度（部分等价）不变**；同步加 `MATRIX_ROWS_UPDATABLE_BY_B23F1 = {"Graph"}`（G19 白名单**只放行这一行**） |
| R-02 | `tests/runtime/test_conditional_edge_surface.py` 模块 docstring | 原文写「`draw_mermaid_png()` 尚未存在」 | 只改注记为「B23F1 已交付」；**不改任何断言** |
| R-03 | `tests/contracts/test_graph.py` | 追加 PNG 测试类 | 既有字段 / 冻结 / 不可哈希 / 相等 / `draw_mermaid` 断言**逐字保留**；新增断言为**追加** |
| R-04 | `tests/runtime/test_graph_offline.py` | 追加 `draw_mermaid_png` 零出站断言 | 既有 `draw_mermaid` / `get_graph` 断言保留；新增为追加 |
| R-05 | `tests/facade/test_get_graph.py` | 追加 PNG 门面断言 | 既有 `get_graph` 断言保留；新增为追加 |
| R-06 | `tests/facade/test_api_snapshot.py` | **不应变红**（门面快照只含 `freegraph.graph` 符号） | 若变红 ⇒ 检查是否误加顶层符号；MUST NOT 用 `--update-api-snapshot` 掩盖 |
| R-07 | `tests/facade/test_facade_gates.py` 的 G19 | README `Graph` 行更新 | 追加 B23F1 白名单；等价程度**不得变差**；其余 18 行**逐字未改** |
| R-08 | `tests/facade/test_compiled_graph.py` / `tests/runtime/test_conditional_edge_surface.py` | `vars(compiled)` / 公开符号面 | **不应变红**；`Graph` 方法不是 `compiled` 字段、不是顶层符号 |
| R-09 | `harness/verification/B23F1/manual-verification.md` | 新建人工记录 | 五段式 + A1–A4 + `B23F1 acceptance: PASS` + T-1 授权来源 |
| R-10 | `harness/demo/visualization.py` | B23F1 后 V4 / V6 从「跳过」转「真跑」 | 期望退出码 **0**；若失败先修 PNG，**不得**改脚本 |
| R-11 | `harness/demo/README.md` | 仍写「`draw_mermaid_png` 未交付」 | 只更新 PNG 相关状态为「B23F1 已交付」；**不越界**改其他 feature 的状态 |

**MUST NOT 变红**（不破面）：
- `target.py`（只读基准）· G1 / G2 / G3 / G4 / G5 / G21 / G22 / G23 / G26 / G27 / G28 / G29 / G30
- G7 公开符号面（`freegraph.graph.__all__` 仍 **8**；契约层仍 **22**；`runtime` 仍 **23**）
- `vars(compiled)` 仍 **11** 键
- `pyproject.toml`（零改动 · 无 `[project.optional-dependencies]`）
- `tests/contracts/test_graph.py` 的字段 / 冻结 / 不可哈希 / 相等断言
- `tests/facade/test_api_snapshot.py` 的入库快照
- `tests/runtime/test_graph_export.py` / `tests/facade/test_get_graph.py` 的既有图导出断言

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 宪法条款 | 门禁化落点 | 状态 |
|---|---|---|
| 原则 I（零 LangSmith / 零出站 / 零环境变量） | FR-007 / FR-008 / FR-013 · G4 / G26 / G27 / G28 | ✅ |
| 原则 II（零 LangChain · 状态语义等价） | 零新增依赖 · G3 / G21 / G22 / G23 · P-01…P-14 / D-01…D-10 | ✅ |
| 原则 III（验收契约优先 · `target.py` 只读） | `target.py` **零改动**；`visualization.py` V4 / V6 真跑；`target.py` diff 断言常驻 | ✅ |
| 原则 IV（可诊断性 · 可视化不阻断） | PNG 离线永不因网络阻断；`draw_mermaid()` 仍纯本地 | ✅ |
| 原则 V（人工验收） | 五段式 `harness/verification/B23F1/manual-verification.md` + 零出站证据 | ✅ |
| 原则 VI（规格驱动 · 判据级覆盖） | FR-001…FR-020 / SC-001…SC-016 ↔ 测试 / 验收 / 差分 | ✅ |
| 原则 VII（职责边界 · C15） | v1 占位 PNG；真实渲染归 v2 / B26；`mermaid.ink` 永久排除 | ✅ |
| 原则 VIII（证据与术语） | `research.md` E-1…E-8 实测 + `contracts/upstream-parity.md` P/X/D 三表一致 | ✅ |
| 原则 IX（许可证 / 商标） | 零新增依赖 ⇒ `THIRD_PARTY_NOTICES` 零变更；PNG 为自有编码 | ✅ |
| 原则 X（署名头 / 文档） | G30 · README 兼容矩阵 + B23F1 零增量注记 | ✅ |
| 原则 XI（上游优先） | 方法挂载 / 返回类别 / 文本前置照抄；偏离 X-01…X-05 如实登记 | ✅ |
| 原则 XII（最优设计 / 零重复载体） | 复用 `draw_mermaid()`；不另写生成器；不引入第二份图模型 | ✅ |
| 立项书 §5.1 **ARCH-1**（L3 → L1 单向；L1 契约层只依赖标准库） | `contracts/graph.py` 只 import `struct` / `zlib`（标准库）；零内部 import | ✅ |
| 立项书 §5.1 **ARCH-3**（跨层只经 Protocol + 纯数据类） | `draw_mermaid_png` 是 `Graph` 的**纯函数式**方法；无新协议 / 无新数据类 | ✅ |
| 运行时基线（3.11 · typing 上限） | Technical Context 逐项 ≤ 3.11 · G9 | ✅ |
| 依赖白名单 / 黑名单 | 零新增运行时依赖；`mermaid.ink` 不在实现路径 | ✅ |

**破冻结面登记**（授权来源：B22F1 契约 §8 + 本 feature 提示词 · 承接方 B23F1）：

| # | 冻结面 | 处置 |
|---|---|---|
| T-1 | B2F1 `Graph` 类型面（2 字段 · 不可哈希；B22F1 已追加 `draw_mermaid`） | **仅追加** `draw_mermaid_png() -> bytes`；字段 / 构造 / 不可哈希 / `__all__` / `draw_mermaid` 语义全部不变 |

> **不新增公开顶层符号**：`draw_mermaid_png` 是 `Graph` 的实例方法；
> 私有 PNG 助手不进 `__all__`；`freegraph.__all__` / `freegraph.graph.__all__` /
> `freegraph.contracts.__all__` / `freegraph.contracts.graph.__all__` 均不变。

---

## Project Structure

### Documentation (this feature)

```text
specs/b23f1-draw-mermaid-png-offline/
├── plan.md                       # 本文件
├── research.md                   # Phase 0 · 决策 + 实测证据
├── data-model.md                 # Phase 1 · 数据形状
├── quickstart.md                 # Phase 1 · 验证指南
├── contracts/
│   ├── png-contract.md           # PNG 方法 / 字节格式 / 占位图的冻结口径
│   └── upstream-parity.md        # P / X / D 三表 + 实测
├── checklists/
│   └── requirements.md           # clarify 后的质量检查表
└── tasks.md                      # Phase 2（/speckit.tasks）
```

### Source Code (repository root)

```text
src/freegraph/
├── contracts/
│   ├── graph.py                  # L1：Graph.draw_mermaid_png + 私有 PNG 助手（**唯一源码改动**）
│   └── __init__.py               # 不改导出面
├── graph.py                      # L2 门面：不改签名 / 不新增符号
└── _stategraph.py                # L3：不改（get_graph 已返回 Graph）

tests/
├── contracts/
│   ├── test_graph_png.py         # 新建：PNG 结构 / 占位图 / 确定性 / IPython 冒烟
│   └── test_graph.py             # 既有断言不改；可追加交叉断言
├── runtime/
│   ├── test_graph_offline.py     # 扩展：draw_mermaid_png 零出站 / 静态扫描 / 环境变量
│   ├── test_graph_png_offline.py # 新建：stream 隔离 / 并发 / 无临时文件
│   ├── test_graph_png_acceptance.py       # 新建：一键验收真跑
│   ├── test_graph_png_manual_record_guard.py  # 新建：人工记录守卫
│   └── test_conditional_edge_surface.py   # R-02：只改 docstring 注记
├── facade/
│   ├── test_get_graph.py         # 扩展：任何运行之前可用 / xray 同款
│   └── test_facade_gates.py      # R-07：G19 白名单追加 Graph
└── differential/
    ├── parity_probe.py           # 扩展：_run_png_scenarios + D-01…D-10
    └── test_parity_probe.py      # 扩展：PNG 差分入口

harness/verification/B23F1/
├── acceptance.py                 # 新建：一键验收（A1–A4）
└── manual-verification.md        # 新建：五段式 + T-1 授权来源 + 零出站证据

README.md                         # R-01：Graph 矩阵行 + B23F1 零增量注记
harness/demo/README.md            # R-11：PNG 交付状态更新（只改 PNG 相关）
```

**Structure Decision**: 单项目（`src/freegraph` + `tests`）。
`draw_mermaid_png` **必须**与 `Graph` 同模块（L1 `contracts/graph.py`）——否则 L1 反向
import L3（ARCH-1 违规）；PNG 编码器是**同模块私有助手**，不进公开面。
`_stategraph.py` / `graph.py` / `contracts/__init__.py` **零改动**。

---

## Phase 0：Outline & Research

**输出**：[research.md](./research.md)

要解决的设计点（**全部已有唯一裁定**，无 `NEEDS CLARIFICATION`）：

1. 占位图的精确形状：64×64 · 3 个方框 + 2 条连线 · 3 色调色板 · 不反映真实图。
2. PNG 字节格式：签名 / `IHDR` / `IDAT` / `IEND`；无附属块；CRC；filter 0；zlib。
3. 零网络路径：无网络 import / 调用；不以「捕获网络异常」实现离线。
4. 唯一图源：先调用 `self.draw_mermaid()`；v1 丢弃文本；不另写生成器。
5. 失败信号：v1 零参数；对任何 `Graph` 成功；内部 bug 暴露（无 catch-all）。
6. 确定性：同图 / 异图均逐字节相同；不依赖随机数 / 时间 / 环境 / 文件。
7. 放置位置：L1 `contracts/graph.py`；私有助手；零公开符号。
8. 验证策略：结构判据（非 golden 哈希）+ IPython 可选冒烟 + G28 断网任务。
9. 差分策略：freegraph-only 场景 + 上游离线模拟；网络依赖断言 skip。
10. 文档 / 门禁：README `Graph` 行 + G19 白名单 + `visualization.py` V4 / V6。
11. 上游版本差异：系统 1.6.3 行号 vs `.venv` 1.7.6 行为；只断言行为。
12. T-1 的回溯修订与基线变红清单。

---

## Phase 1：Design & Contracts

**输出**：[data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

### 数据形状（摘要）

- `Graph(nodes, edges)` 字段不变；**仅追加**无状态方法 `draw_mermaid_png() -> bytes`。
- 占位图 = **固定常量**：64×64 RGB8；调色板 / 方框 / 连线坐标见契约 §2。
- PNG 字节 = 签名 + `IHDR`（13 字节）+ `IDAT`（zlib）+ `IEND`（0 字节）；
  **无** `tEXt` / `gAMA` / `sRGB` 等附属块。
- 无新的公开数据类 / 协议 / 错误类型；无编译期快照改动。

### 接口契约

- [contracts/png-contract.md](./contracts/png-contract.md)：
  `draw_mermaid_png` 的**唯一权威**口径（签名、调用流、占位图、字节格式、
  失败信号、不变量、测试判据、下游接口）。
- [contracts/upstream-parity.md](./contracts/upstream-parity.md)：
  P-01…P-14 / X-01…X-05 / D-01…D-10 + 实测 E-1…E-8。

### 验证指南

- [quickstart.md](./quickstart.md)：最小 PNG / 结构判据 / 断网 / 差分 / 一键验收 /
  `visualization.py` 的可运行步骤与预期输出。

---

## 关键算法（设计级伪代码）

```text
draw_mermaid_png(self) -> bytes:
    # 1) 唯一图源（FR-012）：先取 mermaid 文本；v1 不把它像素化
    self.draw_mermaid()                 # 文本被丢弃；MUST NOT 另写生成器
    # 2) 固定占位图（不读取 self.nodes / self.edges）
    rows = _placeholder_rgb_rows()      # 64×64×3 字节；filter 0 逐行
    # 3) 最小 PNG 编码（标准库）
    return _encode_placeholder_png(rows)
```

```text
_placeholder_rgb_rows() -> bytes:
    canvas = 64×64 全部填 BACKGROUND
    for (x0, y0, x1, y1) in BOXES:       # 3 个方框
        fill interior BOX_FILL; draw 1px border INK
    for (x0, x1, y) in CONNECTORS:       # 2 条连线
        draw 1px horizontal line INK
    return bytes(filter_byte + RGB row for each row)   # filter = 0

_encode_placeholder_png(rows) -> bytes:
    raw = b"".join(b"\x00" + row for row in rows)
    ihdr = struct.pack(">IIBBBBB", 64, 64, 8, 2, 0, 0, 0)
    idat = zlib.compress(raw, 9)
    return PNG_SIGNATURE + chunk("IHDR", ihdr) + chunk("IDAT", idat) + chunk("IEND", b"")

chunk(type, data):
    body = type + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
```

```text
# 判据（tests/contracts/test_graph_png.py）
parse chunks:
    assert signature == 89 50 4E 47 0D 0A 1A 0A
    assert first chunk == IHDR and len == 13
    assert width == height == 64; bit_depth == 8; color_type == 2
    assert compression == filter == interlace == 0
    for chunk: assert len(data) matches; assert type is 4 ASCII; assert CRC matches
    assert IDAT exists; raw = zlib.decompress(idat); len(raw) == 64 * (1 + 64*3)
    for row: assert raw[y*(1+64*3)] == 0
    assert last chunk == IEND and len == 0 and no trailing bytes
    colors = set(RGB tuples); assert len(colors) >= 3 and len(colors) != 1
```

---

## Complexity Tracking

> **仅登记破冻结面与已裁定偏离**；无其它复杂度豁免。

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| `Graph.draw_mermaid_png` 追加（T-1） | 固定脚本调用 `get_graph(...).draw_mermaid_png()`；C15 要求方法同名 | 模块级函数 `draw_mermaid_png(graph)` ⇒ 固定脚本必须改（违反只读基准） |
| v1 只交付占位图（X-03） | 宪法 v1.7.0：v1.0 无 extra、零依赖；真实渲染归 v2 | 引入 `playwright` / `pillow` ⇒ 破零依赖 / 许可证红线 |
| 固定示意图标而非真实拓扑（X-03） | v1 的交付面是「合法 PNG + 离线不阻断」，不是「真实图渲染」 | 读取真实节点 / 边画拓扑 ⇒ 提前拉入 v2 的真实渲染，工作量与边界失控 |
| 无参数（X-01 / X-02） | v1 占位图无样式 / 网络 / 文件语义；避免误导性 `draw_method=API` | 照搬上游参数族 ⇒ 暴露网络入口 / 文件写入，与零出站冲突 |

---

## Re-check（Phase 1 后）

| 检查 | 结论 |
|---|---|
| 分层：L1 `contracts/graph.py` 只 import 标准库；零内部 import | ✅ |
| 零出站：无 `socket` / `http` / `urllib` / `requests` / 子进程；`mermaid.ink` 不出现 | ✅ |
| 公开面：`__all__` 不变；G7 仍 **8**；契约层仍 **22**；`runtime` 仍 **23** | ✅ |
| 冻结面：T-1 有 FR + 授权来源 + 变红清单 | ✅ |
| 判据级覆盖：FR-001…FR-020 ↔ SC-001…SC-016 ↔ D-01…D-10 | ✅ |
| 上游证据：P/X/D 三表一致；E-1…E-8 实测（含 1.6.3 / 1.7.6） | ✅ |
| 人工门禁：五段式记录 + `B23F1 acceptance: PASS` | ✅ |
| 断网门禁：新用例**无需**加入 `offline_exclusions.txt`（不建立真实连接） | ✅ |

---

## 后续（Phase 2 · `/speckit.tasks`）

任务 MUST 至少覆盖：

1. T-1 的回溯修订（`Graph` 方法 + README 矩阵 + G19 白名单 + R-02 注记）。
2. 私有 PNG 编码器 + `draw_mermaid_png`（64×64 / 3 方框 + 2 连线 / CRC / zlib / filter 0）。
3. 契约测试（结构 / 调色板 / 确定性 / `draw_mermaid` 唯一图源 / IPython 冒烟）。
4. 离线测试（socket 夹具 / 静态扫描 / 环境变量 / `stream()` 隔离 / 并发 / 无临时文件）。
5. 门面测试（任何运行之前可用 / `xray=True` 同款）+ 差分场景 D-01…D-10。
6. 一键验收 + 人工验证记录 + `visualization.py` V4 / V6 + `harness/demo/README.md` PNG 状态。
7. 变红清单逐条核对；基线重跑（`.venv/bin/python -m pytest -q tests/`）；
   G21 / G22 / G23 / G26 / G27 / G28 / G29 / G30 全跑并记录退出码。
