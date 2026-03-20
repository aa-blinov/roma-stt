"""scripts/download_model.py — словарь моделей и логика download()."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import download_model as dm
import whisper_models as wm


def test_models_order_matches_whisper_catalog():
    assert dm.ORDERED_MODELS == list(wm.ORDERED_MODEL_KEYS)
    assert set(dm.MODELS) == set(wm.ORDERED_MODEL_KEYS)


def test_download_unknown_returns_false(capsys):
    assert dm.download("not-a-real-model") is False
    err = capsys.readouterr().out
    assert "Unknown model" in err


@patch("download_model.urllib.request.urlopen")
def test_download_writes_file(mock_urlopen, models_dir_path):
    mock_resp = MagicMock()
    mock_resp.headers.get.return_value = "10"
    mock_resp.read.side_effect = [b"ggml-fake", b""]
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_resp
    mock_cm.__exit__.return_value = None
    mock_urlopen.return_value = mock_cm

    ok = dm.download("tiny", dest_dir=models_dir_path)
    assert ok is True
    out = models_dir_path / "ggml-tiny.bin"
    assert out.read_bytes() == b"ggml-fake"


@patch("download_model.urllib.request.urlopen")
def test_download_skips_if_exists(mock_urlopen, models_dir_path):
    existing = models_dir_path / "ggml-tiny.bin"
    existing.write_bytes(b"old")
    assert dm.download("tiny", dest_dir=models_dir_path) is True
    mock_urlopen.assert_not_called()
    assert existing.read_bytes() == b"old"
