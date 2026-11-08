# B3F1 · 项目脚手架 + extras 划分 + CI 门禁 —— 人工验证记录

**feature**: B3F1（M0 地基 · extras 划分 + `src/` 布局 + 10 条新门禁 G21–G30 + 7 作业 CI 矩阵）
**验收依据**: `specs/b3f1-scaffold-ci-gates/spec.md` · `plan.md` · `tasks.md`
**验收指南**: [`specs/b3f1-scaffold-ci-gates/quickstart.md`](../../../specs/b3f1-scaffold-ci-gates/quickstart.md)
**记录日期**: 2026-11-08
**记录人**: 实现者（单人串行推进 · 立项书 §5.2）

> **📌 本文件状态 = 已回填**（五段式：① 环境 ② 步骤 ③ 实际输出 ④ 结论
> ⑤ 遗留问题 + ⑥ 移交后续 feature）。
> 第 3 节粘贴的是**真实输出**（原样粘贴，非「符合预期」）；未实跑的平台 / 版本
> 逐条登记在第 5 节。
>
> **✅ 两条「发起者追认」均已作出**（T049 / T057 · 2026-11-08）—— 依宪法 v1.6.0
> 「质量门禁的分阶段落地与发起者追认」，追认由**发起者本人**作出，**实现者未代签**
> ⇒ 追认文字见 **§3.6**（T057 · 三条质量门禁缺口）与 **§5.1**（T049 · G3 占位填充）。
>
> **📌 订正记（2026-11-08 · 补索引行时发现）**：本提示语原为「**未代签** … ⇒ 见
> §3.6 与 §5 的待办项」，与 §3.6 / §5.1 里**已存在的追认文字**自相矛盾 ⇒
> 订正为现状（**仅订正表述** · 判据与结论一字未改）。

---

## 1. 环境

| 项 | 实际值 |
|---|---|
| 本机 Python | **3.12.3**（`/usr/bin/python3`）—— **仅用于跑门禁脚本本身** |
| 隔离 venv Python（**主判定档**） | **3.11.16**（`uv venv --python 3.11` ⇒ `.venv`） |
| 隔离 venv Python（**最高档**） | **3.14.7**（`uv venv --python 3.14` ⇒ `.venv314`） |
| 平台 | Linux 6.8.0-139-generic x86_64 |
| uv | **0.12.7**（x86_64-unknown-linux-gnu） |
| git | **2.43.0** |
| pytest | **9.2.0**（两个 venv 均为该版本；`pyproject.toml` 的 `[dependency-groups] dev` 装入） |
| packaging | **26.3**（开发期依赖 · SPDX 表达式解析；`packaging.licenses` 自 24.2 起存在） |
| freegraph 版本 | **0.0.3**（`pyproject.toml` 的 `version`） |
| `requires-python` | `>=3.11`（**无** `<` 上界） |
| **v1.0 的发行元数据** | **零依赖包名** —— 实测 `importlib.metadata.requires("freegraph")` == **`None`**（**整个为空**）· 构建产物的 wheel `METADATA` 里**没有任何 `Requires-Dist`** ⇒ **v1.0 真正零依赖**（裁定 26 · 宪法 v1.7.0） |
| v2.0 清单的目标闭包（**预验证对象** · 非 v1.0 依赖） | **恰好 12 个包**：`annotated-types` · `greenlet` · `opentelemetry-api` · `opentelemetry-sdk` · `opentelemetry-semantic-conventions` · `ormsgpack` · `playwright` · `pydantic` · `pydantic-core` · `pyee` · `typing-extensions` · `typing-inspection` |
| `unshare --net --map-root-user` | **本环境不可用**（实测：`unshare: 写失败：/proc/self/uid_map: 不允许的操作` —— 容器内无 `CAP_SYS_ADMIN`）⇒ 断网等价性的**命名空间**部分**未实测**（见 §5 遗留 #1） |

---

## 2. 步骤

> 逐条对应 `quickstart.md` 的 10 节。**命令可直接复制执行**。

| # | 场景 | 命令 | 关联判据 |
|---|---|---|---|
| 0 | 环境准备（**四条命令**） | `uv venv --python 3.11` → `uv pip install --python .venv --group dev` → `uv pip install --python .venv -e .` → `uv pip install --python .venv -e ".[pydantic,checkpoint,otel,png]"` | FR-001 / FR-004 |
| 1 | 脚手架（§1） | `python3 -c "import tomllib,pathlib;print(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['optional-dependencies'])"` · `grep -E 'requires-python' pyproject.toml` · `ls -l src/freegraph/py.typed && wc -c < src/freegraph/py.typed` | SC-002 / FR-002 / FR-003 |
| 2 | 依赖门禁（§2 · 含 ★ 负向验证） | `gate_G21_dependencies.py --project .../extras-v2.toml` · 同上 `gate_G22_isolated_env.py` · `gate_G23_licenses.py --project .../extras-v2.toml` · ★ `gate_G21_dependencies.py --self-test-negative` | SC-001 / SC-009 / SC-013 |
| 3 | 静态门禁（§3） | `gate_G24_config_layer.py` · `gate_G25_import_graph.py` · `gate_G26_network_static.py` · `gate_G30_attribution.py` | SC-002c / SC-012 / SC-008 / SC-016 |
| 4 | 运行时门禁（§4） | `gate_G27_zero_egress.py` · `gate_G28_offline_equiv.py`（**外层** `unshare --net --map-root-user`）· `gate_G29_contract_carrier.py` | SC-006 / SC-004 / SC-003 / SC-011 |
| 5 | 全量测试（§5） | `FREEGRAPH_TEST_INSTALLED=1 uv run --no-project --python .venv python -m pytest tests/ -ra` | 全部 |
| 6 | 矩阵模拟（§6） | 同上，但解释器换成 `.venv314`（3.14 档）+ §6.1 的矩阵形状核对脚本 | SC-002b / SC-012 |
| 7 | 分支保护（§7） | **发起者执行**（本机无 `gh` CLI、无 GitHub 令牌）⇒ 见 §3.4 的**可照抄步骤** | SC-015 |
| 8 | 兼容矩阵分层（§8） | `pytest tests/contracts/test_architecture.py -k compat_matrix -ra` · `pytest tests/facade/test_facade_gates.py -ra` · `gate_G29_contract_carrier.py --check-compat` | SC-011 |
| 9 | 常见失败处置（§9） | 逐条见 §3.7 | — |
| 10 | 完工检查表（§10） | 逐条见 §4 | 全部 |

### 2.1 人工验收清单（发起者照此跑 · 期望值已实测填好）

> **环境准备（一次性 · 四条命令）**：

```bash
uv venv --python 3.11
uv pip install --python .venv --group dev
uv pip install --python .venv -e .
uv pip install --python .venv -e ".[pydantic,checkpoint,otel,png]"
```

> **A · 脚手架**（期望：四个 extra + `requires-python` 无上界 + `py.typed` 为 0 字节）：

```bash
python3 -c "
import tomllib, pathlib
d = tomllib.loads(pathlib.Path('pyproject.toml').read_text())
print(d['project']['requires-python'])
for k, v in d['project']['optional-dependencies'].items():
    print(f'{k:12s} -> {v}')
"
ls -l src/freegraph/py.typed && wc -c < src/freegraph/py.typed
```

> **B · 十条门禁逐条跑**（期望：**每条退出码 0**，输出含 `PASS`）：

