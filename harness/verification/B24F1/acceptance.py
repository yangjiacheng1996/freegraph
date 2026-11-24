#!/usr/bin/env python3
# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B24F1 · 一键验收（打包分发 + 兼容矩阵 + THIRD_PARTY_NOTICES）。

A1 发行包就绪 · A2 兼容矩阵与归属清单齐备 · A3 纯度门禁通过；
并运行 US1–US5 的子检查。退出码：0 = PASS · 1 = FAIL · 2 = 环境未就绪。
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

_FAILURES: list[str] = []
_CHECKS = 0
_RECORD: list[str] = []
_ENV_NOT_READY = False

_FORBIDDEN_OTLP = {
    "certifi",
    "requests",
    "opentelemetry-exporter-otlp",
    "opentelemetry-exporter-otlp-proto-http",
}
_ABS_COMPAT = "https://github.com/yangjiacheng1996/freegraph/blob/main/COMPAT.md"


def check(condition: object, label: str) -> bool:
    global _CHECKS
    _CHECKS += 1
    state = "PASS" if condition else "FAIL"
    line = f"[{state}] {label}"
    print(line)
    _RECORD.append(line)
    if not condition:
        _FAILURES.append(label)
    return bool(condition)


def _run(cmd: list[str], *, cwd: Path = REPO_ROOT, env: dict | None = None, timeout: int = 300):
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    _RECORD.append(f"$ {' '.join(cmd)}")
    if proc.stdout.strip():
        _RECORD.append(proc.stdout.strip())
    if proc.stderr.strip():
        _RECORD.append(proc.stderr.strip())
    return proc


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _make_venv(path: Path) -> Path | None:
    import venv

    try:
        venv.EnvBuilder(with_pip=True, clear=True).create(path)
        return _venv_python(path)
    except Exception as exc:  # noqa: BLE001
        print(f"[ENV] 无法创建隔离 venv：{exc}")
        return None


def _read_project() -> dict:
    return tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def _a1_metadata() -> None:
    project = _read_project()
    check(project["requires-python"] == ">=3.11", "A1 requires-python >= 3.11")
    check(project["dependencies"] == [], "A1 基础依赖为空")
    extras = set(project.get("optional-dependencies", {}))
    check(extras == {"otlp"}, "A1 唯一 extra = [otlp]")
    check("pydantic" not in extras and "checkpoint" not in extras and "otel" not in extras and "png" not in extras, "A1 无 v2 extras")
    check((REPO_ROOT / "src" / "freegraph" / "py.typed").is_file(), "A1 py.typed 存在")
    check(project.get("license") == "MIT", "A1 LICENSE = MIT")


def _a2_compat_and_notices() -> None:
    compat = REPO_ROOT / "COMPAT.md"
    check(compat.is_file(), "A2 COMPAT.md 存在")
    if not compat.is_file():
        return
    text = compat.read_text(encoding="utf-8")
    check("不构成 affiliation" in text, "A2 affiliation 声明")
    rows = _compat_rows(text)
    check(len(rows) == 27, "A2 机读段 27 行")
    check(rows.get("Command", [None, None, None])[2] == "部分等价", "A2 Command = 部分等价")
    items = _section_rows(text, "## 18 项覆盖表")
    check(len(items) == 18, "A2 18 项覆盖表齐备")
    downstream = _section(text, "## 下游承接行")
    for needle in ("MemorySaver", "InMemorySaver", "CheckpointTuple", "SqliteSaver", "CompiledGraph.get_state", "CompiledGraph.get_state_history", "CompiledGraph.update_state", "时间旅行", "OtlpExporter"):
        check(needle in downstream, f"A2 下游行：{needle}")
    notices = (REPO_ROOT / "THIRD_PARTY_NOTICES").read_text(encoding="utf-8")
    check("langgraph-checkpoint-sqlite" in notices and "LangChain, Inc." in notices, "A2 NOTICES §1")
    check("protobuf" in notices and "BSD-3-Clause" in notices, "A2 NOTICES protobuf 归一")


