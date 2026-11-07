# B2F1 · 5 个协议（4 类可插拔协议 + `CompiledGraph`）+ 5 个纯数据类 —— 人工验证记录

**feature**: B2F1（**5 个协议**：4 类可插拔协议 `NodeFunc` / `Checkpointer` / `TraceSink` / `Store` + `CompiledGraph`；**5 个纯数据类**：`Graph` / `Node` / `Edge` / `Span` / `TraceQuery`）
**验收依据**: `specs/b2f1-contracts-protocols/spec.md` · `plan.md` · `tasks.md`
**验收指南**: [`specs/b2f1-contracts-protocols/quickstart.md`](../../../specs/b2f1-contracts-protocols/quickstart.md)
**记录日期**: 2026-11-06
**记录人**: 实现者（单人串行推进 · 立项书 §5.2）

> **📌 本文件状态 = 已回填（2026-11-06）**
> 按宪法原则 V 与 `harness/verification/README.md` 的五段式（环境 / 步骤 / 实际输出 /
> 结论 / 遗留问题）组织。第 3 节的「实际输出」已粘贴**真实输出**（非「符合预期」）。
> **未回填前，本 feature MUST NOT 宣布完成**（原则 X「MUST NOT 在清单缺项的情况下宣布
> 该特性完成」）——本轮回填已完成，该前置条件已解除。
> **仍待补齐的项**：§3.7（3.11 / 3.13 / 3.14 三档多版本实测）——本机只装了 CPython
> **3.12.3**，已显式记入 §7 遗留问题 7（**不伪造**输出）。

---

## 1. 环境

| 项 | 实际值 |
|---|---|
| 本机 Python | **3.12.3**（`/usr/bin/python3.12`；CPython） |
| 隔离 venv Python | **3.12.3**（`python3 -m venv /tmp/fg-verify`）—— ⚠ **本机只装了 3.12**（`ls /usr/bin/python3.*` 仅有 `python3.12`），故**最低支持版本 3.11 的隔离实测未执行**（见 §7 遗留问题 7） |
| 平台 | `Linux 6.8.0-139-generic x86_64 GNU/Linux`（`Linux-6.8.0-139-generic-x86_64-with-glibc2.39`） |
| freegraph 版本 | **0.0.3**（`pyproject.toml` 的 `version`） |
| pytest 版本 | **7.4.4**（本机）/ **9.2.0**（隔离 venv 内 `pip install pytest` 后执行 §3.9） |
| mypy 版本 | **2.4.1**（隔离 venv `/tmp/mypy-venv`，`compiled: yes`）—— ⚠ **本机主环境未安装 mypy** ⇒ `test_protocols.py` 的 SC-004 静态类型检查用例在本机 **`skip`**（见 §3.1 的 skip 说明）；**附加 D** 用隔离 venv 里的 mypy 实跑（§3.10） |
| `requires-python` | **`>=3.11`**（实测一致） |
| 基础安装的包清单 | **`['freegraph']`**（隔离 venv 的 `pip list` 实测——除 `pip` 自身外**无任何第三方包**） |
| 依赖闭包 | **空集 `[]`**（实测：`importlib.metadata.requires` 递归展开 ⇒ `基础安装闭包: []`）⇒ 许可证白名单校验恒通过 |

> **多版本实测**：若在 3.11 / 3.12 / 3.13 / 3.14 上各建裸 venv 复跑，请把四档结果一并记入
> 本节（B1F1 的做法），并在第 5 节记「最低版本下限」的结论。
> **本轮未做四档复跑**——本机只装了 CPython **3.12.3**（3.11 隔离实测**未执行**，已记入 §7）。

---

## 2. 步骤

**最快的入口 —— 本 feature 的可运行验收脚本**（把本文的验收判据落成可判定断言）：

```bash
python3 harness/verification/B2F1/acceptance.py                    # 跑全部（119 条断言）
python3 harness/verification/B2F1/acceptance.py --record out.md    # 同时生成五段式记录片段
```