```bash
for g in G21_dependencies G22_isolated_env G23_licenses G24_config_layer G25_import_graph \
         G26_network_static G27_zero_egress G28_offline_equiv G29_contract_carrier G30_attribution; do
  uv run --no-project --python .venv python "harness/scripts/gates/gate_${g}.py" >/dev/null \
    && echo "OK   $g" || echo "FAIL $g"
done
```

> **C · ★ 负向验证（本 feature 的验收判据本体）** —— 期望：**退出码 0**（自检内部断言的是
> 「门禁**必须**失败」）+ 输出点名 `langchain-core` + **工作树逐字不变**：

```bash
uv run --no-project --python .venv python harness/scripts/gates/gate_G21_dependencies.py --self-test-negative
git status --porcelain        # 与跑之前逐字相同 ⇒ 工作树未被改动
```

> **D · 全量测试（两档 · 期望各 402 passed / 4 skipped）**：

```bash
FREEGRAPH_TEST_INSTALLED=1 uv run --no-project --python .venv python -m pytest tests/ -ra
uv venv --python 3.14 .venv314 && uv pip install --python .venv314 --group dev \
  && uv pip install --python .venv314 -e . \
  && uv pip install --python .venv314 -e ".[pydantic,checkpoint,otel,png]"
FREEGRAPH_TEST_INSTALLED=1 uv run --no-project --python .venv314 python -m pytest tests/ -ra
```

> **E · 兼容矩阵分层**（期望：前两条全绿；第三条输出「**未落地**」且**退出码 0**）：

```bash
uv run --no-project --python .venv python -m pytest tests/contracts/test_architecture.py -k compat_matrix -ra
uv run --no-project --python .venv python -m pytest tests/facade/test_facade_gates.py -ra
uv run --no-project --python .venv python harness/scripts/gates/gate_G29_contract_carrier.py --check-compat
```

> **F · 断网等价性（**可选** · 本机无命名空间权限 ⇒ 留待 CI 的 Linux 作业）**：

```bash
unshare --net --map-root-user uv run --no-project --python .venv python harness/scripts/gates/gate_G28_offline_equiv.py
# 本机实测：`unshare: 写失败：/proc/self/uid_map: 不允许的操作` ⇒ 需在有特权的 Linux 上跑
```

> **G · 分支保护（**只能由发起者在 GitHub 网页端做**）** —— 步骤见 **§3.4**（8 步）。

> **⚠️ 验收通过后请告知实现者**：由实现者补签 **§3.6 的 T057 追认块**与
> **§5 遗留 #2 的 T049 追认块**（追认文字 + 发起者确认 + 日期），并把
> `specs/b3f1-scaffold-ci-gates/tasks.md` 的 **T049 / T057** 勾上 —— 依宪法
> 「MUST NOT 由实现者代签」，该动作**必须**在发起者确认之后发生。

---

## 3. 实际输出

### 3.0 发起者对 4 处实现判断的确认（2026-11-08）

> 实现轮发现 4 处「需在冻结面附近做取舍」的地方 ⇒ **如实登记**（原则 VIII），
> 由**发起者**当场裁决。**发起者结论：按实现的推荐执行，本 feature 的做法获认可。**

| # | 判断 | 落地处 | 发起者结论 |
|---|---|---|---|
| ① | **G30 品牌资产的「禁止文案指纹」子域加 2 条具名例外**（**载体** = 契约本身 · **证据来源** = `harness/reports/Q7-…md`）—— 二者必然含那 3 段官方文案指纹，**不排除则门禁永久红**（违宪 v1.6.0 红线） | `harness/scripts/gates/_gatekit.py` 的 `BRAND_COPY_EXCLUDED_FILES` + 契约 G30 判定第 6 项的补注 | ✅ **认可**（已写死 · 具名 · 非「按需新增」的豁免入口） |
| ② | **`THIRD_PARTY_NOTICES` §2 以「说明文字」登记 extras 依赖、**不**加数据行** —— 既有门禁 **G8** 断言该表**无数据行**（加行即变红），且 T050 原文也只要求同步「说明文字」 | `THIRD_PARTY_NOTICES` §2 | ✅ **认可**（必装依赖仍为空集 · 原则 X 不受影响） |
| ③ | **C4 / C8 的挂载点新建 `tests/contracts/test_contract_regressions.py`**（仓库原先无此约定）—— 未来由 **B5F2** / **B8F1** 落地并把 `status=not-landed` 改成 `landed` | `tests/contracts/test_contract_regressions.py` | ✅ **认可**（G29 ③ 逐条解析 `GATE-MOUNT:` 标记） |
| ④ | **实现后行数实测 ≈ 8,987 行 vs 立项书估 1,100 行** —— 按「**登记，不改立项书**」写进 `plan.md`（沿用 B2F2 的行数口径做法） | `specs/b3f1-scaffold-ci-gates/plan.md` 的 Scale/Scope | ✅ **认可**（**不压缩** —— FR-016 ① 的可定位性优先） |

> **发起者的最终兜底**：`harness/demo/` 的验收脚本集（原则 III 的固定脚本）——
> 该资产**不受**本 feature 的任何取舍影响 ⇒ 四处判断即使将来需要回退，
> 兜底路径仍在。

### 3.1 零出站证据（**取自 `_gatekit` 的口径** · 裁定 19）

> **⚠️ MUST NOT 引用 `harness/demo/acceptance.py` 的 `EgressProbe` 结果** ——
> 它用的是**已被裁定 19 否决**的旧口径（栈里有 `freegraph/` 即框架出站）。
> 本记录的零出站证据**一律**取自 `harness/scripts/gates/_gatekit.py`
> （归因 = **第一个非标准库帧**）。

**G27 独立入口**（观测面 = 在 egress 监测下跑整个测试套件）：

```text
[G27] 当前观测面：测试套件执行期（尚不含内核运行时 —— 运行期待 M2）
[G27] 开始：在 egress 监测下跑整个测试套件（pytest tests/）
...
402 passed, 4 skipped in 17.84s
[G27] 框架出站 = 0 · 用户出站 = 2（记录在案，不判失败）
[G27] PASS —— 零出站动态断言（只观测不阻断 + 第一个非标准库帧归因）
```

**G22 验收环境**（环境② · `langchain-core` 已在场）：

```text
[G22] 隔离环境内的第三方包数 == 0（基础安装闭包为空集）
[G22] import freegraph 后 sys.modules 无 langchain 家族
[G22] 验收环境（langchain-core 已在场）里 import freegraph / freegraph.graph 后 sys.modules 仍无 langchain 家族
[G22] 验收环境里的框架出站 = 0（用户出站 = 0，记录在案不判失败）
[G22] PASS —— 隔离环境断言（依赖闭包为空集 + sys.modules 无 langchain 家族）
```

> **用户出站 = 2 的来源**：`socket.create_connection(...)` 内部再调一次
> `sock.connect(...)` ⇒ 两次调用都被记录 ⇒ 两条记录**都**被归因为「用户出站」
> （**框架出站 = 0**）⇒ 这是 SC-006 的**双向可验证**：用户主动出网**被记录在案
> 但不判失败**。

### 3.2 断网全绿证据（`unshare --net` 下的通过率）

> **⚠️ 本环境无法创建网络命名空间**（实测 `unshare: 写失败：/proc/self/uid_map:
> 不允许的操作`）⇒ **命名空间**这一层**未实测**；下表是 **G28 门禁脚本本身**的
> 实测输出（读清单 → 逐条转 `--deselect` → 跑全量套件 → 断言通过率 == 100%）。
> **断网**这一层由 CI 的 Linux 作业承担（`unshare --net --map-root-user`），
> 见 §5 遗留 #1。

