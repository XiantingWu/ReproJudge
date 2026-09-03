from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from statistics import mean
from typing import Any

from ._paths import reject_symlink_components
from .schema import MAX_EXPECTED_ARTIFACTS, _SHA256_RE, _safe_relative_path
from .telemetry import _ALLOWED_KEYS as _TELEMETRY_KEYS

MAX_RESULT_BYTES = 4 * 1024 * 1024
_ALLOWED_STATUSES = {"passed", "failed", "agent_error", "timeout", "launch_error", "telemetry_error"}
_MAX_RESULT_CHECKS = 512


@dataclass(frozen=True)
class Summary:
    total: int
    passed: int
    failed: int
    pass_rate: float
    mean_duration_seconds: float
    statuses: dict[str, int]
    total_tokens: int
    total_model_cost_usd: float
    interventions: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": self.pass_rate,
            "mean_duration_seconds": self.mean_duration_seconds,
            "statuses": dict(sorted(self.statuses.items())),
            "total_tokens": self.total_tokens,
            "total_model_cost_usd": self.total_model_cost_usd,
            "interventions": self.interventions,
        }


def _no_symlink_components(root: Path, path: Path) -> None:
    relative = path.relative_to(root)
    current = root
    for part in PurePosixPath(relative.as_posix()).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"result path contains a symlink: {relative.as_posix()}")


def _validate_telemetry(telemetry: object, path: Path) -> None:
    if telemetry is None:
        return
    if not isinstance(telemetry, dict):
        raise ValueError(f"result telemetry must be an object or null: {path}")
    unknown = sorted(set(telemetry) - _TELEMETRY_KEYS)
    if unknown:
        raise ValueError(f"result telemetry has unsupported keys: {path}")
    tokens = telemetry.get("token_usage")
    if tokens is not None and (
        not isinstance(tokens, int) or isinstance(tokens, bool) or tokens < 0
    ):
        raise ValueError(f"result telemetry token_usage is invalid: {path}")
    cost = telemetry.get("model_cost_usd")
    if cost is not None and (
        not isinstance(cost, (int, float))
        or isinstance(cost, bool)
        or not math.isfinite(float(cost))
        or float(cost) < 0
    ):
        raise ValueError(f"result telemetry model_cost_usd is invalid: {path}")
    interventions = telemetry.get("interventions")
    if interventions is not None and (
        not isinstance(interventions, list)
        or len(interventions) > 64
        or not all(
            isinstance(item, str)
            and item
            and len(item) <= 256
            and not any(ord(char) < 0x20 or ord(char) == 0x7F for char in item)
            for item in interventions
        )
    ):
        raise ValueError(f"result telemetry interventions are invalid: {path}")
    for key in ("agent_name", "agent_version", "model", "provider"):
        value = telemetry.get(key)
        if value is not None and (
            not isinstance(value, str)
            or not value.strip()
            or len(value.strip()) > 256
            or any(ord(char) < 0x20 or ord(char) == 0x7F for char in value)
        ):
            raise ValueError(f"result telemetry {key} is invalid: {path}")


def _validate_artifacts(artifacts: object, path: Path) -> None:
    if not isinstance(artifacts, list) or len(artifacts) > MAX_EXPECTED_ARTIFACTS:
        raise ValueError(f"result artifacts are invalid: {path}")
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {"path", "size_bytes", "sha256"}:
            raise ValueError(f"result artifact record is invalid: {path}")
        try:
            _safe_relative_path(item["path"], "result artifact path")
        except ValueError as exc:
            raise ValueError(f"result artifact path is invalid: {path}: {exc}") from exc
        size = item["size_bytes"]
        if (
            not isinstance(size, int)
            or isinstance(size, bool)
            or size < 0
            or size > 268435456
        ):
            raise ValueError(f"result artifact size is invalid: {path}")
        if not isinstance(item["sha256"], str) or not _SHA256_RE.fullmatch(item["sha256"]):
            raise ValueError(f"result artifact sha256 is invalid: {path}")


def _validate_checks(checks: object, path: Path) -> None:
    if not isinstance(checks, list) or len(checks) > _MAX_RESULT_CHECKS:
        raise ValueError(f"result checks are invalid: {path}")
    for item in checks:
        if not isinstance(item, dict) or set(item) != {"name", "passed", "detail"}:
            raise ValueError(f"result check record is invalid: {path}")
        name = item["name"]
        detail = item["detail"]
        if not isinstance(name, str) or not name or len(name) > 1024:
            raise ValueError(f"result check name is invalid: {path}")
        if not isinstance(item["passed"], bool):
            raise ValueError(f"result check passed value is invalid: {path}")
        if not isinstance(detail, str) or len(detail) > 4096:
            raise ValueError(f"result check detail is invalid: {path}")


