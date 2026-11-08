# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""门禁 **G23** · 许可证白名单（4 级证据链 · 5 个精确 SPDX id）。

判据（`specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` G23）：

1. **被检查的包集合 =（依赖闭包中的包）∪（取证作用域根下扫到的
   ``*.dist-info`` / ``*.egg-info`` 所对应的包）** —— **并集口径**
   （spec 裁定 25）：只判闭包 ⇒ 反向用例**空转**；只判作用域根 ⇒
   **空门禁 ⇒ 违宪** ⇒ **两者皆不可接受**；
2. **许可证据先**取作用域根下的元数据、**后**回落**已安装**元数据；
3. 四级有序证据链取标识 ⇒ SPDX 表达式**逐叶子**判定 ⇒ **每个叶子**都须
   ∈ {MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, PSF-2.0}；
4. **取不到许可证明 ⇒ 失败并指名**（FR-006 ② · **MUST NOT** skip）；
5. 命中禁用清单（Elastic-2.0 / AGPL / SSPL / BUSL / GPL-2 / GPL-3 / MPL-2.0 /
   LGPL）⇒ 失败并**点名**；ELv2 点名名单 ⇒ 即使许可证合规也**必须**被拒。

**边界**（裁定 18）：MUST **不**引入等价标识符对照表 / 家族判定 / 豁免入口；
MUST **不**使用「子串包含」判定（``"MIT" in upper`` 会放行 ``MIT-CMU``）。

**CLI 契约**（architecture-gates.md §2.1）：``--root <路径>`` —— **被检**的
环境根（**许可证据的取证作用域**；默认仓库根）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _gatekit  # noqa: E402 —— 共享判定库（同一目录 ⇒ 必然可导入）

GATE_ID = "G23"
RULE_TEXT = "许可证白名单（4 级证据链 · 5 个精确 SPDX id）"

REPO_ROOT = Path(__file__).resolve().parents[3]

#: ELv2 点名名单（dependency-gate.md §4.5）—— 即使许可证合规也**必须**被拒。
ELV2_NAMED = ("langgraph-api", "langgraph-runtime-inmem", "phoenix")


def _root_packages(root: Path) -> dict[str, Path]:
    """扫取证作用域根下的 ``*.dist-info`` / ``*.egg-info`` ⇒ ``{包名: 目录}``。"""
    found: dict[str, Path] = {}
    if not root.is_dir():
        return found
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
        package, _version = _gatekit.split_name_version(stem)
        found[_gatekit.normalize_package_name(package)] = child
    return found


def checked_packages(root: Path, project: Path | None = None) -> list[str]:
    """**被检查的包集合**（并集口径 · spec 裁定 25）。

    =（**依赖声明文件**里的依赖闭包）∪（取证作用域根下扫到的
    ``*.dist-info`` / ``*.egg-info`` 所对应的包）。
    """
    project = project if project is not None else root / "pyproject.toml"
    packages: set[str] = set()
    if project.is_file():
        for variant in _gatekit.enumerate_variants(project):
            packages |= _gatekit.closure(variant, project).packages
    packages |= set(_root_packages(root))
    return sorted(packages)


def evaluate(root: Path, project: Path | None = None) -> list[_gatekit.Violation]:
    """判定被检根下的许可证合规性 ⇒ 违规清单（空 = 合规）。"""
    violations: list[_gatekit.Violation] = []
    packages = checked_packages(root, project)
    for package in packages:
        if package in ELV2_NAMED:
            violations.append(
                _gatekit.Violation(
                    entry=package,
                    rule="G23-05",
                    detail="ELv2 点名名单（宪法原则 IX 的 Elastic-2.0 组件禁令）",
                    fix=(
                        "移除该依赖——ELv2 明文禁止以托管服务形式提供"
                        "（恰好否掉 freegraph 最可能的商业模式）"
                    ),
                )
            )
            continue
        evidence = _gatekit.license_evidence(package, root=root)
        if evidence is None:
            violations.append(
                _gatekit.Violation(
                    entry=package,
                    rule="G23-01",
                    detail="四级证据链全无 ⇒ 取不到许可证明",
                    fix=(
                        "换用能提供许可证明的包"
                        "（PEP 639 的 License-Expression / License 字段 / License :: 分类器 / "
                        "dist-info/licenses/ 授权文件）——MUST NOT 放宽白名单（FR-018）"
                    ),
                )
            )
            continue
        source, identifier = evidence
        try:
            leaves = _gatekit.spdx_leaves(identifier)
        except _gatekit.SpdxParseError as exc:
            violations.append(
                _gatekit.Violation(
                    entry=package,
                    rule="G23-02",
                    detail=f"{source}：{identifier!r} —— 无法解析为 SPDX 表达式（{exc}）",
                    fix=(
                        "换用带 SPDX 标识符的包——散文式标识无法归一为 SPDX id"
                        "⇒ 判失败；MUST NOT 引入等价标识符对照表（裁定 18）"
                    ),
                )
            )
            continue
        for leaf in sorted(leaves):
            if leaf in _gatekit.LICENSE_WHITELIST:
                continue
            family = _forbidden_family(leaf)
            violations.append(
                _gatekit.Violation(
                    entry=package,
                    rule="G23-04" if family else "G23-03",
                    detail=(
                        f"{source}：SPDX 叶子 {leaf!r} 不在白名单内"
                        + (f"（禁用清单：{family}）" if family else "")
                    ),
                    fix=(
                        "换用许可证落在白名单内的包"
                        "——白名单的扩充只能走宪法修订（裁定 18 · FR-018）"
                    ),
                )
            )
    return violations


def _forbidden_family(leaf: str) -> str | None:
    """若该 SPDX 叶子落在**禁用清单**（传染性 / 限制性）内 ⇒ 返回族名。

    **只用于点名诊断** —— 判定落点在**白名单比对**（逐叶子 · 精确 id）⇒
    本函数**不参与放行决策**，也**不靠前缀猜测**放行任何标识符（裁定 18）。
    """
    for family in _gatekit.FORBIDDEN_LICENSE_FAMILIES:
        if leaf == family or leaf.startswith(family + "-"):
            return family
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"门禁 {GATE_ID} · {RULE_TEXT}")
    parser.add_argument(
        "--root",
        default=str(REPO_ROOT),
        help="被检的环境根（许可证据的取证作用域；默认：仓库根）",
    )
    parser.add_argument(
        "--project",
        default=None,
        help=(
            "被检的**依赖声明文件**（被检查包集合的闭包来源；"
            "默认：<root>/pyproject.toml）。"
            "v1.0 的发行元数据零依赖（宪法 v1.7.0）⇒ 门禁改对 **v2.0 清单**取证："
            "specs/b3f1-scaffold-ci-gates/contracts/extras-v2.toml"
        ),
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    project = Path(args.project) if args.project else root / "pyproject.toml"
    violations = evaluate(root, project)
    packages = checked_packages(root, project)
    print(
        f"[{GATE_ID}] 被检查的包数 = {len(packages)}"
        f"（并集口径：闭包包集 ∪ 取证作用域根下扫到的 dist-info）"
    )
    return _gatekit.report(violations, GATE_ID, RULE_TEXT)


if __name__ == "__main__":
    raise SystemExit(main())
