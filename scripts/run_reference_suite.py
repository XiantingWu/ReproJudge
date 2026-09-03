from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from reprojudge import __version__
from reprojudge.evidence import source_fingerprint, task_fingerprint
from reprojudge.reporting import summarize
from reprojudge.runner import run_task
from reprojudge.schema import load_task

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = ROOT / "benchmarks/reference-suite.json"
DEFAULT_OUTPUT = ROOT / ".reprojudge/reference-evidence"
MAX_SUITE_BYTES = 256 * 1024


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_suite(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("reference suite must be a regular file")
    raw = path.read_bytes()
    if len(raw) > MAX_SUITE_BYTES:
        raise ValueError("reference suite exceeds size bound")
    payload = json.loads(
        raw.decode("utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON number: {value}")
        ),
    )
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("reference suite must have schema_version=1")
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= 64:
        raise ValueError("reference suite must contain 1-64 tasks")
    return payload


def _safe_suite_path(value: object) -> Path:
    if not isinstance(value, str) or not value or value.startswith(("/", "\\")):
        raise ValueError("suite task path must be relative")
    candidate = ROOT / value
    resolved = candidate.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError("suite task escapes project root") from exc
    current = ROOT
    for part in Path(value).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("suite task path contains a symlink")
    return candidate


def _measured_source_head() -> str | None:
    # The measured head is the exact source actually checked out. Locally this
    # is the current Git HEAD; a hosted measurement lane may supply
    # REPROJUDGE_HEAD_SHA for the exact head it checked out.
    override = os.environ.get("REPROJUDGE_HEAD_SHA")
    if override:
        return override
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def run_reference_suite(suite_path: Path, output_dir: Path) -> dict:
    suite = _load_suite(suite_path)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    agent = ROOT / "examples/reference_agent.py"
    if agent.is_symlink() or not agent.is_file():
        raise ValueError("reference agent is missing or unsafe")

    records = []
    result_payloads = []
    for raw_task in suite["tasks"]:
        task_path = _safe_suite_path(raw_task)
        task = load_task(task_path)
        result, run_dir = run_task(
            task,
            [sys.executable, str(agent)],
            output_root=output_dir / "runs",
            working_directory=ROOT,
            inherit_environment=False,
        )
        payload = result.to_dict()
        result_payloads.append(payload)
        result_file = run_dir / "result.json"
        records.append(
            {
                "task_id": task.task_id,
                "task_file": task_path.relative_to(ROOT).as_posix(),
                "task_sha256": task_fingerprint(task),
                "result_file": result_file.relative_to(output_dir).as_posix(),
                "result_sha256": _sha256(result_file),
                "status": result.status,
                "passed": result.passed,
            }
        )

    summary = summarize(result_payloads)
    manifest = {
        "schema_version": 1,
        "release": __version__,
        "suite_file": suite_path.relative_to(ROOT).as_posix(),
        "suite_sha256": _sha256(suite_path),
        "source_tree_sha256": source_fingerprint(ROOT),
        "reference_agent_sha256": _sha256(agent),
        "cases": records,
        "summary": summary.to_dict(),
        "gate_passed": all(item["passed"] for item in records) and len(records) == len(suite["tasks"]),
        "provenance": {
            "github_repository": os.environ.get("GITHUB_REPOSITORY"),
            "github_workflow": os.environ.get("GITHUB_WORKFLOW"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "measured_source_head_sha": _measured_source_head(),
            "runner_name": os.environ.get("RUNNER_NAME"),
            "runner_environment": os.environ.get("RUNNER_ENVIRONMENT"),
            "runner_arch": os.environ.get("RUNNER_ARCH"),
            "runner_os": os.environ.get("RUNNER_OS"),
        },
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    manifest = run_reference_suite(args.suite, args.output)
    return 0 if manifest["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