> 该脚本**只 import Python 标准库**（零第三方依赖）；环境**未安装** freegraph 时自动注入
> `<repo>/src` 测源码树，「依赖闭包为空集」那条判据标「◌ 环境未就绪」（**不判失败**）。

照 `quickstart.md` 第 1–3 节执行：

| 步 | 命令 | 对应判据 |
|---|---|---|
| 1.1 | `python3 -m pytest tests/contracts -q` | 全量单测 |
| 1.2 | `python3 -m pytest tests/contracts/test_protocols.py -q` | A1 · SC-001 / SC-004 / SC-007 |
| 1.3 | `python3 -m pytest tests/contracts/test_graph.py -q` | A1 · SC-013 / SC-019 |
| 1.4 | `python3 -m pytest tests/contracts/test_span.py -q` | A1 · SC-014 / SC-016 / SC-018 |
| 1.5 | `python3 -m pytest tests/contracts/test_architecture.py -q` | A2 / A3 · G1–G13 |
| 1.6 | `python3 -m pytest tests/contracts/test_types.py -q` | B1F1 回归（四类型未受影响） |
| 1.7 | `python3 -m pytest tests/contracts/test_errors.py -q` | B1F1 回归（异常体系未受影响） |
| 2.1 | 建 venv（3.11）→ `pip install .` → `pip list` | A2 · SC-002 · **零依赖** |
| 2.2 | 依赖闭包脚本（`importlib.metadata.requires` 递归展开） | A2 · SC-002 · G3 |
| 2.3 | `import freegraph.contracts` + 导入耗时脚本 | A2 · SC-002（< 300 ms） |
| 2.4 | 两条 `sys.modules` 清单 | A2 · SC-002 · G1 |
| 2.5 | 静态门禁脚本（G2 / G5 / G8 / G10 / G12）——**其余门禁（G4 / G6 / G9 / G11 / G13）见 `tests/contracts/test_architecture.py`** | A3 · SC-003 / SC-017 / SC-020 |
| 3 | 冒烟脚本（亲手用一遍 5 个协议 + 5 个数据类） | US1–US5 验收场景 |
| 附加 A | （可选）4 个 Python 版本各建裸 venv 装包 + 全量单测 | 最低版本下限 · 零依赖 |
| 附加 B | （可选）发行产物纯度门禁 + wheel METADATA 复核 | 发布门禁 · §9.1 门禁 7 |
| 附加 C | （可选）`FREEGRAPH_TEST_INSTALLED=1` 下跑全量单测（**测发行产物**而非源码树） | B3F1 CI 前置 |
| 附加 D | （可选）mypy 对 `tests/contracts/fixtures/external_impl.py` 跑一次 | SC-004 · **静态类型检查** |

---

## 3. 实际输出

> 以下 MUST 是**真实输出**（非「符合预期」）。未回填处保留 `_待填_`。
>
> **⚠ 骨架里的预填块（§3.3 / §3.4 / §3.5 / §3.6）是「期望输出」样例**（抄自
> `quickstart.md` §2.2–§3 的期望输出）——**不是实测输出**。人工执行后 MUST 用
> **真实输出**替换对应块；**MUST NOT** 把预填的期望输出当作实测输出粘贴
> （否则「实际输出」栏就名存实亡，违反原则 V 的「人工验收是最终验收标准」）。

### 3.1 本地单测（源码树，免安装，Python 3.12.3）

```text
$ python3 -m pytest tests/contracts -q
278 passed, 6 skipped in 1.76s
```

分文件：

```text
$ python3 -m pytest tests/contracts/test_protocols.py -q
38 passed, 1 skipped in 0.14s

$ python3 -m pytest tests/contracts/test_graph.py -q
25 passed in 0.10s

$ python3 -m pytest tests/contracts/test_span.py -q
26 passed in 0.13s

$ python3 -m pytest tests/contracts/test_architecture.py -q -rs
108 passed, 5 skipped in 1.29s
```

**skip 的实测明细**（`pytest -q -rs` 的原始末两行）：

