# Research: B24F1 · 打包分发 + API 兼容矩阵 + `THIRD_PARTY_NOTICES`

**Date**: 2026-11-24 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

> **取证口径**：本文件对**仓库现状 / 门禁实现 / 构建配置**的断言来自本地源码与脚本
> （`tests/` · `harness/scripts/` · `pyproject.toml` · `.github/workflows/`，as-of 2026-11-24）；
> 对**上游行为**的断言沿用既有 feature 的实测基线：**既有矩阵行**保留其原文引用版本
> （含 `StateDict` 的 `1.2.19`）；**新增 / 复核行与差分测试**统一以 `langgraph 1.2.11` 为准。
> 本 feature **不新增**运行时行为。无 `[NEEDS CLARIFICATION]`。

---

## D-01 · 兼容矩阵权威源：`COMPAT.md` 唯一权威 + G8 / G19 / G29 迁移

**Decision**：`COMPAT.md` 为**唯一权威**的逐符号 / 逐项矩阵；README 仅保留
「能力 → freegraph 处置」表、affiliation 声明与指向 `COMPAT.md` 的链接 / 摘要。
G8 / G19 / G29 的取行源同步从 README 迁到 `COMPAT.md`（**不新增门禁编号**）。

**现状证据（关键）**：

| 门禁 | 现状 | 证据 |
|---|---|---|
| G8 | 从 `README.md` 的「## API 兼容矩阵」章节取行；要求契约层符号齐备 + **4 列（现状测试为 `>=4`，T006 收紧为 `==4`）** + 无重复 + affiliation | `tests/contracts/test_architecture.py:1241-1400` |
| G19 | 从 README 取行；要求门面清单（`facade-api.md` §0，**manifest 驱动、当前 8 个**）各恰一行、整表符号集合 == 契约层 ∪ 门面层；并禁止白名单行等价程度**变差** | `tests/facade/test_facade_gates.py:399-620` · `tests/facade/_gatesupport.py:511-545` |
| G29 `--check-compat` | `COMPAT.md` 不存在 ⇒ 报「未落地」退出 0；存在 ⇒ 与 README 逐格比对 | `harness/scripts/gates/gate_G29_contract_carrier.py:252-345` |
| CI | 已跑 `gate_G29_contract_carrier.py --check-compat` | `.github/workflows/ci.yml:156` |

**Rationale**：用户 2026-11-24 在 clarify 后选择 **A**（`COMPAT.md` 唯一权威；README 只留能力表 + 链接）。
若只建 `COMPAT.md` 而不改门禁：
- G8 / G19 仍要求 README 有完整矩阵 ⇒ 与 A-3 冲突；
- G29 会拿 `COMPAT.md` 与 README 比对 ⇒ README 无完整矩阵时**必红**。
⇒ 必须在同一 feature 内完成**取行源迁移**，否则 CI 永久红（违宪「MUST NOT 写永久红的 CI」）。
**README 指针改写 MUST 与 `COMPAT.md` 落库同批（T004）**：G8 / G29 的「README 无完整矩阵」
断言在 Phase 2 就启用，若等到 T033 才改 README，T010「迁源后全绿」不可能成立。
**其他消费者**：`tests/runtime/test_parse_contract.py` 也读 README 矩阵，必须同批迁到
`COMPAT.md`（T043）。**G19 基线**：MUST 用 `HEAD:COMPAT.md` 优先（存在且有机读段行）、`HEAD:README.md` 回退；
固定 `HEAD:README.md` 会在 README 重写提交后变空 ⇒ `assert previous` 失败。

**Alternatives considered**：
- **B：README 保留完整矩阵，`COMPAT.md` 逐字节镜像** —— 拒绝：直接违背 A-3；两份完整矩阵仍需同步。
- **C：README 矩阵由 `COMPAT.md` 自动生成，门禁继续读 README** —— 拒绝：README 仍含第二份完整矩阵；
  且需放宽 A-3 的措辞。
- **只建 `COMPAT.md`、不动门禁** —— 拒绝：G8 / G19 / G29 必红。

**Governance**：这是**门禁判据更新（破冻结面）**，已由用户 2026-11-24 **选项 A** 追认；
正式文字 MUST 落 `harness/verification/B24F1/manual-verification.md`；回溯修订落
`specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md`。

