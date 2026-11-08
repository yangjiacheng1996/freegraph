# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph
"""门禁 **G25** · 导入图单向（ARCH-1 · 层注册表驱动）。

判据（`specs/b3f1-scaffold-ci-gates/contracts/architecture-gates.md` G25）：

1. 层的归属由 `contracts/layer-registry.md`（**唯一权威** · 机器可读）解析
   —— MUST NOT 靠路径前缀猜测（FR-008 ②）；
2. 扫描域 = ``src/freegraph/**`` ∪ 层注册表中声明的**全部跨层单元路径**
   （跨层单元自身的 import 方向**同样受检**）；
3. **允许方向**：层编号递增（高层可 import 低层）；**反向 import 违规**；
   **同层 import 仅 L1 与 L6 允许，L2–L5 之间禁止横向依赖**；
4. **跨层单元**只能 import **L1 与更低层**，且 MUST NOT 被 **L2–L5** import
   （**L6 除外** —— L6 经由公开 API 门面使用内核 ⇒ L6 → 门面是正确方向）；
   **同一跨层单元内部**的模块互相 import ⇒ **不产生层边 ⇒ 不构成违规**；
5. **公开 API 门面**是 ARCH-1 的**唯一既有例外**（由层注册表显式声明，
   MUST NOT 硬编码在门禁实现里）；
6. **本门禁 NOT 重复判的两条**（注册表 §0.3）：**L-2**（契约层内部零内部层
   import ⇒ 既有 G2 承担）；**L-1**（顶层包 MUST NOT import 任何内部层
   ⇒ **G25 判**，优先于「L1 与 L6 允许同层 import」）。

**CLI 契约**（architecture-gates.md §2.1）：``--root <路径>``（被检的树根）·
``--registry <路径>``（被检的层注册表；**只读** —— MUST NOT 改动冻结面）。

**签名头**（宪法原则 X）：本文件带署名头且模块 docstring 是首个语句。
"""

from __future__ import annotations

import argparse
import sys
from fnmatch import fnmatch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _gatekit  # noqa: E402 —— 共享判定库（同一目录 ⇒ 必然可导入）

GATE_ID = "G25"
RULE_TEXT = "导入图单向（ARCH-1 · 层注册表驱动）"

REPO_ROOT = Path(__file__).resolve().parents[3]


def _layer_number(layer: str) -> int:
    """``L3`` ⇒ ``3``；跨层单元（``—``）⇒ ``0``。"""
    if layer.startswith("L") and layer[1:].isdigit():
        return int(layer[1:])
    return 0


def allow(
    source: _gatekit.LayerEntry, target: _gatekit.LayerEntry
) -> tuple[bool, str]:
    """层间方向判定 ⇒ ``(是否合规, 违规说明)``。

    真值表与 spec FR-008 · `layer-registry.md` §0.2 规则 2 ·
    `architecture-gates.md` G25 第 3 条 · `data-model.md` §5.2 **四处口径一致**。
    """
    if source.path == target.path:
        return True, ""
    if source.is_cross_layer and target.is_cross_layer:
        return False, (
            f"跨层单元 {source.path} 不得 import 另一个跨层单元 {target.path}"
            "（跨层单元只能 import L1 与更低层）"
        )
    if source.is_cross_layer:
        if source.exception == "facade-L1-L3":
            if target.layer in {"L1", "L2", "L3"}:
                return True, ""
            return False, (
                f"公开 API 门面（facade-L1-L3 例外）不得 import {target.layer}"
                "（仍不得 import L4 / L5）"
            )
        if target.layer == "L1":
            return True, ""
        return False, (
            f"跨层单元 {source.path} 只能 import L1 与更低层（目标 {target.layer}）"
        )
    if target.is_cross_layer:
        if target.path.startswith("src/"):
            if source.layer == "L6":
                return True, ""
            return False, (
                f"{source.layer} 不得 import 公开 API 门面"
                "（L6 → 门面才是正确方向）"
            )
        return False, (
            f"{source.layer} 不得 import 构建期 / 发行期跨层单元 {target.path}"
            "（它不属运行时依赖图）"
        )
    source_number = _layer_number(source.layer)
    target_number = _layer_number(target.layer)
    if source_number == target_number:
        if source.layer in {"L1", "L6"}:
            return True, ""
        return False, (
            f"{source.layer} 之间的同层横向依赖被禁止"
            "（立项书 §5.1 依赖方向铁律第 3 条：L2–L5 之间禁止横向依赖）"
        )
    if source_number > target_number:
        return True, ""
    return False, f"反向 import（{source.layer} → {target.layer}）"


