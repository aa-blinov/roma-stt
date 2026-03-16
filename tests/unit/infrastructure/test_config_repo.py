"""Infrastructure: config read/write (temp dir)."""

import tempfile
from pathlib import Path

import yaml

# Will implement config loader in infrastructure
from infrastructure.config_repo import load_config, save_config


def test_load_config_reads_yaml():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        path.write_text("module: cpu\nhotkey: Ctrl+Win\nwhisper_model_path: models/x.ggml\n")
        cfg = load_config(path)
        assert cfg["module"] == "cpu"
        assert cfg["hotkey"] == "Ctrl+Win"
        assert cfg["whisper_model_path"] == "models/x.ggml"


def test_save_config_writes_yaml():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "config.yaml"
        save_config(path, {"module": "cuda", "hotkey": "Ctrl+Shift"})
        data = yaml.safe_load(path.read_text())
        assert data["module"] == "cuda"
        assert data["hotkey"] == "Ctrl+Shift"


def test_load_config_missing_file_returns_defaults_or_raises():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "nonexistent.yaml"
    cfg = load_config(path)
    # Allow returning defaults when file missing
    assert isinstance(cfg, dict)