```text
SKIPPED [5] tests/contracts/test_architecture.py:878: freegraph 未安装（无 dist-info 元数据）——依赖闭包门禁须在隔离环境执行（见 quickstart.md §2.2 / T023）
SKIPPED [1] tests/contracts/test_protocols.py:360: mypy 是**开发期工具**且 `freegraph` 未安装 ⇒ 该判据不可执行（本机未装 mypy；SC-004 的静态类型检查用例据此 skip，兜底的注解结构断言仍会跑）
```

> **skip 的含义 MUST 写明**：① G3 依赖闭包 —— 本机未装 freegraph 时恒 skip（**已在隔离环境真跑**，
> 见 §3.3）；② SC-004 的 mypy 用例 —— 本机未装 mypy 时 skip（**兜底的注解结构断言仍须通过**——
> 实测 `test_protocols.py` 的其余 38 个用例全绿；**附加 D** 已用隔离 venv 的 mypy 实跑，见 §3.10）。

### 3.2 隔离环境安装（§2.1）—— **零第三方依赖**

```text
$ /tmp/fg-verify/bin/pip list
Package   Version
--------- -------
freegraph 0.0.3
pip       24.0
```

> **与期望一致**：装完 freegraph，site-packages 里**只有 freegraph 自己**（`pip` 是 venv 自带）。

### 3.3 G3 · 依赖闭包（§2.2）

```text
基础安装闭包: []
OK: 基础安装依赖闭包为空（零第三方运行时依赖）
```

### 3.4 SC-002 · 导入成功且耗时在预算内（§2.3）+ G1 惰性（§2.4）

```text
import OK
耗时 0.11 s / 0.10 s / 0.10 s（三次实测，墙钟含解释器冷启动）
OK: 在 300 ms 预算内

--- import freegraph ---
['freegraph']
--- import freegraph.contracts ---
['freegraph', 'freegraph.contracts', 'freegraph.contracts.errors', 'freegraph.contracts.graph', 'freegraph.contracts.protocols', 'freegraph.contracts.trace', 'freegraph.contracts.types']
```

> 契约层导入后**只加载契约层自身的子模块**，**不含任何内部层模块**（`freegraph.runtime` /
> `freegraph.graph` / `freegraph.persistence` / `freegraph.observability` 一个都不在清单里）。
> **公开符号面实测恰为 18 个**（隔离 venv 内 `len(freegraph.contracts.__all__)` = 18）。

### 3.5 静态门禁（§2.5）

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

> 每条均为 `OK:`，与期望一致。**G9 / G11 / G13 的完整判定见 `test_architecture.py`
> 的运行结果**（§3.1）——此处不重复粘贴。
> **G8 的判定口径与 `contracts/architecture-gates.md` G8 同口径**（逐符号**恰有一行** + 四列齐全 +
> 行内来源行号**只对「有上游同名符号」者**成立）；**既有 8 行按 FR-017 逐字不动**，其来源以矩阵章节的
> 「证据来源」小节为准 ⇒ **不**对既有 8 行断言行内行号。

### 3.6 冒烟：亲手用一遍协议与数据类（§3）

```text
isinstance TraceSink: True
isinstance Checkpointer: False
isinstance Store: False
节点名: ['a', 'b']
别名缺省同 id: b
条件边: True route
start s1 a
end   s1 2026-11-06T10:00:01+00:00
同 id: True | 开始快照的 end_time 仍为空: True
不可哈希: TypeError
查询: r1 None None None None
```

> **形态与次序**是判据；具体 repr / 时间串以实现为准。
> （`start` / `end` 两行出现在上表之前，是因为冒烟脚本里 `sink.on_span_start(s0)` 在
> 打印节点名**之前**执行——与 `quickstart.md` §3 的脚本顺序一致。）

### 3.7 附加 A · 多 Python 版本 × 零依赖 × 全量单测（可选）

```text
_未执行_（本机只装了 CPython 3.12.3；3.11 / 3.13 / 3.14 三档**未实测**——已记入 §7 遗留问题 7）
```

### 3.8 附加 B · 发行产物纯度 + wheel METADATA（可选）

