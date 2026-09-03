from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import pytest

from reprojudge.runner import run_task
from reprojudge.schema import parse_task


def _task(check: dict[str, object] | None = None):
    payload: dict[str, object] = {
        "task_id": "adversarial-output",
        "domain": "test",
        "paper": "synthetic:adversarial",
        "expected_artifacts": [] if check is None else ["artifact.bin"],
        "checks": [] if check is None else [check],
        "timeout_seconds": 5.0,
    }
    return parse_task(payload)


def test_invalid_utf8_stdout_and_stderr_are_captured_as_bounded_bytes(tmp_path: Path) -> None:
    code = (
        "import sys;"
        "sys.stdout.buffer.write(b'\\xff\\xfeOUT');"
        "sys.stderr.buffer.write(b'\\x80ERR')"
    )
    result, run_dir = run_task(
        _task(), [sys.executable, "-c", code], output_root=tmp_path
    )
    assert result.passed
    assert (run_dir / "stdout.log").read_bytes() == b"\xff\xfeOUT"
    assert (run_dir / "stderr.log").read_bytes() == b"\x80ERR"


def test_bounded_stderr_is_truncated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("reprojudge.runner.MAX_CAPTURED_LOG_BYTES", 64)
    result, run_dir = run_task(
        _task(),
        [sys.executable, "-c", "import sys;sys.stderr.write('e'*1000)"],
        output_root=tmp_path,
    )
    assert result.passed
    assert result.stderr_truncated
    assert (run_dir / "stderr.log").stat().st_size == 64


@pytest.mark.parametrize("raw", ["{", "[]", '{"value":NaN}', '{"value":Infinity}'])
def test_malformed_or_nonfinite_json_artifact_fails_closed(tmp_path: Path, raw: str) -> None:
    task = _task(
        {
            "type": "json_equals",
            "artifact": "artifact.bin",
            "json_path": "value",
            "expected": 1,
        }
    )
    code = (
        "import os,pathlib;"
        "p=pathlib.Path(os.environ['REPROJUDGE_OUTPUT_DIR'])/'artifact.bin';"
        f"p.write_text({raw!r}, encoding='utf-8')"
    )
    result, _ = run_task(task, [sys.executable, "-c", code], output_root=tmp_path)
    assert result.status == "failed"
    assert any(
        not check.passed and "could not read JSON value" in check.detail
        for check in result.checks
    )


def test_missing_json_field_fails_closed(tmp_path: Path) -> None:
    task = _task(
        {
            "type": "json_equals",
            "artifact": "artifact.bin",
            "json_path": "required.value",
            "expected": 1,
        }
    )
    code = (
        "import os,pathlib;"
        "p=pathlib.Path(os.environ['REPROJUDGE_OUTPUT_DIR'])/'artifact.bin';"
        "p.write_text('{}', encoding='utf-8')"
    )
    result, _ = run_task(task, [sys.executable, "-c", code], output_root=tmp_path)
    assert result.status == "failed"
    assert "evaluator_check_mismatch" in result.failure_taxonomy


def test_wrong_artifact_hash_fails_closed(tmp_path: Path) -> None:
    expected = hashlib.sha256(b"expected").hexdigest()
    task = _task(
        {
            "type": "file_sha256",
            "artifact": "artifact.bin",
            "sha256": expected,
        }
    )
    code = (
        "import os,pathlib;"
        "p=pathlib.Path(os.environ['REPROJUDGE_OUTPUT_DIR'])/'artifact.bin';"
        "p.write_bytes(b'actual')"
    )
    result, _ = run_task(task, [sys.executable, "-c", code], output_root=tmp_path)
    assert result.status == "failed"
    check = next(item for item in result.checks if item.name.startswith("file_sha256:"))
    assert not check.passed
    assert expected in check.detail


def test_duplicate_declared_artifacts_are_rejected_before_execution() -> None:
    with pytest.raises(ValueError, match="must not contain duplicates"):
        parse_task(
            {
                "task_id": "duplicate-artifacts",
                "domain": "test",
                "paper": "synthetic:duplicate",
                "expected_artifacts": ["x.json", "x.json"],
            }
        )


def test_minimal_environment_does_not_leak_parent_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("REPROJUDGE_SECRET_SENTINEL", "must-not-leak")
    task = parse_task(
        {
            "task_id": "environment-boundary",
            "domain": "test",
            "paper": "synthetic:environment",
            "expected_artifacts": ["artifact.bin"],
            "checks": [
                {
                    "type": "json_equals",
                    "artifact": "artifact.bin",
                    "json_path": "leaked",
                    "expected": False,
                }
            ],
        }
    )
    code = (
        "import json,os,pathlib;"
        "p=pathlib.Path(os.environ['REPROJUDGE_OUTPUT_DIR'])/'artifact.bin';"
        "p.write_text(json.dumps({'leaked':'REPROJUDGE_SECRET_SENTINEL' in os.environ}))"
    )
    result, _ = run_task(task, [sys.executable, "-c", code], output_root=tmp_path)
    assert result.passed


def test_working_directory_output_is_not_mistaken_for_declared_evidence(tmp_path: Path) -> None:
    cwd = tmp_path / "external-cwd"
    cwd.mkdir()
    task = _task(
        {"type": "artifact_exists", "artifact": "artifact.bin"}
    )
    result, _ = run_task(
        task,
        [sys.executable, "-c", "from pathlib import Path;Path('artifact.bin').write_bytes(b'x')"],
        output_root=tmp_path / "runs",
        working_directory=cwd,
    )
    assert (cwd / "artifact.bin").is_file()
    assert result.status == "failed"
    assert "expected_artifact_missing" in result.failure_taxonomy


@pytest.mark.skipif(os.name != "posix", reason="POSIX signal semantics")
def test_timeout_escalates_when_agent_ignores_sigterm(tmp_path: Path) -> None:
    task = parse_task(
        {
            "task_id": "ignore-sigterm",
            "domain": "test",
            "paper": "synthetic:signals",
            "expected_artifacts": [],
            "timeout_seconds": 0.05,
        }
    )
    code = "import signal,time;signal.signal(signal.SIGTERM, signal.SIG_IGN);time.sleep(10)"
    result, _ = run_task(task, [sys.executable, "-c", code], output_root=tmp_path)
    assert result.status == "timeout"
    assert result.timed_out
