"""Whisper.cpp subprocess engine. Infrastructure layer."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class WhisperCppEngine:
    """STT engine that runs whisper.cpp binary. Implements domain STTEngine."""

    def __init__(self, exe_path: str, model_path: str):
        self.exe_path = Path(exe_path)
        self.model_path = Path(model_path)

    def _run_whisper(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
            cwd=str(self.exe_path.parent),
        )

    def transcribe(self, audio_path: str, language: str = "ru", n_gpu_layers: int = 0) -> str:
        """Run whisper.cpp: -m model -f audio.wav -nt -l lang [-ngl N], return stdout as text.
        If the binary does not support -ngl (e.g. CPU-only build), retries without -ngl."""
        audio = Path(audio_path).resolve()
        base_args = [
            str(self.exe_path.resolve()),
            "-m",
            str(self.model_path.resolve()),
            "-f",
            str(audio),
            "-nt",
            "-l",
            language,
        ]
        args_with_gpu = base_args + ["-ngl", str(n_gpu_layers)] if n_gpu_layers > 0 else base_args

        def is_ngl_unsupported(stderr: str) -> bool:
            s = (stderr or "").lower()
            return ("-ngl" in s or "ngl" in s) and "unknown" in s

        result = self._run_whisper(args_with_gpu)
        used_ngl = n_gpu_layers > 0

        if used_ngl and (result.returncode != 0 or not (result.stdout or "").strip()) and is_ngl_unsupported(result.stderr or ""):
            logger.warning("whisper binary does not support -ngl, running without GPU layers")
            result = self._run_whisper(base_args)

        result.check_returncode()
        text = (result.stdout or "").strip()

        if not text and (result.stderr or "").strip() and not is_ngl_unsupported(result.stderr or ""):
            logger.warning(
                "whisper empty stdout (check CUDA/audio) | stderr=%s",
                (result.stderr or "").strip()[:500],
            )
        return text
