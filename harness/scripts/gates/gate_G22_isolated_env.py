# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""门禁 **G22** · 隔离环境断言（依赖闭包为空集 + ``sys.modules`` 无 langchain 家族）。

判据（`specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` G22）：

1. 用 ``uv venv`` 在临时目录建一个**全新虚拟环境**；
2. ``uv pip install <本仓库>``（**只装基础包**，**不装任何 extra**）；
3. 断言**基础安装的第三方依赖闭包 == 空集**（SC-002）—— 即环境内除
   ``freegraph`` 自身与安装器自带组件外**无任何第三方包**；
4. 在该环境中 ``import freegraph`` ⇒ 断言 ``sys.modules`` 中**无**
   ``langsmith`` / ``langchain_core`` / ``langgraph``（FR-005 ②）。

**场景 ② · 验收环境**（FR-005 ③ · 立项书 §9.2 断言③ · 裁定 22 分阶段落地）：

5. 在**同一** venv 里**额外**装 ``langchain-core`` ⇒ 断言
   ① **声明级**：freegraph 自身 ``Requires-Dist`` **无** ``langchain*`` /
   ``langsmith`` / ``langgraph*``；
   ② ``import freegraph`` **及** ``import freegraph.graph`` ⇒ 断言
   ``sys.modules`` 中**从未**出现 ``langchain`` / ``langchain_core`` /
   ``langgraph``（运行环境里有 ≠ 被 freegraph 引入）；
   ③ 同时断言**零出站**（复用 G27 的归因函数 ⇒ 框架出站 == 0）；
6. **③② 运行期（最小图）本 feature MUST NOT 实现** —— 待 B6F1 / B7F2 / B7F3
   交付内核运行时后由 **M2** 承接（裁定 22 · 立项书 §6.2）。

**CLI 契约**（architecture-gates.md §2.1）：``--target-root <路径>``（被检的
源码根，默认仓库根）· ``--project <pyproject 路径>``（默认
``<target-root>/pyproject.toml``）。

**解释器路径 MUST 跨平台**：命令串里**只出现 venv 目录**（``uv pip install
--python <venv>`` / ``uv run --no-project --python <venv> python …``）⇒
MUST NOT 出现任何平台专属的解释器路径（ci-matrix §2.0）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _gatekit  # noqa: E402 —— 共享判定库（同一目录 ⇒ 必然可导入）

GATE_ID = "G22"
RULE_TEXT = "隔离环境断言（依赖闭包为空集 + sys.modules 无 langchain 家族）"

REPO_ROOT = Path(__file__).resolve().parents[3]
GATES_DIR = REPO_ROOT / "harness" / "scripts" / "gates"

#: ``sys.modules`` 里**禁见**的模块族（FR-005 ②）。
FORBIDDEN_MODULE_ROOTS = ("langsmith", "langchain", "langchain_core", "langgraph")

#: 隔离环境里**允许**存在的包（freegraph 自身 + 安装器自带组件）。
ALLOWED_ENV_PACKAGES = {
    "freegraph",
    "pip",
    "setuptools",
    "wheel",
    "pkg-resources",
    "_distutils-hack",
}

_CLOSURE_SNIPPET = """
import importlib.metadata as m
import json
names = []
for dist in m.distributions():
    raw = dist.metadata["Name"] or ""
    name = raw.strip().lower().replace("_", "-")
    if not name:
        continue
    if name in set(%(allowed)s):
        continue
    names.append(name)
print(json.dumps(sorted(set(names))))
"""

_REQUIRES_SNIPPET = """
import importlib.metadata as m
import json
print(json.dumps(m.requires("freegraph") or []))
"""

_IMPORT_SNIPPET = """
import json
import sys
import freegraph
import freegraph.graph
roots = set(%(roots)s)
loaded = sorted(
    name for name in sys.modules if name.split(".")[0] in roots
)
print(json.dumps(loaded))
"""

_EGRESS_SNIPPET = """
import json
import sys
sys.path.insert(0, %(gates)s)
import _gatekit
records = []
with _gatekit.record_egress(records):
    import freegraph
    import freegraph.graph
framework = [r for r in records if r.attribution == "framework"]
print(json.dumps({
    "framework_egress": len(framework),
    "user_egress": len([r for r in records if r.attribution == "user"]),
    "targets": [r.target for r in framework],
}))
"""


