# B1F1 · 契约层骨架 —— 人工验证记录

**feature**: B1F1（契约层骨架：四个核心类型 + 异常体系）
**验收依据**: `specs/b1f1-contracts-core/spec.md` · `plan.md` · `tasks.md`
**验收指南**: [`specs/b1f1-contracts-core/quickstart.md`](../../../specs/b1f1-contracts-core/quickstart.md)
**记录日期**: 2026-11-05
**记录人**: 实现者（单人串行推进 · 立项书 §5.2）

> **📌 术语与编号对照**：本记录写于「F1P1」时代。2026-11-05 全仓库统一术语（宪法 **v1.4.0**）：
> **Phase → feature**（最小开发单位 = speckit 一次闭环）、**Feature → 功能块**（`B<n>`）、
> **域 → 领域**（`A<n>`）。故本 feature 的旧编号 `F1P1` 现为 **`B1F1`**
> （`specs/b1f1-contracts-core/`）。**本记录的实测内容与结论不受影响。**
>
> **⚠️ 本记录含一次「实施期变更」的完整记录**：B1F1 实现期间，发起者复核依赖策略时
> 指出「依赖 `typing-extensions` 令人不爽」→ 评估后**剥离该依赖**并把**最低 Python
> 版本抬至 3.11**（依据：宪法修订记录 **v1.2.0** · `research.md` **D-21** ·
> spec Clarifications「Session 2026-11-05（实现阶段 · 依赖剥离与最低版本上调）」）。
> 本记录的第 3 节是**变更后的**实测输出；变更前的记录见第 8 节「变更前的验收记录（存档）」。

---

## 1. 环境

| 项 | 实际值 |
|---|---|
| 本机 Python | 3.12.3（CPython） |
| 隔离 venv Python | **3.11.16**（CPython）—— 最低支持版本 |
| 平台 | Linux 6.8.0-139-generic x86_64 / `linux` |
| freegraph 版本 | **0.0.3**（`pyproject.toml` 的 `version`） |
| pytest 版本 | 7.4.4 |
| `requires-python` | **`>=3.11`** |
| 基础安装的包清单 | **`['freegraph']`** —— **零第三方运行时依赖**（实测，4 个 Python 版本一致） |
| 依赖闭包许可证 | 基础安装闭包为**空集** ⇒ 许可证白名单校验**恒通过** |

> **多版本实测**：CPython **3.11.16 / 3.12.3 / 3.13.15 / 3.14.7** 上
> 各建一个**裸 venv**（先只装 freegraph），四个环境的 site-packages 清单
> **均为 `['freegraph']`**，且**全量单测均 129 passed**（见 §3.7）。

---

## 2. 步骤

照 `quickstart.md` 第 1–3 节执行：

| 步 | 命令 | 对应判据 |
|---|---|---|
| 1.1 | `python3 -m pytest tests/contracts -q` | FR-010 / SC-007 · 九条门禁断言 |
| 1.2 | `python3 -m pytest tests/contracts/test_types.py -q` | SC-004 |
| 1.3 | `python3 -m pytest tests/contracts/test_errors.py -q` | SC-005 |
| 1.4 | `python3 -m pytest tests/contracts/test_architecture.py -q` | SC-002 / SC-003 / SC-006 / SC-007 |
| 2.1 | 建 venv（3.11）→ `pip install .` | SC-001 · **零依赖** |
| 2.2 | 依赖闭包脚本（`importlib.metadata.requires` 递归展开） | SC-002 · G3 |
| 2.3 | `import freegraph.contracts` + 导入耗时脚本 | SC-001（< 300 ms） |
| 2.4 | 两条 `sys.modules` 清单 | SC-006 · G1 |
| 2.5 | 静态门禁脚本（G2 / G4 / G5 / G6 / G7 / G8） | SC-003 / SC-007 |
| 3 | 冒烟脚本（亲手用一遍四个类型） | US1 / US2 验收场景 |
| 附加 A | **4 个 Python 版本**（3.11 / 3.12 / 3.13 / 3.14）各建裸 venv 装包 + 全量单测 | 最低版本下限 · 零依赖 |
| 附加 B | 发行产物纯度门禁 + wheel METADATA 复核 | 发布门禁 · §9.1 门禁 7 |
| 附加 C | `FREEGRAPH_TEST_INSTALLED=1` 下跑全量单测（**测发行产物**而非源码树） | B3F1 CI 前置 |

