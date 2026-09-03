from __future__ import annotations

import json
from pathlib import Path

import pytest

from reprojudge.schema import parse_task, load_task


def base(**overrides):
    payload = {
        "schema_version": 1,
        "task_id": "case:1",
        "domain": "test",
        "paper": "2607.04613v1",
        "expected_artifacts": ["metrics.json"],
    }
    payload.update(overrides)
    return payload


def test_repo1_style_colon_task_id_is_compatible():
    assert parse_task(base()).task_id == "case:1"


def test_zero_artifact_task_is_valid():
    assert parse_task(base(expected_artifacts=[])).expected_artifacts == ()


def test_reject_duplicate_artifacts():
    with pytest.raises(ValueError, match="duplicates"):
        parse_task(base(expected_artifacts=["a", "a"]))


def test_reject_artifact_traversal():
    with pytest.raises(ValueError, match="safe relative"):
        parse_task(base(expected_artifacts=["../x"]))


def test_text_and_hash_checks_parse():
    digest = "0" * 64
    task = parse_task(
        base(
            expected_artifacts=["report.txt", "blob.bin"],
            checks=[
                {"type": "text_contains", "artifact": "report.txt", "contains": "ok"},
                {"type": "text_regex", "artifact": "report.txt", "pattern": r"seed=\d+"},
                {"type": "file_sha256", "artifact": "blob.bin", "sha256": digest},
            ],
        )
    )
    assert [item.type for item in task.checks] == ["text_contains", "text_regex", "file_sha256"]


def test_reject_bad_regex():
    with pytest.raises(ValueError, match="pattern is invalid"):
        parse_task(
            base(
                checks=[{"type": "text_regex", "artifact": "metrics.json", "pattern": "["}]
            )
        )


def test_reject_bad_sha256():
    with pytest.raises(ValueError, match="64 lowercase"):
        parse_task(
            base(
                checks=[{"type": "file_sha256", "artifact": "metrics.json", "sha256": "abc"}]
            )
        )


def test_reject_unknown_check_type():
    with pytest.raises(ValueError, match="must be one of"):
        parse_task(base(checks=[{"type": "llm_judge", "artifact": "metrics.json"}]))


@pytest.mark.parametrize(
    ("check_type", "valid_fields", "extra_field"),
    [
        ("artifact_exists", {}, {"expected": 1}),
        ("json_equals", {"json_path": "x", "expected": 1}, {"target": 1}),
        ("json_numeric", {"json_path": "x", "target": 1}, {"expected": 1}),
        ("text_contains", {"contains": "ok"}, {"pattern": "ok"}),
        ("text_regex", {"pattern": "ok"}, {"contains": "ok"}),
        ("file_sha256", {"sha256": "0" * 64}, {"json_path": "x"}),
    ],
)
def test_reject_scorer_inapplicable_fields(check_type, valid_fields, extra_field):
    check = {"type": check_type, "artifact": "metrics.json", **valid_fields, **extra_field}
    with pytest.raises(ValueError, match=f"unsupported fields for {check_type}"):
        parse_task(base(checks=[check]))


def test_reject_nonfinite_target():
    with pytest.raises(ValueError, match="finite"):
        parse_task(
            base(
                checks=[
                    {
                        "type": "json_numeric",
                        "artifact": "metrics.json",
                        "json_path": "x",
                        "target": float("inf"),
                    }
                ]
            )
        )


def test_load_task_rejects_nonfinite_json(tmp_path: Path):
    path = tmp_path / "task.json"
    path.write_text(
        '{"task_id":"a","domain":"d","paper":"p","expected_artifacts":[],"metadata":{"x":NaN}}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="non-finite"):
        load_task(path)


def test_load_task_rejects_symlink(tmp_path: Path):
    target = tmp_path / "target.json"
    target.write_text(json.dumps(base()), encoding="utf-8")
    link = tmp_path / "link.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ValueError, match="symlink"):
        load_task(link)


def test_bounds_artifact_count():
    with pytest.raises(ValueError, match="at most 128"):
        parse_task(base(expected_artifacts=[f"{i}.json" for i in range(129)]))


def test_bounds_metadata_keys():
    with pytest.raises(ValueError, match="at most 128"):
        parse_task(base(metadata={str(i): i for i in range(129)}))
