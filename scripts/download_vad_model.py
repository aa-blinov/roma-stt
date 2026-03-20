"""Download Silero VAD model in ggml format for whisper.cpp --vad / -vm. For roma-stt.bat download-vad."""

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"

# ggml-org/whisper-vad (see whisper.cpp README)
VAD_URL = "https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v6.2.0.bin"
DEFAULT_NAME = "ggml-silero-v6.2.0.bin"


def download_vad_model(models_dir: Path | None = None) -> bool:
    """Download Silero VAD ggml into models/. Idempotent. Used by install.py and CLI."""
    dest = models_dir or MODELS_DIR
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / DEFAULT_NAME
    if path.exists():
        print(f"VAD model already present: {path}")
        return True
    print(f"Downloading VAD model from Hugging Face...\n  {VAD_URL}")
    req = urllib.request.Request(VAD_URL, headers={"User-Agent": "roma-stt/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
        path.write_bytes(data)
        print(f"Saved: {path}")
        return True
    except Exception as e:
        print(f"VAD model download failed: {e}")
        if path.exists():
            path.unlink(missing_ok=True)
        return False


def main() -> int:
    return 0 if download_vad_model() else 1


if __name__ == "__main__":
    sys.exit(main())
