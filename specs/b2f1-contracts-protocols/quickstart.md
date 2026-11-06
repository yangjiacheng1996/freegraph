# 验收指南（quickstart.md）

**功能块**: B2F1 · 5 个协议 + 5 个纯数据类
**Branch**: `b2f1-contracts-protocols` · **Date**: 2026-11-06

> 本文件是**可运行的验证指南**：照着做一遍，就能确认本 feature 交付到位。
> 设计意图：每条命令都可直接复制执行，每条都有**期望输出**可比对。
> 冻结面见 [contracts/public-api.md](./contracts/public-api.md)；
> 类型与不变式见 [data-model.md](./data-model.md)；
> 门禁定义见 [contracts/architecture-gates.md](./contracts/architecture-gates.md)。

---

## 0. 前置

| 项 | 要求 |
|---|---|
| Python | ≥ 3.11（`pyproject.toml` 的 `requires-python`） |
| 开发期工具 | `pytest`（**不进发行包**）；`mypy`（**可选**——缺失时 SC-004 的静态类型检查用例 `skip`，见 §1.1 注） |
| 网络 | **仅第 2 节（隔离环境验收）需要一次网络** —— `pip install .` 须拉取构建后端 `hatchling`；**第 1 节（单测）与第 3 节（冒烟）完全本地离线** |
| 命令名 | 下文用 `python3`；venv 内统一用 `/tmp/fg-verify/bin/python` |

---

## 1. 跑单元测试（开发期，免安装）

`tests/contracts/conftest.py` 会把 `src/` 注入 `sys.path`（源码优先），故**无需先 `pip install`**：

```bash
cd <repo-root>
python3 -m pytest tests/contracts -q
```

**期望输出**：

```text
.................................................                       [100%]
XX passed, Y skipped in 0.8s
```

> 断言条数以实现为准（`XX` 是设计预期值）；关键是 **全部 passed、0 failed、0 error**。
> `Y skipped` 的口径见 §1.1 注。

**分文件跑**（便于定位）：

```bash
python3 -m pytest tests/contracts/test_protocols.py   -q  # 5 个协议：方法集 / 纯抽象 / 结构化子类型判定
python3 -m pytest tests/contracts/test_graph.py       -q  # Graph / Node / Edge：字段 / 冻结 / 不可哈希 / 相等
python3 -m pytest tests/contracts/test_span.py        -q  # Span / TraceQuery：字段 / 生命周期 / JSON 可序列化
python3 -m pytest tests/contracts/test_architecture.py -q  # 十三条架构门禁（G1–G13）
python3 -m pytest tests/contracts/test_types.py       -q  # B1F1 的四类型（回归，确认未被改动）
python3 -m pytest tests/contracts/test_errors.py      -q  # B1F1 的异常体系（回归）
```

### 1.1 两个 `skip` 的口径（**是设计如此，不是失败**）

| 用例 | 何时 skip | 为什么 |
|---|---|---|
| **G3 依赖闭包** | 本机 freegraph **未安装**（无 dist-info 元数据） | 该门禁 MUST 在**已安装**的隔离环境里真跑（§2.2）——口径同 B1F1 |
| **SC-004 静态类型检查（mypy）** | 本机**未安装 mypy** | mypy 是**开发期工具**（不进发行包）；缺失时该用例 `skip` 而非失败，**人工验证记录须标注** |

> 兜底：**注解结构断言**（`typing.get_type_hints` 解析协议与夹具的方法名 / 参数名）
> **不依赖 mypy**，任何环境都跑——它挡不住全部类型错误，但能挡住「签名写错」这类最常见的
> 失守。**SC-004 的「静态类型检查」仍以 mypy 为准**（见 `research.md` D-19）。

---

## 2. 隔离环境验收（SC-002 / SC-003 / SC-017 / SC-020）

### 2.1 建环境并安装

```bash
python3 -m venv /tmp/fg-verify
/tmp/fg-verify/bin/pip install .
/tmp/fg-verify/bin/pip list
```

**期望输出**：

```text
Package    Version
---------- -------
freegraph  0.0.3
```

> **只有 freegraph 自己** —— 基础安装**零第三方运行时依赖**（SC-002）。
> 若看到 `typing-extensions` / 任何第三方包 ⇒ 依赖红线破了。

### 2.2 G3 · 依赖闭包：基础安装**为空集**

