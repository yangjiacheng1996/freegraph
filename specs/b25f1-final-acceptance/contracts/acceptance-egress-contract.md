# Contract: 一键验收 + 零出站 + 人工记录

**Feature**: B25F1 · **Date**: 2026-11-25
**Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md)

> 锁定 FR-004 / FR-005 / FR-007 / FR-008 / FR-012 / FR-021 与 A2 / A3 / A4 / SC-002 / SC-004。

---

## 1. 一键验收入口

`harness/verification/B25F1/acceptance.py`（**B25F1 一键验收**；与
`harness/demo/acceptance.py` 的四组（含 diagnostics）编排器**职责不同**，MUST 用全路径区分）

| 参数 | 作用 |
|---|---|
| （无） | A1 / A3 / A4 / A5 / DEP；A2 标记「人工轮未跑」 |
| `--skip-real` | 显式跳过 A2（CI 用；退出码仍可为 0） |
| `--real` | 额外跑 A2（真实模型两段式） |
| `--record <path>` | 生成《人工验收记录》草稿（真实轮已跑则填实测输出） |
| `--suite <names>` | 可选：只跑指定组（调试用） |

**退出码**：

| 码 | 含义 | 判定 |
|---|---|---|
| `0` | PASS | 所有**已要求**的断言通过 |
| `1` | 断言失败 | 能力已就绪但契约未兑现 |
| `2` | 环境未就绪 | 缺 `freegraph` / `langchain` / `IPython` / `--real` 缺凭据 |

最后一行 MUST 打印 `B25F1 acceptance: PASS|FAIL`。

---

## 2. 步骤与依赖

| 步骤 | 内容 | 依赖 |
|---|---|---|
| `DEP` | 依赖断言 + 反向断言 | 无 |
| `A1` | fake 轮（`fake_round.py`） | A1 脚本 |
| `A2` | 真实轮两段式（`real_round.py`） | `--real` + 凭据 / 网络 |
| `A3` | 框架出站 = 0 | 监测夹具 |
| `A4` | 四组（含 diagnostics：`graph_core` / `agent_loop` / `visualization` / `diagnostics`） | 各脚本可运行 |
| `A5` | 双重基线 | SHA-256 + git 基线 ref |

**A4 的组**：`graph_core.py` / `agent_loop.py` / `visualization.py` / `diagnostics.py`
（`harness/demo/acceptance.py` 自身检查亦在其退出码内）。

---

## 3. 零出站监测（A3）

### 3.1 包装面

- `socket.socket.connect`
- `socket.create_connection`

**只记录、不阻断**：包装函数 MUST 调用原实现并放行连接。

### 3.2 归因（G27 权威口径）

从栈顶向下**跳过全部标准库帧**，第一个非标准库帧：

- 在 `freegraph/` 包内 ⇒ **框架出站**；
- 否则 ⇒ **用户出站**。

### 3.3 断言

| 项 | 规则 |
|---|---|
| 框架出站 | **必须 == 0** |
| 用户出站 | **逐条记录**；任意目标、任意条数；**不判失败** |
| 目标白名单 | **MUST NOT** 校验（freegraph 是通用型图框架） |
| 阻断 | **MUST NOT** 阻断任何连接 |

### 3.4 记录

监测记录 MUST 包含：

- 框架出站条目（期望为空）；
- 用户出站逐条（目标 + 归因）；
- 人工轮的实际大模型端点 / OTLP 端点（若启用）；
- 观测面声明（fake 轮 / 真实轮 / 测试套件）。

---

## 4. 断网等价性（FR-005）

| 层 | 要求 |
|---|---|
| 进程内（必做） | 禁用 `socket.socket.connect` / `socket.create_connection`（抛异常）；fake 轮 + diagnostics 核心用例 MUST 全绿 |
| OS 级（条件增强） | 复用 G28 的 `unshare --net --map-root-user`；不具备 ⇒ 登记环境偏离，不判失败 |

