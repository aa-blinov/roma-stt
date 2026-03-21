"""Правки config.yaml для Control UI."""

from __future__ import annotations

from pathlib import Path

from infrastructure.config_repo import load_config, save_config


def set_hotkeys(root: Path, record: str, stop: str) -> tuple[bool, str]:
    record = record.strip()
    stop = stop.strip()
    if not record or not stop:
        return False, "Укажите обе комбинации (запись и стоп)."
    path = root / "config.yaml"
    cfg = load_config(path)
    cfg["hotkey_record"] = record
    cfg["hotkey_stop"] = stop
    save_config(path, cfg)
    return True, "Сохранено. Перезапустите службу в трее, чтобы применить."


def set_language(root: Path, lang: str) -> tuple[bool, str]:
    lang = lang.strip()
    if not lang:
        return False, "Введите код языка (например ru, en)."
    if lang == "russian":
        return False, 'Используйте код "ru", а не "russian".'
    if lang == "english":
        return False, 'Используйте код "en", а не "english".'
    path = root / "config.yaml"
    cfg = load_config(path)
    cfg["language"] = lang
    save_config(path, cfg)
    return True, f"Язык: {lang}"


def apply_hotkeys_from_scan(
    root: Path, free: list[str], record_choice: int | None, stop_choice: int | None
) -> tuple[bool, str]:
    """record_choice/stop_choice — 1-based индекс в списке free, или None = не менять."""
    path = root / "config.yaml"
    cfg = load_config(path)
    if record_choice is not None:
        if record_choice < 1 or record_choice > len(free):
            return False, "Некорректный номер для записи."
        cfg["hotkey_record"] = free[record_choice - 1]
    if stop_choice is not None:
        if stop_choice < 1 or stop_choice > len(free):
            return False, "Некорректный номер для стопа."
        cfg["hotkey_stop"] = free[stop_choice - 1]
    if record_choice is None and stop_choice is None:
        return False, "Выберите хотя бы одну комбинацию."
    save_config(path, cfg)
    return True, "Готово. Перезапустите службу в трее."
