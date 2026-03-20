"""scripts/check_ready.py — точечные проверки без полного окружения."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import check_ready as cr


def test_check_nvcc_returns_bool_and_message():
    ok, msg = cr.check_nvcc()
    assert isinstance(ok, bool)
    assert isinstance(msg, str)
    assert "nvcc" in msg.lower() or "cuda" in msg.lower()


def test_check_config_missing_file(tmp_path: Path):
    missing = tmp_path / "nope.yaml"
    ok, msg = cr.check_config(missing)
    assert ok is False
    assert "missing" in msg.lower()


def test_check_config_ok_with_mocks(monkeypatch, roma_tmp_layout, write_yaml_config):
    (roma_tmp_layout / "bin" / "w.exe").write_bytes(b"")
    (roma_tmp_layout / "models" / "m.bin").write_bytes(b"")
    cfg = write_yaml_config(
        {
            "module": "cpu",
            "whisper_cpp_path_cpu": "bin/w.exe",
            "whisper_model_path": "models/m.bin",
        }
    )
    monkeypatch.setattr(cr, "ROOT", roma_tmp_layout)
    with patch.object(cr, "check_whisper_runs", return_value=(True, "whisper.cpp: runs OK")):
        ok, msg = cr.check_config(cfg)
    assert ok is True
    assert "OK" in msg


def test_check_config_exe_missing(monkeypatch, roma_tmp_layout, write_yaml_config):
    (roma_tmp_layout / "models" / "m.bin").write_bytes(b"")
    cfg = write_yaml_config(
        {
            "module": "cpu",
            "whisper_cpp_path_cpu": "bin/missing.exe",
            "whisper_model_path": "models/m.bin",
        }
    )
    monkeypatch.setattr(cr, "ROOT", roma_tmp_layout)
    ok, msg = cr.check_config(cfg)
    assert ok is False
    assert "not found" in msg.lower()
