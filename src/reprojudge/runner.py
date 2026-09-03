from __future__ import annotations

import hashlib
import json
import os
import platform
import signal
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Sequence

from ._paths import reject_symlink_components
from .evidence import canonical_json_sha256, task_fingerprint
from .reporting import MAX_RESULT_BYTES
from .schema import BenchmarkTask
from .scoring import CheckResult, safe_artifact_path, score_task
from .telemetry import AgentTelemetry, load_agent_telemetry

RESULT_SCHEMA_VERSION = 1
MAX_CAPTURED_LOG_BYTES = 8 * 1024 * 1024
MAX_ARTIFACT_HASH_BYTES = 256 * 1024 * 1024
MAX_COMMAND_ARGS = 256
MAX_COMMAND_ARG_CHARS = 16 * 1024
MAX_COMMAND_TOTAL_CHARS = 256 * 1024


@dataclass(frozen=True)
class ArtifactRecord:
    path: str
    size_bytes: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkResult:
    result_schema_version: int
    run_id: str
    task_id: str
    domain: str
    status: str
    exit_code: int | None
    timed_out: bool
    error: str | None
    started_at: str
    duration_seconds: float
    command: tuple[str, ...]
    artifacts: tuple[ArtifactRecord, ...]
    checks: tuple[CheckResult, ...]
    stdout_path: str
    stderr_path: str
    stdout_truncated: bool
    stderr_truncated: bool
    python_version: str
    platform: str
    evaluator_version: str
    task_sha256: str
    request_sha256: str
    failure_taxonomy: tuple[str, ...]
    telemetry: AgentTelemetry | None

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["command"] = list(self.command)
        payload["artifacts"] = [item.to_dict() for item in self.artifacts]
        payload["checks"] = [item.to_dict() for item in self.checks]
        payload["failure_taxonomy"] = list(self.failure_taxonomy)
        payload["telemetry"] = self.telemetry.to_dict() if self.telemetry else None
        payload["passed"] = self.passed
        return payload


def _agent_request_payload(task: BenchmarkTask) -> dict[str, Any]:
    """Return the agent-visible projection; evaluator gold/check expectations stay private."""
    payload = task.to_dict()
    payload.pop("checks", None)
    return payload


def _failure_taxonomy(status: str, checks: tuple[CheckResult, ...]) -> tuple[str, ...]:
    if status == "passed":
        return ()
    fixed = {
        "launch_error": "launch_error",
        "timeout": "timeout",
        "agent_error": "agent_nonzero_exit",
        "telemetry_error": "invalid_telemetry",
    }
    if status in fixed:
        return (fixed[status],)
    categories: list[str] = []
    for check in checks:
        if check.passed:
            continue
        if "symlink" in check.detail or "escapes output directory" in check.detail:
            categories.append("artifact_path_violation")
        elif check.name.startswith("artifact_exists:") and "missing" in check.detail:
            categories.append("expected_artifact_missing")
        elif check.name.startswith("artifact_evidence:"):
            categories.append("artifact_evidence_unrecordable")
        else:
            categories.append("evaluator_check_mismatch")
    if not categories:
        categories.append("unclassified_evaluation_failure")
    return tuple(dict.fromkeys(categories))


def _package_version() -> str:
    from . import __version__

    return __version__


def _sha256(path: Path) -> str:
    stat = path.stat()
    if stat.st_size > MAX_ARTIFACT_HASH_BYTES:
        raise ValueError(f"artifact exceeds hash byte limit ({MAX_ARTIFACT_HASH_BYTES})")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_records(
    task: BenchmarkTask, artifact_root: Path
) -> tuple[tuple[ArtifactRecord, ...], tuple[CheckResult, ...]]:
    records: list[ArtifactRecord] = []
    evidence_checks: list[CheckResult] = []
    for relative in task.expected_artifacts:
        try:
            candidate = safe_artifact_path(artifact_root, relative)
        except ValueError:
            # The normal scorer already reports path/symlink failures.
            continue
        if not candidate.is_file():
            continue
        label = f"artifact_evidence:{relative}"
        try:
            size = candidate.stat().st_size
            digest = _sha256(candidate)
        except (OSError, ValueError) as exc:
            evidence_checks.append(
                CheckResult(
                    label,
                    False,
                    f"could not record bounded artifact evidence: {exc}",
                )
            )
            continue
        records.append(ArtifactRecord(relative, size, digest))
        evidence_checks.append(
            CheckResult(label, True, "size and SHA-256 recorded")
        )
    return tuple(records), tuple(evidence_checks)


