from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from reprojudge.cli import build_parser, main


def test_validate_cli(tmp_path, capsys):
    path = tmp_path / "task.json"
    path.write_text(
        json.dumps(
            {
                "task_id": "t",
                "domain": "demo",
                "paper": "synthetic:test",
                "expected_artifacts": ["x.json"],
            }
        ),
        encoding="utf-8",
    )
    assert main(["validate", str(path)]) == 0
    assert '"valid": true' in capsys.readouterr().out.lower()


def test_doctor_cli(capsys):
    assert main(["doctor"]) == 0
    assert '"ok": true' in capsys.readouterr().out.lower()


def test_agent_command_is_visible_in_run_help(capsys):
    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args(["run", "--help"])
    assert exc_info.value.code == 0
    assert "MANIFEST -- AGENT ..." in capsys.readouterr().out


def test_init_cli_creates_and_runs_starter_without_overwrite(tmp_path, capsys):
    target = tmp_path / "starter"
    assert main(["init", str(target)]) == 0
    output = capsys.readouterr().out
    assert "created ReproJudge starter" in output

    task = target / "tasks" / "hello-reprojudge.json"
    agent = target / "agent.py"
    assert task.is_file()
    assert agent.is_file()
    assert (target / "README.md").is_file()

    assert main(["validate", str(task)]) == 0
    capsys.readouterr()

    runs = tmp_path / "runs"
    assert (
        main(
            [
                "run",
                str(task),
                "--output",
                str(runs),
                "--",
                sys.executable,
                str(agent),
            ]
        )
        == 0
    )
    assert '"failed": 0' in capsys.readouterr().out

    marker = target / "do-not-overwrite.txt"
    marker.write_text("keep\n", encoding="utf-8")
    assert main(["init", str(target)]) == 2
    assert marker.read_text(encoding="utf-8") == "keep\n"
    assert "refusing to overwrite" in capsys.readouterr().err


def test_readme_quickstart_commands_run_end_to_end(tmp_path, capsys):
    root = Path(__file__).resolve().parents[1]
    target = tmp_path / "my-benchmark"
    assert main(["init", str(target)]) == 0
    capsys.readouterr()

    task = target / "tasks" / "hello-reprojudge.json"
    agent = target / "agent.py"
    runs = tmp_path / "runs"

    assert (
        main(
            [
                "run",
                str(task),
                "--output",
                str(runs),
                "--",
                sys.executable,
                str(agent),
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert main(["summarize", str(runs)]) == 0
    summary_out = capsys.readouterr().out
    assert "passed" in summary_out.lower() or '"passed": 1' in summary_out

    assert main(["leaderboard", str(runs)]) == 0
    board_out = capsys.readouterr().out
    assert "agent" in board_out.lower()

    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "reprojudge init my-benchmark" in readme
    assert "-- python3 agent.py" in readme
    assert "reprojudge summarize runs" in readme
