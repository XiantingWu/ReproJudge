from __future__ import annotations

import argparse
import os
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from reprojudge import __version__
from reprojudge.evidence import source_fingerprint, task_fingerprint
from reprojudge.registry import TaskRegistry
from reprojudge.release_policy import require_trusted_release_authority

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_scientific_seed import validate_scientific_seed

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "benchmarks/release-evidence-0.3.0.json"
MAX_EVIDENCE_BYTES = 512 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


def _current_source(root: Path) -> str:
    # Windows cannot represent POSIX execute bits, so byte identity is
    # verified there without exec-bit normalization; the macOS ARM64 release
    # authority lane always uses the full exec-bit-aware fingerprint.
    return source_fingerprint(root, include_executable_mode=os.name != "nt")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_sha(value: object, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _require_git_sha(value: object, label: str) -> str:
    if not isinstance(value, str) or not _GIT_SHA.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase 40-character git SHA")
    return value


def _load_json(path: Path, label: str, limit: int) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} is missing or unsafe")
    if path.stat().st_size > limit:
        raise ValueError(f"{label} exceeds size bound")
    payload = json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON number: {value}")
        ),
    )
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be an object")
    return payload


def _load_evidence() -> dict[str, Any]:
    return _load_json(EVIDENCE, "release evidence", MAX_EVIDENCE_BYTES)


