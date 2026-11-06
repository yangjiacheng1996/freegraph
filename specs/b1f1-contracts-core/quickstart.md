# 验收指南（quickstart.md）

**功能块**: B1F1 · 契约层骨架（四个核心类型 + 异常体系）
**Branch**: `b1f1-contracts-core` · **Date**: 2026-11-05

> 本文件是**可运行的验证指南**：照着做一遍，就能确认本 feature 交付到位。
> 设计意图：每条命令都可直接复制执行，每条都有**期望输出**可比对。
> 类型细节见 [contracts/public-api.md](./contracts/public-api.md)；
> 不变式清单见 [data-model.md](./data-model.md)；门禁定义见 [contracts/architecture-gates.md](./contracts/architecture-gates.md)。

---

## 0. 前置

| 项 | 要求 |
|---|---|
| Python | ≥ 3.11（`pyproject.toml` 的 `requires-python`） |
| 开发期工具 | `pytest`（**不进发行包**；extras 与 CI 门禁归 B3F1） |
| 网络 | **仅第 2 节（隔离环境验收）需要一次网络** —— `pip install .` 须拉取构建后端 `hatchling`；**第 1 节（单测）与第 3 节（冒烟）完全本地离线**（基础安装**零**第三方依赖，装完只有 freegraph 自己） |
| 命令名 | 下文用 `python3`；若你的环境只有 `python`，把 `python3` 换成 `python` 即可（venv 内统一用 `/tmp/fg-verify/bin/python`） |

---

## 1. 跑单元测试（开发期，免安装）

仓库当前**未安装** freegraph，`tests/contracts/conftest.py` 会把 `src/` 注入 `sys.path`（源码优先），故**无需先 `pip install`**：

```bash
cd <repo-root>
python3 -m pytest tests/contracts -q
```

**期望输出**：

```text
..........................                                     [100%]
26 passed in 0.42s
```

> 断言条数以实现为准（`26` 是设计预期值）；关键是 **全部 passed、0 failed、0 error**。
> 若出现 `ModuleNotFoundError: No module named 'freegraph'` ⇒ `conftest.py` 的 `src/` 注入未生效。

**分文件跑**（便于定位）：

```bash
python3 -m pytest tests/contracts/test_types.py    -q   # 四类型的字段 / 构造 / 校验
python3 -m pytest tests/contracts/test_errors.py   -q   # 异常体系结构与属性
python3 -m pytest tests/contracts/test_architecture.py -q  # 八条架构门禁
```

---

## 2. 隔离环境验收（SC-001 / SC-002 / SC-003）

「隔离」= 一个只装了 freegraph 基础包、没有 LangChain 家族任何包的干净 venv。

### 2.1 建环境并安装

```bash
cd <repo-root>
python -m venv /tmp/fg-verify
/tmp/fg-verify/bin/pip install --upgrade pip
/tmp/fg-verify/bin/pip install .
```

**期望**：`Successfully installed freegraph-0.0.3` —— **只有这一个**（基础安装零第三方依赖）。

### 2.2 G3 · 依赖闭包：基础安装**为空集**（SC-002）

```bash
/tmp/fg-verify/bin/python - <<'PY'
from importlib.metadata import requires

def _specs(pkg):
    """拆 Requires-Dist：返回 (名字, 是否带 extras 条件)。"""
    out = []
    for spec in requires(pkg) or []:
        head, _, marker = spec.partition(";")
        name = head.split("[")[0].split(">")[0].split("<")[0].split("=")[0].strip()
        out.append((name, "extra ==" in marker))
    return out

def closure(pkg, seen=None, with_extras=False):
    seen = seen if seen is not None else set()
    for name, is_extra in _specs(pkg):
        if is_extra and not with_extras:
            continue                      # 基础安装：剥离 extras marker
        key = name.lower().replace("_", "-")
        if key in seen:
            continue
        seen.add(key)
        try:
            closure(name, seen, with_extras)
        except Exception:
            pass
    return seen

# ① 基础安装闭包（SC-002）：MUST 为空集（零第三方运行时依赖）
base = closure("freegraph")
print("基础安装闭包:", sorted(base))
assert base == set(), base
for bad in ("langsmith", "langchain", "langchain-core", "langgraph", "langgraph-core",
            "typing-extensions"):
    assert bad not in base, bad
print("OK: 基础安装依赖闭包为空（零第三方运行时依赖）")

# ② extras 变体闭包：只允许宪法依赖白名单内的包（extras 由 B3F1 引入，当前为空）
#    白名单 = 宪法「依赖白名单」：必装无；可选 extra pydantic / ormsgpack /
#    opentelemetry-api / opentelemetry-sdk（[png] 的 mermaid 相关包
#    由 B3F1 定点后补入本清单）。
WHITELIST = {"pydantic", "ormsgpack",
              "opentelemetry-api", "opentelemetry-sdk"}
extras = closure("freegraph", with_extras=True) - base
print("extras 闭包:", sorted(extras))
assert extras <= WHITELIST, extras
print("OK: extras 闭包均在宪法依赖白名单内")
PY
```

