from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from reprojudge.reporting import MAX_RESULT_BYTES, load_results
from reprojudge.runner import MAX_COMMAND_ARG_CHARS, run_task
from reprojudge.schema import parse_task
from reprojudge.scoring import MAX_CHECK_DETAIL_CHARS


def task(**overrides):
    payload = {
        "task_id": "runner-test",
        "domain": "test",
        "paper": "synthetic:runner",
        "expected_artifacts": ["metrics.json"],
        "checks": [
            {
                "type": "json_numeric",
                "artifact": "metrics.json",
                "json_path": "value",
                "target": 1.0,
                "abs_tol": 0.0,
            }
        ],
        "timeout_seconds": 5,
    }
    payload.update(overrides)
    return parse_task(payload)


def test_run_captures_evidence_and_telemetry(tmp_path: Path):
    code = r"""
import json, os
from pathlib import Path
out=Path(os.environ['REPROJUDGE_OUTPUT_DIR'])
out.mkdir(parents=True, exist_ok=True)
(out/'metrics.json').write_text('{"value":1.0}\n')
Path(os.environ['REPROJUDGE_TELEMETRY_PATH']).write_text(json.dumps({
  "agent_name":"fixture","agent_version":"1","token_usage":7,"model_cost_usd":0.01,"interventions":[]
}))
"""
    result, run_dir = run_task(
        task(), [sys.executable, "-c", code], output_root=tmp_path
    )
    assert result.passed
    assert result.telemetry is not None and result.telemetry.token_usage == 7
    assert len(result.task_sha256) == 64
    payload = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    assert payload["result_schema_version"] == 1
    assert payload["evaluator_version"] == "0.3.0"


def test_invalid_telemetry_fails_closed(tmp_path: Path):
    code = r"""
import os
from pathlib import Path
out=Path(os.environ['REPROJUDGE_OUTPUT_DIR'])
(out/'metrics.json').write_text('{"value":1.0}')
Path(os.environ['REPROJUDGE_TELEMETRY_PATH']).write_text('{"token_usage":-1}')
"""
    result, _ = run_task(
        task(), [sys.executable, "-c", code], output_root=tmp_path
    )
    assert result.status == "telemetry_error"


def test_timeout_is_explicit(tmp_path: Path):
    sleepy = task(expected_artifacts=[], checks=[], timeout_seconds=0.05)
    result, _ = run_task(
        sleepy,
        [sys.executable, "-c", "import time; time.sleep(2)"],
        output_root=tmp_path,
    )
    assert result.status == "timeout"
    assert result.timed_out


def test_agent_error_is_explicit(tmp_path: Path):
    empty = task(expected_artifacts=[], checks=[])
    result, _ = run_task(
        empty,
        [sys.executable, "-c", "raise SystemExit(7)"],
        output_root=tmp_path,
    )
    assert result.status == "agent_error"
    assert result.exit_code == 7


def test_launch_error_is_recorded(tmp_path: Path):
    empty = task(expected_artifacts=[], checks=[])
    result, run_dir = run_task(
        empty,
        ["definitely-not-a-real-command-reprojudge"],
        output_root=tmp_path,
    )
    assert result.status == "launch_error"
    assert "launch error" in (run_dir / "stderr.log").read_text(encoding="utf-8")


def test_bounded_stdout_is_truncated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("reprojudge.runner.MAX_CAPTURED_LOG_BYTES", 64)
    empty = task(expected_artifacts=[], checks=[])
    result, run_dir = run_task(
        empty,
        [sys.executable, "-c", "print('x'*1000)"],
        output_root=tmp_path,
    )
    assert result.passed
    assert result.stdout_truncated
    assert (run_dir / "stdout.log").stat().st_size == 64


def test_symlink_artifact_is_not_hashed(tmp_path: Path):
    outside = tmp_path / "outside.json"
    outside.write_text('{"value":1}', encoding="utf-8")
    probe_target = tmp_path / "symlink-probe-target"
    probe = tmp_path / "symlink-probe"
    try:
        probe.symlink_to(probe_target)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    code = f"""
import os
from pathlib import Path
out=Path(os.environ['REPROJUDGE_OUTPUT_DIR'])
(out/'metrics.json').symlink_to(Path({str(outside)!r}))
"""
    result, _ = run_task(
        task(),
        [sys.executable, "-c", code],
        output_root=tmp_path / "runs",
    )
    assert result.status == "failed"
    assert result.artifacts == ()


def test_rejects_aggregate_command_that_could_overflow_result_contract(
    tmp_path: Path,
):
    empty = task(expected_artifacts=[], checks=[])
    command = ["echo"] + ["x" * MAX_COMMAND_ARG_CHARS] * 17
    assert all(len(item) <= MAX_COMMAND_ARG_CHARS for item in command)
    with pytest.raises(ValueError, match="total characters"):
        run_task(empty, command, output_root=tmp_path)


def test_large_json_mismatch_keeps_result_bounded_and_reloadable(tmp_path: Path):
    bounded_task = task(
        checks=[
            {
                "type": "json_equals",
                "artifact": "metrics.json",
                "json_path": "value",
                "expected": "expected",
            }
        ]
    )
    code = (
        "import json,os,pathlib;"
        "p=pathlib.Path(os.environ['REPROJUDGE_OUTPUT_DIR']);"
        "(p/'metrics.json').write_text(json.dumps({'value':'x'*(1024*1024)}))"
    )
    result, run_dir = run_task(
        bounded_task,
        [sys.executable, "-c", code],
        output_root=tmp_path / "runs",
    )
    assert result.status == "failed"
    mismatch = next(
        check for check in result.checks if check.name.startswith("json_equals:")
    )
    assert len(mismatch.detail) <= MAX_CHECK_DETAIL_CHARS
    result_path = run_dir / "result.json"
    assert result_path.stat().st_size <= MAX_RESULT_BYTES
    loaded = load_results(tmp_path / "runs")
    assert len(loaded) == 1
    assert loaded[0]["status"] == "failed"
