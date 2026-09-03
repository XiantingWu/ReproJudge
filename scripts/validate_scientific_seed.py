from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from reprojudge.evidence import canonical_json_sha256, sha256_file, task_fingerprint
from reprojudge.schema import load_task

ROOT = Path(__file__).resolve().parents[1]
SEED_ROOT = ROOT / "benchmarks/scientific-seed"
MANIFEST = SEED_ROOT / "manifest.json"
MAX_MANIFEST_BYTES = 256 * 1024
EXPECTED_CASE_COUNT = 15
SHARD_ID = "scientific-repository-discovery-v1"
SCOPE = "paper-to-canonical-public-repository discovery only"
CURATION_SOURCE = "revision-pinned arXiv real-paper corpus curated for ReproJudge 0.3.0"
CURATION_SOURCE_BLOB_SHA = "73f65ca4e8a4eb62bc7443502466dda919776c03bae935278d5988496cee755d"
_ARXIV = re.compile(r"^[0-9]{4}\.[0-9]{4,5}v[1-9][0-9]*$")
_GITHUB = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _strict_json(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be a regular file")
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError(f"{label} exceeds {MAX_MANIFEST_BYTES} bytes")
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON number: {value}")
            ),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _safe_task_path(value: object) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("scientific seed task path must be a non-empty string")
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or ".." in parsed.parts or not value.startswith("tasks/"):
        raise ValueError(f"unsafe scientific seed task path: {value!r}")
    candidate = SEED_ROOT / parsed.as_posix()
    current = SEED_ROOT
    for part in parsed.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"scientific seed task path contains a symlink: {value}")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(SEED_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"scientific seed task escapes shard root: {value}") from exc
    return candidate


def validate_scientific_seed() -> dict[str, Any]:
    manifest = _strict_json(MANIFEST, "scientific seed manifest")
    expected_keys = {
        "schema_version",
        "shard_id",
        "scope",
        "description",
        "curation_source",
        "curation_source_blob_sha",
        "case_count",
        "tasks",
    }
    if set(manifest) != expected_keys:
        raise ValueError("scientific seed manifest has unsupported or missing fields")
    if manifest.get("schema_version") != 1:
        raise ValueError("scientific seed manifest must use schema_version=1")
    if manifest.get("shard_id") != SHARD_ID or manifest.get("scope") != SCOPE:
        raise ValueError("scientific seed identity/scope changed")
    if manifest.get("curation_source") != CURATION_SOURCE:
        raise ValueError("scientific seed curation source changed")
    if manifest.get("curation_source_blob_sha") != CURATION_SOURCE_BLOB_SHA:
        raise ValueError("scientific seed curation source blob is not the pinned corpus")
    raw_paths = manifest.get("tasks")
    if manifest.get("case_count") != EXPECTED_CASE_COUNT:
        raise ValueError(f"scientific seed must contain exactly {EXPECTED_CASE_COUNT} cases")
    if not isinstance(raw_paths, list) or len(raw_paths) != EXPECTED_CASE_COUNT:
        raise ValueError(f"scientific seed task list must contain exactly {EXPECTED_CASE_COUNT} paths")
    if len(set(raw_paths)) != len(raw_paths):
        raise ValueError("scientific seed task list contains duplicate paths")

    listed = {_safe_task_path(value).resolve() for value in raw_paths}
    actual = {path.resolve() for path in (SEED_ROOT / "tasks").glob("*.json") if path.is_file()}
    if listed != actual:
        raise ValueError("scientific seed manifest task list does not match task files on disk")

    records: list[dict[str, str]] = []
    task_ids: set[str] = set()
    repositories: set[str] = set()
    papers: set[str] = set()
    for raw_path in raw_paths:
        path = _safe_task_path(raw_path)
        task = load_task(path)
        expected_id = f"repo-discovery-{path.stem}"
        if task.task_id != expected_id or task.task_id in task_ids:
            raise ValueError(f"scientific seed task identity is invalid: {raw_path}")
        task_ids.add(task.task_id)
        if not _ARXIV.fullmatch(task.paper) or task.paper in papers:
            raise ValueError(f"scientific seed paper revision is invalid or duplicated: {task.paper}")
        papers.add(task.paper)
        if task.expected_artifacts != ("discovery.json",):
            raise ValueError(f"scientific seed must emit only discovery.json: {task.task_id}")
        if len(task.checks) != 1:
            raise ValueError(f"scientific seed must have exactly one evaluator check: {task.task_id}")
        check = task.checks[0]
        if (
            check.type != "json_equals"
            or check.artifact != "discovery.json"
            or check.json_path != "repository_url"
            or not isinstance(check.expected, str)
            or not _GITHUB.fullmatch(check.expected)
        ):
            raise ValueError(f"scientific seed repository gold is invalid: {task.task_id}")
        if check.expected in repositories:
            raise ValueError(f"scientific seed repository gold is duplicated: {check.expected}")
        repositories.add(check.expected)
        if not {"scientific-seed", "repository-discovery", task.domain}.issubset(set(task.tags)):
            raise ValueError(f"scientific seed tags are incomplete: {task.task_id}")
        metadata = task.metadata
        if set(metadata) != {"benchmark_shard", "evidence_url", "scope"}:
            raise ValueError(f"scientific seed agent-visible metadata contains unsupported fields: {task.task_id}")
        if metadata.get("benchmark_shard") != SHARD_ID or metadata.get("scope") != SCOPE:
            raise ValueError(f"scientific seed task metadata is invalid: {task.task_id}")
        if metadata.get("evidence_url") != f"https://arxiv.org/abs/{task.paper}":
            raise ValueError(f"scientific seed evidence URL is not revision-pinned: {task.task_id}")
        if "curation_source" in task.to_dict().get("metadata", {}):
            raise ValueError(f"scientific seed leaks evaluator-side curation provenance: {task.task_id}")
        records.append(
            {
                "task_id": task.task_id,
                "paper": task.paper,
                "repository_url": check.expected,
                "task_sha256": task_fingerprint(task),
            }
        )

    sorted_records = sorted(records, key=lambda item: item["task_id"])
    identity = {
        "schema_version": 1,
        "shard_id": SHARD_ID,
        "case_count": len(sorted_records),
        "curation_source_blob_sha": CURATION_SOURCE_BLOB_SHA,
        "tasks": sorted_records,
    }
    return {
        "valid": True,
        "scope": SCOPE,
        "case_count": len(sorted_records),
        "manifest_sha256": sha256_file(MANIFEST),
        "curation_source_blob_sha": CURATION_SOURCE_BLOB_SHA,
        "shard_sha256": canonical_json_sha256(identity),
        "tasks": sorted_records,
    }


def main() -> int:
    result = validate_scientific_seed()
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