---

## 3. 实际输出

> 以下全部是**真实输出**（非「符合预期」）。

### 3.1 本地单测（源码树，免安装，Python 3.12）

```text
$ python3 -m pytest tests/contracts -q
.........................................................                [100%]
124 passed, 5 skipped in 0.82s
```

- **5 个 skip 的含义**：`test_architecture.py` 的 **G3 依赖闭包**用例——
  本机 freegraph **未安装**（无 dist-info 元数据），该门禁 MUST `skip` 而非失败。
  它在隔离环境里**实测执行并通过**（见 §3.7）。

分文件：

```text
$ python3 -m pytest tests/contracts/test_types.py -q
..............................................................             [100%]
62 passed in 0.20s

$ python3 -m pytest tests/contracts/test_errors.py -q
...................                                                       [100%]
19 passed in 0.09s

$ python3 -m pytest tests/contracts/test_architecture.py -q -rs
=========================== short test summary info ============================
SKIPPED [5] tests/contracts/test_architecture.py:486: freegraph 未安装（无 dist-info 元数据）——依赖闭包门禁须在隔离环境执行（见 quickstart.md §2.2 / T023）
43 passed, 5 skipped in 0.61s
```

### 3.2 隔离环境安装（§2.1）—— **零第三方依赖**

```text
$ uv venv --python 3.11 /tmp/fg-verify
$ uv pip install --python /tmp/fg-verify .

  安装后的包清单： ['freegraph']
  （pytest 是验收工具，非 freegraph 的运行时依赖）
```

**与期望一致**：装完 freegraph，site-packages 里**只有 freegraph 自己**。

> 对照变更前：此前为 `Successfully installed freegraph-0.0.2 typing-extensions-4.16.0`
> ——**两个包**。现在是**一个**。

### 3.3 G3 · 依赖闭包（§2.2）

```text
基础安装闭包: []
OK: 基础安装依赖闭包为空（零第三方运行时依赖）
extras 闭包: []
OK: extras 闭包均在宪法依赖白名单内
```

**与期望输出一致**（期望输出已同步改为空集）。

### 3.4 SC-001 · 导入成功且耗时在预算内（§2.3）+ G1 惰性（§2.4）

```text
--- 2.3 import OK ---
import OK

--- 2.3 timing ---
耗时 154 ms  退出码 0
OK: 在 300 ms 预算内

--- 2.4 sys.modules ---
--- import freegraph ---
['freegraph']
--- import freegraph.contracts ---
['freegraph', 'freegraph.contracts', 'freegraph.contracts.errors', 'freegraph.contracts.types']
```

**与期望输出一致**：耗时 154 ms < 300 ms 预算；`import freegraph` 后清单**恰为**
`['freegraph']`；`import freegraph.contracts` 后**不含任何内部层模块**
（契约层自身的 `types` / `errors` 子模块不受限）。

### 3.5 静态门禁（§2.5）

```text
=== G2 · 契约层零内部 import ===
内部 import: []
OK: 契约层零内部 import

=== G4 · 零环境变量 / 零出站（文本粗筛）===
OK: 未发现环境变量读取或网络访问

=== G5 · 署名头 ===
OK 署名头: src/freegraph/contracts/errors.py
OK 署名头: src/freegraph/contracts/__init__.py
OK 署名头: src/freegraph/contracts/types.py

=== G6 · py.typed ===
OK: py.typed 存在且为空

=== G7 · 公开符号面恰 8 个 ===
OK: 公开符号面恰为 8 个

=== G8 · 文档合规门禁 ===
OK: THIRD_PARTY_NOTICES 存在
OK: 兼容矩阵覆盖全部 8 个公开符号
```

**每条均为 `OK:`**，与期望一致。

### 3.6 冒烟：亲手用一遍四个类型（§3）

