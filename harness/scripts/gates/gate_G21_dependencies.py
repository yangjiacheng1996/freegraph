# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""门禁 **G21** · 依赖闭包黑名单（**声明级** · 含全部 extras 变体）。

判据（`specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` G21）：

1. 从 ``pyproject.toml`` 读出 freegraph 的**全部** ``Requires-Dist`` 声明；
2. 按 **freegraph 自身的 extras 变体**逐一枚举（基础 + 每个 extra 单独 +
   全部同时 ⇒ **6 个**），对每种变体求值 marker；
3. 对每个依赖**递归展开其基础依赖**（传递依赖按**基础依赖**展开，
   **不**展开它们自己的 extras —— dependency-gate.md §2.3）；
4. 断言闭包中**无**任何包命中黑名单。

**黑名单**（三族 + 全部 provider 包 + 点名名单 + ``deepagents`` —— 与
dependency-gate.md §5 **逐行一致**）：``langsmith`` 精确名 + ``langsmith-*`` ·
前缀 ``langchain`` · 前缀 ``langgraph`` · 前缀 ``langchain-``（provider 包）·
点名名单 ``langgraph-api`` / ``langgraph-runtime-inmem`` / ``phoenix``（ELv2）·
``deepagents``。

**未安装的依赖 ⇒ 显式报「未安装 ⇒ 无法取证」并判失败**（指名该包），
**MUST NOT** 静默跳过 —— 静默跳过会把「闭包只到第一层」伪装成「闭包干净」。

**CLI 契约**（architecture-gates.md §2.1）：

* ``--project <pyproject 路径>`` —— 被检的依赖声明文件（默认仓库根）；
* ``--self-test-negative`` —— **内置负向验证**：在隔离副本注入
  ``langchain-core`` ⇒ 断言门禁**必须失败** ⇒ **自检通过 ⇒ 退出码 0**
  （自检失败 ⇒ 退出码非 0）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _gatekit  # noqa: E402 —— 共享判定库（同一目录 ⇒ 必然可导入）

GATE_ID = "G21"
RULE_TEXT = "依赖闭包黑名单（声明级 · 含全部 extras 变体）"

REPO_ROOT = Path(__file__).resolve().parents[3]

#: 黑名单的**六条规则**（族 · 匹配规则 · 全部 provider 包 · 点名名单 · deepagents）。
#:
#: 与 dependency-gate.md §5 与 architecture-gates.md G21 的黑名单表**逐行一致**
#: ⇒ 冻结契约 MUST NOT 比红线少一条。
RULES: tuple[tuple[str, str, str], ...] = (
    (
        "G21-05",
        "点名名单（ELv2 组件 · 宪法原则 IX）",
        "移除该依赖（ELv2 明文禁止以托管服务形式提供）"
        "——MUST NOT 引入 langgraph-api / langgraph-runtime-inmem / phoenix",
    ),
    (
        "G21-06",
        "deepagents（宪法包层黑名单明列项）",
        "移除该依赖——MUST NOT 引入 deepagents（宪法原则 IX 与立项书 §5.5）",
    ),
    (
        "G21-01",
        "langsmith 族（精确名 + langsmith-*）",
        "移除该依赖——freegraph MUST NOT 依赖 LangSmith（宪法原则 I）",
    ),
    (
        "G21-04",
        "全部 provider 包（前缀 langchain-）",
        "移除该依赖——provider 包会把 langchain-core 拉回来（宪法原则 II）",
    ),
    (
        "G21-02",
        "langchain 族（前缀 langchain）",
        "移除该依赖——freegraph 内核 MUST NOT 依赖 LangChain（宪法原则 II）",
    ),
    (
        "G21-03",
        "langgraph 族（前缀 langgraph）",
        "移除该依赖——freegraph MUST NOT 依赖 LangGraph 全系列（宪法原则 II）",
    ),
)


def blacklist_rule(package: str) -> tuple[str, str, str] | None:
    """返回该包命中的**规则**（编号 / 说明 / 修复指引）；未命中 ⇒ ``None``。"""
    name = _gatekit.normalize_package_name(package)
    if name in {"langgraph-api", "langgraph-runtime-inmem", "phoenix"}:
        return RULES[0]
    if name == "deepagents":
        return RULES[1]
    if name == "langsmith" or name.startswith("langsmith-"):
        return RULES[2]
    if name.startswith("langchain-"):
        return RULES[3]
    if name.startswith("langchain"):
        return RULES[4]
    if name.startswith("langgraph"):
        return RULES[5]
    return None


