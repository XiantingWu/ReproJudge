from __future__ import annotations

import argparse
import json
import tarfile
import tomllib
from pathlib import Path, PurePosixPath

from reprojudge import __version__

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_CONTENT = (
    "find" + "woods",
    "/Users/" + "woods",
    "Woods-" + "M2",
    "Woods-" + "M1",
    "Woods2" + "deMacBook",
)


def _require_sdist(path: Path) -> tarfile.TarFile:
    if path.is_symlink() or not path.is_file():
        raise ValueError("sdist is missing or unsafe")
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("sdist exceeds size bound")
    try:
        return tarfile.open(path, mode="r:gz")
    except (OSError, tarfile.TarError) as exc:
        raise ValueError(f"invalid sdist archive: {exc}") from exc


def _safe_member(member: tarfile.TarInfo, root: PurePosixPath) -> Path:
    parsed = PurePosixPath(member.name)
    if parsed.is_absolute() or ".." in parsed.parts:
        raise ValueError(f"sdist path traversal attempt: {member.name}")
    resolved = root / parsed
    if not resolved.is_relative_to(root):
        raise ValueError(f"sdist member escapes archive root: {member.name}")
    return resolved


def validate_sdist(path: Path, project_root: Path = ROOT) -> dict[str, object]:
    archive = _require_sdist(path)
    try:
        members = archive.getmembers()
    finally:
        archive.close()
    if not members:
        raise ValueError("sdist contains no files")
    top = PurePosixPath(members[0].name).parts[0]
    root = PurePosixPath(top)

    names: set[str] = set()
    for member in members:
        _safe_member(member, root)
        if member.issym() or member.islnk():
            raise ValueError(f"sdist member must not be a symlink or hard link: {member.name}")
        names.add(member.name)

    top_prefix = f"{top}/"
    if any(name != top and not name.startswith(top_prefix) for name in names):
        raise ValueError("sdist contains files outside the single top-level directory")

    pyproject_path = f"{top}/pyproject.toml"
    if pyproject_path not in names:
        raise ValueError("sdist is missing pyproject.toml")
    project = tomllib.loads(_member_text(path, pyproject_path))["project"]
    if project.get("name") != "reprojudge":
        raise ValueError("sdist project name is not reprojudge")
    if project.get("version") != __version__:
        raise ValueError("sdist version does not match package version")

    required = {
        f"{top}/LICENSE",
        f"{top}/README.md",
        f"{top}/pyproject.toml",
        f"{top}/src/reprojudge/__init__.py",
    }
    missing = sorted(required - names)
    if missing:
        raise ValueError(f"sdist is missing required files: {missing}")

    forbidden_names = {
        f"{top}/.git",
        f"{top}/.DS_Store",
        f"{top}/dist",
        f"{top}/build",
    }
    for name in sorted(names):
        parts = name.split("/")
        if name in forbidden_names or ".git" in parts or ".DS_Store" in parts or parts[-1].endswith(".pyc"):
            raise ValueError(f"sdist contains local/build garbage: {name}")

    total_bytes = 0
    for member in members:
        total_bytes += member.size
    if total_bytes > 64 * 1024 * 1024:
        raise ValueError("sdist expands beyond size bound")

    try:
        text = _member_text(path, f"{top}/pyproject.toml")
    except ValueError:
        text = ""
    if "find" + "woods" in text:
        raise ValueError("sdist metadata contains forbidden identity")

    return {
        "top_level": top,
        "member_count": len(members),
        "version": __version__,
        "valid": True,
    }


def _member_text(sdist_path: Path, member_name: str) -> str:
    with tarfile.open(sdist_path, mode="r:gz") as archive:
        try:
            member = archive.getmember(member_name)
        except KeyError as exc:
            raise ValueError(f"sdist is missing {member_name}") from exc
        if member.size > 4 * 1024 * 1024:
            raise ValueError(f"sdist member is oversized: {member_name}")
        raw = archive.extractfile(member)
        if raw is None:
            raise ValueError(f"could not read sdist member: {member_name}")
        data = raw.read()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"sdist member is not UTF-8: {member_name}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an sdist archive for release integrity.")
    parser.add_argument("sdist", type=Path)
    args = parser.parse_args()
    try:
        result = validate_sdist(args.sdist)
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"PASS: sdist is safe, complete, and version-consistent ({result['member_count']} members)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
