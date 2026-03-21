"""Фасады для Control UI и CLI: одна логика для PS1-меню, скриптов и PySide6."""

from application.control.audio_facade import (
    list_input_devices,
    reset_input_device_default,
    set_input_device_index,
)
from application.control.config_edits import (
    apply_hotkeys_from_scan,
    set_hotkeys,
    set_language,
)
from application.control.gpu_detect import available_whisper_archs, detect_gpu
from application.control.header_state import get_header_state
from application.control.hotkey_facade import scan_free_hotkeys
from application.control.install_actions import remove_venv_and_models
from application.control.menu_state import get_menu_state
from application.control.models_facade import list_model_rows, run_delete_model, run_models_use
from application.control.readiness import get_readiness_lines, get_readiness_summary
from application.control.service import (
    get_running_pid,
    get_service_status,
    start_tray_service,
    stop_tray_service,
)

__all__ = [
    "apply_hotkeys_from_scan",
    "available_whisper_archs",
    "detect_gpu",
    "get_header_state",
    "get_menu_state",
    "get_readiness_lines",
    "get_readiness_summary",
    "get_running_pid",
    "get_service_status",
    "list_input_devices",
    "list_model_rows",
    "remove_venv_and_models",
    "reset_input_device_default",
    "run_delete_model",
    "run_models_use",
    "scan_free_hotkeys",
    "set_hotkeys",
    "set_input_device_index",
    "set_language",
    "start_tray_service",
    "stop_tray_service",
]
