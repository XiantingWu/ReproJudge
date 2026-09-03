from __future__ import annotations

import hashlib
import json
import math
import reprlib
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from ._paths import reject_symlink_components
from .schema import BenchmarkTask, CheckSpec, _safe_relative_path

MAX_SCORER_ARTIFACT_BYTES = 64 * 1024 * 1024
MAX_TEXT_SCORER_BYTES = 4 * 1024 * 1024
MAX_JSON_SCORER_BYTES = 16 * 1024 * 1024
MAX_CHECK_DETAIL_CHARS = 4096
REGEX_TIMEOUT_SECONDS = 1.0

_REPR = reprlib.Repr()
_REPR.maxstring = 1024
_REPR.maxother = 1024
_REPR.maxlist = 20
_REPR.maxtuple = 20
_REPR.maxset = 20
_REPR.maxfrozenset = 20
_REPR.maxdeque = 20
_REPR.maxdict = 20
_REPR.maxarray = 20
_REPR.maxlevel = 4


def _bounded_detail(value: object) -> str:
    detail = str(value)
    if len(detail) <= MAX_CHECK_DETAIL_CHARS:
        return detail
    suffix = "...<truncated>"
    return detail[: MAX_CHECK_DETAIL_CHARS - len(suffix)] + suffix


def _bounded_repr(value: object) -> str:
    return _bounded_detail(_REPR.repr(value))


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "detail", _bounded_detail(self.detail))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def safe_artifact_path(root: Path, relative: str) -> Path:
    """Resolve a declared artifact while rejecting every symlink component."""
    relative = _safe_relative_path(relative, "artifact")
    reject_symlink_components(root, "artifact root")
    root_resolved = root.resolve()
    if root.is_symlink():
        raise ValueError("artifact root must not be a symlink")
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"artifact escapes output directory via symlink: {relative}")
    candidate = current.resolve()
    if root_resolved not in candidate.parents and candidate != root_resolved:
        raise ValueError(f"artifact escapes output directory: {relative}")
    return candidate


def _bounded_file(path: Path, limit: int) -> None:
    try:
        stat = path.stat()
    except OSError as exc:
        raise ValueError(f"could not stat artifact: {exc}") from exc
    if stat.st_size > limit:
        raise ValueError(f"artifact exceeds scorer byte limit ({limit})")


def _json_path(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if isinstance(current, dict):
            if part not in current:
                raise KeyError(path)
            current = current[part]
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            current = current[index]
        else:
            raise KeyError(path)
    return current


def _load_json(path: Path) -> Any:
    _bounded_file(path, MAX_JSON_SCORER_BYTES)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(
            handle,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON number: {value}")
            ),
        )


def _sha256(path: Path) -> str:
    _bounded_file(path, MAX_SCORER_ARTIFACT_BYTES)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _regex_search(pattern: str, path: Path) -> bool:
    """Evaluate Python regex in an isolated child with a hard wall-clock timeout."""
    helper = (
        "import pathlib,re,sys; "
        "p=pathlib.Path(sys.argv[2]); "
        "s=p.stat().st_size; "
        f"assert s <= {MAX_TEXT_SCORER_BYTES}; "
        "t=p.read_text(encoding='utf-8'); "
        "raise SystemExit(0 if re.search(sys.argv[1], t) is not None else 1)"
    )
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-c", helper, pattern, str(path)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=REGEX_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError(
            f"regex evaluation exceeded {REGEX_TIMEOUT_SECONDS:.1f}s timeout"
        ) from exc
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    detail = (completed.stderr or "regex helper failed").strip().splitlines()[-1][:300]
    raise ValueError(f"regex helper failed: {detail}")


def score_check(check: CheckSpec, artifact_root: Path) -> CheckResult:
    label = f"{check.type}:{check.artifact}"
    try:
        artifact = safe_artifact_path(artifact_root, check.artifact)
    except ValueError as exc:
        return CheckResult(label, False, str(exc))
    if not artifact.is_file():
        return CheckResult(label, False, "artifact is missing")
    if check.type == "artifact_exists":
        return CheckResult(label, True, "artifact exists")
    if check.type == "file_sha256":
        try:
            observed = _sha256(artifact)
        except (OSError, ValueError) as exc:
            return CheckResult(label, False, f"could not hash artifact: {exc}")
        passed = observed == check.sha256
        return CheckResult(
            label, passed, f"observed={observed}, expected={check.sha256}"
        )

    if check.type in {"text_contains", "text_regex"}:
        try:
            _bounded_file(artifact, MAX_TEXT_SCORER_BYTES)
            if check.type == "text_contains":
                text = artifact.read_text(encoding="utf-8")
                passed = (check.contains or "") in text
                return CheckResult(label, passed, f"contains={check.contains!r}")
            passed = _regex_search(check.pattern or "", artifact)
            return CheckResult(label, passed, f"pattern={check.pattern!r}")
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            return CheckResult(
                label, False, f"could not evaluate text artifact: {exc}"
            )

    try:
        payload = _load_json(artifact)
        observed = _json_path(payload, check.json_path or "")
    except (
        OSError,
        json.JSONDecodeError,
        UnicodeDecodeError,
        ValueError,
        KeyError,
        IndexError,
        TypeError,
    ) as exc:
        return CheckResult(label, False, f"could not read JSON value: {exc}")

    if check.type == "json_equals":
        passed = observed == check.expected
        return CheckResult(
            label,
            passed,
            f"observed={_bounded_repr(observed)}, expected={_bounded_repr(check.expected)}",
        )

    if check.type != "json_numeric" or check.target is None:
        return CheckResult(label, False, "invalid numeric check specification")
    if (
        not isinstance(observed, (int, float))
        or isinstance(observed, bool)
        or not math.isfinite(float(observed))
    ):
        return CheckResult(
            label,
            False,
            f"observed value is not a finite number: {_bounded_repr(observed)}",
        )
    passed = math.isclose(
        float(observed),
        float(check.target),
        rel_tol=check.rel_tol,
        abs_tol=check.abs_tol,
    )
    return CheckResult(
        label,
        passed,
        f"observed={float(observed)!r}, target={check.target!r}, abs_tol={check.abs_tol}, rel_tol={check.rel_tol}",
    )


def score_task(task: BenchmarkTask, artifact_root: Path) -> tuple[CheckResult, ...]:
    declared_checks = list(task.checks)
    checked_artifacts = {check.artifact for check in declared_checks}
    for artifact in task.expected_artifacts:
        if artifact not in checked_artifacts:
            declared_checks.append(CheckSpec(type="artifact_exists", artifact=artifact))
    return tuple(score_check(check, artifact_root) for check in declared_checks)
