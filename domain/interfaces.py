"""STT engine interface (Domain). No I/O — only contract."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class STTEngine(Protocol):
    """Abstract interface for STT engine. Implementations live in Infrastructure."""

    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to text. Returns text with punctuation."""
        ...
