from __future__ import annotations

import platform
import re

import pytest

from scripts import build_release_evidence

_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


def test_local_measurement_provenance_uses_approved_standalone_identity() -> None:
    provenance = build_release_evidence._local_measurement_provenance("a" * 40)
    assert provenance["repository"] == "XiantingWu/ReproJudge"
    assert provenance["runner_environment"] == "local"
    assert provenance["mode"] == "local-standalone"
    assert provenance["measured_source_head_sha"] == "a" * 40
    assert provenance["os"] == platform.system()
    assert provenance["arch"] == platform.machine().upper()
    assert _GIT_SHA.fullmatch(provenance["measured_source_head_sha"])


def test_local_measurement_refuses_invalid_measured_head() -> None:
    with pytest.raises(ValueError, match="git SHA"):
        build_release_evidence._local_measurement_provenance("not-a-sha")


def test_local_measurement_refuses_unsupported_python(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        build_release_evidence,
        "current_platform_identity",
        lambda: {
            "repository": "XiantingWu/ReproJudge",
            "runner_environment": "local",
            "mode": "local-standalone",
            "os": "Darwin",
            "arch": "ARM64",
            "python_version": "2.7.18",
        },
    )
    with pytest.raises(ValueError, match="Python version"):
        build_release_evidence._local_measurement_provenance("a" * 40)


def test_local_measurement_refuses_unsupported_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        build_release_evidence,
        "current_platform_identity",
        lambda: {
            "repository": "XiantingWu/ReproJudge",
            "runner_environment": "local",
            "mode": "local-standalone",
            "os": "Linux",
            "arch": "X64",
            "python_version": "3.11.9",
        },
    )
    with pytest.raises(ValueError, match="platform"):
        build_release_evidence._local_measurement_provenance("a" * 40)


def test_local_measurement_refuses_non_standalone_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        build_release_evidence,
        "current_platform_identity",
        lambda: {
            "repository": "XiantingWu/ReproJudge",
            "runner_environment": "local",
            "mode": "github-actions-hosted",
            "os": "Darwin",
            "arch": "ARM64",
            "python_version": "3.11.9",
        },
    )
    with pytest.raises(ValueError, match="mode"):
        build_release_evidence._local_measurement_provenance("a" * 40)