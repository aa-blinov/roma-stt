"""Infrastructure: config read/write (temp dir)."""

import tempfile
from pathlib import Path

import yaml

# Will implement config loader in infrastructure
from infrastructure.config_repo import load_config, save_config


def test_load_config_reads_yaml():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text(
            "module: cpu\nhotkey_record: Ctrl+F2\nhotkey_stop: Ctrl+F3\nwhisper_model_path: models/x.ggml\n"
        )
        cfg = load_config(path)
        assert cfg["module"] == "cpu"
        assert cfg["hotkey_record"] == "Ctrl+F2"
        assert cfg["hotkey_stop"] == "Ctrl+F3"
        assert cfg["whisper_model_path"] == "models/x.ggml"


def test_save_config_writes_yaml():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        save_config(path, {"module": "cuda", "hotkey_record": "Ctrl+F2", "hotkey_stop": "Ctrl+F3"})
        data = yaml.safe_load(path.read_text())
        assert data["module"] == "cuda"
        assert data["hotkey_record"] == "Ctrl+F2"
        assert data["hotkey_stop"] == "Ctrl+F3"


def test_load_config_missing_file_returns_defaults_or_raises():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "nonexistent.yaml"
    cfg = load_config(path)
    # Allow returning defaults when file missing
    assert isinstance(cfg, dict)


def test_load_config_merges_defaults_for_missing_keys():
    """Keys absent in YAML are filled from DEFAULT_CONFIG."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text("module: amd\n")
        cfg = load_config(path)
        assert cfg["module"] == "amd"
        assert cfg["hotkey_record"] == "Ctrl+F2"
        assert cfg["hotkey_stop"] == "Ctrl+F3"
        assert cfg["language"] == "ru"
        assert cfg["notifications"] is False


def test_load_config_removes_deprecated_hotkey_key():
    """Old 'hotkey' key must be stripped from loaded config."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text("module: cpu\nhotkey: Ctrl+F9\nhotkey_record: Ctrl+F2\nhotkey_stop: Ctrl+F3\n")
        cfg = load_config(path)
        assert "hotkey" not in cfg


def test_load_config_notifications_default_false():
    """notifications must default to False even when not in YAML."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text("module: cpu\n")
        cfg = load_config(path)
        assert cfg.get("notifications") is False


def test_save_and_reload_roundtrip():
    """Save then reload preserves all values including notifications."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        original = {
            "module": "cuda",
            "hotkey_record": "Ctrl+F3",
            "hotkey_stop": "Ctrl+F4",
            "language": "en",
            "notifications": True,
            "input_device": 2,
            "whisper_cpp_path_cpu": "bin/main-cpu.exe",
            "whisper_cpp_path_cuda": "bin/main-cuda.exe",
            "whisper_cpp_path_amd": "",
            "whisper_model_path": "models/x.bin",
        }
        save_config(path, original)
        loaded = load_config(path)
        assert loaded["module"] == "cuda"
        assert loaded["language"] == "en"
        assert loaded["notifications"] is True
        assert loaded["input_device"] == 2
