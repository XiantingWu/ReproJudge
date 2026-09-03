from __future__ import annotations

import re
import tomllib
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/XiantingWu/ReproJudge"
EXPECTED_URLS = {
    "Homepage": REPOSITORY,
    "Repository": REPOSITORY,
    "Documentation": f"{REPOSITORY}/tree/main/docs",
    "Changelog": f"{REPOSITORY}/blob/main/CHANGELOG.md",
    "Issues": f"{REPOSITORY}/issues",
    "Security": f"{REPOSITORY}/security",
}
REQUIRED = [
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "CITATION.cff",
    "ROADMAP.md",
    "CHANGELOG.md",
    "GOVERNANCE.md",
    "SUPPORT.md",
    "benchmarks/reference-suite.json",
    "benchmarks/scientific-seed/manifest.json",
    "docs/GETTING_STARTED.md",
    "docs/AUTHORING.md",
    "docs/INTEGRATING_AGENTS.md",
    "docs/FAQ.md",
    "docs/ARCHITECTURE.md",
    "docs/EVIDENCE.md",
    "docs/COMPATIBILITY.md",
    "docs/TELEMETRY.md",
    "docs/LEADERBOARD.md",
    "docs/TRUST_MODEL.md",
    "docs/TASK_SPEC.md",
    "docs/RESULT_SPEC.md",
    "docs/BENCHMARK_CORPUS_POLICY.md",
    "docs/LAUNCH_READINESS_0.3.0.md",
    "docs/RELEASING.md",
    "docs/PUBLIC_RELEASE_CHECKLIST.md",
    "schemas/task-v1.schema.json",
    "schemas/result-v1.schema.json",
    "schemas/agent-telemetry-v1.schema.json",
    "src/reprojudge/starter.py",
    "tests/test_cli.py",
    "scripts/build_release_evidence.py",
    "scripts/check_public_identity_hygiene.py",
    "scripts/check_git_history_hygiene.py",
    "scripts/check_scientific_canonical_drift.py",
    "scripts/launch_surface_check.py",
    "scripts/release_check.py",
    "scripts/release_source_check.py",
    "scripts/run_reference_suite.py",
    "scripts/standalone_export.py",
    "scripts/validate_reference_provenance.py",
    "scripts/validate_scientific_seed.py",
    "scripts/validate_sdist.py",
    "scripts/verify_release_dependency_lock.py",
]
FORBIDDEN_PUBLIC_PHRASES = [
    "incubation scaffold",
    "TODO " + "before " + "public",
    "replace-me",
    "find" + "woods",
]
FORBIDDEN_DUPLICATE_FORMS: tuple[str, ...] = ()
_MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def _read(root: Path, relative: str, errors: list[str]) -> str:
    path = root / relative
    if path.is_symlink() or not path.is_file():
        errors.append(f"missing safe public-launch file: {relative}")
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"could not read {relative}: {exc}")
        return ""


def _check_local_markdown_links(root: Path, errors: list[str]) -> None:
    markdown_files = [
        root / name
        for name in (
            "README.md",
            "SECURITY.md",
            "CONTRIBUTING.md",
            "CODE_OF_CONDUCT.md",
            "ROADMAP.md",
            "CHANGELOG.md",
            "GOVERNANCE.md",
            "SUPPORT.md",
        )
    ] + sorted((root / "docs").glob("*.md"))
    for path in markdown_files:
        if path.is_symlink() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in _MARKDOWN_LINK.finditer(text):
            raw = match.group(1).strip()
            if not raw:
                continue
            target = raw.split(maxsplit=1)[0].strip("<>")
            if target.startswith(("https://", "http://", "mailto:", "#")):
                continue
            local = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not local:
                continue
            candidate = (path.parent / local).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                errors.append(
                    f"local markdown link escapes standalone root: "
                    f"{path.relative_to(root).as_posix()} -> {target}"
                )
                continue
            if not candidate.exists():
                errors.append(
                    f"broken local markdown link: "
                    f"{path.relative_to(root).as_posix()} -> {target}"
                )