---

## D-02 · `Command` 等价程度：恢复「部分等价」

**Decision**：`Command` 行第三列定稿为 **部分等价**；G19 增加 **B24F1 定向例外**，只放行
`Command` 从「行为等价」回到「部分等价」的**纠漂移**。

**上游与项目证据**：

| 证据 | 内容 |
|---|---|
| 上游实测 | `langgraph 1.2.11` 的 `Command()` 构造合法，`Command().goto == ()`；freegraph 为 `None` |
| B9F1 parity | `specs/b9f1-command-primitive/contracts/upstream-parity.md` §2：X-1（非法 `goto` 目标 · 显式失败 vs 静默忽略）· X-4（非 dict `update` · 显式失败 vs 静默丢弃）；X-2 / X-3 异常类型差异 |
| G19 自身注解 | `tests/facade/test_facade_gates.py:464` 明写「等价程度 MUST NOT 变（`Command` = 部分等价 · `NodeFunc` = 不支持）」 |
| 当前 README | `Command` 行第三列为「行为等价」—— 由**上游对齐批次 P3（commit `99d43aa`，2026-11-13）**改动；B1F1 原为「部分等价」；B22F1（`125ba0f8`）仅追加泛型化措辞、未改第三列 |
| 用户决定 | 2026-11-24 clarify · 答案 A（恢复部分等价并纠正 P3/`99d43aa` 漂移） |

**Rationale**：上游成功路径属性差异（`goto` 缺省）+ 更严的失败信号 + 异常类型差异
⇒ 「部分等价」有据；恢复它同时满足 B9F1 的定稿口径与 G19 自己的注释。
⚠️ **三态必须分开**：`goto` 缺省 `()` vs `None` 是**成功路径 DIFF**（**Y-01**，既有偏差，
B1F1 冻结 `goto=None`）⇒ **不得**并入 X-06 的 STRICTER；X-06 只覆盖失败信号。
B24F1 只登记 Y-01、不改运行时，并在 `manual-verification.md` 遗留问题中列出。

**Alternatives considered**：
- **保持「行为等价」** —— 拒绝：与上游实测、B9F1 parity、G19 注释三处冲突。
- **仅改差异说明、不改第三列** —— 拒绝：矩阵仍宣称「行为等价」，属过度声明。

**Governance**：G19 的「MUST NOT 变差」是既有冻结判据；B24F1 例外属**破冻结面**，
已由用户 2026-11-24 选项 A 追认；例外 MUST 只含 `{"Command"}`，且 MUST NOT 放宽其它行。
**`Command` 不整体移出单调检查**：仅 `行为等价 → 部分等价` 放行；其它任何等级变化
（含 `部分等价 → 不支持`）MUST 继续失败。

---

## D-03 · 打包配置：沿用 hatchling，产物天然排除仓库文档

**Decision**：**不改**构建后端与依赖面；只验证并通过显式 `exclude` 兜底。

**现状证据**：

| 配置 | 现状 |
|---|---|
| `[build-system]` | `hatchling>=1.27` · `hatchling.build` |
| `[project].dependencies` | `[]` |
| `[project.optional-dependencies]` | 仅 `otlp` |
| `[tool.hatch.build.targets.wheel]` | `packages = ["src/freegraph"]` |
| `[tool.hatch.build.targets.sdist]` | `only-include = ["src/freegraph", "README.md", "LICENSE"]` + `exclude` 含 `harness` / `.specify` / `.opencode` / `specs` / `tests` / `dist` 等（**现状未含 `.gitignore`；T016 增加显式 exclude**） |
| `py.typed` | `src/freegraph/py.typed` 已存在 |

**Rationale**：`only-include` 已限定 sdist；wheel 只打包 `src/freegraph`。`COMPAT.md` /
`THIRD_PARTY_NOTICES` 不在任何 include 列表内 ⇒ **天然不进包**。`.gitignore` 则由 hatchling
默认附带 ⇒ **必须显式 `exclude` 并从纯度脚本允许项移除**。再加显式 `exclude` 只为
「意图可见 + 防未来有人加 `include`」。

