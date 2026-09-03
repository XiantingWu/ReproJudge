from __future__ import annotations

import json
from pathlib import Path

from reprojudge.evidence import source_fingerprint
from scripts.release_source_check import check_release_source


CLAIMS = {
    "scientific_seed_scope": "15 revision-pinned real-paper repository-discovery tasks only",
    "reference_suite_scope": "deterministic evaluator mechanics only",
    "arbitrary_paper_reproducibility_proven": False,
    "scientific_correctness_proven": False,
}


def _fixture(root: Path) -> Path:
    (root / "src").mkdir()
    (root / "src" / "core.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "benchmarks").mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "reprojudge"\nversion = "0.3.0"\n',
        encoding="utf-8",
    )
    source = source_fingerprint(root)
    source_flat = source_fingerprint(root, include_executable_mode=False)
    evidence = {
        "schema_version": 4,
        "release": "0.3.0",
        "source_tree_sha256": source,
        "source_fingerprint": source_flat,
        "measurement_provenance": {
            "repository": "XiantingWu/ReproJudge",
            "runner_environment": "local",
            "mode": "local-standalone",
            "measured_source_head_sha": "b" * 40,
            "os": "Darwin",
            "arch": "ARM64",
            "python_version": "3.11.9",
        },
        "claims": CLAIMS,
    }
    path = root / "benchmarks" / "release-evidence-0.3.0.json"
    path.write_text(json.dumps(evidence), encoding="utf-8")
    return path


def test_release_source_accepts_matching_promoted_evidence(tmp_path: Path):
    _fixture(tmp_path)
    assert check_release_source(tmp_path, require_release_evidence=True) == []


def test_release_source_rejects_stale_source_after_promotion(tmp_path: Path):
    _fixture(tmp_path)
    (tmp_path / "src" / "core.py").write_text("VALUE = 2\n", encoding="utf-8")
    errors = check_release_source(tmp_path, require_release_evidence=True)
    assert errors and "changed after evidence measurement" in errors[0]


def test_release_source_defaults_to_source_only_when_evidence_is_stale(tmp_path: Path):
    _fixture(tmp_path)
    (tmp_path / "src" / "core.py").write_text("VALUE = 2\n", encoding="utf-8")
    assert check_release_source(tmp_path) == []


def test_release_source_requires_evidence_when_requested(tmp_path: Path):
    evidence = _fixture(tmp_path)
    evidence.unlink()
    errors = check_release_source(tmp_path, require_release_evidence=True)
    assert errors and "required release evidence is missing" in errors[0]


def test_release_source_rejects_overstated_claim_boundary(tmp_path: Path):
    evidence = _fixture(tmp_path)
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    payload["claims"]["scientific_correctness_proven"] = True
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    errors = check_release_source(tmp_path, require_release_evidence=True)
    assert errors and "claim boundary" in errors[0]


def test_release_source_rejects_wrong_repository(tmp_path: Path):
    evidence = _fixture(tmp_path)
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    payload["measurement_provenance"]["repository"] = "XiantingWu/OtherProject"
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    errors = check_release_source(tmp_path, require_release_evidence=True)
    assert errors and "approved standalone repository" in errors[0]


def test_release_source_rejects_invalid_measured_head(tmp_path: Path):
    evidence = _fixture(tmp_path)
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    payload["measurement_provenance"]["measured_source_head_sha"] = "not-a-sha"
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    errors = check_release_source(tmp_path, require_release_evidence=True)
    assert errors and "measured_source_head_sha" in errors[0]


def test_release_source_rejects_wrong_release_platform(tmp_path: Path):
    evidence = _fixture(tmp_path)
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    payload["measurement_provenance"]["arch"] = "x86_64"
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    errors = check_release_source(tmp_path, require_release_evidence=True)
    assert errors and "approved release platform" in errors[0]


def test_release_source_rejects_non_standalone_mode(tmp_path: Path):
    evidence = _fixture(tmp_path)
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    payload["measurement_provenance"]["mode"] = "github-actions-hosted"
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    errors = check_release_source(tmp_path, require_release_evidence=True)
    assert errors