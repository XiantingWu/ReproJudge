from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

MAX_MANIFEST_BYTES = 4 * 1024 * 1024
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


def _load(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("reference manifest must be a regular file")
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("reference manifest exceeds size bound")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid reference manifest: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("reference manifest must be an object")
    return payload


def expected_trusted_provenance() -> dict[str, str]:
    head = _measured_source_head()
    return {
        "measured_source_head_sha": head,
        "runner_environment": "local",
        "runner_os": "local",
        "runner_arch": "local",
    }


def _measured_source_head() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("cannot resolve the measured source head from local Git") from exc
    head = result.stdout.strip()
    if not _GIT_SHA.fullmatch(head):
        raise ValueError("measured source head must be a lowercase 40-character Git SHA")
    return head


def validate_reference_provenance(path: Path) -> None:
    manifest = _load(path)
    provenance = manifest.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("reference manifest provenance is missing")
    expected = expected_trusted_provenance()
    if provenance.get("measured_source_head_sha") != expected["measured_source_head_sha"]:
        raise ValueError(
            "reference manifest provenance does not match the current local exact-head run"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bind a reference manifest to the current local exact-head run."
    )
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        validate_reference_provenance(args.manifest)
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 1
    print("PASS: reference manifest provenance matches current local exact-head run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())