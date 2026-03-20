"""List available/downloaded models, set active model. For roma-stt.bat."""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"
CONFIG_PATH = ROOT / "config.yaml"

# Манифест и порядок номеров — единый источник whisper_models.py
from whisper_models import MODEL_DESCRIPTIONS, ORDERED_MODEL_KEYS

MODELS_MANIFEST = {k: MODEL_DESCRIPTIONS[k] for k in ORDERED_MODEL_KEYS}
ORDERED_NAMES = list(ORDERED_MODEL_KEYS)

# ANSI (Windows 10+ cmd/PowerShell поддерживают)
_GREEN = "\033[32m"  # скачана
_GRAY = "\033[90m"   # нет
_RESET = "\033[0m"


def _is_model_downloaded(name: str) -> bool:
    if not MODELS_DIR.is_dir():
        return False
    for stem in (f"ggml-{name}", name):
        if (MODELS_DIR / f"{stem}.bin").exists() or (MODELS_DIR / f"{stem}.ggml").exists():
            return True
    return False


def list_all() -> None:
    """Один список: все модели из манифеста со статусом скачана/нет (цветом)."""
    use_color = sys.stdout.isatty()
    print("Модели (введите номер: если скачана — выберется, если нет — скачается и выберется):")
    for i, name in enumerate(ORDERED_NAMES, 1):
        desc = MODELS_MANIFEST[name]
        downloaded = _is_model_downloaded(name)
        status = "Скачено" if downloaded else "Не скачено"
        if use_color:
            color = _GREEN if downloaded else _GRAY
            print(f"  {i}. {name} — {desc} — {color}{status}{_RESET}")
        else:
            print(f"  {i}. {name} — {desc} — {status}")


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
    CONFIG_PATH.write_text(yaml.dump(config, allow_unicode=True, default_flow_style=False), encoding="utf-8")


def _path_for_model_name(name: str) -> Path | None:
    """Путь к файлу модели по имени из манифеста (если скачана)."""
    if not MODELS_DIR.is_dir():
        return None
    for stem, ext in [(f"ggml-{name}", ".bin"), (f"ggml-{name}", ".ggml"), (name, ".bin"), (name, ".ggml")]:
        p = MODELS_DIR / f"{stem}{ext}"
        if p.exists():
            return p
    return None


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
        print(f"Модель «{name}» не скачана. Сначала скачайте: пункт 5, номер {num}.")
        sys.exit(1)
    _write_config_path(path)
    print(f"Активная модель: {path.name}")


def use_by_number(num_or_name: str) -> None:
    """По номеру или названию: если модель скачана — выбрать активной; если нет — скачать и выбрать."""
    s = num_or_name.strip()
    if s in ORDERED_NAMES:
        num = ORDERED_NAMES.index(s) + 1
    else:
        try:
            num = int(s)
        except ValueError:
            print("Введите номер (1–8) или название модели (например base, large-v3-turbo).")
            sys.exit(1)
        if num < 1 or num > len(ORDERED_NAMES):
            print(f"Номер должен быть от 1 до {len(ORDERED_NAMES)}.")
            sys.exit(1)
    name = ORDERED_NAMES[num - 1]
    if not _is_model_downloaded(name):
        print(f"Скачивание «{name}»...")
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "download_model.py"), name],
            cwd=str(ROOT),
        )
        if r.returncode != 0:
            sys.exit(1)
    set_active_by_number(str(num))


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
