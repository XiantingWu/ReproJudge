from __future__ import annotations

import json
import sys

from reprojudge.runner import run_task
from reprojudge.schema import parse_task


def task(timeout=5):
    return parse_task({
        "task_id": "runner-demo",
        "domain": "demo",
        "paper": "synthetic:test",
        "expected_artifacts": ["metrics.json"],
        "checks": [{"type": "json_numeric", "artifact": "metrics.json", "json_path": "value", "target": 2.5, "abs_tol": 0.0}],
        "timeout_seconds": timeout,
    })


def test_run_task_records_passing_result(tmp_path):
    code = "import json,os,pathlib;p=pathlib.Path(os.environ['REPROJUDGE_OUTPUT_DIR']);p.mkdir(exist_ok=True);(p/'metrics.json').write_text(json.dumps({'value':2.5}))"
    result, run_dir = run_task(task(), [sys.executable, "-c", code], output_root=tmp_path)
    assert result.status == "passed"
    assert result.passed
    assert result.result_schema_version == 1
    assert result.artifacts[0].sha256
    on_disk = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    assert on_disk["passed"] is True
    assert on_disk["result_schema_version"] == 1


def test_run_task_agent_error(tmp_path):
    result, _ = run_task(task(), [sys.executable, "-c", "raise SystemExit(7)"], output_root=tmp_path)
    assert result.status == "agent_error"
    assert result.exit_code == 7


def test_run_task_timeout(tmp_path):
    result, _ = run_task(task(timeout=0.05), [sys.executable, "-c", "import time; time.sleep(1)"], output_root=tmp_path)
    assert result.status == "timeout"
    assert result.timed_out


def test_run_task_launch_error_is_recorded(tmp_path):
    result, run_dir = run_task(task(), [str(tmp_path / "definitely-missing-agent")], output_root=tmp_path)
    assert result.status == "launch_error"
    assert result.exit_code is None
    assert result.error
    assert (run_dir / "result.json").is_file()


def test_canonical_zero_artifact_task_can_pass(tmp_path):
    canonical = parse_task({
        "schema_version": 1,
        "task_id": "governed-individuation-mechanism-v1",
        "domain": "agent-governance",
        "paper": "2607.04613v1",
        "expected_artifacts": [],
    })
    result, _ = run_task(canonical, [sys.executable, "-c", "pass"], output_root=tmp_path)
    assert result.status == "passed"
    assert result.checks == ()
    assert result.artifacts == ()
