"""Record from microphone to WAV (16 kHz mono). Infrastructure layer."""

import threading
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

RECORD_RATE = 16000
RECORD_CHANNELS = 1
DTYPE = np.float32
CHUNK_SEC = 0.5


def record_to_wav(
    path: str | Path, duration_sec: float, samplerate: int = RECORD_RATE, channels: int = RECORD_CHANNELS
) -> None:
    """Record from default input device to a WAV file (16 kHz mono by default)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = int(duration_sec * samplerate)
    data = sd.rec(samples, samplerate=samplerate, channels=channels, dtype=DTYPE)
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
) -> None:
    """Record in chunks until stop_event is set, then save to WAV."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    chunk_samples = int(CHUNK_SEC * samplerate)
    chunks: list[np.ndarray] = []
    while not stop_event.is_set():
        data = sd.rec(chunk_samples, samplerate=samplerate, channels=channels, dtype=DTYPE)
        sd.wait()
        if stop_event.is_set():
            break
        chunks.append(data.copy())
    if not chunks:
        # Minimal silent WAV
        data_int = np.zeros((chunk_samples, channels), dtype=np.int16)
    else:
        data_int = (np.clip(np.vstack(chunks), -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(samplerate)
        wav.writeframes(data_int.tobytes())
