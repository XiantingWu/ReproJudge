from __future__ import annotations

import csv
import io

import pytest

from reprojudge.leaderboard import (
    build_leaderboard,
    leaderboard_csv,
    leaderboard_markdown,
)
from reprojudge.reporting import summarize


def result(
    status="passed",
    agent="a",
    version="1",
    duration=1.0,
    tokens=0,
    cost=0.0,
    interventions=None,
):
    return {
        "task_id": "t",
        "status": status,
        "duration_seconds": duration,
        "telemetry": {
            "agent_name": agent,
            "agent_version": version,
            "token_usage": tokens,
            "model_cost_usd": cost,
            "interventions": interventions or [],
        },
    }


def test_summary_tracks_cost_tokens_and_interventions():
    summary = summarize(
        [
            result(tokens=10, cost=0.2, interventions=["x"]),
            result(status="failed", tokens=5, cost=0.1),
        ]
    )
    assert summary.total == 2
    assert summary.passed == 1
    assert summary.total_tokens == 15
    assert summary.total_model_cost_usd == 0.3
    assert summary.interventions == 1


def test_leaderboard_groups_agent_versions():
    rows = build_leaderboard(
        [
            result(agent="A", version="1"),
            result(agent="A", version="1", status="failed"),
            result(agent="B", version="2"),
        ]
    )
    assert rows[0]["agent"] == "B"
    assert rows[0]["pass_rate"] == 1.0
    assert rows[1]["runs"] == 2


def test_leaderboard_formats():
    rows = build_leaderboard([result()])
    assert "| Agent |" in leaderboard_markdown(rows)
    assert "agent,version" in leaderboard_csv(rows)


def test_leaderboard_rejects_control_character_identity():
    with pytest.raises(ValueError, match="control characters"):
        build_leaderboard([result(agent="agent\nspoof")])


def test_markdown_escapes_agent_authored_table_and_markup_syntax():
    rows = build_leaderboard([result(agent="[agent](https://example.test)|spoof", version="v*1*")])
    rendered = leaderboard_markdown(rows)
    assert r"\[agent\]\(https://example\.test\)\|spoof" in rendered
    assert r"v\*1\*" in rendered
    assert "| spoof |" not in rendered


def test_csv_prefixes_spreadsheet_formula_identity():
    rows = build_leaderboard([result(agent="=HYPERLINK(\"https://example.test\")", version="+1")])
    rendered = leaderboard_csv(rows)
    parsed = list(csv.DictReader(io.StringIO(rendered)))
    assert parsed[0]["agent"].startswith("'=")
    assert parsed[0]["version"].startswith("'+")
