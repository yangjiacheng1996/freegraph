# B23F1 人工验证记录

**Feature**: `specs/b23f1-draw-mermaid-png-offline/`
**日期**: 2026-11-20
**验收人**: opencode（执行）· 发起者（人工验收）
**发起者人工验收**: **通过**（2026-11-20）
**收尾确认**: 人工验收通过，准予收尾（2026-11-20）
**签名**: 发起者

## 1. 环境

- `.venv/bin/python --version`: Python 3.11.16
- `.venv/bin/python -m pytest --version`: pytest 9.2.0
- packaging: 26.3
- 上游（差分用，非仓库依赖）: `langgraph 1.2.11` + `langchain-core 1.7.6`（`.venv`）
- 行号取证: `langchain-core 1.6.3`（系统 site-packages）
- 基线（实施前）: `.venv/bin/python -m pytest -q tests/` = `1700 passed, 4 skipped, 0 failed`（113.76s）
- `pyproject.toml` / `harness/demo/target.py`: 未改动（`git diff --exit-code` 通过）

## 2. 步骤与实际输出

### 2.1 US1 / US2 · 契约 + 运行时 + 门面

```text
$ .venv/bin/python -m pytest -q tests/contracts/test_graph_png.py \
    tests/runtime/test_graph_offline.py tests/runtime/test_graph_png_offline.py \
    tests/facade/test_get_graph.py
42 passed, 1 skipped in 0.67s
```

skip = `.venv` 未安装 IPython ⇒ IPython 冒烟按设计 skip；PNG 结构判据为权威。

### 2.2 US3 · 差分 PNG

```text
$ .venv/bin/python -m pytest -q tests/differential/test_parity_probe.py -k png
1 passed, 1 skipped, 21 deselected in 0.85s
```

skip = 未设置 `FREEGRAPH_ALLOW_UPSTREAM_PNG`；上游 PNG 默认不外呼 `mermaid.ink`。

### 2.3 一键验收

```text
$ .venv/bin/python harness/verification/B23F1/acceptance.py
B23F1 acceptance: PASS
```

### 2.4 固定脚本等价的图形验收

```text
$ .venv/bin/python harness/demo/visualization.py
...
[V4 PNG 渲染 · C15（合法 PNG 字节，离线不抛异常）]
  ✔ C15 返回可被 IPython.display.Image 接受的合法 PNG 字节
  · PNG 字节数 = 173
...
[V6 target.py:144 等价复现（不依赖 LangChain）]
  ✔ V6 get_graph(xray=True).draw_mermaid_png() 返回合法 PNG
...
断言 22 条 · 通过 22 · 失败 0
结论：PASS
```

### 2.5 门禁

```text
$ .venv/bin/python harness/scripts/gates/gate_G21_dependencies.py
[G21] PASS —— 依赖闭包黑名单（声明级 · 含全部 extras 变体）

$ .venv/bin/python harness/scripts/gates/gate_G23_licenses.py
[G23] PASS —— 许可证白名单（4 级证据链 · 5 个精确 SPDX id）

$ .venv/bin/python harness/scripts/gates/gate_G26_network_static.py
[G26] PASS —— 网络静态扫描（src/freegraph/** 无网络客户端调用）

$ .venv/bin/python harness/scripts/gates/gate_G27_zero_egress.py
[G27] PASS —— 零出站动态断言（只观测不阻断 + 第一个非标准库帧归因）
（框架出站 = 0；用户出站 = 2，记录在案，不判失败）

$ .venv/bin/python harness/scripts/gates/gate_G29_contract_carrier.py
[G29] PASS —— 契约门禁载体（只读基准 diff + C4 / C8 挂载点 + 验收脚本集退出码）

$ .venv/bin/python harness/scripts/gates/gate_G30_attribution.py
[G30] PASS —— 全仓署名头（覆盖率 == 100%）+ 第三方品牌资产（FR-021）
```

**G28**：本机 `unshare --net --map-root-user true` 不可用（`/proc/self/uid_map` 不允许操作）
⇒ 断网任务交由 Linux CI 的 **G28** 执行；本 feature 的用例不建立真实连接，
未加入 `tests/gates/data/offline_exclusions.txt`。

### 2.6 SC-010 运行期模块

```text
$ .venv/bin/python -m pytest -q tests/runtime/test_graph_offline.py::test_png_runtime_does_not_load_langchain_family
1 passed
```

子进程中导入 `freegraph` 并调用 `draw_mermaid_png()` 后，`sys.modules` 中
`langchain` / `langchain_core` / `langgraph` / `langsmith` 的出现次数 == 0。

## 3. 差分与一键验收

- PNG 差分场景 **D-01…D-10**：`test_png_parity_scenarios_meet_their_verdicts` 通过；
  D-04 用 monkeypatch `requests.get` 模拟离线（不实际联网）⇒ 上游 `ValueError`，
  freegraph 返回合法 PNG。
- 上游真实渲染的可选对照：默认 skip；设置 `FREEGRAPH_ALLOW_UPSTREAM_PNG=1` 时才触网。
- `B23F1 acceptance: PASS`（A1–A4）。

## 4. 结论（A1–A4）

| # | 判据 | 结论 |
|---|---|---|
| A1 | 离线不抛阻断性异常 | **通过**（socket 守卫下成功；G27 框架出站 = 0） |
| A2 | 返回合法 PNG 字节 | **通过**（签名 / `IHDR` / 块 CRC / `IDAT` 解压 / `IEND` / 无尾随；64×64、3 色） |
| A3 | 方法名同名 | **通过**（`Graph.draw_mermaid_png` 存在于自有 `Graph`；零参数、返回 `bytes`） |
| A4 | 零出站 | **通过**（G26 / G27；静态扫描 0 + observe-only 归因 0） |

## 5. 遗留问题

```text
$ .venv/bin/python -m pytest -q tests/
1736 passed, 6 skipped, 0 failed
```

6 条 skip = 既有环境 / 可选工具（IPython、mypy、上游 PNG 网络对照等）；
**0 failed**。G28 断网任务在 Linux CI 执行。

### T-1 授权

- **授权来源**：B22F1 契约 §8「下游接口（B23F1）」+ 本 feature 提示词。
- **处置**：`Graph` **仅追加** `draw_mermaid_png() -> bytes`；字段 / 构造签名 /
  不可哈希 / 元组容器 / `__all__` / `draw_mermaid()` 语义全部不变。
- **承接方**：B23F1 · M2。
