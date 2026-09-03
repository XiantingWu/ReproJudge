from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _percentage(covered: int, total: int) -> float:
    return 100.0 if total == 0 else (covered / total) * 100.0


def _require_count(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"coverage totals field {key!r} must be a non-negative integer")
    return value


def check_coverage(
    report_path: Path,
    *,
    statement_threshold: float = 90.0,
    branch_threshold: float = 85.0,
) -> tuple[float, float]:
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid coverage JSON: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("totals"), dict):
        raise ValueError("coverage JSON must contain an object-valued totals field")

    totals: dict[str, Any] = payload["totals"]
    statements = _require_count(totals, "num_statements")
    covered_statements = _require_count(totals, "covered_lines")
    branches = _require_count(totals, "num_branches")
    covered_branches = _require_count(totals, "covered_branches")
    if covered_statements > statements or covered_branches > branches:
        raise ValueError("coverage JSON contains impossible covered/total counts")

    statement_pct = _percentage(covered_statements, statements)
    branch_pct = _percentage(covered_branches, branches)
    print(
        "coverage gate: "
        f"statements={statement_pct:.2f}% ({covered_statements}/{statements}) "
        f"branches={branch_pct:.2f}% ({covered_branches}/{branches})"
    )

    failures: list[str] = []
    if statement_pct + 1e-12 < statement_threshold:
        failures.append(
            f"statement coverage {statement_pct:.2f}% is below {statement_threshold:.2f}%"
        )
    if branch_pct + 1e-12 < branch_threshold:
        failures.append(
            f"branch coverage {branch_pct:.2f}% is below {branch_threshold:.2f}%"
        )
    if failures:
        raise ValueError("; ".join(failures))
    return statement_pct, branch_pct


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail closed unless statement and branch coverage meet release thresholds."
    )
    parser.add_argument("report", type=Path)
    parser.add_argument("--statements", type=float, default=90.0)
    parser.add_argument("--branches", type=float, default=85.0)
    args = parser.parse_args()
    try:
        check_coverage(
            args.report,
            statement_threshold=args.statements,
            branch_threshold=args.branches,
        )
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
