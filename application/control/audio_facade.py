"""Список микрофонов и запись в config (scripts.list_audio_devices)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


def _load_audio_module(root: Path) -> Any:
    path = root / "scripts" / "list_audio_devices.py"
    spec = importlib.util.spec_from_file_location("roma_stt_list_audio", path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def list_input_devices(root: Path) -> list[dict[str, Any]]:
    mod = _load_audio_module(root)
    return mod.list_input_devices()


def set_input_device_index(root: Path, device_index: int) -> tuple[bool, str]:
    mod = _load_audio_module(root)
    return mod.set_input_device_index(device_index)


def reset_input_device_default(root: Path) -> tuple[bool, str]:
    mod = _load_audio_module(root)
    return mod.reset_input_device_default()
