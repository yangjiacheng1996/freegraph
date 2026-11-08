<!-- authority: yes -->

# 契约：二元性判据的**权威判定表**（B4F1）

**功能块**: B4F1 · 状态 schema 解析 + 归约器提取 · **Date**: 2026-11-08
**权威来源**: [spec.md](../spec.md)（FR-003 / FR-004 / FR-016 ①-a·①-b · 裁定 9 · 澄清 **Q6** / **Q9**）·
[plan.md](../plan.md)（research D-03 · D-09）· [research.md](../research.md)（D-03 / D-09 / D-10）
**上游参照**: `langgraph/graph/state.py`（**核实环境 `langgraph 1.2.11`** · 实测于 CPython 3.12.3）

> **📌 本文件是判据的**唯一权威**（`<!-- authority: yes -->`）**：
> 测试**解析本表的 Markdown 表格**取样比对（沿用既有门禁 **G25** 解析
> `contracts/layer-registry.md` 的同构手法 · research D-03）
> ⇒ **判据与用例天然分离**：改本表必然改测试同提交可见（杜绝「改判据顺手改断言」的自证）。
> ⇒ 本文件**不进发行包**（在 `specs/` 下）⇒ 不污染发行产物纯度。
>
> **📌 唯一权威的边界（2026-11-08 分析轮补记）**：**判定权威只在本文件 §2** ——
> `spec.md` FR-016 ①-a **只列形态清单 + 指向本文件**，**不复制表格** ⇒ 仓库内**只有一份判定表**；
> 本文 §5 的**实测取样表**是 §2 的**证据镜像**（判定权威只在 §2）。

---

## 1. 判据口径（逐字冻结 · FR-004）

> **候选**：末位元数据元素是 **callable**（**类**与**可调用对象实例**都**不**特殊排除 · 澄清 Q6）。
> **计数**：位置专用（`POSITIONAL_ONLY`）**+** 位置或关键字（`POSITIONAL_OR_KEYWORD`）**== 2**；
> **可变位置（`*args`）· 可变关键字（`**kwargs`）· 仅关键字（keyword-only）一律不计入**。
> **签名取不到**（`inspect.signature` 抛 `ValueError` / `TypeError`）⇒ 判为**非二元** ⇒ **拒绝**。

上游对应实现（`langgraph/graph/state.py:1904-1922` · 核实环境 `langgraph 1.2.11`）：

```python
def _is_field_binop(typ: type[Any]) -> BinaryOperatorAggregate | None:
    if hasattr(typ, "__metadata__"):
        meta = typ.__metadata__
        if len(meta) >= 1 and callable(meta[-1]):
            sig = signature(meta[-1])
            params = list(sig.parameters.values())
            if (
                sum(
                    p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
                    for p in params
                )
                == 2
            ):
                return BinaryOperatorAggregate(typ, meta[-1])
            else:
                raise ValueError(
                    f"Invalid reducer signature. Expected (a, b) -> c. Got {sig}"
                )
    return None
```

> **📌 与上游的差异只有一处**：上游在「末位可调用但非二元」时抛 **`ValueError`**；
> freegraph 抛 **`InvalidSchemaError`**（**继承 `FreegraphError` + `ValueError`** · 裁定 2）
> ⇒ **判定结果（接受 / 拒绝）逐条一致**（本表即该一致性的固化快照），
> **异常类型不同**（spec FR-016 明确「异常类型不要求逐字相同」）。

---

## 2. 判定表 · A —— 二元性判定形态（**16 类** · FR-016 ①-a）

**表列约定**（供测试解析）：

| 列 | 含义 |
|---|---|
| `#` | 序号（连续 · 缺失即判失败） |
| `形态` | 人类可读的形态描述 |
| `输入` | **Python 表达式**（在测试夹具的命名空间中可求值 · 取自 §4 的夹具清单） |
| `期望` | `接受`（判为二元归约器）**或** `拒绝`（判为非二元 ⇒ 抛 `InvalidSchemaError`） |
| `上游` | 上游来源 `路径:行号`（**核实环境 `langgraph 1.2.11`**） |

