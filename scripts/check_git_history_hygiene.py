from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_TERMS = (
    "find" + "woods",
    "/Users/" + "woods",
    "Woods-" + "M2",
    "Woods-" + "M1",
    "Woods2" + "deMacBook",
    "backup/" + "pre-sync",
    "reprojudge-" + "ci",
    "reprojudge-" + "release",
    "repo-" + "reprojudge",
    "329758" + "39765",
    "329889" + "12875",
    "332745" + "20808",
    "332745" + "20776",
    "325233" + "14161",
    "Repo1-" + "VeriRepro",
    "Repository1-" + "ReproAgent",
)
_ALL_REF_PATTERN = re.compile(r"^[0-9a-f]{40}$")

NON_PRODUCTION_REF_NAMESPACES = (
    "refs/heads/audit/",
    "refs/heads/backup/",
    "refs/heads/rewrite/",
    "refs/heads/temp/",
    "refs/heads/archive/",
    "refs/heads/scratch/",
)

DEPENDABOT_TOKEN = "dependabot"


def _run(cmd: list[str], cwd: Path = ROOT) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True)
    return result.stdout


def _reachable_starts() -> list[str]:
    """Return commit starts to traverse: local refs, tags, then detached HEAD."""
    names = _run(["git", "for-each-ref", "--format=%(refname)", "refs/heads", "refs/tags"])
    hashes = _run(["git", "for-each-ref", "--format=%(objectname)", "refs/heads", "refs/tags"])
    starts = [line for line in hashes.splitlines() if _ALL_REF_PATTERN.fullmatch(line)]
    if not starts:
        head = _run(["git", "rev-parse", "--verify", "HEAD"]).strip()
        if _ALL_REF_PATTERN.fullmatch(head):
            starts.append(head)
            names.append("HEAD")
    return starts


def _production_starts(cwd: Path = ROOT) -> list[str]:
    """Commit starts for the current production/default history.

    Production refs are remote-tracking refs plus local branches outside the
    explicit audit/backup/rewrite namespaces.  Audit backups deliberately keep
    pre-rebuild history reachable locally and must not gate production policy.
    """
    refs = _run(
        ["git", "for-each-ref", "--format=%(refname)", "refs/remotes/origin", "refs/heads"],
        cwd=cwd,
    ).splitlines()
    starts: list[str] = []
    for name in refs:
        if name == "refs/remotes/origin/HEAD":
            continue
        if name.startswith(NON_PRODUCTION_REF_NAMESPACES):
            continue
        oid = _run(["git", "rev-parse", "--verify", name], cwd=cwd).strip()
        if _ALL_REF_PATTERN.fullmatch(oid):
            starts.append(oid)
    if not starts:
        head = _run(["git", "rev-parse", "--verify", "HEAD"], cwd=cwd).strip()
        if _ALL_REF_PATTERN.fullmatch(head):
            starts.append(head)
    return list(dict.fromkeys(starts))


def _check_production_attribution(cwd: Path = ROOT) -> list[str]:
    """Reject bot attribution (Author / Co-authored-by) on production history.

    Committer identity is deliberately not restricted: GitHub <noreply@github.com>
    and web-flow committers are legitimate provenance.  Ordinary message text
    mentioning Dependabot (for example a merge subject referencing a Dependabot
    branch) is not attribution and is allowed.
    """
    starts = _production_starts(cwd)
    if not starts:
        return []
    failures: list[str] = []
    authors = _run(["git", "log", "--format=%H%x09%an%x09%ae"] + starts, cwd=cwd)
    for line in authors.splitlines():
        oid, author_name, author_email = line.split("\t")
        if DEPENDABOT_TOKEN in author_name.lower():
            failures.append(f"production commit {oid} has bot author name {author_name!r}")
        if DEPENDABOT_TOKEN in author_email.lower():
            failures.append(f"production commit {oid} has bot author email {author_email!r}")
    messages = _run(["git", "log", "--format=%H%n%B%n---"] + starts, cwd=cwd)
    current_oid = ""
    pending_oid = True
    for line in messages.splitlines():
        if pending_oid:
            current_oid = line
            pending_oid = False
            continue
        if line == "---":
            pending_oid = True
            continue
        if line.lower().startswith("co-authored-by") and DEPENDABOT_TOKEN in line.lower():
            failures.append(
                f"production commit {current_oid or '?'} carries bot co-author trailer"
            )
    return failures


def check_git_history_hygiene(root: Path = ROOT) -> tuple[bool, list[str]]:
    failures: list[str] = []
    try:
        starts = _reachable_starts()
    except (subprocess.CalledProcessError, OSError) as exc:
        return False, [f"could not enumerate reachable refs: {exc}"]
    if not starts:
        return True, []

    try:
        log = _run(
            ["git", "log", "--format=%H%n%an%n%ae%n%cn%n%ce%n%s%n%B", "--all"]
        )
    except (subprocess.CalledProcessError, OSError) as exc:
        return False, [f"could not read git history: {exc}"]
    for line in log.splitlines():
        for term in FORBIDDEN_TERMS:
            if term in line:
                failures.append(f"git history contains forbidden term {term!r}")

    try:
        blobs = _run(["git", "rev-list", "--objects", "--all"])
    except (subprocess.CalledProcessError, OSError) as exc:
        return False, [f"could not enumerate reachable objects: {exc}"]
    blob_hashes = [
        line.split()[0]
        for line in blobs.splitlines()
        if len(line.split()) == 2 and _ALL_REF_PATTERN.fullmatch(line.split()[0])
    ]
    for blob_hash in blob_hashes:
        try:
            raw = subprocess.run(
                ["git", "cat-file", "blob", blob_hash],
                cwd=root,
                capture_output=True,
                check=True,
            ).stdout
        except (subprocess.CalledProcessError, OSError):
            continue
        if b"find" + b"woods" in raw.lower():
            failures.append(f"reachable blob {blob_hash} contains the forbidden identity")

    try:
        failures.extend(_check_production_attribution(root))
    except (subprocess.CalledProcessError, OSError) as exc:
        return False, [f"could not audit production attribution: {exc}"]

    return (not failures, failures)


def main() -> int:
    ok, failures = check_git_history_hygiene()
    for failure in failures[:100]:
        print(f"FAIL: {failure}")
    if not ok:
        print(f"FAIL: git history hygiene violations={len(failures)}")
        return 1
    print("PASS: git history hygiene violations=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
