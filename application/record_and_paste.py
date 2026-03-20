"""Use cases: запись/файл → транскрипция → постобработка → вставка. Application layer."""

from collections.abc import Callable
from dataclasses import dataclass

from domain.interfaces import STTEngine
from infrastructure.recorder import record_to_wav
from infrastructure.text_postprocess import postprocess as apply_text_postprocess


@dataclass(frozen=True)
class TranscribeParams:
    """Параметры вызова whisper.cpp (совпадают с WhisperCppEngine.transcribe)."""

    language: str = "ru"
    n_gpu_layers: int = 0
    beam_size: int = 5
    best_of: int = 5
    prompt: str = ""
    use_vad: bool = True
    vad_model_path: str | None = None


def run_transcription_pipeline(
    *,
    engine: STTEngine,
    wav_path: str,
    params: TranscribeParams,
    paste_fn: Callable[[str], None],
    postprocess_fn: Callable[[str], str] | None = None,
) -> str:
    """Транскрибировать WAV, постобработать; при непустом тексте вызвать paste_fn.

    Возвращает итоговую строку после постобработки (может быть пустой).
    """
    pp = apply_text_postprocess if postprocess_fn is None else postprocess_fn
    text = engine.transcribe(
        wav_path,
        language=params.language,
        n_gpu_layers=params.n_gpu_layers,
        beam_size=params.beam_size,
        best_of=params.best_of,
        prompt=params.prompt,
        use_vad=params.use_vad,
        vad_model_path=params.vad_model_path,
    )
    text = pp(text)
    if text and text.strip():
        paste_fn(text)
    return text


def record_and_paste_use_case(
    *,
    engine: STTEngine,
    record_duration_sec: float,
    wav_path: str,
    paste_fn: Callable[[str], None],
    params: TranscribeParams | None = None,
    postprocess_fn: Callable[[str], str] | None = None,
) -> None:
    """Записать с микрофона фиксированной длительности, затем run_transcription_pipeline."""
    record_to_wav(wav_path, duration_sec=record_duration_sec)
    run_transcription_pipeline(
        engine=engine,
        wav_path=wav_path,
        params=params or TranscribeParams(),
        paste_fn=paste_fn,
        postprocess_fn=postprocess_fn,
    )
