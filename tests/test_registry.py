from __future__ import annotations

import json

import pytest

from reprojudge.registry import TaskRegistry


def manifest(task_id):
    return {"task_id": task_id, "domain": "demo", "paper": "synthetic:test", "expected_artifacts": ["x.json"]}


def test_registry_discovers_sorted_tasks(tmp_path):
    (tmp_path / "b.json").write_text(json.dumps(manifest("b")), encoding="utf-8")
    (tmp_path / "a.json").write_text(json.dumps(manifest("a")), encoding="utf-8")
    registry = TaskRegistry.from_directory(tmp_path)
    assert [entry.task.task_id for entry in registry.entries()] == ["a", "b"]


def test_registry_rejects_duplicate_ids(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps(manifest("same")), encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "b.json").write_text(json.dumps(manifest("same")), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate task_id"):
        TaskRegistry.from_directory(tmp_path)