```text
cfg: RunConfig(thread_id='t-1', context=None, metadata={}, tags=('demo',))
未知键被拒: Unknown key(s) for RunConfig: 'threadId'. Valid keys are: context, metadata, tags, thread_id. Pass ignore_unknown=True to ignore unknown keys.
跳转: Command(goto='review', update=None, resume=None)
跳转+写入: Command(goto=('a', 'b'), update={'n': 1}, resume=None)
跳向父图: Command(goto='__parent__', update=None, resume=None)
空命令被拒: Command requires at least one of 'goto', 'update' or 'resume' to be provided.
快照: StateSnapshot(values={'messages': ['hi']}, next=(), config=RunConfig(thread_id='t-1', context=None, metadata={}, tags=('demo',)), metadata={}, created_at='2026-11-05T10:20:30.123456+00:00', tasks=(), interrupts=())
InvalidUpdateError → Invalid state update: unknown key(s) 'typo'
GraphRecursionError → Graph recursion limit exceeded: recursion_limit=25, current_step=25
GraphInterrupt → Graph execution interrupted with payload <__main__.P object at 0x75347cd5add0>
```

**形态与期望一致**（具体 repr / 消息措辞以实现为准）。

### 3.7 附加 A · 四个 Python 版本 × 零依赖 × 全量单测

```text
───── Python 3.11 ─────
  Python: 3.11.16 | site-packages: ['freegraph']
  ✅ 零第三方依赖
129 passed in 0.89s
───── Python 3.12 ─────
  Python: 3.12.3 | site-packages: ['freegraph']
  ✅ 零第三方依赖
129 passed in 1.00s
───── Python 3.13 ─────
  Python: 3.13.15 | site-packages: ['freegraph']
  ✅ 零第三方依赖
129 passed in 1.06s
───── Python 3.14 ─────
  Python: 3.14.7 | site-packages: ['freegraph']
  ✅ 零第三方依赖
129 passed in 1.23s
```

> **四个版本全部**：site-packages **只有 `freegraph` 自己**、**129 passed**。
> 与本地源码树的差异（124 vs 129）来自 **5 条 G3 用例在装包环境中由 skip 转为真跑并通过**。

### 3.8 附加 B · 发行产物纯度门禁 + wheel METADATA

```text
Successfully built freegraph-0.0.3.tar.gz and freegraph-0.0.3-py3-none-any.whl
[纯度门禁] 2 个产物全部干净，可以发布。

  --- wheel METADATA 关键字段 ---
    License-Expression: MIT
    License-File: LICENSE
    Classifier: Programming Language :: Python :: 3
    Classifier: Programming Language :: Python :: 3.11
    Classifier: Programming Language :: Python :: 3.12
    Classifier: Programming Language :: Python :: 3.13
    Classifier: Programming Language :: Python :: 3.14
    Requires-Python: >=3.11
    License: MIT
```

> **wheel METADATA 中**没有任何 `Requires-Dist` 行** —— 基础安装**零第三方依赖**
> 已落到**发行元数据**层面，不只是源码声明层面。
> `License-Expression: MIT` 不变（剥离依赖不改变本项目自身的许可证）。

### 3.9 附加 C · 全量单测跑在**发行产物**上（`FREEGRAPH_TEST_INSTALLED=1`）

```text
$ FREEGRAPH_TEST_INSTALLED=1 /tmp/fg-verify/bin/python -m pytest tests/contracts -q
129 passed in 0.88s
```

> 确认测试命中的是 **site-packages 里的发行产物**，而非源码树——
> 这正是 B3F1 的 CI 口径所需（`conftest.py` 的环境变量开关已就位）。

---

## 4. 结论

**通过。** B1F1 的全部验收判据（A1–A5）与**九条**架构门禁（G1–G9）均已实测通过，
**且在剥离 `typing-extensions`、最低版本抬至 3.11 之后仍然通过**。

