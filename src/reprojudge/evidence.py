from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

from ._paths import reject_symlink_components

_RELEASE_EVIDENCE = re.compile(r"^benchmarks/release-evidence-[0-9]+\.[0-9]+\.[0-9]+\.json$")
_EXCLUDED_NAMES = {".DS_Store"}
_EXCLUDED_TOP_LEVEL_DIRS = {
    ".git",
    ".venv",
    ".reprojudge",
    ".hypothesis",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "htmlcov",
    "venv",
}
_EXCLUDED_TOP_LEVEL_FILES = {".coverage", "coverage.json"}
_EXCLUDED_CACHE_DIRS = {"__pycache__", ".pytest_cache"}
_MAX_FINGERPRINT_FILE_BYTES = 8 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json_sha256(payload: object) -> str:
    try:
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"value is not canonical JSON: {exc}") from exc
    return sha256_bytes(raw)


def task_fingerprint(task: object) -> str:
    to_dict = getattr(task, "to_dict", None)
    if not callable(to_dict):
        raise TypeError("task must expose to_dict()")
    return canonical_json_sha256(to_dict())


def release_path_excluded(relative_path: Path) -> bool:
    """Return whether a standalone-tree path is deliberate local/generated state.

    Exclusions are intentionally narrow and location-aware. Top-level build,
    environment, coverage, property-test and static-analysis state is generated
    and must not make a release fingerprint depend on which quality gate ran
    first. Nested source directories/files with the same names remain covered.
    """
    parts = relative_path.parts
    if not parts:
        return False
    if parts[0] in _EXCLUDED_TOP_LEVEL_DIRS:
        return True
    if len(parts) == 1 and (
        parts[0] in _EXCLUDED_TOP_LEVEL_FILES
        or parts[0].startswith(".coverage.")
    ):
        return True
    if any(part in _EXCLUDED_CACHE_DIRS for part in parts[:-1]):
        return True
    return relative_path.name in _EXCLUDED_NAMES


def _release_paths(root: Path) -> Iterable[Path]:
    root = root.resolve()
    for path in sorted(
        root.rglob("*"),
        key=lambda candidate: candidate.relative_to(root).as_posix(),
    ):
        relative_path = path.relative_to(root)
        relative = relative_path.as_posix()
        if release_path_excluded(relative_path):
            continue
        # Promoted, versioned release evidence is the one deliberate source-
        # identity exception: it records the fingerprint it is attached to, so
        # including it would create a self-reference. Similarly prefixed files
        # remain covered.
        if _RELEASE_EVIDENCE.fullmatch(relative):
            continue
        if path.is_symlink():
            raise ValueError(f"release-relevant path must not be a symlink: {relative}")
        if path.is_file():
            yield path


def _normalized_git_mode(path: Path) -> bytes:
    """Normalize filesystem execute semantics to Git's regular-file modes."""
    return b"100755" if path.stat().st_mode & 0o111 else b"100644"


def source_fingerprint(root: Path, *, include_executable_mode: bool = True) -> str:
    """Hash standalone source paths, bytes, sizes, and executable semantics.

    The policy is fail-closed: every regular file is covered by default except
    narrowly defined local/generated state and the exact versioned promoted
    evidence record needed to avoid self-reference.

    ``include_executable_mode=False`` normalizes every file to the regular
    mode and is used on Windows, where the filesystem cannot represent POSIX
    execute bits; the release authority platform (macOS ARM64) always uses the
    full exec-bit-aware fingerprint.
    """
    reject_symlink_components(root, "source tree")
    root = root.resolve()
    digest = hashlib.sha256()
    count = 0
    for path in _release_paths(root):
        stat_result = path.stat()
        if stat_result.st_size > _MAX_FINGERPRINT_FILE_BYTES:
            raise ValueError(f"release fingerprint file exceeds size bound: {path}")
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        if include_executable_mode:
            digest.update(_normalized_git_mode(path))
        else:
            digest.update(b"100644")
        digest.update(stat_result.st_size.to_bytes(8, "big"))
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        count += 1
    if count == 0:
        raise ValueError("no release-relevant files found")
    return digest.hexdigest()
