"""Run whisper.cpp on a minimal WAV to verify model and exe work. For roma-stt.bat test-model."""

import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def make_minimal_wav(path: Path, duration_sec: float = 0.5) -> None:
    """Write a minimal 16 kHz mono 16-bit WAV (silence)."""
    rate = 16000
    n_samples = int(rate * duration_sec)
    data = b"\x00\x00" * n_samples  # 16-bit silence
    # WAV header
    size = 36 + len(data)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        rate,
        rate * 2,
        2,
        16,
        b"data",
        len(data),
    )
    path.write_bytes(header + data)


def main() -> int:
    config_path = ROOT / "config.yaml"
    if not config_path.exists():
        print("  config.yaml missing. Run: roma-stt.bat install")
        return 0  # skip, not fail
    import yaml

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    module = data.get("module", "cpu")
    key = f"whisper_cpp_path_{module}"
    exe = (data.get(key) or data.get("whisper_cpp_path_cpu", "")).strip()
    model = (data.get("whisper_model_path", "")).strip()
    if not exe or not model:
        print("  test-model: skip (set whisper_cpp_path_cpu and whisper_model_path in config.yaml)")
        return 0
    exe_p = Path(exe).resolve()
    model_p = Path(model).resolve()
    if not exe_p.exists():
        print(f"  test-model: skip (exe not found: {exe_p})")
        return 0
    if not model_p.exists():
        print(f"  test-model: skip (model not found: {model_p})")
        return 0
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = Path(f.name)
    try:
        make_minimal_wav(wav_path)
        print("  Running whisper.cpp on a short test WAV...")
        r = subprocess.run(
            [str(exe_p), "-m", str(model_p), "-f", str(wav_path)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(exe_p.parent),
        )
        if r.returncode == 0:
            print("  Model works OK (whisper.cpp ran successfully).")
            return 0
        print(f"  Model test failed: exit code {r.returncode}")
        if r.stderr:
            print(r.stderr[:500])
        return 1
    finally:
        wav_path.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