def _declaration_forbids(
    registry: _gatekit.LayerRegistry, rel_path: str
) -> _gatekit.Declaration | None:
    """找出对某个模块生效的「**MUST NOT import 任何内部层**」声明（如 **L-1**）。"""
    for declaration in registry.declarations:
        if not declaration.judged_by_gate25:
            continue
        if not declaration.forbids_internal_import:
            continue
        for pattern in declaration.paths:
            if rel_path == pattern or fnmatch(rel_path, pattern):
                return declaration
    return None


def scan_modules(root: Path, registry: _gatekit.LayerRegistry) -> list[Path]:
    """G25 的**扫描域** —— ``src/freegraph/**`` ∪ 注册表声明的跨层单元路径。"""
    modules: list[Path] = list(_gatekit.iter_python_files(root / "src" / "freegraph"))
    for cross_layer_path in registry.cross_layer_paths:
        modules.extend(_gatekit.iter_python_files(root / cross_layer_path))
    return sorted(set(modules))


def evaluate(root: Path, registry_path: Path) -> list[_gatekit.Violation]:
    """判定被检树的导入方向 ⇒ 违规清单（空 = 合规）。"""
    violations: list[_gatekit.Violation] = []
    registry = _load_registry(registry_path)
    for path in scan_modules(root, registry):
        rel = _gatekit.relative_to_root(path, root)
        entry = registry.match(rel)
        if entry is None:
            violations.append(
                _gatekit.Violation(
                    entry=rel,
                    rule="G25-05",
                    detail="该模块未在层注册表中登记（层归属 MUST NOT 靠路径前缀猜测）",
                    fix=(
                        f"在 {registry_path} 的条目表中登记该路径的层归属"
                        "（新增一层 / 新增跨层单元 ⇒ 只改注册表，门禁实现零改动）"
                    ),
                )
            )
            continue
        declaration = _declaration_forbids(registry, rel)
        for edge in _gatekit.scan_imports(path):
            target_path = _gatekit.resolve_internal_module(
                root, registry, rel, edge
            )
            if target_path is None:
                continue
            target_rel = _gatekit.relative_to_root(target_path, root)
            target_entry = registry.match(target_rel)
            if target_entry is None:
                continue
            if declaration is not None:
                violations.append(
                    _gatekit.Violation(
                        entry=f"{rel}:{edge.lineno}",
                        rule="G25-06",
                        detail=(
                            f"{declaration.ident}：{declaration.text[:120]}"
                            f"（目标 {target_rel}）"
                        ),
                        fix=(
                            "移除该 import——顶层包 MUST 保持**惰性空壳**"
                            "（只暴露 __version__；ARCH-2 · D1 决议附加约束）"
                        ),
                    )
                )
                continue
            compliant, reason = allow(entry, target_entry)
            if compliant:
                continue
            violations.append(
                _gatekit.Violation(
                    entry=f"{rel}:{edge.lineno}",
                    rule="G25-01",
                    detail=f"{reason}（{entry.layer} → {target_entry.layer} · {target_rel}）",
                    fix=(
                        "把实现下沉到低层；或改层注册表（走评审）"
                        "——MUST NOT 引入豁免机制（FR-018）"
                    ),
                )
            )
    return violations


def _load_registry(registry_path: Path) -> _gatekit.LayerRegistry:
    """按**指定路径**读层注册表（默认路径 = 仓库内的冻结面）。"""
    return _gatekit.load_layer_registry(registry_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"门禁 {GATE_ID} · {RULE_TEXT}")
    parser.add_argument(
        "--root",
        default=str(REPO_ROOT),
        help="被检的树根（默认：仓库根）",
    )
    parser.add_argument(
        "--registry",
        default=str(REPO_ROOT / _gatekit.DEFAULT_REGISTRY_RELPATH),
        help="被检的层注册表（只读；默认：仓库内的冻结面）",
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    registry_path = Path(args.registry)
    violations = evaluate(root, registry_path)
    registry = _load_registry(registry_path)
    print(
        f"[{GATE_ID}] 扫描域 = src/freegraph/** + 注册表声明的跨层单元 "
        f"{list(registry.cross_layer_paths)}"
    )
    return _gatekit.report(violations, GATE_ID, RULE_TEXT)


if __name__ == "__main__":
    raise SystemExit(main())
