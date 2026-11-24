# B24F1 · 人工验证记录

**Feature**: B24F1 · 打包分发 + API 兼容矩阵 + `THIRD_PARTY_NOTICES`
**Date**: 2026-11-24
**Environment**: Linux · CPython 3.11.16 · uv 0.12.x · 仓库源码树

## 1. 环境

| 项 | 值 |
|---|---|
| OS | Linux |
| Python | 3.11.16 |
| 构建工具 | `uv`（`uv build`） |
| 安装方式 | 隔离 venv + wheel；`[otlp]` 从配置的包索引安装 |
| 仓库 | `yangjiacheng1996/freegraph` |

## 2. 步骤

1. `python harness/verification/B24F1/acceptance.py --record <file>`（A1–A3 + US1–US5）。
2. 按 `quickstart.md` 复核构建、纯度正 / 负向、隔离安装、`[otlp]`、矩阵与 README。
3. 记录实际输出到本文件第 3 节；迁移前基线见 §2.1。

### 2.1 迁移前基线（T002）

```text
$ git show HEAD:README.md | grep -c '^| `'
27
$ git show HEAD:README.md | grep '^| `Command`' | cut -d'|' -f4
 行为等价
$ uv build --out-dir /tmp/opencode/b24f1-baseline-dist
Successfully built freegraph-0.0.3.tar.gz
Successfully built freegraph-0.0.3-py3-none-any.whl
$ python harness/scripts/check_dist_purity.py /tmp/opencode/b24f1-baseline-dist
[纯度门禁] ✅ freegraph-0.0.3-py3-none-any.whl（wheel）——仅含包代码与必要元数据
[纯度门禁] ✅ freegraph-0.0.3.tar.gz（sdist）——仅含包代码与必要元数据
[纯度门禁] 2 个产物全部干净，可以发布。
purity_exit=0
```

发布流水线顺序（基线）：`.github/workflows/publish.yml` 的 `Build` → `Verify artifact purity` → `Publish to PyPI`。

T003 零运行时基线：`git diff -- src/freegraph harness/demo/target.py` 为空；`pyproject.toml` 的 `dependencies = []` 且只有 `otlp` extra；`src/freegraph/py.typed` 存在。

G8 / G19 / G29 基线：G8 / G19 从 `README.md` 的 `## API 兼容矩阵` 取行；G29 `--check-compat` 在 `COMPAT.md` 不存在时报告「未落地」并退出 0。迁移后三者取行源改为 `COMPAT.md`（已获发起者 2026-11-24 选项 A 追认）。

## 3. 实际输出

## 3. 实际输出

[PASS] A1 requires-python >= 3.11
[PASS] A1 基础依赖为空
[PASS] A1 唯一 extra = [otlp]
[PASS] A1 无 v2 extras
[PASS] A1 py.typed 存在
[PASS] A1 LICENSE = MIT
[PASS] A2 COMPAT.md 存在
[PASS] A2 affiliation 声明
[PASS] A2 机读段 27 行
[PASS] A2 Command = 部分等价
[PASS] A2 18 项覆盖表齐备
[PASS] A2 下游行：MemorySaver
[PASS] A2 下游行：InMemorySaver
[PASS] A2 下游行：CheckpointTuple
[PASS] A2 下游行：SqliteSaver
[PASS] A2 下游行：CompiledGraph.get_state
[PASS] A2 下游行：CompiledGraph.get_state_history
[PASS] A2 下游行：CompiledGraph.update_state
[PASS] A2 下游行：时间旅行
[PASS] A2 下游行：OtlpExporter
[PASS] A2 NOTICES §1
[PASS] A2 NOTICES protobuf 归一
$ uv build --out-dir /tmp/b24f1-dist-1rlb65_s
Building source distribution...
Building wheel from source distribution...
Successfully built /tmp/b24f1-dist-1rlb65_s/freegraph-0.0.3.tar.gz
Successfully built /tmp/b24f1-dist-1rlb65_s/freegraph-0.0.3-py3-none-any.whl
Building source distribution...
Building wheel from source distribution...
Successfully built /tmp/b24f1-dist-1rlb65_s/freegraph-0.0.3.tar.gz
Successfully built /tmp/b24f1-dist-1rlb65_s/freegraph-0.0.3-py3-none-any.whl

$ /home/ctyun/workspace/github/freegraph/.venv/bin/python /home/ctyun/workspace/github/freegraph/harness/scripts/check_dist_purity.py /tmp/b24f1-dist-1rlb65_s
[纯度门禁] ✅ freegraph-0.0.3-py3-none-any.whl（wheel）——仅含包代码与必要元数据
[纯度门禁] ✅ freegraph-0.0.3.tar.gz（sdist）——仅含包代码与必要元数据

