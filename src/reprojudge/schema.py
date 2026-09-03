from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from ._paths import reject_symlink_components

SCHEMA_VERSION = 1
MAX_TASK_BYTES = 1024 * 1024
MAX_EXPECTED_ARTIFACTS = 128
MAX_CHECKS = 256
MAX_TAGS = 64
MAX_METADATA_KEYS = 128
MAX_METADATA_JSON_BYTES = 128 * 1024
MAX_EXPECTED_JSON_BYTES = 64 * 1024
_ALLOWED_CHECKS = {
    "artifact_exists",
    "json_equals",
    "json_numeric",
    "text_contains",
    "text_regex",
    "file_sha256",
}
_ALLOWED_CHECK_FIELDS = {
    "artifact_exists": {"type", "artifact"},
    "json_equals": {"type", "artifact", "json_path", "expected"},
    "json_numeric": {"type", "artifact", "json_path", "target", "abs_tol", "rel_tol"},
    "text_contains": {"type", "artifact", "contains"},
    "text_regex": {"type", "artifact", "pattern"},
    "file_sha256": {"type", "artifact", "sha256"},
}
_ALLOWED_TASK_FIELDS = {
    "schema_version",
    "task_id",
    "domain",
    "paper",
    "expected_artifacts",
    "title",
    "instructions",
    "tags",
    "checks",
    "timeout_seconds",
    "metadata",
}
_TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _ensure_utf8(value: str, field_name: str) -> str:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{field_name} must be valid UTF-8 text") from exc
    return value