```text
[G28] 排除项 = 3 条（逐条有理由）· 实际执行 = 403 / 收集到 406
[G28] ================ 399 passed, 4 skipped, 3 deselected in 12.58s =================
[G28] PASS —— 断网等价性（Linux 网络命名空间 · 全量测试套件 + 可机读排除清单）
```

**排除清单自校验**（清单漂移 ⇒ 指名报错）已由反向用例覆盖：
`tests/gates/test_gates.py` 与 G28 的 `--collect-only` 全集比对（规则 **G28-04**）。

### 3.3 M0 三个 feature 的补检结论（依赖声明 + import 图）

**补检对象**：`src/freegraph/contracts/**`（B1F1 / B2F1）·
`src/freegraph/graph.py` / `_stategraph.py` / `_primitives.py`（B2F2）。

**① 依赖声明与 import 面**（AST 扫描 · 与既有 G2 / G4 / G17 的范围一致）：

```text
=== M0 三 feature 的依赖声明 / import 面补检 ===
第三方 import = 0 条
langchain 家族 import = 0 条
环境变量读取 = 0 条
```

**② 层归属与方向**（对照 `contracts/layer-registry.md`）：

```text
=== 层归属与方向补检（对照 contracts/layer-registry.md）===
  src/freegraph/contracts/__init__.py        -> L1  src/freegraph/contracts/
  src/freegraph/contracts/errors.py          -> L1  src/freegraph/contracts/
  src/freegraph/contracts/graph.py           -> L1  src/freegraph/contracts/
  src/freegraph/contracts/protocols.py       -> L1  src/freegraph/contracts/
  src/freegraph/contracts/trace.py           -> L1  src/freegraph/contracts/
  src/freegraph/contracts/types.py           -> L1  src/freegraph/contracts/
  src/freegraph/graph.py                     ->  —  src/freegraph/graph.py
  src/freegraph/_stategraph.py               -> L3  src/freegraph/_stategraph.py
  src/freegraph/_primitives.py               -> L2  src/freegraph/_primitives.py
```

**结论**：**无违规**。
① 零 langchain 家族 / 零第三方 import / 零环境变量读取；
② 全部 9 个模块的层归属与注册表**逐条一致**，**未发现反向 import**
⇒ **无需修正**，**未触及任何冻结面**（C1–C27 / 门面 7 符号 / API 快照 **零改动**）。

> **同层 import 的既有形态**：`src/freegraph/contracts/__init__.py` → `.errors` /
> `.graph` / `.protocols` / `.trace` / `.types` 属 **L1 → L1 同层** ⇒ 按
> 层注册表 §0.2 规则 2「**同层 import 仅 L1 与 L6 允许**」**合法**
> （若按「层编号严格递增」实现，G25 上线当天即把**已冻结的契约层**判红 ⇒
> 违反 PR-4）。

### 3.4 分支保护的设置步骤与状态取证

> **执行方 = 发起者**（本机**无 `gh` CLI、无 GitHub 令牌** —— 实测）⇒
> 下列步骤**可照抄**；**本记录不代为设置**（FR-020 ①）。

**① 必过检查（7 个）—— 逐字取自 `contracts/ci-matrix.md` §4.1**：

| 检查名 | 出现在 | 必过？ |
|---|---|---|
| `gates (ubuntu-24.04, 3.11)` | 作业 1 | ✅ |
| `gates (ubuntu-24.04, 3.14)` | 作业 2 | ✅ |
| `gates (macos-15, 3.11)` | 作业 3 | ✅ |
| `gates (macos-15, 3.14)` | 作业 4 | ✅ |
| `gates (windows-2025, 3.11)` | 作业 5 | ✅ |
| `gates (windows-2025, 3.14)` | 作业 6 | ✅ |
| `gates (ubuntu-24.04-arm, 3.11)` | 作业 7 | ✅ |

> **⚠️ MUST NOT 另抄一份**（清单**回指** `contracts/ci-matrix.md` §4.1）——
> 两份一旦漂移，分支保护即失效（job 名按**精确匹配**生效）。
> `ci.yml` 的 job 名**由矩阵展开**产生 ⇒ §6.1 的核对脚本逐字比对过（见 §3.5）。

**② 设置步骤（浏览器可照抄）**：

1. 打开 `https://github.com/yangjiacheng1996/freegraph/settings/branches`；
2. 找到 **`main`** 分支 → **Add rule** → **Require status checks to pass before merging**；
3. 在 **status checks** 里**逐个**填入上表 7 个检查名（**必须逐字**；填错 ⇒
   匹配不到任何检查 ⇒ 分支保护**静默失效**）；
4. 勾选 **Require branches to be up to date before merging**（保持线性历史）；
5. 勾选 **Require conversation resolution before merging**（可选）；
6. 勾选 **Do not allow bypassing the above settings**（管理员也必须遵守 —— 否则
   红线可被管理员绕过）；
7. （可选）勾选 **Require signed commits** / **Require linear history**；
8. **保存**。

**③ 启用后的状态取证**（**发起者已确认 · 2026-11-08**）：

```text
发起者确认：分支保护已按上表 7 个必过检查名在 GitHub 网页端设置（保护分支 main ·
          「必须先通过检查才能合并」·「要求分支保持最新」·「管理员也必须遵守」）。
证据形态：**发起者确认** —— 本环境无 gh CLI、无 GitHub 令牌 ⇒ 实现者**无法**独立取证
          （FR-020 ① 的「不代为设置」纪律仍在：实现者未触碰任何 GitHub 设置）。
```

> **⚠️ 纪律留痕**：本条的实现方**只**交付了「可照抄的设置步骤」（FR-020 ②），
> **未代为设置**（FR-020 ①）⇒ 状态证据的形态是**发起者确认**，
> 而非实现者取证 —— 此区别如实登记（原则 VIII）。

**④ 文档兜底**（FR-020 ⑤ · 分支保护未启用期间的**人工**保障）：
`README.md` 的「**开发与验收**」章节已写「**合入前 CI 必须全绿**」
⇒ **MUST NOT** 替代上述设置步骤。

### 3.5 逐条门禁的实测输出（10 条 · 退出码即判定）

```text
[G21] PASS —— 依赖闭包黑名单（声明级 · 含全部 extras 变体）           退出码 = 0
[G22] PASS —— 隔离环境断言（依赖闭包为空集 + sys.modules 无 langchain 家族）  退出码 = 0
[G23] 被检查的包数 = 12（并集口径：闭包包集 ∪ 取证作用域根下扫到的 dist-info）
        —— 闭包来源 = **v2.0 清单**（`--project .../extras-v2.toml` · 裁定 26）
[G23] PASS —— 许可证白名单（4 级证据链 · 5 个精确 SPDX id）            退出码 = 0
[G24] PASS —— 配置层（LANGSMITH_* / LANGCHAIN_* / LANGGRAPH_* 零读取 + 内核零环境变量）  退出码 = 0
[G25] PASS —— 导入图单向（ARCH-1 · 层注册表驱动）                      退出码 = 0
[G26] PASS —— 网络静态扫描（src/freegraph/** 无网络客户端调用）          退出码 = 0
[G27] PASS —— 零出站动态断言（只观测不阻断 + 第一个非标准库帧归因）      退出码 = 0
[G28] PASS —— 断网等价性（Linux 网络命名空间 · 全量测试套件 + 可机读排除清单） 退出码 = 0
[G29] PASS —— 契约门禁载体（只读基准 diff + C4 / C8 挂载点 + 验收脚本集退出码）  退出码 = 0
[G30] 受版本控制的 .py 文件数 = 52（具名例外：['harness/demo/target.py', 'src/freegraph/py.typed']）
[G30] PASS —— 全仓署名头（覆盖率 == 100%）+ 第三方品牌资产（FR-021）      退出码 = 0
```