| 判据 | 结果 | 证据 |
|---|---|---|
| A1 `import freegraph.contracts` 成功 | ✅ | §3.4（`import OK`，耗时 154 ms < 300 ms） |
| A2 依赖**零**（闭包为空集） | ✅ | §3.3（基础安装闭包 = `[]`）+ §3.7（4 个版本的 site-packages 均只有 `freegraph`）+ §3.8（wheel 无 `Requires-Dist`） |
| A3 C1/C11/C16/C22 类型冻结 | ✅ | §3.6 + 本文第 5 节「类型冻结记录」 |
| A4 契约层不 import 任何内部模块 | ✅ | §3.5（G2）+ 门禁自检（故意造违规目录，门禁**确实报出**） |
| A5 顶层包惰性 | ✅ | §3.4（`import freegraph` → `['freegraph']`） |
| SC-007 署名头 100% | ✅ | §3.5（G5）+ 单测 `test_signature_header`（8 个文件逐一断言首行逐字相等） |
| **最低版本下限** | ✅ | §3.7（3.11 / 3.12 / 3.13 / 3.14 **四个版本**全绿） |
| **G9 运行时环境基线**（typing 构件上限 = 3.11，宪法 v1.3.0） | ✅ | §3.10 —— 3.11 与 3.12 双版本各 138 passed；门禁自检覆盖 8 类违规；并**实证**同一段 3.12+ 代码在 3.12 上可用、在 3.11 上 `ImportError` |

**关于原则 V 的「双跑」子项**：**本 feature 不适用**——契约层**无运行时、无模型调用**，
故不存在「fake 模型 + 真实模型各跑一遍」的验收对象。此处**显式记录为不适用**，
**非忽略**：原则 II 的 C4（稀疏状态）与 C8（条件边读 fresh 状态）两条回归测试子项
分别归 **B5F2** / **B8F1**；原则 III 的 `harness/demo/target.py` 验收契约归 **B2F2**（门面）
与 **B7F3**（运行时）——本 feature **不修改** `target.py`，不得为凑该门禁而提前交付门面。

---

### 3.10 G9 · 运行时环境基线（typing 构件上限 = 3.11 · 宪法 v1.3.0）

```text
$ python3 -m pytest tests/contracts -q          # 3.12
138 passed, 5 skipped in 0.74s

$ /tmp/fg311/bin/python -m pytest tests/contracts -q   # 3.11（主判定环境）
138 passed, 5 skipped in 0.69s
```

**门禁自检**（8 类违规逐一验证 + 1 类不误报）：

| 违规类型 | 是否被抓出 |
|---|---|
| `from typing import TypeAliasType` | ✅ |
| `from typing import ReadOnly` | ✅ |
| `from typing import TypeIs` | ✅ |
| `from typing import override` | ✅ |
| `typing.TypeAliasType` 属性引用 | ✅ |
| `@override` 装饰器用法 | ✅ |
| `type Alias = int`（PEP 695 `type` 语句） | ✅ |
| `class C[T]`（PEP 695 泛型类） | ✅ |
| **不误报**：`Self` / `NotRequired` / `TypeVarTuple` / `Unpack` / `LiteralString` / `dataclass_transform` / 叫 `override` 的**普通方法名** | ✅ 全部不报 |

**端到端实证**（临时注入 `from typing import TypeAliasType` 到真实源码）：

```text
E  AssertionError: types.py:18: 禁用了 TypeAliasType（3.12 才进标准库）
E  AssertionError: types.py:212: 禁用了 TypeAliasType（3.12 才进标准库）
1 failed, 3 passed
```

**主判定的有效性实证**（同一段代码，两个解释器）：

```text
$ python3 probe312.py              # 3.12
3.12 上: Alias

$ /tmp/fg311/bin/python probe312.py  # 3.11
    from typing import TypeAliasType
ImportError: cannot import name 'TypeAliasType' from 'typing'
```

> 即：**CI 最低档跑 3.11 这件事本身就是一道有效门禁**——
> 任何 3.12+ / 3.13+ 构件都会在该档直接崩掉。G9 静态断言的作用是
> **把报错变成一句人话**（指明「你用了 3.12+ 的 X」），而不是让开发者
> 对着 `ImportError` 猜原因。

---

## 5. 类型冻结记录（SC-008）

