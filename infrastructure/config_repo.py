"""Read/write config YAML. Infrastructure layer."""

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG: dict[str, Any] = {
    "module": "cpu",
    "hotkey_record": "Ctrl+F2",  # запись
    "hotkey_stop": "Ctrl+F3",  # стоп
    "whisper_cpp_path_cpu": "",
    "whisper_cpp_path_cuda": "",
    "whisper_cpp_path_amd": "",
    "whisper_model_path": "",
    "language": "ru",
    "input_device": None,  # None = системный по умолчанию, иначе PortAudio-индекс
    "input_device_name": None,  # имя устройства — для поиска при смене индекса
    "notifications": False,  # всплывающие уведомления Windows (по умолчанию выключены)
    # Whisper параметры качества
    "whisper_beam_size": 5,  # -bs: сколько вариантов beam search (больше = точнее, медленнее)
    "whisper_best_of": 5,  # -bo: сколько кандидатов сравнивать (для non-greedy)
    "whisper_prompt": "",  # --prompt: подсказка модели (имена, термины, стиль речи)
    "whisper_vad": True,  # --vad: только если есть файл модели (см. whisper_vad_model_path)
    "whisper_vad_model_path": "models/ggml-silero-v6.2.0.bin",  # -vm; скачать: roma-stt.bat download-vad
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
    # Устаревшие ключи — не используем и не сохраняем
    out.pop("hotkey", None)
    out.pop("postprocess", None)  # постобработка всегда включена в main.py
    return out


def save_config(config_path: str | Path, config: dict[str, Any]) -> None:
    """Save config to YAML file."""
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(config, allow_unicode=True, default_flow_style=False), encoding="utf-8"
    )