**★ 负向验证（验收判据 A1 · 引文 §6「门禁生效」· 对应执行闸口 **A2**）**：

```text
$ uv run --no-project --python .venv python harness/scripts/gates/gate_G21_dependencies.py --self-test-negative
[G21] 自检通过 —— 注入 langchain-core 后门禁**失败**并点名：
  违规条目: langchain-core
  规则编号: G21-07
  细节    : 未安装 ⇒ 无法取证（出现在变体：基础安装、仅 [pydantic]、仅 [checkpoint]、仅 [otel]、仅 [png]、全部 extras 同时启用）——递归展开 MUST 走到闭包末端
  修复指引: 先安装该传递依赖再跑本门禁（CI：uv pip install --python .venv -e ".[pydantic,checkpoint,otel,png]"）
  违规条目: langchain-core
  规则编号: G21-04
  细节    : 命中规则：全部 provider 包（前缀 langchain-）（出现在变体：基础安装、仅 [pydantic]、仅 [checkpoint]、仅 [otel]、仅 [png]、全部 extras 同时启用）
  修复指引: 移除该依赖——provider 包会把 langchain-core 拉回来（宪法原则 II）
退出码 = 0
```

> **退出码语义**：**自检通过 ⇒ 退出码 0**（其内部断言的是「门禁**必须**失败」）
> ⇒ 该命令可安全地作为 CI 的一步。
> **工作树逐字不变**（SC-010 · 裁定 9）：由
> `tests/gates/test_gates.py::test_g21_self_test_negative_end_to_end` 以
> `git status --porcelain` 的**前后对比**断言（工作树本就有未提交改动 ⇒
> 「干净」不是判据）。

**矩阵形状核对（§6.1）**：

```text
矩阵档位数 = 7
  gates (ubuntu-24.04, 3.11)
  gates (ubuntu-24.04, 3.14)
  gates (macos-15, 3.11)
  gates (macos-15, 3.14)
  gates (windows-2025, 3.11)
  gates (windows-2025, 3.14)
  gates (ubuntu-24.04-arm, 3.11)
job 名模板 = gates (${{ matrix.runner }}, ${{ matrix.python }})
展开后的 job 名与契约 §4.1 逐字一致： True
runner 标签含 latest： False
```

**双档验证（§6 · T052）**：

```text
$ FREEGRAPH_TEST_INSTALLED=1 uv run --no-project --python .venv python -m pytest tests/ -ra -q
402 passed, 4 skipped in 17.91s          ← CPython 3.11.16（主判定档 · typing 构件上限 = 3.11）

$ FREEGRAPH_TEST_INSTALLED=1 uv run --no-project --python .venv314 python -m pytest tests/ -ra -q
402 passed, 4 skipped in 19.12s          ← CPython 3.14.7（最高档）
```

**基础安装闭包（§1.1）**：

```text
Requires-Dist = ["ormsgpack>=1.0; extra == 'checkpoint'", "opentelemetry-api>=1.20; extra == 'otel'",
                 "opentelemetry-sdk>=1.20; extra == 'otel'", "playwright>=1.40; extra == 'png'",
                 "pydantic>=2.0; extra == 'pydantic'"]
无 extra 标记的条目数 = 0 []
```

**兼容矩阵分层（§8）**：

```text
$ uv run --no-project --python .venv python harness/scripts/gates/gate_G29_contract_carrier.py --check-compat
[G29] COMPAT.md：**未落地**（非阻断）——终版兼容矩阵归后续 feature；已入库的 README「API 兼容矩阵」章节
由既有门禁 G8 / G19 严格比对（只接线 · 判据零改动）
退出码 = 0
```

### 3.6 三条宪法质量门禁缺口的登记与追认状态

> 宪法「质量门禁 3 / 4 / 5」三项在本 feature **不适用** —— 三者**共享同一根因**：
> 「MVP 验收基线的跑通需要**内核运行时**，而内核运行时按 立项书 §6.2 属 **M2**
> （固定脚本最小交付集 = B6F1 / B7F2 / B7F3 / B8F1 / B22F1 / B23F1）；
> 本 feature 是 **M0 地基** feature、**不交付内核功能**」。

| # | 被偏离的门禁项 | 本 feature 的处置 | 承接方 | 追认状态 |
|---|---|---|---|---|
| ① | 宪法质量门禁 **3** 的「MUST 包含 **C4** 与 **C8** 两条独立回归测试」 | **不适用**（C4 → M1/B5F2 · C8 → M2/B8F1）⇒ 只落**挂载点**并**明确标「未落地」**（`tests/contracts/test_contract_regressions.py` 的 `GATE-MOUNT:` 标记 · 由 **G29 ③** 逐条解析） | **B5F2**（C4 · M1）/ **B8F1**（C8 · M2） | ✅ **已追认（2026-11-08 · T057）** |
| ② | 宪法质量门禁 **4** 的「**fake 模型**跑通验收基线的一轮」 | **不适用**（内核运行时未接线 · `StateGraph``add_node`` 抛 `NotImplementedError`）⇒ 以 **G29 ②** 的「退出码 ∈ {0,1,2} + **按失败来源细分**」**部分落地**（实测：三个脚本退出码全为 1 且失败**全部**源于 `NotImplementedError` ⇒ 判为**环境未就绪** ⇒ 绿） | **B7F2**（fake 注入） | ✅ **已追认（2026-11-08 · T057）** |
| ③ | 宪法质量门禁 **5** + 原则 V 的「人工记录含**真实模型一轮**」 | **不适用**（无图可跑）⇒ 以本记录的**五段式** + 零出站证据（§3.1）+ 断网全绿证据（§3.2）覆盖 | **B25F1**（双跑验收） | ✅ **已追认（2026-11-08 · T057）** |

**判据未被放宽的论证**：宪法原则 I / II / IX 的**红线**（依赖红线 · 许可证红线 ·
商标红线 · 零出站红线）在本 feature **全部**落地（G21 / G23 / G24 / G26 / G27 /
G30 · 见 §3.5）⇒ 被延后的**只有**「依赖内核运行时」的**能力型**门禁项 ⇒
符合宪法 v1.6.0「质量门禁的分阶段落地与发起者追认」的适用范围（窄口径）。

**追认记录（T057 · 发起者已填写 · 2026-11-08）**：

```text
追认文字：三条宪法质量门禁缺口（门禁 3 的 C4 / C8 回归 · 门禁 4 的 fake 模型轮 ·
          门禁 5 + 原则 V 的真实模型轮）在本 feature（B3F1 · M0 地基 · 不交付内核
          功能）**均不适用**；本 feature 已按宪法 v1.6.0「质量门禁的分阶段落地与
          发起者追认」落**挂载点**并明确标「未落地」，红线判据一条未放宽 ⇒ **准予追认**。
          承接方：C4 → B5F2（M1）· C8 → B8F1（M2）· fake 轮 → B7F2（M2）·
          真实模型轮 → B25F1（M4）。
