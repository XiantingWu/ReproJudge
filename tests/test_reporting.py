from reprojudge.reporting import markdown_summary, summarize


def test_summary_counts_statuses():
    summary = summarize([
        {"task_id": "a", "status": "passed", "duration_seconds": 1.0},
        {"task_id": "b", "status": "failed", "duration_seconds": 3.0},
    ])
    assert summary.total == 2
    assert summary.passed == 1
    assert summary.pass_rate == 0.5
    assert summary.mean_duration_seconds == 2.0
    assert "Pass rate: 50.0%" in markdown_summary(summary)
