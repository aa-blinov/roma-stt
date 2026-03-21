"""Удаление установки (.venv, models). Полная установка — через scripts/install.py (GUI: QProcess)."""

from __future__ import annotations

import shutil
from pathlib import Path


def remove_venv_and_models(root: Path) -> tuple[bool, str]:
    """Удалить `.venv` и `models`. Перед этим остановите службу (трей)."""
    removed: list[str] = []
    for name in (".venv", "models"):
        p = root / name
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
            removed.append(name)
    if not removed:
        return True, "Папок .venv и models не было."
    return True, "Удалено: " + ", ".join(removed)
