"""Состояние для шапки меню / Control UI: конфиг в виде dict (без PS1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from infrastructure.config_repo import load_config


def get_menu_state(config_path: Path) -> dict[str, Any]:
    """Поля для отображения: язык, модель, хоткеи, модуль (cpu/cuda/amd)."""
    cfg = load_config(config_path)
    mp = cfg.get("whisper_model_path") or ""
    model_stem = Path(mp).stem if mp else ""
    return {
        "lang": cfg.get("language", "ru"),
        "model_stem": model_stem,
        "hotkey_record": cfg.get("hotkey_record", "Ctrl+F2"),
        "hotkey_stop": cfg.get("hotkey_stop", "Ctrl+F3"),
        "module": cfg.get("module", "cpu"),
    }
