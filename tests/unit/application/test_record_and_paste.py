"""Application: record -> transcribe -> paste use case."""

from unittest.mock import MagicMock, patch

from application.record_and_paste import (
    TranscribeParams,
    record_and_paste_use_case,
    run_transcription_pipeline,
)


@patch("application.record_and_paste.apply_text_postprocess", side_effect=lambda t: t)
@patch("application.record_and_paste.record_to_wav")
def test_record_and_paste_records_then_transcribes_then_pastes(mock_record, _mock_pp, tmp_path):
    """Use case: record to WAV, call engine.transcribe, then paste result."""
    mock_engine = MagicMock()
    mock_engine.transcribe.return_value = "Transcribed text."
    mock_paste = MagicMock()
    wav_path = tmp_path / "audio.wav"

    record_and_paste_use_case(
        engine=mock_engine,
        record_duration_sec=1.0,
        wav_path=str(wav_path),
        paste_fn=mock_paste,
    )

    mock_record.assert_called_once()
    mock_engine.transcribe.assert_called_once()
    call_arg = mock_engine.transcribe.call_args[0][0]
    assert call_arg == str(wav_path) or "audio" in call_arg
    mock_paste.assert_called_once_with("Transcribed text.")


@patch("application.record_and_paste.apply_text_postprocess", side_effect=lambda t: t)
@patch("application.record_and_paste.record_to_wav")
def test_record_and_paste_does_not_paste_empty_transcription(mock_record, _mock_pp, tmp_path):
    """Пустой результат — в буфер не вставляем (как в main.py)."""
    mock_engine = MagicMock()
    mock_engine.transcribe.return_value = ""
    mock_paste = MagicMock()
    wav_path = tmp_path / "a.wav"

    record_and_paste_use_case(
        engine=mock_engine,
        record_duration_sec=0.5,
        wav_path=str(wav_path),
        paste_fn=mock_paste,
    )

    mock_paste.assert_not_called()


@patch("application.record_and_paste.apply_text_postprocess", side_effect=lambda t: t)
def test_run_transcription_pipeline_pastes_only_non_empty(_mock_pp):
    mock_engine = MagicMock()
    mock_engine.transcribe.return_value = "  hello  "
    mock_paste = MagicMock()
    text = run_transcription_pipeline(
        engine=mock_engine,
        wav_path="x.wav",
        params=TranscribeParams(),
        paste_fn=mock_paste,
    )
    assert text == "  hello  "
    mock_paste.assert_called_once_with("  hello  ")


@patch("application.record_and_paste.apply_text_postprocess", side_effect=lambda t: t)
def test_run_transcription_pipeline_skips_paste_whitespace_only(_mock_pp):
    mock_engine = MagicMock()
    mock_engine.transcribe.return_value = "   \n"
    mock_paste = MagicMock()
    text = run_transcription_pipeline(
        engine=mock_engine,
        wav_path="x.wav",
        params=TranscribeParams(),
        paste_fn=mock_paste,
    )
    assert text == "   \n"
    mock_paste.assert_not_called()


def test_run_transcription_pipeline_passes_params_to_engine():
    mock_engine = MagicMock()
    mock_engine.transcribe.return_value = "ok"
    params = TranscribeParams(
        language="en",
        n_gpu_layers=7,
        beam_size=3,
        best_of=2,
        prompt="ctx",
        use_vad=False,
        vad_model_path="/vad.bin",
    )
    with patch("application.record_and_paste.apply_text_postprocess", side_effect=lambda t: t):
        run_transcription_pipeline(
            engine=mock_engine,
            wav_path="f.wav",
            params=params,
            paste_fn=lambda _t: None,
        )
    mock_engine.transcribe.assert_called_once_with(
        "f.wav",
        language="en",
        n_gpu_layers=7,
        beam_size=3,
        best_of=2,
        prompt="ctx",
        use_vad=False,
        vad_model_path="/vad.bin",
    )
