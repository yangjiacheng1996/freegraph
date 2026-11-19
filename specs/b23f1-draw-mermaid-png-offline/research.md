# Research · B23F1 `draw_mermaid_png()`：离线不阻断

**Feature**: `specs/b23f1-draw-mermaid-png-offline/` · **Date**: 2026-11-20
**上游版本**: 行号锚点 = `langgraph 1.2.11` + `langchain-core 1.6.3`
（系统 site-packages · 非仓库依赖）；行为复核 = `.venv` 的
`langgraph 1.2.11` + `langchain-core 1.7.6`
**运行环境**: `.venv` · CPython **3.11.16** · pytest 9.2.0 · packaging 26.3

> 纪律：宪法原则 XI「上游有答案 ⇒ 照抄」；**行为断言 MUST 有实测支撑**。
> 本节只记录**已取证**的决定；没有 `NEEDS CLARIFICATION`。

---

## §0.1 取证环境与锚点复核

**环境**：`.venv` · CPython **3.11.16** · `pytest 9.2.0` · `packaging 26.3`；
上游差分组 = `langgraph==1.2.11`（既有 `differential` 组）。

**系统 Python（行号取证）**：`langchain-core 1.6.3`
（用户 site-packages · 非仓库依赖）。

| 用途 | 1.6.3 路径:行号 | 1.7.6（`.venv`）路径:行号 |
|---|---|---|
| `Graph.draw_mermaid_png` | `langchain_core/runnables/graph.py:632` | `.../graph.py:635` |
| `Graph.draw_mermaid` | `.../graph.py:577` | `.../graph.py:580` |
| 模块级 `draw_mermaid_png` | `langchain_core/runnables/graph_mermaid.py:277` | `.../graph_mermaid.py:317` |
| 模块级 `draw_mermaid` | `.../graph_mermaid.py:45` | `.../graph_mermaid.py:86` |
| `_render_mermaid_using_api` | `.../graph_mermaid.py:405` | `.../graph_mermaid.py:445` |
| 默认 `mermaid.ink` | `.../graph_mermaid.py:422-423` | `.../graph_mermaid.py:462-463` |
| `requests.get` / 失败路径 | `.../graph_mermaid.py:461` / `:484-503` | `.../graph_mermaid.py:501` / `:524-543` |
| 先取 `self.draw_mermaid(...)` | `.../graph.py:689-695` | `.../graph.py:692-698` |
| `get_graph` | `langgraph/pregel/main.py:845` | `langgraph/pregel/main.py:845`（同版） |
| `get_graph().draw_mermaid_png()` | `.../pregel/main.py:919` | `.../pregel/main.py:919`（同版） |

> **版本纪律**：spec 的 P 表行号以 **1.6.3** 为准；`.venv` 的差分组解析为 **1.7.6**
> ⇒ 行号有偏移，但**离线失败行为已重新实测同款**（E-1）。
> 差分测试只断言**行为 / 结构 / 返回类别**，**不断言行号**；换版本后 MUST 重新核实行号。

---

## §0.2 无 `NEEDS CLARIFICATION`

所有设计点在 spec 的 `Clarifications`（Q1–Q10 + clarify 轮）中已拍板：
零参数签名、固定示意图标、64×64、≥3 色、结构判据、无 catch-all、v1 只做方案 C。
本文件不引入新的开放问题。

---

## §1 决策清单（Decision / Rationale / Alternatives）

### D-01 · 方法签名：零参数、返回 `bytes`

- **Decision**：`def draw_mermaid_png(self) -> bytes`；不暴露上游的
  `draw_method` / `output_file_path` / `base_url` / `proxies` / `curve_style` 等参数。
- **Rationale**：v1 占位图没有真实渲染参数；暴露 `draw_method=API` 会与零出站冲突；
  固定脚本只做无参调用；B22F1 的 `draw_mermaid()` 已是零参口径。
- **Alternatives**：逐项镜像上游参数（v1 接受但忽略）⇒ 误导性 API；
  仅接受 `output_file_path` ⇒ 引入文件副作用。**均拒绝**。
