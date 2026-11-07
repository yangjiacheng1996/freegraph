# Quickstart · B2F2 公开 API 门面 + API 签名快照

**验收指南**：本文件给出**可复制**的验证步骤，逐条证明本 feature 的成功标准（SC-001…SC-018）
已成立。**不是**实现教程——实现细节在 `tasks.md` 与源码里；**冻结面**的权威在
[`contracts/facade-api.md`](./contracts/facade-api.md) / [`contracts/snapshot-format.md`](./contracts/snapshot-format.md) /
[`data-model.md`](./data-model.md)。

> **⚠️ 本 feature 零行为**：`StateGraph` 的四个方法与 `interrupt` 一律抛
> `NotImplementedError`（**这是预期行为**，不是缺陷）⇒ §5 的断言是「**必须抛**」，
> 而「**必须不抛**」的断言只针对 `StateGraph(schema)` 的**构造**。

---

## 0. 速查（验收命令一览）

| # | 场景 | 命令 | 关联 |
|---|---|---|---|
| A | 隔离环境 import | `python -c "from freegraph.graph import StateGraph, START, END"` | SC-001 |
| B | 导出面 / 常量 | `pytest tests/facade/test_facade.py -v` | SC-002 / SC-003 |
| C | 快照 | `pytest tests/facade/test_api_snapshot.py -v` | SC-005 / SC-006 |
| D | 未接线语义 | `pytest tests/facade/test_facade.py -v -k "not_wired or constructor"` | SC-010 / SC-011 / SC-017 |
| E | 顶层包惰性 | `pytest tests/facade/test_facade_gates.py -v -k "load or lazy"` | SC-007 / SC-008 |
| F | 依赖卫生 | `pytest tests/facade/test_facade_gates.py -v -k "hygiene"` | SC-009 |
| G | 兼容矩阵 | `pytest tests/facade/test_facade_gates.py -v -k "matrix"` | SC-012 |
| H | 契约层未受影响 | `pytest tests/contracts/test_architecture.py -v -k "g7 or g12"` | SC-015 |
| I | 只读基准 / 署名头 | `git diff --exit-code -- harness/demo/target.py` | SC-014 |
| J | 验收脚本的预期退出码 | `python harness/demo/graph_core.py; echo $?` | SC-011 |
| K | 导入开销预算 | 见 §12 | SC-018 |
| 全量 | 本 feature + 既有门禁 | `pytest -q` | 全部 |

---

## 1. 前置

| 项 | 要求 |
|---|---|
| Python | **≥ 3.11**（`requires-python = ">=3.11"`）；本机实测 3.12.3 |
| 依赖 | **零**第三方运行时依赖（`dependencies = []`）；开发期只需 `pytest` |
| 工作目录 | 仓库根（`<repo>/`） |
| 源码可见性 | 仓库**未安装** freegraph 时，`tests/facade/conftest.py` 会把 `<repo>/src` 插入 `sys.path` 最前（源码优先）；已安装时设 `FREEGRAPH_TEST_INSTALLED=1` 跳过注入（供 B3F1 的 CI 用） |

```bash
cd <repo>
python -V                 # 期望：Python 3.11+
python -m pytest --version
```

---

## 2. 场景 A · 隔离环境的 import（SC-001 / A1）

**目的**：证明「只换包名」的验收契约第 1 项在**第一个可运行的 feature** 就成立。

```bash
python -m venv /tmp/fg-b2f2 && /tmp/fg-b2f2/bin/pip install -q .
/tmp/fg-b2f2/bin/python -c "from freegraph.graph import StateGraph, START, END; print(START, END, StateGraph)"
echo "exit=$?"
```

**期望**：

- 退出码 **0**；
- 输出 `__start__ __end__ <class '...StateGraph'>`；
- 隔离环境 `pip list` 中**只有** `freegraph`（无任何第三方包）⇒ 依赖闭包为空集（原则 I / II）。

> **隔离环境是「零依赖」的唯一可信证据**：本机环境可能装了 `langchain` / `langgraph`，
> 会掩盖依赖泄漏。

---

## 3. 场景 B · 导出面与常量（SC-002 / SC-003）

```bash
python -m pytest tests/facade/test_facade.py -v
```

**期望**（逐条断言见 `tests/facade/test_facade.py`）：

