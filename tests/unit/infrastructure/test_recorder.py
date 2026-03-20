"""Infrastructure: recorder — WAV (native rate in stop mode; fixed rate in timed helper)."""

import tempfile
from pathlib import Path
from threading import Event
from unittest.mock import patch

import numpy as np
import sounddevice as sd

from infrastructure.recorder import (
    BLOCKSIZE,
    RECORD_CHANNELS,
    RECORD_RATE,
    record_to_wav,
    record_to_wav_until_stopped,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stream_cls(chunks: int, stop: Event, error_with_device: bool = False):
    """Fake sd.InputStream that delivers `chunks` callbacks then sets stop.

    If error_with_device=True, raises PortAudioError when 'device' kwarg present
    (simulates invalid-device error), and succeeds on the fallback call.
    """

    class FakeStream:
        def __init__(self, **kwargs):
            self._cb = kwargs.get("callback")
            self._has_device = "device" in kwargs
            self._blocksize = int(kwargs.get("blocksize", BLOCKSIZE))
            self._fake_data = np.zeros((self._blocksize, RECORD_CHANNELS), dtype=np.float32)

        def __enter__(self):
            if error_with_device and self._has_device:
                raise sd.PortAudioError("Invalid device [-9996]")
            for _ in range(chunks):
                if self._cb:
                    self._cb(self._fake_data, self._blocksize, None, None)
            stop.set()
            return self

        def __exit__(self, *_):
            pass

    return FakeStream


# ---------------------------------------------------------------------------
# record_to_wav
# ---------------------------------------------------------------------------


def test_record_to_wav_accepts_duration_and_path():
    """Record for a short duration to a path; check file exists and format."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.wav"
        samples = int(0.1 * RECORD_RATE)
        fake_audio = np.zeros((samples, RECORD_CHANNELS), dtype=np.float32)
        with patch("infrastructure.recorder.sd.rec", return_value=fake_audio):
            with patch("infrastructure.recorder.sd.wait"):
                record_to_wav(path, duration_sec=0.1)
        assert path.exists()
        assert path.stat().st_size >= 44


def test_record_constants():
    assert RECORD_RATE == 16000
    assert RECORD_CHANNELS == 1


# ---------------------------------------------------------------------------
# record_to_wav_until_stopped
# ---------------------------------------------------------------------------


@patch("infrastructure.recorder._device_native_rate", return_value=16000)
def test_record_until_stopped_creates_wav(_mock_native):
    """Stop before any chunks — should still produce a valid (silent) WAV file."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "out.wav"
        stop = Event()

        with patch("infrastructure.recorder.sd.InputStream", _make_stream_cls(0, stop)):
            record_to_wav_until_stopped(path, stop)

        assert path.exists()
        assert path.stat().st_size >= 44  # at least WAV header


@patch("infrastructure.recorder._device_native_rate", return_value=16000)
def test_record_until_stopped_collects_chunks(_mock_native):
    """Three chunks → WAV must be larger than the minimal silent placeholder."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "out.wav"
        stop = Event()

        with patch("infrastructure.recorder.sd.InputStream", _make_stream_cls(3, stop)):
            record_to_wav_until_stopped(path, stop)

        assert path.exists()
        assert path.stat().st_size > 44  # real audio data present


@patch("infrastructure.recorder._device_native_rate", return_value=16000)
def test_record_until_stopped_device_fallback(_mock_native):
    """Invalid device (-9996) → retry without device, set fallback_used[0]=True."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "out.wav"
        stop = Event()
        fallback_used = [False]

        with patch(
            "infrastructure.recorder.sd.InputStream",
            _make_stream_cls(1, stop, error_with_device=True),
        ):
            record_to_wav_until_stopped(path, stop, device=5, fallback_used=fallback_used)

        assert fallback_used[0] is True
        assert path.exists()


@patch("infrastructure.recorder._device_native_rate", return_value=16000)
def test_record_until_stopped_no_fallback_without_device(_mock_native):
    """PortAudioError with device=None must propagate (no fallback possible)."""

    class ErrorStream:
        def __init__(self, **_):
            pass

        def __enter__(self):
            raise sd.PortAudioError("some error")

        def __exit__(self, *_):
            pass

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "out.wav"
        stop = Event()

        with patch("infrastructure.recorder.sd.InputStream", ErrorStream):
            try:
                record_to_wav_until_stopped(path, stop, device=None)
                assert False, "should have raised PortAudioError"
            except sd.PortAudioError:
                pass
