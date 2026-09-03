from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from reprojudge.runner import run_task
from reprojudge.schema import parse_task
from reprojudge.telemetry import AgentTelemetry

ROOT = Path(__file__).resolve().parents[1]


def _schema(name: str) -> dict:
    payload = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(payload)
    return payload


def test_published_schemas_are_valid_draft_2020_12():
    for name in (
        "task-v1.schema.json",
        "result-v1.schema.json",
        "agent-telemetry-v1.schema.json",
    ):
        _schema(name)


def test_task_and_result_match_published_schemas(tmp_path):
    task = parse_task(
        {
            "schema_version": 1,
            "task_id": "schema-roundtrip",
            "domain": "demo",
            "paper": "synthetic:test",
            "expected_artifacts": ["metrics.json"],
            "checks": [
                {
                    "type": "json_numeric",
                    "artifact": "metrics.json",
                    "json_path": "value",
                    "target": 1.0,
                }
            ],
        }
    )
    Draft202012Validator(_schema("task-v1.schema.json")).validate(task.to_dict())
    code = (
        "import json,os,pathlib;"
        "p=pathlib.Path(os.environ['REPROJUDGE_OUTPUT_DIR']);"
        "(p/'metrics.json').write_text(json.dumps({'value':1.0}))"
    )
    result, run_dir = run_task(
        task, [sys.executable, "-c", code], output_root=tmp_path
    )
    Draft202012Validator(_schema("result-v1.schema.json")).validate(result.to_dict())
    request = json.loads((run_dir / "request.json").read_text(encoding="utf-8"))
    Draft202012Validator(_schema("task-v1.schema.json")).validate(request)
    assert "checks" not in request


def _minimal_result(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "result_schema_version": 1,
        "run_id": "0123456789ab",
        "task_id": "schema-result",
        "domain": "demo",
        "status": "passed",
        "duration_seconds": 0.1,
        "command": ["python"],
        "artifacts": [],
        "checks": [],
        "passed": True,
        "timed_out": False,
    }
    payload.update(overrides)
    return payload


def test_result_schema_rejects_status_passed_inconsistency():
    validator = Draft202012Validator(_schema("result-v1.schema.json"))
    with pytest.raises(ValidationError):
        validator.validate(_minimal_result(status="failed", passed=True))


def test_result_schema_rejects_oversized_check_detail():
    validator = Draft202012Validator(_schema("result-v1.schema.json"))
    payload = _minimal_result(
        checks=[{"name": "json_equals:x", "passed": False, "detail": "x" * 4097}],
        status="failed",
        passed=False,
    )
    with pytest.raises(ValidationError):
        validator.validate(payload)


def test_result_schema_keeps_historical_null_telemetry_compatibility():
    validator = Draft202012Validator(_schema("result-v1.schema.json"))
    payload = _minimal_result(
        telemetry={
            "agent_name": None,
            "agent_version": None,
            "token_usage": None,
            "model_cost_usd": None,
            "interventions": [],
        }
    )
    validator.validate(payload)


def test_canonical_telemetry_matches_published_schema():
    payload = AgentTelemetry(
        agent_name="agent",
        agent_version="1.2",
        model="model",
        provider="provider",
        token_usage=12,
        model_cost_usd=0.25,
        interventions=("repo_override",),
    ).to_dict()
    Draft202012Validator(_schema("agent-telemetry-v1.schema.json")).validate(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"agent_name": None},
        {"token_usage": None},
        {"model_cost_usd": None},
        {"agent_name": "   "},
        {"agent_name": "agent\nspoof"},
        {"interventions": ["override\tspoof"]},
    ],
)
def test_telemetry_schema_rejects_runtime_invalid_values(payload: dict[str, object]):
    validator = Draft202012Validator(_schema("agent-telemetry-v1.schema.json"))
    with pytest.raises(ValidationError):
        validator.validate(payload)


