# Quickstart · B23F1 `draw_mermaid_png()`：离线不阻断

**Feature**: `specs/b23f1-draw-mermaid-png-offline/` · **Date**: 2026-11-20
**目的**: 用**可运行**的场景验证 PNG 导出 / 合法字节 / 离线 / 零出站；
不含实现细节，细节见 [contracts/png-contract.md](./contracts/png-contract.md)。

---

## §0 前置

```bash
cd /home/ctyun/workspace/github/freegraph
.venv/bin/python --version          # 期望 Python 3.11.x
.venv/bin/python -m pytest -q       # 基线：1700 passed, 4 skipped
```

> ⚠️ 必须用 `.venv`：系统 `python3`（3.12）未安装 `freegraph`，环境性失败
> 不代表代码红。

---

## §1 最小验收（P1 / P2）

```python
from typing import TypedDict

from freegraph.graph import END, START, StateGraph

class State(TypedDict, total=False):
    v: int

def a(state):   return {"v": 1}
def b(state):   return {"v": 2}
def route(s):   return "b"

g = StateGraph(State)
g.add_node("a", a)
g.add_node("b", b)
g.add_edge(START, "a")
g.add_conditional_edges("a", route, ["b", END])
g.add_edge("b", END)
app = g.compile()

graph = app.get_graph(xray=True)
data = graph.draw_mermaid_png()
print(type(data), len(data))
print(data[:8])
```

**期望**

- `type(data) is bytes`；`len(data) > 0`；
- `data[:8] == b"\x89PNG\r\n\x1a\n"`；
- 不抛异常；无需任何网络。

---

## §2 PNG 结构合法性（独立于 IPython / PIL）

**直接跑契约测试**（推荐）：

```bash
.venv/bin/python -m pytest -q tests/contracts/test_graph_png.py
```

**期望**：全部通过；测试会逐块校验签名 / `IHDR` / 每块 CRC / `IDAT` 解压 /
`IEND` / 无尾随字节 / 64×64 / 3 色 / 确定性。

**手工快速检查**（只读，不修改仓库）：

```python
import struct, zlib

data = app.get_graph().draw_mermaid_png()
assert data[:8] == b"\x89PNG\r\n\x1a\n"
pos = 8
while pos < len(data):
    n = struct.unpack(">I", data[pos:pos+4])[0]
    typ = data[pos+4:pos+8]
    body = data[pos+8:pos+8+n]
    crc = struct.unpack(">I", data[pos+8+n:pos+12+n])[0]
    assert (zlib.crc32(typ + body) & 0xFFFFFFFF) == crc
    print(typ.decode(), n)
    pos += 12 + n
assert pos == len(data)
```

**期望**：依次打印 `IHDR 13` / `IDAT ...` / `IEND 0`；末尾 `pos == len(data)`。

---

## §3 离线 / 零出站（P3）

### 3.1 socket 夹具（本地）

```bash
.venv/bin/python -m pytest -q tests/runtime/test_graph_offline.py
```

**期望**：全部通过；「框架出站 = 0」。

### 3.2 断网任务（Linux，推荐）

```bash
unshare --net --map-root-user .venv/bin/python harness/verification/B23F1/acceptance.py
```

**期望**：`B23F1 acceptance: PASS`（退出码 0）。

> 若本机不支持非特权用户命名空间，改跑 CI 的 **G28** 作业；判据相同：
> 无网络接口 + 框架出站 = 0 + PNG 成功。

### 3.3 静态 / 依赖 / 零出站门禁

```bash
uv run --no-project --python .venv python harness/scripts/gates/gate_G21_dependencies.py
uv run --no-project --python .venv python harness/scripts/gates/gate_G23_licenses.py
uv run --no-project --python .venv python harness/scripts/gates/gate_G26_network_static.py
uv run --no-project --python .venv python harness/scripts/gates/gate_G27_zero_egress.py
```

**期望**：全部通过；`src/freegraph/**` 无网络客户端 import；G27 的 observe-only 归因下
「框架出站 = 0」；依赖闭包 / 许可证门禁仍绿。

---

## §4 占位图外观（可选目视）

```python
import struct, zlib

data = app.get_graph().draw_mermaid_png()
# 取 IDAT 并解压（v1 用单个 IDAT + filter 0）
pos, idat = 8, b""
while pos < len(data):
    n = struct.unpack(">I", data[pos:pos+4])[0]
    typ = data[pos+4:pos+8]
    if typ == b"IDAT":
        idat += data[pos+8:pos+8+n]
    pos += 12 + n
raw = zlib.decompress(idat)
colors = set()
for y in range(64):
    row = raw[y*(1+64*3):(y+1)*(1+64*3)]
    for x in range(64):
        colors.add(tuple(row[1+x*3:4+x*3]))
print(sorted(colors))
```

**期望**：3 种颜色：

```text
[(51, 102, 153), (217, 232, 255), (245, 245, 245)]
```

画面 = 3 个方框 + 2 条连线的固定示意图标；**不**反映真实节点 / 边。

> 若本地装了 IPython，可 `from IPython.display import Image; Image(data)` 目视；
> 未装 IPython 不影响验收（结构判据是权威）。

---

## §5 一键验收 / 差分 / 固定脚本等价

```bash
.venv/bin/python harness/verification/B23F1/acceptance.py
.venv/bin/python -m pytest -q tests/runtime/test_graph_png_acceptance.py
.venv/bin/python -m pytest -q tests/differential/test_parity_probe.py -k png
.venv/bin/python harness/demo/visualization.py
```

**期望**

- `B23F1 acceptance: PASS`（退出码 0）；
- PNG 差分场景 D-01…D-10 符合各自判词（上游缺席 / 网络缺席即 skip）；
- `visualization.py` 退出码 **0**（V4 / V6 的 PNG 判据从「跳过」转为真跑）。

> `harness/demo/target.py` 是**只读基准**：本 feature MUST NOT 改动其任何一行；
> 它自带的 `langchain` 导入属脚本自身依赖。固定脚本的 fake / 真实模型双跑归
> **B25F1**（本 feature 只闭环 `draw_mermaid_png()` 环节）。

---

## §6 结果判据（A1–A4）

| # | 判据 | 快速验证 |
|---|---|---|
| A1 | 离线不抛阻断性异常 | §3.1 / §3.2 成功 |
| A2 | 返回合法 PNG 字节 | §2 结构判据全过 |
| A3 | 方法名同名 | `hasattr(app.get_graph(), "draw_mermaid_png")` |
| A4 | 零出站 | §3.1 socket 夹具 + §3.3 静态扫描 |

---

## §7 常见失败与定位

| 现象 | 可能原因 | 处理 |
|---|---|---|
| `AttributeError: draw_mermaid_png` | 方法未加到 `Graph` / 未重新安装 | 检查 `src/freegraph/contracts/graph.py`；`uv pip install -e .` |
| `Image()` 抛 `UnidentifiedImageError` | 字节不是合法 PNG | 跑 §2 结构判据，先修 `IHDR` / CRC / `IEND` |
| 断网任务红 | 新增用例建立了真实连接 | 本 feature 的用例 MUST NOT 联网；不要加入排除清单来「绕过」 |
| `G19` 红 | 改了 README `Graph` 行但未加 B23F1 白名单 | 追加 `MATRIX_ROWS_UPDATABLE_BY_B23F1 = {"Graph"}`；只放行该行 |
| `G30` 红 | 新文件缺署名头 | 按仓库既有文件加首行版权头 + 模块 docstring |
