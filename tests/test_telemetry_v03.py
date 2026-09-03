from __future__ import annotations

import json
from pathlib import Path

import pytest

from reprojudge.telemetry import AgentTelemetry, load_agent_telemetry


def test_load_valid_telemetry(tmp_path: Path):
    path = tmp_path / "telemetry.json"
    path.write_text(
        json.dumps(
            {
                "agent_name": "agent",
                "agent_version": "1.2",
                "token_usage": 12,
                "model_cost_usd": 0.25,
                "interventions": ["repo_override"],
            }
        ),
        encoding="utf-8",
    )
    value = load_agent_telemetry(path)
    assert value is not None
    assert value.token_usage == 12
    assert value.interventions == ("repo_override",)


def test_missing_telemetry_is_none(tmp_path: Path):
    assert load_agent_telemetry(tmp_path / "missing.json") is None


def test_reject_unknown_telemetry_key(tmp_path: Path):
    path = tmp_path / "telemetry.json"
    path.write_text('{"secret":"x"}', encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        load_agent_telemetry(path)


def test_reject_negative_cost(tmp_path: Path):
    path = tmp_path / "telemetry.json"
    path.write_text('{"model_cost_usd":-1}', encoding="utf-8")
    with pytest.raises(ValueError, match="non-negative"):
        load_agent_telemetry(path)


@pytest.mark.parametrize("field", ["agent_name", "agent_version", "model", "provider"])
def test_reject_explicit_null_text_field(tmp_path: Path, field: str):
    path = tmp_path / "telemetry.json"
    path.write_text(json.dumps({field: None}), encoding="utf-8")
    with pytest.raises(ValueError, match="must be omitted"):
        load_agent_telemetry(path)


@pytest.mark.parametrize("field", ["token_usage", "model_cost_usd"])
def test_reject_explicit_null_numeric_field(tmp_path: Path, field: str):
    path = tmp_path / "telemetry.json"
    path.write_text(json.dumps({field: None}), encoding="utf-8")
    with pytest.raises(ValueError, match="must be omitted"):
        load_agent_telemetry(path)


@pytest.mark.parametrize(
    "payload",
    [
        {"agent_name": "agent\nspoof"},
        {"agent_version": "\t1"},
        {"interventions": ["override\rspoof"]},
    ],
)
def test_reject_control_characters(tmp_path: Path, payload: dict[str, object]):
    path = tmp_path / "telemetry.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="control characters"):
        load_agent_telemetry(path)


@pytest.mark.parametrize(
    "payload",
    [
        {"agent_name": 7},
        {"provider": ""},
        {"model": "x" * 257},
        {"interventions": "not-a-list"},
        {"interventions": ["x"] * 65},
        {"token_usage": True},
    ],
)
def test_reject_wrong_types_and_bounds(tmp_path: Path, payload: dict[str, object]):
    path = tmp_path / "telemetry.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        load_agent_telemetry(path)


def test_reject_directory_and_oversized_telemetry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path / "telemetry-dir"
    directory.mkdir()
    with pytest.raises(ValueError, match="regular file"):
        load_agent_telemetry(directory)

    path = tmp_path / "telemetry.json"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("reprojudge.telemetry.MAX_TELEMETRY_BYTES", 1)
    with pytest.raises(ValueError, match="exceeds"):
        load_agent_telemetry(path)


@pytest.mark.parametrize(
    "raw",
    [
        b"\xff",
        b"{",
        b"[]",
        b'{"model_cost_usd":NaN}',
    ],
)
def test_reject_invalid_utf8_json_shape_and_nonfinite_numbers(
    tmp_path: Path, raw: bytes
) -> None:
    path = tmp_path / "telemetry.json"
    path.write_bytes(raw)
    with pytest.raises(ValueError, match="invalid agent telemetry|must be an object|non-finite"):
        load_agent_telemetry(path)


def test_canonical_result_telemetry_includes_present_optional_scalars():
    payload = AgentTelemetry(
        agent_name="agent",
        agent_version="1",
        model="model",
        provider="provider",
        token_usage=3,
        model_cost_usd=0.5,
        interventions=("review",),
    ).to_dict()
    assert payload == {
        "agent_name": "agent",
        "agent_version": "1",
        "model": "model",
        "provider": "provider",
        "token_usage": 3,
        "model_cost_usd": 0.5,
        "interventions": ["review"],
    }


def test_canonical_result_telemetry_omits_absent_optional_scalars():
    payload = AgentTelemetry(agent_name="agent").to_dict()
    assert payload == {"agent_name": "agent", "interventions": []}
    assert all(value is not None for value in payload.values())
