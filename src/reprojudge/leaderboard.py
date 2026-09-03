from __future__ import annotations

import csv
import html
import io
import math
from collections import defaultdict
from statistics import mean
from typing import Any

_MARKDOWN_SPECIAL = set("\\`*_{}[]()#+-.!|>")
_SPREADSHEET_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _finite_nonnegative(value: object, field: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise ValueError(f"{field} must be a non-negative finite number")
    return float(value)


def _has_control_characters(value: str) -> bool:
    return any(ord(char) < 0x20 or ord(char) == 0x7F for char in value)


def _bounded_identity(value: object, field: str) -> str:
    if value is None:
        return "unknown"
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a bounded non-empty string")
    if _has_control_characters(value):
        raise ValueError(
            f"{field} must be a bounded non-empty string without control characters"
        )
    result = value.strip()
    if not result or len(result) > 256:
        raise ValueError(f"{field} must be a bounded non-empty string")
    return result


def _markdown_cell(value: object) -> str:
    """Render an untrusted label as inert Markdown table text."""
    text = str(value).replace("\r", " ").replace("\n", " ")
    escaped_html = html.escape(text, quote=False)
    return "".join(
        f"\\{char}" if char in _MARKDOWN_SPECIAL else char
        for char in escaped_html
    )


def _spreadsheet_safe_cell(value: object) -> object:
    """Prevent agent-authored labels from becoming spreadsheet formulas."""
    if not isinstance(value, str):
        return value
    stripped = value.lstrip(" ")
    if stripped.startswith(_SPREADSHEET_FORMULA_PREFIXES) or value.startswith(
        ("\t", "\r", "\n")
    ):
        return "'" + value
    return value


def build_leaderboard(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        if not isinstance(result, dict):
            raise ValueError("leaderboard results must be objects")
        status = result.get("status")
        if status not in {
            "passed",
            "failed",
            "agent_error",
            "timeout",
            "launch_error",
            "telemetry_error",
        }:
            raise ValueError("leaderboard result has unsupported status")
        duration = result.get("duration_seconds")
        if duration is not None:
            _finite_nonnegative(duration, "duration_seconds")
        telemetry = result.get("telemetry")
        agent_name = "unknown"
        agent_version = "unknown"
        if telemetry is not None:
            if not isinstance(telemetry, dict):
                raise ValueError("leaderboard telemetry must be an object or null")
            agent_name = _bounded_identity(telemetry.get("agent_name"), "agent_name")
            agent_version = _bounded_identity(
                telemetry.get("agent_version"), "agent_version"
            )
            tokens = telemetry.get("token_usage")
            if tokens is not None and (
                not isinstance(tokens, int) or isinstance(tokens, bool) or tokens < 0
            ):
                raise ValueError("token_usage must be a non-negative integer")
            cost = telemetry.get("model_cost_usd")
            if cost is not None:
                _finite_nonnegative(cost, "model_cost_usd")
            interventions = telemetry.get("interventions")
            if interventions is not None and (
                not isinstance(interventions, list)
                or len(interventions) > 64
                or not all(
                    isinstance(item, str)
                    and item
                    and len(item) <= 256
                    and not _has_control_characters(item)
                    for item in interventions
                )
            ):
                raise ValueError("interventions must be a bounded string list")
        grouped[(agent_name, agent_version)].append(result)

    rows: list[dict[str, Any]] = []
    for (name, version), items in grouped.items():
        passed = sum(item.get("status") == "passed" for item in items)
        durations = [
            _finite_nonnegative(item["duration_seconds"], "duration_seconds")
            for item in items
            if item.get("duration_seconds") is not None
        ]
        tokens = 0
        cost = 0.0
        interventions = 0
        for item in items:
            telemetry = item.get("telemetry")
            if not isinstance(telemetry, dict):
                continue
            token_value = telemetry.get("token_usage")
            if token_value is not None:
                tokens += int(token_value)
            cost_value = telemetry.get("model_cost_usd")
            if cost_value is not None:
                cost += _finite_nonnegative(cost_value, "model_cost_usd")
            raw_interventions = telemetry.get("interventions")
            if isinstance(raw_interventions, list):
                interventions += len(raw_interventions)
        rows.append(
            {
                "agent": name,
                "version": version,
                "runs": len(items),
                "passed": passed,
                "pass_rate": round(passed / len(items), 6),
                "mean_duration_seconds": round(mean(durations), 6)
                if durations
                else 0.0,
                "token_usage": tokens,
                "model_cost_usd": round(cost, 8),
                "interventions": interventions,
            }
        )
    return sorted(
        rows,
        key=lambda row: (-row["pass_rate"], row["agent"], row["version"]),
    )


def leaderboard_markdown(rows: list[dict[str, Any]]) -> str:
    header = (
        "| Agent | Version | Runs | Passed | Pass rate | Mean s | Tokens | Cost USD | Interventions |\n"
        "|---|---|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    body = "".join(
        f"| {_markdown_cell(row['agent'])} | {_markdown_cell(row['version'])} | "
        f"{row['runs']} | {row['passed']} | {row['pass_rate']:.1%} | "
        f"{row['mean_duration_seconds']:.3f} | {row['token_usage']} | "
        f"{row['model_cost_usd']:.6f} | {row['interventions']} |\n"
        for row in rows
    )
    return header + body


def leaderboard_csv(rows: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    fields = [
        "agent",
        "version",
        "runs",
        "passed",
        "pass_rate",
        "mean_duration_seconds",
        "token_usage",
        "model_cost_usd",
        "interventions",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        rendered = dict(row)
        rendered["agent"] = _spreadsheet_safe_cell(rendered.get("agent"))
        rendered["version"] = _spreadsheet_safe_cell(rendered.get("version"))
        writer.writerow(rendered)
    return buffer.getvalue()
