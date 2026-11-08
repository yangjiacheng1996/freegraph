# Quickstart: B3F1 · 项目脚手架 + extras 划分 + CI 门禁

**Date**: 2026-11-07 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**用途**: **可照抄的验证手册** —— 证明本 feature 端到端成立。
**读法**: 每节 = 「做什么 → 期望看到什么」。**命令可直接复制执行**。

---

## 0. 前置条件

| 项 | 要求 | 本机实测（2026-11-07） |
|---|---|---|
| Python | **3.11+** | `python3` = 3.12.3 ✅ · `python3.11` = 3.11.16 ✅ |
| uv | 任意近期版（**须支持 `--group`** · PEP 735） | `uv 0.12.7` ✅ |
| pytest | 任意近期版（由 **dev 组**提供） | `pytest 7.4.4` ✅ |
| 网络 | 仅**安装依赖**时需要 | — |
| Git | 任意近期版 | `git 2.43.0` ✅ |

> **门禁本身零第三方依赖**；`packaging`（SPDX 表达式解析）仅作**开发期**依赖。

### 0.1 环境准备（**一次性 · 四条命令**）

> **⚠️ 跨平台的解释器写法（2026-11-08 分析轮订正 · C1）**：下面的命令串**只出现 venv 目录 `.venv`**，
> **三个平台逐字相同**（Windows 上 `uv venv` 生成的是 `.venv\Scripts\` 布局 ⇒ 硬编码 POSIX 解释器路径
> 会让 `windows-2025` 的作业**每一条命令**路径失效 ⇒ 必红）。
> **安装**用 `uv pip install --python .venv …`（**实测 uv 0.12.7 接受 venv 目录路径**）·
> **调用**用 `uv run --no-project --python .venv python …`（`--no-project` ⇒ **不同步环境**
> ⇒ MUST NOT 让它把已装的四个 extras 依赖卸掉）。

```bash
# ① 建 venv —— ⚠️ 必做：uv pip install 在**无活动虚拟环境**时报
#    "error: No virtual environment found" 并以退出码 2 失败（实测）
uv venv --python 3.11

# ② 开发期依赖组（pytest + packaging）—— PEP 735 · 不进发行包 / 不进 Requires-Dist
uv pip install --python .venv --group dev

# ③ 发行形态（可编辑安装）
uv pip install --python .venv -e .

