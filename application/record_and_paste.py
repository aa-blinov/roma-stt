"""Use case: record audio -> transcribe -> paste result. Application layer."""

from typing import Callable

from domain.interfaces import STTEngine
from infrastructure.recorder import record_to_wav


def record_and_paste_use_case(
    *,
    engine: STTEngine,
    record_duration_sec: float,
    wav_path: str,
    paste_fn: Callable[[str], None],
) -> None:
    """Record from mic to WAV, transcribe with engine, pass text to paste_fn."""
    record_to_wav(wav_path, duration_sec=record_duration_sec)
    text = engine.transcribe(wav_path)
    paste_fn(text)
