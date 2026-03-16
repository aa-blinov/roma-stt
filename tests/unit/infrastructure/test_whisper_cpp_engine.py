"""Infrastructure: whisper.cpp subprocess — mock subprocess, check CLI args."""

from unittest.mock import MagicMock, patch

from domain.interfaces import STTEngine
from infrastructure.whisper_cpp_engine import WhisperCppEngine


def test_whisper_cpp_engine_implements_stt_engine():
    engine = WhisperCppEngine(exe_path="dummy/main.exe", model_path="dummy/model.ggml")
    assert isinstance(engine, STTEngine)


@patch("infrastructure.whisper_cpp_engine.subprocess.run")
def test_transcribe_calls_exe_with_m_and_f(mock_run):
    mock_run.return_value = MagicMock(stdout="Hello world.\n", returncode=0)
    engine = WhisperCppEngine(exe_path="bin/whisper.exe", model_path="models/ggml-base.ggml")
    result = engine.transcribe("C:/temp/audio.wav")
    mock_run.assert_called_once()
    call_args = mock_run.call_args
    args = call_args[0][0]
    assert "whisper" in str(args[0]).lower() or args[0] == "bin/whisper.exe"
    assert "-m" in args
    assert "ggml-base.ggml" in str(args[args.index("-m") + 1])
    assert "-f" in args
    assert "audio.wav" in str(args[args.index("-f") + 1])
    assert result == "Hello world."


@patch("infrastructure.whisper_cpp_engine.subprocess.run")
def test_transcribe_returns_stdout_stripped(mock_run):
    mock_run.return_value = MagicMock(stdout="  Some text.\n\n  ", returncode=0)
    engine = WhisperCppEngine(exe_path="w.exe", model_path="m.ggml")
    result = engine.transcribe("a.wav")
    assert "Some text" in result