def _require_nonempty_string(value: object, field_name: str, *, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    result = value.strip()
    if len(result) > maximum or "\x00" in result:
        raise ValueError(f"{field_name} exceeds its allowed bound")
    return _ensure_utf8(result, field_name)


def _optional_string(value: object, field_name: str, *, maximum: int) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    result = value.strip()
    if len(result) > maximum or "\x00" in result:
        raise ValueError(f"{field_name} exceeds its allowed bound")
    return _ensure_utf8(result, field_name)


def _safe_task_id(value: object) -> str:
    task_id = _require_nonempty_string(value, "task_id", maximum=200)
    if not _TASK_ID_RE.fullmatch(task_id):
        raise ValueError("task_id must match [A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
    return task_id


def _safe_relative_path(value: object, field_name: str) -> str:
    path = _require_nonempty_string(value, field_name, maximum=512)
    if value != path:
        raise ValueError(f"{field_name} must not have leading or trailing whitespace")
    normalized = path.replace("\\", "/")
    parsed = PurePosixPath(normalized)
    windows = PureWindowsPath(path)
    if (
        parsed.is_absolute()
        or windows.drive
        or windows.root
        or normalized.startswith("~")
        or ".." in normalized.split("/")
    ):
        raise ValueError(f"{field_name} must be a safe relative path")
    if any(part in {"", "."} for part in normalized.split("/")):
        raise ValueError(f"{field_name} must not contain empty or current-directory components")
    return parsed.as_posix()


def _finite_number(
    value: object,
    field_name: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError(f"{field_name} must be a finite number")
    result = float(value)
    if minimum is not None and result < minimum:
        raise ValueError(f"{field_name} must be >= {minimum}")
    if maximum is not None and result > maximum:
        raise ValueError(f"{field_name} must be <= {maximum}")
    return result


def _json_value(value: object, field_name: str, *, maximum_bytes: int) -> Any:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ValueError(f"{field_name} must be finite UTF-8 JSON data") from exc
    if len(encoded) > maximum_bytes:
        raise ValueError(f"{field_name} exceeds its JSON byte bound ({maximum_bytes})")
    return value


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not allowed: {value}")


@dataclass(frozen=True)
class CheckSpec:
    type: str
    artifact: str
    json_path: str | None = None
    expected: Any = None
    target: float | None = None
    abs_tol: float = 0.0
    rel_tol: float = 0.0
    contains: str | None = None
    pattern: str | None = None
    sha256: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"type": self.type, "artifact": self.artifact}
        if self.type == "json_equals":
            payload.update({"json_path": self.json_path, "expected": self.expected})
        elif self.type == "json_numeric":
            payload.update(
                {
                    "json_path": self.json_path,
                    "target": self.target,
                    "abs_tol": self.abs_tol,
                    "rel_tol": self.rel_tol,
                }
            )
        elif self.type == "text_contains":
            payload["contains"] = self.contains
        elif self.type == "text_regex":
            payload["pattern"] = self.pattern
        elif self.type == "file_sha256":
            payload["sha256"] = self.sha256
        return payload


@dataclass(frozen=True)
class BenchmarkTask:
    task_id: str
    domain: str
    paper: str
    expected_artifacts: tuple[str, ...]
    schema_version: int = SCHEMA_VERSION
    title: str = ""
    instructions: str = ""
    tags: tuple[str, ...] = ()
    checks: tuple[CheckSpec, ...] = ()
    timeout_seconds: float = 300.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["expected_artifacts"] = list(self.expected_artifacts)
        payload["tags"] = list(self.tags)
        payload["checks"] = [check.to_dict() for check in self.checks]
        return payload


def _parse_check(payload: object, index: int) -> CheckSpec:
    if not isinstance(payload, dict):
        raise ValueError(f"checks[{index}] must be an object")
    check_type = _require_nonempty_string(payload.get("type"), f"checks[{index}].type", maximum=64)
    if check_type not in _ALLOWED_CHECKS:
        raise ValueError(f"checks[{index}].type must be one of: {', '.join(sorted(_ALLOWED_CHECKS))}")
    unknown = sorted(str(key) for key in payload if key not in _ALLOWED_CHECK_FIELDS[check_type])
    if unknown:
        raise ValueError(
            f"checks[{index}] contains unsupported fields for {check_type}: {', '.join(unknown)}"
        )
    artifact = _safe_relative_path(payload.get("artifact"), f"checks[{index}].artifact")
    json_path = payload.get("json_path")
    if json_path is not None:
        json_path = _require_nonempty_string(json_path, f"checks[{index}].json_path", maximum=512)

    if check_type == "artifact_exists":
        return CheckSpec(type=check_type, artifact=artifact)
    if check_type == "file_sha256":
        digest = _require_nonempty_string(payload.get("sha256"), f"checks[{index}].sha256", maximum=64)
        if not _SHA256_RE.fullmatch(digest):
            raise ValueError(f"checks[{index}].sha256 must be 64 lowercase hex characters")
        return CheckSpec(type=check_type, artifact=artifact, sha256=digest)
    if check_type == "text_contains":
        contains = _require_nonempty_string(payload.get("contains"), f"checks[{index}].contains", maximum=4096)
        return CheckSpec(type=check_type, artifact=artifact, contains=contains)
    if check_type == "text_regex":
        pattern = _require_nonempty_string(payload.get("pattern"), f"checks[{index}].pattern", maximum=4096)
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ValueError(f"checks[{index}].pattern is invalid: {exc}") from exc
        return CheckSpec(type=check_type, artifact=artifact, pattern=pattern)

    if json_path is None:
        raise ValueError(f"checks[{index}].json_path is required for {check_type}")
    if check_type == "json_equals":
        if "expected" not in payload:
            raise ValueError(f"checks[{index}].expected is required for json_equals")
        expected = _json_value(
            payload["expected"],
            f"checks[{index}].expected",
            maximum_bytes=MAX_EXPECTED_JSON_BYTES,
        )
        return CheckSpec(type=check_type, artifact=artifact, json_path=json_path, expected=expected)

    target = _finite_number(payload.get("target"), f"checks[{index}].target")
    abs_tol = _finite_number(payload.get("abs_tol", 0.0), f"checks[{index}].abs_tol", minimum=0.0)
    rel_tol = _finite_number(payload.get("rel_tol", 0.0), f"checks[{index}].rel_tol", minimum=0.0)
    return CheckSpec(
        type=check_type,
        artifact=artifact,
        json_path=json_path,
        target=target,
        abs_tol=abs_tol,
        rel_tol=rel_tol,
    )


def parse_task(payload: dict[str, object]) -> BenchmarkTask:
    if not isinstance(payload, dict):
        raise ValueError("task manifest must be a JSON object")
    unknown = sorted(str(key) for key in payload if key not in _ALLOWED_TASK_FIELDS)
    if unknown:
        raise ValueError("task manifest contains unsupported fields: " + ", ".join(unknown))
    required = ("task_id", "domain", "paper", "expected_artifacts")
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")

    schema_version = payload.get("schema_version", SCHEMA_VERSION)
    if schema_version != SCHEMA_VERSION or isinstance(schema_version, bool):
        raise ValueError(f"unsupported schema_version {schema_version!r}; expected {SCHEMA_VERSION!r}")

    artifacts = payload["expected_artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) > MAX_EXPECTED_ARTIFACTS:
        raise ValueError(f"expected_artifacts must be a list with at most {MAX_EXPECTED_ARTIFACTS} items")
    normalized_artifacts = tuple(_safe_relative_path(item, "expected_artifacts item") for item in artifacts)
    if len(set(normalized_artifacts)) != len(normalized_artifacts):
        raise ValueError("expected_artifacts must not contain duplicates")

    tags = payload.get("tags", [])
    if not isinstance(tags, list) or len(tags) > MAX_TAGS:
        raise ValueError(f"tags must be a list with at most {MAX_TAGS} items")
    normalized_tags = tuple(
        _require_nonempty_string(item, f"tags[{index}]", maximum=128)
        for index, item in enumerate(tags)
    )

    checks_payload = payload.get("checks", [])
    if not isinstance(checks_payload, list) or len(checks_payload) > MAX_CHECKS:
        raise ValueError(f"checks must be a list with at most {MAX_CHECKS} entries")
    checks = tuple(_parse_check(item, index) for index, item in enumerate(checks_payload))
    artifact_set = set(normalized_artifacts)
    unknown_artifacts = sorted({check.artifact for check in checks} - artifact_set)
    if unknown_artifacts:
        raise ValueError("checks reference undeclared artifacts: " + ", ".join(unknown_artifacts))

    timeout = _finite_number(
        payload.get("timeout_seconds", 300.0),
        "timeout_seconds",
        minimum=0.000001,
        maximum=86400.0,
    )
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict) or len(metadata) > MAX_METADATA_KEYS:
        raise ValueError(f"metadata must be an object with at most {MAX_METADATA_KEYS} keys")
    for key in metadata:
        if not isinstance(key, str) or not key or len(key) > 128 or "\x00" in key:
            raise ValueError("metadata keys must be bounded non-empty strings")
        _ensure_utf8(key, "metadata key")
    _json_value(metadata, "metadata", maximum_bytes=MAX_METADATA_JSON_BYTES)

    return BenchmarkTask(
        task_id=_safe_task_id(payload["task_id"]),
        domain=_require_nonempty_string(payload["domain"], "domain", maximum=200),
        paper=_require_nonempty_string(payload["paper"], "paper", maximum=4096),
        expected_artifacts=normalized_artifacts,
        schema_version=SCHEMA_VERSION,
        title=_optional_string(payload.get("title", ""), "title", maximum=500),
        instructions=_optional_string(payload.get("instructions", ""), "instructions", maximum=20000),
        tags=normalized_tags,
        checks=checks,
        timeout_seconds=timeout,
        metadata=dict(metadata),
    )


def load_task(path: Path) -> BenchmarkTask:
    reject_symlink_components(path, "task manifest")
    if path.is_symlink():
        raise ValueError("task manifest must not be a symlink")
    try:
        stat = path.stat()
    except OSError as exc:
        raise ValueError(f"could not read task manifest: {exc}") from exc
    if not path.is_file():
        raise ValueError("task manifest must be a regular JSON file")
    if stat.st_size > MAX_TASK_BYTES:
        raise ValueError(f"task manifest exceeds {MAX_TASK_BYTES} bytes")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_json_constant)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid task manifest JSON: {exc}") from exc
    return parse_task(payload)