- **锚点**：上游 `graph.py:632`（1.6.3）/ `:635`（1.7.6）；spec Q1 / X-01 / X-02。

### D-02 · 占位图：固定示意图标（64×64 · 3 方框 + 2 连线）

- **Decision**：
  - 画布 **64×64**、RGB8（PNG color type 2）、非交错；
  - 调色板 3 色：`BACKGROUND=(245,245,245)` · `BOX_FILL=(217,232,255)` ·
    `INK=(51,102,153)`；
  - 3 个 1px 方框（含边框）：`(8,24)-(19,39)` / `(26,24)-(37,39)` / `(44,24)-(55,39)`；
  - 2 条 1px 水平连线：`y=32` · `x=20..25` 与 `x=38..43`；
  - **不读取** `self.nodes` / `self.edges`；所有 `Graph` 返回相同字节；
  - 不使用字体 / 文本 / 外部图片 / 外部服务。
- **Rationale**：满足「人眼可见的极简图形」与「≥3 色 · 非单色」的结构判据；
  固定图标不承诺真实拓扑；64×64 在 notebook 中可见；zlib 后仅 **173 字节**（E-3）。
- **Alternatives**：1×1 单色（不可见）· 真实拓扑（提前进入 v2）· 纯色块（不像图）**均拒绝**。
- **证据**：E-3；spec Q2 / Q7 / FR-010 / SC-016。

### D-03 · PNG 字节格式：最小块结构 + CRC + filter 0

- **Decision**：
  - 8 字节签名 `89 50 4E 47 0D 0A 1A 0A`；
  - `IHDR`（13 字节）：宽 64 · 高 64 · 位深 8 · 颜色类型 2 · 压缩 0 · 过滤 0 · 交织 0；
  - `IDAT`：每行 `0x00`（filter None）+ 64×3 RGB 字节；共 64 行；原始长度 **12,352**；
    `zlib.compress(raw, 9)`；
  - `IEND`：长度 0；
  - **无** `tEXt` / `gAMA` / `sRGB` / `pHYs` 等附属块；
  - 每块 CRC = `zlib.crc32(type + data) & 0xFFFFFFFF`，大端写入。
- **Rationale**：标准库即可；结构判据可机械校验；无附属块 ⇒ 字节最小、无文本 / 时间 /
  平台元数据；确定性最强。
- **Alternatives**：RGBA（多一通道、无必要）· 灰度（难以用 3 色表达）·
  加 `tEXt` 标识（非必需）· 逐行不同 filter（增加实现与测试复杂度）**均不采用**。
- **证据**：E-3；spec Q3 / FR-004 / FR-010。

### D-04 · 零网络路径：无网络代码，不以 catch 兜底

- **Decision**：实现路径不 import / 调用 `socket` / `http` / `urllib.request` /
  `requests` / `httpx` / `aiohttp` / 子进程；不访问 `mermaid.ink`；不读环境变量。
- **Rationale**：宪法原则 I 明文点名 `mermaid.ink`；「先请求、失败后返回占位」仍然发出了
  出站请求，**不算合规**；固定脚本必须在第 163 行之前不中断。
- **Alternatives**：捕获上游 `ValueError` 后返回占位 ⇒ 请求已发出；设置代理 / 超时
  ⇒ 仍是网络代码。**均拒绝**。
- **证据**：E-1 / E-6；spec Q4 / X-05 / FR-007 / FR-008 / SC-003。

### D-05 · 唯一图源：先调用 `self.draw_mermaid()`

- **Decision**：`draw_mermaid_png()` MUST 先调用 `self.draw_mermaid()`；v1 **丢弃**返回值，
  不把文本像素化；MUST NOT 另写 mermaid 生成器 / 过滤边集合。
- **Rationale**：B22F1 契约 §8 规定 `draw_mermaid()` 是 PNG 的唯一文本前置；v2 真实渲染
  将直接消费该文本；v1 保留该调用以保证接口单一入口。
- **Alternatives**：v1 直接跳过文本（更省一次字符串拼接）⇒ 破坏 B22F1 D-1 / H-1；
  另写一套生成器 ⇒ 双份口径。**均拒绝**。