# ④ 四个 extras 的依赖 —— **G21 / G23 / G3 可判定的前置条件**（只装 Python 包，不装浏览器二进制）
uv pip install --python .venv -e ".[pydantic,checkpoint,otel,png]"
```

> **⚠️ 第 ④ 条 MUST NOT 省略、且适用范围是全部 7 个作业**（2026-11-07 分析轮订正）：不装 extras ⇒
> ① **G23** 取不到许可证据（要么必红、要么退化为空门禁 ⇒ **违宪**）② **G21** 的闭包走不到末端
> （且非 Linux 作业上 G21 会因「未安装 ⇒ 判失败」而**必红**）③ **G3** 的 12 名白名单永不触达
> ⇒ **四个 extras 的依赖是纯 Python 包、跨平台可得**（`playwright` 只装 Python 包、不装浏览器二进制）。
> **实测**：四个 extras 的完整闭包**恰好 12 个包**（`annotated-types` · `greenlet` · `opentelemetry-api` ·
> `opentelemetry-sdk` · `opentelemetry-semantic-conventions` · `ormsgpack` · `playwright` · `pydantic` ·
> `pydantic-core` · `pyee` · `typing-extensions` · `typing-inspection`）⇒ 与 G3 的白名单**逐一命中**。
> **G22 的隔离 venv 仍只装基础包**（它断言的正是「基础安装闭包 == 空集」）。
> **⚠️ 隔离副本另需 `README.md` + `LICENSE`**（`pyproject.toml` 的硬引用 · 缺一即构建失败）。

---

## 1. 脚手架：extras 划分与版本矩阵

### 1.1 基础安装的依赖闭包 MUST 为空集（SC-002）

```bash
uv venv /tmp/fg-base && \
uv pip install --python /tmp/fg-base . && \
uv run --no-project --python /tmp/fg-base python -c "
import importlib.metadata as m
r = m.requires('freegraph')
base = [x for x in (r or []) if 'extra ==' not in x]
print('Requires-Dist:', r)
print('无 extra 标记的条目:', len(base), base)
"
```

**期望**：**无 `extra ==` 标记的条目数 == 0** ⇒ 基础安装零第三方依赖 ⇒ 基础闭包为空集。

> **⚠️ 路径说明（2026-11-08 分析轮订正 · C1）**：第三行**只出现 venv 目录 `/tmp/fg-base`**（**不出现**平台专属的
> 解释器子路径）⇒ 三个平台**同一写法**；Windows 上把 `/tmp/fg-base` 换成 `%TEMP%\fg-base` 即可。

> **⚠️ 口径订正（2026-11-07 分析轮 · 实测）**：**T002 声明四个 extras 之后，`Requires-Dist` 不再是 `None`** ——
> 实测：它变成**一个 list**（**5** 个条目，**每个都带 `extra == '...'` 标记**）：
> `"pydantic>=2.0; extra == 'pydantic'"` · `"ormsgpack>=1.0; extra == 'checkpoint'"` ·
> `"opentelemetry-api>=1.20; extra == 'otel'"` · `"opentelemetry-sdk>=1.20; extra == 'otel'"` ·
> `"playwright>=1.40; extra == 'png'"`。
> ⇒ 故判据 MUST 是「**不带 `extra ==` 标记的条目数 == 0**」（**T045 / 闸口 A1 的口径**），
> **MUST NOT** 断言「`Requires-Dist` 为 `None`」（那只在**未声明 extras** 时成立 ⇒ 断言必红）。
> **`None` 与 `[]` 的区别**：一个依赖都没有时 `importlib.metadata.requires()` 返回 `None` 而非 `[]`。
> **⚠️ 计数订正（2026-11-08 分析轮订正 · M8①）**：原写「**4** 个条目」⇒ **漏了 `opentelemetry-sdk`**
> ⇒ 与 T045 与闸口 A1 的「**5** 个条目」逐字一致地订正为 **5**；同段的 `ormsgpack>=1.10`
> ⇒ 与 T002 声明的 `ormsgpack>=1.0` 统一为 **`>=1.0`**。
>
> **注**：**开发期依赖组 `[dependency-groups] dev` 不进 `Requires-Dist`**（PEP 735 · 实测安装后 `extra ==` 标记条目数不变）
> ⇒ 基础安装的零依赖承诺不受 pytest / packaging 影响。

### 1.2 `requires-python` MUST 为 `>=3.11` 且**不设上限**（FR-001 / FR-003）

```bash
grep -E 'requires-python' pyproject.toml
```

**期望**：`requires-python = ">=3.11"`（**无** `<` 上界）。

### 1.3 四个 extra MUST 存在且各自独立可选（FR-004）

```bash
python3 -c "
import tomllib, pathlib
d = tomllib.loads(pathlib.Path('pyproject.toml').read_text())
for k, v in d['project']['optional-dependencies'].items():
    print(f'{k:12s} -> {v}')
