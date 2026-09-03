from __future__ import annotations

import json

from reprojudge.schema import parse_task
from reprojudge.scoring import score_task


def test_json_numeric_and_equals(tmp_path):
    (tmp_path / "metrics.json").write_text(json.dumps({"score": 1.00001, "name": "ok"}), encoding="utf-8")
    task = parse_task({
        "task_id": "t",
        "domain": "demo",
        "paper": "synthetic:test",
        "expected_artifacts": ["metrics.json"],
        "checks": [
            {"type": "json_numeric", "artifact": "metrics.json", "json_path": "score", "target": 1.0, "abs_tol": 0.001},
            {"type": "json_equals", "artifact": "metrics.json", "json_path": "name", "expected": "ok"},
        ],
    })
    results = score_task(task, tmp_path)
    assert all(item.passed for item in results)


def test_missing_artifact_fails(tmp_path):
    task = parse_task({"task_id": "t", "domain": "demo", "paper": "synthetic:test", "expected_artifacts": ["missing.json"]})
    results = score_task(task, tmp_path)
    assert len(results) == 1
    assert not results[0].passed