**MUST NOT** 把 OS 级「跑不了」写成「没验证」；**MUST NOT** 因此判失败。

---

## 5. 环境清理（FR-021）

三轮验收（⓪ 依赖断言 / ① CI / ② 人工）MUST：

- 清空全部 `LANGSMITH_*`；
- 子进程 env 不得透传 `LANGSMITH_*`；
- 记录写明「清空方式」与「清空后计数 == 0」。

**MUST NOT** 读取 / 依赖任何环境变量来开启观测或出站（原则 I）。

---

## 6. 人工验收记录（FR-008 / SC-004）

**路径**：`harness/verification/B25F1/manual-verification.md`

### 6.1 五要素

1. **验证环境**：OS / Python / 依赖 / 环境变量清理方式 / 接入路径；
2. **验证步骤**：fake 轮、真实轮（两段）、四组（含 diagnostics）、双重基线、断网、依赖断言；
   发布前清单 MUST 纳入 B14F1 的 `harness/verification/B14F1/manual-verification.md` 与
   `harness/verification/B14F1/acceptance.py`（只引用、不回改）；
3. **实际输出**：逐条命令 / 断言的真实输出（**非「符合预期」**）；
4. **结论**：双跑 / 零出站 / 脚本集 / 只读基准 / 文档；
5. **遗留问题**：逐条；含 **Y-01** 的 v1 行为提示。

### 6.2 三附件

1. 依赖断言轮输出（`Requires-Dist` / `pip freeze` / 运行时 `sys.modules` 反向断言）；
2. 「框架出站 = 0」监测记录（框架 0；用户出站逐条）；
3. 反向断言结果（运行时无 `langchain` / `langchain_core`）。

### 6.3 证据要求

- 真实轮证据 MUST 含 B15/B16/B20/B21/B23/B24 的非空实测输出；
- **MUST 含 B14F1 的 `harness/verification/B14F1/manual-verification.md` 与
  `harness/verification/B14F1/acceptance.py` 引用**（FR-019）；
- **MUST 含接入路径**（官方直连 / 兼容网关；gateway 不得写成官方直连）；
- 环境偏离 MUST 写明「已完成 / 未完成 / 原因」；
- **MUST NOT** 回改既有 feature 的记录；
- **MUST NOT** 用自动验收通过冒充人工验收。

---

## 7. 自动文档守卫

`tests/runtime/test_b25f1_manual_record_guard.py` MUST 断言：

- 记录存在；**记录缺失 / 含占位 / 无真实轮证据时 `pytest.skip`**（T019，避免永久红 CI）；
  常驻 CI 保持 skip；**T052 的严格模式仅在发布 / 人工门禁执行**（宪法 v1.13.0）；
- 五段式标题存在且正文非空；
- 三附件齐备且各含实际输出；
- **「实际输出」与「结论」段 MUST NOT 以整句「符合预期」/「未验证」替代实测**（允许出现在否定 / 引用语境）；
- 含 B15/B16/B20/B21/B23/B24 的实测输出关键词；
- **含 B14F1 的 `harness/verification/B14F1/manual-verification.md` 与
  `harness/verification/B14F1/acceptance.py` 引用**；
- **含接入路径（官方直连 / 兼容网关；gateway 不得写成官方直连）**；
- 含 **Y-01**；
- 遗留问题非空；
- 占位符检测只针对 `待填` / `TODO` / `⬜` / 空表格；**MUST NOT** 用裸「未验证」「符合预期」子串误伤正文。

---

## 8. 失败示例

```text
[FAIL] A1 llm_calls 期望 2，实际 1 —— 工具循环未执行
[FAIL] A3 框架出站 = 1（freegraph/observability/...）—— 违反零出站
[FAIL] A5 target.py SHA-256 不一致
[ENV]  A2 真实模型凭据缺失 —— 已完成：fake 轮 / 四组 / 诊断；未完成：真实轮
[FAIL] 记录：真实轮只有「符合预期」，无实际输出 —— 违反证据门禁
```