def _run_in_venv(
    venv: Path, code: str, cwd: Path
) -> tuple[int, str, str]:
    """在隔离 venv 里跑一段 Python ⇒ ``(退出码, stdout, stderr)``。

    **解释器路径 MUST 跨平台** ⇒ 命令串里**只出现 venv 目录**。
    """
    command = [
        "uv",
        "run",
        "--no-project",
        "--python",
        str(venv),
        "python",
        "-c",
        code,
    ]
    proc = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _uv(*args: str, cwd: Path) -> tuple[int, str, str]:
    """跑一条 ``uv`` 命令 ⇒ ``(退出码, stdout, stderr)``。"""
    proc = subprocess.run(
        ["uv", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _declaration_violations(project: Path) -> list[_gatekit.Violation]:
    """**声明级**断言（③①）—— freegraph 自身不得声明 langchain 家族。"""
    violations: list[_gatekit.Violation] = []
    if not project.is_file():
        return violations
    for spec in _gatekit.read_requires_dist(project):
        name = _gatekit.requirement_name(spec).lower()
        if (
            name.startswith("langchain")
            or name.startswith("langgraph")
            or name.startswith("langsmith")
        ):
            violations.append(
                _gatekit.Violation(
                    entry=name,
                    rule="G22-03",
                    detail=f"freegraph 自身的依赖声明命中 langchain 家族：{spec}",
                    fix=(
                        "移除该声明——freegraph 内核 MUST NOT 依赖 LangChain 家族"
                        "（宪法原则 II · FR-005 ③①）"
                    ),
                )
            )
    return violations


def evaluate(target_root: Path, project: Path) -> list[_gatekit.Violation]:
    """在**隔离 venv** 里判定 ⇒ 违规清单（空 = 合规）。"""
    violations: list[_gatekit.Violation] = []
    violations.extend(_declaration_violations(project))
    with tempfile.TemporaryDirectory(prefix="freegraph-g22-venv-") as tmp:
        venv = Path(tmp) / "venv"
        code, out, err = _uv("venv", "--python", sys.executable, str(venv), cwd=target_root)
        if code != 0:
            return violations + [
                _gatekit.Violation(
                    entry="uv venv",
                    rule="G22-01",
                    detail=f"建隔离 venv 失败（退出码 {code}）：{err.strip()[:400]}",
                    fix="确认 uv 可用且能下载 Python 解释器（本门禁需联网）",
                )
            ]
        code, out, err = _uv(
            "pip", "install", "--python", str(venv), str(target_root), cwd=target_root
        )
        if code != 0:
            return violations + [
                _gatekit.Violation(
                    entry="uv pip install <target-root>",
                    rule="G22-01",
                    detail=(
                        f"在隔离环境安装被检包失败（退出码 {code}）："
                        f"{err.strip()[:400]}"
                    ),
                    fix=(
                        "确认被检根**可构建**——MUST 含 pyproject.toml + src/ + "
                        "README.md + LICENSE（后两者是 pyproject.toml 的硬引用）"
                    ),
                )
            ]
        # 场景 ① —— 基础安装的第三方闭包 == 空集
        snippet = _CLOSURE_SNIPPET % {
            "allowed": repr(sorted(ALLOWED_ENV_PACKAGES))
        }
        code, out, err = _run_in_venv(venv, snippet, target_root)
        if code != 0:
            violations.append(
                _gatekit.Violation(
                    entry="隔离环境 · 依赖闭包",
                    rule="G22-01",
                    detail=f"子进程失败（退出码 {code}）：{err.strip()[:400]}",
                    fix="修好隔离环境的探针脚本",
                )
            )
        else:
            packages = json.loads(out.strip().splitlines()[-1])
            if packages:
                violations.append(
                    _gatekit.Violation(
                        entry="、".join(packages),
                        rule="G22-01",
                        detail="基础安装的第三方依赖闭包 MUST 为空集（SC-002）",
                        fix=(
                            "移除基础安装的第三方依赖——`dependencies = []`"
                            "（宪法 v1.2.0 · 零第三方运行时依赖）"
                        ),
                    )
                )
            else:
                print(f"[{GATE_ID}] 隔离环境内的第三方包数 == 0（基础安装闭包为空集）")
        # 场景 ① —— sys.modules 无 langchain 家族
        snippet = _IMPORT_SNIPPET % {"roots": repr(sorted(FORBIDDEN_MODULE_ROOTS))}
        code, out, err = _run_in_venv(venv, snippet, target_root)
        if code != 0:
            violations.append(
                _gatekit.Violation(
                    entry="隔离环境 · import freegraph",
                    rule="G22-02",
                    detail=f"子进程失败（退出码 {code}）：{err.strip()[:400]}",
                    fix="修好隔离环境的探针脚本",
                )
            )
        else:
            loaded = json.loads(out.strip().splitlines()[-1])
            if loaded:
                violations.append(
                    _gatekit.Violation(
                        entry="、".join(loaded),
                        rule="G22-02",
                        detail="import freegraph 后 sys.modules 出现了 langchain 家族",
                        fix=(
                            "移除该 import——freegraph MUST NOT 引入 langchain 家族"
                            "（宪法原则 II · FR-005 ②）"
                        ),
                    )
                )
            else:
                print(f"[{GATE_ID}] import freegraph 后 sys.modules 无 langchain 家族")
        # 场景 ② —— 验收环境（脚本自带的 langchain 系）
        code, out, err = _uv(
            "pip",
            "install",
            "--python",
            str(venv),
            "langchain-core",
            cwd=target_root,
        )
        if code != 0:
            violations.append(
                _gatekit.Violation(
                    entry="uv pip install langchain-core",
                    rule="G22-03",
                    detail=f"场景 ② 的验收环境构造失败（退出码 {code}）：{err.strip()[:400]}",
                    fix="确认网络可用（本门禁需联网安装 langchain-core）",
                )
            )
            return violations
        snippet = _REQUIRES_SNIPPET
        code, out, err = _run_in_venv(venv, snippet, target_root)
        if code != 0:
            violations.append(
                _gatekit.Violation(
                    entry="验收环境 · Requires-Dist",
                    rule="G22-03",
                    detail=f"子进程失败（退出码 {code}）：{err.strip()[:400]}",
                    fix="修好隔离环境的探针脚本",
                )
            )
        else:
            requires = json.loads(out.strip().splitlines()[-1])
            for spec in requires:
                name = _gatekit.requirement_name(spec).lower()
                if (
                    name.startswith("langchain")
                    or name.startswith("langgraph")
                    or name.startswith("langsmith")
                ):
                    violations.append(
                        _gatekit.Violation(
                            entry=name,
                            rule="G22-03",
                            detail=f"已安装的 freegraph 声明了 langchain 家族：{spec}",
                            fix="移除该声明（宪法原则 II · FR-005 ③①）",
                        )
                    )
        snippet = _IMPORT_SNIPPET % {"roots": repr(sorted(FORBIDDEN_MODULE_ROOTS))}
        code, out, err = _run_in_venv(venv, snippet, target_root)
        if code != 0:
            violations.append(
                _gatekit.Violation(
                    entry="验收环境 · import freegraph",
                    rule="G22-02",
                    detail=f"子进程失败（退出码 {code}）：{err.strip()[:400]}",
                    fix="修好隔离环境的探针脚本",
                )
            )
        else:
            loaded = json.loads(out.strip().splitlines()[-1])
            if loaded:
                violations.append(
                    _gatekit.Violation(
                        entry="、".join(loaded),
                        rule="G22-02",
                        detail=(
                            "验收环境（langchain-core 已在场）里 import freegraph 后 "
                            "sys.modules 仍出现了 langchain 家族"
                        ),
                        fix=(
                            "移除该 import——运行环境里有 ≠ 被 freegraph 引入"
                            "（FR-005 ③① · 裁定 22）"
                        ),
                    )
                )
            else:
                print(
                    f"[{GATE_ID}] 验收环境（langchain-core 已在场）里 "
                    f"import freegraph / freegraph.graph 后 sys.modules 仍无 langchain 家族"
                )
        snippet = _EGRESS_SNIPPET % {"gates": json.dumps(str(GATES_DIR))}
        code, out, err = _run_in_venv(venv, snippet, target_root)
        if code != 0:
            violations.append(
                _gatekit.Violation(
                    entry="验收环境 · 零出站",
                    rule="G22-04",
                    detail=f"子进程失败（退出码 {code}）：{err.strip()[:400]}",
                    fix="修好隔离环境的探针脚本",
                )
            )
        else:
            report = json.loads(out.strip().splitlines()[-1])
            if report["framework_egress"]:
                violations.append(
                    _gatekit.Violation(
                        entry="、".join(report["targets"]) or "（未知目标）",
                        rule="G22-04",
                        detail=(
                            f"验收环境里出现了 {report['framework_egress']} 次"
                            "**框架出站**"
                        ),
                        fix="移除该出站（宪法原则 I · 零出站）",
                    )
                )
            else:
                print(
                    f"[{GATE_ID}] 验收环境里的框架出站 = 0"
                    f"（用户出站 = {report['user_egress']}，记录在案不判失败）"
                )
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"门禁 {GATE_ID} · {RULE_TEXT}")
    parser.add_argument(
        "--target-root",
        default=str(REPO_ROOT),
        help="被检的源码根（隔离 venv 里 uv pip install 的目标；默认：仓库根）",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="被检的依赖声明文件（默认：<target-root>/pyproject.toml）",
    )
    args = parser.parse_args(argv)
    target_root = Path(args.target_root)
    project = Path(args.project) if args.project else target_root / "pyproject.toml"
    return _gatekit.run_gate(
        lambda: _gatekit.report(
            evaluate(target_root, project), GATE_ID, RULE_TEXT
        ),
        GATE_ID,
        RULE_TEXT,
    )


if __name__ == "__main__":
    raise SystemExit(main())
