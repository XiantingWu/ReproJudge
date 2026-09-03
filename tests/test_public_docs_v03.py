from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_public_onboarding_uses_portable_python3_commands_on_unix():
    readme = _text("README.md")
    getting_started = _text("docs/GETTING_STARTED.md")
    contributing = _text("CONTRIBUTING.md")
    releasing = _text("docs/RELEASING.md")
    evidence = _text("docs/EVIDENCE.md")

    assert "python3 -m pip install ." in readme
    assert "-- python3 agent.py" in readme
    assert "python3 -m pip install -e ." in getting_started
    assert "-- python3 examples/demo_agent.py" in getting_started
    assert "-- python3 /tmp/reprojudge-starter/agent.py" in contributing
    assert "python3 -m pip install -e '.[dev]'" in releasing
    assert "python3 scripts/release_check.py --require-release-evidence" in evidence

    for text in (readme, getting_started, contributing, releasing):
        assert "python -m pip install" not in text
    for text in (evidence, releasing):
        assert "python scripts/" not in text


def test_public_claim_docs_do_not_leak_internal_star_targets():
    for path in ("README.md", "docs/LAUNCH_READINESS_0.3.0.md"):
        text = _text(path).lower()
        assert "github stars" not in text
        assert "number of stars" not in text


def test_public_docs_do_not_expose_transitional_incubator_identity():
    public_paths = (
        "README.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "ROADMAP.md",
        "SECURITY.md",
        "GOVERNANCE.md",
        "SUPPORT.md",
        "docs/ARCHITECTURE.md",
        "docs/COMPATIBILITY.md",
        "docs/EVIDENCE.md",
        "docs/GETTING_STARTED.md",
        "docs/LAUNCH_READINESS_0.3.0.md",
        "docs/RELEASING.md",
        "docs/TASK_SPEC.md",
        "docs/TRUST_MODEL.md",
    )
    forbidden = (
        "Repository2-" + "ReproJudge",
        "trusted incubator",
        "In the incubator",
        "Repository1-" + "ReproAgent",
        "find" + "woods",
        "reprojudge-" + "ci",
        "reprojudge-" + "release",
        "repo-" + "reprojudge",
    )

    for path in public_paths:
        text = _text(path)
        for phrase in forbidden:
            assert phrase not in text, f"{phrase!r} leaked into {path}"


def test_architecture_declares_canonical_standalone_identity():
    architecture = _text("docs/ARCHITECTURE.md")

    assert "`XiantingWu/ReproJudge` is the canonical standalone source" in architecture
    assert "no sibling repository is a runtime dependency" in architecture


def test_trust_model_declares_workflow_free_execution_boundary():
    trust_model = _text("docs/TRUST_MODEL.md").lower()
    assert "no github actions workflows" in trust_model
    assert "workstation" in trust_model
    assert "self-hosted" not in trust_model


def test_repo1_compatibility_is_documented_as_deferred():
    compatibility = _text("docs/COMPATIBILITY.md").lower()
    roadmap = _text("ROADMAP.md").lower()
    changelog = _text("CHANGELOG.md").lower()

    assert "deferred" in compatibility
    assert "deferred" in roadmap
    assert "deferred" in changelog