- **证据**：spec Q5 / FR-012 / SC-013；B22F1 契约 §5 / §8。

### D-06 · 确定性：同图 / 异图逐字节相同

- **Decision**：同一 `Graph` 重复调用、以及不同 `Graph` 之间，均返回**逐字节相同**的 PNG。
- **Rationale**：固定示意图标不读取图结构；确定性使测试可判定、排除随机 / 时间 / 环境。
- **Alternatives**：按图规模改变图标 ⇒ 需读取图结构，接近真实渲染；随机 / 时间戳 ⇒ 不可复现。
- **证据**：E-3（两次编码逐字节相同）；spec Q7 / FR-014 / SC-007。

### D-07 · 失败信号：零参数；对任何 `Graph` 成功；内部 bug 暴露

- **Decision**：v1 无参数 ⇒ 无「非法参数」失败面；空图 / 退化图 / 特殊字符节点名 MUST 成功；
  **不写 catch-all**；未预期的内部实现 bug MUST 暴露。
- **Rationale**：spec 的硬约束是「离线不抛阻断性异常」；本地编码器对有限输入应当 total；
  catch-all 会把 bug 静默成假占位图。
- **Alternatives**：兜底返回 1×1 PNG + warning ⇒ 掩盖缺陷；静默兜底 ⇒ 更差。
- **证据**：spec Q6 / FR-011；用户 2026-11-20 决策。

### D-08 · 放置位置：L1 `contracts/graph.py` + 私有助手

- **Decision**：方法追加在 `freegraph.contracts.graph.Graph`；编码器为模块级私有函数 /
  私有常量（`_png_chunk` / `_placeholder_rgb_rows` / `_encode_placeholder_png`），
  **不进 `__all__`**；不新建公开模块。
- **Rationale**：`Graph` 是 L1 类型；方法必须同模块，否则 L1 反向 import L3（ARCH-1）。
  只用标准库 ⇒ 不违反契约层「只依赖标准库」。
- **Alternatives**：放 L3 `_stategraph.py` ⇒ `Graph` 方法需 monkey-patch / 反向依赖；
  新建公开 `freegraph.png` 模块 ⇒ 新增公开面。**均拒绝**。
- **证据**：`tests/contracts/test_architecture.py` 的 G2 白名单（标准库）；
  spec Q8 / FR-015 / SC-015。

### D-09 · 验证策略：结构判据 + IPython 可选冒烟

- **Decision**：权威判据 = 自行解析 PNG 的签名 / 块 / CRC / `IDAT` / `IEND` / 颜色；
  IPython 冒烟仅在可用时跑（`pytest.importorskip("IPython")`）；**不**用 golden 哈希。
- **Rationale**：spec 要求判据独立于 IPython / PIL；zlib 输出可能随版本变化，
  golden 哈希会误报；结构判据 + 两次调用确定性足以证明「合法且稳定」。
- **Alternatives**：只靠 IPython 不报错 ⇒ 不能证明结构；golden 哈希 ⇒ zlib 版本脆弱。
- **证据**：E-5（`.venv` 未装 IPython ⇒ 冒烟 skip）；spec Q3 / SC-002 / SC-016。

### D-10 · 离线证据：G26 + G27 + socket 夹具 + G28

- **Decision**：四层证据：
  ① `src/freegraph/**` 静态扫描无网络客户端（**G26**）；
  ② **G27** 的 observe-only 零出站归因（只观测、不阻断、按调用栈归因）；
  ③ pytest 的 socket 夹具「框架出站 = 0」（只观测、不阻断、按调用栈归因）；
  ④ Linux CI 的 **G28** 断网任务（`unshare --net --map-root-user`）跑全量测试套件。
- **Rationale**：宪法原则 I / V；G27 / G28 是既有门禁；新用例不建立真实连接 ⇒ **无需**
  加入 `tests/gates/data/offline_exclusions.txt`。
- **Alternatives**：只在普通 CI 跑（无断网证明）；把用例加入排除清单（会削弱证据）。
- **证据**：E-6；spec FR-017 / SC-001 / SC-003。

