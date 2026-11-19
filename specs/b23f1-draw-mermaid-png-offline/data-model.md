# Data Model · B23F1 `draw_mermaid_png()`：离线不阻断

**Feature**: `specs/b23f1-draw-mermaid-png-offline/` · **Date**: 2026-11-20
**权威口径**: [spec.md](./spec.md) · [contracts/png-contract.md](./contracts/png-contract.md)

> 本文件只描述**数据形状与不变量**；算法细节见 plan.md §「关键算法」与契约
> `png-contract.md`。本 feature **不新增**公开数据类 / 协议 / 错误类型 / 快照字段。

---

## §1 公开类型面（L1 · 字段不变）

### 1.1 `Graph`（`freegraph.contracts.graph.Graph`）

| 字段 / 成员 | 类型 | 缺省 | 语义 |
|---|---|---|---|
| `nodes` | `tuple[Node, ...]` | `()` | 节点表（**不变**） |
| `edges` | `tuple[Edge, ...]` | `()` | 边表（**不变**） |
| `draw_mermaid()` | `() -> str` | — | B22F1 已交付（**语义不变**） |
| **`draw_mermaid_png()`** | **`() -> bytes`** | — | **B23F1 追加**（T-1） |

- `frozen=True, slots=True, kw_only=True`；**不可哈希**；字段 / 构造签名**不变**。
- `draw_mermaid_png` **不读** `self.nodes` / `self.edges` 来绘制占位图；它只先调用
  `self.draw_mermaid()`（唯一图源，返回值在 v1 被丢弃）。
- 无参数、返回内置 `bytes`；对任何 `Graph` 不抛异常；无共享可变状态。

### 1.2 `Node` / `Edge`

- **零改动**：字段、缺省、冻结 / 不可哈希、`Edge.condition=None` 的既有语义全部不变。
- PNG 路径不新增 / 不修改任何 `Node` / `Edge` 实例。

---

## §2 固定示意图标（v1 的占位画面）

### 2.1 画布

| 项 | 值 |
|---|---|
| 宽 × 高 | **64 × 64**（像素） |
| 颜色类型 | **2**（RGB truecolor） |
| 位深 | **8** 位 / 通道 |
| 压缩 / 过滤 / 交织 | `0` / `0` / `0` |
| 颜色数 | **≥3**（非单色；v1 参考实现 = 3） |

### 2.2 调色板（固定常量）

| 名称 | RGB | 十六进制 | 用途 |
|---|---|---|---|
| `BACKGROUND` | `(245, 245, 245)` | `#F5F5F5` | 画布背景 |
| `BOX_FILL` | `(217, 232, 255)` | `#D9E8FF` | 方框内部 |
| `INK` | `(51, 102, 153)` | `#336699` | 方框边框 / 连线 |

### 2.3 几何（闭区间像素坐标）

| 元素 | 坐标 | 说明 |
|---|---|---|
| 方框 1 | `(8,24)` – `(19,39)` | 1px `INK` 边框 + `BOX_FILL` 内部 |
| 方框 2 | `(26,24)` – `(37,39)` | 同上 |
| 方框 3 | `(44,24)` – `(55,39)` | 同上 |
| 连线 1 | `y=32` · `x=20..25` | 1px `INK` 水平线 |
| 连线 2 | `y=32` · `x=38..43` | 1px `INK` 水平线 |

- 其余像素一律 `BACKGROUND`。
- 图样**固定**：不读取真实节点 / 边；不同 `Graph` ⇒ 相同像素 / 相同字节。
- **不**含文字 / 字体 / 外部图片 / 外部服务。

### 2.4 不变量

| # | 不变量 |
|---|---|
| P-01 | 解码后尺寸恒为 64×64 |
| P-02 | 颜色数 ≥3 且非单色；v1 参考调色板为 3 色（`len(distinct_colors) == 3`） |
| P-03 | 不同 `Graph` 的像素 / 字节**逐字节相等** |
| P-04 | 不因节点名 / 边类型 / 空图 / 特殊字符而改变像素 |
| P-05 | 不写文件、不读环境变量、不发起网络 |

---

## §3 PNG 字节结构

### 3.1 总体

```text
PNG_SIGNATURE
IHDR chunk (length 13)
IDAT chunk (zlib-compressed scanlines)
IEND chunk (length 0)
```

- **无** `tEXt` / `gAMA` / `sRGB` / `pHYs` 等附属块。
- 无尾随字节。

### 3.2 签名

```text
89 50 4E 47 0D 0A 1A 0A
```

### 3.3 `IHDR`（13 字节）