发起者确认：杨家成（发起者）——「验证通过，同意本 feature 的做法」
日期：2026-11-08
```

> **⚠️ 签名的时序**：本块由**发起者**在人工验收通过后填写 ⇒ 实现者**只负责
> 转录与勾选**，MUST NOT 预签（MUST NOT 由实现者代签 · 宪法 v1.6.0）。

### 3.9 修订轮记录：**v1.0 零依赖**（2026-11-08 · 裁定 26 · 宪法 v1.7.0 · 发起者已决）

> **发起者的产品决定**：「freegraph v1.0 不希望看到依赖包，所有依赖包放到 v2.0；
> 如果这个浏览器是必要的，也需要我们互动调研后决策。」

**决策与落地**

| # | 项 | 处置 |
|---|---|---|
| ① | **v1.0 的发行元数据** | **零依赖包名** —— `pyproject.toml` **移除** `[project.optional-dependencies]`；实测 `requires("freegraph")` == **`None`**；构建产物的 wheel `METADATA` 里**无任何 `Requires-Dist`** |
| ② | **四个 extra 的声明** | 移入仓库内的 **`contracts/extras-v2.toml`**（**不进发行包** · **刻意与 `pyproject` 同构** ⇒ 门禁解析器零改动即可消费） |
| ③ | **门禁的判据对象** | **G21 / G23 对该清单取证**（G23 新增 `--project` 参数，**同名同义**于 G21 的 `--project`）⇒ **v1.0 即完成预验证**：实测 **被检查 12 个包**（**非空门禁** ✓） |
| ④ | **CI** | 步骤 5.5 改为「**v2.0 预验证依赖**」（直接装 5 个包 · **不是** v1.0 的依赖 · 不进发行包 / 不进 `Requires-Dist`）；步骤 7 的 G21 / G23 追加 `--project .../extras-v2.toml` |
| ⑤ | **既有门禁 G3** | 12 名白名单**一字未改**（**T049 的追认依然有效**）· 仅补注适用版本为「**v2.0 的目标闭包**」⇒ v1.0 为**空断言** · v2.0 落地时**自动变实质**（门禁零改动） |
| ⑥ | **`[png]` 的真 PNG 渲染** | **渲染后端方向留待 v2.0 专项调研后决策**（候选与代价见 `research.md` **D-16** 与立项书 §5.5 的 PNG 方案表）⇒ v1.0 只出**占位 PNG**（自研最小编码器 · 零依赖） |
| ⑦ | **红线** | **一条未动**：原则 IX 的许可证白名单与包层黑名单仍**逐包**适用（对 v2.0 清单**立即**生效）⇒ **违规的依赖进不了 v2.0**（比 v2.0 开工后再发现**更早**） |

**修订轮的实测输出**

```text
$ uv pip install --python .venv -e . && uv run --no-project --python .venv python -c \
    "import importlib.metadata as m; print(m.requires('freegraph'))"
Requires-Dist = None                      ← v1.0 零依赖包名（更强：整个为空）

$ uv run --no-project --python .venv python harness/scripts/gates/gate_G21_dependencies.py \
    --project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml
[G21] PASS —— 依赖闭包黑名单（声明级 · 含全部 extras 变体）      退出码 = 0

$ uv run --no-project --python .venv python harness/scripts/gates/gate_G23_licenses.py \
    --project specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml
[G23] 被检查的包数 = 12（并集口径：闭包包集 ∪ 取证作用域根下扫到的 dist-info）
[G23] PASS —— 许可证白名单（4 级证据链 · 5 个精确 SPDX id）      退出码 = 0

$ python3 -c "…读 dist/*.whl 的 METADATA…"
Name: freegraph
Version: 0.0.3                             ← **无任何 Requires-Dist** ⇒ 发行物真正零依赖

$ FREEGRAPH_TEST_INSTALLED=1 uv run --no-project --python .venv python -m pytest tests/ -ra -q
405 passed, 4 skipped                      ← 3.11 档（修订轮后新增 3 条断言）
$ FREEGRAPH_TEST_INSTALLED=1 uv run --no-project --python .venv314 python -m pytest tests/ -ra -q
405 passed, 4 skipped                      ← 3.14 档
```

**修订轮的落地清单**（tasks **T058–T066**）：宪法 v1.7.0 · `pyproject.toml` ·
`contracts/extras-v2.toml`（新建）· `gate_G23_licenses.py`（`--project`）· `ci.yml` ·
`tests/gates/test_gates.py` · spec 裁定 26 · 三份契约 + `data-model.md` ·
`research.md`（D-16 + DR-8）· `plan.md` · `tasks.md` · `quickstart.md` ·
`README.md` · `THIRD_PARTY_NOTICES` · 立项书（D14 修订 + **D15** 新增）·
`harness/prompts/init_constitution.md` · 本记录。

### 3.7 来源覆盖表（宪法原则 VIII）

| 结论 | 来源标记 |
|---|---|
| 四个 extra 的完整闭包 = **12 个包** | 本机实测（`uv pip install -e ".[pydantic,checkpoint,otel,png]"` ⇒ 13 个包，其中 freegraph 自身 ⇒ 12 个传递依赖）；与 `specs/b3f1-scaffold-ci-gates/research.md` **D-02** 的实测表逐条一致 |
| 各包许可证标识（`MIT` / `Apache-2.0 OR MIT` / `MIT AND PSF-2.0` / `PSF-2.0` …） | 本机实测 `importlib.metadata.metadata(pkg).get("License-Expression")`；与 research **D-05** 的实测表逐条一致 |
| G3 的白名单子集断言变绿 | 本机实测（`pytest tests/contracts/test_architecture.py -k "closure or license"` 全绿） |
| G25 的同层口径（L1 / L6 允许 · L2–L5 禁止） | 层注册表 §0.2 规则 2 + `data-model.md` §5.2 的真值表 + 本 feature 的**四条反向用例**（L1→L3 红 · 跨层→L2 红 · L2→L2 红 · L1→L1 绿 · L6→L6 绿） |
| G29 的退出码口径（1 + 全 `NotImplementedError` ⇒ 环境未就绪） | 本机实测三个验收脚本的退出码与输出（§3.5 的 G29 段） |
| G27 / G28 的归因口径（第一个非标准库帧） | 裁定 19 + research **D-11**；本 feature 的**四形态合成栈**单元断言 + **一次真实用户出站**实测 |
| 断网排除清单 = **3 条** | `tests/gates/data/offline_exclusions.txt` + `contracts/ci-matrix.md` §3.2 的 `--deselect` 展开式（**逐字一致**） |
| 第三方品牌资产的「禁止文案指纹」3 条 | `harness/reports/Q7-开源边界地图与许可证合规.md` §3.3.3（来源 **D10** · `https://www.langchain.com/brand-assets` · as-of **2026-11-01**） |
| 「禁止色值清单」= **空集** ⇒ **待取证** | 官方品牌色值**尚未逐字取证**并落入本仓库 ⇒ **MUST NOT** 凭记忆写入 hex（原则 VIII） |
| 分支保护未代为设置 | 本机**无 `gh` CLI、无 GitHub 令牌**（实测）⇒ 只能交付可照抄的步骤（FR-020 ①） |

### 3.8 常见失败与处置（§9）的实测取证