### D-11 · 差分策略：freegraph-only + 上游离线模拟

- **Decision**：
  - D-01…D-03 / D-05…D-10 只断言 freegraph 的方法存在 / 返回类别 / PNG 结构 / 确定性 /
    零出站 / 类型来源，不依赖网络；
  - **D-04（上游离线失败）** 通过 monkeypatch `requests.get` 抛
    `ConnectionError` 来模拟离线；断言上游 `ValueError` 与 freegraph 成功；
  - 上游「有网络时返回 `bytes`」的对照为**可选**：网络不可用时 `pytest.skip`，
    不判失败；
  - **不断言** PNG 像素 / 字节与上游相等；**不断言**行号。
- **Rationale**：G28 断网任务会跑全量测试套件；若差分硬依赖真实网络，会在断网下假红。
  上游离线行为可无网络模拟，且与 E-1 实测一致。
- **Alternatives**：让上游差分联网跑 ⇒ G28 断网任务失败 / 需加入排除清单；
  只做 freegraph 内部测试 ⇒ 缺少上游对照。
- **证据**：E-1 / E-6；spec D-01…D-10。

### D-12 · 文档与门禁：README 矩阵 + G19 白名单

- **Decision**：
  - 更新 `README.md` 的 `Graph` 矩阵行，补「B23F1 起提供 `draw_mermaid_png()`（v1 占位 PNG，
    零出站）」；等价程度仍「部分等价」；
  - 追加 `tests/facade/test_facade_gates.py` 的
    `MATRIX_ROWS_UPDATABLE_BY_B23F1 = frozenset({"Graph"})`，并纳入 G19 的 `changed` 过滤；
  - 追加 README 的「B23F1 公开面增量 == 0 行」注记；
  - 更新 `tests/runtime/test_conditional_edge_surface.py` 的模块 docstring 注记
    （「`draw_mermaid_png()` 尚未存在」→「B23F1 已交付」），不改断言。
- **Rationale**：原则 X 要求兼容矩阵随 feature 更新；G19 的「既有行逐字未改」需要
  **只放行 Graph 行**；`draw_mermaid_png` 不是顶层符号 ⇒ 快照与符号面不变。
- **Alternatives**：不更新 README ⇒ 矩阵过期；更新但不加白名单 ⇒ G19 红；
  改快照 ⇒ 掩盖公开面变化。
- **证据**：E-7 / E-8；spec FR-015 / SC-015。

---

## §2 实测证据（E-1…E-8）

### E-1 · 上游离线失败信号（1.6.3 与 1.7.6 同款）

**系统 Python（langchain-core 1.6.3）**：monkeypatch `requests.get` 抛
`requests.exceptions.ConnectionError("offline-simulated")`，调用
`Graph().draw_mermaid_png(max_retries=0, retry_delay=0.0)`：

```text
UPSTREAM_OFFLINE_EXC ValueError Failed to reach https://mermaid.ink API while trying to render your graph after 0 retries. To resolve this issue:
```

**`.venv`（langchain-core 1.7.6）**：同一模拟：

```text
VENV_UPSTREAM_OFFLINE_EXC ValueError Failed to reach https://mermaid.ink API while trying to render your graph after 0 retries. To resolve this issue:
```

⇒ 上游离线**必抛** `ValueError`；freegraph 的目标是**成功返回合法 PNG**（STRICTER）。

### E-2 · 上游方法挂载与签名

- `langchain_core/runnables/graph.py:632`（1.6.3）/ `:635`（1.7.6）：
  `Graph.draw_mermaid_png`，仅关键字参数族，返回 `bytes`；
- `graph.py:689-695`（1.6.3）/ `:692-698`（1.7.6）：先 `self.draw_mermaid(...)`，再把文本交给渲染器；
- `langgraph/pregel/main.py:845`（`get_graph`）/ `:919`（`self.get_graph().draw_mermaid_png()`）。

⇒ freegraph 照抄「挂在 `Graph` 上 / 返回 `bytes` / 先取 mermaid 文本」；
参数族与文件输出登记为 **DIFF**（X-01 / X-02）。