```bash
/tmp/fg-verify/bin/python - <<'PY'
from importlib.metadata import requires
import importlib.metadata as md

def closure(dist):
    seen, out = set(), []
    stack = [dist]
    while stack:
        d = stack.pop()
        if d.lower() in seen:
            continue
        seen.add(d.lower())
        try:
            reqs = md.requires(d) or []
        except Exception:
            continue
        out.extend(reqs)
        for r in reqs:
            name = r.split(";")[0].split("[")[0].split("=")[0].split(">")[0].split("<")[0].strip()
            if name:
                stack.append(name)
    return sorted({r for r in out})

print("基础安装闭包:", closure("freegraph"))
assert closure("freegraph") == [], "基础安装闭包必须为空集"
print("OK: 基础安装依赖闭包为空（零第三方运行时依赖）")
PY
```

**期望输出**：

```text
基础安装闭包: []
OK: 基础安装依赖闭包为空（零第三方运行时依赖）
```

### 2.3 导入成功且耗时在预算内（SC-002）

```bash
/tmp/fg-verify/bin/python -c "import freegraph.contracts; print('import OK')"
time /tmp/fg-verify/bin/python -c "import freegraph.contracts"
```

**期望输出**：

```text
import OK
```

> 墙钟 **< 300 ms**（含解释器冷启动）——阈值沿用 B1F1（B1F1 实测 154 ms / CPython 3.12.3）；
> 本 feature 新增 3 个模块后仍须在预算内。

### 2.4 G1 · 顶层包惰性 + 契约层零内部层

```bash
/tmp/fg-verify/bin/python - <<'PY'
import subprocess, sys
for mod in ("freegraph", "freegraph.contracts"):
    code = f"import {mod}, sys; print(sorted(m for m in sys.modules if m.startswith('freegraph')))"
    print(f"--- import {mod} ---")
    print(subprocess.run([sys.executable, "-c", code], capture_output=True, text=True).stdout.strip())
PY
```

**期望输出**：

```text
--- import freegraph ---
['freegraph']
--- import freegraph.contracts ---
['freegraph', 'freegraph.contracts', 'freegraph.contracts.errors', 'freegraph.contracts.graph',
 'freegraph.contracts.protocols', 'freegraph.contracts.trace', 'freegraph.contracts.types']
```

> `import freegraph` 后清单**恰为** `['freegraph']`；
> 导入契约层后**不含任何内部层模块**（契约层自身的子模块不受限）。

### 2.5 G2 / G5 / G8 / G10 / G12 · 静态门禁

