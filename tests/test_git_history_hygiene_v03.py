from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from scripts import check_git_history_hygiene as hygiene

ROOT = Path(__file__).resolve().parents[1]

XIANTING_NAME = "XiantingWu"
XIANTING_EMAIL = "319609216+XiantingWu@users.noreply.github.com"
GITHUB_COMMITTER = ("GitHub", "noreply@github.com")
WEBFLOW_COMMITTER = ("web-flow", "noreply@github.com")


def _git(cwd: Path, *args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=True, env=env)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", XIANTING_NAME)
    _git(repo, "config", "user.email", XIANTING_EMAIL)
    (repo / "README.md").write_text("canonical repository\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    return repo


def _commit(
    repo: Path,
    message: str,
    author: tuple[str, str] = (XIANTING_NAME, XIANTING_EMAIL),
    committer: tuple[str, str] = (XIANTING_NAME, XIANTING_EMAIL),
    trailers: list[str] | None = None,
) -> str:
    body = message
    if trailers:
        body = body + "\n\n" + "\n".join(trailers)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": author[0],
        "GIT_AUTHOR_EMAIL": author[1],
        "GIT_COMMITTER_NAME": committer[0],
        "GIT_COMMITTER_EMAIL": committer[1],
    }
    _git(repo, "commit", "-q", "--allow-empty", "-m", body, env=env)
    return _git_out(repo, "rev-parse", "HEAD")


def _git_out(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, check=True, text=True
    ).stdout.strip()


@pytest.mark.parametrize(
    "committer",
    [(XIANTING_NAME, XIANTING_EMAIL), GITHUB_COMMITTER, WEBFLOW_COMMITTER],
)
def test_allows_xiantingwu_author_with_legitimate_committer(
    tmp_path: Path, committer: tuple[str, str]
) -> None:
    repo = _init_repo(tmp_path)
    _commit(repo, "trusted change", committer=committer)
    ok, failures = hygiene.check_git_history_hygiene(repo)
    assert ok, failures


def test_rejects_dependabot_author_name(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _commit(
        repo,
        "Bump ruff from 0.16.3 to 0.16.4",
        author=("dependabot[bot]", "49699333+dependabot[bot]@users.noreply.github.com"),
        committer=GITHUB_COMMITTER,
    )
    ok, failures = hygiene.check_git_history_hygiene(repo)
    assert not ok
    assert any("bot author name" in f for f in failures)


def test_rejects_dependabot_author_email(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _commit(
        repo,
        "regular subject",
        author=("XiantingWu", "49699333+dependabot[bot]@users.noreply.github.com"),
        committer=GITHUB_COMMITTER,
    )
    ok, failures = hygiene.check_git_history_hygiene(repo)
    assert not ok
    assert any("bot author email" in f for f in failures)


def test_rejects_dependabot_co_author_trailer(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _commit(
        repo,
        "merged change",
        trailers=["Co-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>"],
    )
    ok, failures = hygiene.check_git_history_hygiene(repo)
    assert not ok
    assert any("co-author trailer" in f for f in failures)


def test_allows_message_text_mentioning_dependabot(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _commit(
        repo,
        "Merge pull request #1 from XiantingWu/dependabot/pip/ruff-0.16.4",
        committer=GITHUB_COMMITTER,
    )
    ok, failures = hygiene.check_git_history_hygiene(repo)
    assert ok, failures


def test_audit_backup_ref_does_not_gate_production_policy(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _commit(repo, "clean production commit", committer=GITHUB_COMMITTER)
    _git(repo, "branch", "audit/pre-attribution-rebuild")
    _git(repo, "switch", "-q", "audit/pre-attribution-rebuild")
    _commit(
        repo,
        "old bot history",
        author=("dependabot[bot]", "49699333+dependabot[bot]@users.noreply.github.com"),
        committer=GITHUB_COMMITTER,
    )
    _git(repo, "switch", "-q", "main")
    ok, failures = hygiene.check_git_history_hygiene(repo)
    assert ok, failures


def test_production_remote_ref_is_scanned(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    bare = tmp_path / "bare.git"
    _git(repo, "clone", "-q", "--bare", str(repo), str(bare))
    remote = tmp_path / "remote"
    _git(repo, "clone", "-q", str(bare), str(remote))
    _commit(
        remote,
        "bot on production remote",
        author=("dependabot[bot]", "49699333+dependabot[bot]@users.noreply.github.com"),
        committer=GITHUB_COMMITTER,
    )
    _git(remote, "push", "-q", "origin", "main")
    _git(repo, "remote", "add", "origin", str(bare))
    _git(repo, "fetch", "-q", "origin")
    ok, failures = hygiene.check_git_history_hygiene(repo)
    assert not ok
    assert any("bot author" in f for f in failures)