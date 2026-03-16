"""Application: record -> transcribe -> paste use case."""

from unittest.mock import MagicMock, patch

from application.record_and_paste import record_and_paste_use_case


@patch("application.record_and_paste.record_to_wav")
def test_record_and_paste_records_then_transcribes_then_pastes(mock_record, tmp_path):
    """Use case: record to WAV, call engine.transcribe, then paste result."""
    mock_engine = MagicMock()
    mock_engine.transcribe.return_value = "Transcribed text."
    mock_paste = MagicMock()
    wav_path = tmp_path / "audio.wav"
    mock_record.return_value = str(wav_path)

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


@patch("application.record_and_paste.record_to_wav")
def test_record_and_paste_passes_through_empty_transcription(mock_record, tmp_path):
    mock_engine = MagicMock()
    mock_engine.transcribe.return_value = ""
    mock_paste = MagicMock()
    wav_path = tmp_path / "a.wav"
    mock_record.return_value = str(wav_path)

    record_and_paste_use_case(
        engine=mock_engine,
        record_duration_sec=0.5,
        wav_path=str(wav_path),
        paste_fn=mock_paste,
    )

    mock_paste.assert_called_once_with("")
