from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from reprojudge.schema import CheckSpec, parse_task
from reprojudge.scoring import score_check, score_task


def test_text_contains_and_regex(tmp_path: Path):
    (tmp_path / "report.txt").write_text("hello\nseed=42\n", encoding="utf-8")
    contains = score_check(CheckSpec(type="text_contains", artifact="report.txt", contains="hello"), tmp_path)
    regex = score_check(CheckSpec(type="text_regex", artifact="report.txt", pattern=r"seed=\d+"), tmp_path)
    assert contains.passed and regex.passed


def test_file_sha256(tmp_path: Path):
    path = tmp_path / "blob.bin"
    path.write_bytes(b"abc")
    digest = hashlib.sha256(b"abc").hexdigest()
    assert score_check(CheckSpec(type="file_sha256", artifact="blob.bin", sha256=digest), tmp_path).passed


def test_json_numeric_rejects_nonfinite_observed(tmp_path: Path):
    (tmp_path / "metrics.json").write_text('{"x": NaN}', encoding="utf-8")
    result = score_check(
        CheckSpec(type="json_numeric", artifact="metrics.json", json_path="x", target=1.0),
        tmp_path,
    )
    assert not result.passed


def test_programmatic_numeric_check_without_target_fails_closed(tmp_path: Path):
    (tmp_path / "metrics.json").write_text(json.dumps({"x": 1.0}), encoding="utf-8")
    result = score_check(
        CheckSpec(type="json_numeric", artifact="metrics.json", json_path="x"),
        tmp_path,
    )
    assert not result.passed
    assert result.detail == "invalid numeric check specification"


def test_symlink_artifact_fails_closed(tmp_path: Path):
    outside = tmp_path.parent / "outside-reprojudge.txt"
    outside.write_text("secret", encoding="utf-8")
    try:
        (tmp_path / "linked.txt").symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    result = score_check(CheckSpec(type="artifact_exists", artifact="linked.txt"), tmp_path)
    assert not result.passed
    assert "symlink" in result.detail


def test_implicit_existence_check_is_added(tmp_path: Path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    task = parse_task(
        {
            "task_id": "a",
            "domain": "d",
            "paper": "p",
            "expected_artifacts": ["a.txt"],
        }
    )
    results = score_task(task, tmp_path)
    assert len(results) == 1 and results[0].passed
