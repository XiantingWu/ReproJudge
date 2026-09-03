from __future__ import annotations

import tempfile
from pathlib import Path

_SYSTEM_INDIRECTIONS = frozenset(
    Path(p) for p in ("/private/tmp", "/private/var", "/private/etc")
) | {Path(tempfile.gettempdir()).resolve()}


def _resolves_to_system_indirection(current: Path) -> bool:
    try:
        return current.resolve() in _SYSTEM_INDIRECTIONS
    except OSError:
        return False


def reject_symlink_components(path: Path, label: str) -> None:
    current = path.absolute()
    while True:
        if current.is_symlink():
            if _resolves_to_system_indirection(current):
                return
            raise ValueError(f"{label} must not be a symlink or contain symlink components: {path}")
        if current.parent == current:
            return
        current = current.parent