"
```

**期望**：恰好 `pydantic` / `checkpoint` / `otel` / `png` 四项，各自列出依赖。
**`[otel]` 的内容 MUST 恰为 `opentelemetry-api` + `opentelemetry-sdk`**，**MUST NOT** 含任何
OTLP exporter（`opentelemetry-exporter-otlp`）—— 其闭包含 `certifi`（**MPL-2.0**）⇒ 必被 G23 拒
（spec 裁定 21 · 宪法「依赖白名单」原文 · exporter 归 B21F1）。

### 1.4 `py.typed` MUST 存在且为空（FR-002 · PEP 561）

```bash
ls -l src/freegraph/py.typed && wc -c < src/freegraph/py.typed
```

**期望**：文件存在 · 大小 **0 字节**。

---

## 2. 依赖门禁

### 2.1 G21 · 依赖闭包黑名单（**声明级** · 读 `pyproject.toml` 的声明）

> **⚠️ 前提（2026-11-07 分析轮补入）**：G21 判的是**声明级**（读 `pyproject.toml`，无需安装 freegraph 本身），
> 但**递归展开传递依赖**需要读取**传递依赖自身的元数据** ⇒ **传递依赖 MUST 已安装**
> ⇒ CI / 本地复现 MUST 先装齐四个 extras 的依赖（**§0.1 ④**）⇒ 否则闭包只到第一层，
> 且「未安装 ⇒ 无法取证」按契约 **判失败**（MUST NOT 静默跳过）。

```bash
uv run --no-project --python .venv python harness/scripts/gates/gate_G21_dependencies.py
```

**期望**：退出码 **0** · 输出无违规。

### 2.2 G22 · 隔离环境断言（**真隔离 venv**）

```bash
uv run --no-project --python .venv python harness/scripts/gates/gate_G22_isolated_env.py
```

**期望**：退出码 **0**；输出显示隔离环境内**第三方包数 == 0**，`sys.modules` 无
`langsmith` / `langchain_core` / `langgraph`。

### 2.3 G23 · 许可证白名单（4 级证据链 · 5 个精确 SPDX id）

```bash
uv run --no-project --python .venv python harness/scripts/gates/gate_G23_licenses.py
```

**期望**：退出码 **0**；输出逐包列出「包名 → 证据来源 → SPDX 表达式 → 判定」。

> **⚠️ 取证作用域 = 并集口径（2026-11-08 分析轮订正 · spec 裁定 25）**：G23 的**被检查包集合** =
> **（依赖闭包中的包）∪（`--root` 下扫到的 `*.dist-info` / `*.egg-info` 所对应的包）**；
> **许可证据先**取 `--root` 下的元数据、**后**回落**已安装**元数据。
> ⇒ **只判闭包** ⇒ 反向用例（T016 注入的假元数据）**空转**；
> ⇒ **只判 `--root`** ⇒ 正常路径（`--root` 默认 = 仓库根，其下无 `dist-info`）**空门禁 ⇒ 违宪**。
> ⇒ **反向用例的复现方式**：`gate_G23_licenses.py --root <isolated_copy>`，
> 假元数据落成 `<isolated_copy>/<name>-<version>.dist-info/METADATA`
> （**必填四头**：`Metadata-Version` / `Name` / `Version` / `License-Expression`，
> 且 `Name` / `Version` MUST 与目录名一致）。

### 2.4 ★ 负向验证（**本 feature 的验收判据本体** · SC-001 / **验收判据 A1**（引文 §6 · 门禁生效）· 对应执行闸口 **A2**）

```bash
# 在临时副本中注入 langchain-core，断言门禁失败，且工作树逐字不变
uv run --no-project --python .venv python harness/scripts/gates/gate_G21_dependencies.py --self-test-negative
```

**期望**：
- **自检通过 ⇒ 退出码 0**（自检内部断言的是「门禁**必须**失败」：注入 `langchain-core` 后门禁应失败并输出
  **包名 `langchain-core`** + **规则编号** + 修复指引）——**自检失败 ⇒ 退出码非 0**
  （口径与 FR-016「0 = 通过 · 非 0 = 失败」一致 ⇒ 该命令可安全地作为 CI 的一步）；
- **原工作树 `git status` 仍干净**（SC-010）。

> **⚠️ 口径提醒（2026-11-07 分析轮补入）**：`--self-test-negative` 的退出码语义是
> 「**自检是否通过**」，不是「**门禁是否失败**」——门禁在自检里**本来就该失败** ⇒
> **自检通过 = 退出码 0**。若把「退出码 ≠ 0」当作该命令的期望，会在 CI 里把「成功」判成「失败」。

**手工复现版**（等价、更直观）：

```bash
tmp=$(mktemp -d); cp pyproject.toml "$tmp/"; mkdir -p "$tmp/src"
python3 - "$tmp" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]) / "pyproject.toml"
t = p.read_text().replace('dependencies = []',
    'dependencies = ["langchain-core>=0.3"]')
