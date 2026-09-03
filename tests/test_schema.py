from __future__ import annotations

import json
import math

import pytest

from reprojudge.schema import MAX_TASK_BYTES, load_task, parse_task


def base_payload():
    return {
        "task_id": "task-1",
        "domain": "demo",
        "paper": "synthetic:test",
        "expected_artifacts": ["metrics.json"],
    }


def test_parse_minimal_task_is_backward_compatible():
    task = parse_task(base_payload())
    assert task.schema_version == 1
    assert task.expected_artifacts == ("metrics.json",)
    assert task.timeout_seconds == 300.0


def test_canonical_integer_schema_and_empty_artifacts_are_supported():
    task = parse_task({
        "schema_version": 1,
        "task_id": "governed-individuation-mechanism-v1",
        "domain": "agent-governance",
        "paper": "2607.04613v1",
        "expected_artifacts": [],
    })
    assert task.schema_version == 1
    assert task.expected_artifacts == ()


def test_rejects_path_traversal():
    payload = base_payload()
    payload["expected_artifacts"] = ["../secret.txt"]
    with pytest.raises(ValueError, match="safe relative path"):
        parse_task(payload)


def test_rejects_unknown_schema_version():
    payload = base_payload()
    payload["schema_version"] = 99
    with pytest.raises(ValueError, match="unsupported schema_version"):
        parse_task(payload)


def test_rejects_string_schema_version():
    payload = base_payload()
    payload["schema_version"] = "1"
    with pytest.raises(ValueError, match="unsupported schema_version"):
        parse_task(payload)


def test_rejects_check_for_undeclared_artifact():
    payload = base_payload()
    payload["checks"] = [{"type": "artifact_exists", "artifact": "other.json"}]
    with pytest.raises(ValueError, match="undeclared"):
        parse_task(payload)


def test_numeric_check_parses_tolerances():
    payload = base_payload()
    payload["checks"] = [{
        "type": "json_numeric",
        "artifact": "metrics.json",
        "json_path": "score",
        "target": 1.0,
        "abs_tol": 0.1,
        "rel_tol": 0.2,
    }]
    task = parse_task(payload)
    assert task.checks[0].abs_tol == 0.1
    assert task.checks[0].rel_tol == 0.2


def test_rejects_non_finite_programmatic_numbers():
    payload = base_payload()
    payload["timeout_seconds"] = math.inf
    with pytest.raises(ValueError, match="finite number"):
        parse_task(payload)


def test_load_task_rejects_non_finite_json(tmp_path):
    path = tmp_path / "task.json"
    path.write_text('{"task_id":"t","domain":"d","paper":"p","expected_artifacts":[],"timeout_seconds":NaN}', encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite JSON number"):
        load_task(path)


def test_load_task_rejects_symlink(tmp_path):
    target = tmp_path / "target.json"
    target.write_text(json.dumps(base_payload()), encoding="utf-8")
    link = tmp_path / "task.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ValueError, match="symlink"):
        load_task(link)


def test_load_task_rejects_oversized_file(tmp_path):
    path = tmp_path / "task.json"
    path.write_bytes(b" " * (MAX_TASK_BYTES + 1))
    with pytest.raises(ValueError, match="exceeds"):
        load_task(path)
