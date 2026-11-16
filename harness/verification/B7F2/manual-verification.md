# B7F2 · `compile()` → `CompiledGraph` · 人工验证记录

**Feature**: `specs/b7f2-compile/` · **日期**: 2026-11-16
**上游**: `langgraph 1.2.11`（开发 / 测试侧差分依赖；不在发行面）

---

## 1. 环境

| 项 | 值 |
|---|---|
| Python | **3.11.16**（`.venv/bin/python`） |
| 平台 | Linux（CPython 3.11.16） |
| freegraph | 源码树（`PYTHONPATH=src`） |
| 上游差分依赖 | `langgraph 1.2.11`（`.venv` 实际安装版本） |
| 第三方运行时依赖 | **零**（`dependencies = []`） |

---

## 2. 步骤（可复制命令）

```bash
# ① 全量 pytest（含 B7F2 新增 facade / differential 用例）
.venv/bin/python -m pytest -q

# ② B7F2 一键验收（A1–A3 / 3 类错误 / 6 静态断点 / 注入项 / 快照 / 冻结字段 / 零调用）
.venv/bin/python harness/verification/B7F2/acceptance.py

# ③ compile-only 差分（D-75…D-91）
.venv/bin/python -m pytest tests/differential/test_parity_probe.py -q -k compile

# ④ 上游取证脚本（E-25…E-55 · 上游缺席即干净跳过）
.venv/bin/python harness/verification/B7F2/probe_upstream.py

# ⑤ 验收脚本退出码（compile 已交付、invoke 未就绪 ⇒ A3 通过后仍 rc=2）
PYTHONPATH=src .venv/bin/python harness/demo/graph_core.py; echo "rc=$?"

# ⑥ 受影响门禁
.venv/bin/python harness/scripts/gates/gate_G21_dependencies.py --project pyproject.toml
.venv/bin/python harness/scripts/gates/gate_G23_licenses.py
.venv/bin/python harness/scripts/gates/gate_G24_config_layer.py
.venv/bin/python harness/scripts/gates/gate_G25_import_graph.py --root .
.venv/bin/python harness/scripts/gates/gate_G26_network_static.py
.venv/bin/python harness/scripts/gates/gate_G27_zero_egress.py
.venv/bin/python harness/scripts/gates/gate_G29_contract_carrier.py
.venv/bin/python harness/scripts/gates/gate_G30_attribution.py --root .
```

---

## 3. 实际输出

### 3.1 全量 pytest

```text
1421 passed, 4 skipped in 78.72s
```

（基线 1323 passed / 4 skipped ⇒ B7F2 新增 **98** 条用例。）

### 3.2 B7F2 一键验收

```text
共 33 项断言 · 失败 0 项
结论：PASS（B7F2 编译期判据全部满足）
```

### 3.3 compile-only 差分

```text
1 passed, 15 deselected          # -k compile
28 passed                        # tests/differential 全量
```

D-75…D-91 判词与 `specs/b7f2-compile/contracts/upstream-parity.md` §3.2 逐条一致：

- **SAME**：D-75 / D-76 / D-79 / D-80 / D-81 / D-83 / D-84 / D-85 / D-86 / D-87 / D-88 / D-89 / D-91
- **STRICTER**：D-82（裸空串断点）
- **DIFF**：D-77（checkpointer 类型校验 · X-4）/ D-78（store 警告 · X-3）/ D-90（改图提示 · X-5）

### 3.4 上游取证脚本

```text
langgraph 1.2.11
E-25: [...]
...
E-55: 'my-graph'
```

（逐条结果以本机实际运行输出为准；`langgraph` 缺席时脚本打印 `[SKIP]` 并退出 0。）

### 3.5 `graph_core.py` 退出码

```text
[A3 图构建与编译 · C9 / C10]
  ✔ C9 START 常量值
  ✔ C9 END 常量值
  ✔ C10 compile() 无参可调用
  ✔ C10 编译产物具备 invoke()
  ✔ C10 编译产物具备 stream()
  ✔ C10 compile(checkpointer=, store=) 关键字被接受
[环境未就绪] invoke() 仍为桩（执行属 B7F3）
rc=2
```

