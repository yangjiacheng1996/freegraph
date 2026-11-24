# Copyright (c) 2026 杨家成 · MIT License · https://github.com/yangjiacheng1996/freegraph

"""B19F1 · US2：L5 惰性 / 导出位置 / trace_run_scope 内部性。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _python(src_dir: Path, code: str) -> str:
    env = {**os.environ, "PYTHONPATH": str(src_dir)}
    env.pop("LANGSMITH_TRACING", None)
    proc = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def test_import_freegraph_is_lazy_and_exports_are_in_l5_only(src_dir: Path) -> None:
    output = _python(
        src_dir,
        """
import sys
import freegraph
loaded = sorted(name for name in sys.modules if name.startswith('freegraph.'))
assert loaded == [], loaded
import freegraph.graph as graph
assert 'current_span' not in graph.__all__
import freegraph.observability as observability
assert 'current_span' in observability.__all__
assert 'TraceRecord' in observability.__all__
assert 'FileTraceStore' in observability.__all__
assert 'SqliteTraceStore' in observability.__all__
assert 'OtlpExporter' in observability.__all__
assert 'trace_run_scope' not in observability.__all__
assert 'SqliteTraceStore' not in graph.__all__
print('ok')
""",
    )
    assert output.strip() == "ok"
