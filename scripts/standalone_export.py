from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from reprojudge.evidence import _RELEASE_EVIDENCE, release_path_excluded, source_fingerprint
from reprojudge._paths import reject_symlink_components

ROOT = Path(__file__).resolve().parents[1]


def export_standalone(destination: Path) -> dict[str, object]:
    source = ROOT.resolve()
    reject_symlink_components(destination, "standalone export destination")
    destination = destination.resolve()
    if destination == source or source in destination.parents:
        raise ValueError("standalone export destination must be outside the source tree")
    if destination.exists():
        if not destination.is_dir():
            raise ValueError("standalone export destination must be a directory")
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    copied = 0
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if release_path_excluded(relative):
            continue
        if _RELEASE_EVIDENCE.fullmatch(relative.as_posix()):
            continue
        if path.is_symlink():
            raise ValueError(f"standalone export refuses symlink: {relative.as_posix()}")
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            # copy2 deliberately preserves executable semantics; the release
            # fingerprint verifies those semantics as well as file bytes.
            shutil.copy2(path, target)
            copied += 1
    source_sha = source_fingerprint(source)
    export_sha = source_fingerprint(destination)
    if source_sha != export_sha:
        raise ValueError(
            f"standalone export fingerprint mismatch: source={source_sha} export={export_sha}"
        )
    return {"files": copied, "source_tree_sha256": source_sha}


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a symlink-free standalone ReproJudge export.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = export_standalone(args.output)
    print(
        f"standalone export PASS files={result['files']} "
        f"source_tree_sha256={result['source_tree_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