> 本节内容 MUST 与 `specs/b1f1-contracts-core/contracts/public-api.md`
> 的「冻结面速查」一致——**该文件是冻结面的唯一规范源**。
> **本记录是后续 30 个 feature 的唯一引用基准。**
>
> **⚠️ 依赖剥离与最低版本上调**（2026-11-05）**未触及**本记录的任何一行**——
> 8 个符号、字段清单、字段类型、结构化属性名、常量值、表示形态、行为**全部不变**；
> 变的只是**依赖声明**与**解释器版本下限**。

### 5.1 公开符号面（恰好 8 个）

| # | 符号 | 表示形态 | 冻结要点 |
|---|---|---|---|
| 1 | `StateDict` | **类型别名**（`TypeAlias`） | `StateDict == dict[str, Any]`；**不支持**参数化；需字段补全者改用自己的 `TypedDict` |
| 2 | `Command` | **不可变类**（`@dataclass(frozen=True, slots=True, kw_only=True)`） | 三语义位 `goto` / `update` / `resume`；类级常量 `PARENT` |
| 3 | `StateSnapshot` | **不可变类**（同上） | 七字段全必填 |
| 4 | `RunConfig` | **不可变类**（同上） | 四字段全可选；`from_dict` 裸 dict 构造路径 |
| 5 | `FreegraphError` | **异常基类**（直接继承 `Exception`，不自定义 `__init__`） | 基类名**不得再改**；后续可**新增**子类 |
| 6 | `InvalidUpdateError` | **异常子类**（派生自 `FreegraphError`） | 结构化属性 `invalid_keys` |
| 7 | `GraphRecursionError` | **异常子类**（派生自 `FreegraphError`） | 结构化属性 `recursion_limit` / `current_step` |
| 8 | `GraphInterrupt` | **异常子类**（派生自 `FreegraphError`） | 结构化属性 `payload` |

### 5.2 字段清单与字段类型

| 类型 | 字段 | 类型 | 缺省 | 说明 |
|---|---|---|---|---|
| `Command` | `goto` | `str \| Sequence[str] \| None` | `None` | 单个 = 节点名；一组 = 任意序列；**不归一化** |
| | `update` | `StateDict \| None` | `None` | 部分状态更新 |
| | `resume` | `Any \| None` | `None` | 恢复值 |
| `StateSnapshot` | `values` | `StateDict` | —（必填） | 该时刻的完整状态（稀疏映射） |
| | `next` | `tuple[str, ...]` | —（必填） | 本步之后要执行的节点名；空元组 = 无后续 |
| | `config` | `RunConfig` | —（必填） | 取回该快照所用的运行配置 |
| | `metadata` | `Mapping[str, Any]` | —（必填） | 附加信息（只读映射） |
| | `created_at` | `str` | —（必填） | UTC 的 ISO-8601 字符串 |
| | `tasks` | `tuple[Any, ...]` | —（必填） | 本步任务列表（元素类型归 B2F1） |
| | `interrupts` | `tuple[Any, ...]` | —（必填） | 本步发生的中断（元素类型归 B2F1） |
| `RunConfig` | `thread_id` | `str \| None` | `None` | **会话**标识（用户可指定） |
| | `context` | `Any` | `None` | 运行时上下文——**独立通道**（C21） |
| | `metadata` | `Mapping[str, Any]` | 空映射 | 附加信息，**不参与标识** |
| | `tags` | `Sequence[str]` | 空序列 | 附加标签，**不参与标识** |

### 5.3 结构化属性名

| 类 | 属性 | 类型 | 含义 |
|---|---|---|---|
| `InvalidUpdateError` | `invalid_keys` | `tuple[str, ...]` | 状态 schema 中**不存在**的 key 列表（顺序保持） |
| `GraphRecursionError` | `recursion_limit` | `int` | 递归上限 |
| | `current_step` | `int` | 已达步数 |
| `GraphInterrupt` | `payload` | 本 feature `Any` | 中断载荷**对象**（按 C17 带 `.value` 与 `.id`） |

### 5.4 常量值

| 常量 | 值 | 形态 | 语义 |
|---|---|---|---|
| `Command.PARENT` | `"__parent__"` | `ClassVar[Literal["__parent__"]]` | 「跳向最近的父图」；节点名 `__parent__` 为**保留名** |

