# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""门禁的**共享判定库**（B3F1）—— G21–G30 的重活全在这里。

**结构决策**（`specs/b3f1-scaffold-ci-gates/plan.md`「Structure Decision」）：
十条门禁**各一个薄壳**（`gate_GNN_*.py` —— 只做「参数解析 → 调用判定 → 打印报告
→ 退出码」），**判定逻辑集中在本模块** ⇒

1. 满足 FR-016「**逐条调用 + 退出码即判定**」；
2. 避免「**同一判据两处实现**」（裁定 8 第三条理由）—— 例如
   「负向验证的隔离副本构造」只有本模块的 `make_isolated_copy()` 一份实现
   （pytest 夹具与门禁脚本的 `--self-test-negative` **共用**它）；
3. 「**两个入口 · 同一实现**」（G27）—— 归因函数与 socket 包装只有本模块一份
   （独立入口与 pytest 夹具**共用**它）。

**本模块只依赖标准库**（`ast` / `importlib.metadata` / `subprocess` / `socket` /
`difflib` / `tomllib` …）；唯一的第三方依赖 `packaging`（SPDX 表达式解析）**仅在
需要时惰性导入**，且它是**开发期**依赖（不进发行包 —— 门禁代码本身也在 `harness/`
内，不进发行包）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import ast
import contextlib
import dataclasses
import difflib
import importlib.metadata
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path

__all__ = [
    "CROSS_LAYER",
    "configure_stdio",
    "ClosureResult",
    "Declaration",
    "EgressRecord",
    "ImportEdge",
    "LayerEntry",
    "LayerRegistry",
    "SpdxParseError",
    "StackFrame",
    "Variant",
    "Violation",
    "attribute_egress",
    "brand_asset_violations",
    "closure",
    "enumerate_variants",
    "evaluate_variant",
    "git_show",
    "license_evidence",
    "list_tracked_files",
    "load_layer_registry",
    "make_isolated_copy",
    "read_requires_dist",
    "record_egress",
    "report",
    "resolve_internal_module",
    "run_gate",
    "scan_env_reads",
    "scan_imports",
    "scan_network_calls",
    "signature_header_violations",
    "spdx_leaves",
]

# ── 常量 ──────────────────────────────────────────────────────────────────

#: 跨层单元的层标记（层注册表里的 ``—`` · U+2014）。
CROSS_LAYER = "—"

#: 许可证白名单 —— **恰好 5 个精确 SPDX 标识符**（dependency-gate.md §4.1）。
#:
#: **MUST NOT** 引入等价标识符对照表 / 许可证家族判定 / 豁免入口 /
#: 子串匹配（裁定 18 · FR-018）—— 白名单的扩充**只能走宪法修订**。
LICENSE_WHITELIST = frozenset(
    {
        "MIT",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "PSF-2.0",
    }
)

#: 传染性 / 限制性许可证（宪法原则 IX）—— **只用于点名诊断**。
#:
#: **判定落点在白名单比对**（逐叶子 · 精确 id）⇒ 本清单**不**参与放行决策，
#: 也**不靠前缀猜测**放行任何标识符（裁定 18）。
FORBIDDEN_LICENSE_FAMILIES = (
    "Elastic-2.0",
    "AGPL",
    "SSPL",
    "BUSL",
    "GPL-2",
    "GPL-3",
    "MPL-2.0",
    "LGPL-2.1",
    "LGPL-3.0",
)

#: 依赖黑名单（包层 · 宪法「依赖白名单 / 黑名单」· dependency-gate.md §5）。
#:
#: 与 `contracts/architecture-gates.md` G21 的黑名单表**逐行一致**（族 · 匹配规则 ·
#: 全部 provider 包 · 点名名单 · ``deepagents`` —— 五项**缺一不可**）。
BLACKLIST_EXACT = frozenset(
    {
        "langsmith",
        "langgraph-api",
        "langgraph-runtime-inmem",
        "phoenix",
        "deepagents",
    }
)
BLACKLIST_PREFIXES = ("langsmith-", "langchain", "langgraph", "langchain-")

#: 命名空间黑名单（宪法「配置层黑名单」）—— 前缀形态。
CONFIG_LAYER_PREFIXES = ("LANGSMITH_", "LANGCHAIN_")
CONFIG_LAYER_EXACT = ("LANGGRAPH_CLOUD_LICENSE_KEY",)
CONFIG_LAYER_PREFIXES_EXTRA = ("LANGGRAPH_AUTH",)

#: 网络客户端清单（architecture-gates.md G26）—— 逐个列名。
NETWORK_CLIENT_MODULES = (
    "socket",
    "ssl",
    "http",
    "http.client",
    "urllib.request",
    "urllib3",
    "requests",
    "httpx",
    "aiohttp",
    "websockets",
    "ftplib",
    "smtplib",
    "telnetlib",
    "xmlrpc",
    "asyncio.open_connection",
)

#: G26 的**具名例外**（模块路径逐个列出）—— **当前为空**（OTLP exporter 属 B21F1）。
#:
#: 例外 MUST 以**显式名单**表达，MUST NOT 放宽扫描域本身（FR-009 ① · FR-018 ①）。
G26_EXCEPTED_MODULES: tuple[str, ...] = ()

#: 环境变量读取 API（属性链形态 + 导入形态）—— 与既有
#: `tests/facade/_gatesupport.py` 的 `env_and_io_violations` **同口径**。
FORBIDDEN_ENV_ATTRS = frozenset({"environ", "environb", "getenv"})

#: 署名头（**逐字**）—— 宪法原则 X。
SIGNATURE_HEADER = (
    "# Copyright (c) 2026 杨家成 · MIT License · "
    "https://github.com/yangjiacheng1996/freegraph"
)

#: G30 的**两个具名例外**（宪法原则 X / 宪法原则 III）。
G30_EXCEPTED_FILES = frozenset({"src/freegraph/py.typed", "harness/demo/target.py"})

#: 第三方品牌资产 · **图像资产**的扩展名（FR-021 ①）。
BRAND_IMAGE_EXTENSIONS = frozenset(
    {
        ".svg",
        ".png",
        ".ico",
        ".jpg",
        ".jpeg",
        ".webp",
        ".gif",
        ".bmp",
        ".tiff",
    }
)

#: 第三方品牌资产 · **清单类**子域的扫描域（受版本控制的 ``.md`` + ``.css`` / ``.scss``）。
BRAND_TEXT_EXTENSIONS = frozenset({".md", ".css", ".scss"})

