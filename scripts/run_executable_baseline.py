from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from reprojudge.evidence import source_fingerprint, task_fingerprint
from reprojudge.reporting import summarize
from reprojudge.runner import run_task
from reprojudge.schema import load_task

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "benchmarks/executable-baseline/manifest.json"
DEFAULT_OUTPUT = ROOT / ".reprojudge/executable-baseline"
AGENT = ROOT / "examples/executable_baseline_agent.py"
MAX_MANIFEST_BYTES = 256 * 1024
EXPECTED_SCOPE = "deterministic subprocess evaluator baseline only"
EXPECTED_CLAIM = (
    "Passing this baseline validates ReproJudge execution, artifact capture, and scoring "
    "mechanics for these fixed tasks only; it does not prove arbitrary-paper reproducibility "
    "or scientific correctness."
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_project_path(value: object) -> Path:
    if not isinstance(value, str) or not value or value.startswith(("/", "\\")):
        raise ValueError("executable baseline task path must be relative")
    candidate = ROOT / value
    resolved = candidate.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError("executable baseline task escapes project root") from exc
    current = ROOT
    for part in Path(value).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("executable baseline task path contains a symlink")
    return candidate


def _load_manifest(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("executable baseline manifest must be a regular file")
    raw = path.read_bytes()
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError("executable baseline manifest exceeds size bound")
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON number: {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid executable baseline manifest: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("executable baseline manifest must have schema_version=1")
    if payload.get("scope") != EXPECTED_SCOPE or payload.get("claim_boundary") != EXPECTED_CLAIM:
        raise ValueError("executable baseline claim boundary changed")
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 3 or len(set(map(str, tasks))) != 3:
        raise ValueError("executable baseline must contain exactly three distinct tasks")
    return payload


def run_executable_baseline(manifest_path: Path, output_dir: Path) -> dict[str, object]:
    manifest = _load_manifest(manifest_path)
    if AGENT.is_symlink() or not AGENT.is_file():
        raise ValueError("executable baseline agent is missing or unsafe")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, object]] = []
    result_payloads: list[dict[str, object]] = []
    raw_tasks = manifest["tasks"]
    assert isinstance(raw_tasks, list)
    for raw_task in raw_tasks:
        task_path = _safe_project_path(raw_task)
        task = load_task(task_path)
        result, run_dir = run_task(
            task,
            [sys.executable, str(AGENT)],
            output_root=output_dir / "runs",
            working_directory=ROOT,
            inherit_environment=False,
        )
        result_payloads.append(result.to_dict())
        result_path = run_dir / "result.json"
        records.append(
            {
                "task_id": task.task_id,
                "task_file": task_path.relative_to(ROOT).as_posix(),
                "task_sha256": task_fingerprint(task),
                "result_sha256": _sha256(result_path),
                "status": result.status,
                "passed": result.passed,
            }
        )

    summary = summarize(result_payloads)
    gate_passed = len(records) == 3 and all(record["passed"] is True for record in records)
    result_manifest: dict[str, object] = {
        "schema_version": 1,
        "scope": EXPECTED_SCOPE,
        "claim_boundary": EXPECTED_CLAIM,
        "source_tree_sha256": source_fingerprint(ROOT),
        "manifest_sha256": _sha256(manifest_path),
        "agent_sha256": _sha256(AGENT),
        "case_count": len(records),
        "cases": records,
        "summary": summary.to_dict(),
        "gate_passed": gate_passed,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(result_manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result_manifest, indent=2, sort_keys=True))
    return result_manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the deterministic subprocess executable baseline."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run_executable_baseline(args.manifest, args.output)
    return 0 if result["gate_passed"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
