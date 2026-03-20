"""Check that whisper.cpp executable runs (e.g. -h). For roma-stt.bat."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def check_whisper_exe(exe_path: str | Path) -> tuple[bool, str]:
    """Run whisper exe with -h; return (True, msg) if it runs."""
    exe = Path(exe_path).resolve()
    if not exe.exists():
        return False, f"Not found: {exe}"
    try:
        r = subprocess.run(
            [str(exe), "-h"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(exe.parent),
        )
        if (
            r.returncode == 0
            or "usage" in (r.stdout or "").lower()
            or "usage" in (r.stderr or "").lower()
        ):
            return True, f"whisper.cpp: OK ({exe.name})"
        return False, f"whisper.cpp: unexpected exit {r.returncode}"
    except FileNotFoundError:
        return False, f"Could not run: {exe}"
    except subprocess.TimeoutExpired:
        return False, "whisper.cpp: timeout"
    except Exception as e:
        return False, f"whisper.cpp: {e}"


def main() -> int:
    config_path = ROOT / "config.yaml"
    if not config_path.exists():
        print("  config.yaml missing. Run Install first.")
        return 1
    import yaml

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    module = data.get("module", "cpu")
    key = f"whisper_cpp_path_{module}"
    exe = data.get(key) or data.get("whisper_cpp_path_cpu", "")
    if not exe:
        print(
            "  Set whisper_cpp_path_cpu (or cuda/amd) in config.yaml to your whisper main.exe path."
        )
        print("  Build from: https://github.com/ggml-org/whisper.cpp")
        return 1
    ok, msg = check_whisper_exe(exe)
    print(f"  [{msg}]")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
