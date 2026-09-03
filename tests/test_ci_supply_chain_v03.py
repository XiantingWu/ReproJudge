import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_no_github_directory_by_design() -> None:
    dot_github = ROOT / ".github"
    assert not dot_github.exists(), "no GitHub-only platform directory is allowed by design"


def test_public_surface_does_not_reference_removed_workflows() -> None:
    for relative in (
        "README.md",
        "CHANGELOG.md",
        "GOVERNANCE.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "SUPPORT.md",
    ):
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        assert "actions/workflows" not in text, f"{relative} references removed workflows"
        assert ".github/workflows/" not in text, f"{relative} references removed workflows"
        assert "dependabot.yml" not in text, f"{relative} references removed dependabot config"


def test_docs_do_not_reference_removed_workflows() -> None:
    for path in sorted((ROOT / "docs").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        assert "actions/workflows" not in text, f"{path.name} references removed workflows"
        assert ".github/workflows/" not in text, f"{path.name} references removed workflows"


def test_direct_release_toolchain_is_exactly_pinned() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for requirement in (
        "hatchling==1.32.0",
        "build==1.5.0",
        "jsonschema==4.26.0",
        "pytest==9.1.1",
        "twine==7.0.0",
        'license = "MIT"',
    ):
        assert requirement in pyproject


def test_release_dependency_lock_is_committed_for_the_authority_platform() -> None:
    lock = (ROOT / "release-lock/requirements-cp311-macos-arm64.txt").read_text(
        encoding="utf-8"
    )
    assert lock.count("--hash=sha256:") >= 40


def test_ci_supply_chain_surface_is_clean() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "actions/setup-python@" not in pyproject
    assert "pip install --upgrade pip" not in pyproject
    assert "pip==26.2.1" not in pyproject


def test_cli_and_runtime_do_not_depend_on_workflows() -> None:
    source_files = list((ROOT / "src").rglob("*.py"))
    scripts_files = [
        p
        for p in (ROOT / "scripts").glob("*.py")
        if p.name not in ("check_scientific_canonical_drift.py", "launch_surface_check.py")
    ]
    for path in source_files + scripts_files:
        text = path.read_text(encoding="utf-8")
        assert ".github/workflows" not in text, f"{path} references workflows"
        assert "actions/workflows/" not in text, f"{path} references workflow files"

    cli_text = (ROOT / "src/reprojudge/cli.py").read_text(encoding="utf-8")
    assert "reprojudge doctor" in cli_text or "doctor" in cli_text


def test_git_history_hygiene_script_still_present() -> None:
    hygiene = (ROOT / "scripts/check_git_history_hygiene.py").read_text(encoding="utf-8")
    assert "dependabot" in hygiene