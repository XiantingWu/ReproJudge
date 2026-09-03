from __future__ import annotations

import os
from pathlib import Path

import pytest

from reprojudge.evidence import _release_paths

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(os.name == "nt", reason="Windows does not expose POSIX execute-bit semantics")
def test_release_tree_has_only_deliberately_executable_files() -> None:
    executable = {
        path.relative_to(ROOT).as_posix()
        for path in _release_paths(ROOT)
        if path.stat().st_mode & 0o111
    }
    assert executable == set()
