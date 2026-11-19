<!-- authority: yes -->

# PNG 导出契约（png-contract.md）· B23F1

**Feature**: `specs/b23f1-draw-mermaid-png-offline/` · **Date**: 2026-11-20
**契约性质**: **冻结面 · 唯一权威** —— `Graph.draw_mermaid_png()` 的签名 / 调用流 /
占位图 / PNG 字节格式 / 失败信号 / 不变量
**上位权威**: [spec.md](../spec.md) · 本文件只把形状与判据**落细**，**不得**放宽 spec
**上游**: `langgraph 1.2.11` + `langchain-core 1.6.3`（行号取证）/
`langchain-core 1.7.6`（`.venv` 行为复核）· 详见 [upstream-parity.md](./upstream-parity.md)

> **机器标记**：`<!-- authority: yes -->`。下游 **B24F1 / B25F1 / v2.0 / B26**
> MUST 以本文件为 `draw_mermaid_png()` 的口径。

---

## 0. 作用域

覆盖：

1. `Graph.draw_mermaid_png(self) -> bytes` 的签名与调用面；
2. v1 固定示意图标的尺寸 / 调色板 / 几何；
3. PNG 字节格式（签名 / `IHDR` / `IDAT` / `IEND` / CRC / zlib / filter）；
4. 失败信号、确定性、只读 / 零网络 / 零环境变量 / 零文件副作用；
5. 测试的机械判据（独立于 IPython / PIL / golden 哈希）；
6. 下游接口（B24F1 / B25F1 / v2.0 / B26）。

**不覆盖**：真实图形渲染（方案 D）· `[png]` extra · PNG 文件落盘 ·
上游 `draw_method` / `output_file_path` 参数族 · 图结构导出 / mermaid 文本
（归 B22F1）· 子图 / 别名（C26 / B8F3）。

---

## 1. 方法入口（**签名冻结**）

```python
def draw_mermaid_png(self) -> bytes: ...
```

| # | 要求 |
|---|---|
| 1.1 | 方法挂在 `freegraph.contracts.graph.Graph` 上，与上游**同名** |
| 1.2 | **零参数**（除 `self`）；无 `*args` / `**kwargs` |
| 1.3 | 返回**内置 `bytes`**（不是 `str` / `bytearray` / memoryview） |
| 1.4 | 长度 MUST > 0 |
| 1.5 | 对任何 `Graph`（含空图 / 退化图 / 特殊字符节点名）MUST 成功 |
| 1.6 | MUST 在任何 `invoke()` / `stream()` **之前**可用 |
| 1.7 | `get_graph(xray=True)` 与 `get_graph(xray=False)` 的返回值均具备该方法 |
| 1.8 | MUST NOT 新增公开顶层符号 / 公开模块；`__all__` 不变 |
| 1.9 | MUST NOT 修改 `Graph` 的字段 / 构造签名 / 不可哈希 / 元组容器 |
| 1.10 | MUST NOT 修改 `draw_mermaid()` 的输出语义 |

---

## 2. 调用流（**唯一图源**）

```python
def draw_mermaid_png(self) -> bytes:
    self.draw_mermaid()              # 唯一图源；v1 丢弃返回值
    rows = _placeholder_rgb_rows()   # 固定 64×64×3；不读 self.nodes / self.edges
    return _encode_placeholder_png(rows)
```

| # | 要求 |
|---|---|
| 2.1 | MUST 先调用 `self.draw_mermaid()`；调用次数 ≥ 1 |
| 2.2 | MUST NOT 另写 mermaid 生成器 / 过滤边集合 / 重算条件边 |
| 2.3 | v1 **丢弃**文本；不把文本像素化；不因文本内容改变 PNG |
| 2.4 | MUST NOT 依赖 `invoke()` / `stream()` 的副作用 |
| 2.5 | `stream()` MUST NOT 调用 `draw_mermaid_png()` |
| 2.6 | 不修改 `Graph` 或其共享内部状态 |

---

## 3. 固定示意图标（v1）

### 3.1 画布

| 项 | 值 |
|---|---|
| 宽 × 高 | **64 × 64** |
| 颜色类型 | **2**（RGB truecolor） |
| 位深 | **8** |
| 压缩 / 过滤 / 交织 | `0` / `0` / `0` |
| 颜色数 | **≥3**（非单色；v1 参考调色板 = 3 色） |

