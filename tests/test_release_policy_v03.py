from __future__ import annotations

import pytest

from reprojudge.release_policy import (
    TRUSTED_RELEASE_ARCH,
    TRUSTED_RELEASE_OS,
    TRUSTED_RELEASE_REPOSITORY,
    current_platform_identity,
    require_trusted_release_authority,
)


def _valid_kwargs() -> dict[str, str]:
    return {
        "repository": TRUSTED_RELEASE_REPOSITORY,
        "mode": "local-standalone",
        "measured_source_head_sha": "a" * 40,
        "os_name": TRUSTED_RELEASE_OS,
        "arch": TRUSTED_RELEASE_ARCH,
        "python_version": "3.11.9",
    }


@pytest.mark.parametrize("python_version", ["3.11.9", "3.12.10", "3.13.15", "3.14.7"])
def test_release_policy_accepts_supported_standalone_release_lane(python_version: str):
    require_trusted_release_authority(**{**_valid_kwargs(), "python_version": python_version})


@pytest.mark.parametrize(
    "field,value",
    [
        ("repository", "XiantingWu/OtherProject"),
        ("mode", "github-actions-hosted"),
        ("measured_source_head_sha", "g" * 40),
        ("measured_source_head_sha", "not-a-sha"),
        ("measured_source_head_sha", ""),
        ("os_name", "Linux"),
        ("arch", "x86_64"),
        ("python_version", "3.10.14"),
        ("python_version", "3.15.0"),
        ("python_version", ""),
    ],
)
def test_release_policy_fails_closed_for_non_authority(field: str, value: str):
    with pytest.raises(ValueError):
        require_trusted_release_authority(**{**_valid_kwargs(), field: value})


def test_current_platform_identity_is_standalone() -> None:
    identity = current_platform_identity()
    assert identity["repository"] == TRUSTED_RELEASE_REPOSITORY
    assert identity["runner_environment"] == "local"
    assert identity["mode"] == "local-standalone"
    assert identity["os"]
    assert identity["arch"]
    assert identity["python_version"]