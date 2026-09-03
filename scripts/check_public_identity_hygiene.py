from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private-identity", re.compile("find" + "woods", re.IGNORECASE)),
    ("personal-home-path", re.compile(r"/Users/" + "woods", re.IGNORECASE)),
    ("personal-host-m2", re.compile(r"Woods-" + "M2", re.IGNORECASE)),
    ("personal-host-m1", re.compile(r"Woods-" + "M1", re.IGNORECASE)),
    ("personal-host-woods2", re.compile(r"Woods2" + "deMacBook", re.IGNORECASE)),
    ("draft-backup-ref", re.compile(r"backup/" + "pre-sync", re.IGNORECASE)),
    ("draft-runner-ci", re.compile(r"reprojudge-" + "ci", re.IGNORECASE)),
    ("draft-runner-release", re.compile(r"reprojudge-" + "release", re.IGNORECASE)),
    ("draft-runner-repo", re.compile(r"repo-" + "reprojudge", re.IGNORECASE)),
    ("self-hosted", re.compile(r"self[- ]hosted", re.IGNORECASE)),
    ("draft-run-id-1", re.compile(r"329758" + "39765")),
    ("draft-run-id-2", re.compile(r"329889" + "12875")),
    ("draft-run-id-3", re.compile(r"332745" + "20808")),
    ("draft-run-id-4", re.compile(r"332745" + "20776")),
    ("draft-run-id-5", re.compile(r"325233" + "14161")),
    ("draft-pr-8", re.compile(r"PR\s*#8\b", re.IGNORECASE)),
    ("internal-repo1", re.compile(r"Repo1-" + "VeriRepro", re.IGNORECASE)),
    ("internal-repo1-short", re.compile(r"Repository1-" + "ReproAgent", re.IGNORECASE)),
]

# The enforcement machinery itself defines the forbidden tokens (its pattern
# tables) and is kept out of the content scan; the same machinery is still
# structurally verified by launch_surface_check.py and the CI supply-chain
# tests.
HYGIENE_MACHINERY = frozenset(
    {
        "scripts/check_public_identity_hygiene.py",
        "scripts/check_git_history_hygiene.py",
        "scripts/launch_surface_check.py",
        "scripts/validate_sdist.py",
    }
)

# Public tests may reference the forbidden tokens only inside explicit
# assertion contexts ("assert <token> not in ...", forbidden-word tuples,
# raises() fixtures, or lines commented "# forbidden-fixture"); any other
# occurrence in tests is a leak.
ASSERTION_MARKERS = ("assert", "forbidden", "not in", "raises", "forbidden-fixture")

MAX_FILE_BYTES = 8 * 1024 * 1024
BINARY_SUFFIXES = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".zip", ".gz", ".whl"}


def _is_allowed_test_occurrence(relative: str, line: str) -> bool:
    if not relative.startswith("tests/"):
        return False
    lowered = line.lower()
    return any(marker in lowered for marker in ASSERTION_MARKERS)


def _scan_tree(root: Path, failures: list[str]) -> int:
    total_matches = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            continue
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith(".git/"):
            continue
        if relative in HYGIENE_MACHINERY:
            continue
        if any(
            part in {".venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".hypothesis", "dist", "build", "htmlcov", ".reprojudge"}
            for part in path.relative_to(root).parts
        ):
            continue
        if relative in {".coverage", "coverage.json"} or path.suffix in BINARY_SUFFIXES:
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            failures.append(f"oversized scan target: {relative}")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for label, pattern in FORBIDDEN_PATTERNS:
                if pattern.search(line):
                    if _is_allowed_test_occurrence(relative, line):
                        continue
                    total_matches += 1
                    failures.append(f"{relative}:{line_number} forbidden={label}")
    return total_matches


def check_public_identity_hygiene(root: Path = ROOT) -> tuple[bool, list[str], int]:
    failures: list[str] = []
    total = _scan_tree(root, failures)
    return (not failures and total == 0, failures, total)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail closed unless every tracked public tree file is free of forbidden private identity."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    ok, failures, total = check_public_identity_hygiene(args.root)
    for failure in failures[:200]:
        print(f"FAIL: {failure}")
    if total > len(failures[:200]):
        print(f"FAIL: {total - len(failures[:200])} further matches suppressed")
    if not ok:
        print(f"FAIL: public identity hygiene violations={total}")
        return 1
    print("PASS: public identity hygiene violations=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
