"""Record from microphone to WAV (16 kHz mono). Infrastructure layer."""

import logging
import threading
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)

RECORD_RATE = 16000
RECORD_CHANNELS = 1
DTYPE = np.float32
CHUNK_SEC = 0.5
# PortAudio: Invalid device (unplugged or index changed)
PA_INVALID_DEVICE = -9996


def record_to_wav(
    path: str | Path,
    duration_sec: float,
    samplerate: int = RECORD_RATE,
    channels: int = RECORD_CHANNELS,
    device: int | None = None,
) -> None:
    """Record from input device to a WAV file (16 kHz mono by default). device = None для системного по умолчанию."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = int(duration_sec * samplerate)
    rec_kw: dict = dict(samplerate=samplerate, channels=channels, dtype=DTYPE)
    if device is not None:
        rec_kw["device"] = device
    data = sd.rec(samples, **rec_kw)
    sd.wait()
    # Convert float32 [-1,1] to int16 for WAV
    data_int = (np.clip(data, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)  # 16 bit
        wav.setframerate(samplerate)
        wav.writeframes(data_int.tobytes())


def record_to_wav_until_stopped(
    path: str | Path,
    stop_event: threading.Event,
    samplerate: int = RECORD_RATE,
    channels: int = RECORD_CHANNELS,
    device: int | None = None,
    fallback_used: list | None = None,
) -> None:
    """Record continuously (callback-based) until stop_event is set, then save to WAV.

    Uses sd.InputStream with a callback so PortAudio fills buffers without gaps.
    If device is invalid (e.g. unplugged), falls back to default and sets fallback_used[0]=True.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    chunks: list[np.ndarray] = []

    def _callback(indata: np.ndarray, frames: int, time_info, status) -> None:  # noqa: ARG001
        if status:
            logger.warning("sounddevice status: %s", status)
        chunks.append(indata.copy())

    stream_kw: dict = dict(
        samplerate=samplerate,
        channels=channels,
        dtype=DTYPE,
        callback=_callback,
        blocksize=int(CHUNK_SEC * samplerate),
    )
    if device is not None:
        stream_kw["device"] = device

    def _run(kw: dict) -> None:
        with sd.InputStream(**kw):
            stop_event.wait()

    try:
        _run(stream_kw)
    except sd.PortAudioError as e:
        err_str = str(e)
        if (str(PA_INVALID_DEVICE) in err_str or "-9996" in err_str) and device is not None:
            logger.warning("invalid input device %s, using default", device)
            stream_kw.pop("device", None)
            if fallback_used is not None:
                fallback_used[0] = True
            _run(stream_kw)
        else:
            raise

    if not chunks:
        data_int = np.zeros((int(CHUNK_SEC * samplerate), channels), dtype=np.int16)
    else:
        data_int = (np.clip(np.vstack(chunks), -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(samplerate)
        wav.writeframes(data_int.tobytes())
