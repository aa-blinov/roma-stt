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


@patch("infrastructure.whisper_cpp_engine.subprocess.run")
def test_transcribe_passes_language(mock_run):
    mock_run.return_value = MagicMock(stdout="текст", returncode=0)
    engine = WhisperCppEngine(exe_path="w.exe", model_path="m.ggml")
    engine.transcribe("a.wav", language="ru")
    args = mock_run.call_args[0][0]
    assert "-l" in args
    assert args[args.index("-l") + 1] == "ru"


@patch("infrastructure.whisper_cpp_engine.subprocess.run")
def test_transcribe_no_ngl_when_gpu_layers_zero(mock_run):
    mock_run.return_value = MagicMock(stdout="text", returncode=0)
    engine = WhisperCppEngine(exe_path="w.exe", model_path="m.ggml")
    engine.transcribe("a.wav", n_gpu_layers=0)
    args = mock_run.call_args[0][0]
    assert "-ngl" not in args


@patch("infrastructure.whisper_cpp_engine.subprocess.run")
def test_transcribe_passes_ngl_when_gpu_layers_nonzero(mock_run):
    mock_run.return_value = MagicMock(stdout="text", returncode=0)
    engine = WhisperCppEngine(exe_path="w.exe", model_path="m.ggml")
    engine.transcribe("a.wav", n_gpu_layers=99)
    args = mock_run.call_args[0][0]
    assert "-ngl" in args
    assert args[args.index("-ngl") + 1] == "99"


@patch("infrastructure.whisper_cpp_engine.subprocess.run")
def test_transcribe_retries_without_ngl_when_unsupported(mock_run):
    """If binary doesn't support -ngl, should retry without it and return text."""
    ngl_error = MagicMock(
        returncode=1,
        stdout="",
        stderr="error: unknown argument: -ngl",
    )
    ok_result = MagicMock(returncode=0, stdout="распознанный текст", stderr="")
    mock_run.side_effect = [ngl_error, ok_result]

    engine = WhisperCppEngine(exe_path="w.exe", model_path="m.ggml")
    result = engine.transcribe("a.wav", n_gpu_layers=99)

    assert mock_run.call_count == 2
    # Second call must not contain -ngl
    second_args = mock_run.call_args_list[1][0][0]
    assert "-ngl" not in second_args
    assert result == "распознанный текст"


@patch("infrastructure.whisper_cpp_engine.subprocess.run")
def test_transcribe_no_retry_on_non_ngl_error(mock_run):
    """Non-ngl errors should not trigger retry — check_returncode raises."""
    import subprocess as sp

    fail = MagicMock(returncode=1, stdout="", stderr="model file not found")
    fail.check_returncode.side_effect = sp.CalledProcessError(1, "w.exe")
    mock_run.return_value = fail

    engine = WhisperCppEngine(exe_path="w.exe", model_path="m.ggml")
    try:
        engine.transcribe("a.wav", n_gpu_layers=0)
        assert False, "should have raised"
    except sp.CalledProcessError:
        pass
    assert mock_run.call_count == 1