### 5.5 冻结的行为

| 行为 | 冻结内容 |
|---|---|
| `Command()` | **必抛** `FreegraphError`（三语义位全空）；三语义位**可任意组合** |
| `RunConfig.from_dict(d)` | **默认严格**：出现四字段之外的键 → 抛 `FreegraphError` 且**点名该键**；`ignore_unknown=True` → 忽略未知键 |
| 异常摘要 | **英文**且**点名关键值**（如未知 key）；`message="..."` 可覆盖 |
| 构造期校验 | **仅两条**（`Command()` 三全空、`from_dict` 未知键）；其余**只做类型注解、不校验值** |
| 容器拷贝 | `StateSnapshot.metadata` 拷贝；`RunConfig.metadata` + `RunConfig.tags` 拷贝（均为**浅拷贝**） |
| `metadata` / `tags` | 一律声明为 `Mapping[str, Any]` / `Sequence[str]`（只读映射 / 序列） |

### 5.6 移交后续 feature 的边界

- **不属于冻结面**：`tasks` / `interrupts` / `payload` 的**元素类型**（归 B2F1；
  细化时**不改动字段注解本身**）、额外的便利方法（如 `to_dict()`）。
- **字段的注解本身已冻结**：B4F1 / B8F3 只能**新增字段**、**不得改动已有字段的注解**。

---

## 6. 后续 feature 注意事项

| # | 事项 | 归属 | 性质 |
|---|---|---|---|
| 1 | `GraphInterrupt.payload` 的**具体元素类型** | **B2F1** | 属性名 `payload` 与载荷结构（`.value` / `.id`）**已冻结，不得改动**；只收紧**类型注解** |
| 2 | `RunConfig` 四字段与 `StateSnapshot` 七字段的**字段注解已随字段一并冻结** | B4F1 / B8F3 | 只能**新增字段**、**不得改动已有字段的注解** |
| 3 | `tasks` / `interrupts` 的**元素类型** | **B2F1** | 属「元素类型」而非「字段注解」，与第 2 条不冲突 |
| 4 | 节点名 `__parent__` 属**保留名**，运行时校验 | B7F2 / B9F1 | 本 feature 只冻结「该名字属保留名」这一约定 |
| 5 | `invoke` 入口「容忍裸 dict」行为 | **B7F3** | 本 feature 只冻结 `RunConfig.from_dict` 提供了构造路径 |
| 6 | 架构断言接入 CI 流水线 | **B3F1** | 本 feature 只交付 pytest 断言，不动 `.github/workflows/`；CI 须**先装包**，否则 G3 恒 skip |
| 7 | 兼容矩阵与 `THIRD_PARTY_NOTICES` 的**补全与定稿** | **B24F1** | **建立与本层填写**已在本 feature 完成 |
| 8 | `Send` / `interrupt` 的导出 | **B2F1** | 本 feature **不导出**（公开符号面严格 = 8 个） |
| 9 | 公开 API 门面 `freegraph/graph.py` | **B2F2** | 本 feature **不交付** |
| 10 | **最低 Python 版本 3.11**（CI 矩阵最低档、隔离验收环境档位） | **B3F1 / B24F1** | 宪法 v1.2.0 · `research.md` D-21——CI 矩阵最低档由 3.10 改 3.11、最高档由 3.13 改 3.14 |
| 11 | **不得**再引入 `typing_extensions` | **全局** | 已剥离；3.11 起 `Self` / `NotRequired` / `Required` / `TypeVarTuple` / `Unpack` / `LiteralString` / `dataclass_transform` 均在标准库内 |
| 12 | `extras` 划分与 `[pydantic]` / `[checkpoint]` / `[otel]` / `[png]` | **B3F1** | 本 feature **无** extras；extras 闭包另按宪法依赖白名单校验（{pydantic, ormsgpack, opentelemetry-api, opentelemetry-sdk}） |
| 13 | 姊妹项目 `freechain` 的依赖链随之变化（不再有 `typing-extensions`） | **freechain 仓库** | 本仓库**不代改**；已在 `harness/proposals/更名与迁移说明.md` 注明 |
| 14 | **typing 构件上限 = 3.11**（禁用 `TypeAliasType` / `override` / `ReadOnly` / `TypeIs` / PEP 695 语法） | **全局** | 宪法 v1.3.0「运行时环境基线」· 门禁 **G9**；CI 最低档 MUST 为 3.11 且跑全量测试 |