```text
$ python3 harness/scripts/check_dist_purity.py
[纯度门禁] ✅ freegraph-0.0.3-py3-none-any.whl（wheel）——仅含包代码与必要元数据
[纯度门禁] ✅ freegraph-0.0.3.tar.gz（sdist）——仅含包代码与必要元数据

[纯度门禁] 2 个产物全部干净，可以发布。
```

> 复用仓库已有的 `dist/` 产物（本 feature **零**新增第三方依赖 ⇒ 依赖登记表不变）。

### 3.9 附加 C · 全量单测跑在**发行产物**上（可选）

```text
$ FREEGRAPH_TEST_INSTALLED=1 /tmp/fg-verify/bin/python -m pytest tests/contracts -q -rs
283 passed, 1 skipped in 1.96s
```

> **测的是发行产物而非源码树**（`FREEGRAPH_TEST_INSTALLED=1` ⇒ `conftest.py` 跳过 `src/` 注入）。
> 与 §3.1 的 **278 passed / 6 skipped** 相比：**多了 5 个用例**——正是 G3 依赖闭包门禁的
> 5 条断言（**本机未装 freegraph ⇒ 恒 skip**；隔离 venv 里**已安装** ⇒ 真跑通过）。
> 剩余的 1 个 skip 仍是 **mypy**（隔离 venv 未装 mypy）。

### 3.10 附加 D · mypy 静态类型检查（SC-004）

```text
$ MYPYPATH=src /tmp/mypy-venv/bin/python -m mypy --strict tests/contracts/fixtures/external_impl.py
Success: no issues found in 1 source file

$ MYPYPATH=src /tmp/mypy-venv/bin/python -m mypy --strict src/freegraph/contracts
Success: no issues found in 6 source files

$ /tmp/mypy-venv/bin/python -m mypy --version
mypy 2.4.1 (compiled: yes)
```

> **本机主环境未装 mypy** ⇒ `test_protocols.py` 的 SC-004 用例在本机 **`skip`**（原因已写明于
> §3.1）；本块用**隔离 venv 里的 mypy 2.4.1** 实跑 ⇒ **判据本身已实跑通过**。
> **协议一致性断言**（把三个夹具实现传给**形参标注为协议类型**的函数 ⇒ mypy 静态校验其可赋值性）
> 落在夹具的 `prove_conformance_with_concrete_implementations()`，由本块的 `--strict` 一并覆盖。

---

## 4. 结论

**已回填（2026-11-06 · 实现者单人串行推进）**。逐条对照 A1–A4（见下表）+ SC-001…SC-021 的关键项：

| 判据 | 结果 | 证据 |
|---|---|---|
| **A1 协议齐全**（5 协议 + 5 数据类全部存在且可导入 · SC-001） | ✅ 通过 | §3.1 / §3.6；隔离 venv 内 `len(__all__)` = **18** |
| **A2 契约层可被单独消费**（隔离环境导入无副作用 · 依赖闭包为空集 · SC-002） | ✅ 通过 | §3.2（`pip list` 只有 `freegraph`）/ §3.3（闭包 `[]`）/ §3.4（导入 **0.10–0.11 s** < 300 ms；`sys.modules` 只有契约层自身子模块） |
| **A3 ARCH-2 通过**（AST 断言零内部依赖、零 `langchain*` import · SC-003） | ✅ 通过 | §3.5（内部 import `[]`、第三方 import `[]`）+ §3.1（`test_architecture.py` 108 passed） |
| **A4 D11 已批准且三项修订全部落地**（C27 条目 / C23 字段约定 / C22 标识约定 · SC-005 / SC-006） | ✅ 通过 | `contracts/public-api.md` §2（C22 / C23 / C27 行）+ §3；机械核对：C27 → `TraceQuery` 5 字段；C23 → `Span` 11 字段含必带四项；C22 → `RunConfig` 四字段且**不含** `run_id` |
| 公开符号面**恰 18 个**（SC-001 / SC-017） | ✅ 通过 | §3.4（`__all__` = 18）；G7 两段断言（子集段 + 集合相等段）全绿 |
| 协议**纯抽象** + 结构化子类型判定可用（SC-007 / G10 / G11） | ✅ 通过 | §3.1（G10 / G11 断言）；缺方法变体逐个判**假** |
| 四个数据类**统一不可哈希** + 字段级相等（SC-019） | ✅ 通过 | §3.1（`test_graph.py` / `test_span.py`）+ §3.6（`不可哈希: TypeError`） |
| `Span` **不可变** + 结束收同 `id` 新实例 + 开始快照不被改写（SC-016） | ✅ 通过 | §3.6（同 id: True \| 开始快照的 end_time 仍为空: True）+ `test_span.py` 的 `replace` 断言 |
| `Span` / `TraceQuery` **100% 可 JSON 序列化**（SC-011） | ✅ 通过 | §3.1（`json.dumps(asdict(span))` 与 span 列表整体序列化两条断言） |
| 四份交付物已落盘且**权威唯一**（SC-020） | ✅ 通过 | §3.5（G12：权威清单文件数 = 1，指向 B2F1 的 `public-api.md`） |
| 兼容矩阵**逐符号**覆盖本层 10 个符号（SC-021） | ✅ 通过 | §3.5（G8：18 个符号逐个恰有一行、四列齐全、来源合规）+ `README.md` 的「API 兼容矩阵」章节 |
| 冻结对照表覆盖 **C1–C27 全 27 条**、遗漏 0（SC-006） | ✅ 通过 | `contracts/public-api.md` §2（已冻结 15 + 挂起 12 = 27；「修订」列 4 条独立标注）；与 Q8 §3.4 逐条对照**差异数 = 0** |

