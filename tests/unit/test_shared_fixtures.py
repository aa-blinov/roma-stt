"""Дымовая проверка общих фикстур из tests/conftest.py."""

from __future__ import annotations

from pathlib import Path


def test_project_root_points_at_repo(project_root: Path) -> None:
    assert (project_root / "pyproject.toml").is_file()
    assert (project_root / "main.py").is_file()


def test_scripts_dir_under_project(scripts_dir: Path, project_root: Path) -> None:
    assert scripts_dir == project_root / "scripts"
    assert (scripts_dir / "whisper_models.py").is_file()