| 字段 | 值 | 说明 |
|---|---|---|
| width | 64 | 大端 4 字节 |
| height | 64 | 大端 4 字节 |
| bit depth | 8 | 1 字节 |
| color type | 2 | RGB |
| compression | 0 | deflate |
| filter | 0 | 标准过滤 |
| interlace | 0 | 非交错 |

### 3.4 `IDAT`

- 每行：`0x00`（filter None）+ 64 × 3 字节 RGB；
- 行数：64；原始长度 = `64 * (1 + 64*3)` = **12,352**；
- `zlib.compress(raw, 9)`。

### 3.5 块信封与 CRC

```text
length (4 · 大端) | type (4 · ASCII) | data | crc (4 · 大端)
crc = zlib.crc32(type + data) & 0xFFFFFFFF
```

| 块 | length | data |
|---|---|---|
| `IHDR` | 13 | 见 §3.3 |
| `IDAT` | ≥ 1 | 见 §3.4 |
| `IEND` | 0 | 空 |

---

## §4 调用流与状态

```text
Graph.draw_mermaid_png(self) -> bytes
    │
    ├─ self.draw_mermaid()          # 唯一图源；v1 丢弃返回值
    │
    ├─ _placeholder_rgb_rows()      # 64×64×3 固定像素；不读 self.nodes / self.edges
    │
    └─ _encode_placeholder_png()    # 签名 + IHDR + IDAT + IEND
```

| 规则 | 说明 |
|---|---|
| 唯一图源 | `self.draw_mermaid()` MUST 被调用；MUST NOT 另写生成器 |
| 无分支 | v1 不根据 mermaid 文本 / 图结构改变输出 |
| 无参数 | 无「非法参数」失败面 |
| 无共享状态 | 每次调用重新编码；无模块级可变缓存 / 临时文件 |
| 失败信号 | 对任何 `Graph` 成功；内部未预期 bug 暴露（无 catch-all） |

---

## §5 离线证据实体

| 实体 | 语义 | 判据 |
|---|---|---|
| **静态扫描（G26）** | `src/freegraph/**` 无网络客户端 import | 命中数 == 0 |
| **socket 夹具** | 只观测、不阻断、按调用栈归因 | 「框架出站 = 0」 |
| **G28 断网任务** | Linux 网络命名空间跑全量测试 | 通过率 == 100% |
| **排除清单** | `tests/gates/data/offline_exclusions.txt` | 本 feature **零新增**（不建立真实连接） |
| **人工证据** | `harness/verification/B23F1/manual-verification.md` | 五段式 + A1–A4 |

---

## §6 与上游的数据面映射

| 项 | 上游（`langchain-core`） | freegraph | 关系 |
|---|---|---|---|
| 方法挂载 | `Graph.draw_mermaid_png` | `Graph.draw_mermaid_png` | SAME |
| 返回类别 | `bytes` | `bytes` | SAME |
| 输入文本 | 先 `self.draw_mermaid(...)` | 先 `self.draw_mermaid()` | SAME |
| 参数族 | 关键字参数（含 `draw_method` / `output_file_path`） | **零参数** | DIFF（X-01 / X-02） |
| 渲染 | 公网 API 或本地 pyppeteer | **固定占位图**（标准库） | DIFF（X-03） |
| 离线 | 抛 `ValueError` | **成功返回合法 PNG** | STRICTER（X-05） |
| 确定性 | 不承诺 | **逐字节相同** | STRICTER（X-04） |
| 类型来源 | `langchain_core.runnables.graph` | `freegraph.contracts.graph` | DIFF（P-12） |

---

## §7 不变量汇总

| # | 不变量 |
|---|---|
| I-01 | `Graph` 字段 / 构造 / 不可哈希 / `__all__` 不变 |
| I-02 | `draw_mermaid_png` 返回内置 `bytes`，长度 > 0 |
| I-03 | 对任何 `Graph` 成功（空图 / 退化图 / 特殊字符） |
| I-04 | PNG 结构合法（签名 + `IHDR` + 块 CRC + `IDAT` + `IEND` + 无尾随） |
| I-05 | 64×64 · RGB8 · 3 色 · 非单色 |
| I-06 | 同图 / 异图逐字节相同 |
| I-07 | `draw_mermaid()` 被调用且未被改写 |
| I-08 | 无网络 / 无环境变量 / 无文件写入 / 无子进程 |
| I-09 | 无共享可变状态；并发 / 重入成功 |
| I-10 | `stream()` 不调用 PNG 导出；PNG 不依赖 `stream()` 副作用 |
| I-11 | 公开符号面 / `vars(compiled)` 键数不变 |
| I-12 | `target.py` 逐字未改 |
