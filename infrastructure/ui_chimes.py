"""Короткие сигналы начала/конца записи: синус + плавная огибающая (мягче, чем winsound.Beep).

Воспроизведение через winsound.PlaySound(SND_MEMORY) — без файлов на диске.
"""

from __future__ import annotations

import array
import io
import math
import wave
import winsound

_SAMPLE_RATE = 44100


def _note_samples(
    frequency_hz: float,
    duration_sec: float,
    *,
    volume: float = 0.26,
) -> array.array[int]:
    n = max(1, int(_SAMPLE_RATE * duration_sec))
    attack = max(1, int(_SAMPLE_RATE * 0.018))
    release = max(1, int(_SAMPLE_RATE * 0.048))
    out: array.array[int] = array.array("h")
    for i in range(n):
        t = i / _SAMPLE_RATE
        sample = volume * 32767.0 * math.sin(2.0 * math.pi * frequency_hz * t)
        if i < attack:
            env = i / attack
        elif i >= n - release:
            env = (n - i) / release
        else:
            env = 1.0
        v = int(max(-32767, min(32767, sample * env)))
        out.append(v)
    return out


def _silence_samples(duration_sec: float) -> array.array[int]:
    n = max(0, int(_SAMPLE_RATE * duration_sec))
    return array.array("h", [0] * n)


def _mix_to_wav_bytes(chunks: list[array.array[int]]) -> bytes:
    buf = io.BytesIO()
    all_samples: array.array[int] = array.array("h")
    for c in chunks:
        all_samples.extend(c)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(all_samples.tobytes())
    return buf.getvalue()


def _play_wav(data: bytes) -> None:
    try:
        winsound.PlaySound(data, winsound.SND_MEMORY)
    except Exception:
        pass


def play_recording_started_chime() -> None:
    """Два короткых восходящих тона (мажорная терция) — «можно говорить»."""
    # C5 → E5
    a = _note_samples(523.25, 0.10, volume=0.25)
    gap = _silence_samples(0.03)
    b = _note_samples(659.25, 0.13, volume=0.23)
    _play_wav(_mix_to_wav_bytes([a, gap, b]))


def play_recording_stopped_chime() -> None:
    """Два нисходящих более низких тона — «стоп, обрабатываю»."""
    # G4 → D4
    a = _note_samples(392.0, 0.095, volume=0.21)
    gap = _silence_samples(0.038)
    b = _note_samples(293.66, 0.11, volume=0.19)
    _play_wav(_mix_to_wav_bytes([a, gap, b]))