> **实现补充（T016）**：hatchling 的 sdist builder 在 `get_default_build_data` 中把
> VCS 忽略文件（根 `.gitignore`）**强制加入** `force_include`，`exclude` 无法拦截。
> 因此增加 **sdist-only** 构建钩子 `harness/build_hooks/sdist_prune.py`，在 `finalize`
> 阶段从 tar.gz 删除 `.gitignore`；钩子文件本身位于 `harness/`，不进入 sdist。

**Alternatives considered**：
- **改用其它构建后端** —— 拒绝：无理由；hatchling 已满足。
- **把 `COMPAT.md` 打进 sdist** —— 拒绝：spec FR-002 允许列表不含它；会让纯度门禁失败。

---

## D-04 · 纯度门禁：脚本已独立，补负向与顺序断言

**Decision**：保留 `harness/scripts/check_dist_purity.py` 与 `publish.yml` 的现有顺序；
新增**合成产物**正 / 负向测试与**工作流顺序**断言；**并给纯度脚本补 wheel `METADATA`
extras 检查**（`Provides-Extra` ⊆ `{"otlp"}`；`[otlp]` 闭包无 `certifi` / HTTP exporter /
元包），以兑现 FR-017 的「发行元数据」判据（T045）；**METADATA 解析只用标准库**
（`email.parser.Parser` + PEP 503 规范化，**MUST NOT import `packaging`**，因为发布流水线
用系统 `python3` 直接执行脚本）；同时**收紧 wheel 根级允许清单**为
`freegraph/` + `freegraph-*.dist-info/`（现脚本对任意 `freegraph-` 前缀放行，属已知缺口）。

**现状证据**：

| 项 | 现状 |
|---|---|
| 脚本（现状 + T045 收紧） | `harness/scripts/check_dist_purity.py`：**现状** wheel 允许 `freegraph/` + 任意 `freegraph-` 前缀；**T045 收紧为** `freegraph/` + `freegraph-*.dist-info/`（`freegraph-evil.txt` ⇒ 失败）；sdist 只允许 `src/freegraph/` + `{README.md, LICENSE, pyproject.toml, PKG-INFO}`（**`.gitignore` 不得放行**）；禁止目录含 `harness/` / `.specify/` / `.opencode/` / `.github/` / `specs/` / `tests/` 等 |
| 必需文件 | wheel：`freegraph/__init__.py` + `freegraph/py.typed`；sdist：`src/freegraph/__init__.py` + `README.md` + `LICENSE` + `PKG-INFO` |
| 空 / 缺目录 | 退出码 2 |
| 发布流水线 | `uv build` → `Verify artifact purity`（调用脚本）→ `uv publish --trusted-publishing always` |

**Rationale**：门禁已**独立于构建配置**（不读 `only-include`）；负向验证用 `zipfile` /
`tarfile` 合成产物即可，无需 `uv build`，测试快且可本地跑。顺序断言防止未来有人把
purity 步骤移到 publish 之后。

**Alternatives considered**：
- **在单元测试里真实 `uv build`** —— 拒绝：慢、依赖工具链与网络；CI 已有真实构建步骤。
- **只测正向** —— 拒绝：无法证明门禁能拦住污染。

> **2026-11-24 修订（I1 修复）**：`uv build` 实测会在输出目录自动生成 `dist/.gitignore`（内容 `*`）。
> 「额外产物」检查 MUST 只针对**归档类**非 `.whl` / `.tar.gz` 文件（`.zip` / `.tar` / `.tgz` / `.tar.bz2`），
> 并显式豁免 `dist/.gitignore`；否则干净的 CI 构建会被误判为污染。

---

## D-05 · 依赖与许可证：零依赖 + `[otlp]` 唯一 extra + `protobuf` 归一

**Decision**：不改依赖面；验证并复用既有 G21 / G23 口径。

**证据**：

| 项 | 现状 |
|---|---|
| 基础依赖 | `dependencies = []` |
| 唯一 extra | `otlp = ["opentelemetry-api>=1.20", "opentelemetry-sdk>=1.20", "opentelemetry-exporter-otlp-proto-grpc>=1.20"]` |
| 其它 extra | `pydantic` / `checkpoint` / `otel` / `png` 只在 `specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml`（不进发行包） |
| `protobuf` | `3-Clause BSD License`（散文标识）经**仅此一包**归一为 `BSD-3-Clause`（B21F1 · G23） |
| 禁用闭包 | `certifi` / `requests` / HTTP exporter / `opentelemetry-exporter-otlp` 元包 MUST NOT 出现 |

