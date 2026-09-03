from __future__ import annotations

import sys
from pathlib import Path

import pytest

from reprojudge.cli import main
from reprojudge.schema import parse_task
from reprojudge.scoring import score_task


def test_task_id_cannot_escape_run_directory():
    with pytest.raises(ValueError, match="task_id must match"):
        parse_task({
            "task_id": "../escape",
            "domain": "demo",
            "paper": "synthetic:test",
            "expected_artifacts": ["metrics.json"],
        })


def test_symlink_artifact_escape_is_a_scoring_failure(tmp_path):
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text('{"value": 1}', encoding="utf-8")
    try:
        (artifact_root / "metrics.json").symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    task = parse_task({
        "task_id": "safe-task",
        "domain": "demo",
        "paper": "synthetic:test",
        "expected_artifacts": ["metrics.json"],
    })
    results = score_task(task, artifact_root)
    assert len(results) == 1
    assert results[0].passed is False
    assert "escapes output directory" in results[0].detail


def test_documented_demo_command_runs_end_to_end(tmp_path):
    root = Path(__file__).resolve().parents[1]
    task = root / "examples" / "tasks" / "demo-task.json"
    agent = root / "examples" / "demo_agent.py"
    exit_code = main([
        "run",
        str(task),
        "--output",
        str(tmp_path / "runs"),
        "--",
        sys.executable,
        str(agent),
    ])
    assert exit_code == 0
    assert len(list((tmp_path / "runs").rglob("result.json"))) == 1