---

## 7. 遗留问题

| # | 问题 | 性质 | 处理 |
|---|---|---|---|
| 1 | 兼容面比上游 LangGraph（3.10+）**窄一档** | 有意的取舍 | 已记入宪法 v1.2.0 的「代价」栏；理由：3.10 已于 2026-10 EOL、3.11 的 typing 增量 / 兼容面比最佳。若将来需要回到 3.10，闭合办法见 `research.md` D-21（`Self` → `TypeVar` bound 惯用法等） |
| 2 | `Command(resume=None)` 与「恢复值恰为 `None`」不可区分 | 冻结注解的已知限制（`resume: Any \| None = None`） | 记在案；若将来需区分，须走**契约修订**流程（说明变更了什么 / 为什么 / 受影响的类型与特性 / 迁移方案），并同步更新 `public-api.md` 的冻结面速查，**不得就地改型** |
| 3 | `StateSnapshot.metadata` 传 `None` 会在构造期抛 `TypeError` | 防御性拷贝的**副作用**（非主动校验） | 已记入 spec Edge Cases；调用方须自行保证传入合法值 |
| 4 | G3 依赖闭包门禁在**未安装** freegraph 的本地环境恒 skip | 设计如此（需 dist-info 元数据） | 已在 §3.7 证明其在隔离环境**真实生效**；B3F1 接 CI 时**必须先装包** |
| 5 | 架构门禁目前只覆盖**契约层** | 范围限定 | 全仓库范围的同类扫描归 B3F1 的 CI 门禁 |
| 6 | 已发布的 **v0.0.2** 仍带 `Requires-Dist: typing-extensions>=4.7.0` / `Requires-Python: >=3.10` | **历史事实，不予改写** | 下一次发布（**v0.0.3**）起为 `Requires-Dist` 无 / `Requires-Python: >=3.11`；已在宪法与 `更名与迁移说明.md` 注明 |
| 7 | 「typing 构件上限 = 3.11」此前**只存在于文档**，代码层面无约束 | 已由宪法 v1.3.0 + 门禁 G9 闭合 | 开发者若在 3.12/3.13 机器上写码，会不知不觉用上 `TypeAliasType` / `override` 等，把「3.11 是下限」在**代码里**破掉——而这种破坏**不会在开发机上暴露**，只在用户装包时才炸 |

---

## 8. 变更前的验收记录（存档）

> 以下是**剥离 `typing-extensions` 之前**（v0.0.2 · 最低 3.10 · 带 `typing-extensions`）
> 的实测输出，**仅作存档对照**——它**不代表当前状态**。
> 当时的结论是「通过」，但其「A2 依赖仅 `typing-extensions`」一条现已被
> **更强**的判据取代：「A2 依赖**零**（闭包为空集）」。

```text
$ python3 -m pytest tests/contracts -q
122 passed, 4 skipped in 0.70s

$ /tmp/fg-verify/bin/pip install .
Successfully installed freegraph-0.0.2 typing-extensions-4.16.0

基础安装闭包: ['typing-extensions']
OK: 基础安装依赖闭包只有 typing-extensions
extras 闭包: []
OK: extras 闭包均在宪法依赖白名单内

耗时 111 ms  退出码 0
OK: 在 300 ms 预算内

--- import freegraph ---
['freegraph']
--- import freegraph.contracts ---
['freegraph', 'freegraph.contracts', 'freegraph.contracts.errors', 'freegraph.contracts.types']
```

**当时的一处文档笔误**（本次已一并更正）：`THIRD_PARTY_NOTICES` §2 原将
`typing-extensions` 的许可证记为 **MIT**；隔离环境实测其发行元数据为
`License-Expression: PSF-2.0`。该包现已**整体剥离**，§2 登记表清空，
故该笔误**不再适用**——但记录在此以留痕。
