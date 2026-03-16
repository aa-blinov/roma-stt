"""List available/downloaded models, set active model. For roma-stt.bat."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"
CONFIG_PATH = ROOT / "config.yaml"

# Manifest of available multilingual/turbo models (name -> description).
# Order = numbers in list-available and download by number.
MODELS_MANIFEST = {
    "tiny": "мультиязычная, ~75 MiB",
    "base": "мультиязычная, ~142 MiB, рекомендуется для начала",
    "small": "мультиязычная",
    "medium": "мультиязычная",
    "large-v3": "мультиязычная",
    "large-v3-turbo": "мультиязычная, turbo",
    "base-q5_1": "мультиязычная, квантизация",
    "small-q5_1": "мультиязычная, квантизация",
}


def list_available() -> None:
    print("Доступные модели (мультиязычные/turbo). Для скачивания введите номер или название:")
    for i, (name, desc) in enumerate(MODELS_MANIFEST.items(), 1):
        print(f"  {i}. {name} — {desc}")


def list_downloaded() -> None:
    if not MODELS_DIR.is_dir():
        print("models/ folder missing.")
        return
    files = sorted(MODELS_DIR.glob("*.ggml")) + sorted(MODELS_DIR.glob("*.bin"))
    if not files:
        print("No models in models/ yet. Download via Install or Models menu.")
        return
    print("Downloaded:")
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f.name}")


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
    import yaml

    config = {}
    if CONFIG_PATH.exists():
        config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    config["whisper_model_path"] = str(path.resolve())
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(yaml.dump(config, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    print(f"Active model set to: {path.name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("list-available")
    sub.add_parser("list-downloaded")
    p_set = sub.add_parser("set")
    p_set.add_argument("name", help="Model file name or base name")
    args = parser.parse_args()
    if args.cmd == "list-available":
        list_available()
    elif args.cmd == "list-downloaded":
        list_downloaded()
    elif args.cmd == "set":
        set_active(args.name)
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