#: **禁止文案指纹清单**（官方《Brand Assets & Usage Guidelines》的 "Approved copy"）。
#:
#: 来源：`harness/reports/Q7-开源边界地图与许可证合规.md` §3.3.3（来源 **D10** ·
#: `https://www.langchain.com/brand-assets` · as-of **2026-11-01**）。
#: 取**可识别的指纹片段** ⇒ 既能捕获「照抄」，又 MUST NOT 把官方全文收入本仓库。
FORBIDDEN_COPY_FINGERPRINTS = (
    "enables every company to own their intelligence",
    "model-agnostic harnesses give teams choice and control",
    "brings testing, deployment, and monitoring together",
)

#: **禁止色值清单** —— **当前为空集**。
#:
#: 官方品牌色值**尚未逐字取证**并落入本仓库 ⇒ **MUST NOT** 凭记忆写入 hex
#: （宪法原则 VIII）⇒ 该子域当前**天然成立**，但 MUST NOT 记作「已自动判定」
#: ⇒ MUST 在人工验证记录中标注「**待取证**」（spec SC-016 的限定语）。
FORBIDDEN_BRAND_COLORS: tuple[str, ...] = ()

#: **自有品牌资产白名单** —— **当前为空集**（FR-021 ②④）。
#:
#: 正确口径 = **禁止第三方品牌资产**；**自有**资产（项目自有 logo / 架构图 /
#: 演示截图）MUST 登记在本清单中 ⇒ **MUST NOT** 采用「白名单为空 ⇒ 禁止一切
#: 图像」的过宽口径（那会连**自有** logo 一并禁掉，超出宪法原则 IX 第三条范围）。
OWN_BRAND_ASSET_ALLOWLIST: frozenset[str] = frozenset()

#: **禁止文案指纹**扫描的**具名例外**（FR-021 ② · 已写死 · 非「按需新增」的豁免入口）。
#:
#: 两个条目**缺一不可** —— 否则门禁**永久红**（违反宪法 v1.6.0 红线
#: 「MUST NOT 写永久红的 CI」）：
#:
#: ① **指纹清单的载体** —— 禁止文案指纹 MUST 记录在某处（否则无从判定）；
#:    载体本身必然包含这些片段 ⇒ MUST 排除；
#: ② **证据文档** —— 调研报告引用官方原文以**记录商标边界**（宪法原则 VIII 的
#:    来源标记义务）⇒ MUST 排除。
#:
#: **MUST NOT** 把本清单当成「按需新增」的豁免入口（FR-018 ①）——
#: 扩充 MUST 走评审（与层注册表 §3 同纪律）。
BRAND_COPY_EXCLUDED_FILES: frozenset[str] = frozenset(
    {
        "specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md",
        "harness/reports/Q7-开源边界地图与许可证合规.md",
    }
)

#: 层注册表的**默认路径**（相对仓库根）。
DEFAULT_REGISTRY_RELPATH = "specs/b3f1-scaffold-ci-gates/contracts/layer-registry.md"

#: 遍历目录时 MUST 跳过的目录名（构建产物 / 缓存 / 虚拟环境）。
SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        ".env",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
        "dist",
        "build",
        ".eggs",
    }
)


