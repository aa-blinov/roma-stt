"""application.control.gpu_detect — доступные архитектуры."""

from unittest.mock import patch

from application.control.gpu_detect import available_whisper_archs


def test_available_archs_cpu_only_without_gpu():
    gpu = {
        "nvidia_name": "",
        "amd_name": "",
        "has_nvidia": False,
        "has_amd": False,
    }
    assert available_whisper_archs(gpu) == ["cpu"]


def test_available_archs_includes_cuda_and_amd_when_present():
    gpu = {
        "nvidia_name": "NVIDIA GeForce RTX",
        "amd_name": "AMD Radeon RX",
        "has_nvidia": True,
        "has_amd": True,
    }
    assert available_whisper_archs(gpu) == ["cpu", "cuda", "amd"]
