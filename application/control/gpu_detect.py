"""Определение видеокарты для доступных архитектур whisper (как Detect-Gpu в roma-stt.ps1)."""

from __future__ import annotations

import subprocess
from typing import Any


def detect_gpu() -> dict[str, Any]:
    """NVIDIA / AMD по WMI. Без GPU — только CPU-режим в UI."""
    nvidia_name = ""
    amd_name = ""
    try:
        r = subprocess.run(
            ["wmic", "path", "Win32_VideoController", "get", "Name"],
            capture_output=True,
            text=True,
            timeout=15,
            encoding="utf-8",
            errors="replace",
        )
        if r.returncode != 0 or not r.stdout:
            return _result(nvidia_name, amd_name)
        for raw in r.stdout.splitlines():
            line = raw.strip()
            if not line or line.lower() == "name":
                continue
            low = line.lower()
            if "nvidia" in low and not nvidia_name:
                nvidia_name = line
            if ("amd" in low or "radeon" in low) and not amd_name:
                amd_name = line
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return _result(nvidia_name, amd_name)


def _result(nvidia_name: str, amd_name: str) -> dict[str, Any]:
    return {
        "nvidia_name": nvidia_name,
        "amd_name": amd_name,
        "has_nvidia": bool(nvidia_name),
        "has_amd": bool(amd_name),
    }


def available_whisper_archs(gpu: dict[str, Any] | None = None) -> list[str]:
    """Список архитектур для ComboBox: cpu всегда; cuda и amd только при наличии GPU."""
    if gpu is None:
        gpu = detect_gpu()
    out: list[str] = ["cpu"]
    if gpu.get("has_nvidia"):
        out.append("cuda")
    if gpu.get("has_amd"):
        out.append("amd")
    return out
