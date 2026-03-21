"""Сканирование свободных хоткеев (scripts.scan_hotkeys)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


def _load_scan_module(root: Path) -> Any:
    path = root / "scripts" / "scan_hotkeys.py"
    spec = importlib.util.spec_from_file_location("roma_stt_scan_hotkeys", path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scan_free_hotkeys(root: Path) -> tuple[list[str], list[tuple[str, str]]]:
    """Свободные комбинации и список занятых с причинами."""
    mod = _load_scan_module(root)
    return mod.scan_free_hotkeys()
