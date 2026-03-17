"""Infrastructure: recorder — WAV 16 kHz mono."""

import tempfile
from pathlib import Path
from threading import Event
from unittest.mock import patch

import numpy as np
import sounddevice as sd

from infrastructure.recorder import (
    RECORD_CHANNELS,
    RECORD_RATE,
    record_to_wav,
    record_to_wav_until_stopped,
)


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


# --- record_to_wav_until_stopped ---


def _fake_chunk():
    return np.zeros((int(0.5 * RECORD_RATE), RECORD_CHANNELS), dtype=np.float32)


def test_record_until_stopped_creates_wav():
    """Stop immediately — should still produce a valid WAV file."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "out.wav"
        stop = Event()
        stop.set()  # already stopped

        with patch("infrastructure.recorder._rec_chunk", return_value=_fake_chunk()):
            with patch("infrastructure.recorder.sd.wait"):
                record_to_wav_until_stopped(path, stop)

        assert path.exists()
        assert path.stat().st_size >= 44


def test_record_until_stopped_collects_chunks():
    """Two chunks before stop — both end up in the WAV (larger than minimal)."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "out.wav"
        stop = Event()
        call_count = [0]

        def fake_chunk(n, kw):
            call_count[0] += 1
            if call_count[0] >= 3:
                stop.set()
            return _fake_chunk()

        with patch("infrastructure.recorder._rec_chunk", side_effect=fake_chunk):
            with patch("infrastructure.recorder.sd.wait"):
                record_to_wav_until_stopped(path, stop)

        assert path.exists()
        assert path.stat().st_size > 44  # audio data present


def test_record_until_stopped_device_fallback():
    """Invalid device (-9996) → retry with default device, set fallback_used[0]=True."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "out.wav"
        stop = Event()
        stop.set()
        fallback_used = [False]

        def fake_chunk(n, kw):
            if "device" in kw:
                raise sd.PortAudioError("Invalid device [-9996]")
            return _fake_chunk()

        with patch("infrastructure.recorder._rec_chunk", side_effect=fake_chunk):
            with patch("infrastructure.recorder.sd.wait"):
                record_to_wav_until_stopped(path, stop, device=5, fallback_used=fallback_used)

        assert fallback_used[0] is True
        assert path.exists()


def test_record_until_stopped_no_fallback_without_device():
    """PortAudioError with device=None must propagate (no fallback possible)."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "out.wav"
        stop = Event()

        with patch("infrastructure.recorder._rec_chunk", side_effect=sd.PortAudioError("some error")):
            with patch("infrastructure.recorder.sd.wait"):
                try:
                    record_to_wav_until_stopped(path, stop, device=None)
                    assert False, "should have raised PortAudioError"
                except sd.PortAudioError:
                    pass
