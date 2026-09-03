from __future__ import annotations

import platform
import re

TRUSTED_RELEASE_REPOSITORY = "XiantingWu/ReproJudge"
TRUSTED_RELEASE_MODE = "local-standalone"
TRUSTED_RELEASE_OS = "Darwin"
TRUSTED_RELEASE_ARCH = "ARM64"
_SUPPORTED_PYTHON = re.compile(r"^3\.(?:11|12|13|14)\.\d+$")
_HEAD_SHA = re.compile(r"^[0-9a-f]{40}$")


def require_trusted_release_authority(
    *,
    repository: object,
    mode: object,
    measured_source_head_sha: object,
    os_name: object,
    arch: object,
    python_version: object,
) -> None:
    """Fail closed unless provenance names the approved standalone measurement lane."""
    if repository != TRUSTED_RELEASE_REPOSITORY:
        raise ValueError("release evidence repository is not the approved standalone repository")
    if mode != TRUSTED_RELEASE_MODE:
        raise ValueError("release evidence mode is not the approved standalone mode")
    if not isinstance(measured_source_head_sha, str) or not _HEAD_SHA.fullmatch(
        measured_source_head_sha
    ):
        raise ValueError("release evidence measured source head sha is invalid")
    if os_name != TRUSTED_RELEASE_OS or arch != TRUSTED_RELEASE_ARCH:
        raise ValueError("release evidence platform is not the approved release platform")
    if not isinstance(python_version, str) or not _SUPPORTED_PYTHON.fullmatch(python_version):
        raise ValueError("release evidence Python version is not supported")


def current_platform_identity() -> dict[str, str]:
    """Describe the local measurement platform for release evidence provenance."""
    arch = platform.machine().upper()
    return {
        "repository": TRUSTED_RELEASE_REPOSITORY,
        "runner_environment": "local",
        "mode": TRUSTED_RELEASE_MODE,
        "os": platform.system(),
        "arch": arch,
        "python_version": platform.python_version(),
    }