def _require_release_evidence(registry: TaskRegistry) -> None:
    payload = _load_evidence()
    if set(payload) != {
        "schema_version",
        "release",
        "source_tree_sha256",
        "source_fingerprint",
        "scientific_seed",
        "reference_suite",
        "measurement_provenance",
        "claims",
    }:
        raise ValueError("release evidence has unsupported top-level fields")
    if payload.get("schema_version") != 4:
        raise ValueError("unsupported release evidence schema")
    if payload.get("release") != __version__:
        raise ValueError("release evidence version does not match package")
    current_source = source_fingerprint(ROOT, include_executable_mode=os.name != "nt")
    if payload.get("source_fingerprint") != source_fingerprint(ROOT, include_executable_mode=False):
        raise ValueError("release evidence source fingerprint identity is stale")
    if os.name != "nt":
        if payload.get("source_tree_sha256") != current_source:
            raise ValueError("release evidence source fingerprint is stale")
    elif not isinstance(payload.get("source_tree_sha256"), str) or not _SHA256.fullmatch(
        payload.get("source_tree_sha256")
    ):
        raise ValueError("release evidence source_tree_sha256 is invalid")

    current_scientific = validate_scientific_seed()
    scientific = payload.get("scientific_seed")
    if not isinstance(scientific, dict) or set(scientific) != {
        "gate_passed",
        "scope",
        "case_count",
        "manifest_sha256",
        "curation_source_blob_sha",
        "shard_sha256",
        "tasks",
    }:
        raise ValueError("release evidence scientific-seed shape is invalid")
    if scientific.get("gate_passed") is not True or scientific.get("case_count") != 15:
        raise ValueError("release evidence lacks the exact 15-case scientific discovery shard")
    for key in ("scope", "case_count", "manifest_sha256", "curation_source_blob_sha", "shard_sha256", "tasks"):
        if scientific.get(key) != current_scientific.get(key):
            raise ValueError(f"release evidence scientific seed is stale: {key}")
    _require_sha(scientific.get("manifest_sha256"), "scientific seed manifest_sha256")
    _require_sha(scientific.get("shard_sha256"), "scientific seed shard_sha256")
    scientific_tasks = scientific.get("tasks")
    if not isinstance(scientific_tasks, list) or len(scientific_tasks) != 15:
        raise ValueError("release evidence scientific seed task identities are incomplete")
    for item in scientific_tasks:
        if not isinstance(item, dict) or set(item) != {
            "task_id",
            "paper",
            "repository_url",
            "task_sha256",
        }:
            raise ValueError("scientific seed task evidence shape is invalid")
        _require_sha(item.get("task_sha256"), "scientific seed task_sha256")

    reference = payload.get("reference_suite")
    if not isinstance(reference, dict) or set(reference) != {
        "gate_passed",
        "case_count",
        "suite_sha256",
        "reference_agent_sha256",
        "manifest_sha256",
        "cases",
    }:
        raise ValueError("release evidence reference-suite shape is invalid")
    if reference.get("gate_passed") is not True or reference.get("case_count") != 4:
        raise ValueError("release evidence lacks the exact passing four-case reference suite")
    if reference.get("suite_sha256") != _sha256(ROOT / "benchmarks/reference-suite.json"):
        raise ValueError("release evidence reference suite hash is stale")
    if reference.get("reference_agent_sha256") != _sha256(ROOT / "examples/reference_agent.py"):
        raise ValueError("release evidence reference agent hash is stale")
    _require_sha(reference.get("manifest_sha256"), "reference manifest_sha256")
    cases = reference.get("cases")
    if not isinstance(cases, list) or len(cases) != 4:
        raise ValueError("release evidence reference cases are incomplete")
    by_id = {entry.task.task_id: entry for entry in registry.entries()}
    seen: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"task_id", "task_sha256", "result_sha256", "status"}:
            raise ValueError("reference release evidence case shape is invalid")
        if case.get("status") != "passed":
            raise ValueError("reference release evidence contains a non-passing case")
        task_id = case.get("task_id")
        if not isinstance(task_id, str) or task_id not in by_id or task_id in seen:
            raise ValueError("reference release evidence task identity is invalid")
        seen.add(task_id)
        if case.get("task_sha256") != task_fingerprint(by_id[task_id].task):
            raise ValueError(f"reference task evidence is stale: {task_id}")
        _require_sha(case.get("result_sha256"), f"reference result_sha256 for {task_id}")
    if seen != set(by_id):
        raise ValueError("reference release evidence does not cover every release task")

    provenance = payload.get("measurement_provenance")
    if not isinstance(provenance, dict) or set(provenance) != {
        "repository",
        "runner_environment",
        "mode",
        "measured_source_head_sha",
        "os",
        "arch",
        "python_version",
    }:
        raise ValueError("release evidence measurement provenance shape is invalid")
    _require_git_sha(provenance.get("measured_source_head_sha"), "measurement measured_source_head_sha")
    require_trusted_release_authority(
        repository=provenance.get("repository"),
        mode=provenance.get("mode"),
        measured_source_head_sha=provenance.get("measured_source_head_sha"),
        os_name=provenance.get("os"),
        arch=provenance.get("arch"),
        python_version=provenance.get("python_version"),
    )

    claims = payload.get("claims")
    expected_claims = {
        "scientific_seed_scope": "15 revision-pinned real-paper repository-discovery tasks only",
        "reference_suite_scope": "deterministic evaluator mechanics only",
        "arbitrary_paper_reproducibility_proven": False,
        "scientific_correctness_proven": False,
    }
    if claims != expected_claims:
        raise ValueError("release evidence claim boundary changed or is overstated")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-release-evidence", action="store_true")
    args = parser.parse_args()

    if __version__ != "0.3.0":
        raise SystemExit(f"unexpected release version: {__version__}")
    registry = TaskRegistry.from_directory(ROOT / "benchmarks/reference/tasks")
    if len(registry.entries()) != 4:
        raise SystemExit("reference registry must contain exactly four release tasks")

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/launch_surface_check.py")],
        cwd=ROOT,
        check=False,
    )
    if result.returncode:
        return result.returncode
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_public_identity_hygiene.py")],
        cwd=ROOT,
        check=False,
    )
    if result.returncode:
        return result.returncode
    if args.require_release_evidence:
        try:
            _require_release_evidence(registry)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise SystemExit(f"release evidence check failed: {exc}") from exc
    print(
        f"release check PASS version={__version__} "
        f"reference_tasks={len(registry.entries())} source={source_fingerprint(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())