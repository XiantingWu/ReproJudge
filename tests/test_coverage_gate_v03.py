from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check_coverage_thresholds import check_coverage


def _report(path: Path, **totals: int) -> Path:
    defaults = {
        "num_statements": 100,
        "covered_lines": 90,
        "num_branches": 100,
        "covered_branches": 85,
    }
    defaults.update(totals)
    path.write_text(json.dumps({"totals": defaults}), encoding="utf-8")
    return path


def test_coverage_gate_accepts_threshold_edges(tmp_path: Path) -> None:
    statements, branches = check_coverage(_report(tmp_path / "coverage.json"))
    assert statements == 90.0
    assert branches == 85.0


def test_coverage_gate_reports_statement_and_branch_failures_separately(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="statement coverage"):
        check_coverage(
            _report(tmp_path / "statements.json", covered_lines=89, covered_branches=100)
        )
    with pytest.raises(ValueError, match="branch coverage"):
        check_coverage(
            _report(tmp_path / "branches.json", covered_lines=100, covered_branches=84)
        )


def test_coverage_gate_rejects_malformed_or_impossible_reports(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="totals"):
        check_coverage(invalid)

    with pytest.raises(ValueError, match="non-negative integer"):
        check_coverage(_report(tmp_path / "negative.json", covered_lines=-1))

    with pytest.raises(ValueError, match="impossible"):
        check_coverage(_report(tmp_path / "impossible.json", covered_lines=101))


def test_coverage_gate_handles_zero_denominators(tmp_path: Path) -> None:
    statements, branches = check_coverage(
        _report(
            tmp_path / "empty.json",
            num_statements=0,
            covered_lines=0,
            num_branches=0,
            covered_branches=0,
        )
    )
    assert statements == branches == 100.0