def _validate_result_payload(payload: dict[str, Any], path: Path) -> None:
    try:
        json.dumps(payload, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"result contains non-finite/non-JSON values: {path}: {exc}") from exc
    version = payload.get("result_schema_version")
    if version is not None and (version != 1 or isinstance(version, bool)):
        raise ValueError(f"unsupported result schema version: {path}")
    task_id = payload.get("task_id")
    status = payload.get("status")
    if not isinstance(task_id, str) or not task_id or len(task_id) > 200:
        raise ValueError(f"result JSON lacks bounded task identity: {path}")
    if status not in _ALLOWED_STATUSES:
        raise ValueError(f"result JSON has unsupported status: {path}")
    duration = payload.get("duration_seconds")
    if duration is not None and (
        not isinstance(duration, (int, float))
        or isinstance(duration, bool)
        or not math.isfinite(float(duration))
        or float(duration) < 0
    ):
        raise ValueError(f"result duration_seconds is invalid: {path}")
    passed = payload.get("passed")
    if passed is not None and (
        not isinstance(passed, bool) or passed != (status == "passed")
    ):
        raise ValueError(f"result passed/status fields are inconsistent: {path}")
    taxonomy = payload.get("failure_taxonomy")
    if taxonomy is not None and (
        not isinstance(taxonomy, list)
        or len(taxonomy) > 64
        or len({item for item in taxonomy if isinstance(item, str)}) != len(taxonomy)
        or not all(
            isinstance(item, str)
            and item
            and len(item) <= 128
            and not any(ord(char) < 0x20 or ord(char) == 0x7F for char in item)
            for item in taxonomy
        )
    ):
        raise ValueError(f"result failure_taxonomy is invalid: {path}")
    if "artifacts" in payload:
        _validate_artifacts(payload["artifacts"], path)
    if "checks" in payload:
        _validate_checks(payload["checks"], path)
    _validate_telemetry(payload.get("telemetry"), path)


def _strict_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"result must be a regular file: {path}")
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ValueError(f"could not stat result: {path}: {exc}") from exc
    if size > MAX_RESULT_BYTES:
        raise ValueError(f"result exceeds {MAX_RESULT_BYTES} bytes: {path}")
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite number: {value}")
            ),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid result JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"result JSON must be an object: {path}")
    _validate_result_payload(payload, path)
    return payload


def load_results(root: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    reject_symlink_components(root, "result root")
    if root.is_symlink():
        raise ValueError("result directory must not be a symlink")
    if not root.exists():
        return results
    if not root.is_dir():
        raise ValueError("result root must be a directory")
    root_resolved = root.resolve()
    for path in sorted(root.rglob("result.json")):
        _no_symlink_components(root, path)
        resolved = path.resolve()
        if root_resolved not in resolved.parents and resolved != root_resolved:
            raise ValueError(f"result escapes result root: {path}")
        results.append(_strict_json(path))
    return results


def summarize(results: list[dict[str, Any]]) -> Summary:
    if not results:
        return Summary(0, 0, 0, 0.0, 0.0, {}, 0, 0.0, 0)
    statuses: dict[str, int] = {}
    durations: list[float] = []
    passed = 0
    total_tokens = 0
    total_cost = 0.0
    interventions = 0
    for result in results:
        status = str(result.get("status", "unknown"))
        statuses[status] = statuses.get(status, 0) + 1
        if status == "passed":
            passed += 1
        duration = result.get("duration_seconds")
        if (
            isinstance(duration, (int, float))
            and not isinstance(duration, bool)
            and math.isfinite(float(duration))
            and float(duration) >= 0
        ):
            durations.append(float(duration))
        telemetry = result.get("telemetry")
        if isinstance(telemetry, dict):
            tokens = telemetry.get("token_usage")
            if isinstance(tokens, int) and not isinstance(tokens, bool) and tokens >= 0:
                total_tokens += tokens
            cost = telemetry.get("model_cost_usd")
            if (
                isinstance(cost, (int, float))
                and not isinstance(cost, bool)
                and math.isfinite(float(cost))
                and float(cost) >= 0
            ):
                total_cost += float(cost)
            raw_interventions = telemetry.get("interventions")
            if isinstance(raw_interventions, list):
                interventions += len(raw_interventions)
    total = len(results)
    return Summary(
        total=total,
        passed=passed,
        failed=total - passed,
        pass_rate=round(passed / total, 6),
        mean_duration_seconds=round(mean(durations), 6) if durations else 0.0,
        statuses=statuses,
        total_tokens=total_tokens,
        total_model_cost_usd=round(total_cost, 8),
        interventions=interventions,
    )


def markdown_summary(summary: Summary) -> str:
    status_rows = "\n".join(
        f"| {name} | {count} |" for name, count in sorted(summary.statuses.items())
    ) or "| none | 0 |"
    return (
        "# ReproJudge summary\n\n"
        f"- Runs: {summary.total}\n"
        f"- Passed: {summary.passed}\n"
        f"- Failed: {summary.failed}\n"
        f"- Pass rate: {summary.pass_rate:.1%}\n"
        f"- Mean duration: {summary.mean_duration_seconds:.3f}s\n"
        f"- Tokens: {summary.total_tokens}\n"
        f"- Model cost (USD): {summary.total_model_cost_usd:.6f}\n"
        f"- Recorded interventions: {summary.interventions}\n\n"
        "| Status | Count |\n|---|---:|\n"
        f"{status_rows}\n"
    )