def check_launch_surface(root: Path = ROOT) -> list[str]:
    root = Path(root).resolve()
    errors: list[str] = []

    for relative in REQUIRED:
        _read(root, relative, errors)
    for relative in FORBIDDEN_DUPLICATE_FORMS:
        path = root / relative
        if path.exists() or path.is_symlink():
            errors.append(f"duplicate public contribution form must be removed: {relative}")

    pyproject_text = _read(root, "pyproject.toml", errors)
    readme = _read(root, "README.md", errors)
    security = _read(root, "SECURITY.md", errors)
    contributing = _read(root, "CONTRIBUTING.md", errors)
    authoring = _read(root, "docs/AUTHORING.md", errors)
    integrating = _read(root, "docs/INTEGRATING_AGENTS.md", errors)
    faq = _read(root, "docs/FAQ.md", errors)
    task_spec = _read(root, "docs/TASK_SPEC.md", errors)
    trust_model = _read(root, "docs/TRUST_MODEL.md", errors)
    source_identity = _read(root, "docs/SOURCE_IDENTITY.md", errors)
    evidence_doc = _read(root, "docs/EVIDENCE.md", errors)
    launch_readiness = _read(root, "docs/LAUNCH_READINESS_0.3.0.md", errors)
    release_checklist = _read(root, "docs/PUBLIC_RELEASE_CHECKLIST.md", errors)
    releasing = _read(root, "docs/RELEASING.md", errors)
    corpus_policy = _read(root, "docs/BENCHMARK_CORPUS_POLICY.md", errors)
    governance = _read(root, "GOVERNANCE.md", errors)
    support = _read(root, "SUPPORT.md", errors)
    citation = _read(root, "CITATION.cff", errors)
    dot_github = root / ".github"
    if dot_github.exists() or dot_github.is_symlink():
        errors.append("no GitHub-only platform directory is allowed by design: .github")

    if pyproject_text:
        try:
            project = tomllib.loads(pyproject_text)["project"]
        except (tomllib.TOMLDecodeError, KeyError) as exc:
            errors.append(f"could not parse pyproject project metadata: {exc}")
        else:
            if project.get("name") != "reprojudge":
                errors.append("distribution name must be reprojudge")
            if project.get("version") != "0.3.0":
                errors.append("release version must be 0.3.0")
            if project.get("dependencies") not in (None, []):
                errors.append("core runtime must remain dependency-free")
            if project.get("license") != "MIT":
                errors.append("project license must use the PEP 639 SPDX expression MIT")
            if "License :: OSI Approved :: MIT License" in (project.get("classifiers") or []):
                errors.append("deprecated license classifier must be removed under PEP 639")
            classifiers = project.get("classifiers")
            if not isinstance(classifiers, list) or "Programming Language :: Python :: 3.14" not in classifiers:
                errors.append("project metadata must declare tested Python 3.14 support")
            urls = project.get("urls")
            if not isinstance(urls, dict):
                errors.append("pyproject.toml must define [project.urls]")
            else:
                for label, expected in EXPECTED_URLS.items():
                    if urls.get(label) != expected:
                        errors.append(
                            f"project URL {label!r} must be canonical standalone URL {expected!r}"
                        )

    public_text = "\n".join(
        (
            readme,
            security,
            contributing,
            governance,
            support,
            authoring,
            integrating,
            faq,
            task_spec,
            trust_model,
            source_identity,
            evidence_doc,
            launch_readiness,
            release_checklist,
            releasing,
            corpus_policy,
            pyproject_text,
            citation,
        )
    )
    assertions = {
        "readme_security_boundary": "not a security sandbox" in readme.lower(),
        "readme_real_scientific_shard": "15" in readme and "repository-discovery" in readme.lower(),
        "readme_starter_onboarding": "reprojudge init" in readme
        and "60-second start" in readme.lower(),
        "authoring_hidden_checks_boundary": "agent-visible request" in authoring.lower()
        and "checks" in authoring.lower()
        and "not a security sandbox" in authoring.lower(),
        "integration_environment_contract": "REPROJUDGE_TASK_MANIFEST" in integrating
        and "REPROJUDGE_OUTPUT_DIR" in integrating
        and "REPROJUDGE_TELEMETRY_PATH" in integrating,
        "faq_claim_boundary": "repository-discovery" in faq.lower()
        and "not a security sandbox" in faq.lower(),
        "private_evaluator_checks_documented": "agent-visible" in task_spec.lower()
        and "checks" in task_spec.lower(),
        "security_private_reporting": "private security" in security.lower(),
        "citation_repository": f'repository-code: "{REPOSITORY}"' in citation,
        "citation_url": f'url: "{REPOSITORY}"' in citation,
        "no_dot_github_by_design": not (ROOT / ".github").exists(),
        "docs_execution_boundary": "no github actions workflows" in trust_model.lower()
        and "workstation" in trust_model.lower()
        and "self-hosted" not in trust_model.lower(),
        "docs_exact_main_policy": "exact current" in source_identity.lower()
        and "main" in source_identity.lower(),
        "docs_corpus_policy_present": "canonical repository" in corpus_policy.lower()
        and "drift" in corpus_policy.lower(),
        "docs_governance_present": "maintainer" in governance.lower(),
        "docs_support_present": "security" in support.lower()
        and "benchmark" in support.lower(),
        "single_maintainer_honest": "single-maintainer" in governance.lower()
        or "single maintainer" in governance.lower(),
        "trust_model_no_personal_runner_privacy": "public runner-log privacy" not in trust_model.lower(),
        "private_identity_zero_in_public_surface": "find" + "woods" not in public_text.lower(),
        "no_github_only_surface_in_docs": ".github" not in public_text.lower(),
        "no_personal_path_in_public_surface": "/Users/" + "woods" not in public_text
        and "Woods-" + "M2" not in public_text,
    }
    failed = [name for name, ok in assertions.items() if not ok]
    if failed:
        errors.append("launch surface assertions failed: " + ", ".join(failed))

    for phrase in FORBIDDEN_PUBLIC_PHRASES:
        for relative in ("README.md", "SECURITY.md", "CONTRIBUTING.md", "ROADMAP.md"):
            text = _read(root, relative, errors)
            if phrase.lower() in text.lower():
                errors.append(f"stale public wording: {relative}:{phrase}")

    _check_local_markdown_links(root, errors)
    return errors


def main() -> int:
    errors = check_launch_surface()
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(
        "PASS: standalone source surface is canonical, linked, benchmark-bearing, "
        "workflow-free-by-design, contributor-ready, and release-gated "
        "(repository/PyPI account controls are verified separately)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