| 症状 | 复现 | 实测结果 |
|---|---|---|
| G21 报「`langchain-core` 违规」 | `--self-test-negative` | ✅ 指名包名 + 规则编号 + 修复指引（§3.5） |
| G23 报「取不到许可证明」 | 注入 `bare-pkg-1.0.0.dist-info/METADATA`（无任何许可字段） | ✅ 失败并指名 `bare-pkg`（反向用例） |
| G23 报「`MPL-2.0` 不在白名单」 | —— | ✅ 叶子判定（`MPL-2.0` ∉ 5 个白名单 id）⇒ 由白名单比对拦下 |
| G23 报「`3-Clause BSD License` 无法解析」 | —— | ✅ SPDX 解析抛 `SpdxParseError` ⇒ 判失败（**不**引入映射表 · 裁定 18） |
| G25 报「层 L1 反向 import L3」 | 注入 L1 模块 import L3 | ✅ 失败并指名（反向用例） |
| G26 报「`socket` 违规」 | 注入 `import socket` | ✅ 失败并指名文件 + 行号（反向用例） |
| G27 报「框架出站 > 0」 | —— | ✅ 框架出站恒为 0（§3.1） |
| G30 报「缺署名头」 | 删掉副本文件的首行 | ✅ 失败并指名该文件（反向用例） |
| G30 报「第三方品牌资产」 | 注入第三方 `.svg` | ✅ 失败并指名该文件（反向用例） |
| G23 输出「被检查 0 个包」 | —— | ✅ 实测 **12 个包** ⇒ **非空门禁**（违宪防护的反向用例） |
| G28 报「通过率 < 100%」 | —— | ✅ 实测 100%（§3.2）；清单漂移 ⇒ 指名报错（规则 G28-04） |
| 3.11 档报 `ImportError` | —— | ✅ 两档全绿（§3.5） |

### 3.10 **CI 首跑 → 7/7 全绿**的实测与修复（2026-11-08）

> **三轮**（每轮都是 7 个作业）：**第 1 轮**（`e82a8a7`）macOS × 2 成功、
> ubuntu × 3 与 windows × 2 失败；**第 2 轮**（`6eb6989`）**ubuntu × 3 全绿**
> （断网任务在 GitHub runner 上真跑通了）、windows × 2 仍失败；
> **第 3 轮**（`e35b55e`）**7/7 全绿** ✅。
>
> **诊断手段**（值得沉淀）：GitHub 的「下载作业日志」接口**需要 admin 权限** ⇒
> 外部拿不到日志 ⇒ ① 用 REST API 的 **作业 / 步骤结论**定位到失败的**步骤**；
> ② 增设**诊断通道**——pytest 的失败逐条输出为 **GitHub 注解**
> （`::error title=…::…`，见 `tests/conftest.py`）⇒ 可经 REST API 的
> `check-runs/{id}/annotations` **免鉴权直读** ⇒ 拿到了确切的失败用例。
>
> **第 1 轮的两个失败面**（**平台性**问题，非门禁判据问题）：

| 失败面 | 根因（实测） | 处置 |
|---|---|---|
| **ubuntu × 3** 止步于 **Gate G28（offline equivalence）** | **Ubuntu 24.04 的发行版级限制**：默认启用 AppArmor 的「限制非特权用户命名空间」策略（`kernel.apparmor_restrict_unprivileged_userns=1`）⇒ `unshare --map-root-user`（需要**用户命名空间**）对普通用户直接 `Operation not permitted` ⇒ **该步骤必红** | CI 步骤先 `sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0`（解除**发行版级策略**）⇒ 命名空间仍以**非特权**方式创建（`--map-root-user` · 免 `CAP_SYS_ADMIN`）⇒ **设计前提不变**；另加「命名空间创建能力自检」，失败时给出**指名**的 `::error::` 而非裸红 |
| **windows × 2** 止步于 **Run test suite** | **Windows 的输出编码**：控制台 / 管道默认 **cp1252 / cp936** ⇒ ① **打印**中文（门禁报告 · pytest 的 skip 理由 · `harness/demo/*.py` 的验收输出）会 `UnicodeEncodeError`；② **读取**中文输出会 `UnicodeDecodeError` ⇒ **既有** `tests/facade/test_facade.py` 的两条验收脚本用例即崩（**实测**：本地用 `PYTHONIOENCODING=cp1252` 复现了同一处 `UnicodeDecodeError`） | ① CI 的 job `env:` 设 **`PYTHONUTF8=1`**（UTF-8 模式 · 三个平台统一）· ② `_gatekit.configure_stdio()` 把门禁自己的 stdout/stderr 切到 UTF-8（**脱离 CI 也能跑**）· ③ 门禁与测试里的**全部子进程**显式 `encoding="utf-8", errors="replace"` + 给子进程设 `PYTHONIOENCODING=utf-8` · ④ 既有的 `tests/contracts/test_architecture.py` / `tests/facade/_gatesupport.py` / `tests/facade/test_facade.py` 三处子进程执行器**同源加固**（**判据零改动** —— 只是解码口径） |

| **windows × 2**（止步于 **Run test suite**）—— **换行符**：Windows 上的 Git 默认 `core.autocrlf=true` ⇒ 检出时把 **LF 转成 CRLF** ⇒ 破坏既有门禁 **G16** 的「API 快照**逐字节**比对」与快照文本合规判据（`tests/facade/test_api_snapshot.py::TestSnapshotTextCompliance::test_line_endings_are_lf` ⇒ 快照 MUST 用 LF）⇒ 连带 `test_update_entry_point_is_off_by_default`（它在子进程里再跑一次该文件 ⇒ 连带失败） | **新增 `.gitattributes`**（`* text=auto eol=lf`）⇒ 换行口径**固定在仓库里**（不依赖每个开发者的本地 git 配置）⇒ 三个平台的检出**逐字节一致** ⇒ 快照类判据在任何平台都成立。**实测**：用 `core.autocrlf=true` 克隆后检出 ⇒ 快照**不含** CRLF ✅ |

**本地复现与验证**（不等 CI）：

```text
$ PYTHONIOENCODING=cp1252 FREEGRAPH_TEST_INSTALLED=1 uv run --no-project --python .venv python -m pytest tests/ -q
  # 修复前：2 failed, 403 passed（UnicodeDecodeError · tests/facade/test_facade.py 的两条验收脚本用例）
  # 修复后：405 passed, 4 skipped
$ PYTHONIOENCODING=ascii LC_ALL=C LANG=C … pytest tests/ -q
  405 passed, 4 skipped          ← 最严模拟（ASCII 输出 + C locale）
$ PYTHONIOENCODING=cp1252 … gate_G21_dependencies.py   → PASS（退出码 0）
$ PYTHONIOENCODING=ascii  … gate_G30_attribution.py    → PASS（退出码 0）
```

> **判据未被改动**：本次修复**只动「输出编码 / 命名空间创建的前置 / 换行口径」**，
> **G1–G30 的任何判据句都未变**（既有门禁只改了子进程的**解码口径**，判据逻辑逐字未动；
> `.gitattributes` 是**让工作树满足既有判据**，不是放宽判据）。

**第 3 轮结果（7/7 全绿）**：

```text
gates (ubuntu-24.04, 3.11)       success
gates (ubuntu-24.04, 3.14)       success
gates (ubuntu-24.04-arm, 3.11)   success
gates (macos-15, 3.11)           success
gates (macos-15, 3.14)           success
gates (windows-2025, 3.11)       success
gates (windows-2025, 3.14)       success
```

> ⇒ **§5 遗留 #1**（断网等价性的「命名空间」层）**已由 CI 证实**：Linux 作业在
> `unshare --net --map-root-user` 下**通过率 == 100%**（G28 步骤绿）⇒ 该层**不再是遗留**；
> **§5 遗留 #10**（macOS / Windows 作业）**已实测全绿** ⇒ 该项**关闭**。

---

## 4. 结论

**总体结论：B3F1 的交付成立** —— 逐条对照 spec 的 **21 条 FR** 与 **18 条 SC**：

