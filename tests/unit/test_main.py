"""Entry point: get_config_path, create_engine (mocked config/validation)."""

from unittest.mock import patch

import pytest

from main import create_engine, get_config_path


def test_get_config_path_returns_config_yaml_in_project_root():
    path = get_config_path()
    assert path.name == "config.yaml"
    assert path.parent.name != ""


@patch("main.validate_model_path")
def test_create_engine_builds_engine_from_config(mock_validate):
    config = {
        "whisper_cpp_path_cpu": "bin/main.exe",
        "whisper_model_path": "models/ggml-base.bin",
    }
    engine = create_engine("cpu", config)
    assert "main.exe" in str(engine.exe_path)
    assert "ggml-base" in str(engine.model_path)
    mock_validate.assert_called_once()


@patch("main.validate_model_path")
def test_create_engine_falls_back_to_cpu_path_when_module_path_missing(mock_validate):
    config = {
        "whisper_cpp_path_cpu": "bin/main.exe",
        "whisper_model_path": "models/ggml-base.bin",
    }
    engine = create_engine("cuda", config)
    assert "main.exe" in str(engine.exe_path)


def test_create_engine_raises_when_exe_missing():
    config = {"whisper_model_path": "models/ggml-base.bin"}
    with pytest.raises(ValueError, match="Config must set"):
        create_engine("cpu", config)


def test_create_engine_raises_when_model_missing():
    config = {"whisper_cpp_path_cpu": "bin/main.exe"}
    with pytest.raises(ValueError, match="whisper_model_path"):
        create_engine("cpu", config)