**关于「不适用」子项**（MUST 显式记一句，非忽略）：

- **原则 III**（`harness/demo/target.py` 原样可跑）—— 本 feature **不交付**公开门面与运行时，
  分别归 **B2F2** / **B7F3**；
- **原则 V 的「双跑」子项**（fake 模型 + 真实模型各跑一遍）—— 本 feature **无运行时、无模型调用**；
- **原则 II 的 C4 / C8 两条回归测试** —— 分别归 **B5F2** / **B8F1**；
- **G8 的逐符号兼容矩阵覆盖** —— 本 feature **已填入本层 10 行**（FR-017 / SC-021）；**全库**矩阵的补全与定稿归 **B24F1**；`THIRD_PARTY_NOTICES` 因零新增依赖**无需新增登记**
  （本 feature **零**新增第三方依赖 ⇒ `THIRD_PARTY_NOTICES` **无需新增登记**）。
- **附加 A（3.11 / 3.13 / 3.14 三档多版本实测）** —— 本机只装了 CPython **3.12.3**，
  **最低支持版本 3.11 的隔离实测未执行**（已记入 §7 遗留问题 7 ⇒ 归 **B3F1** 的 CI 矩阵）。

---

## 5. 冻结记录（SC-006 / SC-020 / FR-013）

> 本节内容 MUST 与 `specs/b2f1-contracts-protocols/contracts/public-api.md` 一致——
> **该文件是冻结面的唯一规范源**（并**取代** B1F1 的同名文件，后者作为历史快照保留）。
> **本记录是后续 30 个 feature 的唯一引用基准。**

### 5.1 公开符号面（恰 18 个）

见 `public-api.md` §0。**新增的 10 个**：