| # | 形态 | 输入 | 期望 | 上游 |
|---|---|---|---|---|
| 1 | 位置专用 2 参（内置函数） | `operator.add` | 接受 | `langgraph/graph/state.py:1908-1916` |
| 2 | 位置或关键字 2 参 | `two_positional` | 接受 | `langgraph/graph/state.py:1910-1916` |
| 3 | 3 个位置参数 | `three_positional` | 拒绝 | `langgraph/graph/state.py:1918-1921` |
| 4 | 1 个位置参数 | `one_positional` | 拒绝 | `langgraph/graph/state.py:1918-1921` |
| 5 | 1 位置参 + `*args` | `one_positional_varargs` | 拒绝 | `langgraph/graph/state.py:1910-1916` |
| 6 | 2 位置参 + `*args` | `two_positional_varargs` | 接受 | `langgraph/graph/state.py:1910-1916` |
| 7 | 2 位置参 + keyword-only | `two_positional_kwonly` | 接受 | `langgraph/graph/state.py:1910-1916` |
| 8 | 仅关键字（0 位置参） | `kwonly_only` | 拒绝 | `langgraph/graph/state.py:1918-1921` |
| 9 | 类 · `__init__` 无参 | `ClassNoInit` | 拒绝 | `langgraph/graph/state.py:1908-1921` |
| 10 | 类 · `__init__(self, a)` | `ClassOneArgInit` | 拒绝 | `langgraph/graph/state.py:1918-1921` |
| 11 | 类 · `__init__(self, a, b)` | `ClassTwoArgInit` | 接受 | `langgraph/graph/state.py:1910-1916` |
| 12 | 可调用实例 · `__call__(self, a, b)` | `CallableInstance` | 接受 | `langgraph/graph/state.py:1910-1916` |
| 13 | 可调用实例 · `__call__(self, *, a, b)` | `CallableKwOnlyInstance` | 拒绝 | `langgraph/graph/state.py:1918-1921` |
| 14 | `functools.partial(add, 1)` | `partial_add_one` | 拒绝 | `langgraph/graph/state.py:1910-1921` |
| 15 | 绑定方法（`self` 已绑定） | `bound_method` | 拒绝 | `langgraph/graph/state.py:1910-1921` |
| 16 | 内置类型（签名不可取） | `str` | 拒绝 | `langgraph/graph/state.py:1908`（`signature()` 抛 `ValueError`） |

> **📌 第 11 行的重要后果（澄清 Q6 的裁定）**：`ClassTwoArgInit` 的 `signature` 恰为 `(a, b)`
> ⇒ 机械判据**接受**它 ⇒ 运行期语义 = `ClassTwoArgInit(current, new)`（**构造实例**）。
> 这是**与上游同构**的行为，MUST NOT 被「善意地」改成拒绝（那会造成与上游的**行为差异**）。

---

## 3. 判定表 · B —— 归约器**提取**形态（**2 类** · FR-016 ①-b）

| # | 形态 | 输入（`Annotated` 元数据 · **具名** · 见 §4 夹具清单） | 期望 | 上游 |
|---|---|---|---|---|
| E-1 | 末位**非** callable（说明文字） | `meta_non_callable` | **无归约器** · 语义 `overwrite` · **不报错** | `langgraph/graph/state.py:1905-1907` |
| E-2 | 多条目元数据（末位才是 callable） | `meta_multi_entry` | 只认**末位** ⇒ 归约器 = `operator.add` | `langgraph/graph/state.py:1905-1907` |

> **📌 E-1 不是「拒绝」**：末位非 callable ⇒ 该 key **无归约器**（走默认覆盖语义 · C3），
> 解析**成功**。把它与 §2 的「拒绝」混为一谈 ⇒ 会把合法用法判成错误。

> **📌 「输入」列的形态统一**：§2 与 §3 的「输入」列**一律是 §4 夹具清单里的名字**
> ⇒ 测试的求值命名空间**只有一份**、**逐名一致**（MUST NOT 在测试里另抄一份表）。
> §3 的两个名字指向**元数据元组**（不是「末位候选」），语义见 §4 的说明列。

---

## 4. 测试夹具清单（本表 `输入` 列的求值命名空间）

> **📌 唯一命名空间（2026-11-08 分析轮修订）**：本节是 **§2（16 类二元性形态）+ §3（2 类提取形态）
> 共 18 条**「`输入`」列的**唯一**求值命名空间 ⇒ §2 / §3 的**每一个**输入名 MUST 能在本节找到
> （`tasks.md` T004 / T046 据此断言「缺失条数 == 0」）⇒ 夹具**只有一套**。

