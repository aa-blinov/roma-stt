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
# Smaller blocksize = more frequent callbacks = less chance of buffer overflow.
# 2048 samples @ 48 kHz ≈ 43 ms per callback — a good balance.
BLOCKSIZE = 2048
# PortAudio: Invalid device (unplugged or index changed)
PA_INVALID_DEVICE = -9996


def _device_native_rate(device: int | None) -> int:
    """Return the device's default (native) sample rate, or RECORD_RATE as fallback."""
    try:
        info = sd.query_devices(device, "input")
        native = int(info["default_samplerate"])
        return native if native > 0 else RECORD_RATE
    except Exception:
        return RECORD_RATE


def _resample(data: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
    """Resample mono float32 array from orig_rate to target_rate via linear interpolation.

    Linear interpolation is dependency-free and good enough for speech at 16 kHz.
    """
    if orig_rate == target_rate:
        return data
    flat = data.flatten()
    target_len = int(round(len(flat) * target_rate / orig_rate))
    x_orig = np.linspace(0.0, 1.0, len(flat))
    x_new = np.linspace(0.0, 1.0, target_len)
    return np.interp(x_new, x_orig, flat).astype(np.float32)


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

    Records at the device's native sample rate to avoid Windows internal resampling
    (which can cause glitches). Resamples to 16 kHz with numpy before saving.

    If device is invalid (e.g. unplugged), falls back to default and sets fallback_used[0]=True.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    chunks: list[np.ndarray] = []

    def _callback(indata: np.ndarray, frames: int, time_info, status) -> None:  # noqa: ARG001
        if status:
            logger.warning("sounddevice status: %s", status)
        chunks.append(indata.copy())

    def _build_stream_kw(dev: int | None) -> dict:
        native_rate = _device_native_rate(dev)
        kw: dict = dict(
            samplerate=native_rate,
            channels=channels,
            dtype=DTYPE,
            callback=_callback,
            blocksize=BLOCKSIZE,
        )
        if dev is not None:
            kw["device"] = dev
        return kw

    def _run(kw: dict) -> None:
        with sd.InputStream(**kw):
            stop_event.wait()

    stream_kw = _build_stream_kw(device)
    native_rate = stream_kw["samplerate"]
    logger.debug("recording at native rate=%d Hz (target=%d Hz)", native_rate, samplerate)

    try:
        _run(stream_kw)
    except sd.PortAudioError as e:
        err_str = str(e)
        if (str(PA_INVALID_DEVICE) in err_str or "-9996" in err_str) and device is not None:
            logger.warning("invalid input device %s, using default", device)
            if fallback_used is not None:
                fallback_used[0] = True
            stream_kw = _build_stream_kw(None)
            native_rate = stream_kw["samplerate"]
            _run(stream_kw)
        else:
            raise

    if not chunks:
        data_float = np.zeros(BLOCKSIZE, dtype=np.float32)
    else:
        data_float = np.vstack(chunks).flatten()

    # Resample from native device rate to target 16 kHz
    if native_rate != samplerate:
        data_float = _resample(data_float, native_rate, samplerate)

    data_int = (np.clip(data_float, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(samplerate)
        wav.writeframes(data_int.tobytes())
