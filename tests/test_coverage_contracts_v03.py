from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import reprojudge.cli as cli
import reprojudge.evidence as evidence
import reprojudge.reporting as reporting
from reprojudge.registry import TaskRegistry
from reprojudge.schema import parse_task


def _manifest(task_id: str = "coverage-task") -> dict[str, object]:
    return {
        "task_id": task_id,
        "domain": "coverage",
        "paper": "synthetic:coverage",
        "expected_artifacts": [],
    }


def _result(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "result_schema_version": 1,
        "task_id": "coverage-task",
        "status": "passed",
        "passed": True,
        "duration_seconds": 1.0,
        "artifacts": [],
        "checks": [],
        "telemetry": None,
    }
    payload.update(overrides)
    return payload


def test_schema_rejects_non_utf8_programmatic_text() -> None:
    with pytest.raises(ValueError, match="UTF-8"):
        parse_task({**_manifest(), "domain": "bad\ud800"})
    with pytest.raises(ValueError, match="UTF-8"):
        parse_task({**_manifest(), "tags": ["bad\ud800"]})
    with pytest.raises(ValueError, match="UTF-8|finite"):
        parse_task({**_manifest(), "metadata": {"bad\ud800": "value"}})
    with pytest.raises(ValueError, match="UTF-8|finite"):
        parse_task({**_manifest(), "metadata": {"key": "bad\ud800"}})


def test_evidence_helpers_and_exclusion_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_bytes(b"abc")
    assert evidence.sha256_file(sample) == evidence.sha256_bytes(b"abc")
    assert evidence.canonical_json_sha256({"b": 2, "a": 1}) == evidence.canonical_json_sha256(
        {"a": 1, "b": 2}
    )
    with pytest.raises(ValueError, match="canonical JSON"):
        evidence.canonical_json_sha256(float("nan"))
    with pytest.raises(ValueError, match="canonical JSON"):
        evidence.canonical_json_sha256(object())
    with pytest.raises(TypeError, match="to_dict"):
        evidence.task_fingerprint(object())

    assert not evidence.release_path_excluded(Path())
    assert evidence.release_path_excluded(Path("dist/out.whl"))
    assert evidence.release_path_excluded(Path("pkg/__pycache__/x.pyc"))
    assert evidence.release_path_excluded(Path("docs/.DS_Store"))
    assert not evidence.release_path_excluded(Path("pkg/dist/source.py"))

    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ValueError, match="no release-relevant files"):
        evidence.source_fingerprint(empty)

    oversized = tmp_path / "oversized"
    oversized.mkdir()
    (oversized / "x").write_bytes(b"12")
    monkeypatch.setattr(evidence, "_MAX_FINGERPRINT_FILE_BYTES", 1)
    with pytest.raises(ValueError, match="size bound"):
        evidence.source_fingerprint(oversized)


def test_registry_error_paths_lookup_and_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "missing"
    with pytest.raises(ValueError, match="does not exist"):
        TaskRegistry.from_directory(missing)

    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ValueError, match="no task manifests"):
        TaskRegistry.from_directory(empty)

    tasks = tmp_path / "tasks"
    tasks.mkdir()
    (tasks / "a.json").write_text(json.dumps(_manifest("a")), encoding="utf-8")
    (tasks / "b.json").write_text(json.dumps(_manifest("b")), encoding="utf-8")
    registry = TaskRegistry.from_directory(tasks)
    assert registry.get("a").task.task_id == "a"
    with pytest.raises(KeyError):
        registry.get("missing")

    monkeypatch.setattr("reprojudge.registry.MAX_REGISTRY_TASKS", 1)
    with pytest.raises(ValueError, match="exceeds 1 manifests"):
        TaskRegistry.from_directory(tasks)


def test_registry_rejects_symlink_root_and_nested_path(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / "a.json").write_text(json.dumps(_manifest("a")), encoding="utf-8")
    root_link = tmp_path / "root-link"
    try:
        root_link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ValueError, match="symlink"):
        TaskRegistry.from_directory(root_link)

    root = tmp_path / "root"
    root.mkdir()
    nested_link = root / "nested"
    nested_link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        TaskRegistry.from_directory(root)