| 名字 | 定义 | 说明 |
|---|---|---|
| `operator.add` | `operator.add` | **位置专用 2 参**（§2 第 1 行）· 签名 `(a, b, /)` |
| `two_positional` | `def two_positional(a, b): ...` | — |
| `three_positional` | `def three_positional(a, b, c): ...` | — |
| `one_positional` | `def one_positional(a): ...` | — |
| `one_positional_varargs` | `def one_positional_varargs(a, *args): ...` | — |
| `two_positional_varargs` | `def two_positional_varargs(a, b, *args): ...` | — |
| `two_positional_kwonly` | `def two_positional_kwonly(a, b, *, c=None): ...` | — |
| `kwonly_only` | `def kwonly_only(*, a, b): ...` | — |
| `ClassNoInit` | `class ClassNoInit: ...` | `__init__` 无参（§2 第 9 行） |
| `ClassOneArgInit` | `class ClassOneArgInit:` + `__init__(self, a)` | — |
| `ClassTwoArgInit` | `class ClassTwoArgInit:` + `__init__(self, a, b)` | **被接受**（§2 第 11 行） |
| `CallableInstance` | `class CallableInstance:` + `__call__(self, a, b)` | — |
| `CallableKwOnlyInstance` | `class CallableKwOnlyInstance:` + `__call__(self, *, a, b)` | — |
| `partial_add_one` | `functools.partial(operator.add, 1)` | 签名 `(b, /)` |
| `bound_method` | `two_positional.__get__(object())` | 签名 `(b)`（`self` 已绑定） |
| `str` | `str`（内置类型） | **签名不可取**（§2 第 16 行）· `inspect.signature` 抛 `ValueError` |
| `meta_non_callable` | `("说明文字",)` | **元数据元组**（§3 E-1）—— 末位**非** callable ⇒ 无归约器 · 不报错 |
| `meta_multi_entry` | `("描述", operator.add)` | **元数据元组**（§3 E-2）—— 只认**末位** |

---

## 5. 判据的**实测取样**（CPython 3.12.3 与 3.11.16 一致 · 本轮 research 实测）

> **📌 本表是 §2 的**证据镜像**，不是第二份判定权威** —— 「期望」一列 MUST 与 §2 逐行一致；
> **判定权威只在 §2** ⇒ 本表 MUST NOT 被独立于 §2 修改（改了 §2 必须同提交改本表）。

| 输入 | `inspect.signature` | 位置参数计数 | 期望 |
|---|---|---|---|
| `operator.add` | `(a, b, /)` | **2** | 接受 |
| `def f(a, b)` | `(a, b)` | **2** | 接受 |
| `def f(a, b, c)` | `(a, b, c)` | 3 | 拒绝 |
| `def f(a)` | `(a)` | 1 | 拒绝 |
| `def f(a, *args)` | `(a, *args)` | 1 | 拒绝 |
| `def f(a, b, *args)` | `(a, b, *args)` | **2** | 接受 |
| `def f(a, b, *, c=None)` | `(a, b, *, c=None)` | **2** | 接受 |
| `def f(*, a, b)` | `(*, a, b)` | 0 | 拒绝 |
| `ClassNoInit` | `()` | 0 | 拒绝 |
| `ClassOneArgInit` | `(a)` | 1 | 拒绝 |
| `ClassTwoArgInit` | `(a, b)` | **2** | **接受** |
| `CallableInstance` | `(a, b)` | **2** | 接受 |
| `CallableKwOnlyInstance` | `(*, a, b)` | 0 | 拒绝 |
| `functools.partial(operator.add, 1)` | `(b, /)` | 1 | 拒绝 |
| 绑定方法 | `(b)` | 1 | 拒绝 |
| `str` / `max`（内置类型 / 内置函数） | —— `inspect.signature` 抛 `ValueError` | —— | 拒绝 |

> **实测命令**（可复现）：
> `python3 -c "import inspect; print(inspect.signature(ClassTwoArgInit))"` 等逐条取样；
> 完整取样见 [research.md](../research.md) D-01 / D-09 与 spec「依据」节的实测行。

---

## 6. 判据的**变更纪律**

| 变更类型 | 处置 |
|---|---|
| **上游**行为变化（`langgraph` 升级） | MUST **重新核实**本表 ⇒ 行号与判定逐条复核 ⇒ **人工动作**（不自动化）⇒ 记录进 `harness/verification/B4F1/manual-verification.md` 的「遗留问题 / 结论」 |
| 本表**判定**变化（freegraph 侧有意偏离上游） | MUST 走**评审**（本文件是冻结面）⇒ 并在**兼容矩阵**登记差异（**当前无差异** ⇒ 矩阵零新增行 · SC-015） |
| 本表**形态**增补（新增测试形态） | 直接增行（**只增不改**既有判定）⇒ 测试随之增行（同一提交可见） |

> **📌 为什么不在 CI 里跑上游实时对照**（澄清 Q5）：`langgraph` 是**仅 dev/test** 依赖，
> 本 feature **零依赖声明、CI 不装它** ⇒ 上游升级**不会**让本 feature 的 CI 变红；
> 实时对照留给 **B5F2 / B8F1** 的差分夹具（立项书 §5.2 B5F2 行）。
