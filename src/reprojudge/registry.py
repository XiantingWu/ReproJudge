from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ._paths import reject_symlink_components
from .evidence import task_fingerprint
from .schema import BenchmarkTask, load_task

MAX_REGISTRY_TASKS = 10000


@dataclass(frozen=True)
class RegisteredTask:
    task: BenchmarkTask
    path: Path
    sha256: str


class TaskRegistry:
    def __init__(self, entries: tuple[RegisteredTask, ...]) -> None:
        ids = [entry.task.task_id for entry in entries]
        duplicates = sorted({item for item in ids if ids.count(item) > 1})
        if duplicates:
            raise ValueError("duplicate task_id values: " + ", ".join(duplicates))
        self._entries = tuple(sorted(entries, key=lambda item: item.task.task_id))

    @classmethod
    def from_directory(cls, root: Path) -> "TaskRegistry":
        reject_symlink_components(root, "task directory")
        if root.is_symlink():
            raise ValueError("task directory must not be a symlink")
        root = root.resolve()
        if not root.is_dir():
            raise ValueError(f"task directory does not exist: {root}")
        entries: list[RegisteredTask] = []
        for path in sorted(root.rglob("*.json")):
            if len(entries) >= MAX_REGISTRY_TASKS:
                raise ValueError(f"task registry exceeds {MAX_REGISTRY_TASKS} manifests")
            relative = path.relative_to(root)
            current = root
            unsafe = False
            for part in relative.parts:
                current = current / part
                if current.is_symlink():
                    unsafe = True
                    break
            if unsafe:
                raise ValueError(f"task registry contains symlinked path: {relative.as_posix()}")
            task = load_task(path)
            entries.append(RegisteredTask(task, path, task_fingerprint(task)))
        if not entries:
            raise ValueError(f"no task manifests found under {root}")
        return cls(tuple(entries))

    def entries(self) -> tuple[RegisteredTask, ...]:
        return self._entries

    def get(self, task_id: str) -> RegisteredTask:
        for entry in self._entries:
            if entry.task.task_id == task_id:
                return entry
        raise KeyError(task_id)
