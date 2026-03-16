"""Config and model path validation. Only multilingual models allowed; reject en-only."""

import re
from pathlib import Path

# Markers that indicate English-only model — reject these
EN_ONLY_MARKERS = (
    r"-en\.ggml",
    r"-en\.bin",
    r"\.en\.ggml",
    r"\.en\.bin",
    r"[/\\]en\.ggml",
    r"[/\\]en\.bin",
    r"en-only",
)


def is_multilingual_model_path(model_path: str | Path) -> bool:
    """
    Return True if the path is acceptable for a multilingual model.
    Reject paths that clearly indicate English-only models.
    """
    if not model_path:
        return False
    path_str = str(model_path).lower()
    for pattern in EN_ONLY_MARKERS:
        if re.search(pattern, path_str, re.IGNORECASE):
            return False
    return True


def validate_model_path(model_path: str | Path) -> None:
    """
    Validate that model path is for a multilingual model.
    Raises ValueError if path indicates en-only model.
    """
    if not is_multilingual_model_path(model_path):
        raise ValueError(
            f"Model path appears to be English-only (not allowed): {model_path}. Use only multilingual or turbo models."
        )