[纯度门禁] 2 个产物全部干净，可以发布。
[PASS] A3 纯度正向退出码 0
[PASS] A3 wheel + sdist 均存在
[PASS] A3 wheel 不含 harness/
[PASS] A3 wheel 不含 .specify/
[PASS] A3 wheel 不含 .opencode/
[PASS] A3 wheel 不含 COMPAT.md
[PASS] A3 wheel 不含 THIRD_PARTY_NOTICES
[PASS] A3 sdist 不含 harness/
[PASS] A3 sdist 不含 .specify/
[PASS] A3 sdist 不含 .opencode/
[PASS] A3 sdist 不含 COMPAT.md
[PASS] A3 sdist 不含 THIRD_PARTY_NOTICES
$ /tmp/b24f1-base-qyjyadys/venv/bin/python -m pip install --no-index --no-deps /tmp/b24f1-dist-1rlb65_s/freegraph-0.0.3-py3-none-any.whl
Processing /tmp/b24f1-dist-1rlb65_s/freegraph-0.0.3-py3-none-any.whl
Installing collected packages: freegraph
Successfully installed freegraph-0.0.3
[PASS] US1 基础安装成功
$ /tmp/b24f1-base-qyjyadys/venv/bin/python -c import freegraph
[PASS] US1 import freegraph 成功
$ /tmp/b24f1-base-qyjyadys/venv/bin/python -m pip freeze
freegraph @ file:///tmp/b24f1-dist-1rlb65_s/freegraph-0.0.3-py3-none-any.whl#sha256=136e7a2db937320329d9cbb31dfe15e6545cb87bf1ca56e7bcf7ac46964f4f96
[PASS] US1 pip freeze 无第三方运行时依赖
$ /tmp/b24f1-otlp-pq_dpvfz/venv/bin/python -m pip install /tmp/b24f1-dist-1rlb65_s/freegraph-0.0.3-py3-none-any.whl[otlp]
Looking in indexes: https://mirrors.aliyun.com/pypi/simple/
Processing /tmp/b24f1-dist-1rlb65_s/freegraph-0.0.3-py3-none-any.whl (from freegraph==0.0.3)
Collecting opentelemetry-api>=1.20 (from freegraph==0.0.3->freegraph==0.0.3)
  Using cached https://mirrors.aliyun.com/pypi/packages/a9/2d/610db864d7513158cebb8f36cc88e67e73bd6c7aa1905ef18d89e1281c81/opentelemetry_api-1.45.2-py3-none-any.whl (60 kB)
Collecting opentelemetry-exporter-otlp-proto-grpc>=1.20 (from freegraph==0.0.3->freegraph==0.0.3)
  Using cached https://mirrors.aliyun.com/pypi/packages/e8/48/14301cac3d106e795eef7e89e191489f086b4e5ad26e47c9635a198e95f4/opentelemetry_exporter_otlp_proto_grpc-1.45.2-py3-none-any.whl (19 kB)
Collecting opentelemetry-sdk>=1.20 (from freegraph==0.0.3->freegraph==0.0.3)
  Using cached https://mirrors.aliyun.com/pypi/packages/9f/a5/9a3b793ef48245f2336a16beb2324c2397dbb3f987cd68942f77cca06156/opentelemetry_sdk-1.45.2-py3-none-any.whl (141 kB)
Collecting typing-extensions>=4.5.0 (from opentelemetry-api>=1.20->freegraph==0.0.3->freegraph==0.0.3)
  Using cached https://mirrors.aliyun.com/pypi/packages/49/d3/b8441a820a491ddfc024b0b0cf0393375b75ea13866d9c66727e54c2fc80/typing_extensions-4.16.0-py3-none-any.whl (45 kB)
Collecting googleapis-common-protos~=1.57 (from opentelemetry-exporter-otlp-proto-grpc>=1.20->freegraph==0.0.3->freegraph==0.0.3)
  Using cached https://mirrors.aliyun.com/pypi/packages/05/6d/78dc67a9e779e594b49bf62604034d3a6aa428a55afc729cafda4b7333e1/googleapis_common_protos-1.76.0-py3-none-any.whl (307 kB)
Collecting grpcio<2.0.0,>=1.63.2 (from opentelemetry-exporter-otlp-proto-grpc>=1.20->freegraph==0.0.3->freegraph==0.0.3)
  Using cached https://mirrors.aliyun.com/pypi/packages/fa/22/414f8c0d95d8a86be1a05e1997e7da7fa71a1d5078045eb274a679cac104/grpcio-1.85.4-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (7.4 MB)
