from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts import check_public_identity_hygiene as hygiene

ROOT = Path(__file__).resolve().parents[1]


def test_public_tree_contains_zero_forbidden_identity_matches() -> None:
    ok, failures, total = hygiene.check_public_identity_hygiene(ROOT)
    assert ok, "\n".join(failures[:20])
    assert total == 0


def test_hygiene_gate_fails_closed_when_forbidden_identity_appears(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("canonical repository\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("originally curated under " + "find" + "woods\n", encoding="utf-8")  # forbidden-fixture
    ok, failures, total = hygiene.check_public_identity_hygiene(tmp_path)
    assert not ok
    assert total == 1
    assert "forbidden=private-identity" in failures[0]


def test_hygiene_gate_rejects_personal_path_and_runner_names(tmp_path: Path) -> None:
    personal_path = "/Users/" + "woods" + "/machine"
    runner_name = "reprojudge-" + "ci"
    (tmp_path / "doc.md").write_text(
        "runner " + runner_name + " on " + personal_path + "\n", encoding="utf-8"
    )  # forbidden-fixture
    ok, failures, total = hygiene.check_public_identity_hygiene(tmp_path)
    assert not ok
    assert total == 2


def test_hygiene_gate_accepts_empty_tree(tmp_path: Path) -> None:
    ok, failures, total = hygiene.check_public_identity_hygiene(tmp_path)
    assert ok
    assert total == 0


def test_history_hygiene_script_runs_cleanly_in_cli() -> None:
    if not (ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    head = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if head.returncode != 0:
        pytest.skip("no commits yet in this checkout")
    result = subprocess.run(
        [sys.executable, "scripts/check_git_history_hygiene.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
