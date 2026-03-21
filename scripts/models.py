"""List available/downloaded models, set active model. For roma-stt.bat."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from whisper_models import (
    MODEL_COMPARE_HINTS,
    MODEL_DESCRIPTIONS,
    MODEL_SIZE_BYTES,
    ORDERED_MODEL_KEYS,
    format_model_size_bytes,
)

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"
CONFIG_PATH = ROOT / "config.yaml"

MODELS_MANIFEST = {k: MODEL_DESCRIPTIONS[k] for k in ORDERED_MODEL_KEYS}
ORDERED_NAMES = list(ORDERED_MODEL_KEYS)

# ANSI (Windows 10+ cmd/PowerShell поддерживают)
_GREEN = "\033[32m"  # скачана
_GRAY = "\033[90m"  # нет
_RESET = "\033[0m"


def _is_model_downloaded(name: str) -> bool:
    if not MODELS_DIR.is_dir():
        return False
    for stem in (f"ggml-{name}", name):
        if (MODELS_DIR / f"{stem}.bin").exists() or (MODELS_DIR / f"{stem}.ggml").exists():
            return True
    return False


def list_all() -> None:
    """Тот же состав строк, что на вкладке «Модель» в Control UI: размер HF, сравнение, статус."""
    use_color = sys.stdout.isatty()
    print(
        "Модели Whisper (формат как в окне управления). "
        "Номер: если скачана — выберется, если нет — скачается и выберется."
    )
    for i, name in enumerate(ORDERED_NAMES, 1):
        desc = MODELS_MANIFEST[name]
        size_label = format_model_size_bytes(int(MODEL_SIZE_BYTES[name]))
        cmp_hint = MODEL_COMPARE_HINTS[name]
        downloaded = _is_model_downloaded(name)
        status = "скачано" if downloaded else "не скачано"
        line = (
            f"  {i}. {name} — {desc}. "
            f"~{size_label} на диске (HF). {cmp_hint} ({status})"
        )
        if use_color:
            color = _GREEN if downloaded else _GRAY
            print(f"{color}{line}{_RESET}")
        else:
            print(line)


def set_active(name: str) -> None:
    path = MODELS_DIR / name
    if not path.exists():
        path = MODELS_DIR / f"ggml-{name}.ggml"
    if not path.exists():
        path = MODELS_DIR / f"ggml-{name}.bin"
    if not path.exists():
        path = MODELS_DIR / f"{name}.ggml"
    if not path.exists():
        path = MODELS_DIR / f"{name}.bin"
    if not path.exists():
        print(f"Model not found: {name}")
        sys.exit(1)
    _write_config_path(path)
    print(f"Active model set to: {path.name}")


def _write_config_path(path: Path) -> None:
    import yaml

    config = {}
    if CONFIG_PATH.exists():
        config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    config["whisper_model_path"] = str(path.resolve())
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        yaml.dump(config, allow_unicode=True, default_flow_style=False), encoding="utf-8"
    )


def _clear_whisper_model_path_in_config() -> None:
    import yaml

    config = {}
    if CONFIG_PATH.exists():
        config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    config["whisper_model_path"] = ""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        yaml.dump(config, allow_unicode=True, default_flow_style=False), encoding="utf-8"
    )


def _active_model_path_resolved() -> Path | None:
    import yaml

    if not CONFIG_PATH.exists():
        return None
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    raw = (config.get("whisper_model_path") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    if not p.is_absolute():
        p = ROOT / p
    return p.resolve()


def delete_downloaded_model(name: str) -> tuple[bool, str]:
    """Удалить скачанный файл модели. Если он был активным в config — сбросить whisper_model_path."""
    if name not in ORDERED_NAMES:
        return False, f"Неизвестное имя модели: {name!r}."
    if not _is_model_downloaded(name):
        return False, f"Модель «{name}» не скачана — удалять нечего."
    path = _path_for_model_name(name)
    if not path or not path.is_file():
        return False, f"Файл модели «{name}» не найден."
    active = _active_model_path_resolved()
    try:
        path.unlink()
    except OSError as e:
        return False, f"Не удалось удалить файл: {e}"
    lines = [f"Удалён файл: {path.name}."]
    if active is not None and path.resolve() == active:
        _clear_whisper_model_path_in_config()
        lines.append("Активная модель в config сброшена — выберите другую модель.")
    return True, "\n".join(lines)


def _path_for_model_name(name: str) -> Path | None:
    """Путь к файлу модели по имени из манифеста (если скачана)."""
    if not MODELS_DIR.is_dir():
        return None
    for stem, ext in [
        (f"ggml-{name}", ".bin"),
        (f"ggml-{name}", ".ggml"),
        (name, ".bin"),
        (name, ".ggml"),
    ]:
        p = MODELS_DIR / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def parse_use_spec(num_or_name: str) -> tuple[str | None, str | None]:
    """Разобрать номер или имя модели. Возвращает (имя, None) или (None, сообщение об ошибке)."""
    s = num_or_name.strip()
    if s in ORDERED_NAMES:
        return s, None
    try:
        num = int(s)
    except ValueError:
        return None, (
            f"Введите номер (1–{len(ORDERED_NAMES)}) или название модели "
            "(например base, large-v3-turbo)."
        )
    if num < 1 or num > len(ORDERED_NAMES):
        return None, f"Номер должен быть от 1 до {len(ORDERED_NAMES)}."
    return ORDERED_NAMES[num - 1], None


def download_and_activate_by_name(
    name: str,
    *,
    on_download_progress: Callable[[int, int], None] | None = None,
) -> tuple[bool, str]:
    """Скачать при необходимости и записать whisper_model_path в config. Без sys.exit."""
    if not _is_model_downloaded(name):
        print(f"Скачивание «{name}»...")
        from download_model import download as dm_download

        if not dm_download(name, MODELS_DIR, on_progress=on_download_progress):
            return False, "Не удалось скачать модель."
    path = _path_for_model_name(name)
    if not path:
        return False, f"Файл модели не найден после скачивания: {name}"
    _write_config_path(path)
    return True, f"Активная модель: {path.name}"


def set_active_by_number(num_str: str) -> None:
    """Выбрать активную модель по номеру из общего списка (1-based). Модель должна быть скачана."""
    try:
        num = int(num_str)
    except ValueError:
        print("Введите номер цифрой (1, 2, 3...).")
        sys.exit(1)
    if num < 1 or num > len(ORDERED_NAMES):
        print(f"Номер должен быть от 1 до {len(ORDERED_NAMES)}.")
        sys.exit(1)
    name = ORDERED_NAMES[num - 1]
    path = _path_for_model_name(name)
    if not path:
        print(f"Модель «{name}» не скачана. Сначала скачайте: пункт 4 (модели), номер {num}.")
        sys.exit(1)
    _write_config_path(path)
    print(f"Активная модель: {path.name}")


def use_by_number(num_or_name: str) -> None:
    """По номеру или названию: если модель скачана — выбрать активной; если нет — скачать и выбрать."""
    name, err = parse_use_spec(num_or_name)
    if err:
        print(err)
        sys.exit(1)
    ok, msg = download_and_activate_by_name(name)
    if not ok:
        print(msg)
        sys.exit(1)
    print(msg)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("list-all", help="One list of models with downloaded status")
    p_set = sub.add_parser("set")
    p_set.add_argument("name", help="Model file name or base name")
    p_set_num = sub.add_parser("set-by-number")
    p_set_num.add_argument("num", help="Number from list-all (1-based), model must be downloaded")
    p_use = sub.add_parser("use")
    p_use.add_argument(
        "num",
        help=f"Number 1–{len(ORDERED_NAMES)}: set active if downloaded, else download then set",
    )
    args = parser.parse_args()
    if args.cmd == "list-all":
        list_all()
    elif args.cmd == "set":
        set_active(args.name)
    elif args.cmd == "set-by-number":
        set_active_by_number(args.num)
    elif args.cmd == "use":
        use_by_number(args.num)
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