Collecting opentelemetry-exporter-otlp-common==0.66b2 (from opentelemetry-exporter-otlp-proto-grpc>=1.20->freegraph==0.0.3->freegraph==0.0.3)
  Using cached https://mirrors.aliyun.com/pypi/packages/a8/47/b3049e30b339c82e3c7ec1fc692185a5d5a3ba65a94c570bb39b2c0b8424/opentelemetry_exporter_otlp_common-0.66b2-py3-none-any.whl (12 kB)
Collecting opentelemetry-exporter-otlp-proto-common==1.45.2 (from opentelemetry-exporter-otlp-proto-grpc>=1.20->freegraph==0.0.3->freegraph==0.0.3)
  Using cached https://mirrors.aliyun.com/pypi/packages/e6/d6/0f30d38120a949aef70528f845bf539f80df62abb4b8e62fdf69c2b6df5a/opentelemetry_exporter_otlp_proto_common-1.45.2-py3-none-any.whl (15 kB)
Collecting opentelemetry-proto==1.45.2 (from opentelemetry-exporter-otlp-proto-grpc>=1.20->freegraph==0.0.3->freegraph==0.0.3)
  Using cached https://mirrors.aliyun.com/pypi/packages/7e/0d/a0b8f2b9efe2ec1abdf639d3696db9b1563ebeb11d91aac08ba7341e9122/opentelemetry_proto-1.45.2-py3-none-any.whl (72 kB)
Collecting protobuf<8.0,>=5.0 (from opentelemetry-proto==1.45.2->opentelemetry-exporter-otlp-proto-grpc>=1.20->freegraph==0.0.3->freegraph==0.0.3)
  Using cached https://mirrors.aliyun.com/pypi/packages/db/f3/3996583dd2906297a637af12114deddf7658af6e683fedb83be061983fb5/protobuf-7.36.2-cp310-abi3-manylinux2014_x86_64.whl (343 kB)
Collecting opentelemetry-semantic-conventions==0.66b2 (from opentelemetry-sdk>=1.20->freegraph==0.0.3->freegraph==0.0.3)
  Using cached https://mirrors.aliyun.com/pypi/packages/67/bd/6bf33ed31521c565931c037e9e81bac47c1acb000e850c6e24220e2a0c00/opentelemetry_semantic_conventions-0.66b2-py3-none-any.whl (206 kB)
Installing collected packages: typing-extensions, protobuf, freegraph, opentelemetry-proto, opentelemetry-api, grpcio, googleapis-common-protos, opentelemetry-semantic-conventions, opentelemetry-exporter-otlp-proto-common, opentelemetry-sdk, opentelemetry-exporter-otlp-common, opentelemetry-exporter-otlp-proto-grpc
Successfully installed freegraph-0.0.3 googleapis-common-protos-1.76.0 grpcio-1.85.4 opentelemetry-api-1.45.2 opentelemetry-exporter-otlp-common-0.66b2 opentelemetry-exporter-otlp-proto-common-1.45.2 opentelemetry-exporter-otlp-proto-grpc-1.45.2 opentelemetry-proto-1.45.2 opentelemetry-sdk-1.45.2 opentelemetry-semantic-conventions-0.66b2 protobuf-7.36.2 typing-extensions-4.16.0
[notice] A new release of pip is available: 24.0 -> 26.3
[notice] To update, run: /tmp/b24f1-otlp-pq_dpvfz/venv/bin/python -m pip install --upgrade pip
[PASS] US1 [otlp] 安装成功
$ /tmp/b24f1-otlp-pq_dpvfz/venv/bin/python -m pip freeze
freegraph @ file:///tmp/b24f1-dist-1rlb65_s/freegraph-0.0.3-py3-none-any.whl#sha256=136e7a2db937320329d9cbb31dfe15e6545cb87bf1ca56e7bcf7ac46964f4f96
googleapis-common-protos==1.76.0
grpcio==1.85.4
opentelemetry-api==1.45.2
opentelemetry-exporter-otlp-common==0.66b2
opentelemetry-exporter-otlp-proto-common==1.45.2
opentelemetry-exporter-otlp-proto-grpc==1.45.2
opentelemetry-proto==1.45.2
opentelemetry-sdk==1.45.2
opentelemetry-semantic-conventions==0.66b2
protobuf==7.36.2
typing_extensions==4.16.0
[PASS] US1 [otlp] 无禁用包
[PASS] US2 wheel 根级仅包代码 + dist-info
[PASS] US2 wheel 含 py.typed
[PASS] US2 sdist 含 pyproject.toml
[PASS] US2 sdist 不含 .gitignore
[PASS] US2 sdist 无仓库内容
$ /home/ctyun/workspace/github/freegraph/.venv/bin/python /home/ctyun/workspace/github/freegraph/harness/scripts/check_dist_purity.py /tmp/b24f1-negative-ztw0qaft
[纯度门禁] ❌ freegraph-0.0.3-py3-none-any.whl（wheel）
    · wheel 含有非包内容：harness/report.md
    · wheel 含有禁止目录内容：harness/report.md
