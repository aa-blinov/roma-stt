"""Whisper.cpp subprocess engine. Infrastructure layer."""

import subprocess
from pathlib import Path


class WhisperCppEngine:
    """STT engine that runs whisper.cpp binary. Implements domain STTEngine."""

    def __init__(self, exe_path: str, model_path: str):
        self.exe_path = Path(exe_path)
        self.model_path = Path(model_path)

    def transcribe(self, audio_path: str, language: str = "ru", n_gpu_layers: int = 0) -> str:
        """Run whisper.cpp: -m model -f audio.wav -nt -l lang [-ngl N], return stdout as text."""
        audio = Path(audio_path).resolve()
        args = [
            str(self.exe_path.resolve()),
            "-m",
            str(self.model_path.resolve()),
            "-f",
            str(audio),
            "-nt",  # no timestamps
            "-l",
            language,
        ]
        if n_gpu_layers > 0:
            args.extend(["-ngl", str(n_gpu_layers)])

        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
            cwd=str(self.exe_path.parent),
        )
        result.check_returncode()
        return (result.stdout or "").strip()