**Rationale**：宪法 v1.17.0 的唯一具名例外；G21 / G23 已实现；本 feature 只需断言不回退。

**Alternatives considered**：无（既有决策）。

---

## D-06 · README：能力表 + 链接 + 状态修正 + 英文关键段

**Decision**：README 删除完整兼容矩阵，新增：
1. 「能力 → freegraph 处置」表——**逐字复刻立项书 §3.2 的 5 列 + 8 行** + `as-of 2026-11-01`；
2. `## API 兼容矩阵` 章节改为**指针**（说明唯一权威在 `COMPAT.md` + **绝对 GitHub URL**）；
3. 顶部状态说明修正（保留「占位版本」客观事实，删除「内核尚未实现 / 没有任何运行时能力 / 请勿用于生产」）；
4. 英文覆盖关键段落（独立实现声明 / 三条承诺 / 安装与 `[otlp]` / 能力摘要 / `COMPAT.md` 链接）；
5. **保留 OTLP 段**：OpenLIT / Langfuse / Phoenix 三后端并列、**无默认推荐**（H-8③），
   以及既有 doc guard 所需字符串（`update_state` / `时间旅行已交付` / `只读快照` / `v1 不支持 Store` 等）。

> **2026-11-24 拍板**：三条承诺第三项 = **零第三方运行时依赖**（零 license key 并入零账号）。

**现状证据**：README 目前有完整符号矩阵（`## API 兼容矩阵`，约 27 行），**没有**「能力 → 处置」表
（`grep` 无命中）；顶部仍有「占位版 · 内核尚未实现」段落。

**Rationale**：D7 要求能力表在 README；A-3 要求 README 不维护第二份完整矩阵；两者可同时满足：
能力表 + 指针，完整矩阵在 `COMPAT.md`。

**Alternatives considered**：
- **README 保留完整矩阵** —— 拒绝（A-3）。
- **README 只有中文** —— 拒绝（FR-006 要求英文关键段）。

---

## D-07 · `THIRD_PARTY_NOTICES`：定稿与必需条目

**Decision**：保留现有两节结构（§1 引入代码 / §2 依赖 + 说明），核对并定稿：
`SqliteSaver` 的 MIT 改编（LangChain, Inc. 版权）+ `[otlp]` 闭包逐包 + v2 extra 计划说明。

**现状证据**：`THIRD_PARTY_NOTICES` 已有 §1（`langgraph-checkpoint-sqlite` 3.1.1 的 MIT 改编）
与 §2（`[otlp]` 闭包、v2 extras 说明）；`SqliteSaver` 源文件带改编署名。

**Rationale**：原则 X 要求「任何引入的第三方代码 MUST 进入清单」；现有内容已覆盖，
本 feature 只需补齐「定稿」状态与 B24F1 的维护注记，不新增依赖。

**Alternatives considered**：
- **登记 `langgraph==1.2.11`（differential）** —— 拒绝：测试侧、不进发行包（A-11）；登记反而误导。
- **把 `COMPAT.md` 当第三方归属** —— 拒绝：它是本项目文档，不是第三方代码。

---

## D-08 · `COMPAT.md` 结构：机读段与补充段分离

**Decision**：`COMPAT.md` 采用六段结构：

```text
# API 兼容矩阵
## API 兼容矩阵            ← 机读段（G8 / G19 / G29 取行）；affiliation 声明在段内
> 兼容意图为互操作，不构成 affiliation ...
## 18 项覆盖表             ← Q3 §3.4，逐项
## 下游承接行              ← MemorySaver … OtlpExporter
## 证据与来源              ← 路径:行号 / Q3 裁定 / feature 实测
## 维护规则                ← 活文档更新义务
```

**Rationale**：G8 / G19 只解析 `## API 兼容矩阵` 章节内首列为 `` `标识符` `` 的 4 列行，
且 G19 要求符号集合**恰为**契约层 ∪ 门面层。若把 18 项（首列为 `1`…`18`）或下游符号
（`MemorySaver` 等不在清单内）放进同一段，G19 的「整表恰为两层」判据会失败。
⇒ 补充内容放独立章节，机读段保持「两层 + 无清单外符号」。