### E-3 · 占位 PNG 原型实测（标准库）

原型（不入库）在 64×64 RGB8 上画 3 个方框 + 2 条连线，使用上述 3 色调色板；
`zlib.compress(raw, 9)`：

```text
len 173
magic True
chunks [('IHDR', 13, True), ('IDAT', 116, True), ('IEND', 0, True)]
decompressed 12352 expected 12352
distinct colors 3 [(51, 102, 153), (217, 232, 255), (245, 245, 245)]
deterministic True
```

⇒ 合法 PNG、块 CRC 全绿、IDAT 解压长度 = `64 * (1 + 64*3) = 12352`、3 色、逐字节确定。
（**不**把哈希写进测试；避免 zlib 版本差异误报。）

### E-4 · 实施前基线

```text
$ .venv/bin/python -m pytest -q
1700 passed, 4 skipped in 113.76s (0:01:53)
```

4 条 skip = 既有环境 / 可选工具 / Windows 专属路径；**0 failed**。

### E-5 · IPython 可用性

`.venv` **未安装 IPython**：

```text
ModuleNotFoundError: No module named 'IPython'
```

⇒ IPython 冒烟测试 MUST `pytest.importorskip("IPython")`；权威判据仍是 PNG 结构。

### E-6 · 离线门禁基础设施（既有）

- **G26**：`harness/scripts/gates/gate_G26_network_static.py` 扫描
  `src/freegraph/**` 的网络客户端 import；当前例外名单为空。
- **G27**：`harness/scripts/gates/gate_G27_zero_egress.py` 的 observe-only 零出站归因
  （只观测、不阻断、按调用栈归因）；它是 SC-003 / FR-017 的**权威证据之一**。
- **G28**：`.github/workflows/ci.yml` 在 Linux 用
  `unshare --net --map-root-user` 跑全量 `tests/`；排除清单 =
  `tests/gates/data/offline_exclusions.txt`（仅两类：断网任务自身 / 语义上必须建立连接）。
- 本 feature 的新用例**不建立真实连接**（socket 夹具只观测；上游离线用 monkeypatch 模拟）
  ⇒ **无需**加入排除清单。

### E-7 · 既有 Graph / 公开面断言

- `tests/contracts/test_graph.py`：字段清单 / 冻结 / 不可哈希 / 字段级相等 /
  `draw_mermaid` 语义；新增方法不应使这些断言变红。
- `tests/facade/test_api_snapshot.py`：快照只含 `freegraph.graph` 的公开名；
  `Graph` 方法不是顶层符号 ⇒ **不应变红**，MUST NOT 更新快照。
- `tests/facade/test_compiled_graph.py` / `tests/runtime/test_conditional_edge_surface.py`：
  `vars(compiled)` 仍 11 键；`draw_mermaid_png` 是 `Graph` 侧能力，不进入 `compiled` 字段。

### E-8 · README / G19 现状

`README.md` 的 `Graph` 行当前写「**B22F1 起**提供 `draw_mermaid()`」；
`tests/facade/test_facade_gates.py` 的 G19 白名单目前只允许
`MATRIX_ROWS_UPDATABLE_BY_B22F1 = {"Command", "Graph"}`。
⇒ B23F1 更新 `Graph` 行时必须追加
`MATRIX_ROWS_UPDATABLE_BY_B23F1 = frozenset({"Graph"})` 并纳入 `changed` 过滤；
**只放行 Graph 行**，等价程度不得变差。

---

## §3 三表一致性

| 检查 | 结果 |
|---|---|
| 上游对照表（P）与偏离登记（X）逐条对应 | ✅（X-01↔P-06；X-02↔P-07；X-03↔P-04/P-05/P-10；X-04↔P-11；X-05↔P-04/P-09） |
| 差分场景组（D）覆盖 STRICTER / DIFF | ✅（D-04 / D-07 / D-08 / D-09 / D-10） |
| 无「未登记的分叉」 | ✅ |
| 换版本重核义务 | §0.1 已写明 |
| 行为断言有实测支撑 | ✅（E-1…E-8） |