p.write_text(t)
PY
uv run --no-project --python .venv python harness/scripts/gates/gate_G21_dependencies.py --project "$tmp/pyproject.toml"
echo "退出码 = $?"   # 期望：非 0
rm -rf "$tmp"
```

---

## 3. 静态门禁（AST 类）

| 门禁 | 命令 | 期望 |
|---|---|---|
| **G24** 配置层 | `uv run --no-project --python .venv python harness/scripts/gates/gate_G24_config_layer.py` | 退出码 0（`src/freegraph/**` 内零环境变量读取） |
| **G25** 导入图 | `uv run --no-project --python .venv python harness/scripts/gates/gate_G25_import_graph.py` | 退出码 0（层间方向单向；门面例外被承认） |
| **G26** 网络静态 | `uv run --no-project --python .venv python harness/scripts/gates/gate_G26_network_static.py` | 退出码 0（`src/freegraph/**` 无网络客户端调用） |
| **G30** 署名头 + 品牌资产 | `uv run --no-project --python .venv python harness/scripts/gates/gate_G30_attribution.py` | 退出码 0（全仓 `.py` 覆盖率 == 100% **且** 无第三方品牌资产：图像资产 / 品牌色值 / "Approved copy" 文案三类） |

### 3.1 G25 的判据来自**唯一权威**（层注册表）

```bash
grep -m1 'authority: yes' specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md
```

**期望**：命中 `layer-registry.md`（**有且仅有**一份）。

### 3.2 G30 的存量补齐已生效

```bash
# 署名头在**文件顶部**：首行是 shebang ⇒ 取第二行；否则取首行
# （宪法原则 X · FR-013 ② · 与 architecture-gates.md G30 §1.4 逐字一致）
for f in $(git ls-files '*.py'); do
  { head -1 "$f"; head -2 "$f" | tail -1; } | grep -q 'Copyright (c) 2026 杨家成' \
    || echo "缺头: $f"
done
```

**期望**：**只输出** `harness/demo/target.py`（只读基准 · 具名例外）。

> **⚠️ 先 `git add` 再跑（2026-11-08 分析轮补入）**：G30 的扫描域 = `git ls-files '*.py'` ⇒ **只含受版本控制的文件** ⇒
> **尚未 `git add` 的新文件不在检查域内**（本 feature 新写的 10 个门禁脚本 + `tests/gates/**` 同理）⇒
> 本地跑 G30 前 MUST 先 `git add`（否则新文件漏检）；CI 上天然满足（已提交）。
> （这是 FR-013 ④「**受版本控制的** `.py`」的设计意图，非缺陷。）

> **⚠️ 为何不能只用 `head -1`（2026-11-07 分析轮补入）**：实测全仓 37 个 `.py` 中有 **9 个首行是 shebang**
> （`#!/usr/bin/env python3`）⇒ 它们的署名头按宪法原则 X 放在 **shebang 之后（第二行）**
> ⇒ 用 `head -1` 检查会把这 9 个**已合规**的文件**误报为「缺头」**（同时也会掩盖真正缺头的那个）。

---

## 4. 运行时门禁

### 4.1 G27 · 零出站动态断言（**只观测不阻断**）

```bash
uv run --no-project --python .venv python harness/scripts/gates/gate_G27_zero_egress.py
```

**期望**：退出码 **0**；输出「框架出站 = **0**」+「用户出站 = N（记录在案，不判失败）」
+「**当前观测面：测试套件执行期（尚不含内核运行时 —— 运行期待 M2）**」。

> **⚠️ 观测面 MUST 显式打印（2026-11-08 分析轮订正 · 与 spec SC-006 ① 一致）**：MUST NOT 让「空断言 /
> 极窄观测面」被误读为「零出站已被证明」⇒ 该入口的观测面 = **在 egress 监测下跑整个测试套件**。
> **代价登记**：该入口在 Linux 作业上会**再跑一遍全量测试套件**（CI 步骤 6 已跑过）
> ⇒ plan 的 Performance Goals 已同步为「G22 / G27 / G28 三条可能超时的门禁」。

### 4.2 G28 · 断网等价性（**Linux 专属**）

```bash
unshare --net --map-root-user uv run --no-project --python .venv python harness/scripts/gates/gate_G28_offline_equiv.py
```

**期望**：退出码 **0**；输出「通过率 = 100%」+「排除项 N 条（逐条有理由）」。

> **排除清单是可见的**：`tests/gates/data/offline_exclusions.txt`（**单文件** · 每行 = `用例标识 :: 排除理由`）。
> **⚠️ 排除清单 MUST 显式施加（2026-11-08 分析轮订正 · H7）**：上面的命令调用的是 **G28 门禁脚本**
> ⇒ 它**读该清单并逐条转成 `--deselect` 参数**传给 pytest ⇒ 排除范围**唯一**由那**一个文件**持有；
> **MUST NOT** 照抄「不带排除清单的裸 `pytest tests/ -ra`」⇒ 那会在被排除的用例上**假红**
> （断网下连接必然失败 ⇒ 属**假红**，不是 freegraph 的缺陷）⇒ **SC-004 必假红**。
> 等价的**手工展开**形式（把清单逐条展开成 `--deselect`）见
> [`contracts/ci-matrix.md` §3.2](./contracts/ci-matrix.md)。

### 4.3 G29 · 契约门禁载体（只读基准 diff + C4/C8 挂载点）

```bash
uv run --no-project --python .venv python harness/scripts/gates/gate_G29_contract_carrier.py
```

**期望**：退出码 **0**；输出「`target.py` 与基准**逐字相同**」+「C4 / C8 挂载点：**未落地**（C4 → M1 · C8 → M2）」。

> **C4 / C8 标「未落地」是正确状态** —— MUST NOT 伪装成「已通过」（FR-011 ②）。
>
> **⚠️ 基准载体**：只读基准 = **Git 索引中的 `HEAD:harness/demo/target.py`**（`git show HEAD:harness/demo/target.py`）——
> 仓库内**不存在**第二份基准副本 ⇒ MUST NOT 依赖「仓库内另一份文件」。
>
> **⚠️ 验收脚本集退出码的口径（2026-11-07 分析轮订正）**：G29 ② 断言退出码 ∈ **{0, 1, 2}**，并按**失败来源**细分 ——
> CI 中 freegraph **已安装** ⇒ 三个脚本 import 成功 ⇒ 退出码 **2** 的分支（`except ImportError`）**不触发**
> ⇒ 脚本走到用例体并因 `NotImplementedError` 被记为**断言失败** ⇒ **退出码为 1**（**实测**：freegraph 可导入时三者退出码**全为 1**）。
> 故：**1 且失败全部源于 `NotImplementedError`** ⇒ 判为**环境未就绪**（**通过**）；**1 且有非 `NotImplementedError` 的失败** ⇒ **CI 失败**。

---

## 5. 全量测试套件

```bash
uv run --no-project --python .venv python -m pytest tests/ -ra
```

**期望**：**全绿**（前提：§0.1 的 **②** 已装 dev 组 —— 否则 `pytest` 命令不存在）。

> **源码优先 vs 发行形态**：默认把 `<repo>/src` 插到 `sys.path` **最前**（测源码树）；
> 设 `FREEGRAPH_TEST_INSTALLED=1` 则**跳过**注入（测**已安装**的发行形态）—— CI 用后者。

---

## 6. CI 矩阵（本地模拟）

```bash
# 与 CI 同序：建 venv → 装 dev 组 → 装发行形态 → 装 extras（**四步** · 与 ci-matrix §2 步骤 3.5 / 4 / 5 / 5.5 一致）
uv venv --python 3.11                       # ⚠️ 必做：无活动虚拟环境时 uv pip install 直接失败
uv pip install --python .venv --group dev
uv pip install --python .venv -e .
uv pip install --python .venv -e ".[pydantic,checkpoint,otel,png]"

# 最低档 = 3.11 且跑全量测试（typing 构件上限的主判定）
# ⚠️ MUST 用 venv 里的解释器（`uv run --no-project --python .venv python …`）——
#    直接写 `python3.11 -m pytest` 依赖**全局** 3.11 已装 pytest（干净机器上不存在 ⇒ 命令失败）
FREEGRAPH_TEST_INSTALLED=1 uv run --no-project --python .venv python -m pytest tests/ -ra

# 最高档 = 3.14 —— ⚠️ MUST 另建一个 3.14 的 venv（.venv 是 3.11 档）
uv venv --python 3.14 .venv314
uv pip install --python .venv314 --group dev
uv pip install --python .venv314 -e .
uv pip install --python .venv314 -e ".[pydantic,checkpoint,otel,png]"
FREEGRAPH_TEST_INSTALLED=1 uv run --no-project --python .venv314 python -m pytest tests/ -ra
```

**期望**：两档**全绿**。若源码里用了 3.12+ 的 typing 构件 ⇒ **3.11 档天然失败**
（`ImportError` / `AttributeError` / `SyntaxError`）⇒ 这正是「主判定」的机制。

> **⚠️ 三点与 CI 对齐（2026-11-07 分析轮补入）**：① **必须先 `uv venv`** —— `uv pip install` 在**无活动虚拟环境**时报
> `error: No virtual environment found` 并以**退出码 2** 失败（**实测**）；② 所有 uv 命令用**显式 `--python`**（不依赖隐式环境变量）；
> ③ **四个 extras 的依赖在全部 7 个作业上都装**（**不再仅限 Linux 全量作业**）—— 否则非 Linux 作业的 G21 因
> 「未安装 ⇒ 判失败」而**必红**（ci-matrix §2 步骤 5.5）。

### 6.1 矩阵形状核对（SC-012）

> **⚠️ 核对脚本已按契约 §2.0 的**矩阵配方**订正（2026-11-08 实现轮）**：
> 契约 §2.0 **明确**要求用 `strategy.matrix.include` 的**单作业 + 7 档矩阵**
> （否则 7 个作业会实现分叉）⇒ 原脚本用「顶层 job 键计数」**数不出 7**
> （矩阵作业只有 1 个 job 键）⇒ 改为**数矩阵档位**，并**逐字**核对
> **展开后的 7 个 job 名**与契约 §4.1 的必过检查名。

```bash
python3 - <<'PY'
import re, pathlib
t = pathlib.Path(".github/workflows/ci.yml").read_text()
entries = re.findall(
    r"-\s*\{\s*runner:\s*([^,]+),\s*python:\s*[\"']?([^\"',]+)", t
)
print("矩阵档位数 =", len(entries))
for runner, python in entries:
    print(f"  gates ({runner.strip()}, {python.strip()})")
template = re.search(r"^\s{4}name:\s*(.+)$", t, re.M).group(1).strip()
print("job 名模板 =", template)
expanded = {
    template.replace("${{ matrix.runner }}", r.strip())
    .replace("${{ matrix.python }}", p.strip())
    for r, p in entries
}
expected = {
    "gates (ubuntu-24.04, 3.11)", "gates (ubuntu-24.04, 3.14)",
    "gates (macos-15, 3.11)", "gates (macos-15, 3.14)",
    "gates (windows-2025, 3.11)", "gates (windows-2025, 3.14)",
    "gates (ubuntu-24.04-arm, 3.11)",
}
print("展开后的 job 名与契约 §4.1 逐字一致：", expanded == expected)
print("runner 标签含 latest：", any("latest" in r for r, _ in entries))
PY
```

**期望**：矩阵档位数 == **7**；展开后的 **7 个 job 名逐字等于**
`gates (<runner>, <Python>)` 形式（contracts/ci-matrix.md §4.1）—— GitHub 的
required check 按 job 名**精确匹配** ⇒ 名字不符则分支保护**静默失效**
（FR-020③ 的「已启用」名存实亡）；runner 标签**无** `latest` 等浮动标签。

> **⚠️ 平台专属解释器路径的核对**：命令串里 MUST NOT 出现平台专属的解释器
> 子路径（POSIX 的 `bin/` 布局 / Windows 的 `Scripts\` 布局）⇒ 可用
> `grep -n "venv/bin\|venv\\\\Scripts" .github/workflows/ci.yml` 自查
> （**期望无命中**；注释里也不写这两个形态，免得自查误报）。

---

## 7. 分支保护（**由发起者执行** · FR-020）

**本机无 `gh` CLI、无 GitHub 令牌**（实测）⇒ **无法代为设置**。

**设置步骤**见 [`harness/verification/B3F1/manual-verification.md`](../../../../harness/verification/B3F1/manual-verification.md)
（**可照抄**：勾选哪些 job 为必过检查 · 保护哪些分支 · 是否启用「必须先通过检查才能合并」）。

**快速自查**（设置后）：

```bash
# 浏览器打开：
# https://github.com/yangjiacheng1996/freegraph/settings/branches
# 确认 main 的「Require status checks to pass before merging」已勾，
# 且 7 个 gates job 全部列入。
```

---

## 8. 兼容矩阵与 API 快照的**分层**判定（裁定 13）

```bash
# 已入库的 README 矩阵 → 严格比对并阻断（由既有 G8 / G19 承担）
uv run --no-project --python .venv python -m pytest tests/contracts/test_architecture.py -k compat_matrix -ra
uv run --no-project --python .venv python -m pytest tests/facade/test_facade_gates.py -ra

# 终版 COMPAT.md 未建立 → 非阻断地显式报告「未落地」
uv run --no-project --python .venv python harness/scripts/gates/gate_G29_contract_carrier.py --check-compat
```

**期望**：前两条**全绿**；后一条输出「`COMPAT.md`：**未落地**（非阻断）」，
且**退出码 0**（MUST NOT 静默跳过）。

> **⚠️ `COMPAT.md` 建立后的口径（2026-11-08 分析轮订正 · 与 spec FR-012 ② / SC-011 一致）**：
> `COMPAT.md` **存在** ⇒ 该步骤**自动转为严格比对** ⇒ **有不一致**时才以非 0 退出（并指名行 / 符号）；
> **一致 ⇒ 退出码 0**。**MUST NOT** 仅因「文件存在」而非 0（否则后续 feature 建出 `COMPAT.md` 后
> 该步骤**永久红** ⇒ 违宪 v1.6.0 红线「MUST NOT 写永久红的 CI」）。

---

## 9. 常见失败与处置

| 症状 | 原因 | 处置 |
|---|---|---|
| G21 报「`langchain-core` 违规」 | 依赖里混入了黑名单包 | 移除该依赖；若是**传递**引入，换掉引入方 |
| G23 报「取不到许可证明」 | 该包四级证据链全空 | 换包；MUST NOT 放宽白名单（FR-018） |
| G23 报「`MPL-2.0` 不在白名单」 | 该包是传染性 / 限制性许可证 | 换包（例：`requests` → `certifi` 的链） |
| G23 报「`3-Clause BSD License` 无法解析」 | 散文式许可证名 | 换包（MUST NOT 加映射表 —— 裁定 18） |
| G25 报「层 L1 反向 import L3」 | 跨层依赖 | 把实现下沉到低层；或**改层注册表**（走评审） |
| G26 报「`socket` 违规」 | 包内引入了网络客户端 | 移除；合法的只有**具名例外**（OTLP exporter · B21F1） |
| G27 报「框架出站 > 0」 | freegraph 真的联网了 | 阻断性缺陷（MUST NOT 合入） |
| G30 报「缺署名头」 | 新文件没带头 | 加首行署名头（shebang 之后） |
| G30 报「第三方品牌资产」 | 仓库内出现第三方 logo / 品牌色 / 官方 "Approved copy" 文案 | 移除该资产；**自有**资产 MUST 登记进「自有品牌资产白名单」（当前为空集）· FR-021 ② |
| G23 输出「被检查 0 个包」 | 只判了 `--root`（默认 = 仓库根 ⇒ 无 dist-info）⇒ **空门禁** | 按**并集口径**实现（闭包 ∪ `--root` 下 dist-info）· 裁定 25 |
| G28 报「通过率 < 100%」 | 断网下某用例失效 | **不得**随手跳过 ⇒ 按判据决定是否进排除清单（**逐条写理由**） |
| 3.11 档报 `ImportError` | 用了 3.12+ 的 typing 构件 | 换成 ≤3.11 的写法（主判定在起作用） |

---

## 10. 完工检查表

- [x] `pytest tests/ -ra` **全绿**
- [x] **环境已按 §0.1 准备**：dev 组已装 + 发行形态已装 + **四个 extras 的依赖已装齐**
- [x] 10 条新门禁**逐条**退出码 **0**
- [x] 负向验证：**门禁失败** + **工作树逐字不变**（`--self-test-negative` 自检**通过 ⇒ 退出码 0**）
- [x] 3.11 档与 3.14 档**各跑一次**全量测试，均全绿
- [x] `git ls-files '*.py'` 的**顶部**署名头覆盖率 == **100%**（**首行或 shebang 之后**；除 `target.py`）
- [x] 基础安装**无 `extra ==` 标记的 `Requires-Dist` 条目数 == 0**（**口径订正** · 声明 extras 后 `Requires-Dist` **非** `None`）
- [x] `ci.yml` **矩阵档位数 == 7**（单作业 + `strategy.matrix.include` 7 档 · 契约 ci-matrix §2.0 的实现配方）· runner 标签**无浮动** · 展开后的 **7 个 job 名**与契约 §4.1 **逐字一致**
- [x] 人工验证记录 `harness/verification/B3F1/manual-verification.md` **已回填**（**五段式** · 仓库既有约定）
      （含：零出站证据 · 断网全绿证据 · M0 三 feature 补检结论 · **分支保护设置步骤与状态取证**）
- [x] **G3 占位填充的追认**（plan.md「唯一一处例外」· `tasks.md` **T049**）已获发起者确认
- [x] **plan 登记项 R-4 偏离的追认**（宪法**质量门禁 3 / 4 / 5 三项**在本 feature 均不适用 ——
      门禁 3 的 C4 / C8 回归 · 门禁 4 的 fake 模型轮 · 门禁 5 + 原则 V 的真实模型轮 · `tasks.md` **T057**）已获发起者确认
      （**追认文字 + 发起者确认 + 日期** · 记录在人工验证记录里 · **未追认前 MUST NOT 合入**）
- [x] **G23 按并集口径实现**（被检查集 =（闭包包集）∪（`--root` 下扫到的 dist-info）· 裁定 25）——
      **只判闭包 ⇒ 反向用例空转；只判 `--root` ⇒ 空门禁 ⇒ 违宪**

> **📌 2026-11-08 分析轮补入的核对项（对应已排期任务）**：
> - [ ] **T032** · 发行产物**纯度先行检查**已进 `ci.yml`（`uv build` + `harness/scripts/check_dist_purity.py dist/` ⇒ 产物不含 `harness/` / `.specify/` / `.opencode/` / `specs/` / `tests/`）—— **MUST NOT** 改动 `publish.yml`
> - [ ] **T033** · README / CONTRIBUTING 已写「**合入前 CI 必须全绿**」的**文档兜底句**（分支保护未启用期间的人工保障）
> - [ ] **T050** · `THIRD_PARTY_NOTICES` **§2** 的「第三方运行时依赖」表说明文字已同步（基础安装闭包**仍为空集** · extras 的依赖为**可选**）
> - [ ] **T051** · README 的「可选依赖（extras）」章节已写（四个 extra 的用途 + `[png]` = **`playwright`**（**宪法 v1.5.0 已列明**）+ **浏览器二进制需用户显式 `playwright install chromium`** + **运行期零出站**）且**兼容矩阵章节逐字不动**
> - [ ] **T055** · **质量门禁 7 项**的落地复核已写入人工验证记录（逐条写明**对应断言**与**是否全自动**）
> - [ ] **T039** · 断网**排除清单已定稿**（`tests/gates/data/offline_exclusions.txt` · **单文件** · **逐条带理由** · 含新测试的**入册判据**）
> - [ ] **T046 / T047** · **M0 三 feature 的补检结论**已写入人工验证记录（**依赖声明** + **import 图**）
> - [ ] **T028 ②** · G30 的**品牌资产段**已按契约 G30 **判定第 6 项**的**两份具名清单**实现：
>       「禁止文案指纹清单」的 3 条来自 `harness/reports/Q7-开源边界地图与许可证合规.md` §3.3.3（来源 **D10** · as-of **2026-11-01**）；
>       「禁止色值清单」若仍为**空集** ⇒ MUST 在人工验证记录中标注「**待取证**」，**MUST NOT** 记作「已自动判定」（spec SC-016 限定语）
> - [ ] **T016 / T023** · G23 的**反向用例**已按**并集口径**验证：假元数据落 `<isolated_copy>/<name>-<version>.dist-info/METADATA`
>       （**四必填头**）⇒ G23 失败并指名；且**正常路径**下 G23 的被检查包数 == 闭包包数（**非 0** ⇒ 非空门禁）
