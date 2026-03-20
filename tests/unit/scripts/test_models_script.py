"""scripts/models.py — манифест, поиск файлов, запись config."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

import models as models_cli


def test_manifest_matches_whisper_order():
    assert list(models_cli.ORDERED_NAMES) == list(models_cli.ORDERED_MODEL_KEYS)
    assert set(models_cli.MODELS_MANIFEST) == set(models_cli.ORDERED_NAMES)


def test_is_model_downloaded_ggml_prefix(monkeypatch, models_dir_path: Path):
    (models_dir_path / "ggml-small.bin").write_bytes(b"x")
    monkeypatch.setattr(models_cli, "MODELS_DIR", models_dir_path)
    assert models_cli._is_model_downloaded("small") is True
    assert models_cli._is_model_downloaded("tiny") is False


def test_path_for_model_name_variants(monkeypatch, models_dir_path: Path):
    (models_dir_path / "ggml-medium.bin").touch()
    monkeypatch.setattr(models_cli, "MODELS_DIR", models_dir_path)
    p = models_cli._path_for_model_name("medium")
    assert p is not None
    assert p.name == "ggml-medium.bin"


def test_set_active_writes_whisper_model_path(monkeypatch, roma_tmp_layout, models_dir_path: Path):
    bin_path = models_dir_path / "ggml-base.bin"
    bin_path.write_bytes(b"x")
    cfg_path = roma_tmp_layout / "config.yaml"
    monkeypatch.setattr(models_cli, "MODELS_DIR", models_dir_path)
    monkeypatch.setattr(models_cli, "CONFIG_PATH", cfg_path)
    models_cli.set_active("base")
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert Path(data["whisper_model_path"]).resolve() == bin_path.resolve()


def test_set_active_exits_when_missing(monkeypatch, roma_tmp_layout, models_dir_path: Path):
    monkeypatch.setattr(models_cli, "MODELS_DIR", models_dir_path)
    monkeypatch.setattr(models_cli, "CONFIG_PATH", roma_tmp_layout / "config.yaml")
    with pytest.raises(SystemExit):
        models_cli.set_active("tiny")


def test_set_active_by_number_exits_when_not_downloaded(monkeypatch, models_dir_path: Path):
    monkeypatch.setattr(models_cli, "MODELS_DIR", models_dir_path)
    with pytest.raises(SystemExit):
        models_cli.set_active_by_number("1")


def test_use_by_number_skips_download_when_model_present(monkeypatch, roma_tmp_layout, models_dir_path: Path):
    (models_dir_path / "ggml-tiny.bin").touch()
    cfg_path = roma_tmp_layout / "config.yaml"
    monkeypatch.setattr(models_cli, "MODELS_DIR", models_dir_path)
    monkeypatch.setattr(models_cli, "CONFIG_PATH", cfg_path)
    monkeypatch.setattr(models_cli, "ROOT", roma_tmp_layout)
    with patch.object(models_cli.subprocess, "run") as mock_run:
        models_cli.use_by_number("1")
    mock_run.assert_not_called()
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert "tiny" in data["whisper_model_path"]


def test_use_by_number_downloads_then_sets_config(monkeypatch, roma_tmp_layout, models_dir_path: Path):
    """Номер 2 → tiny-q8_0; пока файла нет — вызывается download_model, затем активируем."""
    cfg_path = roma_tmp_layout / "config.yaml"
    monkeypatch.setattr(models_cli, "MODELS_DIR", models_dir_path)
    monkeypatch.setattr(models_cli, "CONFIG_PATH", cfg_path)
    monkeypatch.setattr(models_cli, "ROOT", roma_tmp_layout)

    def run_side_effect(cmd, cwd=None, **_kwargs):
        assert "download_model.py" in str(cmd)
        assert cwd == str(roma_tmp_layout)
        (models_dir_path / "ggml-tiny-q8_0.bin").write_bytes(b"x")
        return MagicMock(returncode=0)

    with patch.object(models_cli.subprocess, "run", side_effect=run_side_effect):
        models_cli.use_by_number("2")

    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert "tiny-q8_0" in data["whisper_model_path"]
