"""Repository root discovery and path resolution.

All filesystem paths in config should be expressed relative to the monorepo
root (the directory that contains ``docker-compose.yml``, ``api/``, ``webapp/``,
``db/``, and ``storage/``). This module finds that root from any working
directory so clones work on any machine without hard-coded absolute paths.
"""

from __future__ import annotations

import os
from pathlib import Path

_ROOT_MARKERS = ("docker-compose.yml", "api", "webapp", "db", "storage")


def find_project_root(*, start: Path | None = None) -> Path:
    """Return the monorepo root directory.

    Honors ``PROJECT_ROOT`` when set (used by ``scripts/start.py``). Otherwise
    walks upward from ``start`` (default: this file's location) until all marker
    paths exist.
    """

    env_root = os.environ.get("PROJECT_ROOT")
    if env_root:
        root = Path(env_root).expanduser().resolve()
        if not _is_project_root(root):
            raise RuntimeError(f"PROJECT_ROOT is not a valid repo root: {root}")
        return root

    current = (start or Path(__file__).resolve()).parent
    for candidate in (current, *current.parents):
        if _is_project_root(candidate):
            return candidate

    raise RuntimeError(
        "Could not locate project root (expected docker-compose.yml + api/ + webapp/ + db/ + storage/)"
    )


def _is_project_root(path: Path) -> bool:
    return all((path / marker).exists() for marker in _ROOT_MARKERS)


def resolve_from_root(relative: str | Path, *, root: Path | None = None) -> Path:
    """Resolve ``relative`` against the project root; leave absolute paths unchanged."""

    p = Path(relative)
    if p.is_absolute():
        return p.resolve()
    base = root or find_project_root()
    return (base / p).resolve()