⚠️ **口径**：`compile()` 已交付 ⇒ A3 **真跑通过**；`invoke()` 归 B7F3 ⇒ A3 之后以
**退出码 2** 结束（**不是 FAIL**）。**MUST NOT** 把守卫改成「6 方法能力面 ⇒ 已就绪」。

### 3.6 门禁

| 门禁 | 结果 |
|---|---|
| G14 门面零实现体 / G17 import·env·IO / G19 兼容矩阵 / G20 署名头（**pytest 载体**） | ✅ 全绿（随 `pytest -q`） |
| G21 依赖闭包黑名单 | ✅ PASS |
| G23 许可证白名单 | ✅ PASS（被检查包数 = 0） |
| G24 配置层（零环境变量读取） | ✅ PASS |
| G25 导入图单向（ARCH-1） | ✅ PASS |
| G26 网络静态扫描 | ✅ PASS |
| G27 零出站动态断言 | ✅ PASS（框架出站 = 0） |
| G29 契约门禁载体（`target.py` diff / C4·C8 挂载点 / 验收脚本退出码） | ✅ PASS |
| G30 全仓署名头 + 第三方品牌资产 | ⚠️ **8 条违规，均为 B7F2 之前已存在的 tracked 文件**（`harness/demo/target.py` 的具名例外逻辑、`harness/reports/Q7-*.md` 与 `specs/b3f1-*/architecture-gates.md` 中的上游 Approved copy 指纹）；**B7F2 未新增违规**，详见 §5 |

---

## 4. 结论（逐条对照验收判据）

| SC | 判据 | 结果 |
|---|---|---|
| SC-001 | `compile()` 无参返回非空产物；`graph_core` A3 通过后 rc=2 | ✅ |
| SC-002 | `checkpointer=None, store=None` 被接受；注入对象身份可读 | ✅ |
| SC-003 | 3 类核心错误各一例，`ValueError` 且消息点名 | ✅ |
| SC-004 | 6 个能力面方法全部存在；零 `AttributeError` | ✅ |
| SC-005 | 编译期零用户函数调用 / 零 env / 零出站 | ✅ |
| SC-006 | CV-14 项 + NV-7 项（C-07/C-08 正向覆盖） | ✅ |
| SC-007 | 静态断点 6 形态；元素级/裸字符串逐字同款 | ✅ |
| SC-008 | 单源 END 过滤 / 多源 V-16 / `__parent__` / 6 方法异常 | ✅ |
| SC-009 | 适配正确性（END 过滤后）+ 顺序与确定性 | ✅ |
| SC-010 | 冻结字段名 + 条件边 5 键形状 + `GraphSpec.conditional_edges` 恒空 | ✅ |
| SC-011 | 通道零残留 + 两映射独立 | ✅ |
| SC-012 | 快照隔离 + 两次编译结构等价 | ✅ |
| SC-013 | 门面 7 符号不变；API 快照逐字节不变 | ✅ |
| SC-014 | 最小图可编译；`target.py` diff 为空 | ✅ |
| SC-015 | 6 关键字可读 + store 恰好 1 条 warning + README 写明边界 | ✅ |
| SC-016 | 差分 D-75…D-91 判词逐条一致 | ✅ |

### 来源覆盖

- **上游实测 E-25…E-55**：`harness/verification/B7F2/probe_upstream.py`（可复现）。
- **差分 D-75…D-91**：`tests/differential/parity_probe.py` 的 `_run_compile_scenarios()`。
- **偏离登记**：X-1…X-12；本 feature 追认 **X-9**（`debug` 硬编码 `False` · 零环境变量）、
  **X-11**（断点属性暴露归一化元组）、**X-12**（`transformers` 与上游 `stream_transformers`
  的命名差异）。