```bash
cd <repo-root>
python3 - <<'PY'
import ast, pathlib, re

src = pathlib.Path("src/freegraph/contracts")
tests = pathlib.Path("tests/contracts")
fixtures = tests / "fixtures"
BANNED = ("langchain", "langgraph", "langsmith", "pydantic", "typing_extensions")
SIG = "# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph"

def is_internal(mod: str) -> bool:
    """指向 freegraph 顶层或包外 freegraph.* ⇒ 违规；freegraph.contracts 内部合法。"""
    if mod.split(".")[0] != "freegraph":
        return False
    return not (mod == "freegraph.contracts" or mod.startswith("freegraph.contracts."))

def imports_of(f):
    tree = ast.parse(f.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield node.lineno, a.name, 0
        elif isinstance(node, ast.ImportFrom):
            yield node.lineno, (node.module or ""), node.level

# G2 · 零内部 import（扫 src/contracts + tests/contracts）/ 零第三方 import（扫 src/contracts + 夹具目录）
internal, third = [], []
for f in sorted(src.rglob("*.py")) + sorted(tests.rglob("*.py")):
    for lineno, mod, level in imports_of(f):
        if level >= 2:
            internal.append(f"{f}:{lineno}: 包外相对 import（level={level}）")
        elif level == 1:
            continue                      # 包内相对 import ⇒ 合法
        elif is_internal(mod):
            internal.append(f"{f}:{lineno}: {mod}")
for f in sorted(src.rglob("*.py")) + sorted(fixtures.rglob("*.py")):
    for lineno, mod, level in imports_of(f):
        if mod.split(".")[0] in BANNED:
            third.append(f"{f}:{lineno}: {mod}")
print("内部 import:", internal)
print("第三方 import:", third)
assert not internal and not third, "G2 违规"
print("OK: 契约层零内部 / 零第三方 import")

# G5 · 署名头
for f in sorted(src.rglob("*.py")) + sorted(fixtures.rglob("*.py")):
    assert f.read_text(encoding="utf-8").splitlines()[0] == SIG, f"缺署名头: {f}"
print("OK: 署名头齐备")

# G10 · 协议纯抽象（方法体只有 ...）
for f in sorted(src.rglob("protocols.py")):
    tree = ast.parse(f.read_text(encoding="utf-8"))
    for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
        for fn in [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            body = [s for s in fn.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and s.value.value is Ellipsis)]
            if body:
                raise AssertionError(f"G10 违规: {cls.name}.{fn.name} 有非 ... 的方法体")
print("OK: 协议纯抽象")

# G12 · 公开符号面唯一权威（只认机器标记，不看字样）
authorities = [p for p in pathlib.Path(".").rglob("public-api.md")
               if "<!-- authority: yes -->" in p.read_text(encoding="utf-8")[:400]]
print("标记为权威的清单文件:", authorities)
assert len(authorities) == 1, "G12 违规：权威文件数 != 1"
assert authorities[0].as_posix().endswith(
    "specs/b2f1-contracts-protocols/contracts/public-api.md"), "G12 违规：权威文件不是 B2F1 的"
print("OK: 公开符号面唯一权威")

# G8 · 兼容矩阵逐符号覆盖（期望值从 public-api.md §0 解析，不硬编码）
# 判定与 contracts/architecture-gates.md G8 **同口径**：
#   ① 每个符号**恰有一行**  ② 该行含「对应上游符号 / 等价程度 / 差异说明」三列
#   ③ **行内上游来源行号**只对「有上游同名符号者」成立（既有 8 行按 FR-017 逐字不动）
#   ④ 取行范围 = 「## API 兼容矩阵」**章节内**（不扫全文）
#   ⑤ 矩阵**保持 4 列**（来源行号写进「差异说明」单元格末尾 ⇒ 不新增列）
api = pathlib.Path("specs/b2f1-contracts-protocols/contracts/public-api.md").read_text(encoding="utf-8")
block = api.split("from freegraph.contracts import (", 1)[1].split(")", 1)[0]
existing, new = [], []
bucket = existing
for ln in block.splitlines():
    s = ln.strip()
    if not s:
        continue
    if s.startswith("#"):                       # 分组注释行不是符号；「新增」标记切换分组
        if "新增" in s:
            bucket = new
        continue
    name = s.split(",")[0].split("#")[0].strip()
    if name:
        bucket.append(name)
symbols = existing + new
assert len(symbols) == 18, f"§0 解析出的符号数 != 18: {len(symbols)}"
matrix = pathlib.Path("README.md").read_text(encoding="utf-8")
# 取行范围 = 「## API 兼容矩阵」**章节内**（与门禁 G8 的 COMPAT_MATRIX_PATTERN 同口径）
# ——不扫全文，否则 README 其它章节里以 "| `X`" 开头的表格行会被误判为矩阵行
m = re.search(r"^## API 兼容矩阵\s*$", matrix, re.M)
assert m, "README.md 缺少「## API 兼容矩阵」章节"
section = matrix[m.start():]
nxt = re.search(r"^## ", section[len(m.group(0)):], re.M)
if nxt:
    section = section[: len(m.group(0)) + nxt.start()]
rows = [ln for ln in section.splitlines() if ln.startswith("| `")]
def row_of(sym):
    return [r for r in rows if r.split("|")[1].strip() == f"`{sym}`"]
missing = [x for x in symbols if not row_of(x)]
dup     = [x for x in symbols if len(row_of(x)) > 1]
present = [x for x in symbols if row_of(x)]                             # 已存在的行
bad_col = [x for x in present if len(row_of(x)[0].split("|")) - 2 < 4]   # 四列：符号/上游/等价程度/差异说明
NO_UPSTREAM = {"NodeFunc", "TraceSink", "Span", "TraceQuery"}         # 无上游同名符号 ⇒ 写「无上游对应」
bad_src = []
for x in present:
    if x not in new:                       # 既有 8 行按 FR-017 逐字不动 ⇒ 不要求行内来源行号
        continue
    r = row_of(x)[0]
    if x in NO_UPSTREAM:
        if "无上游对应" not in r:
            bad_src.append(x)
    elif not re.search(r"[\w/]+\.py:\d+", r):                           # 有上游同名符号 ⇒ 须有来源行号
        bad_src.append(x)