**期望输出**：

```text
基础安装闭包: []
OK: 基础安装依赖闭包为空（零第三方运行时依赖）
extras 闭包: []
OK: extras 闭包均在宪法依赖白名单内
```

### 2.3 SC-001 · 导入成功且耗时在预算内

```bash
/tmp/fg-verify/bin/python -c "import freegraph.contracts; print('import OK')"
```

**期望**：`import OK`

```bash
/tmp/fg-verify/bin/python - <<'PY'
import subprocess, sys, time
t0 = time.perf_counter()
r = subprocess.run([sys.executable, "-c", "import freegraph.contracts"], capture_output=True)
dt = (time.perf_counter() - t0) * 1000
print(f"耗时 {dt:.0f} ms  退出码 {r.returncode}")
assert r.returncode == 0
assert dt < 300, f"超出 300 ms 预算：{dt:.0f} ms"
print("OK: 在 300 ms 预算内")
PY
```

**期望输出**：`耗时 < 300 ms  退出码 0` + `OK: 在 300 ms 预算内`

> 预算依据：解释器冷启动 ≈ 30 ms（本机实测基线；**基础安装零依赖后不再有
> `import typing_extensions` 的 ≈ 90 ms 开销**），取 300 ms 留约 10 倍余量。
> CI 机器性能差异大，故不设更紧的阈值。

### 2.4 G1 · 顶层包惰性（SC-006）

```bash
echo "--- import freegraph ---"
/tmp/fg-verify/bin/python -c "import freegraph, sys; print(sorted(m for m in sys.modules if m.startswith('freegraph')))"
echo "--- import freegraph.contracts ---"
/tmp/fg-verify/bin/python -c "import freegraph.contracts, sys; print(sorted(m for m in sys.modules if m.startswith('freegraph')))"
```

**期望输出**：

```text
--- import freegraph ---
['freegraph']
--- import freegraph.contracts ---
['freegraph', 'freegraph.contracts', 'freegraph.contracts.errors', 'freegraph.contracts.types']
```

### 2.5 G2 / G4 / G5 / G6 / G7 · 静态门禁

这些已由 `tests/contracts/test_architecture.py` 覆盖，在第 1 步跑过。此处给出**手工复核**命令：

```bash
# G2 · 契约层零内部 import
# 注：包内相对导入（from .types import ...）合法，故只看绝对模块名；
#     正式门禁见 tests/contracts/test_architecture.py（AST 口径，判 level）。
python3 - <<'PY'
import ast, pathlib
bad = []
for p in pathlib.Path("src/freegraph/contracts").rglob("*.py"):
    tree = ast.parse(p.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            bad += [(p.name, a.name) for a in node.names if a.name.startswith("freegraph")]
        elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith("freegraph"):
            if node.module != "freegraph.contracts":
                bad.append((p.name, node.module))
print("内部 import:", bad)
assert not bad, bad
print("OK: 契约层零内部 import")
PY

# G4 · 零环境变量 / 零出站（先确认目录存在，避免「目录没了」被当成「没有违规」）
# 注：这是**文本粗筛**（grep）；正式门禁以 tests/contracts/test_architecture.py 的
#     **AST 口径**为准——只看 Import/ImportFrom 的模块名与 Attribute/Name 访问，
#     不扫 docstring 与注释（避免「docstring 里提到 subprocess」造成假阳性）。
test -d src/freegraph/contracts || { echo "契约层目录不存在"; exit 1; }
if grep -rnE "os\.environ|os\.getenv|import socket|import http|urllib|requests|httpx|subprocess" src/freegraph/contracts/; then
  echo "发现环境变量读取或网络访问"; exit 1
else
  echo "OK: 未发现环境变量读取或网络访问"
fi

# G5 · 署名头
for f in src/freegraph/contracts/*.py; do
  head -1 "$f" | grep -q "^# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph$" \
    && echo "OK 署名头: $f" || echo "缺署名头: $f"
done

# G6 · py.typed
test -f src/freegraph/py.typed && [ ! -s src/freegraph/py.typed ] && echo "OK: py.typed 存在且为空"

# G7 · 公开符号面恰为 8 个
/tmp/fg-verify/bin/python -c "
import freegraph.contracts as c
want = {'StateDict','Command','StateSnapshot','RunConfig','FreegraphError','InvalidUpdateError','GraphRecursionError','GraphInterrupt'}
assert set(c.__all__) == want, c.__all__
assert not hasattr(c, 'Send') and not hasattr(c, 'interrupt')
print('OK: 公开符号面恰为 8 个')
"

# G8 · 文档合规门禁（THIRD_PARTY_NOTICES + API 兼容矩阵）
test -f THIRD_PARTY_NOTICES && echo "OK: THIRD_PARTY_NOTICES 存在"
python3 - <<'PY'
import re, pathlib
readme = pathlib.Path("README.md").read_text(encoding="utf-8")
m = re.search(r"^## API 兼容矩阵\s*$(.*?)(?=^## |\Z)", readme, re.S | re.M)
assert m, "README.md 缺少「## API 兼容矩阵」章节"
rows = re.findall(r"^\|\s*`([A-Za-z_]+)`\s*\|", m.group(1), re.M)
want = {"StateDict", "Command", "StateSnapshot", "RunConfig",
        "FreegraphError", "InvalidUpdateError", "GraphRecursionError", "GraphInterrupt"}
assert set(rows) == want, set(rows) ^ want
assert "不构成 affiliation" in m.group(1)
print("OK: 兼容矩阵覆盖全部 8 个公开符号")
PY
```