- **证据锚点**：`langgraph 1.2.11` 的 `graph/state.py` / `pregel/main.py`（见 spec 的
  Upstream Parity 与 `contracts/upstream-parity.md`）。

---

## 5. 遗留问题

1. **EV-1a / EV-1b / EV-1c**（门禁 3 / 4 / 5 的端到端部分）在本 feature **物理不可达成**：
   需要 `invoke()` / 路由 / 图导出 / PNG 渲染 ⇒ 具名承接 **B7F3 / B8F1 / B22F1 / B23F1 / B25F1**；
   本 feature **不写永久红 CI**。人工记录按 plan 的 EV-1a/b/c 口径留档，待发起者一次追认。
2. **G22「场景②」运行期断言**未点亮；由 **B7F3** 承接（B3F1 裁定 22）。
3. **G30 的 8 条违规为既有问题**（B7F2 之前已存在的 tracked 文档 / 具名例外逻辑），
   属 B3F1 门禁自身的后续修正范围；B7F2 未新增违规。
4. **`invoke()` / `stream()` / `get_graph()` / 条件边求值 / checkpointer 行为 / store 行为 /
   节点别名语义**均不在本 feature 范围（各自归属 feature 见 spec 的 Out of Scope）。
5. **本机仅 CPython 3.11.16 一档**；3.13 / 3.14 / macOS / Windows / arm64 多档实测未执行，
   沿用 CI 矩阵覆盖。

---

## 6. 质量门禁分阶段落地登记（EV-1）

| # | 被偏离的门禁部分 | 不可达成根因 | 承接方 / 里程碑 | 本 feature 的替代判据 |
|---|---|---|---|---|
| **EV-1a** | 门禁 3 的「`target.py` 原样可跑」 | 需要 `invoke()` / 路由 / 图导出 | **B7F3 / B8F1 / B22F1 / B23F1**（M2 六项齐备）· 最终双跑 **B25F1**（M4） | 只判 `compile()` 侧：A1–A3 + 校验清单 + 注入项；`G29` 断言 `target.py` diff 为空；**G22「场景②」的运行期断言由 B7F3 点亮（B3F1 裁定 22 · H-6）** |
| **EV-1b** | 门禁 4 的「fake 模型跑通验收基线一轮」 | 无 `invoke()`，图不可执行 | **B25F1**（M4） | 以 facade 编译测试 + compile-only 差分探针（D-75…D-91）替代；未写永久红 CI |
| **EV-1c** | 门禁 5 + 原则 V 的「真实模型一轮」 | 无 `invoke()`，无法跑真实模型轮 | **B25F1**（M4） | 人工验证记录照常五段式；真实模型轮具名承接 B25F1 |

> **发起者追认**：EV-1a / EV-1b / EV-1c 合并为一次发起者追认；已按发起者
> 「人工验收通过，授权收尾签字」的指示确认（见 §7）。红线（依赖 / 许可证 / 商标 /
> 零出站）**不适用**本条，照常执行。

## 7. 追认文字（已签字 · 2026-11-16）

> 本人已确认 B7F2 的人工验收结果（一键验收 **33 条断言全绿**、全量 pytest
> **1421 passed / 4 skipped**、compile-only 差分 **D-75…D-91 逐条符合判词**、
> `target.py` diff 为空、`graph_core` A3 真跑通过后以退出码 2 结束），并追认本 feature 的
> **EV-1a / EV-1b / EV-1c** 分阶段落地：门禁 3 的端到端部分承接
> **B7F3 / B8F1 / B22F1 / B23F1**，门禁 4 / 5 的 fake 轮与真实模型轮承接 **B25F1**（M4）。
> 同时追认 **X-9**（`debug` 硬编码 `False`）、**X-11**（断点属性暴露归一化元组）、
> **X-12**（`transformers` 命名差异）。判据未放宽，红线照常执行。

**发起者签字 / 日期**：杨家成 · **2026-11-16**
