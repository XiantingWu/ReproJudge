from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from reprojudge.registry import TaskRegistry

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "benchmarks/scientific-seed"


def test_scientific_seed_contains_fifteen_real_paper_discovery_tasks():
    registry = TaskRegistry.from_directory(SEED / "tasks")
    entries = registry.entries()
    assert len(entries) == 15
    assert len({entry.task.paper for entry in entries}) == 15
    assert len({entry.task.checks[0].expected for entry in entries}) == 15
    for entry in entries:
        task = entry.task
        assert task.task_id.startswith("repo-discovery-")
        assert task.expected_artifacts == ("discovery.json",)
        assert len(task.checks) == 1
        check = task.checks[0]
        assert check.type == "json_equals"
        assert check.artifact == "discovery.json"
        assert check.json_path == "repository_url"
        assert isinstance(check.expected, str) and check.expected.startswith("https://github.com/")
        assert set(task.metadata) == {"benchmark_shard", "evidence_url", "scope"}
        assert "curation_source" not in task.metadata
        assert task.metadata["evidence_url"] == f"https://arxiv.org/abs/{task.paper}"
        assert "scientific-seed" in task.tags
        assert "repository-discovery" in task.tags


def test_known_canonical_repository_gold_spellings_are_locked():
    registry = TaskRegistry.from_directory(SEED / "tasks")
    actual = {entry.task.task_id: entry.task.checks[0].expected for entry in registry.entries()}
    expected = {
        "repo-discovery-albert": "https://github.com/google-research/albert",
        "repo-discovery-clip": "https://github.com/openai/CLIP",
        "repo-discovery-jax-md": "https://github.com/jax-md/jax-md",
    }
    for task_id, repository_url in expected.items():
        assert actual[task_id] == repository_url


def test_scientific_seed_validator_emits_deterministic_identity():
    completed = subprocess.run(
        [sys.executable, "scripts/validate_scientific_seed.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["valid"] is True
    assert payload["case_count"] == 15
    assert payload["scope"] == "paper-to-canonical-public-repository discovery only"
    assert payload["curation_source_blob_sha"] == "73f65ca4e8a4eb62bc7443502466dda919776c03bae935278d5988496cee755d"
    assert len(payload["manifest_sha256"]) == 64
    assert len(payload["shard_sha256"]) == 64
    assert len(payload["tasks"]) == 15
    assert [item["task_id"] for item in payload["tasks"]] == sorted(
        item["task_id"] for item in payload["tasks"]
    )
