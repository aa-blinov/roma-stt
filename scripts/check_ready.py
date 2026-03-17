"""Check readiness: uv, .venv, exe, models, config, optional CUDA. For roma-stt.bat."""

import shutil
import sys
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parent.parent


def check_nvcc() -> tuple[bool, str]:
    """Whether nvcc (CUDA Toolkit) is in PATH — needed to build/use cuda."""
    nvcc = shutil.which("nvcc")
    if nvcc:
        return True, "nvcc (CUDA): in PATH"
    return False, "nvcc (CUDA): not in PATH (install CUDA Toolkit for cuda build)"


def check_uv() -> tuple[bool, str]:
    try:
        import subprocess

        r = subprocess.run(["uv", "--version"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return True, "uv: OK"
        return False, "uv: not found or error"
    except Exception as e:
        return False, f"uv: {e}"


def check_venv() -> tuple[bool, str]:
    venv = ROOT / ".venv"
    if not venv.is_dir():
        return False, ".venv: missing (run Install from bat)"
    py = venv / "Scripts" / "python.exe"
    if not py.exists():
        return False, ".venv: Scripts/python.exe missing"
    return True, ".venv: OK"


def check_whisper_runs(exe_path: str) -> tuple[bool, str]:
    """Verify whisper.cpp exe runs (e.g. -h)."""
    try:
        import subprocess

        resolved = Path(exe_path) if Path(exe_path).is_absolute() else ROOT / exe_path
        resolved = resolved.resolve()
        r = subprocess.run(
            [str(resolved), "-h"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(resolved.parent),
        )
        out = (r.stdout or "").lower() + (r.stderr or "").lower()
        if r.returncode == 0 or "usage" in out or "options" in out or "help" in out:
            return True, "whisper.cpp: runs OK"
        return False, f"whisper.cpp: exit code {r.returncode}"
    except Exception as e:
        return False, f"whisper.cpp: {e}"


def check_config(config_path: Path | None = None) -> tuple[bool, str]:
    config_path = config_path or ROOT / "config.yaml"
    if not config_path.exists():
        return False, "config.yaml: missing"
    import yaml

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    module = data.get("module", "cpu")
    key = f"whisper_cpp_path_{module}"
    exe = data.get(key) or data.get("whisper_cpp_path_cpu", "")
    model = data.get("whisper_model_path", "")
    if not exe:
        return False, f"config: set {key} to whisper.cpp executable"
    if not model:
        return False, "config: set whisper_model_path to ggml model (multilingual/turbo)"
    exe_path = Path(exe) if Path(exe).is_absolute() else ROOT / exe
    if not exe_path.exists():
        return False, f"config: exe not found: {exe}"
    model_path = Path(model) if Path(model).is_absolute() else ROOT / model
    if not model_path.exists():
        return False, f"config: model not found: {model}"
    ok, msg = check_whisper_runs(exe)
    if not ok:
        return False, msg
    return True, "config: OK"


def check_models_dir() -> tuple[bool, str]:
    models = ROOT / "models"
    if not models.is_dir():
        return False, "models/: missing"
    files = list(models.glob("*.ggml")) + list(models.glob("*.bin"))
    if not files:
        return False, "models/: empty (download a multilingual/turbo model)"
    return True, f"models/: {len(files)} file(s)"


def main() -> int:
    checks = [check_uv(), check_venv(), check_models_dir(), check_config()]
    all_ok = True
    for ok, msg in checks:
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {msg}")
        if not ok:
            all_ok = False
    # Всегда показывать модуль из конфига и статус CUDA (nvcc)
    try:
        import yaml
        config_path = ROOT / "config.yaml"
        module = "cpu"
        if config_path.exists():
            data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            module = data.get("module", "cpu")
        print(f"  [--] module: {module}")
        nvcc_ok, nvcc_msg = check_nvcc()
        status = "OK" if nvcc_ok else "WARN"
        print(f"  [{status}] {nvcc_msg}")
    except Exception:
        pass
    if all_ok:
        print("Ready. You can start the service from the bat menu.")
    else:
        print("Not ready. Use bat menu: 1=Install, 4=Models.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
