"""Read/write config YAML. Infrastructure layer."""

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG: dict[str, Any] = {
    "module": "cpu",
    "hotkey": "Ctrl+F9",
    "whisper_cpp_path_cpu": "",
    "whisper_cpp_path_cuda": "",
    "whisper_cpp_path_amd": "",
    "whisper_model_path": "",
    "language": "ru",
}


def load_config(config_path: str | Path) -> dict[str, Any]:
    """Load config from YAML file. Returns defaults if file missing."""
    path = Path(config_path)
    if not path.exists():
        return dict(DEFAULT_CONFIG)
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    out = dict(DEFAULT_CONFIG)
    out.update(data)
    return out


def save_config(config_path: str | Path, config: dict[str, Any]) -> None:
    """Save config to YAML file."""
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(config, allow_unicode=True, default_flow_style=False), encoding="utf-8")
