"""Tests for repo-root path resolution."""

from __future__ import annotations

from pathlib import Path

from src.core.paths import find_project_root, resolve_from_root


def test_find_project_root_has_markers() -> None:
    root = find_project_root()
    assert (root / "docker-compose.yml").is_file()
    assert (root / "api" / "src").is_dir()
    assert (root / "storage" / "uploads").is_dir()


def test_resolve_from_root_relative() -> None:
    root = find_project_root()
    resolved = resolve_from_root("storage/uploads", root=root)
    assert resolved == (root / "storage" / "uploads").resolve()


def test_settings_uploads_dir_is_absolute() -> None:
    from src.core.config import settings

    p = Path(settings.uploads_dir)
    assert p.is_absolute()
    assert p.name == "uploads"