def configure_stdio() -> None:
    """把 ``stdout`` / ``stderr`` 切到 **UTF-8**（幂等）。

    **为什么**：Windows 的控制台 / 管道默认编码是 **cp1252 / cp936** ⇒ 门禁报告里
    的中文（规则文本、修复指引）会抛 ``UnicodeEncodeError`` ⇒ **作业直接崩**
    （实测：CI 首跑的 2 个 Windows 作业即止步于此）。

    CI 另外用 ``PYTHONUTF8=1`` 从环境侧兜底；本函数让脚本**脱离 CI 也能跑**。
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):  # pragma: no cover —— 某些流不可重配
            pass


configure_stdio()


# ── 违规报告（data-model.md §7 · FR-016 ①）─────────────────────────────


@dataclasses.dataclass(frozen=True)
class Violation:
    """一条违规 —— 三个要素**缺一不可**（FR-016 ①）。"""

    entry: str
    """违规条目 —— **包名** 或 **文件路径:行号**。"""

    rule: str
    """命中的**规则编号**（否则「指不出是哪条规则」）。"""

    detail: str = ""
    """细节 —— 附加信息（出现在哪个变体 / 实测到的许可证标识 / 调用栈 …）。"""

    fix: str = ""
    """**修复指引** —— 具体动作（MUST NOT 是「请修复」这类空话）。"""


def report(violations: Sequence[Violation], gate_id: str, rule_text: str) -> int:
    """打印**统一格式**的违规报告并返回**退出码**。

    退出码：**0 = 通过** · **非 0 = 失败**（MUST NOT 吞掉失败）。
    """
    if not violations:
        print(f"[{gate_id}] PASS —— {rule_text}")
        return 0
    print(f"[{gate_id}] FAIL —— {rule_text}")
    for violation in violations:
        print(f"  违规条目: {violation.entry}")
        print(f"  规则编号: {violation.rule}")
        if violation.detail:
            print(f"  细节    : {violation.detail}")
        print(f"  修复指引: {violation.fix}")
    print(f"[{gate_id}] 共 {len(violations)} 条违规")
    return 1


def run_gate(
    fn: "callable[[], int]",
    gate_id: str = "G??",
    rule_text: str = "",
) -> int:
    """包装门禁主逻辑 —— **异常判失败**而非崩溃（MUST NOT 静默通过）。"""
    try:
        return int(fn())
    except Exception as exc:  # noqa: BLE001 —— 门禁异常 ⇒ 判失败
        print(
            f"[{gate_id}] ERROR —— 门禁执行异常（判失败，非崩溃）："
            f"{type(exc).__name__}: {exc}"
        )
        return 2


# ── 隔离副本（负向验证的工作树隔离副本 · research D-12）──────────────────


def make_isolated_copy(root: Path, dest: Path | None = None) -> Path:
    """构造**可构建**的隔离副本（负向验证的被检树）。

    **MUST 含** ``pyproject.toml`` + ``src/`` + ``README.md`` + ``LICENSE``
    —— 后两者是 ``pyproject.toml`` 的**硬引用**（``readme`` / ``license-files``），
    缺一即构建失败（实测 ``OSError: Readme file does not exist: README.md``）
    ⇒ 缺任一即会让门禁在**构建阶段**而非**断言阶段**失败。

    另含 ``harness/demo/``（只读基准 + 验收脚本集）—— G29 的只读基准 diff 与
    验收脚本集退出码断言需要它们。

    **pytest 夹具与门禁脚本的 ``--self-test-negative`` 共用本函数**
    ⇒ MUST NOT 各写一份拷贝逻辑（裁定 8 第三条理由）。
    """
    root = Path(root).resolve()
    if dest is None:
        dest = Path(tempfile.mkdtemp(prefix="freegraph-isolated-"))
    dest = Path(dest)
    copy = dest / root.name
    copy.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / "pyproject.toml", copy / "pyproject.toml")
    for name in ("README.md", "LICENSE"):
        source = root / name
        if source.is_file():
            shutil.copy2(source, copy / name)
    src_tree = root / "src"
    if src_tree.is_dir():
        shutil.copytree(src_tree, copy / "src", dirs_exist_ok=True)
    demo_tree = root / "harness" / "demo"
    if demo_tree.is_dir():
        shutil.copytree(demo_tree, copy / "harness" / "demo", dirs_exist_ok=True)
    return copy


# ── 层注册表（层归属的**唯一权威** · research D-07）──────────────────────


@dataclasses.dataclass(frozen=True)
class LayerEntry:
    """层注册表的一条**层条目**（4 列 · 目录优先 + 文件精确）。"""

    path: str
    layer: str
    exception: str
    note: str

    @property
    def is_directory(self) -> bool:
        """该条目是**目录**（前缀匹配）还是**文件**（精确匹配）。"""
        return self.path.endswith("/")

    @property
    def is_cross_layer(self) -> bool:
        """是否**跨层单元**（层 = ``—``）。"""
        return self.layer == CROSS_LAYER


@dataclasses.dataclass(frozen=True)
class Declaration:
    """层注册表 §0.3 的**可判定的声明**（如 **L-1** / **L-2**）。"""

    ident: str
    text: str
    owner: str
    paths: tuple[str, ...]
    forbids_internal_import: bool

    @property
    def judged_by_gate25(self) -> bool:
        """该声明是否由 **G25** 判（``L-2`` 归既有 G2 ⇒ G25 **不重复判**）。"""
        return "G25 判" in self.owner and "不重复判" not in self.owner


@dataclasses.dataclass(frozen=True)
class LayerRegistry:
    """层注册表的解析结果（**条目** + **可判定的声明**）。"""

    entries: tuple[LayerEntry, ...]
    declarations: tuple[Declaration, ...]

    def __iter__(self) -> Iterator[LayerEntry]:
        return iter(self.entries)

    def match(self, rel_path: str) -> LayerEntry | None:
        """**最长前缀优先**地匹配一个仓库相对路径（目录前缀 + 文件精确）。

        未匹配到任何条目 ⇒ 返回 ``None``（调用方 MUST 判失败并指名 ——
        MUST NOT 静默放行 · FR-008 ②）。
        """
        best: LayerEntry | None = None
        for entry in self.entries:
            if entry.is_directory:
                if not rel_path.startswith(entry.path):
                    continue
            elif rel_path != entry.path:
                continue
            if best is None or len(entry.path) > len(best.path):
                best = entry
        return best

    @property
    def cross_layer_paths(self) -> tuple[str, ...]:
        """注册表声明的**全部跨层单元路径**（G25 的扫描域之一）。"""
        return tuple(
            entry.path for entry in self.entries if entry.is_cross_layer
        )


def _iter_markdown_tables(text: str) -> Iterator[list[list[str]]]:
    """产出 markdown 表格 —— 每张表 = ``[[表头单元格…], [数据行单元格…], …]``。"""
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        if lines[index].lstrip().startswith("|"):
            block: list[str] = []
            while index < len(lines) and lines[index].lstrip().startswith("|"):
                block.append(lines[index].strip())
                index += 1
            rows = [_table_cells(row) for row in block]
            if len(rows) >= 2:
                yield rows
        else:
            index += 1


def _is_separator_row(cells: Sequence[str]) -> bool:
    """markdown 表格的**分隔行**（``|---|---|``）—— 不是数据行。"""
    return all(
        set(cell) <= {"-", ":"} and cell for cell in cells
    )


def _table_cells(row: str) -> list[str]:
    """把一行 markdown 表格切成单元格列表。"""
    stripped = row.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _strip_backticks(text: str) -> str:
    """去掉反引号包裹（注册表里的路径 / 层号都是反引号形态）。"""
    return text.strip().strip("`").strip()


def load_layer_registry(repo_root: Path) -> LayerRegistry:
    """解析**层注册表** —— 层归属的**唯一权威**。

    ``repo_root`` 既可以是**仓库根**（则取 `DEFAULT_REGISTRY_RELPATH`），
    也可以直接是**注册表文件**（负向验证用副本时用）。

    解析两张表：

    ① §1 的**条目表**（4 列：路径 / 层 / 例外 / 说明）；
    ② §0.3 的**可判定的声明表**（3 列：编号 / 声明 / 判定归属）——
       **MUST 同时解析**（否则 §0.3 的声明在实现中不可判定 = 等于没写）。

    **MUST NOT** 在门禁实现里硬编码任何层归属（层归属的唯一权威 = 该注册表）。
    """
    given = Path(repo_root)
    registry_path = given if given.is_file() else given / DEFAULT_REGISTRY_RELPATH
    text = registry_path.read_text(encoding="utf-8")
    entries: list[LayerEntry] = []
    declarations: list[Declaration] = []
    for table in _iter_markdown_tables(text):
        header = [cell.strip() for cell in table[0]]
        if header[:4] == ["路径", "层", "例外", "说明"]:
            for row in table[1:]:
                if len(row) < 4 or _is_separator_row(row):
                    continue
                path = _strip_backticks(row[0])
                if not path:
                    continue
                entries.append(
                    LayerEntry(
                        path=path,
                        layer=_strip_backticks(row[1]),
                        exception=_strip_backticks(row[2]),
                        note=row[3],
                    )
                )
        elif header[:3] == ["编号", "声明", "判定归属"]:
            for row in table[1:]:
                if len(row) < 3 or _is_separator_row(row):
                    continue
                ident = _strip_backticks(row[0]).strip("*").strip()
                statement = row[1]
                paths = tuple(
                    _strip_backticks(token)
                    for token in re.findall(r"`([^`]+)`", statement)
                    if "/" in token
                )
                declarations.append(
                    Declaration(
                        ident=ident,
                        text=statement,
                        owner=row[2],
                        paths=paths,
                        forbids_internal_import="MUST NOT import" in statement,
                    )
                )
    return LayerRegistry(entries=tuple(entries), declarations=tuple(declarations))


# ── AST 扫描工具 ──────────────────────────────────────────────────────────


@dataclasses.dataclass(frozen=True)
class ImportEdge:
    """一条 import 边（源模块 → 目标模块）。"""

    module: str
    """目标模块名（绝对导入时是点号形态；相对导入时是 ``from`` 后的部分）。"""

    names: tuple[str, ...]
    """``from X import a, b`` 的被导入名字。"""

    level: int
    """相对层级（``0`` = 绝对导入 · ``>= 1`` = 相对导入）。"""

    lineno: int


def scan_imports(path: Path) -> list[ImportEdge]:
    """扫描一个模块的**全部** import（``import`` / ``from … import`` / 相对导入）。

    第三方 import **不**产生层边（由 G2 / G17 判）—— 层的判定见
    `resolve_internal_module`。
    """
    tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=str(path))
    edges: list[ImportEdge] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                edges.append(
                    ImportEdge(
                        module=alias.name,
                        names=(),
                        level=0,
                        lineno=node.lineno,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            edges.append(
                ImportEdge(
                    module=node.module or "",
                    names=tuple(alias.name for alias in node.names),
                    level=node.level or 0,
                    lineno=node.lineno,
                )
            )
    return edges


def _root_name(node: ast.AST) -> str:
    """取属性链 / 名字的**根标识符**（``os.environ.get`` ⇒ ``os``）。"""
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        current = current.value
    if isinstance(current, ast.Name):
        return current.id
    return ""


def _dotted_name(node: ast.AST) -> str:
    """把属性链还原成点号形态（``os.environ`` / ``asyncio.open_connection``）。"""
    parts: list[str] = []
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def scan_env_reads(path: Path) -> list[tuple[int, str]]:
    """扫描环境变量读取 —— **四种形态全须覆盖**（FR-007）。

    ① ``os.environ``（属性链）· ② ``os.getenv``（属性链）·
    ③ ``os.environb``（属性链）· ④ ``from os import environ / getenv / environb``
    （**导入形态**）。

    与既有 `tests/facade/_gatesupport.py` 的 `env_and_io_violations` **同口径**
    （既有实现已明确覆盖导入形态并写进 docstring）⇒
    **漏掉导入形态 ⇒ G24 可被 ``from os import getenv`` 绕过**。

    返回的标识里**尽量带上被读的键名**（``os.environ['LANGSMITH_API_KEY']``）
    ⇒ G24 才能区分「配置层黑名单」与「其它环境变量读取」。
    """
    tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=str(path))
    hits: dict[int, tuple[int, str]] = {}
    os_aliases: set[str] = set()
    env_bindings: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "os":
                    os_aliases.add(alias.asname or "os")
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module == "os":
                for alias in node.names:
                    if alias.name in FORBIDDEN_ENV_ATTRS:
                        env_bindings.add(alias.asname or alias.name)
                        hits[id(node)] = (node.lineno, f"from os import {alias.name}")
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            target = node.value
            if (
                isinstance(target, ast.Attribute)
                and target.attr in {"environ", "environb"}
                and _root_name(target.value) in os_aliases
            ):
                key = ""
                slice_node = node.slice
                if isinstance(slice_node, ast.Constant) and isinstance(
                    slice_node.value, str
                ):
                    key = slice_node.value
                label = f"os.{target.attr}[{key!r}]" if key else f"os.{target.attr}"
                hits[id(target)] = (node.lineno, label)
        elif isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "getenv"
                and _root_name(func.value) in os_aliases
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                hits[id(func)] = (node.lineno, f"os.getenv({node.args[0].value!r})")
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if id(node) in hits:
                continue
            if node.attr in FORBIDDEN_ENV_ATTRS and _root_name(node.value) in os_aliases:
                hits[id(node)] = (node.lineno, f"os.{node.attr}")
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in env_bindings:
            hits[id(node)] = (node.lineno, node.id)
    return sorted(hits.values())


def scan_network_calls(path: Path) -> list[tuple[int, str]]:
    """扫描**网络客户端**的导入 / 使用（architecture-gates.md G26）。

    判定以 **import 形式**为准（``import X`` / ``from X import …``）⇒
    清单内的**纯 stdlib 常量用法**（如 ``http.HTTPStatus``）会被**一并命中**
    ⇒ 这类形态需**具名例外**才可通过（MUST NOT 因此放宽清单本身）。

    ``asyncio.open_connection`` 不是可导入的模块名 ⇒ 另按**属性链**形态判定。
    """
    tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=str(path))
    hits: set[tuple[int, str]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _matches_network_module(alias.name):
                    hits.add((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module and _matches_network_module(module):
                hits.add((node.lineno, module))
            for alias in node.names:
                if module and _matches_network_module(f"{module}.{alias.name}"):
                    hits.add((node.lineno, f"{module}.{alias.name}"))
        elif isinstance(node, ast.Attribute):
            dotted = _dotted_name(node)
            if dotted in NETWORK_CLIENT_MODULES:
                hits.add((node.lineno, dotted))
    return sorted(hits)


def _matches_network_module(name: str) -> bool:
    """一个导入名是否命中**网络客户端清单**（逐名 / 前缀精确匹配）。"""
    for candidate in NETWORK_CLIENT_MODULES:
        if name == candidate or name.startswith(candidate + "."):
            return True
    return False


# ── 模块定位（import 目标 ⇒ 仓库内路径）─────────────────────────────────


def _package_parts(rel_path: str) -> tuple[str, ...]:
    """求一个仓库相对 ``.py`` 路径所属**包**的点号形态。

    ``src/freegraph/contracts/protocols.py`` ⇒ ``("freegraph", "contracts")``；
    ``src/freegraph/contracts/__init__.py`` ⇒ ``("freegraph", "contracts")``。
    """
    parts = rel_path.split("/")[:-1]
    if parts and parts[0] == "src":
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return tuple(parts)


def _module_candidates(
    rel_path: str, edge: ImportEdge
) -> list[str]:
    """列出一个 import 边可能的**目标模块名**（含 ``from X import a`` 的子模块候选）。"""
    if edge.level == 0:
        base = edge.module
        candidates = [base] if base else []
        candidates.extend(f"{base}.{name}" for name in edge.names if base)
        return candidates
    package = _package_parts(rel_path)
    cut = len(package) - (edge.level - 1)
    prefix = package[: max(cut, 0)]
    base = ".".join([*prefix, edge.module] if edge.module else prefix)
    candidates = [base] if base else []
    candidates.extend(f"{base}.{name}" for name in edge.names if base)
    return candidates


def resolve_internal_module(
    root: Path,
    registry: LayerRegistry,
    importer_rel_path: str,
    edge: ImportEdge,
) -> Path | None:
    """把 import 目标**定位到具体路径**（层判定的机械步骤）。

    口径（`layer-registry.md` §0.2 规则 3 的注 · 与 spec FR-008 ④ /
    `data-model.md` §5.2 / `architecture-gates.md` G25 第 4 条 **四处一致**）：

    * 落在**同一注册表条目**下 ⇒ 单元内部引用（**不产生层边**）；
    * 落在**其它条目**下 ⇒ 按层间方向判定；
    * **无法解析到仓库内路径** ⇒ 视为第三方 ⇒ **不产生层边**。

    解析顺序：相对导入按**包层级**解析；绝对导入先试源码树（``src/<pkg>/…``），
    再试**导入方所在目录**（脚本目录语义 —— 如门禁脚本的 ``import _gatekit``）。
    """
    root = Path(root)
    importer_dir = (root / importer_rel_path).parent
    for candidate in _module_candidates(importer_rel_path, edge):
        parts = candidate.split(".")
        relative = Path(*parts)
        for base in (root / "src", importer_dir):
            module_path = base / relative.with_suffix(".py")
            if module_path.is_file():
                return module_path
            package_path = base / relative / "__init__.py"
            if package_path.is_file():
                return package_path
    return None


# ── 许可证据链 + SPDX 表达式（dependency-gate.md §3 / §4）────────────────


class SpdxParseError(ValueError):
    """许可标识**无法**解析为 SPDX 表达式（散文式名称即此例）。"""


def split_name_version(stem: str) -> tuple[str, str]:
    """把 ``<name>-<version>`` 拆成 ``(name, version)``（wheel 的命名约定）。

    ``agpl-pkg-1.0.0`` ⇒ ``("agpl-pkg", "1.0.0")``；``typing-extensions-4.16.0``
    ⇒ ``("typing-extensions", "4.16.0")``（版本号以数字开头 ⇒ 名字里的 ``-``
    不会误判）。
    """
    match = re.match(r"^(?P<name>.+?)-(?P<version>\d.*)$", stem)
    if match:
        return match.group("name"), match.group("version")
    return stem, ""


def _metadata_from_root(root: Path, pkg: str) -> object | None:
    """从取证作用域根下取 ``<name>-<version>.dist-info/METADATA`` 的元数据。"""
    root = Path(root)
    if not root.is_dir():
        return None
    normalized = pkg.lower().replace("_", "-")
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        name = child.name
        if name.endswith(".dist-info"):
            stem = name[: -len(".dist-info")]
        elif name.endswith(".egg-info"):
            stem = name[: -len(".egg-info")]
        else:
            continue
        package, _version = split_name_version(stem)
        if package.lower().replace("_", "-") != normalized:
            continue
        metadata_path = (
            child / "METADATA" if name.endswith(".dist-info") else child / "PKG-INFO"
        )
        if metadata_path.is_file():
            return _parse_metadata(metadata_path.read_text(encoding="utf-8"))
    return None


def _parse_metadata(text: str) -> object:
    """把 METADATA / PKG-INFO 文本解析成 ``email.message.Message``。"""
    import email.parser

    return email.parser.Parser().parsestr(text)


def _license_from_metadata(metadata: object) -> tuple[str, str] | None:
    """四级证据链的**前三级**（同一份元数据内 · 取到即止）。"""
    expr = metadata.get("License-Expression")  # type: ignore[attr-defined]
    if expr and expr.strip() and expr.strip().upper() != "UNKNOWN":
        return ("License-Expression", expr.strip())
    lic = metadata.get("License")  # type: ignore[attr-defined]
    if lic and lic.strip() and lic.strip().upper() != "UNKNOWN":
        return ("License", lic.strip())
    classifiers = metadata.get_all("Classifier") or []  # type: ignore[attr-defined]
    for classifier in classifiers:
        if classifier.startswith("License ::"):
            return ("License :: 分类器", classifier.strip())
    return None


def _license_file_text(pkg: str, root: Path | None = None) -> str | None:
    """第四级证据链 —— ``dist-info/licenses/`` 下的**授权文件原文**。

    **⚠️ 为什么「原文」而不是「识别出的标识」**：第 4 级的授权文件是**散文**
    （``MIT License\\n\\nCopyright (c) ...``）⇒ 要把它「识别」成 SPDX id
    就必须引入**等价标识符对照表 / 家族判定** ⇒ **裁定 18 明令禁止**
    （FR-006 ①①① · FR-018）⇒ 故本函数**只取原文**（文件头部若干行），
    由 SPDX 解析器接手 ⇒ 散文式标识**解析失败** ⇒ 按 FR-006 ③② 的
    「识别不出 ⇒ 判失败并指名」处置。
    """
    candidates: list[Path] = []
    if root is not None:
        normalized = pkg.lower().replace("_", "-")
        for child in sorted(Path(root).iterdir()) if Path(root).is_dir() else []:
            if child.is_dir() and child.name.lower().startswith(normalized):
                candidates.append(child / "licenses")
    try:
        distribution = importlib.metadata.distribution(pkg)
    except importlib.metadata.PackageNotFoundError:
        distribution = None
    if distribution is not None:
        located = getattr(distribution, "_path", None)
        if located is not None:
            candidates.append(Path(located) / "licenses")
    for licenses_dir in candidates:
        if not licenses_dir.is_dir():
            continue
        for license_file in sorted(licenses_dir.iterdir()):
            if not license_file.is_file():
                continue
            text = license_file.read_text(encoding="utf-8", errors="replace")
            head = "\n".join(text.splitlines()[:20]).strip()
            if head:
                return head
    return None


def license_evidence(
    pkg: str, root: Path | None = None
) -> tuple[str, str] | None:
    """取一个包的**许可证据** ⇒ ``(来源, 标识)``；**四级全无** ⇒ 返回 ``None``。

    证据链（**取到即止** · dependency-gate.md §3）：

    ① ``License-Expression``（PEP 639）→ ② ``License`` 字段 →
    ③ ``License ::`` 分类器 → ④ ``dist-info/licenses/`` 授权文件原文。

    **取证位置**（并集口径 · spec 裁定 25）：先取 ``root`` 下的元数据
    （第 1–3 级），后回落**已安装**元数据（第 1–3 级），最后才取**授权文件
    原文**（第 4 级）。

    **MUST NOT** 在四级全无时静默放行（FR-006 ② —— 调用方 MUST 判失败并指名）。
    """
    if root is not None:
        metadata = _metadata_from_root(root, pkg)
        if metadata is not None:
            found = _license_from_metadata(metadata)
            if found is not None:
                return (f"{root} 下的元数据 · {found[0]}", found[1])
    try:
        metadata = importlib.metadata.metadata(pkg)
    except importlib.metadata.PackageNotFoundError:
        metadata = None
    if metadata is not None:
        found = _license_from_metadata(metadata)
        if found is not None:
            return (f"已安装元数据 · {found[0]}", found[1])
    text = _license_file_text(pkg, root)
    if text is not None:
        return ("dist-info/licenses/ 授权文件原文", text)
    return None


def spdx_leaves(expression: str) -> set[str]:
    """把许可标识解析为 SPDX 表达式并取**叶子**（逐叶子判定 · FR-006 ④）。

    **叶子的取法**（research D-05 · MUST 照此实现）：
    `packaging.licenses` 的**公开面**只有 `canonicalize_license_expression` /
    `InvalidLicenseExpression` / `NormalizedLicenseExpression` ——
    **不存在**表达式树 / 叶子迭代 API（返回值是**普通 str**）⇒
    叶子 MUST 取自**规范化输出**：**按空白分词**、剔除
    ``AND`` / ``OR`` / ``WITH`` / ``(`` / ``)`` 后取剩余 token。

    **MUST NOT** 对**原始标识**做字符级切分（``re.split(r"[|&()]")`` 会把
    ``MIT AND PSF-2.0`` 误切成 1 个 token）；**MUST NOT** 引入等价标识符对照表 /
    家族判定（裁定 18）。

    解析失败（散文式名称，如 ``3-Clause BSD License``）⇒ 抛 `SpdxParseError`
    ⇒ 调用方 MUST 判失败。
    """
    from packaging.licenses import canonicalize_license_expression

    try:
        normalized = canonicalize_license_expression(expression)
    except Exception as exc:  # noqa: BLE001 —— InvalidLicenseExpression 等
        raise SpdxParseError(f"{expression!r} 无法解析为 SPDX 表达式：{exc}") from exc
    operators = {"AND", "OR", "WITH", "(", ")"}
    return {token for token in normalized.split() if token not in operators}


# ── extras 变体 + 依赖闭包（dependency-gate.md §2）────────────────────────


@dataclasses.dataclass(frozen=True)
class Variant:
    """一个 **extras 变体**（基础 + 每个 extra 单独 + 全部同时 ⇒ 6 个）。"""

    name: str
    extras: frozenset[str]


@dataclasses.dataclass
class ClosureResult:
    """某个变体的**依赖闭包**。"""

    packages: set[str]
    """闭包内的**全部包名**（PEP 503 规范化：小写 + ``_`` → ``-``）。"""

    missing: set[str]
    """**未安装 ⇒ 无法取证**的包（调用方 MUST 判失败并指名）。"""


def normalize_package_name(name: str) -> str:
    """PEP 503 规范化（**小写** + ``_`` → ``-``）。"""
    return name.strip().lower().replace("_", "-")


def requirement_name(spec: str) -> str:
    """取一条 requirement 声明的**包名**（去掉版本约束 / extras / marker）。"""
    head = spec.partition(";")[0].strip()
    head = head.split("[")[0]
    match = re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*", head)
    return match.group(0) if match else head


def read_requires_dist(pyproject_path: Path) -> list[str]:
    """读 ``pyproject.toml`` 的 ``Requires-Dist`` 形态声明（**带 marker**）。

    = ``[project].dependencies`` + ``[project.optional-dependencies]`` 的各 extra。
    """
    data = tomllib.loads(Path(pyproject_path).read_text(encoding="utf-8"))
    project = data.get("project", {})
    specs: list[str] = []
    for item in project.get("dependencies", []) or []:
        specs.append(str(item))
    for extra, items in (project.get("optional-dependencies", {}) or {}).items():
        for item in items or []:
            specs.append(f'{item}; extra == "{extra}"')
    return specs


def enumerate_variants(pyproject_path: Path) -> list[Variant]:
    """枚举**全部 extras 变体**（**6 个** · 基础 1 + 单独 4 + 全部同时 1）。

    **MUST NOT** 漏掉任一**单独**的 extra ⇒ 否则该 extra 的依赖**永不被判**。
    """
    data = tomllib.loads(Path(pyproject_path).read_text(encoding="utf-8"))
    extras = list((data.get("project", {}).get("optional-dependencies", {}) or {}))
    variants = [Variant(name="基础安装", extras=frozenset())]
    for extra in extras:
        variants.append(Variant(name=f"仅 [{extra}]", extras=frozenset({extra})))
    variants.append(
        Variant(name="全部 extras 同时启用", extras=frozenset(extras))
    )
    return variants


_EXTRA_EQUAL = re.compile(r"""extra\s*==\s*["']([^"']+)["']""")
_EXTRA_NOT_EQUAL = re.compile(r"""extra\s*!=\s*["']([^"']+)["']""")


def evaluate_variant(requires: Sequence[str], variant: Variant) -> set[str]:
    """按 marker 求值 ⇒ 该变体下**成立**的声明集合。

    * 无 marker ⇒ **恒成立**（基础依赖）；
    * ``extra == "X"`` ⇒ 当且仅当 ``X ∈ variant`` 时成立；
    * **其它 marker**（如 ``python_version``）⇒ **必须求值**（MUST NOT 忽略）。

    实现口径：``extra`` 条件**手工判定**（变体的定义就是「哪些 extra 被启用」），
    其余条件交给 ``packaging.markers`` 在**当前环境**上求值（``extra`` 位置
    填入被选中的 extra 名或空串）。
    """
    from packaging.markers import Marker

    active: set[str] = set()
    for spec in requires:
        marker_text = spec.partition(";")[2].strip()
        if not marker_text:
            active.add(spec)
            continue
        selected = _EXTRA_EQUAL.findall(marker_text)
        if selected and not all(name in variant.extras for name in selected):
            continue
        if _EXTRA_NOT_EQUAL.search(marker_text) and not variant.extras:
            continue
        environment = {"extra": selected[0] if selected else ""}
        try:
            satisfied = bool(Marker(marker_text).evaluate(environment))
        except Exception:  # noqa: BLE001 —— marker 无法求值 ⇒ 保守判不成立
            satisfied = False
        if satisfied:
            active.add(spec)
    return active


def _transitive_active(spec: str) -> bool:
    """传递依赖的一条声明是否**基础**（不含 extras）且在当前环境成立。

    **传递依赖的 extras 一律不展开**（只取其**基础**依赖）—— extra 是
    「**freegraph 对用户的承诺**」，不是「传递依赖的私有细节」。
    """
    from packaging.markers import Marker

    marker_text = spec.partition(";")[2].strip()
    if not marker_text:
        return True
    if "extra" in marker_text:
        return False
    try:
        return bool(Marker(marker_text).evaluate())
    except Exception:  # noqa: BLE001
        return False


def closure(variant: Variant, pyproject_path: Path) -> ClosureResult:
    """展开某个变体的**依赖闭包**（**递归走到闭包末端**）。

    **未安装的依赖 ⇒ 显式报「未安装 ⇒ 无法取证」**（进 `missing`），
    **MUST NOT** 静默跳过 —— 静默跳过会把「闭包只到第一层」伪装成「闭包干净」
    ⇒ 间接引入的黑名单包**永远抓不到**（spec Edge Case）。
    """
    requires = read_requires_dist(pyproject_path)
    direct = evaluate_variant(requires, variant)
    packages: set[str] = set()
    missing: set[str] = set()
    queue: list[str] = []
    for spec in sorted(direct):
        name = requirement_name(spec)
        key = normalize_package_name(name)
        if key in packages:
            continue
        packages.add(key)
        queue.append(name)
    while queue:
        name = queue.pop(0)
        try:
            sub_requires = importlib.metadata.requires(name)
        except importlib.metadata.PackageNotFoundError:
            missing.add(normalize_package_name(name))
            continue
        for spec in sub_requires or []:
            if not _transitive_active(spec):
                continue
            sub_name = requirement_name(spec)
            key = normalize_package_name(sub_name)
            if key in packages:
                continue
            packages.add(key)
            queue.append(sub_name)
    return ClosureResult(packages=packages, missing=missing)


# ── 出站归因 + socket 包装（裁定 19 · 只观测不阻断）────────────────────────


@dataclasses.dataclass(frozen=True)
class StackFrame:
    """调用栈的一帧。"""

    module: str
    """帧所在模块的点号名（``socket`` / ``freegraph.graph`` / ``__main__`` …）。"""

    path: str = ""
    """帧所在文件的路径。"""


@dataclasses.dataclass(frozen=True)
class EgressRecord:
    """一条**出站记录**（目标 + 栈帧 + 归因）。"""

    target: str
    frames: tuple[StackFrame, ...]
    attribution: str
    """``framework``（框架出站）· ``user``（用户出站）。"""


def _is_freegraph_frame(frame: StackFrame) -> bool:
    """该帧是否属于 **freegraph 包**内。

    判据取**模块的点号名**（``freegraph`` / ``freegraph.*``）⇒ 源码树与安装
    形态**都**成立。

    > **⚠️ MUST NOT** 用「文件路径里含 ``freegraph/``」当判据 ——
    > **仓库目录本身就叫 ``freegraph``** ⇒ 用户的测试脚本也会被误判成
    > 「框架出站」⇒ 门禁假红（裁定 19 的反面）。
    """
    module = frame.module
    return module == "freegraph" or module.startswith("freegraph.")


def attribute_egress(frames: Sequence[StackFrame]) -> str:
    """出站**归因** —— 从栈顶（最靠近连接发生处）向下遍历。

    * **跳过全部标准库帧**（用 ``sys.stdlib_module_names``）；
    * 遇到的**第一个非标准库帧**在 ``freegraph/`` 包内 ⇒ ``"framework"``；
    * 否则 ⇒ ``"user"``；
    * 全是标准库帧 ⇒ ``"user"``。

    裁定 19：用户工具函数联网（freegraph 只是调用方）⇒ **用户出站**
    —— MUST NOT 误判为框架出站（否则用户正常用 AI 工具访问外网会每次把门禁打红）。
    """
    for frame in frames:
        root = frame.module.split(".")[0] if frame.module else ""
        if root and root in sys.stdlib_module_names:
            continue
        return "framework" if _is_freegraph_frame(frame) else "user"
    return "user"


def _capture_frames() -> tuple[StackFrame, ...]:
    """采集**调用方**的调用栈（跳过本函数与 socket 包装器自身）。"""
    frames: list[StackFrame] = []
    frame = sys._getframe(2)
    while frame is not None:
        frames.append(
            StackFrame(
                module=frame.f_globals.get("__name__", ""),
                path=frame.f_code.co_filename,
            )
        )
        frame = frame.f_back
    return tuple(frames)


def _format_target(address: object) -> str:
    """把连接目标格式化成 ``host:port``（Unix 路径原样）。"""
    if isinstance(address, tuple) and len(address) >= 2:
        return f"{address[0]}:{address[1]}"
    return str(address)


@contextlib.contextmanager
def record_egress(records: list[EgressRecord]) -> Iterator[None]:
    """只包装 ``socket.connect`` / ``socket.create_connection``。

    **只观测不阻断** —— **记录**目标与调用栈、**放行**全部连接
    （FR-009 ② · 裁定 7）⇒ **MUST NOT** 安装任何出网拦截机制。

    归因在**连接发生前**计算 ⇒ 即便连接失败（断网 / 端口未监听）也已**记录在案**。
    """
    original_connect = socket.socket.connect
    original_create_connection = socket.create_connection

    def connect_wrapper(self: socket.socket, address: object, *args: object, **kwargs: object) -> object:
        frames = _capture_frames()
        records.append(
            EgressRecord(
                target=_format_target(address),
                frames=frames,
                attribution=attribute_egress(frames),
            )
        )
        return original_connect(self, address, *args, **kwargs)  # type: ignore[arg-type]

    def create_connection_wrapper(address: object, *args: object, **kwargs: object) -> object:
        frames = _capture_frames()
        records.append(
            EgressRecord(
                target=_format_target(address),
                frames=frames,
                attribution=attribute_egress(frames),
            )
        )
        return original_create_connection(address, *args, **kwargs)  # type: ignore[arg-type]

    socket.socket.connect = connect_wrapper  # type: ignore[method-assign]
    socket.create_connection = create_connection_wrapper  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket.connect = original_connect  # type: ignore[method-assign]
        socket.create_connection = original_create_connection  # type: ignore[assignment]


# ── 文件清单 + 署名头（G30）───────────────────────────────────────────────


def _walk_files(root: Path) -> list[Path]:
    """遍历目录下的**全部**文件（跳过构建产物 / 缓存 / 虚拟环境）。"""
    files: list[Path] = []
    root = Path(root)
    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIR_NAMES for part in path.relative_to(root).parts[:-1]):
            continue
        if path.is_file():
            files.append(path)
    return files


def list_tracked_files(root: Path) -> list[Path]:
    """列出被检树内**受版本控制**的文件（``git ls-files``）。

    **非 git 树**（如负向验证的隔离副本）⇒ 退回文件系统遍历 ⇒
    隔离副本里注入的第三方品牌资产**照样可见**（反向用例不空转）。
    """
    root = Path(root).resolve()
    try:
        toplevel = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
        listed = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return _walk_files(root)
    if toplevel.returncode == 0 and listed.returncode == 0:
        try:
            same_tree = Path(toplevel.stdout.strip()).resolve() == root
        except OSError:
            same_tree = False
        if same_tree:
            names = [name for name in listed.stdout.split("\0") if name]
            return [root / name for name in names]
    return _walk_files(root)


def signature_header_violations(path: Path, rel_path: str) -> list[str]:
    """G30 · 署名头 —— 返回违规清单（空 = 合规）。

    两条判据：① **顶部**署名头**逐字**相等（**首行**；**首行是 shebang 时取第二行**）；
    ② 模块 docstring 仍是**首个语句**（宪法原则 X · FR-013 ②）。
    """
    violations: list[str] = []
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    if not lines:
        return [f"{rel_path}: 文件为空"]
    header_index = 1 if lines[0].startswith("#!") else 0
    if len(lines) <= header_index or lines[header_index] != SIGNATURE_HEADER:
        violations.append(
            f"{rel_path}: 顶部署名头缺失或不逐字相等"
            f"（{'第二行（shebang 之后）' if header_index else '首行'}）"
        )
    tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=str(path))
    if not ast.get_docstring(tree):
        violations.append(f"{rel_path}: 缺少模块 docstring")
    elif not (
        isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
    ):
        violations.append(f"{rel_path}: 模块 docstring 不是首个语句")
    return violations


def brand_asset_violations(root: Path, files: Sequence[Path]) -> list[str]:
    """G30 · 第三方品牌资产 —— 返回违规清单（空 = 合规）。

    三类扫描域（FR-021 ①）：

    ① **图像资产**（``.svg`` / ``.png`` / ``.ico`` / ``.jpg`` / ``.jpeg`` /
       ``.webp`` / ``.gif`` …）—— 按扩展名全量扫描；
    ② **品牌色定义** —— 与「禁止色值清单」逐值比对（**当前为空集 ⇒ 待取证**）；
    ③ **官方 "Approved copy" 描述文案** —— 与「禁止文案指纹清单」逐条子串比对
       （大小写不敏感）；扫描域 = 受版本控制的 ``.md`` + ``.css`` / ``.scss``。

    **白名单口径**（FR-021 ②）：= **禁止第三方品牌资产**；**自有资产** MUST 登记
    在「自有品牌资产白名单」中 ⇒ **MUST NOT** 采用「白名单为空 ⇒ 禁止一切图像」
    的过宽口径。
    """
    violations: list[str] = []
    root = Path(root)
    for path in files:
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            rel = path.as_posix()
        suffix = path.suffix.lower()
        if suffix in BRAND_IMAGE_EXTENSIONS:
            if rel in OWN_BRAND_ASSET_ALLOWLIST:
                continue
            violations.append(f"{rel}: 第三方品牌资产（图像）——仓库内 MUST NOT 出现")
            continue
        if suffix not in BRAND_TEXT_EXTENSIONS:
            continue
        if rel in BRAND_COPY_EXCLUDED_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lowered = text.lower()
        for fingerprint in FORBIDDEN_COPY_FINGERPRINTS:
            if fingerprint.lower() in lowered:
                violations.append(
                    f"{rel}: 第三方品牌资产（官方 Approved copy 文案指纹）"
                    f"—— {fingerprint!r}"
                )
        for color in FORBIDDEN_BRAND_COLORS:
            if color.lower() in lowered:
                violations.append(
                    f"{rel}: 第三方品牌资产（品牌色值）—— {color}"
                )
    return violations


# ── 杂项 ──────────────────────────────────────────────────────────────────


def git_show(ref: str, path: str, cwd: Path | None = None) -> str | None:
    """读 Git 索引中的某个文件（``git show <ref>:<path>``）；不存在 ⇒ ``None``。

    **只读** —— MUST NOT 改动工作树（基准侧的唯一载体）。
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(cwd or "."), "show", f"{ref}:{path}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def unified_diff(expected: str, actual: str, fromfile: str, tofile: str) -> str:
    """两段文本的 **unified diff**（空 = 逐字相同）。"""
    return "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile=fromfile,
            tofile=tofile,
        )
    )


def iter_python_files(root: Path) -> list[Path]:
    """列出目录下的全部 ``*.py``（按路径排序）。"""
    root = Path(root)
    if not root.is_dir():
        return []
    return sorted(path for path in root.rglob("*.py") if path.is_file())


def relative_to_root(path: Path, root: Path) -> str:
    """把路径转成**相对仓库根**的 posix 形态（报告里统一用它）。"""
    try:
        return Path(path).relative_to(Path(root)).as_posix()
    except ValueError:
        return Path(path).as_posix()


def iter_unique(items: Iterable[str]) -> list[str]:
    """去重并保持顺序。"""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out
