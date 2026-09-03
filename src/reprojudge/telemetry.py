from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ._paths import reject_symlink_components

MAX_TELEMETRY_BYTES = 64 * 1024
_ALLOWED_KEYS = {
    "agent_name",
    "agent_version",
    "model",
    "provider",
    "token_usage",
    "model_cost_usd",
    "interventions",
}
_TEXT_FIELDS = ("agent_name", "agent_version", "model", "provider")


@dataclass(frozen=True)
class AgentTelemetry:
    agent_name: str | None = None
    agent_version: str | None = None
    model: str | None = None
    provider: str | None = None
    token_usage: int | None = None
    model_cost_usd: float | None = None
    interventions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical telemetry projection used inside result bundles.

        Optional scalar fields are omitted when absent instead of being emitted
        as explicit JSON null. This keeps evaluator-authored telemetry inside
        the same machine-readable contract accepted from agents.
        """
        payload: dict[str, Any] = {"interventions": list(self.interventions)}
        for field in _TEXT_FIELDS:
            value = getattr(self, field)
            if value is not None:
                payload[field] = value
        if self.token_usage is not None:
            payload["token_usage"] = self.token_usage
        if self.model_cost_usd is not None:
            payload["model_cost_usd"] = self.model_cost_usd
        return payload


def _has_control_characters(value: str) -> bool:
    return any(ord(char) < 0x20 or ord(char) == 0x7F for char in value)


def _optional_text(
    value: object,
    field: str,
    limit: int = 256,
    *,
    present: bool = False,
) -> str | None:
    if value is None:
        if present:
            raise ValueError(f"{field} must be omitted or a bounded non-empty string")
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a bounded non-empty string")
    if _has_control_characters(value):
        raise ValueError(
            f"{field} must be a bounded non-empty string without control characters"
        )
    result = value.strip()
    if not result or len(result) > limit:
        raise ValueError(f"{field} must be a bounded non-empty string")
    return result


def load_agent_telemetry(path: Path) -> AgentTelemetry | None:
    reject_symlink_components(path, "agent telemetry")
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file():
        raise ValueError("agent telemetry must be a regular file")
    if path.stat().st_size > MAX_TELEMETRY_BYTES:
        raise ValueError(f"agent telemetry exceeds {MAX_TELEMETRY_BYTES} bytes")
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite telemetry number: {value}")
            ),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid agent telemetry: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("agent telemetry must be an object")
    unknown = sorted(set(payload) - _ALLOWED_KEYS)
    if unknown:
        raise ValueError("unsupported agent telemetry keys: " + ", ".join(unknown))

    token_usage = payload.get("token_usage")
    if "token_usage" in payload and (
        not isinstance(token_usage, int)
        or isinstance(token_usage, bool)
        or token_usage < 0
    ):
        raise ValueError("token_usage must be omitted or a non-negative integer")

    cost = payload.get("model_cost_usd")
    if "model_cost_usd" in payload:
        if (
            not isinstance(cost, (int, float))
            or isinstance(cost, bool)
            or not math.isfinite(float(cost))
            or float(cost) < 0
        ):
            raise ValueError("model_cost_usd must be omitted or a non-negative finite number")
        cost = float(cost)

    raw_interventions = payload.get("interventions", [])
    if not isinstance(raw_interventions, list) or len(raw_interventions) > 64:
        raise ValueError("interventions must be a list with at most 64 entries")
    interventions = tuple(
        _optional_text(item, "intervention", 256, present=True)
        for item in raw_interventions
    )

    return AgentTelemetry(
        agent_name=_optional_text(
            payload.get("agent_name"), "agent_name", present="agent_name" in payload
        ),
        agent_version=_optional_text(
            payload.get("agent_version"),
            "agent_version",
            present="agent_version" in payload,
        ),
        model=_optional_text(payload.get("model"), "model", present="model" in payload),
        provider=_optional_text(
            payload.get("provider"), "provider", present="provider" in payload
        ),
        token_usage=token_usage,
        model_cost_usd=cost,
        interventions=tuple(item for item in interventions if item is not None),
    )