def _compat_rows(text: str) -> dict[str, list[str]]:
    section = _section(text, "## API 兼容矩阵")
    rows: dict[str, list[str]] = {}
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", stripped.strip("|"))]
        if cells and re.fullmatch(r"`[A-Za-z_][A-Za-z0-9_]*`", cells[0]):
            rows[cells[0].strip("`")] = cells
    return rows


def _section(text: str, heading: str) -> str:
    match = re.search(rf"^{re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text, re.S | re.M)
    return match.group(1) if match else ""


def _section_rows(text: str, heading: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in _section(text, heading).splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or re.fullmatch(r"\|[\s\-|:]+\|", stripped):
            continue
        cells = [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", stripped.strip("|"))]
        if cells and cells[0] not in {"#", "行", "freegraph 符号"}:
            rows.append(cells)
    return rows


def _build_artifacts(out_dir: Path) -> tuple[int, str]:
    proc = _run(["uv", "build", "--out-dir", str(out_dir)], timeout=300)
    return proc.returncode, proc.stdout + proc.stderr


def _artifact_paths(dist: Path) -> tuple[Path | None, Path | None]:
    wheels = sorted(dist.glob("*.whl"))
    sdists = sorted(dist.glob("*.tar.gz"))
    return (wheels[0] if wheels else None, sdists[0] if sdists else None)


def _a3_purity(dist: Path) -> None:
    script = REPO_ROOT / "harness" / "scripts" / "check_dist_purity.py"
    proc = _run([sys.executable, str(script), str(dist)], timeout=120)
    check(proc.returncode == 0, "A3 纯度正向退出码 0")
    wheel, sdist = _artifact_paths(dist)
    check(wheel is not None and sdist is not None, "A3 wheel + sdist 均存在")
    if wheel is None or sdist is None:
        return
    with zipfile.ZipFile(wheel) as zf:
        names = zf.namelist()
    for forbidden in ("harness/", ".specify/", ".opencode/", "COMPAT.md", "THIRD_PARTY_NOTICES"):
        check(not any(name.startswith(forbidden) or forbidden in name for name in names), f"A3 wheel 不含 {forbidden}")
    with tarfile.open(sdist) as tf:
        members = [m.name for m in tf.getmembers() if m.isfile()]
    stripped = ["/".join(Path(name).parts[1:]) for name in members if len(Path(name).parts) > 1]
    for forbidden in ("harness/", ".specify/", ".opencode/", "COMPAT.md", "THIRD_PARTY_NOTICES"):
        check(not any(name.startswith(forbidden) or forbidden in name for name in stripped), f"A3 sdist 不含 {forbidden}")


def _us1_install(dist: Path) -> None:
    wheel, _ = _artifact_paths(dist)
    if wheel is None:
        check(False, "US1 wheel 缺失")
        return
    with tempfile.TemporaryDirectory(prefix="b24f1-base-") as tmp:
        venv_dir = Path(tmp) / "venv"
        python = _make_venv(venv_dir)
        if python is None:
            _mark_env("US1 隔离 venv 创建失败")
            return
        proc = _run([str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)], timeout=180)
        check(proc.returncode == 0, "US1 基础安装成功")
        import_proc = _run([str(python), "-c", "import freegraph"], timeout=60)
        check(import_proc.returncode == 0, "US1 import freegraph 成功")
        freeze = _run([str(python), "-m", "pip", "freeze"], timeout=60)
        packages = [line for line in freeze.stdout.splitlines() if line.strip()]
        check(all(line.lower().startswith("freegraph") for line in packages), "US1 pip freeze 无第三方运行时依赖")
    with tempfile.TemporaryDirectory(prefix="b24f1-otlp-") as tmp:
        venv_dir = Path(tmp) / "venv"
        python = _make_venv(venv_dir)
        if python is None:
            _mark_env("US1 [otlp] venv 创建失败")
            return
        proc = _run([str(python), "-m", "pip", "install", f"{wheel}[otlp]"], timeout=300)
        if proc.returncode != 0:
            _mark_env("US1 [otlp] 依赖安装不可用（离线 / 网络 / 缓存）")
            _RECORD.append(proc.stdout + proc.stderr)
            return
        check(True, "US1 [otlp] 安装成功")
        freeze = _run([str(python), "-m", "pip", "freeze"], timeout=60)
        names = {
            re.split(r"[=<>!~ ]", line.strip(), 1)[0].lower()
            for line in freeze.stdout.splitlines()
            if line.strip()
        }
        normalized = {re.sub(r"[-_.]+", "-", name) for name in names}
        check(not (normalized & _FORBIDDEN_OTLP), "US1 [otlp] 无禁用包")


def _us2_artifacts(dist: Path) -> None:
    wheel, sdist = _artifact_paths(dist)
    if wheel is None or sdist is None:
        check(False, "US2 产物缺失")
        return
    with zipfile.ZipFile(wheel) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
    check(all(n.startswith("freegraph/") or re.match(r"^freegraph-[^/]+\.dist-info/", n) for n in names), "US2 wheel 根级仅包代码 + dist-info")
    check("freegraph/py.typed" in names, "US2 wheel 含 py.typed")
    with tarfile.open(sdist) as tf:
        members = [m.name for m in tf.getmembers() if m.isfile()]
    stripped = ["/".join(Path(name).parts[1:]) for name in members if len(Path(name).parts) > 1]
    check("pyproject.toml" in stripped, "US2 sdist 含 pyproject.toml")
    check(".gitignore" not in stripped, "US2 sdist 不含 .gitignore")
    check(not any(name.startswith("harness/") or name.startswith(".specify/") for name in stripped), "US2 sdist 无仓库内容")


def _us3_negative(dist: Path) -> None:
    wheel, _ = _artifact_paths(dist)
    if wheel is None:
        check(False, "US3 wheel 缺失")
        return
    before = hashlib.sha256(wheel.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="b24f1-negative-") as tmp:
        temp_dist = Path(tmp)
        poisoned = temp_dist / wheel.name
        shutil.copy2(wheel, poisoned)
        with zipfile.ZipFile(poisoned, "a") as zf:
            zf.writestr("harness/report.md", "leak\n")
        proc = _run([sys.executable, str(REPO_ROOT / "harness" / "scripts" / "check_dist_purity.py"), str(temp_dist)], timeout=120)
        check(proc.returncode != 0, "US3 混入仓库文件 ⇒ 纯度门禁失败")
        check("拒绝发布" in proc.stdout + proc.stderr or "harness/report.md" in proc.stdout + proc.stderr, "US3 负向输出指名违规")
    check(hashlib.sha256(wheel.read_bytes()).hexdigest() == before, "US3 真实产物未被污染")
    workflow = (REPO_ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")
    try:
        order = (workflow.index("- name: Build"), workflow.index("- name: Verify artifact purity"), workflow.index("- name: Publish to PyPI"))
        check(order[0] < order[1] < order[2], "US3 工作流顺序 build → purity → publish")
    except ValueError:
        check(False, "US3 工作流步骤名缺失")


def _us4_compat() -> None:
    if not (REPO_ROOT / "COMPAT.md").is_file():
        check(False, "US4 COMPAT.md 缺失")
        return
    text = (REPO_ROOT / "COMPAT.md").read_text(encoding="utf-8")
    rows = _compat_rows(text)
    check("Command" in rows and rows["Command"][2] == "部分等价", "US4 Command = 部分等价")
    check("Y-01" in rows.get("Command", ["", "", "", ""])[3], "US4 Command 含 Y-01")
    check("X-06" in rows.get("Command", ["", "", "", ""])[3], "US4 Command 含 X-06")
    check("Y-02" in rows.get("CompiledGraph", ["", "", "", ""])[3], "US4 CompiledGraph 含 Y-02")
    check("Y-03" in rows.get("Send", ["", "", "", ""])[3], "US4 Send 含 Y-03")
    evidence = _section(text, "## 证据与来源")
    check("Store" in evidence and "协议等价" in evidence, "US4 Store 澄清在证据与来源")


def _us5_readme() -> None:
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    for outdated in ("内核尚未实现", "没有任何图运行时能力", "请勿用于生产", "请勿当作可用替代品"):
        check(outdated not in text, f"US5 无过时断言：{outdated}")
    check("独立实现、非 LangChain Inc. 产品" in text, "US5 独立实现声明")
    check("零账号" in text and "零出站" in text and "零第三方运行时依赖" in text, "US5 三条承诺")
    check("| 能力 | Developer $0 | Plus $39/seat/月 | Enterprise | freegraph v1 |" in text, "US5 能力表 5 列")
    section = _section(text, "## 能力 → freegraph 处置")
    rows = [line for line in section.splitlines() if line.strip().startswith("|") and not line.strip().startswith("| 能力 ") and not re.fullmatch(r"\|[\s\-|:]+\|", line.strip())]
    check(len(rows) == 8, "US5 能力表 8 行")
    check("2026-11-01" in section, "US5 as-of 日期")
    api = _section(text, "## API 兼容矩阵")
    check(_ABS_COMPAT in api, "US5 COMPAT 绝对链接")
    check(not re.search(r"^\|\s*`[A-Za-z_][A-Za-z0-9_]*`\s*\|", api, re.M), "US5 README 无完整矩阵")
    otlp = _section(text, "## OTLP 导出（B21F1 · 可选 `[otlp]`）")
    check(all(name in otlp for name in ("OpenLIT", "Langfuse", "Phoenix")), "US5 OTLP 三后端")
    check("无默认推荐" in otlp, "US5 OTLP 无默认推荐")
    check(_section(text, "## English") != "", "US5 English 关键段存在")


def _mark_env(reason: str) -> None:
    global _ENV_NOT_READY
    _ENV_NOT_READY = True
    print(f"[ENV] {reason}")
    _RECORD.append(f"[ENV] {reason}")


def _record_section(env: str, steps: str, outputs: str, conclusion: str, open_items: str) -> str:
    return (
        "## 1. 环境\n\n"
        f"{env}\n\n"
        "## 2. 步骤\n\n"
        f"{steps}\n\n"
        "## 3. 实际输出\n\n"
        f"{outputs}\n\n"
        "## 4. 结论\n\n"
        f"{conclusion}\n\n"
        "## 5. 遗留问题\n\n"
        f"{open_items}\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B24F1 acceptance")
    parser.add_argument("--record", type=Path, help="输出五段式记录片段")
    args = parser.parse_args(argv)

    _a1_metadata()
    _a2_compat_and_notices()
    with tempfile.TemporaryDirectory(prefix="b24f1-dist-") as tmp:
        dist = Path(tmp)
        rc, output = _build_artifacts(dist)
        _RECORD.append(output)
        if rc != 0:
            _mark_env("uv build 不可用")
        else:
            _a3_purity(dist)
            _us1_install(dist)
            _us2_artifacts(dist)
            _us3_negative(dist)
    _us4_compat()
    _us5_readme()

    if args.record:
        args.record.write_text(
            _record_section(
                env=f"Linux · Python {sys.version.split()[0]} · 仓库 {REPO_ROOT}",
                steps="python harness/verification/B24F1/acceptance.py",
                outputs="\n".join(_RECORD),
                conclusion="PASS" if not _FAILURES and not _ENV_NOT_READY else "FAIL / ENV_NOT_READY",
                open_items="见 manual-verification.md §5",
            ),
            encoding="utf-8",
        )

    if _ENV_NOT_READY:
        print(f"B24F1 acceptance: ENV_NOT_READY ({_CHECKS} checks)")
        return 2
    if _FAILURES:
        print(f"B24F1 acceptance: FAIL ({len(_FAILURES)} failed / {_CHECKS} checks)")
        return 1
    print(f"B24F1 acceptance: PASS ({_CHECKS} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
