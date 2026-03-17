"""Install: uv venv, uv sync, optionally download model and check whisper build. For roma-stt.bat."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"


def run(cmd: list[str], cwd: Path | None = None) -> bool:
    cwd = cwd or ROOT
    cwd = Path(cwd).resolve()
    r = subprocess.run(cmd, cwd=str(cwd), shell=False)
    return r.returncode == 0


def download_default_model() -> bool:
    """Download recommended multilingual model (large-v3-turbo) if models/ is empty."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if list(MODELS_DIR.glob("*.bin")) or list(MODELS_DIR.glob("*.ggml")):
        return True
    print("Downloading default model (large-v3-turbo, multilingual)...")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "download_model.py"), "large-v3-turbo"], cwd=ROOT)
    if r.returncode != 0:
        return False
    # Set in config if missing
    config_path = ROOT / "config.yaml"
    if config_path.exists():
        import yaml

        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not data.get("whisper_model_path"):
            model_path = MODELS_DIR / "ggml-large-v3-turbo.bin"
            if model_path.exists():
                data["whisper_model_path"] = str(model_path.resolve())
                config_path.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False), encoding="utf-8")
                print("Set whisper_model_path in config.yaml to ggml-large-v3-turbo.bin")
    return True


def build_whisper_cpp(arch: str = "cpu") -> bool:
    """Clone/pull, build whisper.cpp, copy to bin/. Returns True on success."""
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_whisper_cpp.py"), "--arch", arch], cwd=ROOT)
    return r.returncode == 0


def check_build() -> None:
    """Run check_build.py to verify whisper.cpp exe if path is set."""
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_build.py")], cwd=ROOT)
    if r.returncode != 0:
        print("Tip: install Git and CMake and Visual Studio Build Tools, then run Install again to build whisper.cpp.")


def main() -> int:
    os.chdir(ROOT)
    parser = argparse.ArgumentParser()
    parser.add_argument("--arch", choices=["cpu", "cuda", "amd"], default="cpu", help="Target architecture")
    parser.add_argument("--no-download", action="store_true", help="Skip downloading default model")
    parser.add_argument("--no-whisper-build", action="store_true", help="Skip automatic whisper.cpp clone and build")
    parser.add_argument("--no-build-check", action="store_true", help="Skip whisper.cpp build check")
    args = parser.parse_args()
    if not run(["uv", "python", "install", "3.12"]):
        print("Failed to ensure Python 3.12 via uv.")
        return 1
    venv_dir = ROOT / ".venv"
    venv_py = venv_dir / "Scripts" / "python.exe"
    if not venv_py.exists():
        if not run(["uv", "venv"]):
            print("Failed to create .venv")
            return 1
    else:
        print("Using existing .venv (uv sync only).")
    if not run(["uv", "sync"]):
        print("Failed to uv sync")
        return 1
    build_ok = True
    if not args.no_whisper_build:
        build_ok = build_whisper_cpp(args.arch)
        if not build_ok:
            print("whisper.cpp build failed. You can retry later: roma-stt.bat build-whisper")
    if not args.no_download:
        if build_ok:
            if not download_default_model():
                print("Загрузка модели не удалась. Позже: пункт 5 -> модели.")
        else:
            print("Сборка не удалась — модель не качаем. После успешной сборки: пункт 5 -> модели.")
    if not args.no_build_check:
        check_build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