[纯度门禁] 发行产物不干净，共 2 处问题；**拒绝发布**。
           仓库内容（harness/ .specify/ .opencode/）不得进入 PyPI 发行包。
[PASS] US3 混入仓库文件 ⇒ 纯度门禁失败
[PASS] US3 负向输出指名违规
[PASS] US3 真实产物未被污染
[PASS] US3 工作流顺序 build → purity → publish
[PASS] US4 Command = 部分等价
[PASS] US4 Command 含 Y-01
[PASS] US4 Command 含 X-06
[PASS] US4 CompiledGraph 含 Y-02
[PASS] US4 Send 含 Y-03
[PASS] US4 Store 澄清在证据与来源
[PASS] US5 无过时断言：内核尚未实现
[PASS] US5 无过时断言：没有任何图运行时能力
[PASS] US5 无过时断言：请勿用于生产
[PASS] US5 无过时断言：请勿当作可用替代品
[PASS] US5 独立实现声明
[PASS] US5 三条承诺
[PASS] US5 能力表 5 列
[PASS] US5 能力表 8 行
[PASS] US5 as-of 日期
[PASS] US5 COMPAT 绝对链接
[PASS] US5 README 无完整矩阵
[PASS] US5 OTLP 三后端
[PASS] US5 OTLP 无默认推荐
[PASS] US5 English 关键段存在

## 4. 结论

- `B24F1 acceptance: PASS`（68 checks，环境就绪）；基础安装 `pip freeze` 只有 freegraph；`[otlp]` 安装成功且无 `certifi` / `requests` / `opentelemetry-exporter-otlp` 元包。
- 纯度正向退出码 **0**；负向（混入 `harness/report.md`）退出码 **1** 且输出「拒绝发布」；真实产物哈希未变。
- `COMPAT.md`：18 项齐备、下游行齐备、`Command` = 部分等价（Y-01 / X-06 / X-2 / X-3 / P3/`99d43aa` 纠正来源）。
- **G8 / G19 / G29 取行源迁移 + `Command` 定向例外** 已由发起者 2026-11-24 选项 A 追认；正式追认文字即本节。
- **质量门禁 5 偏离**（真实模型轮 → B25F1）已由发起者 2026-11-24 追认，并由 **B25F1（M4）** 承接。
- **B15F1 / B16F1 人工验收证据**：见 `harness/verification/B15F1/manual-verification.md` 与 `harness/verification/B16F1/manual-verification.md`。
- **T048 立项书复核**：`harness/proposals/立项书.md` §6.2.1 第 6 条与 §12 D7 已确认——README 只保留「能力 → freegraph 处置」表 + `COMPAT.md` 指针；逐符号矩阵以 `COMPAT.md` 为唯一权威；不改变门禁判据、不新增门禁编号。
- **G28 断网等价**：本机 `unshare --net` 不被允许（环境未就绪）；G22 / G27 已通过，G28 由 CI Linux 作业覆盖（与 T036 的口径一致）。

### 4.1 发起者签署

| 事项 | 结论 | 签署人 | 日期 |
|---|---|---|---|
| G8 / G19 / G29 取行源迁移 + `Command` 定向例外（选项 A） | 同意 | 杨家成（发起者） | 2026-11-24 |
| 质量门禁 5 真实模型轮偏离 → B25F1（M4）承接 | 同意 | 杨家成（发起者） | 2026-11-24 |
| `Y-01` 既有 DIFF 的文档记录 → B25F1 承接 | 同意 | 杨家成（发起者） | 2026-11-24 |

## 5. 遗留问题

- **Y-01**（`Command.goto` 缺省 `()` vs `None`）：既有 DIFF；**具名承接 B25F1（M4）**；运行时对齐归 v2。
- **Y-02**（`get_state` 无快照 `None` vs 上游空 `StateSnapshot`）：B15F1 X-01；只登记，运行时对齐归 v2。
- **Y-03**（`Send` 不可变 vs 上游可变）：B11F1；只登记，运行时对齐归 v2。
- **质量门禁 5 偏离**：真实模型轮由 **B25F1（M4）** 承接；发起者 2026-11-24 追认。
- **B15F1 / B16F1 人工验收证据**：链接见 §4。
- G8 / G19 / G29 的取行源迁移若在后续 feature 变更，MUST 同步更新本记录。