| 断言 | 期望 |
|---|---|
| `__all__` 集合 | **恰 7 个**：`StateGraph` / `START` / `END` / `Command` / `Send` / `interrupt` / `RunConfig`（期望值从 `contracts/facade-api.md` §0 解析） |
| 门面模块内公开名集合 | **同上 7 个**（多一个 / 少一个都失败） |
| `START` / `END` | `'__start__'` / `'__end__'`，且均为 `str` |
| `Command` / `RunConfig` 的同一性 | `freegraph.graph.Command is freegraph.contracts.Command` ⇒ **True**；`RunConfig` 同理 |

> **期望值来自 `facade-api.md` §0 而非生成的快照** ⇒ 门禁判定**非循环**（research D-07）。

---

## 4. 场景 C · API 签名快照（SC-005 / SC-006 / A2）

### 4.1 比对（常规）

```bash
python -m pytest tests/facade/test_api_snapshot.py -v
```

**期望**：全部通过——生成的快照与入库的 `contracts/public-api-snapshot.txt` **逐字节相同**；
**两次生成逐字节相同**（可复现）。

### 4.2 更新入口（**默认不生效**）

```bash
cp contracts/public-api-snapshot.txt /tmp/snap.before
python -m pytest tests/facade/test_api_snapshot.py -q          # 不带开关
diff -u /tmp/snap.before contracts/public-api-snapshot.txt && echo "快照未被改动 ✓"

python -m pytest tests/facade/test_api_snapshot.py -q --update-api-snapshot   # 显式更新
git diff --stat contracts/public-api-snapshot.txt              # 无变化 ⇒ 幂等
```

**期望**：

- 不带开关 ⇒ 快照文件**逐字节未变**（FR-011 ① · SC-005）；
- 带开关 ⇒ 重新生成；在**代码未变**时结果**相同**（幂等）；
- 若确有合法签名变更 ⇒ 开关产出新文本，**必须人工 review `git diff` 后再提交**
  （MUST NOT 静默自动更新）。

### 4.3 自检（快照确实能抓出漂移）

```bash
python -m pytest tests/facade/test_api_snapshot.py -v -k selfcheck
```

**期望**：自检用例**通过**——它内部构造一个「参数被改名」的**人造命名空间**，断言渲染结果
与入库快照**不同**且 **diff 非空**（FR-011 ②）。若该用例失败 ⇒ 说明比对逻辑**抓不出漂移**
⇒ 门禁形同虚设。

> **自检不碰源码**（渲染器是纯函数，research D-10）⇒ 可在只读环境跑、无副作用。

---

## 5. 场景 D · 未接线语义与构造（SC-010 / SC-011 / SC-017）

```bash
python -m pytest tests/facade/test_facade.py -v -k "not_wired or constructor or send or interrupt"
```

**期望**：

| 断言 | 期望 |
|---|---|
| `StateGraph(schema)` | **构造成功**、**不抛异常**、**零副作用** |
| `StateGraph(schema, extra)` | 抛 `TypeError`（构造**只**接受一个位置参数） |
| `add_node` / `add_edge` / `add_conditional_edges` | 抛 `NotImplementedError`，消息匹配 `<方法名> 尚未接线（由 B6F1 交付）` |
| `compile` | 抛 `NotImplementedError`，消息匹配 `compile 尚未接线（由 B7F2 交付）` |
| `interrupt("x")` | 抛 `NotImplementedError`，消息匹配 `interrupt 尚未接线（由 B10F1 交付）` |
| `Send("w", {"n": 1})` | **构造成功**；`Send(node="w", arg={"n": 1})` 同样**合法**（位置或关键字皆可） |
| 改 `Send` 的属性 | 失败（**不可变记录**） |
| 四个方法的签名 | 与 `data-model.md` §2.1 **逐项一致**（参数名 / 缺省值 / keyword-only 标记 / 链式返回） |

> **异常消息的正则**：`(?:add_node|add_edge|add_conditional_edges|compile|interrupt) 尚未接线（由 B\dF\d 交付）`
> ——「必须点名归属 feature」是可机械判定的（FR-009）。

---

## 6. 场景 E · 顶层包惰性与模块加载面（SC-007 / SC-008 / A3）

```bash
python -m pytest tests/facade/test_facade_gates.py -v -k "load or lazy"
```

**期望**（**子进程**执行，测试进程自身的 `sys.modules` 不可作依据）：