print("矩阵缺失的符号:", missing, "| 重复行:", dup, "| 列数不足:", bad_col, "| 来源不合规:", bad_src)
assert not (missing or dup or bad_col or bad_src), "G8 违规：兼容矩阵未按 §0 逐符号合规覆盖"
print("OK: 兼容矩阵逐符号覆盖", len(symbols), "个")
PY
```

**期望输出**：

```text
内部 import: []
第三方 import: []
OK: 契约层零内部 / 零第三方 import
OK: 署名头齐备
OK: 协议纯抽象
标记为权威的清单文件: [PosixPath('specs/b2f1-contracts-protocols/contracts/public-api.md')]
OK: 公开符号面唯一权威
矩阵缺失的符号: [] | 重复行: [] | 列数不足: [] | 来源不合规: []
OK: 兼容矩阵逐符号覆盖 18 个
```

> **注意**：G8 的「行内来源行号」只对**有上游同名符号**的**新增 10 行**成立——
> `NodeFunc` / `TraceSink` / `Span` / `TraceQuery` **无上游同名符号** ⇒ 该 4 行写
> 「无上游对应」+ 契约条目号（**MUST NOT** 硬凑行号）。**既有 8 行按 FR-017 逐字不动**，
> 其上游来源以矩阵章节的「证据来源」小节为准 —— 故本脚本**不**对既有 8 行断言行内行号。
> **矩阵保持 4 列**（来源行号写进该行的「差异说明」单元格末尾）⇒ 既有 8 行与新增 10 行的列数一致；
> 本脚本**取行范围 = 「## API 兼容矩阵」章节内**（不扫全文，与门禁 G8 同口径）。

> **正式门禁以 `tests/contracts/test_architecture.py` 的 AST 口径为准**——本节脚本是
> **便于人工快速核对的同口径简化版**（如「零出站」的文本粗筛在正式门禁里是 AST 口径）。
> **G4 / G6 / G9 / G11 / G13 的完整判定见该测试文件**。
> **G2 的两档范围**（B2F1 第二轮复核裁定）：「零内部 import」扫 `src/freegraph/contracts/**`
> + `tests/contracts/**`；「零第三方 import」扫 `src/freegraph/contracts/**` +
> `tests/contracts/fixtures/**`——**其余测试文件豁免**（`pytest` 是开发期工具，
> 一刀切会让门禁恒失败）。
> **G8 的「行内来源行号」只对「有上游同名符号」的新增行成立**——`NodeFunc` / `TraceSink` /
> `Span` / `TraceQuery` 无上游同名符号，该 4 行写「无上游对应」+ 契约条目号。

---

## 3. 冒烟：亲手用一遍协议与数据类

> 下面是**使用**示例（不是实现代码）——用来确认「对外的手感」符合冻结面。

```bash
/tmp/fg-verify/bin/python - <<'PY'
from dataclasses import replace
from freegraph.contracts import (
    NodeFunc, Checkpointer, TraceSink, Store, CompiledGraph,
    Graph, Node, Edge, Span, TraceQuery,
)

# ① 五个协议都是「协议」：无需继承即可被判定
class MySink:
    def on_span_start(self, span): print("start", span.id, span.node)
    def on_span_end(self, span):   print("end  ", span.id, span.end_time)
    def current_span(self):        return None

sink = MySink()
print("isinstance TraceSink:", isinstance(sink, TraceSink))          # True
print("isinstance Checkpointer:", isinstance(sink, Checkpointer))    # False（缺方法）
print("isinstance Store:", isinstance(sink, Store))                  # False（缺方法）

# ② 图结构：字段名与容器形态
g = Graph(
    nodes=(Node(id="a", name="别名 A"), Node(id="b")),
    edges=(Edge(source="a", target="b", conditional=True, condition="route"),),
)
print("节点名:", [n.id for n in g.nodes])            # ['a', 'b']
print("别名缺省同 id:", g.nodes[1].name)             # 'b'
print("条件边:", g.edges[0].conditional, g.edges[0].condition)

# ③ span：11 字段 + 不可变 + 生命周期（结束 = 同 id 的新实例）
s0 = Span(id="s1", name="node:a", run_id="r1", node="a",
           start_time="2026-11-06T10:00:00+00:00")
sink.on_span_start(s0)
s1 = replace(s0, end_time="2026-11-06T10:00:01+00:00")
sink.on_span_end(s1)
print("同 id:", s0.id == s1.id, "| 开始快照的 end_time 仍为空:", s0.end_time is None)

# ④ 不可哈希（统一口径）
try:
    {g.nodes[0]}
except TypeError as e:
    print("不可哈希:", type(e).__name__)

# ⑤ 查询请求：5 字段全可空，全空 = 取全部
q = TraceQuery(run_id="r1")
print("查询:", q.run_id, q.thread_id, q.node, q.start_time, q.end_time)
PY
```

**期望输出**（措辞以实现为准，**形态与次序**是判据）：

```text
isinstance TraceSink: True
isinstance Checkpointer: False
isinstance Store: False
start s1 a
end   s1 2026-11-06T10:00:01+00:00
节点名: ['a', 'b']
别名缺省同 id: b
条件边: True route
同 id: True | 开始快照的 end_time 仍为空: True
不可哈希: TypeError
查询: r1 None None None None
```

---

## 4. 人工验证记录（原则 V · 人工门禁）

按 `harness/verification/README.md` 的五段式（**环境 / 步骤 / 实际输出 / 结论 / 遗留问题**）
把本指南的执行结果记入：

```text
harness/verification/B2F1/manual-verification.md
```

**必须逐条核对 A1–A4 四项验收判据**：

| 判据 | 判定方式 | 本指南对应节 |
|---|---|---|
| **A1 协议齐全** | 5 个协议 + 5 个数据类**全部存在且可导入** | §1（`test_protocols.py` / `test_graph.py` / `test_span.py`）+ §3 |
| **A2 契约层可被单独消费** | 隔离环境导入无副作用；依赖闭包**为空集** | §2.1 / §2.2 / §2.3 / §2.4 |
| **A3 ARCH-2 通过** | AST 断言：契约层零内部依赖、零 `langchain*` import | §2.5 + `test_architecture.py` |
| **A4 D11 已批准** | 三项修订**全部落地可查**：C27 条目 / C23 字段约定 / C22 标识约定 | `contracts/public-api.md` §2（C22 / C23 / C27 行）+ §3 |

> **必须显式记录的「不适用」子项**（非忽略）：
> ① 原则 III 的 `harness/demo/target.py` 原样可跑 —— 本 feature **不交付**门面与运行时，
> 依赖分别归 **B2F2** / **B7F3**；
> ② 原则 V 的「fake 模型 + 真实模型各跑一遍」—— 本 feature **无运行时、无模型调用**；
> ③ 原则 II 的 C4 / C8 两条回归测试 —— 分别归 **B5F2** / **B8F1**。

---

## 5. 清理

```bash
rm -rf /tmp/fg-verify
find . -name "__pycache__" -type d -prune -exec rm -rf {} +
```

---

## 附：失败时先查这张表

| 症状 | 多半是 | 先查 |
|---|---|---|
| `ModuleNotFoundError: freegraph` | `conftest.py` 的 `src/` 注入未生效 | `tests/contracts/conftest.py` |
| G3 恒 skip | 本机未装 freegraph（无 dist-info） | §2.1 的隔离环境 |
| G7 报「符号数不符」 | 新增/漏导出符号 | `contracts/public-api.md` §0 与 `__all__` |
| G10 报「有非 ... 的方法体」 | 给协议方法写了默认实现 | `protocols.py`；**协议必须纯抽象** |
| G12 报「权威文件数 != 1」 | 两个 `public-api.md` 都带 `<!-- authority: yes -->` | 两文件的**首行附近**标记；旧文件应为 `<!-- authority: no -->` |
| G8 报「矩阵未逐符号覆盖」 | `README.md` 兼容矩阵缺本层 10 个新符号的行 | FR-017：逐符号补行（**无上游同名符号**的 4 行写「无上游对应」+ 契约编号） |
| G2 报「第三方 import 违规：pytest」 | 扫描范围误扩到全部 `tests/contracts/**` | G2 的**两档范围**：第三方档**只扫 `tests/contracts/fixtures/**`** |
| G13 报「字段含对象类型」 | 数据类加了装对象引用的字段 | `data-model.md` §4.3（纯数据纪律） |
| 导入耗时 > 300 ms | 契约层拉进了重量级依赖 | G2 的第三方 import 扫描 |
| `isinstance(f, NodeFunc)` 恒为真 | **正常**——`__call__` 协议的固有性质 | 见 `data-model.md` §2.1 的「已知局限」 |