@pytest.mark.parametrize(
    "telemetry,match",
    [
        ("bad", "object or null"),
        ({"unknown": 1}, "unsupported keys"),
        ({"token_usage": True}, "token_usage"),
        ({"token_usage": -1}, "token_usage"),
        ({"model_cost_usd": float("nan")}, "model_cost_usd"),
        ({"model_cost_usd": -1}, "model_cost_usd"),
        ({"interventions": ["bad\nvalue"]}, "interventions"),
        ({"agent_name": "\n"}, "agent_name"),
    ],
)
def test_reporting_rejects_invalid_telemetry(
    tmp_path: Path, telemetry: object, match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        reporting._validate_telemetry(telemetry, tmp_path / "result.json")


@pytest.mark.parametrize(
    "artifacts,match",
    [
        ("bad", "artifacts are invalid"),
        ([{"path": "x"}], "record is invalid"),
        ([{"path": "../x", "size_bytes": 0, "sha256": "0" * 64}], "path is invalid"),
        ([{"path": "x", "size_bytes": True, "sha256": "0" * 64}], "size is invalid"),
        ([{"path": "x", "size_bytes": -1, "sha256": "0" * 64}], "size is invalid"),
        ([{"path": "x", "size_bytes": 0, "sha256": "bad"}], "sha256 is invalid"),
    ],
)
def test_reporting_rejects_invalid_artifact_records(
    tmp_path: Path, artifacts: object, match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        reporting._validate_artifacts(artifacts, tmp_path / "result.json")


@pytest.mark.parametrize(
    "checks,match",
    [
        ("bad", "checks are invalid"),
        ([{"name": "x"}], "record is invalid"),
        ([{"name": "", "passed": True, "detail": "ok"}], "name is invalid"),
        ([{"name": "x", "passed": 1, "detail": "ok"}], "passed value is invalid"),
        ([{"name": "x", "passed": True, "detail": "x" * 4097}], "detail is invalid"),
    ],
)
def test_reporting_rejects_invalid_check_records(
    tmp_path: Path, checks: object, match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        reporting._validate_checks(checks, tmp_path / "result.json")


@pytest.mark.parametrize(
    "overrides,match",
    [
        ({"result_schema_version": 2}, "unsupported result schema"),
        ({"task_id": ""}, "task identity"),
        ({"status": "unknown"}, "unsupported status"),
        ({"duration_seconds": -1}, "duration_seconds"),
        ({"duration_seconds": float("inf")}, "non-finite"),
        ({"passed": False}, "inconsistent"),
        ({"failure_taxonomy": ["same", "same"]}, "failure_taxonomy"),
        ({"failure_taxonomy": ["bad\nvalue"]}, "failure_taxonomy"),
    ],
)
def test_reporting_result_payload_fail_closed(
    tmp_path: Path, overrides: dict[str, object], match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        reporting._validate_result_payload(_result(**overrides), tmp_path / "result.json")


def test_reporting_strict_json_and_summary_branches(tmp_path: Path) -> None:
    result_path = tmp_path / "result.json"
    result_path.write_bytes(b"\xff")
    with pytest.raises(ValueError, match="invalid result JSON"):
        reporting._strict_json(result_path)

    assert reporting.summarize([]).to_dict() == {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "pass_rate": 0.0,
        "mean_duration_seconds": 0.0,
        "statuses": {},
        "total_tokens": 0,
        "total_model_cost_usd": 0.0,
        "interventions": 0,
    }
    summary = reporting.summarize(
        [
            {
                "task_id": "a",
                "status": "passed",
                "duration_seconds": 1.0,
                "telemetry": {
                    "token_usage": 2,
                    "model_cost_usd": 0.25,
                    "interventions": ["human-check"],
                },
            },
            {
                "task_id": "b",
                "status": "failed",
                "duration_seconds": "bad",
                "telemetry": None,
            },
        ]
    )
    assert summary.total_tokens == 2
    assert summary.total_model_cost_usd == 0.25
    assert summary.interventions == 1
    assert "| failed | 1 |" in reporting.markdown_summary(summary)


def test_cli_report_leaderboard_fingerprint_registry_and_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    task_dir = tmp_path / "tasks"
    task_dir.mkdir()
    task_path = task_dir / "task.json"
    task_path.write_text(json.dumps(_manifest()), encoding="utf-8")

    assert cli.main(["registry", str(task_dir)]) == 0
    assert '"count": 1' in capsys.readouterr().out

    assert cli.main(["fingerprint", str(task_path)]) == 0
    assert len(capsys.readouterr().out.strip()) == 64

    source = tmp_path / "source"
    source.mkdir()
    (source / "README.md").write_text("source\n", encoding="utf-8")
    assert cli.main(["fingerprint", str(source), "--source-tree"]) == 0
    assert len(capsys.readouterr().out.strip()) == 64

    results = tmp_path / "results"
    run = results / "run"
    run.mkdir(parents=True)
    (run / "result.json").write_text(json.dumps(_result()), encoding="utf-8")

    for fmt in ("json", "markdown"):
        assert cli.main(["summarize", str(results), "--format", fmt]) == 0
        assert capsys.readouterr().out
    for fmt in ("json", "markdown", "csv"):
        assert cli.main(["leaderboard", str(results), "--format", fmt]) == 0
        assert capsys.readouterr().out

    assert cli.main(["run", str(task_path)]) == 2
    assert "agent command is required" in capsys.readouterr().err
    assert cli.main(["validate", str(tmp_path / "missing.json")]) == 2
    assert "reprojudge: error:" in capsys.readouterr().err


def test_cli_suite_success_and_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    task_dir = tmp_path / "tasks"
    task_dir.mkdir()
    for task_id in ("a", "b"):
        (task_dir / f"{task_id}.json").write_text(
            json.dumps(_manifest(task_id)), encoding="utf-8"
        )
    assert (
        cli.main(
            [
                "suite",
                str(task_dir),
                "--output",
                str(tmp_path / "runs-ok"),
                "--",
                sys.executable,
                "-c",
                "pass",
            ]
        )
        == 0
    )
    assert '"failed": 0' in capsys.readouterr().out

    assert (
        cli.main(
            [
                "suite",
                str(task_dir),
                "--output",
                str(tmp_path / "runs-fail"),
                "--",
                sys.executable,
                "-c",
                "raise SystemExit(3)",
            ]
        )
        == 2
    )
    assert '"failed": 2' in capsys.readouterr().out


def test_doctor_strict_failure_and_docker_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli.shutil, "which", lambda _name: None)
    ok, checks = cli._doctor(False, True)
    assert not ok
    assert checks["docker_cli"] is False

    def timeout(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.TimeoutExpired(cmd="python", timeout=5)

    monkeypatch.setattr(cli.subprocess, "run", timeout)
    ok, checks = cli._doctor(True, False)
    assert not ok
    assert checks["child_process_boundary"] is False


def test_main_doctor_failure_exit(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli, "_doctor", lambda _strict, _docker: (False, {"probe": False}))
    assert cli.main(["doctor", "--strict"]) == 1
    assert '"ok": false' in capsys.readouterr().out.lower()
