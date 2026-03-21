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

    def _make_argv(
        self,
        audio: Path,
        language: str,
        beam_size: int,
        best_of: int,
        *,
        n_gpu_layers: int,
        prompt: str,
        vad_file: Path | None,
        use_vad: bool,
    ) -> list[str]:
        args: list[str] = [
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
        if use_vad and vad_file is not None:
            args.extend(["--vad", "-vm", str(vad_file)])
        if prompt:
            args += ["--prompt", prompt]
        if n_gpu_layers > 0:
            args += ["-ngl", str(n_gpu_layers)]
        return args

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
        vad_file: Path | None = None
        if vad_model_path:
            p = Path(vad_model_path)
            if p.is_file():
                vad_file = p.resolve()

        def is_ngl_unsupported(stderr: str) -> bool:
            s = (stderr or "").lower()
            arg_rejected = "unknown" in s or "unrecognized" in s or "invalid option" in s
            mentions_ngl = "ngl" in s or "n-gpu-layers" in s
            return arg_rejected and mentions_ngl

        used_ngl = n_gpu_layers > 0
        last_ngl_used = n_gpu_layers if used_ngl else 0

        argv = self._make_argv(
            audio,
            language,
            beam_size,
            best_of,
            n_gpu_layers=last_ngl_used,
            prompt=prompt,
            vad_file=vad_file,
            use_vad=use_vad,
        )
        result = self._run_whisper(argv)

        if (
            used_ngl
            and (result.returncode != 0 or not (result.stdout or "").strip())
            and is_ngl_unsupported(result.stderr or "")
        ):
            logger.warning("whisper binary does not support -ngl, running without GPU layers")
            last_ngl_used = 0
            argv = self._make_argv(
                audio,
                language,
                beam_size,
                best_of,
                n_gpu_layers=0,
                prompt=prompt,
                vad_file=vad_file,
                use_vad=use_vad,
            )
            result = self._run_whisper(argv)

        # Большие -bs/-bo на CUDA сильно раздувают память под beam search; часто exit != 0 (напр. 10).
        if (
            result.returncode != 0
            and (beam_size > 5 or best_of > 5)
        ):
            err = (result.stderr or "").strip()
            logger.error(
                "whisper.cpp failed (exit=%s). stderr (first 4k): %s",
                result.returncode,
                err[:4000] if err else "(empty)",
            )
            if last_ngl_used > 0:
                logger.warning(
                    "Повтор распознавания с -bs 5 -bo 5 (при больших beam/best_of на GPU часто не хватает VRAM)"
                )
            else:
                logger.warning(
                    "Повтор распознавания с -bs 5 -bo 5 (меньше нагрузка на beam search)"
                )
            argv = self._make_argv(
                audio,
                language,
                5,
                5,
                n_gpu_layers=last_ngl_used,
                prompt=prompt,
                vad_file=vad_file,
                use_vad=use_vad,
            )
            result = self._run_whisper(argv)
            if result.returncode == 0:
                logger.info("Повтор с -bs 5 -bo 5 выполнен успешно")

        if result.returncode != 0:
            err = (result.stderr or "").strip()
            logger.error(
                "whisper.cpp failed (exit=%s). stderr (first 4k): %s",
                result.returncode,
                err[:4000] if err else "(empty)",
            )

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