| 断言 | 期望 |
|---|---|
| `import freegraph` 后 | `sys.modules` 中 `freegraph.*` 的**子模块数 == 0**（只有 `freegraph` 本身） |
| `import freegraph.graph` 后 | **不含**持久化层 / 可观测层子模块（**== 0**）——门面不横向依赖 L4 / L5 |
| `from freegraph.graph import StateGraph` 后 | `freegraph.contracts` **被加载**（门面**可以**依赖 L1 契约层） |

手工复核（等价于门禁的子进程口径）：

```bash
python -c "import sys, freegraph; print(sorted(m for m in sys.modules if m.startswith('freegraph')))"
# 期望：['freegraph']

python -c "import sys, freegraph.graph; print(sorted(m for m in sys.modules if m.startswith('freegraph')))"
# 期望：['freegraph', 'freegraph.contracts', 'freegraph.contracts.errors', 'freegraph.contracts.graph',
#        'freegraph.contracts.protocols', 'freegraph.contracts.trace', 'freegraph.contracts.types',
#        'freegraph.graph', 'freegraph._primitives', 'freegraph._stategraph']
#        ——不含任何 persistence / observability / runtime 形态的模块
```

> **本门禁是 D1 决议附加约束的执行手段**：顶层包一旦拖进门面，
> `import freegraph.contracts` 就会连带加载 L3 → L2，契约层「可独立消费」的收益随之失效。

---

## 7. 场景 F · 门面依赖卫生（SC-009）

```bash
python -m pytest tests/facade/test_facade_gates.py -v -k hygiene
```

**期望**（AST 扫描门面的**三个**模块：`graph.py` / `_stategraph.py` / `_primitives.py`）：

| 档 | 期望计数 |
|---|---|
| ① **内部 import**：指向 L2 / L3 / L4 / L5（`runtime` / `persistence` / `observability`）的 import | **== 0**（`freegraph.contracts` 与门面包内私有模块**合法**） |
| ② **第三方 import**：`langchain*` / `langgraph*` / `langsmith` / `pydantic` / `typing_extensions` | **== 0**（**标准库**用 `sys.stdlib_module_names` 判 ⇒ `freegraph.*` **不属**本档） |
| ③ **环境变量读取**：`os.environ` / `os.getenv` 等 | **== 0** |
| ④ **出站 / 文件 I/O**：`socket` / `urllib` / `http` / `open(` / `Path.write_*` / `subprocess` 等 | **== 0** |

> **⚠️ 两档制的理由**（research D-22）：第三方档**不得**写成「任何非标准库顶层包」——
> 门面**必须** import `freegraph.contracts`，而 `freegraph` 不是标准库 ⇒ 一刀切会让门禁
> 对本 feature 的**必需代码恒红**（B2F1 的 G2 已就同一类缺陷留过判例）。
> 违规时门禁**报出行号**，可直接定位。

---

## 8. 场景 G · 兼容矩阵（SC-012）

```bash
python -m pytest tests/facade/test_facade_gates.py -v -k matrix
```

**期望**：

- 门面 7 个符号在 `README.md` 的「## API 兼容矩阵」章节内**各恰有一行**；
- 新增 5 行的「等价程度」逐符号为：`StateGraph` / `Send` / `interrupt` = **部分等价**；
  `START` / `END` = **行为等价**；
- 新增 5 行含**上游来源行号**（写在「差异说明」单元格末尾，核实环境 `langgraph 1.2.11`）：
  `langgraph/graph/state.py:131` / `langgraph/constants.py:30` / `langgraph/constants.py:28` /
  `langgraph/types.py:704` / `langgraph/types.py:851`；
- **既有 18 行逐字未改**。

人工复核：

```bash
sed -n '/^## API 兼容矩阵/,/^## /p' README.md | grep -E '^\| `(StateGraph|START|END|Send|interrupt)`'
```

---

## 9. 场景 H · 契约层未受影响（SC-015）

```bash
python -m pytest tests/contracts/test_architecture.py -q -k "g7 or g12"
python -c "import sys; sys.path.insert(0,'src'); import freegraph.contracts as c; print(len(c.__all__))"
```

**期望**：`len(c.__all__) == 18`，且 `Send` / `interrupt` **不在**其中（裁定 2 · SC-015）。
本 feature **不修改** `src/freegraph/contracts/**` ⇒ 既有门禁 G7 / G12 **零改动**。

---

## 10. 场景 I · 只读基准与署名头（SC-014）