def evaluate(project: Path) -> list[_gatekit.Violation]:
    """判定被检项目的依赖闭包黑名单 ⇒ 违规清单（空 = 合规）。"""
    violations: list[_gatekit.Violation] = []
    variants = _gatekit.enumerate_variants(project)
    missing_variants: dict[str, list[str]] = {}
    hit_variants: dict[str, list[str]] = {}
    hit_rule: dict[str, tuple[str, str, str]] = {}
    for variant in variants:
        result = _gatekit.closure(variant, project)
        for missing in sorted(result.missing):
            missing_variants.setdefault(missing, []).append(variant.name)
        for package in sorted(result.packages):
            rule = blacklist_rule(package)
            if rule is None:
                continue
            hit_variants.setdefault(package, []).append(variant.name)
            hit_rule.setdefault(package, rule)
    for package, names in sorted(missing_variants.items()):
        violations.append(
            _gatekit.Violation(
                entry=package,
                rule="G21-07",
                detail=(
                    f"未安装 ⇒ 无法取证（出现在变体：{'、'.join(names)}）"
                    "——递归展开 MUST 走到闭包末端"
                ),
                fix=(
                    "先安装该传递依赖再跑本门禁"
                    "（CI：uv pip install --python .venv -e \".[pydantic,checkpoint,otel,png]\"）"
                ),
            )
        )
    for package, names in sorted(hit_variants.items()):
        rule = hit_rule[package]
        violations.append(
            _gatekit.Violation(
                entry=package,
                rule=rule[0],
                detail=(
                    f"命中规则：{rule[1]}"
                    f"（出现在变体：{'、'.join(names)}）"
                ),
                fix=rule[2],
            )
        )
    return violations


def _inject_dependency(project: Path, requirement: str) -> None:
    """往被检 ``pyproject.toml`` 的**基础依赖**里注入一条声明（负向验证用）。"""
    text = project.read_text(encoding="utf-8")
    marker = "dependencies = []"
    if marker not in text:
        raise SystemExit(f"{project} 的 dependencies 段形态与预期不符（负向验证中止）")
    project.write_text(
        text.replace(marker, f'dependencies = ["{requirement}"]', 1),
        encoding="utf-8",
    )


def self_test_negative(repo_root: Path) -> int:
    """**内置负向验证** —— 注入 ``langchain-core`` ⇒ 断言门禁**必须失败**。

    **退出码语义**：**自检通过 ⇒ 0**（其内部断言的是「门禁**必须**失败」）；
    **自检失败 ⇒ 非 0** ⇒ 该模式可安全地作为 CI 的一步。
    """
    with tempfile.TemporaryDirectory(prefix="freegraph-g21-selftest-") as tmp:
        copy = _gatekit.make_isolated_copy(repo_root, dest=Path(tmp))
        project = copy / "pyproject.toml"
        _inject_dependency(project, "langchain-core>=0.3")
        violations = evaluate(project)
        if not violations:
            print(
                f"[{GATE_ID}] 自检失败 —— 注入 langchain-core 后门禁仍通过"
                "（判据失效）"
            )
            return 1
        entries = {violation.entry for violation in violations}
        if "langchain-core" not in entries:
            print(
                f"[{GATE_ID}] 自检失败 —— 违规清单未点名 langchain-core："
                f"{sorted(entries)}"
            )
            return 1
        incomplete = [
            violation.entry
            for violation in violations
            if not violation.rule or not violation.fix
        ]
        if incomplete:
            print(
                f"[{GATE_ID}] 自检失败 —— 以下违规缺「规则编号」或「修复指引」："
                f"{incomplete}"
            )
            return 1
        print(
            f"[{GATE_ID}] 自检通过 —— 注入 langchain-core 后门禁**失败**并点名："
        )
        for violation in violations:
            print(f"  违规条目: {violation.entry}")
            print(f"  规则编号: {violation.rule}")
            print(f"  细节    : {violation.detail}")
            print(f"  修复指引: {violation.fix}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"门禁 {GATE_ID} · {RULE_TEXT}")
    parser.add_argument(
        "--project",
        default=str(REPO_ROOT / "pyproject.toml"),
        help="被检的依赖声明文件（默认：仓库根的 pyproject.toml）",
    )
    parser.add_argument(
        "--self-test-negative",
        action="store_true",
        help="内置负向验证（注入 langchain-core ⇒ 断言门禁必须失败）",
    )
    args = parser.parse_args(argv)
    if args.self_test_negative:
        return _gatekit.run_gate(
            lambda: self_test_negative(REPO_ROOT), GATE_ID, "内置负向验证"
        )
    violations = evaluate(Path(args.project))
    return _gatekit.report(violations, GATE_ID, RULE_TEXT)


if __name__ == "__main__":
    raise SystemExit(main())
