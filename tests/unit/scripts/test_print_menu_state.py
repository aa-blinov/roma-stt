"""scripts/print_menu_state.py — JSON для шапки меню."""

from __future__ import annotations

import json
from unittest.mock import patch

import print_menu_state as pms


def test_main_prints_json_from_config(roma_tmp_layout, write_yaml_config, capsys) -> None:
    write_yaml_config(
        {
            "language": "de",
            "module": "cuda",
            "hotkey_record": "Ctrl+Shift+F5",
            "hotkey_stop": "Alt+F10",
            "whisper_model_path": "models/ggml-small.bin",
        }
    )
    with patch.object(pms, "ROOT", roma_tmp_layout):
        pms.main()
    out = capsys.readouterr().out.strip()
    data = json.loads(out)
    assert data == {
        "lang": "de",
        "model_stem": "ggml-small",
        "hotkey_record": "Ctrl+Shift+F5",
        "hotkey_stop": "Alt+F10",
        "module": "cuda",
    }


def test_main_defaults_when_keys_missing(roma_tmp_layout, write_yaml_config, capsys) -> None:
    write_yaml_config({})
    with patch.object(pms, "ROOT", roma_tmp_layout):
        pms.main()
    data = json.loads(capsys.readouterr().out.strip())
    assert data["lang"] == "ru"
    assert data["model_stem"] == ""
    assert data["module"] == "cpu"
    assert "F2" in data["hotkey_record"]
    assert "F3" in data["hotkey_stop"]
