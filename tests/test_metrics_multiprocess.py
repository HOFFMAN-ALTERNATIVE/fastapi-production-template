"""Multiprocess metrics: samples from separate worker processes are merged on scrape.

Each step runs in its own interpreter, because prometheus_client picks its value
storage when it is imported, based on PROMETHEUS_MULTIPROC_DIR.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

WORKER = """
import os
from app.core.metrics import REQUESTS, mark_worker_dead
REQUESTS.labels("GET", "/health/live", "200").inc({n})
mark_worker_dead()
print(os.getpid())
"""

SCRAPE = """
from app.core.metrics import metrics_endpoint
print(metrics_endpoint().body.decode())
"""


def _run(code: str, mp_dir: Path) -> str:
    env = {**os.environ, "PROMETHEUS_MULTIPROC_DIR": str(mp_dir)}
    root = Path(__file__).resolve().parents[1]
    out = subprocess.run(  # noqa: S603 - fixed argv: this interpreter and a test-owned snippet
        [sys.executable, "-c", code], env=env, cwd=root, capture_output=True, text=True, check=True
    )
    return out.stdout


def test_scrape_merges_counters_from_all_workers(tmp_path: Path) -> None:
    pids = {_run(WORKER.format(n=n), tmp_path).strip() for n in (3, 4)}
    assert len(pids) == 2, "the two workers must be different processes"
    assert len(list(tmp_path.glob("counter_*.db"))) == 2

    body = _run(SCRAPE, tmp_path)
    lines = body.splitlines()
    line = next(ln for ln in lines if ln.startswith("http_requests_total{") and "/live" in ln)
    assert float(line.rsplit(" ", 1)[1]) == 7.0


def test_without_multiproc_dir_the_default_registry_is_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import metrics

    monkeypatch.delenv("PROMETHEUS_MULTIPROC_DIR", raising=False)
    assert metrics.multiprocess_dir() is None
    metrics.mark_worker_dead()  # no-op, must not fail
    assert b"http_requests_total" in metrics.metrics_endpoint().body