def _minimal_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    allow = (
        "PATH",
        "HOME",
        "USERPROFILE",
        "TMPDIR",
        "TEMP",
        "TMP",
        "SYSTEMROOT",
        "WINDIR",
    )
    env = {key: value for key, value in os.environ.items() if key in allow}
    if extra:
        env.update(extra)
    return env


def _copy_stream(
    stream: BinaryIO,
    destination: BinaryIO,
    limit: int,
    state: dict[str, bool],
    key: str,
) -> None:
    written = 0
    try:
        while True:
            chunk = stream.read(65536)
            if not chunk:
                return
            if written < limit:
                remaining = limit - written
                destination.write(chunk[:remaining])
                destination.flush()
                written += min(len(chunk), remaining)
                if len(chunk) > remaining:
                    state[key] = True
            else:
                state[key] = True
    finally:
        try:
            stream.close()
        except OSError:
            pass


def _kill_process_group(pgid: int, signal_number: int) -> None:
    """Call the POSIX-only process-group primitive without a Windows type error."""
    killpg = getattr(os, "killpg", None)
    if callable(killpg):
        killpg(pgid, signal_number)


def _terminate_residual_posix_group(pgid: int) -> None:
    """Terminate descendants that remain in the agent process group after its leader exits."""
    if os.name != "posix":
        return
    try:
        _kill_process_group(pgid, 0)
    except OSError:
        return
    try:
        _kill_process_group(pgid, signal.SIGTERM)
    except OSError:
        return
    deadline = time.monotonic() + 0.5
    while time.monotonic() < deadline:
        try:
            _kill_process_group(pgid, 0)
        except OSError:
            return
        time.sleep(0.02)
    try:
        _kill_process_group(pgid, int(getattr(signal, "SIGKILL", 9)))
    except OSError:
        # The process group may have exited between the liveness check and KILL.
        pass


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            _kill_process_group(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.wait(timeout=3)
        return
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        if os.name == "posix":
            _kill_process_group(process.pid, int(getattr(signal, "SIGKILL", 9)))
        else:
            process.kill()
    except OSError:
        # The process may have exited between terminate escalation attempts.
        pass
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        # A process that survives SIGKILL/kill is an OS-level failure. The caller
        # will still report timeout; no further portable escalation exists here.
        pass


def _run_bounded(
    command: Sequence[str],
    *,
    cwd: Path,
    env: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
    timeout: float,
) -> tuple[int | None, bool, str | None, bool, bool]:
    state = {"stdout": False, "stderr": False}
    try:
        process = subprocess.Popen(
            list(command),
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            start_new_session=(os.name == "posix"),
        )
    except OSError as exc:
        stderr_path.write_text(
            f"reprojudge launch error: {exc}\n", encoding="utf-8"
        )
        stdout_path.write_bytes(b"")
        return None, False, str(exc), False, False

    assert process.stdout is not None and process.stderr is not None
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        threads = [
            threading.Thread(
                target=_copy_stream,
                args=(
                    process.stdout,
                    stdout,
                    MAX_CAPTURED_LOG_BYTES,
                    state,
                    "stdout",
                ),
                daemon=True,
            ),
            threading.Thread(
                target=_copy_stream,
                args=(
                    process.stderr,
                    stderr,
                    MAX_CAPTURED_LOG_BYTES,
                    state,
                    "stderr",
                ),
                daemon=True,
            ),
        ]
        for thread in threads:
            thread.start()
        timed_out = False
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            _terminate_process_tree(process)
        finally:
            # An agent that exits successfully may still leave descendants in its
            # process group. They must not mutate artifacts while the evaluator
            # scores/hashes them. A child that deliberately creates a new session
            # can escape this application-level control and requires OS isolation.
            _terminate_residual_posix_group(process.pid)
        for thread in threads:
            thread.join(timeout=3)
        # Defensive close for unusual descendants that inherited a pipe and kept
        # it open after the evaluated process exited or was terminated.
        if threads[0].is_alive():
            try:
                process.stdout.close()
            except OSError:
                # A descendant may already have closed the inherited pipe.
                pass
        if threads[1].is_alive():
            try:
                process.stderr.close()
            except OSError:
                # A descendant may already have closed the inherited pipe.
                pass
        for thread in threads:
            thread.join(timeout=1)
        return (
            process.returncode,
            timed_out,
            None,
            state["stdout"],
            state["stderr"],
        )


def run_task(
    task: BenchmarkTask,
    command: Sequence[str],
    *,
    output_root: Path,
    working_directory: Path | None = None,
    inherit_environment: bool = False,
) -> tuple[BenchmarkResult, Path]:
    if (
        not command
        or len(command) > MAX_COMMAND_ARGS
        or any(
            not isinstance(item, str)
            or not item
            or len(item) > MAX_COMMAND_ARG_CHARS
            or "\x00" in item
            for item in command
        )
        or sum(len(item) for item in command if isinstance(item, str))
        > MAX_COMMAND_TOTAL_CHARS
    ):
        raise ValueError(
            "command must contain 1-"
            f"{MAX_COMMAND_ARGS} bounded non-empty arguments with at most "
            f"{MAX_COMMAND_TOTAL_CHARS} total characters"
        )

    reject_symlink_components(output_root, "output root")
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:12]
    run_dir = output_root / task.task_id / run_id
    artifact_dir = run_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=False)

    request_path = run_dir / "request.json"
    agent_request = _agent_request_payload(task)
    request_path.write_text(
        json.dumps(agent_request, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    stdout_path = run_dir / "stdout.log"
    stderr_path = run_dir / "stderr.log"
    telemetry_path = run_dir / "agent-telemetry.json"

    env_extra = {
        "REPROJUDGE_RUN_ID": run_id,
        "REPROJUDGE_TASK_ID": task.task_id,
        "REPROJUDGE_TASK_MANIFEST": str(request_path),
        "REPROJUDGE_OUTPUT_DIR": str(artifact_dir),
        "REPROJUDGE_TELEMETRY_PATH": str(telemetry_path),
    }
    env = os.environ.copy() if inherit_environment else _minimal_environment()
    env.update(env_extra)
    cwd = (working_directory or Path.cwd()).resolve()
    if not cwd.is_dir():
        raise ValueError(f"working directory does not exist: {cwd}")

    started = datetime.now(timezone.utc)
    monotonic_start = time.monotonic()
    exit_code, timed_out, launch_error, stdout_truncated, stderr_truncated = (
        _run_bounded(
            command,
            cwd=cwd,
            env=env,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            timeout=task.timeout_seconds,
        )
    )
    duration = round(time.monotonic() - monotonic_start, 6)

    telemetry: AgentTelemetry | None = None
    telemetry_error: str | None = None
    try:
        telemetry = load_agent_telemetry(telemetry_path)
    except ValueError as exc:
        telemetry_error = str(exc)

    score_checks = score_task(task, artifact_dir)
    artifacts, evidence_checks = _artifact_records(task, artifact_dir)
    checks = score_checks + evidence_checks
    check_passed = all(item.passed for item in checks)
    if launch_error is not None:
        status = "launch_error"
    elif timed_out:
        status = "timeout"
    elif exit_code != 0:
        status = "agent_error"
    elif telemetry_error is not None:
        status = "telemetry_error"
    elif check_passed:
        status = "passed"
    else:
        status = "failed"

    result = BenchmarkResult(
        result_schema_version=RESULT_SCHEMA_VERSION,
        run_id=run_id,
        task_id=task.task_id,
        domain=task.domain,
        status=status,
        exit_code=exit_code,
        timed_out=timed_out,
        error=launch_error or telemetry_error,
        started_at=started.isoformat(),
        duration_seconds=duration,
        command=tuple(command),
        artifacts=artifacts,
        checks=checks,
        stdout_path=str(stdout_path.relative_to(run_dir)),
        stderr_path=str(stderr_path.relative_to(run_dir)),
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        evaluator_version=_package_version(),
        task_sha256=task_fingerprint(task),
        request_sha256=canonical_json_sha256(agent_request),
        failure_taxonomy=_failure_taxonomy(status, checks),
        telemetry=telemetry,
    )
    rendered = (
        json.dumps(result.to_dict(), indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")
    if len(rendered) > MAX_RESULT_BYTES:
        raise RuntimeError(
            "internal result-size invariant exceeded; this is an evaluator bug"
        )
    (run_dir / "result.json").write_bytes(rendered)
    return result, run_dir
