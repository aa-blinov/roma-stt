"""Download ggml model from Hugging Face (multilingual only). For roma-stt.bat."""

import argparse
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"

# Multilingual models only (no .en). Hugging Face ggerganov/whisper.cpp
HF_BASE = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"
MODELS = {
    "tiny": f"{HF_BASE}/ggml-tiny.bin",
    "base": f"{HF_BASE}/ggml-base.bin",
    "small": f"{HF_BASE}/ggml-small.bin",
    "medium": f"{HF_BASE}/ggml-medium.bin",
    "large-v3": f"{HF_BASE}/ggml-large-v3.bin",
    "large-v3-turbo": f"{HF_BASE}/ggml-large-v3-turbo.bin",
    "base-q5_1": f"{HF_BASE}/ggml-base-q5_1.bin",
    "small-q5_1": f"{HF_BASE}/ggml-small-q5_1.bin",
}
# Порядок для выбора по номеру (должен совпадать с models.py list-available)
ORDERED_MODELS = list(MODELS.keys())


def download(name: str, dest_dir: Path | None = None) -> bool:
    """Download model by name. Returns True on success."""
    if name not in MODELS:
        print(f"Unknown model: {name}. Choose from: {', '.join(MODELS)}")
        return False
    dest_dir = dest_dir or MODELS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    url = MODELS[name]
    filename = url.split("/")[-1]
    path = dest_dir / filename
    if path.exists():
        print(f"Already exists: {path}")
        return True
    print(f"Downloading {name} from Hugging Face...")
    req = urllib.request.Request(url, headers={"User-Agent": "roma-stt/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("content-length", 0))
            chunk_size = 1024 * 1024
            downloaded = 0
            with open(path, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = 100 * downloaded / total
                        print(
                            f"\r  {downloaded // (1024 * 1024)} MiB / {total // (1024 * 1024)} MiB ({pct:.0f}%)", end=""
                        )
        print(f"\nSaved: {path}")
        return True
    except Exception as e:
        print(f"\nDownload failed: {e}")
        if path.exists():
            path.unlink()
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download multilingual ggml model. Name or number 1-%d (see list-available)." % len(ORDERED_MODELS)
    )
    parser.add_argument("name", help="Model name or number (1-%d)" % len(ORDERED_MODELS))
    parser.add_argument("--dir", type=Path, default=MODELS_DIR, help="Destination directory")
    args = parser.parse_args()
    name = args.name.strip()
    if name.isdigit():
        idx = int(name)
        if idx < 1 or idx > len(ORDERED_MODELS):
            print(f"Номер должен быть от 1 до {len(ORDERED_MODELS)}. Доступные: a/d в меню моделей.")
            return 1
        name = ORDERED_MODELS[idx - 1]
    if name not in MODELS:
        print(f"Неизвестная модель: {name}. Доступные: {', '.join(ORDERED_MODELS)} или номер 1-{len(ORDERED_MODELS)}.")
        return 1
    return 0 if download(name, args.dir) else 1


if __name__ == "__main__":
    sys.exit(main())
