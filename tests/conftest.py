"""Общие фикстуры и настройка pytest для всего дерева `tests/`.

Фикстуры:
  project_root   — корень репозитория (родитель `tests/`).
  scripts_dir    — `project_root / "scripts"`.
  roma_tmp_layout — временный «корень проекта»: есть `models/` и `bin/`.
  write_yaml_config — функция: записать `config.yaml` (или другое имя) из str/dict.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml


def pytest_configure(config) -> None:  # noqa: ARG001
    """Добавляем `scripts/` в sys.path (импорты `whisper_models`, `models`, … в тестах)."""
    scripts = Path(__file__).resolve().parent.parent / "scripts"
    s = str(scripts)
    if s not in sys.path:
        sys.path.insert(0, s)


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def scripts_dir(project_root: Path) -> Path:
    return project_root / "scripts"


@pytest.fixture
def roma_tmp_layout(tmp_path: Path) -> Path:
    """Временный каталог с `models/` и `bin/` (как у установленного проекта)."""
    (tmp_path / "models").mkdir(parents=True)
    (tmp_path / "bin").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def write_yaml_config(tmp_path: Path) -> Callable[..., Path]:
    """Вернуть writer(path_relative = tmp_path / filename)."""

    def _write(
        data: str | dict[str, Any],
        *,
        filename: str = "config.yaml",
    ) -> Path:
        path = tmp_path / filename
        if isinstance(data, str):
            path.write_text(data, encoding="utf-8")
        else:
            path.write_text(
                yaml.dump(data, allow_unicode=True, default_flow_style=False),
                encoding="utf-8",
            )
        return path

    return _write


@pytest.fixture
def models_dir_path(roma_tmp_layout: Path) -> Path:
    """`roma_tmp_layout / "models"` (уже создан)."""
    return roma_tmp_layout / "models"
