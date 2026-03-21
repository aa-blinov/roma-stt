"""Список моделей и выбор активной модели (скачивание + запись config)."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any


def _load_models_module(root: Path) -> Any:
    scripts = str(root / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    path = root / "scripts" / "models.py"
    spec = importlib.util.spec_from_file_location("roma_stt_models_facade", path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def list_model_rows(root: Path) -> list[dict[str, Any]]:
    """Индекс, имя, описание, скачана ли модель."""
    mod = _load_models_module(root)
    rows: list[dict[str, Any]] = []
    for i, name in enumerate(mod.ORDERED_NAMES, 1):
        rows.append(
            {
                "index": i,
                "name": name,
                "description": mod.MODELS_MANIFEST[name],
                "compare_hint": mod.MODEL_COMPARE_HINTS[name],
                "downloaded": mod._is_model_downloaded(name),
                "size_bytes": int(mod.MODEL_SIZE_BYTES[name]),
                "size_label": mod.format_model_size_bytes(int(mod.MODEL_SIZE_BYTES[name])),
            }
        )
    return rows


def run_models_use(
    root: Path,
    num_or_name: str,
    on_download_progress: Callable[[int, int], None] | None = None,
) -> tuple[bool, str]:
    """Выбрать/скачать модель (как «models.py use …»)."""
    spec = num_or_name.strip()
    if not spec:
        return False, "Введите номер или имя модели."
    py = root / ".venv" / "Scripts" / "python.exe"
    if not py.is_file():
        return False, "Нет .venv — сначала вкладка «Установка»."
    mod = _load_models_module(root)
    name, err = mod.parse_use_spec(spec)
    if err:
        return False, err
    return mod.download_and_activate_by_name(name, on_download_progress=on_download_progress)


def run_delete_model(root: Path, name: str) -> tuple[bool, str]:
    """Удалить скачанный файл модели с диска (как «удаление» в GUI)."""
    spec = name.strip()
    if not spec:
        return False, "Выберите модель в списке."
    mod = _load_models_module(root)
    if spec not in mod.ORDERED_NAMES:
        return False, f"Неизвестное имя модели: {spec!r}."
    return mod.delete_downloaded_model(spec)