| # | 符号 | 表示形态 | 冻结要点 |
|---|---|---|---|
| 9 | `NodeFunc` | **协议**（`Protocol` + `runtime_checkable`，纯抽象） | `__call__(state: StateDict) -> StateDict \| Command \| None` |
| 10 | `Checkpointer` | **协议**（6 方法，纯抽象） | 方法集恰为六个；**方法名与参数名已冻结**（`config` / `thread_id`）；读写面承载检查点标识；载荷为纯数据；**返回类型与载荷形状挂起 B14F1** |
| 11 | `TraceSink` | **协议**（3 方法，纯抽象） | `current_span()` 无当前 span 时返回**空值**（不抛异常） |
| 12 | `Store` | **协议**（6 方法，纯抽象） | 按 (命名空间, 键) 寻址；**方法名与参数名已冻结**（`namespace` / `key` / `value` / `namespace_prefix` / `prefix` / `ops`，**逐字镜像上游 LangGraph 1.2.11**）；**v1 无实现**；载体形态挂起 v2 |
| 13 | `CompiledGraph` | **协议**（6 方法，纯抽象） | 返回类别已冻结；`get_state` 查不到返回**空值**；**参数名按 `data-model.md` §2.5 冻结为占位名**，行为细节挂起各实现 feature |
| 14 | `Graph` | **不可变类** | `nodes` / `edges` 为不可变元组 |
| 15 | `Node` | **不可变类** | `id`（节点名）/ `name`（别名，缺省归一为 `id`）/ `metadata` |
| 16 | `Edge` | **不可变类** | `source` / `target` / `conditional` / `condition`；**显式 `__hash__ = None`** |
| 17 | `Span` | **不可变类**（11 字段） | 必带四项 `thread_id` / `run_id` / `node` / `checkpoint_id`；`parent` 为标识字符串 |
| 18 | `TraceQuery` | **不可变类**（5 字段） | 全可空、可组合；全空 = 取全部 |

### 5.2 关键不变式

| 不变式 | 冻结内容 |
|---|---|
| 协议纯抽象 | 5 个协议的方法体**只有** `...`（G10） |
| 协议无继承链 | 用户**无需继承**即可满足协议（FR-007） |
| 数据类不可变 | 构造后字段不可改；映射字段浅拷贝 |
| 统一不可哈希 | `Node` / `Edge` / `Graph` / `Span` 不可哈希（`Edge` 显式 `__hash__ = None`）；`TraceQuery` 可哈希（有意如此） |
| span 生命周期 | 开始收「`end_time` 为空」实例 → 结束收**同 `id`、已填 `end_time` 的新实例**；按 `id` 配对；开始快照**不被事后改写** |
| 构造期校验 | **零值校验**——只做类型注解、缺省归一、容器浅拷贝 |
| JSON 可序列化 | `Span` / `TraceQuery` **100% 可 JSON 序列化**（C27 前提） |

### 5.3 移交后续 feature

见 `public-api.md` §5（16 条移交项）。**本 feature 的义务是「登记」，不是「改别人的文件」**——
兼容矩阵的**本层 10 行已在本 feature 补入**（全库补全与定稿归 **B24F1**）；`THIRD_PARTY_NOTICES` **无需新增登记**（零新增第三方依赖）。

---

## 6. 后续 feature 注意事项

> **本表 MUST 与 `specs/b2f1-contracts-protocols/contracts/public-api.md` §5 的 16 条逐条对齐**
> （编号可不同，**内容集合必须相同**；合并须显式标注）——§5.3 的「16 条移交项」即指此表。

