from __future__ import annotations

import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given, settings, strategies as st

from reprojudge.leaderboard import build_leaderboard
from reprojudge.schema import parse_task
from reprojudge.scoring import score_task

_SAFE_SEGMENT = st.from_regex(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,20}", fullmatch=True)
_FINITE_FLOAT = st.floats(
    min_value=-1_000_000,
    max_value=1_000_000,
    allow_nan=False,
    allow_infinity=False,
    width=64,
)
_JSON_SCALAR = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(2**31), max_value=2**31 - 1),
    _FINITE_FLOAT,
    st.text(alphabet=st.characters(exclude_categories=("Cs",)), max_size=40),
)
_JSON_VALUE = st.recursive(
    _JSON_SCALAR,
    lambda children: st.one_of(
        st.lists(children, max_size=5),
        st.dictionaries(_SAFE_SEGMENT, children, max_size=5),
    ),
    max_leaves=12,
)


@settings(max_examples=80, deadline=None)
@given(segment=_SAFE_SEGMENT, expected=_JSON_VALUE)
def test_schema_json_round_trip_is_invariant(segment: str, expected: object) -> None:
    artifact = f"nested/{segment}.json"
    task = parse_task(
        {
            "task_id": f"property-{segment}",
            "domain": "property",
            "paper": "synthetic:property",
            "expected_artifacts": [artifact],
            "checks": [
                {
                    "type": "json_equals",
                    "artifact": artifact,
                    "json_path": "value",
                    "expected": expected,
                }
            ],
            "metadata": {"seed": expected},
        }
    )
    serialized = json.dumps(task.to_dict(), sort_keys=True, allow_nan=False)
    reparsed = parse_task(json.loads(serialized))
    assert reparsed == task


@settings(max_examples=100, deadline=None)
@given(
    observed=_FINITE_FLOAT,
    target=_FINITE_FLOAT,
    tolerance=st.floats(
        min_value=0.0,
        max_value=1_000_000,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_numeric_scoring_is_deterministic_and_serialization_invariant(
    observed: float,
    target: float,
    tolerance: float,
) -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "metrics.json").write_text(
            json.dumps({"value": observed}, allow_nan=False), encoding="utf-8"
        )
        task = parse_task(
            {
                "task_id": "numeric-property",
                "domain": "property",
                "paper": "synthetic:numeric",
                "expected_artifacts": ["metrics.json"],
                "checks": [
                    {
                        "type": "json_numeric",
                        "artifact": "metrics.json",
                        "json_path": "value",
                        "target": target,
                        "abs_tol": tolerance,
                        "rel_tol": 0.0,
                    }
                ],
            }
        )
        first = score_task(task, root)
        second = score_task(task, root)
        round_tripped = parse_task(
            json.loads(json.dumps(task.to_dict(), allow_nan=False))
        )
        third = score_task(round_tripped, root)
        assert first == second == third


@settings(max_examples=100, deadline=None)
@given(
    observed=_FINITE_FLOAT,
    target=_FINITE_FLOAT,
    low=st.floats(
        min_value=0.0, max_value=10_000, allow_nan=False, allow_infinity=False
    ),
    delta=st.floats(
        min_value=0.0, max_value=10_000, allow_nan=False, allow_infinity=False
    ),
)
def test_widening_numeric_tolerance_is_monotone(
    observed: float,
    target: float,
    low: float,
    delta: float,
) -> None:
    high = low + delta
    if not math.isfinite(high):
        return
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "metrics.json").write_text(
            json.dumps({"value": observed}, allow_nan=False), encoding="utf-8"
        )

        def evaluate(abs_tol: float) -> bool:
            task = parse_task(
                {
                    "task_id": "tolerance-property",
                    "domain": "property",
                    "paper": "synthetic:tolerance",
                    "expected_artifacts": ["metrics.json"],
                    "checks": [
                        {
                            "type": "json_numeric",
                            "artifact": "metrics.json",
                            "json_path": "value",
                            "target": target,
                            "abs_tol": abs_tol,
                            "rel_tol": 0.0,
                        }
                    ],
                }
            )
            return score_task(task, root)[0].passed

        assert not evaluate(low) or evaluate(high)


@settings(max_examples=75, deadline=None)
@given(payload=_JSON_VALUE, extra=_JSON_VALUE)
def test_undeclared_evidence_cannot_change_score(payload: object, extra: object) -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "declared.json").write_text(
            json.dumps({"value": payload}, allow_nan=False), encoding="utf-8"
        )
        task = parse_task(
            {
                "task_id": "evidence-property",
                "domain": "property",
                "paper": "synthetic:evidence",
                "expected_artifacts": ["declared.json"],
                "checks": [
                    {
                        "type": "json_equals",
                        "artifact": "declared.json",
                        "json_path": "value",
                        "expected": payload,
                    }
                ],
            }
        )
        before = score_task(task, root)
        (root / "undeclared.json").write_text(
            json.dumps({"value": extra}, allow_nan=False), encoding="utf-8"
        )
        after = score_task(task, root)
        assert before == after


def test_leaderboard_tie_breaker_and_input_order_are_deterministic() -> None:
    rows = [
        {
            "task_id": "1",
            "status": "passed",
            "duration_seconds": 2.0,
            "telemetry": {"agent_name": "beta", "agent_version": "1"},
        },
        {
            "task_id": "2",
            "status": "passed",
            "duration_seconds": 1.0,
            "telemetry": {"agent_name": "alpha", "agent_version": "2"},
        },
        {
            "task_id": "3",
            "status": "passed",
            "duration_seconds": 3.0,
            "telemetry": {"agent_name": "alpha", "agent_version": "1"},
        },
    ]
    expected = build_leaderboard(rows)
    assert build_leaderboard(list(reversed(rows))) == expected
    assert [(row["agent"], row["version"]) for row in expected] == [
        ("alpha", "1"),
        ("alpha", "2"),
        ("beta", "1"),
    ]
