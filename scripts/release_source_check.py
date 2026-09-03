from __future__ import annotations

import argparse
import os
import json
import re
import tomllib
from pathlib import Path
from typing import Any

from reprojudge import __version__
from reprojudge.evidence import source_fingerprint
from reprojudge.release_policy import require_trusted_release_authority

ROOT = Path(__file__).resolve().parents[1]
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
MAX_EVIDENCE_BYTES = 512 * 1024

_EXPECTED_CLAIMS = {
    "scientific_seed_scope": "15 revision-pinned real-paper repository-discovery tasks only",
    "reference_suite_scope": "deterministic evaluator mechanics only",
    "arbitrary_paper_reproducibility_proven": False,
    "scientific_correctness_proven": False,
}


def _project_version(root: Path) -> str:
    path = root / "pyproject.toml"
    if path.is_symlink() or not path.is_file():
        raise ValueError("pyproject.toml is missing or unsafe")
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
        version = payload["project"]["version"]
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError, KeyError, TypeError) as exc:
        raise ValueError(f"could not resolve project version: {exc}") from exc
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("project version must be a numeric X.Y.Z release")
    return version


def _load_evidence(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("release evidence is missing or unsafe")
    if path.stat().st_size > MAX_EVIDENCE_BYTES:
        raise ValueError("release evidence exceeds size bound")
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON number: {value}")
            ),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid release evidence JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("release evidence must be a JSON object")
    return payload


def _require_git_sha(value: object, label: str) -> str:
    if not isinstance(value, str) or not _GIT_SHA.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase 40-character git SHA")
    return value


def _validate_evidence_identity(root: Path, version: str, observed: str) -> None:
    evidence_path = root / f"benchmarks/release-evidence-{version}.json"
    payload = _load_evidence(evidence_path)
    if payload.get("schema_version") != 4:
        raise ValueError("unsupported release evidence schema")
    if payload.get("release") != version or payload.get("release") != __version__:
        raise ValueError("release evidence version does not match package/project version")

    expected_source = payload.get("source_tree_sha256")
    if not isinstance(expected_source, str) or not _SHA256.fullmatch(expected_source):
        raise ValueError("release evidence source_tree_sha256 is invalid")
    expected_flat = payload.get("source_fingerprint")
    if not isinstance(expected_flat, str) or not _SHA256.fullmatch(expected_flat):
        raise ValueError("release evidence source_fingerprint is invalid")
    if os.name == "nt":
        # Windows cannot represent POSIX execute bits; byte identity is bound
        # to the exec-normalized fingerprint there. The macOS ARM64 authority
        # lane always enforces the full exec-bit-aware fingerprint.
        if expected_flat != observed:
            raise ValueError(
                "release-relevant source bytes changed after evidence measurement: "
                f"expected {expected_flat}, observed {observed}"
            )
    else:
        if expected_source != observed:
            raise ValueError(
                "release-relevant source bytes changed after evidence measurement: "
                f"expected {expected_source}, observed {observed}"
            )

    provenance = payload.get("measurement_provenance")
    if not isinstance(provenance, dict) or set(provenance) != {
        "repository",
        "runner_environment",
        "mode",
        "measured_source_head_sha",
        "os",
        "arch",
        "python_version",
    }:
        raise ValueError("release evidence measurement provenance shape is invalid")
    _require_git_sha(
        provenance.get("measured_source_head_sha"), "measurement measured_source_head_sha"
    )
    require_trusted_release_authority(
        repository=provenance.get("repository"),
        mode=provenance.get("mode"),
        measured_source_head_sha=provenance.get("measured_source_head_sha"),
        os_name=provenance.get("os"),
        arch=provenance.get("arch"),
        python_version=provenance.get("python_version"),
    )

    if payload.get("claims") != _EXPECTED_CLAIMS:
        raise ValueError("release evidence claim boundary changed or is overstated")


def check_release_source(
    root: Path = ROOT,
    *,
    expect: str | None = None,
    require_release_evidence: bool = False,
) -> list[str]:
    root = Path(root).resolve()
    errors: list[str] = []
    try:
        version = _project_version(root)
        if version != __version__:
            raise ValueError(
                f"project version {version} does not match package version {__version__}"
            )
        observed = source_fingerprint(root, include_executable_mode=os.name != "nt")
        if expect is not None:
            if not _SHA256.fullmatch(expect):
                raise ValueError("--expect must be a lowercase SHA-256 digest")
            if expect != observed:
                raise ValueError(
                    f"release source mismatch: expected {expect}, observed {observed}"
                )
        evidence_path = root / f"benchmarks/release-evidence-{version}.json"
        if evidence_path.exists() and require_release_evidence:
            _validate_evidence_identity(root, version, observed)
        elif require_release_evidence:
            raise ValueError(
                f"required release evidence is missing: {evidence_path.relative_to(root)}"
            )
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify release-source identity and, when promoted, bind it to the "
            "version-matched trusted standalone measurement evidence."
        )
    )
    parser.add_argument("--expect")
    parser.add_argument("--require-release-evidence", action="store_true")
    args = parser.parse_args()

    errors = check_release_source(
        expect=args.expect,
        require_release_evidence=args.require_release_evidence,
    )
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    observed = source_fingerprint(ROOT, include_executable_mode=os.name != "nt")
    evidence = ROOT / f"benchmarks/release-evidence-{__version__}.json"
    mode = "evidence-bound" if args.require_release_evidence and evidence.is_file() else "source-only"
    print(f"release_source_sha256={observed}")
    print(f"PASS: release source identity is valid mode={mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
