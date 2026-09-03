from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from reprojudge.schema import load_task

ROOT = Path(__file__).resolve().parents[1]
SEED_MANIFEST = ROOT / "benchmarks/scientific-seed/manifest.json"
MAX_MANIFEST_BYTES = 256 * 1024
GITHUB_API = "https://api.github.com/repos/"


def _load_manifest() -> dict[str, Any]:
    if SEED_MANIFEST.is_symlink() or not SEED_MANIFEST.is_file():
        raise ValueError("scientific seed manifest is missing or unsafe")
    if SEED_MANIFEST.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("scientific seed manifest exceeds size bound")
    payload = json.loads(SEED_MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("scientific seed manifest must be an object")
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("scientific seed manifest tasks must be a list")
    return payload


def _canonical_urls() -> dict[str, str]:
    urls: dict[str, str] = {}
    for relative in _load_manifest()["tasks"]:
        path = ROOT / "benchmarks/scientific-seed" / relative
        task = load_task(path)
        check = task.checks[0]
        urls[task.task_id] = check.expected
    return urls


def _resolve(repository: str) -> tuple[str, str]:
    url = GITHUB_API + repository
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ReproJudge-canonical-drift-monitor",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return ("404", "")
        if exc.code == 301:
            return ("redirect", exc.headers.get("Location", ""))
        return (f"http-{exc.code}", "")
    except (urllib.error.URLError, OSError) as exc:
        return ("unreachable", str(exc))
    full_name = payload.get("full_name", "")
    archived = bool(payload.get("archived", False))
    status = "archived" if archived else "ok"
    return (status, full_name)


def check_canonical_drift() -> dict[str, Any]:
    canonical = _canonical_urls()
    drift: list[dict[str, str]] = []
    for task_id, url in sorted(canonical.items()):
        repository = url.removeprefix("https://github.com/")
        status, resolved = _resolve(repository)
        renamed = ""
        if resolved and resolved.lower() != repository.lower():
            renamed = resolved
        entry = {
            "task_id": task_id,
            "canonical_repository": repository,
            "status": status,
            "resolved_repository": renamed,
        }
        if status not in ("ok", "archived"):
            drift.append(entry)
        elif renamed:
            drift.append(entry)
    return {"canonical_repositories": len(canonical), "drift": drift}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect canonical benchmark repository rename, transfer, 404, or archive drift."
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    result = check_canonical_drift()
    if not args.quiet:
        print(json.dumps(result, indent=2, sort_keys=True))
    if result["drift"]:
        for entry in result["drift"]:
            print(
                f"FAIL: canonical drift for {entry['task_id']}: "
                f"{entry['canonical_repository']} -> {entry['status']} {entry['resolved_repository']}"
            )
        return 1
    print(
        f"PASS: canonical repository drift none across {result['canonical_repositories']} tasks"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
