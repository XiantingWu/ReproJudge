from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from reprojudge import __version__
from reprojudge.evidence import source_fingerprint
from reprojudge.release_policy import (
    TRUSTED_RELEASE_REPOSITORY,
    current_platform_identity,
    require_trusted_release_authority,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_scientific_seed import validate_scientific_seed

ROOT = Path(__file__).resolve().parents[1]
MAX_MANIFEST_BYTES = 4 * 1024 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} manifest must be a regular file")
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError(f"{label} manifest exceeds size bound")
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON number: {value}")
            ),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid {label} manifest: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} manifest must be an object")
    return payload


def _require_sha(value: object, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase SHA-256 hex digest")
    return value


def _local_measurement_provenance(measured_head: str) -> dict[str, str]:
    head_sha = _require_git_sha(measured_head, "measured_source_head_sha")
    identity = current_platform_identity()
    require_trusted_release_authority(
        repository=identity["repository"],
        mode=identity["mode"],
        measured_source_head_sha=head_sha,
        os_name=identity["os"],
        arch=identity["arch"],
        python_version=identity["python_version"],
    )
    return {
        "repository": TRUSTED_RELEASE_REPOSITORY,
        "runner_environment": identity["runner_environment"],
        "mode": identity["mode"],
        "measured_source_head_sha": head_sha,
        "os": identity["os"],
        "arch": identity["arch"],
        "python_version": identity["python_version"],
    }


def _require_git_sha(value: object, label: str) -> str:
    if not isinstance(value, str) or not _GIT_SHA.fullmatch(value):
        raise ValueError(f"{label} must be a 40-character lowercase git SHA")
    return value


def build_release_evidence(reference_manifest: Path) -> dict[str, Any]:
    reference = _load_manifest(reference_manifest, "reference")
    scientific = validate_scientific_seed()
    source = source_fingerprint(ROOT)
    source_flat = source_fingerprint(ROOT, include_executable_mode=False)

    if scientific.get("valid") is not True or scientific.get("case_count") != 15:
        raise ValueError("scientific discovery seed did not validate")
    if scientific.get("scope") != "paper-to-canonical-public-repository discovery only":
        raise ValueError("scientific discovery seed scope changed")
    _require_sha(scientific.get("curation_source_blob_sha"), "scientific seed curation blob sha")
    _require_sha(scientific.get("manifest_sha256"), "scientific seed manifest_sha256")
    _require_sha(scientific.get("shard_sha256"), "scientific seed shard_sha256")
    scientific_tasks = scientific.get("tasks")
    if not isinstance(scientific_tasks, list) or len(scientific_tasks) != 15:
        raise ValueError("scientific discovery seed task evidence is incomplete")

    if reference.get("release") != __version__:
        raise ValueError("reference release does not match package version")
    if reference.get("source_tree_sha256") != source:
        raise ValueError("reference manifest is stale for the current release source")
    if reference.get("gate_passed") is not True:
        raise ValueError("reference suite gate did not pass")
    cases = reference.get("cases")
    if not isinstance(cases, list) or len(cases) != 4:
        raise ValueError("reference suite must contain exactly four release cases")
    if not all(
        isinstance(case, dict)
        and case.get("passed") is True
        and case.get("status") == "passed"
        for case in cases
    ):
        raise ValueError("one or more reference cases did not pass")

    evidence = {
        "schema_version": 4,
        "release": __version__,
        "source_tree_sha256": source,
        "source_fingerprint": source_flat,
        "scientific_seed": {
            "gate_passed": True,
            "scope": scientific["scope"],
            "case_count": scientific["case_count"],
            "manifest_sha256": scientific["manifest_sha256"],
            "curation_source_blob_sha": scientific["curation_source_blob_sha"],
            "shard_sha256": scientific["shard_sha256"],
            "tasks": scientific_tasks,
        },
        "reference_suite": {
            "gate_passed": True,
            "case_count": len(cases),
            "suite_sha256": _require_sha(reference.get("suite_sha256"), "reference suite_sha256"),
            "reference_agent_sha256": _require_sha(
                reference.get("reference_agent_sha256"), "reference agent sha256"
            ),
            "manifest_sha256": _sha256(reference_manifest),
            "cases": [
                {
                    "task_id": str(case["task_id"]),
                    "task_sha256": _require_sha(case.get("task_sha256"), "reference task_sha256"),
                    "result_sha256": _require_sha(case.get("result_sha256"), "reference result_sha256"),
                    "status": "passed",
                }
                for case in cases
            ],
        },
        "measurement_provenance": _local_measurement_provenance(_measured_source_head()),
        "claims": {
            "scientific_seed_scope": "15 revision-pinned real-paper repository-discovery tasks only",
            "reference_suite_scope": "deterministic evaluator mechanics only",
            "arbitrary_paper_reproducibility_proven": False,
            "scientific_correctness_proven": False,
        },
    }
    return evidence


def _measured_source_head() -> str:
    """Resolve the current measured source head from the local Git repository."""
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("cannot resolve the measured source head from local Git") from exc
    return _require_git_sha(result.stdout.strip(), "measured_source_head_sha")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build sanitized, source-bound ReproJudge release evidence.")
    parser.add_argument("--reference-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = build_release_evidence(args.reference_manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print("REPROJUDGE_RELEASE_EVIDENCE_WRITTEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
