"""STT engine interface (Domain). No I/O — only contract."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class STTEngine(Protocol):
    """Abstract interface for STT engine. Implementations live in Infrastructure."""

    def transcribe(self, audio_path: str, **kwargs: Any) -> str:
        """Transcribe audio file to text. Implementations accept whisper.cpp options as kwargs."""
        ...
