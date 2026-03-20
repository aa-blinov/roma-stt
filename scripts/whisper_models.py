"""Каталог мультиязычных ggml-моделей ggerganov/whisper.cpp (без .en).

Порядок: по возрастанию «тяжести» архитектуры; внутри каждой линейки —
полная (FP16) → Q8 → Q5. Для large-v3 без turbo на HF нет Q8, только Q5.
"""

from __future__ import annotations

HF_BASE = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"

# (ключ совпадает с суффиксом файла ggml-{ключ}.bin)
WHISPER_MODEL_ROWS: list[tuple[str, str]] = [
    ("tiny", "мультиязычная, полная (~75 MiB)"),
    ("tiny-q8_0", "мультиязычная, квант Q8"),
    ("tiny-q5_1", "мультиязычная, квант Q5"),
    ("base", "мультиязычная, полная (~142 MiB)"),
    ("base-q8_0", "мультиязычная, квант Q8"),
    ("base-q5_1", "мультиязычная, квант Q5"),
    ("small", "мультиязычная, полная (~466 MiB)"),
    ("small-q8_0", "мультиязычная, квант Q8"),
    ("small-q5_1", "мультиязычная, квант Q5"),
    ("medium", "мультиязычная, полная (~1.5 GiB)"),
    ("medium-q8_0", "мультиязычная, квант Q8"),
    ("medium-q5_0", "мультиязычная, квант Q5"),
    ("large-v1", "мультиязычная, large v1 (устаревшая)"),
    ("large-v2", "мультиязычная, large v2, полная (~3 GiB)"),
    ("large-v2-q8_0", "мультиязычная, v2, квант Q8"),
    ("large-v2-q5_0", "мультиязычная, v2, квант Q5"),
    ("large-v3", "мультиязычная, v3, рекомендуется (~3 GiB)"),
    ("large-v3-q5_0", "мультиязычная, v3, квант Q5"),
    ("large-v3-turbo", "мультиязычная, v3 turbo, полная"),
    ("large-v3-turbo-q8_0", "мультиязычная, turbo, квант Q8"),
    ("large-v3-turbo-q5_0", "мультиязычная, turbo, квант Q5"),
]

ORDERED_MODEL_KEYS = [row[0] for row in WHISPER_MODEL_ROWS]
MODEL_DESCRIPTIONS = dict(WHISPER_MODEL_ROWS)


def model_download_url(key: str) -> str:
    return f"{HF_BASE}/ggml-{key}.bin"