| # | 事项 | 归属 | 性质 |
|---|---|---|---|
| 1 | 检查点载荷的**具体字段形状** | **B14F1** | `Checkpointer` 协议面已冻结；只细化载荷 |
| 2 | `Store` 命名空间**载体形态** + `batch` **操作表示** | **v2** | C20 仍冻结，v1 无实现 |
| 3 | `stream()` 的 **mode 枚举全集** | **B8F2** | `stream` 返回类别已冻结 |
| 4 | `CompiledGraph` 各方法的**行为细节与实现**（**参数名已冻结为占位名**） | **B7F3 / B8F2 / B15F1 / B16F1** | 返回类别与参数名已冻结 |
| 5 | 「存储与查询」协议的方法集 | **B20F1** | C27 数据面已冻结 |
| 6 | **span 的生产行为** | **B18F1** | `Span` 类型面以 `public-api.md` 为准 |
| 7 | `TraceSink` 接入 + `current_span()` 嵌套实现 | **B19F1** | 协议面已冻结 |
| 8 | 子图实现（C26） | **v2** | v1 只保 `get_graph(xray=)` 签名兼容 |
| 9 | `mermaid` 文本 / **PNG** 渲染 | **B22F1 / B23F1** | 消费本层的 `Graph` / `Edge` |
| 10 | 公开 API 门面 `freegraph/graph.py` | **B2F2** | 本 feature **不交付** |
| 11 | `README.md` **兼容矩阵**补本层 **10** 个新符号（**保持 4 列**；上游来源行号**写进该行的「差异说明」单元格末尾**——既有 8 行逐字不动 ⇒ 不可新增列；**有上游同名符号者附来源行号，无上游对应者写「无上游对应」+ 契约条目号**） | **B24F1**（全库补全与定稿） | **本 feature 已填入本层 10 行**（FR-017 / SC-021）；B24F1 只做全库总校对与定稿 |
| 12 | `THIRD_PARTY_NOTICES` 的补登 | **B24F1** | 本 feature **零**新增第三方依赖 ⇒ **无需新增登记**（依赖登记表不变） |
| 13 | 架构断言接入 CI 流水线 | **B3F1** | 本 feature 只交付 pytest 断言；CI 须**先装包**，否则 G3 恒 skip |
| 14 | `Send` / `interrupt` 的导出 | **v2**（B11F1 / B10F1） | 公开符号面严格 = 18 个 |
| 15 | **B18F1 提示词**交付物口径收窄为「span 生产行为」 | **B18F1** | 类型面以本 feature 为准 |
| 16 | **B22F1 提示词**的 `Graph` / `Node` / `Edge` 命名 | **B22F1** | **不变** |

---

## 7. 遗留问题

| # | 问题 | 性质 | 处理 |
|---|---|---|---|
| 1 | `NodeFunc` 的结构化子类型判定对**任意可调用对象恒为真** | `runtime_checkable` + `__call__` 的固有性质 | 记在案（`data-model.md` §2.1 / `architecture-gates.md` G11）；「合法节点函数」由**静态类型检查**判定 |
| 2 | `Checkpointer` / `Store` 的签名中仍有 `Any` 占位 | **已决策的挂起**（非未决） | 占位处逐个写明挂起归属；收紧属契约修订流程 |
| 3 | `TraceQuery` 可哈希而其余四类不可哈希 | 有意的差异 | 根因是「含映射字段」；记在案以免被当作疏漏 |
| 4 | G3 依赖闭包门禁在**未安装** freegraph 的本地环境恒 skip | 设计如此（需 dist-info 元数据） | 须在隔离环境**真实执行**（§3.3）；B3F1 接 CI 时**必须先装包** |
| 5 | SC-004 的 mypy 用例在本机未装 mypy 时 skip | mypy 是**开发期工具**（不进发行包） | 兜底的注解结构断言仍须通过；人工记录须标注 |
| 6 | G8 的逐符号兼容矩阵覆盖**在本 feature 启用** | 本 feature 已补本层 10 行 | 期望值从 `public-api.md` §0 解析（清单变更时断言自动跟随）；全库总校对归 **B24F1** |
| 7 | **最低支持版本 3.11 的隔离实测未执行** | 本机只装了 CPython **3.12.3**（`/usr/bin/python3.12`），无 3.11 解释器可用 | 记在案，**不伪造**输出；由 **B3F1** 的 CI 矩阵（最低档 3.11）补齐——本 feature 的代码只用了 ≤ 3.11 的 typing 构件（`Protocol` / `runtime_checkable` / `dataclass` / `Mapping` / `Sequence` / `Iterator`），G9 已静态断言 |
| 8 | `Edge` / `Graph` 的 `__hash__ = None` 需带 `# type: ignore[assignment]` | mypy 对 `__hash__ = None` 的既有误报（`object.__hash__` 声明为 `Callable[[], int]`） | 已用 `type: ignore` 消解（`--strict` 下契约层 6 个源文件 `Success: no issues found`）；**不影响**运行时语义（dataclass 的 `_hash_action` 对显式 `__hash__` 不覆盖） |

---

## 8. 变更记录（如有）

_本 feature 实现期间若有口径变更，在此逐条记录「变更了什么 / 为什么 / 受影响的类型与特性 /
迁移方案」，并同步更新 `contracts/public-api.md`——**不得就地改型**（宪法 §Governance）。_
