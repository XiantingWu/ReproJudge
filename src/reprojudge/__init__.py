"""ReproJudge public package API."""

from .evidence import source_fingerprint, task_fingerprint
from .runner import BenchmarkResult, run_task
from .schema import BenchmarkTask, CheckSpec, parse_task

__version__ = "0.3.0"

__all__ = [
    "BenchmarkResult",
    "BenchmarkTask",
    "CheckSpec",
    "parse_task",
    "run_task",
    "source_fingerprint",
    "task_fingerprint",
]
