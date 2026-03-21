"""Сводка для шапки окна (как верхняя часть меню roma-stt.ps1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from application.control.menu_state import get_menu_state
from application.control.readiness import get_readiness_summary
from application.control.service import get_service_status


def get_header_state(root: Path) -> dict[str, Any]:
    """Служба, режим, модель, хоткеи, язык, готовность."""
    cfg_path = root / "config.yaml"
    menu = get_menu_state(cfg_path)
    svc = get_service_status(root)
    ready_ok, ready_detail = get_readiness_summary(root)
    model_short = menu.get("model_stem") or ""
    if model_short.startswith("ggml-"):
        model_short = model_short[5:]
    return {
        **menu,
        **svc,
        "ready_ok": ready_ok,
        "ready_detail": ready_detail,
        "model_display": model_short or "?",
    }