**Alternatives considered**：
- **全部放一张表** —— 拒绝：会破坏 G19 的符号集合判据；要么放宽门禁（违反「判据不降」）。
- **下游符号补进契约清单** —— 拒绝：会改 L1 契约面（本 feature 零运行时改动）。

---

## D-09 · 证据可追溯：每行附来源

**Decision**：`COMPAT.md` 的每一行 MUST 在「差异说明」或独立「证据」列附来源：
Q3 §3.4 的裁定编号、上游 `路径:行号`、或对应 feature 的 spec / 测试锚点。

**Rationale**：宪法原则 VIII / 原则 X；spec FR-015 / SC-004。18 项表直接引用 Q3 §3.4 的 # 行；
下游行引用 B7F4 / B14F1 / B15F1 / B16F1 / B21F1 / B23F1 的 spec 与契约。

**Alternatives considered**：无（强制义务）。

---

## D-10 · 负向纯度验证：合成产物，不污染真实 `dist/`

**Decision**：在 `tmp_path` 中合成最小 wheel（zip）与 sdist（tar.gz）：
- 正向：只含允许文件 ⇒ 脚本退出码 0；
- 负向：注入 `harness/report.md`（或 `specs/...`）⇒ 退出码 1，并指出违规路径；
- 空目录 / 无产物 ⇒ 退出码 2；
- 负向用例 MUST NOT 修改仓库根的真实 `dist/`。

**Rationale**：脚本的判据只依赖产物内容；合成产物能精确覆盖「混入仓库文件」与
「空产物」两类边界，且无需真实构建。CI 的真实 `uv build` + purity 步骤仍保留。

**Alternatives considered**：
- **在测试里真实 `uv build`** —— 拒绝（慢 / 依赖）；CI 已覆盖。
- **只测脚本的纯函数** —— 拒绝：需要端到端退出码判据。

---

## D-11 · 人工验收与 B25F1 边界

**Decision**：`harness/verification/B24F1/acceptance.py` 一键跑：构建（可选）/ 纯度正负向 /
隔离安装 / `[otlp]` 安装 / 矩阵与 README 核对；`manual-verification.md` 记录实际输出。
**质量门禁 5 的真实模型轮与迁移说明归 B25F1**（按 v1.6.0 登记偏离 + 发起者追认 + 具名承接）；
**Y-01 文档记录亦由 B25F1（M4）承接**，运行时对齐归 v2。
**SC-008 的判定 MUST 由可自动核验的文档守卫承担**（宪法 v1.13.0）：
`tests/runtime/test_b24f1_manual_record_guard.py` 断言记录存在 / 五段式 / 非空 / 含必需实测输出，
且**排在记录写就之后**（**T046 → T039 → T042**），避免永久红。

**Rationale**：原则 V；spec FR-014 / SC-008。B24F1 是发行前置，B25F1 是 MVP 最终验收。

**Alternatives considered**：无（流程强制）。

---

## D-12 · 宪法原则 XI 的最小差分场景组

**Decision**：本 feature 虽为发行 / 文档单元、**不新增运行时行为**，仍 MUST 交付
`tests/differential/test_b24f1_matrix_parity.py` 的 **B24F1-D-01…D-03** 最小差分组：
`Command().goto` 缺省（Y-01）、`Send` 可变性（Y-03）、`get_state` 无快照（Y-02）。
该组**只断言矩阵所陈述的既有差异**与上游一致，**不要求对齐运行时**；上游缺席 ⇒ `pytest.skip`。

**Rationale**：宪法原则 XI 的「可验证出口」要求每个 feature 交付一组「上游 ↔ freegraph 同场景对跑」
的差分场景。纯文档 feature 不能以「零运行时改动」为由跳过该组；用最小差分组可同时满足
原则 XI、避免新增运行时能力、并让 `COMPAT.md` 的 Y-01 / Y-02 / Y-03 具备可执行证据。

**Alternatives considered**：
- **不新增、只复用既有套件** —— 拒绝：与本原则的「每个 feature MUST 交付一组」不一致；
- **修改宪法为文档 feature 开豁免** —— 拒绝：当前不需要放宽原则 XI；最小差分组即可合规；
- **在本 feature 对齐 Y-01 / Y-02 / Y-03** —— 拒绝：属运行时变更，超出本 feature 范围。
