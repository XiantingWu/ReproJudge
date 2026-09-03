from reprojudge.schema import parse_task


def test_parse_task() -> None:
    task = parse_task(
        {
            "task_id": "demo-001",
            "domain": "machine-learning",
            "paper": "arXiv:2401.00001",
            "expected_artifacts": ["metrics.json"],
        }
    )
    assert task.task_id == "demo-001"
    assert task.expected_artifacts == ("metrics.json",)