| 维度 | 结论 |
|---|---|
| **脚手架** | 四个 extra 已声明且**各自独立可选**；基础安装闭包**为空集**（无 marker 的 `Requires-Dist` 条目数 == 0）；`requires-python = ">=3.11"` 且**无上界**；`py.typed` 存在且**大小 == 0** |
| **10 条新门禁** | G21–G30 **逐条**退出码 **0**（§3.5）；每条都是**可独立执行**的检查（退出码即判定） |
| **8 条强制反向用例**（SC-009） | 全部**实测通过**（注入 ⇒ 门禁失败且指名 ⇒ 撤销 ⇒ 通过）⇒ 门禁**确实生效**（不是「恰好没触发」） |
| **零出站** | 「框架出站 = 0」在**测试套件执行期**与**验收环境**两处实测（§3.1） |
| **隔离环境** | 基础安装闭包 == 空集；`sys.modules` 无 langchain 家族（场景①与场景②） |
| **CI 矩阵** | 7 档矩阵 · runner 标签钉死 · job 名与契约 §4.1 **逐字一致**（§3.5） |
| **既有门禁** | G1–G20 **判据零改动**（唯一例外 = **G3 的占位填充**，见 §5 遗留 #2 · **待追认**） |
| **双档验证** | 3.11 与 3.14 两档**各跑一次**全量测试，均 **402 passed / 4 skipped** |
| **M0 补检** | 三个 feature 的依赖声明与 import 图**无违规**（§3.3） |

**质量门禁 7 项的落地复核（SC-003 · T055）**：

| # | 质量门禁 | 对应断言 | 是否全自动 | 状态 |
|---|---|---|---|---|
| ① | **规格门禁** | `specs/b3f1-scaffold-ci-gates/spec.md` 存在且非空 + `tasks.md` 可逐条勾选 + `tests/gates/test_gates.py::test_quality_gate_artifact_existence`（**存在性**检查） | **半自动**（存在性自动 / 内容复核人工） | ✅ 已通过 |
| ② | **依赖门禁**（红线 · 阻断） | **G21**（依赖黑名单）· **G23**（许可证白名单）· **G24**（配置层）· **G26**（网络静态） | **全自动** | ✅ 已通过 |
| ③ | **契约门禁** | **G29**（只读基准 diff + 验收脚本集退出码 + **C4 / C8 挂载点**） | **全自动**（**MUST 包含 C4 与 C8** 一项**本 feature 不适用** ⇒ 只落挂载点并标「未落地」⇒ **偏离登记** ⇒ 追认状态见 §3.6） | ⚠️ **偏离已登记 · 待追认** |
| ④ | **自动门禁** | **CI 全绿**（7 作业 × 步骤 6）+ **G27** 的零出站断言（**只观测不阻断 + 按发起方归因**） | **全自动**（**fake 模型跑通验收基线的一轮**一项**本 feature 不适用** ⇒ 以 G29 ② 的退出码细分**部分落地** ⇒ **偏离登记** ⇒ 见 §3.6） | ⚠️ **偏离已登记 · 待追认** |
| ⑤ | **人工门禁** | **本文件**（五段式齐全）+ **零出站证据**（§3.1）+ **断网全绿证据**（§3.2） | **人工**（**含真实模型一轮**一项**本 feature 不适用**（无图可跑）⇒ 以五段式 + 上述两项实测证据覆盖 ⇒ **偏离登记** ⇒ 见 §3.6） | ⚠️ **偏离已登记 · 待追认** |
| ⑥ | **证据门禁** | §3.7 的**来源覆盖表**（存在且非空 ⇒ 由 `test_quality_gate_artifact_existence` 断言） | **半自动**（存在性自动 / 来源正确性人工） | ✅ 已通过 |
| ⑦ | **文档合规门禁** | **T050**（`THIRD_PARTY_NOTICES` §2 的说明文字已同步 · **必装依赖仍为空集**）+ **T051**（README 的「可选依赖（extras）」章节）+ 既有 **G8 / G19**（兼容矩阵逐字未动） | **全自动** | ✅ 已通过 |

> **⚠️ ③④⑤ 三项 MUST NOT 记成「已通过」** —— 上表逐条写明了
> 「**本 feature 不适用 + 偏离登记 + 追认状态**」（宪法 v1.6.0）。

### 4.1 完工检查表（quickstart §10 · 逐条）

- [x] `pytest tests/ -ra` **全绿** —— **402 passed / 4 skipped**（3.11 与 3.14 两档各一次）
- [x] **环境已按 §0.1 准备**：dev 组已装 + 发行形态已装 + **四个 extras 的依赖已装齐**（12 个传递依赖）
- [x] 10 条新门禁**逐条**退出码 **0**（§3.5）
- [x] 负向验证：**门禁失败** + **工作树逐字不变**（`--self-test-negative` 自检**通过 ⇒ 退出码 0**）
- [x] 3.11 档与 3.14 档**各跑一次**全量测试，均全绿
- [x] `git ls-files '*.py'` 的**顶部**署名头覆盖率 == **100%**（**首行或 shebang 之后**；除 `target.py`）—— 实测 **52** 个受版本控制的 `.py`，**零**违规
- [x] 基础安装**无 `extra ==` 标记的 `Requires-Dist` 条目数 == **0**（**口径订正** · 声明 extras 后 `Requires-Dist` **非** `None`）
- [x] `ci.yml` 矩阵档位数 == **7** · runner 标签**无浮动** · 展开后的 7 个 job 名与契约 §4.1 **逐字一致**
- [x] 人工验证记录 `harness/verification/B3F1/manual-verification.md` **已回填**（**五段式** · 仓库既有约定）
      （含：零出站证据 · 断网全绿证据 · M0 三 feature 补检结论 · **分支保护设置步骤与状态取证**）
- [x] **v1.0 的发行元数据零依赖包名**：`Requires-Dist` **整个为空** + wheel `METADATA` **无任何 `Requires-Dist`** + `pyproject.toml` **不含** `[project.optional-dependencies]`（裁定 26 · 宪法 v1.7.0）
- [x] **v2.0 清单的预验证**：G21 / G23 对 `contracts/extras-v2.toml` 取证 ⇒ **被检查 12 个包**（**非空门禁** ✓）
- [x] **G3 占位填充的追认**（plan.md「唯一一处例外」· `tasks.md` **T049**）已获发起者确认 —— ✅ **2026-11-08 已追认**（追认文字见 §5.1）
- [x] **plan 登记项 R-4 偏离的追认**（宪法**质量门禁 3 / 4 / 5 三项**在本 feature 均不适用 ——
      门禁 3 的 C4 / C8 回归 · 门禁 4 的 fake 模型轮 · 门禁 5 + 原则 V 的真实模型轮 · `tasks.md` **T057**）已获发起者确认
      （**追认文字 + 发起者确认 + 日期** · 记录在人工验证记录里 · **未追认前 MUST NOT 合入**）—— ✅ **2026-11-08 已追认**（追认文字见 §3.6）
- [x] **G23 按并集口径实现**（被检查集 =（闭包包集）∪（`--root` 下扫到的 dist-info）· 裁定 25）——
      **只判闭包 ⇒ 反向用例空转；只判 `--root` ⇒ 空门禁 ⇒ 违宪** —— 实测**被检查的包数 = 12**（非空门禁）

---

## 5. 遗留问题

