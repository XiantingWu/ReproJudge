from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_reprojudge_owns_unique_distribution_import_and_cli_namespace() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert config["project"]["name"] == "reprojudge"
    assert config["project"]["scripts"] == {"reprojudge": "reprojudge.cli:main"}
    assert (ROOT / "src/reprojudge").is_dir()
    assert not (ROOT / "src/reprobench").exists()


def test_runtime_no_longer_uses_legacy_reprobench_namespace() -> None:
    for path in (ROOT / "src/reprojudge").glob("*.py"):
        text = path.read_text()
        assert "import reprobench" not in text
        assert "from reprobench" not in text
        assert "REPROBENCH_" not in text
        assert 'prog="reprobench"' not in text


def test_public_tree_never_mentions_forbidden_private_identity() -> None:
    forbidden = (
        "find" + "woods",
        "reprojudge-" + "ci",
        "reprojudge-" + "release",
        "repo-" + "reprojudge",
    )
    machinery = {
        "check_public_identity_hygiene.py",
        "check_git_history_hygiene.py",
        "launch_surface_check.py",
        "validate_sdist.py",
    }
    for path in sorted((ROOT / "src").rglob("*.py")) + sorted((ROOT / "scripts").rglob("*.py")):
        if path.name in machinery:
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in forbidden:
            assert phrase not in text, f"{phrase!r} leaked into {path}"


def test_benchmark_evidence_material_is_deferred_not_fabricated() -> None:
    assert not (ROOT / "benchmarks/reproagent-compatibility-attestation-0.8.0.json").exists()
    assert not (ROOT / "benchmarks/reproagent-compatibility-lock.json").exists()
    assert not (ROOT / "benchmarks/reproagent-compatibility-tasks").exists()
    evidence = ROOT / "benchmarks/release-evidence-0.3.0.json"
    if evidence.exists():
        payload = json.loads(evidence.read_text(encoding="utf-8"))
        assert payload.get("schema_version") == 4
        assert payload.get("release") == "0.3.0"
        assert "find" + "woods" not in evidence.read_text(encoding="utf-8")
