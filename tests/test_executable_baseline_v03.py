from __future__ import annotations

import json
from pathlib import Path

from scripts.run_executable_baseline import (
    DEFAULT_MANIFEST,
    EXPECTED_CLAIM,
    EXPECTED_SCOPE,
    run_executable_baseline,
)


def test_executable_baseline_runs_three_real_subprocess_cases(tmp_path: Path) -> None:
    output = tmp_path / "baseline"
    manifest = run_executable_baseline(DEFAULT_MANIFEST, output)

    assert manifest["scope"] == EXPECTED_SCOPE
    assert manifest["claim_boundary"] == EXPECTED_CLAIM
    assert manifest["case_count"] == 3
    assert manifest["gate_passed"] is True
    cases = manifest["cases"]
    assert isinstance(cases, list)
    assert {case["task_id"] for case in cases} == {
        "executable-digest",
        "executable-linear-fit",
        "executable-mean",
    }
    assert all(case["passed"] is True for case in cases)
    assert (output / "manifest.json").is_file()

    requests = list((output / "runs").rglob("request.json"))
    assert len(requests) == 3
    for request in requests:
        payload = json.loads(request.read_text(encoding="utf-8"))
        assert "checks" not in payload
        assert payload["metadata"]["operation"] in {"mean", "linear_fit", "sha256"}
