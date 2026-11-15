# B6F1 · `StateGraph` 构建器 · 人工验证记录

## 1. 验证环境

| 项 | 实际值 |
|---|---|
| 仓库 | `freegraph`（`/home/ctyun/workspace/github/freegraph`） |
| 平台 | Linux x86_64 |
| Python | CPython **3.11.16**（`.venv/bin/python`） |
| 上游差分 | `langgraph 1.2.11`（开发期依赖，未进入发行面） |
| 日期 | 2026-11-15 |

## 2. 验证步骤

1. `.venv/bin/python -m pytest -q`
2. `.venv/bin/python -m coverage run --source=freegraph._stategraph -m pytest -q tests/facade/test_stategraph_builder.py tests/facade/test_stategraph_validation.py tests/facade/test_stategraph_spec.py`
3. `.venv/bin/python -m coverage report -m`
4. `.venv/bin/python harness/verification/B6F1/acceptance.py`（覆盖 quickstart §2–§5 的建图 / path_map / 错误 / 链式 / 纯净性场景）
5. `.venv/bin/python harness/scripts/diff_parity.py -k builder`
6. 门禁：`gate_G21_dependencies.py` / `gate_G24_config_layer.py` / `gate_G25_import_graph.py --registry specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md` / `gate_G26_network_static.py` / `gate_G27_zero_egress.py` / `gate_G29_contract_carrier.py` / `gate_G30_attribution.py`
7. `.venv/bin/python -m pytest -q tests/facade/test_facade_gates.py tests/gates/test_gates.py`（G17 / G18 / G19 等 facade 门禁）
8. `.venv/bin/python -m pytest -q tests/facade/test_api_snapshot.py`（公开 API 快照）
9. `git diff --exit-code -- harness/demo/target.py`
10. `.venv/bin/python harness/demo/graph_core.py`（记录退出码）

## 3. 实际输出

| # | 命令 / 判据 | 实际输出 |
|---|---|---|
| 1 | 全量回归 | **1323 passed, 4 skipped in 60.24s**；4 个 skip 均为既有环境门禁（C8 待 B8F1 / mypy 未安装 / 快照更新开关未开 / Windows 专属） |
| 2–3 | `_stategraph.py` 覆盖率 | **227 statements / 0 missed / 100%**（行覆盖率 100%） |
| 4 | 一键验收 | **共 40 条断言 · 失败 0 条 · `B6F1 acceptance: PASS`** |
| 5 | builder 差分 | **25 / 25 符合判词**（D-50…D-74；含 STRICTER 与 DIFF 登记项） |
| 6 | G21 / G24 / G25 / G26 / G27 / G29 / G30 | 全部 `PASS`（退出码 0）；G27：框架出站 **0**、用户出站 2 条记录在案不判失败 |
| 7 | facade / 架构门禁 | **77 passed**（G17 / G18 / G19 等） |
| 8 | 公开 API 快照 | **15 passed, 1 skipped**（skip = 未开启 `--update-api-snapshot`，属预期） |
| 9 | `harness/demo/target.py` diff | **空**（退出码 0） |
| 10 | `harness/demo/graph_core.py` | 退出码 **2**（`ENV_NOT_READY` · compile / invoke 仍归 B7F2 / B7F3；**不是**本 feature 失败） |

## 4. 结论

- **SC-001…SC-015** 均由 pytest / 差分 / acceptance 覆盖；构建器在 `target.py:142-155` 的建图段原样可用。
- 构建器**不执行**节点 / 路由 / 归约器；两次 `_build_spec()` 结构等价且快照相互独立。
- `_BuilderSpec` 已按冻结字段产出（含 `_ConditionalEdgeSpec.branch`），可机械适配 B7F1 的 `GraphSpec` / `NodeSpec`。
- 空节点表、未知端点、保留名 / 保留字符、非法 `path_map`、多源错误、schema 错误等均在构建期显式失败。
- G22「场景②」的**运行期**最小图断言**未在本 feature 点亮**，承接 **B7F3**（H-7 · 裁定 11）。

## 5. 遗留问题

| # | 遗留项 | 承接方 / 说明 |
|---|---|---|
| 1 | G22 场景② 运行期最小图断言 | **B7F3**（本 feature 只交付建图；不新增门禁编号） |
| 2 | `harness/demo/graph_core.py` 退出码 2 | **B7F2 / B7F3**（compile / invoke 未就绪；属预期） |
| 3 | EV-1a / EV-1b / EV-1c 的发起者追认 | ✅ **已追认（2026-11-15）**（见 §7） |
| 4 | 真实模型轮 / fake 模型端到端轮 | **B25F1**（M4 双跑验收） |

## 6. 质量门禁分阶段落地登记（EV-1）

| # | 被偏离的门禁部分 | 不可达成根因 | 承接方 / 里程碑 | 本 feature 的替代判据 |
|---|---|---|---|---|
| **EV-1a** | 门禁 3 的「`target.py` 原样可跑」 | 需要 `compile()` / `invoke()` / 路由 / 图导出 | B7F2 / B7F3 / B8F1 / B22F1 / B23F1（M2 六项齐备）· 最终双跑 B25F1（M4） | 只判 `target.py:142-155` 建图段原样可执行；`target.py` diff 为空 |
| **EV-1b** | 门禁 4 的「fake 模型跑通验收基线一轮」 | 无 `invoke()`，图不可执行 | B25F1（M4） | L3 构建器单测 + builder 差分探针替代；未写永久红 CI |
| **EV-1c** | 门禁 5 + 原则 V 的「真实模型一轮」 | 无 `invoke()`，无法跑真实模型轮 | B25F1（M4） | 人工验证记录照常五段式；真实模型轮具名承接 B25F1 |

> **发起者追认**：EV-1a / EV-1b / EV-1c 合并为一次发起者追认；已按发起者「人工验收通过，授权收尾签字」的指示确认（见 §7）。

## 7. 追认文字（已签字 · 2026-11-15）

> 本人已确认 B6F1 的人工验收结果（一键验收 **40 条断言全绿**、全量 pytest **1323 passed / 4 skipped**、
> `_stategraph.py` 覆盖率 **100%**、builder 差分 **25/25**），并追认本 feature 的
> **EV-1a / EV-1b / EV-1c** 分阶段落地：门禁 3 的端到端部分承接 B7F2 / B7F3 / B8F1 / B22F1 / B23F1，
> 门禁 4 / 5 的 fake 轮与真实模型轮承接 B25F1（M4）。判据未放宽，红线照常执行。

**发起者签字 / 日期**：杨家成 · **2026-11-15**