| # | 遗留 | 归属 | 状态 |
|---|---|---|---|
| **1** | **断网等价性的「命名空间」层** —— **✅ 已由 CI 证实**（2026-11-08 · 第 3 轮）：3 个 Linux 作业在 `unshare --net --map-root-user` 下**全绿**（G28 步骤通过 ⇒ 通过率 == 100%）⇒ **本条关闭** | CI（Linux 作业） | ✅ **已关闭** |
| **2** | **T049 · G3 占位填充的发起者追认** —— 既有门禁 **G3** 的**判据句逐字未动**，但 `CONSTITUTION_DEPENDENCY_WHITELIST`（4 个占位 → **12 个确切包名**）与 extras 枚举语义（过近似 → 精确变体）被填充 ⇒ **净效果 = 变严** ⇒ 依裁定 8 属**唯一一处例外** ⇒ **MUST 由发起者追认**（**实现者不代签**） | **发起者** | ✅ **已追认（2026-11-08 · T049 · 追认文字见下）** |
| **3** | **T057 · 三条宪法质量门禁缺口的发起者追认**（§3.6 的 ①②③） | **发起者** | ✅ **已追认（2026-11-08 · T049 · 追认文字见下）** |
| **4** | **FR-020 · 分支保护未启用** —— 本机无 `gh` CLI、无 GitHub 令牌 ⇒ 只能交付**可照抄的设置步骤**（§3.4）；**未启用前该项在人工验证记录中标「未完成」**，MUST NOT 记为通过 | **发起者** | ✅ **已启用（2026-11-08 · 发起者确认 · 见 §3.4 ③）** |
| **5** | **「禁止色值清单」为空集 ⇒ 品牌色子域「待取证」** —— 官方品牌色值**尚未逐字取证**并落入本仓库 ⇒ MUST NOT 凭记忆写入 hex（原则 VIII）⇒ 该子域**当前天然成立**，但 **MUST NOT** 记作「已自动判定」（spec SC-016 的限定语） | 后续取证（可并入 B25F1） | **待取证** |
| **6** | **「自有品牌资产白名单」为空集** —— 实测仓库内**无任何**受版本控制的图像 / 样式文件 ⇒ 「白名单外图像文件数 == 0」**天然成立**；一旦引入**自有** logo / 架构图，MUST 登记进该白名单（FR-021 ②） | 引入自有资产时 | **待登记** |
| **7** | **G3 的 12 名白名单是**版本敏感**的快照** —— extras 的版本约束是**开区间**（`pydantic>=2.0`）⇒ 上游**新增一个传递依赖**即会让闭包多出一个包名 ⇒ 白名单失配 ⇒ CI 变红。⇒ 复核的**双触发点**：① **extras 的版本约束变更**（`[project.optional-dependencies]` 任一条变更）· ② **CI 因闭包失配而红** ⇒ **二者任一**即 MUST **重跑闭包实测**并追认更新白名单（**MUST NOT** 以「放宽白名单让它变绿」的方式绕过 · FR-018） | 依赖变更时 | **纪律已登记** |
| **8** | **`[otel]` 的 OTLP exporter 归 B21F1** —— `opentelemetry-exporter-otlp` 的闭包含 `certifi`（**MPL-2.0**）⇒ 不可进 `[otel]`（裁定 21） | **B21F1** | **已登记** |
| **9** | **判据重叠（已登记 · 不合并）** —— ① 既有 `tests/facade/_gatesupport.py` 与本 feature 的 **G24 / G25 / G29 / G30** 判据大面积重叠（方向是**更严**）；② `harness/demo/acceptance.py` 的 `EgressProbe` 是仓库内**第三份**出站归因实现，用的是**已被裁定 19 否决**的旧口径 ⇒ 本 feature 的零出站证据**一律**取自 `_gatekit`；③ 既有 G3 与新 G23 的许可证口径不同（`MIT-CMU` 在 G3 通过 / 在 G23 被拒 ⇒ **G23 更严** ⇒ 总体为严） | **B25F1** 统一 | **已登记** |
| **11** | **`[png]` 的真 PNG 渲染后端方向待 v2.0 专项调研** —— 候选与代价见 `research.md` **D-16**（`playwright` 需另装浏览器二进制 · 约 300 MB / 自研最小渲染器 · 永久零依赖 / 继续只出占位 PNG）⇒ **v1.0 只出占位 PNG**（零依赖）⇒ **不阻塞**本 feature | **v2.0 专项调研**（发起者 + 实现者互动 · research DR-8） | **待调研** |
| **10** | **Windows / macOS 作业** —— **✅ 已实测全绿**（2026-11-08 · 第 3 轮）：**7/7 作业 success** ⇒ 命令串的**跨平台写法**与**换行口径**均已验证 | CI | ✅ **已关闭** |

### 5.1 T049 的追认文字（G3 占位填充 · 裁定 8 的唯一一处例外 · 2026-11-08）

```text
追认文字：既有门禁 G3 的两处占位被填充 —— ① CONSTITUTION_DEPENDENCY_WHITELIST
          由 4 个占位包名改为四个 extra 真实闭包的**恰好 12 个确切包名**
          （有限 · 逐个列名 · 无通配符 · 无前缀匹配）；② extras 变体的枚举语义
          由「无差别剥离 / 保留 extras marker」改为「**只枚举 freegraph 自身的
          extras 变体**（传递依赖按其基础依赖展开）」。
          G3 的**判据句逐字未动**、**许可证取值方式零改动**、**净效果 = 变严**
          （更精确的白名单 + 更正确的枚举）⇒ 无一处放宽（FR-018）。
          **准予追认**（plan.md「唯一一处例外」· Complexity Tracking）。
          附：白名单为**开区间版本约束下的实测快照**，复核的双触发点与
          「MUST NOT 以放宽白名单让它变绿」的红线已登记于 §5 遗留 #7。
发起者确认：杨家成（发起者）——「验证通过，同意本 feature 的做法」
日期：2026-11-08
```

> **⚠️ 签名的时序**：本块由**发起者**在人工验收通过后填写 ⇒ 实现者**只负责
> 转录与勾选**，MUST NOT 预签（MUST NOT 由实现者代签 · 宪法 v1.6.0）。

---

## 6. 移交后续 feature

| 承接方 | 移交内容 |
|---|---|
| **B5F2**（M1） | **C4**（稀疏状态读）的**独立回归测试** —— 落点 `tests/contracts/test_contract_regressions.py::test_c4_sparse_state_read`（当前 `status=not-landed`）⇒ 落地后把标记改成 `status=landed` |
| **B8F1**（M2） | **C8**（条件边 fresh 状态读）的**独立回归测试** —— 落点 `tests/contracts/test_contract_regressions.py::test_c8_conditional_edge_fresh_state_read`（当前 `status=not-landed`） |
| **B7F2**（M2） | **fake 模型注入** ⇒ 门禁 **4** 的「fake 模型跑通验收基线的一轮」随内核运行时一并落地（G29 ② 的退出码细分届时将判为「真断言失败」而非「环境未就绪」） |
| **B21F1** | **OTLP exporter 插件**（`opentelemetry-exporter-otlp`）—— 归 B21F1 解决；**不可**进 `[otel]` extra（`certifi` / MPL-2.0） |
| **v2.0 的 extras 落地** | 把 `contracts/extras-v2.toml` 的内容搬进 `pyproject.toml` 的 `[project.optional-dependencies]` ⇒ **门禁实现零改动**（G21 / G23 的 `--project` 换回 `pyproject.toml` 即可） |
| **B24F1** | **发行流水线的最终拦截** —— 本 feature 只提供**先行检查**（`ci.yml` 的「发行产物纯度先行检查」）；`publish.yml` **零改动** |
| **B25F1** | **双跑验收** + `acceptance.py` 的退出码断言 + **`_gatekit` 归因口径的统一**（替掉 `acceptance.py` 的 `EgressProbe` 旧口径）+ 自有品牌资产白名单的登记 |
| **发起者** | ~~T049 / T057 的追认~~ **（2026-11-08 已完成）** · ~~分支保护的启用~~ **（2026-11-08 已完成）** |