**期望输出**：每条均为 `OK: ...`（`grep` 无命中时输出 `OK: 未发现环境变量读取或网络访问`）。

---

## 3. 冒烟：亲手用一遍四个类型

```bash
/tmp/fg-verify/bin/python - <<'PY'
from freegraph.contracts import (
    StateDict, Command, StateSnapshot, RunConfig,
    FreegraphError, InvalidUpdateError, GraphRecursionError, GraphInterrupt,
)

# 1) 运行配置：裸 dict 构造（严格 / 宽松）
cfg = RunConfig.from_dict({"thread_id": "t-1", "tags": ["demo"]})
print("cfg:", cfg)

try:
    RunConfig.from_dict({"threadId": "t-1"})
except FreegraphError as e:
    print("未知键被拒:", e)

# 2) 命令原语
print("跳转:", Command(goto="review"))
print("跳转+写入:", Command(goto=("a", "b"), update={"n": 1}))
print("跳向父图:", Command(goto=Command.PARENT))
try:
    Command()
except FreegraphError as e:
    print("空命令被拒:", e)

# 3) 状态快照
snap = StateSnapshot(
    values={"messages": ["hi"]},
    next=(),
    config=cfg,
    metadata={},
    created_at="2026-11-05T10:20:30.123456+00:00",
    tasks=(),
    interrupts=(),
)
print("快照:", snap)

# 4) 异常体系：只捕获基类即可兜住全部内核错误
for exc in (
    InvalidUpdateError(["typo"]),
    GraphRecursionError(25, 25),
    GraphInterrupt(type("P", (), {"value": "v", "id": "i"})()),
):
    try:
        raise exc
    except FreegraphError as e:
        print(type(e).__name__, "→", e)
PY
```

**期望输出**（形态一致即可，具体 repr 以实现为准）：

```text
cfg: RunConfig(thread_id='t-1', context=None, metadata={}, tags=('demo',))
未知键被拒: ...
跳转: Command(goto='review', update=None, resume=None)
跳转+写入: Command(goto=('a', 'b'), update={'n': 1}, resume=None)
跳向父图: Command(goto='__parent__', update=None, resume=None)
空命令被拒: ...
快照: StateSnapshot(values={'messages': ['hi']}, next=(), config=RunConfig(...), ...)
InvalidUpdateError → ...
GraphRecursionError → ...
GraphInterrupt → ...
```

---

## 4. 人工验证记录（原则 V · 人工门禁）

本 feature 结束**必须**留一份人工验证记录，路径：

```text
harness/verification/B1F1/manual-verification.md
```

须包含五段：**环境** / **步骤** / **实际输出** / **结论** / **遗留问题**。
第 1–3 节的命令与期望输出可直接作为「步骤」与「实际输出」的骨架。

---

## 5. 清理

```bash
rm -rf /tmp/fg-verify
```

---

## 附：失败时先查这张表

| 症状 | 多半是 | 处理 |
|---|---|---|
| `ModuleNotFoundError: freegraph` | `conftest.py` 未把 `src/` 注入 | 确认 `tests/contracts/conftest.py` 存在；或用 `PYTHONPATH=src python3 -m pytest ...` |
| G1 期望输出多出 `freegraph.contracts` | 顶层包不再惰性 | 查 `src/freegraph/__init__.py` 是否新增了 import |
| G2 报出内部 import | 契约层引用了内部层 | 改为自包含实现，或把该能力挪到 B2F1+ |
| G3 闭包多出条目 | `pyproject.toml` 依赖白名单被改（或 extras 依赖未剥离 marker） | 恢复 `dependencies = []`（基础安装零第三方依赖） |
| G5 报「缺署名头」 | 新文件未加署名头 | 补首行署名（docstring 仍须是首个语句） |
| SC-001 超 300 ms | 契约层拉起了重量级依赖 | 查 `__init__.py` 的导入链 |
| G2 报出第三方 import | 契约层引了 `langchain_core` 之类 | 改为自包含实现（FR-005 / FR-007 红线） |
| G8 报「覆盖不全」 | 新增了公开符号但没更新兼容矩阵 | 在 `README.md` 的兼容矩阵补一行 |