### 3.2 调色板（固定）

| 名称 | RGB | 十六进制 |
|---|---|---|
| `BACKGROUND` | `(245, 245, 245)` | `#F5F5F5` |
| `BOX_FILL` | `(217, 232, 255)` | `#D9E8FF` |
| `INK` | `(51, 102, 153)` | `#336699` |

### 3.3 几何（闭区间像素坐标）

| 元素 | 坐标 | 画法 |
|---|---|---|
| 方框 1 | `(8,24)` – `(19,39)` | 1px `INK` 边框 + `BOX_FILL` 内部 |
| 方框 2 | `(26,24)` – `(37,39)` | 同上 |
| 方框 3 | `(44,24)` – `(55,39)` | 同上 |
| 连线 1 | `y=32` · `x=20..25` | 1px `INK` 水平线 |
| 连线 2 | `y=32` · `x=38..43` | 1px `INK` 水平线 |

其余像素 = `BACKGROUND`。

### 3.4 语义

- 图样**固定**，**不反映**真实 `Graph` 的节点 / 边 / 条件边 / 别名；
- 不同 `Graph` ⇒ **相同像素 / 相同字节**；
- 不承诺包含节点名 / 文本 / 图结构；
- 不含字体 / 外部图片 / 外部服务。

---

## 4. PNG 字节格式

### 4.1 总序列

```text
PNG_SIGNATURE
IHDR (length 13)
IDAT (zlib-compressed scanlines)
IEND (length 0)
```

- **无** `tEXt` / `gAMA` / `sRGB` / `pHYs` 等附属块；
- **无**尾随字节。

### 4.2 签名

```text
89 50 4E 47 0D 0A 1A 0A
```

### 4.3 `IHDR`（13 字节）

```text
width         = 64      (4 bytes · big-endian)
height        = 64      (4 bytes · big-endian)
bit_depth     = 8       (1 byte)
color_type    = 2       (1 byte · RGB)
compression   = 0       (1 byte)
filter        = 0       (1 byte)
interlace     = 0       (1 byte)
```

### 4.4 `IDAT`

- 每行：`0x00`（filter None）+ 64 × 3 字节 RGB；
- 行数：64；原始长度 = `64 * (1 + 64*3)` = **12,352**；
- `zlib.compress(raw, 9)`；
- 可拆成多个 `IDAT` 块，但 v1 实现为**单个** `IDAT`。

### 4.5 块信封与 CRC

```text
length (4 · big-endian) | type (4 · ASCII) | data | crc (4 · big-endian)
crc = zlib.crc32(type + data) & 0xFFFFFFFF
```

---

## 5. 失败信号与错误策略

| # | 场景 | 时机 | 信号 |
|---|---|---|---|
| 5.1 | 空图 / 退化图 / 特殊字符节点名 | 调用 | **成功返回** `bytes` |
| 5.2 | 无 `[png]` extra（v1.0 的唯一形态） | 调用 | **成功返回**；MUST NOT 尝试导入可选依赖 |
| 5.3 | 内部编码 bug / 未预期异常 | 调用 | **暴露**（MUST NOT catch-all / 静默兜底） |
| 5.4 | 调用方传参数 | 调用 | Python 自身 `TypeError`（v1 无参数） |
| 5.5 | 离线 / 无网络 | 调用 | **不抛阻断性异常**；MUST NOT 发起网络请求 |
| 5.6 | 未来 v2 的可选参数 | v2 | 另立契约；MUST NOT 追溯影响 v1 的零参调用 |

---

## 6. 确定性 / 只读 / 副作用

| # | 要求 |
|---|---|
| 6.1 | 同一 `Graph` 重复调用 ⇒ **逐字节相同** |
| 6.2 | 不同 `Graph` 之间 ⇒ **逐字节相同**（固定示意图标） |
| 6.3 | MUST NOT 依赖随机数 / 时间 / 进程 id / 环境变量 / 网络 / 外部文件 |
| 6.4 | MUST NOT 读环境变量 / 写文件 / 写临时文件 / 启动子进程 |
| 6.5 | MUST NOT 使用模块级可变缓存；并发 / 重入 MUST 成功 |
| 6.6 | 实现路径 MUST NOT 含网络客户端 import / 调用 |
| 6.7 | MUST NOT 访问 `mermaid.ink` 或任何外部域名 |