@pytest.mark.parametrize(
    "artifact",
    [
        "../escape.json",
        "nested/../../escape.json",
        "nested\n/../escape.json",
        "/absolute.json",
        r"\absolute.json",
        "~/.secret",
    ],
)
def test_task_schema_rejects_runtime_unsafe_artifact_paths(artifact: str):
    payload = {
        "schema_version": 1,
        "task_id": "unsafe-schema-path",
        "domain": "demo",
        "paper": "synthetic:test",
        "expected_artifacts": [artifact],
    }
    validator = Draft202012Validator(_schema("task-v1.schema.json"))
    with pytest.raises(ValidationError):
        validator.validate(payload)


def test_task_schema_rejects_unsafe_check_artifact_path():
    payload = {
        "schema_version": 1,
        "task_id": "unsafe-check-path",
        "domain": "demo",
        "paper": "synthetic:test",
        "expected_artifacts": ["metrics.json"],
        "checks": [
            {
                "type": "artifact_exists",
                "artifact": "../metrics.json",
            }
        ],
    }
    validator = Draft202012Validator(_schema("task-v1.schema.json"))
    with pytest.raises(ValidationError):
        validator.validate(payload)


@pytest.mark.parametrize(
    "artifact",
    ["C:/absolute.json", "C:relative.json", "foo/./bar.json", "foo//bar.json", "./foo.json", "foo/"],
)
def test_runtime_and_schema_reject_same_noncanonical_artifact_paths(artifact: str):
    payload = {
        "schema_version": 1,
        "task_id": "parity-path",
        "domain": "demo",
        "paper": "synthetic:test",
        "expected_artifacts": [artifact],
    }
    with pytest.raises(ValueError):
        parse_task(payload)
    with pytest.raises(ValidationError):
        Draft202012Validator(_schema("task-v1.schema.json")).validate(payload)


def test_runtime_and_schema_share_timeout_lower_bound():
    payload = {
        "schema_version": 1,
        "task_id": "parity-timeout",
        "domain": "demo",
        "paper": "synthetic:test",
        "expected_artifacts": [],
        "timeout_seconds": 0.0000001,
    }
    with pytest.raises(ValueError):
        parse_task(payload)
    with pytest.raises(ValidationError):
        Draft202012Validator(_schema("task-v1.schema.json")).validate(payload)


@pytest.mark.parametrize(
    "field,value",
    [
        ("domain", "   "),
        ("domain", "demo\x00spoof"),
        ("paper", "\n\t"),
        ("paper", "paper\x00spoof"),
        ("tags", ["   "]),
        ("tags", ["tag\x00spoof"]),
    ],
)
def test_task_schema_rejects_runtime_invalid_core_strings(field: str, value: object):
    payload = {
        "schema_version": 1,
        "task_id": "invalid-core-string",
        "domain": "demo",
        "paper": "synthetic:test",
        "expected_artifacts": [],
    }
    payload[field] = value
    validator = Draft202012Validator(_schema("task-v1.schema.json"))
    with pytest.raises(ValidationError):
        validator.validate(payload)


def test_task_schema_allows_multiline_nonempty_text_when_runtime_does():
    payload = {
        "schema_version": 1,
        "task_id": "multiline-text",
        "domain": "\n demo \n",
        "paper": "paper\nrevision",
        "expected_artifacts": [],
        "checks": [],
    }
    validator = Draft202012Validator(_schema("task-v1.schema.json"))
    validator.validate(payload)
    task = parse_task(payload)
    assert task.domain == "demo"
    assert task.paper == "paper\nrevision"


def test_task_schema_rejects_runtime_invalid_metadata_key():
    payload = {
        "schema_version": 1,
        "task_id": "invalid-metadata-key",
        "domain": "demo",
        "paper": "synthetic:test",
        "expected_artifacts": [],
        "metadata": {"bad\x00key": 1},
    }
    validator = Draft202012Validator(_schema("task-v1.schema.json"))
    with pytest.raises(ValidationError):
        validator.validate(payload)
