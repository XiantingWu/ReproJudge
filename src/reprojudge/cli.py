from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence

from . import __version__
from .evidence import source_fingerprint, task_fingerprint
from .leaderboard import build_leaderboard, leaderboard_csv, leaderboard_markdown
from .registry import TaskRegistry
from .reporting import load_results, markdown_summary, summarize
from .runner import run_task
from .schema import load_task
from .starter import create_starter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reprojudge",
        description="Neutral benchmark runner for scientific reproducibility agents",
    )
    parser.add_argument("--version", action="version", version=f"ReproJudge {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser(
        "init",
        help="create a minimal benchmark starter without overwriting existing files",
    )
    init.add_argument(
        "directory",
        type=Path,
        nargs="?",
        default=Path("reprojudge-starter"),
        help="empty or new directory to populate (default: reprojudge-starter)",
    )

    validate = subparsers.add_parser("validate", help="validate one benchmark task manifest")
    validate.add_argument("manifest", type=Path)

    registry = subparsers.add_parser("registry", help="validate and list a directory of task manifests")
    registry.add_argument("directory", type=Path)

    run = subparsers.add_parser(
        "run",
        help="run one task against an agent command",
        usage="reprojudge run [-h] [--output OUTPUT] [--cwd CWD] [--inherit-env] MANIFEST -- AGENT ...",
        epilog="Put the agent command after --; it receives the generated ReproJudge environment variables.",
    )
    run.add_argument("manifest", type=Path)
    run.add_argument("--output", type=Path, default=Path(".reprojudge/runs"))
    run.add_argument("--cwd", type=Path, default=Path.cwd())
    run.add_argument("--inherit-env", action="store_true")

    suite = subparsers.add_parser(
        "suite",
        help="run every manifest in a task directory against one agent command",
        usage="reprojudge suite [-h] [--output OUTPUT] [--cwd CWD] [--inherit-env] DIRECTORY -- AGENT ...",
        epilog="Put the agent command after --; it receives the generated ReproJudge environment variables.",
    )
    suite.add_argument("directory", type=Path)
    suite.add_argument("--output", type=Path, default=Path(".reprojudge/runs"))
    suite.add_argument("--cwd", type=Path, default=Path.cwd())
    suite.add_argument("--inherit-env", action="store_true")

    report = subparsers.add_parser("summarize", help="summarize result.json bundles under a directory")
    report.add_argument("directory", type=Path)
    report.add_argument("--format", choices=("json", "markdown"), default="markdown")

    leaderboard = subparsers.add_parser("leaderboard", help="aggregate results by agent identity")
    leaderboard.add_argument("directory", type=Path)
    leaderboard.add_argument("--format", choices=("json", "markdown", "csv"), default="markdown")

    fingerprint = subparsers.add_parser("fingerprint", help="print deterministic task or source fingerprints")
    fingerprint.add_argument("path", type=Path)
    fingerprint.add_argument("--source-tree", action="store_true")

    doctor = subparsers.add_parser("doctor", help="check local ReproJudge readiness")
    doctor.add_argument(
        "--strict",
        action="store_true",
        help="also verify writable temp storage and a child Python process boundary",
    )
    doctor.add_argument(
        "--require-docker",
        action="store_true",
        help="add Docker CLI availability to readiness checks for container-backed integrations",
    )

    return parser


def _split_agent_command(argv: Sequence[str] | None) -> tuple[list[str], list[str]]:
    raw = list(sys.argv[1:] if argv is None else argv)
    if "--" not in raw:
        return raw, []
    index = raw.index("--")
    return raw[:index], raw[index + 1:]


def _doctor(strict: bool, require_docker: bool) -> tuple[bool, dict[str, bool]]:
    checks = {
        "python_3_11_or_newer": sys.version_info >= (3, 11),
        "cwd_writable": os.access(Path.cwd(), os.W_OK),
        "utf8": sys.getdefaultencoding().lower() == "utf-8",
    }
    if strict:
        tmp = Path(tempfile.gettempdir())
        checks["temp_directory_writable"] = tmp.is_dir() and os.access(tmp, os.W_OK)
        try:
            child = subprocess.run(
                [sys.executable, "-I", "-c", "raise SystemExit(0)"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
            checks["child_process_boundary"] = child.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            checks["child_process_boundary"] = False
    if require_docker:
        checks["docker_cli"] = shutil.which("docker") is not None
    return all(checks.values()), checks


def main(argv: Sequence[str] | None = None) -> int:
    parser_argv, agent_command = _split_agent_command(argv)
    args = build_parser().parse_args(parser_argv)
    try:
        if args.command == "init":
            created = create_starter(args.directory)
            print(f"created ReproJudge starter: {args.directory}")
            for path in created:
                print(f"  {path}")
            print(
                "next: cd "
                f"{args.directory} && reprojudge run tasks/hello-reprojudge.json "
                "--output runs -- python3 agent.py"
            )
            return 0

        if args.command == "validate":
            task = load_task(args.manifest)
            print(
                json.dumps(
                    {
                        "valid": True,
                        "schema_version": task.schema_version,
                        "task_id": task.task_id,
                        "domain": task.domain,
                        "task_sha256": task_fingerprint(task),
                    },
                    indent=2,
                )
            )
            return 0

        if args.command == "registry":
            registry = TaskRegistry.from_directory(args.directory)
            print(
                json.dumps(
                    {
                        "valid": True,
                        "count": len(registry.entries()),
                        "tasks": [
                            {"task_id": entry.task.task_id, "sha256": entry.sha256}
                            for entry in registry.entries()
                        ],
                    },
                    indent=2,
                )
            )
            return 0

        if args.command in {"run", "suite"}:
            if not agent_command:
                raise ValueError("an agent command is required after --")
            if args.command == "run":
                tasks = [(load_task(args.manifest), args.manifest)]
            else:
                tasks = [
                    (entry.task, entry.path)
                    for entry in TaskRegistry.from_directory(args.directory).entries()
                ]
            results = []
            for task, _path in tasks:
                result, run_dir = run_task(
                    task,
                    agent_command,
                    output_root=args.output,
                    working_directory=args.cwd,
                    inherit_environment=args.inherit_env,
                )
                results.append(result.to_dict())
                print(f"{task.task_id}: {result.status} -> {run_dir}")
            summary = summarize(results)
            print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
            return 0 if summary.failed == 0 else 2

        if args.command == "summarize":
            summary = summarize(load_results(args.directory))
            if args.format == "json":
                print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
            else:
                print(markdown_summary(summary), end="")
            return 0

        if args.command == "leaderboard":
            rows = build_leaderboard(load_results(args.directory))
            if args.format == "json":
                print(json.dumps(rows, indent=2, sort_keys=True))
            elif args.format == "csv":
                print(leaderboard_csv(rows), end="")
            else:
                print(leaderboard_markdown(rows), end="")
            return 0

        if args.command == "fingerprint":
            if args.source_tree:
                print(source_fingerprint(args.path))
            else:
                print(task_fingerprint(load_task(args.path)))
            return 0

        if args.command == "doctor":
            ok, checks = _doctor(args.strict, args.require_docker)
            print(
                json.dumps(
                    {
                        "ok": ok,
                        "strict": args.strict,
                        "require_docker": args.require_docker,
                        "checks": checks,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0 if ok else 1
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"reprojudge: error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