---

## 7. 测试判据（机械可验 · 独立于 IPython / PIL）

### 7.1 PNG 结构

| # | 判据 |
|---|---|
| 7.1.1 | 8 字节签名正确 |
| 7.1.2 | 首块为 `IHDR`，长度 13 |
| 7.1.3 | 宽 = 高 = 64；位深 8；颜色类型 2；压缩 / 过滤 / 交织 0 |
| 7.1.4 | 每块长度字段与实际数据长度一致；类型为 4 个 ASCII 字母 |
| 7.1.5 | 每块 CRC == `zlib.crc32(type + data) & 0xFFFFFFFF` |
| 7.1.6 | `IDAT` 存在；`zlib.decompress` 后长度 == 12,352 |
| 7.1.7 | 每行首字节 == 0；RGB 行长度 == 192 |
| 7.1.8 | 末块为 `IEND`，长度 0；其后无尾随字节 |
| 7.1.9 | 解码后颜色数 ≥3 且非单色（v1 参考调色板 = `{BACKGROUND, BOX_FILL, INK}`） |

### 7.2 行为

| # | 判据 |
|---|---|
| 7.2.1 | 返回类型精确为 `bytes`；长度 > 0 |
| 7.2.2 | 空图 / 退化图成功 |
| 7.2.3 | 同图 / 异图逐字节相同 |
| 7.2.4 | `draw_mermaid()` 调用次数 ≥ 1；返回值不影响 PNG |
| 7.2.5 | `draw_mermaid()` 输出在 PNG 调用前后逐字相同 |
| 7.2.6 | G27 / socket 夹具下「框架出站 = 0」（observe-only 归因） |
| 7.2.7 | `stream()` 前后 PNG 逐字节相同；`stream()` 不调用 PNG |
| 7.2.8 | IPython 可用时 `Image(data)` 构造不抛（**可选冒烟**） |
| 7.2.9 | **不**逐字节比对 golden 哈希（避免 zlib 版本差异误报） |

---

## 8. 不变量（I-01…I-12）

| # | 不变量 | 判据 |
|---|---|---|
| I-01 | 方法挂载 | `type(graph).__module__ == "freegraph.contracts.graph"` 且有 `draw_mermaid_png` |
| I-02 | 返回类型 | `type(data) is bytes`；`len(data) > 0` |
| I-03 | 全图成功 | 对任何 `Graph` 不抛 |
| I-04 | PNG 合法 | §7.1 全过 |
| I-05 | 固定图标 | 64×64 · RGB8 · 3 色 |
| I-06 | 确定性 | 同图 / 异图逐字节相同 |
| I-07 | 唯一文本源 | `draw_mermaid()` 调用 ≥ 1；文本未改 |
| I-08 | 零出站 | 无网络 import / 调用；框架出站 = 0 |
| I-09 | 零环境 | 不读环境变量 |
| I-10 | 零文件 | 不写文件 / 临时文件 |
| I-11 | 零共享状态 | 并发 / 重入成功；无模块级可变缓存 |
| I-12 | 公开面 | `__all__` 不变；`vars(compiled)` 仍 11 键 |

---

## 9. 下游接口

### 9.1 B24F1（打包 / 兼容矩阵）

- `pyproject.toml` MUST 仍无 `[project.optional-dependencies]`；
- 兼容矩阵 MUST 记录「v1.0 PNG = 合法占位图（非真实图形渲染）」与 v2.0 的 `[png]` 升级路径。

### 9.2 B25F1（双跑验收）

- 固定脚本的 fake / 真实模型轮 MUST 记录 `draw_mermaid_png()` 的
  字节数 / PNG 结构判据结果 / 框架出站计数；
- MUST NOT 用「符合预期」替代实测输出；真实轮受环境限制时登记**环境偏离**。

### 9.3 v2.0 / B26（真实渲染）

- 方案 D（`playwright` 本地 Chromium）与纯 Python 最小 SVG→PNG 渲染器 MUST 作为
  **可选 `[png]` extra**（默认关闭）落地；
- 运行期 MUST 零出站（`mermaid.ink` 仍在网络层黑名单）；
- MUST NOT 破坏本契约的**零参调用面**与 `bytes` 返回类别；
- v2 MUST 直接消费 `draw_mermaid()` 的文本（不得另写生成器）。
