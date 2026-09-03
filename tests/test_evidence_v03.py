from __future__ import annotations

import os
from pathlib import Path

import pytest

from reprojudge.evidence import _release_paths, canonical_json_sha256, source_fingerprint
from reprojudge.schema import parse_task
from reprojudge.evidence import task_fingerprint


def test_canonical_json_hash_is_order_independent():
    assert canonical_json_sha256({"a": 1, "b": 2}) == canonical_json_sha256({"b": 2, "a": 1})


def test_task_fingerprint_is_stable():
    task = parse_task({"task_id":"a","domain":"d","paper":"p","expected_artifacts":[]})
    assert task_fingerprint(task) == task_fingerprint(task)


def test_source_fingerprint_excludes_promoted_evidence(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x=1\n", encoding="utf-8")
    first = source_fingerprint(tmp_path)
    (tmp_path / "benchmarks").mkdir()
    (tmp_path / "benchmarks" / "release-evidence-0.3.0.json").write_text("{}", encoding="utf-8")
    assert source_fingerprint(tmp_path) == first
    (tmp_path / "src" / "a.py").write_text("x=2\n", encoding="utf-8")
    assert source_fingerprint(tmp_path) != first


def test_source_fingerprint_does_not_hide_similarly_prefixed_benchmark(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "benchmarks").mkdir()
    first = source_fingerprint(tmp_path)
    (tmp_path / "benchmarks" / "release-evidence-notes.json").write_text("{}", encoding="utf-8")
    assert source_fingerprint(tmp_path) != first


def test_release_paths_use_platform_independent_relative_order(tmp_path: Path):
    (tmp_path / "config" / "rules").mkdir(parents=True)
    (tmp_path / "config" / "rules" / "policy.txt").write_text("x\n", encoding="utf-8")
    (tmp_path / "config" / "settings.txt").write_text("x\n", encoding="utf-8")
    paths = [path.relative_to(tmp_path).as_posix() for path in _release_paths(tmp_path)]
    assert paths == sorted(paths)


def test_source_fingerprint_covers_unknown_root_files(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x=1\n", encoding="utf-8")
    first = source_fingerprint(tmp_path)
    (tmp_path / "conftest.py").write_text("VALUE = 1\n", encoding="utf-8")
    assert source_fingerprint(tmp_path) != first


def test_nested_build_and_dist_directories_remain_release_relevant(tmp_path: Path):
    (tmp_path / "src" / "reprojudge" / "build").mkdir(parents=True)
    nested = tmp_path / "src" / "reprojudge" / "build" / "helper.py"
    nested.write_text("VALUE = 1\n", encoding="utf-8")
    first = source_fingerprint(tmp_path)
    nested.write_text("VALUE = 2\n", encoding="utf-8")
    assert source_fingerprint(tmp_path) != first

    (tmp_path / "src" / "reprojudge" / "dist").mkdir()
    nested_dist = tmp_path / "src" / "reprojudge" / "dist" / "runtime.py"
    second = source_fingerprint(tmp_path)
    nested_dist.write_text("VALUE = 3\n", encoding="utf-8")
    assert source_fingerprint(tmp_path) != second


def test_top_level_generated_build_and_dist_are_excluded(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("x=1\n", encoding="utf-8")
    first = source_fingerprint(tmp_path)
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "generated.txt").write_text("build\n", encoding="utf-8")
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "generated.whl").write_text("dist\n", encoding="utf-8")
    assert source_fingerprint(tmp_path) == first


def test_quality_tool_state_is_excluded_without_hiding_nested_source(tmp_path: Path):
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "core.py").write_text("VALUE = 1\n", encoding="utf-8")
    first = source_fingerprint(tmp_path)

    for directory in (".hypothesis", ".mypy_cache", ".ruff_cache", "htmlcov"):
        path = tmp_path / directory
        path.mkdir()
        (path / "state.bin").write_bytes(b"generated-state")
    (tmp_path / ".coverage").write_bytes(b"coverage-db")
    (tmp_path / ".coverage.worker-1").write_bytes(b"parallel-coverage-db")
    (tmp_path / "coverage.json").write_text("{}\n", encoding="utf-8")

    assert source_fingerprint(tmp_path) == first

    nested_cache_named_source = tmp_path / "src" / "pkg" / ".mypy_cache"
    nested_cache_named_source.mkdir()
    nested_file = nested_cache_named_source / "runtime.py"
    nested_file.write_text("VALUE = 2\n", encoding="utf-8")
    assert source_fingerprint(tmp_path) != first


@pytest.mark.skipif(os.name == "nt", reason="Windows does not expose POSIX execute-bit semantics")
def test_source_fingerprint_covers_executable_mode(tmp_path: Path):
    (tmp_path / "scripts").mkdir()
    script = tmp_path / "scripts" / "tool.sh"
    script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    script.chmod(0o644)
    non_executable = source_fingerprint(tmp_path)
    script.chmod(0o755)
    executable = source_fingerprint(tmp_path)
    assert executable != non_executable
