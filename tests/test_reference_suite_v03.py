from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts/run_reference_suite.py"
    spec = importlib.util.spec_from_file_location("run_reference_suite", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return root, module


def test_reference_suite_end_to_end(tmp_path: Path):
    root, module = _load_module()
    manifest = module.run_reference_suite(root / "benchmarks/reference-suite.json", tmp_path)
    assert manifest["gate_passed"] is True
    assert manifest["summary"]["total"] == 4
    assert manifest["summary"]["passed"] == 4
    assert len(manifest["source_tree_sha256"]) == 64


def test_reference_suite_prefers_exact_measurement_head_over_pr_merge_sha(
    tmp_path: Path, monkeypatch
):
    root, module = _load_module()
    exact_head = "a" * 40
    synthetic_merge = "b" * 40
    monkeypatch.setenv("REPROJUDGE_HEAD_SHA", exact_head)
    monkeypatch.setenv("GITHUB_SHA", synthetic_merge)
    monkeypatch.setenv("GITHUB_REPOSITORY", "XiantingWu/ReproJudge")
    monkeypatch.setenv("GITHUB_WORKFLOW", "ReproJudge trusted release audit")
    monkeypatch.setenv("GITHUB_RUN_ID", "1")
    monkeypatch.setenv("RUNNER_NAME", "GitHub Actions 1")
    monkeypatch.setenv("RUNNER_ENVIRONMENT", "github-hosted")
    monkeypatch.setenv("RUNNER_ARCH", "ARM64")
    monkeypatch.setenv("RUNNER_OS", "macOS")
    manifest = module.run_reference_suite(
        root / "benchmarks/reference-suite.json", tmp_path / "reference"
    )
    provenance = manifest["provenance"]
    assert provenance["github_repository"] == "XiantingWu/ReproJudge"
    assert provenance["measured_source_head_sha"] == exact_head
    assert provenance["runner_environment"] == "github-hosted"
    assert "github_sha" not in provenance