```bash
git diff --exit-code -- harness/demo/target.py && echo "target.py 未被修改 ✓"
git diff --exit-code -- THIRD_PARTY_NOTICES && echo "第三方清单未变 ✓（零新增依赖）"
```

**期望**：两条命令均**退出码 0**（无 diff）。

署名头由既有门禁 **G5**（守契约层那批文件）+ **G20**（守本 feature 新建的 10 个文件，
门面侧覆盖）共同覆盖：

```bash
python -m pytest tests/contracts/test_architecture.py -v -k g5
python -m pytest tests/facade/test_facade_gates.py -v -k g20
```

---

## 11. 场景 J · 验收脚本的**预期退出码**（SC-011）

```bash
python harness/demo/graph_core.py; echo "exit=$?"
```

**期望**：

- 脚本**能导入**门面（7 个名字齐备）⇒ **不再**以退出码 **2**（「环境未就绪」）结束；
- 但用例**必然全红**（`StateGraph` 未接线）⇒ 退出码 **1**（断言失败）；
- **退出码 1 是本 feature 的预期状态**，**不是**缺陷——`graph_core.py` 的用例在 M1 / M2 逐条转绿。

> **本 feature MUST NOT 因此宣称验收脚本已跑通**（spec FR-009 / FR-018）。

---

## 12. 场景 K · 导入开销预算（SC-018 / FR-019）

**目的**：确认门面的导入开销在预算内（三个新增模块不把总耗时推过 120 ms）。

```bash
# 复用场景 A 建的 venv（不新建）；基准解释器 = CPython 3.11.x
# ① 预热一次（排除首次 .pyc 落盘 / 磁盘冷启动噪声）  ② 取三次的最小值
/tmp/fg-b2f2/bin/python -c "import freegraph.graph"
for i in 1 2 3; do
  /tmp/fg-b2f2/bin/python -c "import time; t=time.perf_counter(); import freegraph.graph; print(time.perf_counter()-t)"
done
# 基线（同一口径）
for i in 1 2 3; do
  /tmp/fg-b2f2/bin/python -c "import time; t=time.perf_counter(); import freegraph.contracts; print(time.perf_counter()-t)"
done
```

**期望**：

- 输出 **< 0.12**（即 **< 120 ms**）；
- **计时口径（唯一）**：以 `time.perf_counter()` 在 import 语句**前后**取差、
  **不含解释器自身启动**、**暖机后 best-of-3**（先预热一次再取三次最小值）、
  **基准 CPython 3.11.x**（FR-019）；
- 基线参照：`import freegraph.contracts` = **50–63 ms**（实测 · CPython 3.12.3 · 暖机 best-of-3 · 2026-11-07）。

> 实测值 **与基线值** MUST 记入 `harness/verification/B2F2/manual-verification.md` 第 3 节
> （`tasks.md` T040）；**测量环境**（OS / CPU / Python 版本）记入第 1 节。

---

## 13. 人工验证记录（SC-013 / 原则 V）

```bash
mkdir -p harness/verification/B2F2
# 骨架见本 feature 交付的 harness/verification/B2F2/manual-verification.md
```

**记录 MUST 采用五段式**（环境 / 步骤 / 实际输出 / 结论 / 遗留问题），第 3 节 MUST 粘贴
**真实输出**（不是「符合预期」）；未实跑的平台 / 版本 MUST 显式记入「遗留问题」
（MUST NOT 伪造输出）。

**逐条核对**验收判据：

| 判据 | 判定方式 | 本 quickstart 的落点 |
|---|---|---|
| **A1** `from freegraph.graph import StateGraph, START, END` 可用 | 隔离环境执行，退出码 0 | §2 |
| **A2** 签名快照入库 | 仓库中存在快照文件 + CI 跑快照比对 | §4.1（CI 挂载归 B3F1） |
| **A3** 顶层包惰性 | `import freegraph` 后的 `sys.modules` 检查 | §6 |

---

## 14. 全量验收

```bash
python -m pytest -q          # 本 feature 的用例 + 既有的契约层用例（**必须全绿**）
```

**期望**：**全绿**。既有门禁 G1–G13 因本 feature **零改动**契约层而**保持原状**；
新增门禁 G14–G20 与其 **8 条自检**（7 条门禁，G15 两段各一条）全绿。

> **若某个既有门禁变红**：先查是否**误改**了 `src/freegraph/contracts/**` 或
> `tests/contracts/**`——本 feature **不要求**改动它们（见 plan「与既有 feature 的关系」）。
