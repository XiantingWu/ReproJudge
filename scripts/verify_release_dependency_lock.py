from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "release-lock/requirements-cp311-macos-arm64.txt"
_REQUIREMENT = re.compile(r"^(?P<name>[A-Za-z0-9._-]+)==(?P<version>[0-9][A-Za-z0-9.]+)(?P<hashes>(?:\s+--hash=sha256:[0-9a-f]{64})*)\s*$")


def _load_lock(path: Path) -> dict[str, dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"release dependency lock is missing: {path}")
    locked: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _REQUIREMENT.fullmatch(stripped)
        if not match:
            raise ValueError(f"invalid lock line {line_number}: {stripped}")
        name = match.group("name").lower().replace("_", "-")
        hashes = re.findall(r"sha256:[0-9a-f]{64}", match.group("hashes"))
        if not hashes:
            raise ValueError(f"lock entry lacks hashes: {stripped}")
        locked[name] = {"version": match.group("version"), "hashes": set(hashes)}
    if not locked:
        raise ValueError("release dependency lock is empty")
    return locked


def _regenerate_report() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "report.json"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--dry-run",
                "--ignore-installed",
                "--no-cache-dir",
                "--report",
                str(report),
                "-e",
                ".[dev]",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise ValueError(f"pip dry-run failed: {result.stderr[-2000:]}")
        return json.loads(report.read_text(encoding="utf-8"))


def verify_release_dependency_lock(path: Path = LOCK) -> list[str]:
    locked = _load_lock(path)
    report = _regenerate_report()
    errors: list[str] = []
    seen: set[str] = set()
    for item in report.get("install", []):
        metadata = item.get("metadata") or {}
        name = str(metadata.get("name", "")).lower().replace("_", "-")
        version = metadata.get("version")
        if name in {"reprojudge"}:
            continue
        seen.add(name)
        if name not in locked:
            errors.append(f"unlocked transitive dependency resolved: {name}=={version}")
            continue
        if version != locked[name]["version"]:
            errors.append(
                f"dependency version drift: {name}=={version} expected {locked[name]['version']}"
            )
        hashes = set()
        download_info = item.get("download_info") or {}
        archive_info = download_info.get("archive_info") or {}
        for algorithm, digest in (archive_info.get("hashes") or {}).items():
            hashes.add(f"{algorithm}:{digest}")
        if not hashes or not hashes & locked[name]["hashes"]:
            errors.append(f"dependency hash mismatch: {name}=={version}")
    for name in locked:
        if name not in seen:
            errors.append(f"locked dependency no longer resolved: {name}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the release-lane --require-hashes lock matches the resolved dependency graph."
    )
    parser.add_argument("--lock", type=Path, default=LOCK)
    args = parser.parse_args()
    try:
        errors = verify_release_dependency_lock(args.lock)
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 1
    for error in errors:
        print(f"FAIL: {error}")
    if errors:
        return 1
    print(f"PASS: release dependency lock matches resolved graph ({args.lock.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
