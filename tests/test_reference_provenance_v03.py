from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import validate_reference_provenance


def _manifest(path: Path, *, head: str = "a" * 40) -> Path:
    provenance = {
        "measured_source_head_sha": head,
        "runner_environment": "local",
        "runner_os": "local",
        "runner_arch": "local",
    }
    path.write_text(json.dumps({"provenance": provenance}), encoding="utf-8")
    return path


def test_reference_provenance_accepts_current_local_exact_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        validate_reference_provenance,
        "_measured_source_head",
        lambda: "a" * 40,
    )
    validate_reference_provenance.validate_reference_provenance(_manifest(tmp_path / "manifest.json"))


def test_reference_provenance_rejects_synthetic_merge_sha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        validate_reference_provenance,
        "_measured_source_head",
        lambda: "a" * 40,
    )
    path = _manifest(tmp_path / "manifest.json", head="b" * 40)
    with pytest.raises(ValueError, match="current local exact-head run"):
        validate_reference_provenance.validate_reference_provenance(path)


def test_reference_provenance_requires_valid_exact_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def bad_head() -> str:
        raise ValueError("cannot resolve the measured source head from local Git")

    monkeypatch.setattr(validate_reference_provenance, "_measured_source_head", bad_head)
    with pytest.raises(ValueError, match="measured source head"):
        validate_reference_provenance.validate_reference_provenance(_manifest(tmp_path / "manifest.json"))