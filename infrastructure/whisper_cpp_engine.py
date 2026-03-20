"""Whisper.cpp subprocess engine. Infrastructure layer."""

import logging
import subprocess
from pathlib import Path
from typing import Any

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
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

    def transcribe(
        self,
        audio_path: str,
        language: str = "ru",
        n_gpu_layers: int = 0,
        beam_size: int = 5,
        best_of: int = 5,
        prompt: str = "",
        use_vad: bool = True,
        vad_model_path: str | None = None,
        **_kw: Any,
    ) -> str:
        """Run whisper.cpp: -m model -f audio.wav -nt -l lang [options], return stdout as text.
        If the binary does not support -ngl (e.g. CPU-only build), retries without -ngl.
        whisper.cpp requires -vm/--vad-model when using --vad; without a real file, VAD is skipped."""
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
            "-bs",
            str(beam_size),
            "-bo",
            str(best_of),
        ]
        vad_file: Path | None = None
        if vad_model_path:
            p = Path(vad_model_path)
            if p.is_file():
                vad_file = p.resolve()
        if use_vad and vad_file is not None:
            base_args.extend(["--vad", "-vm", str(vad_file)])
        if prompt:
            base_args += ["--prompt", prompt]
        args_with_gpu = base_args + ["-ngl", str(n_gpu_layers)] if n_gpu_layers > 0 else base_args

        def is_ngl_unsupported(stderr: str) -> bool:
            # Only flag when the binary explicitly rejects -ngl / --n-gpu-layers
            # as an unknown/unrecognized argument.  Do NOT match broad "gpu"
            # so that CUDA init messages (e.g. "invalid CUDA device") don't
            # cause a false positive and silently disable GPU acceleration.
            s = (stderr or "").lower()
            arg_rejected = "unknown" in s or "unrecognized" in s or "invalid option" in s
            mentions_ngl = "ngl" in s or "n-gpu-layers" in s
            return arg_rejected and mentions_ngl

        result = self._run_whisper(args_with_gpu)
        used_ngl = n_gpu_layers > 0

        if (
            used_ngl
            and (result.returncode != 0 or not (result.stdout or "").strip())
            and is_ngl_unsupported(result.stderr or "")
        ):
            logger.warning("whisper binary does not support -ngl, running without GPU layers")
            result = self._run_whisper(base_args)

        result.check_returncode()
        text = (result.stdout or "").strip()

        if (
            not text
            and (result.stderr or "").strip()
            and not is_ngl_unsupported(result.stderr or "")
        ):
            logger.warning(
                "whisper empty stdout (check CUDA/audio) | stderr=%s",
                (result.stderr or "").strip()[:500],
            )
        return text
