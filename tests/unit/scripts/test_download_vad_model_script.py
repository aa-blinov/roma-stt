"""scripts/download_vad_model.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import download_vad_model as dvm


@patch("download_vad_model.urllib.request.urlopen")
def test_download_vad_writes_default_filename(mock_urlopen, models_dir_path):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"fake-vad"
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_resp
    mock_cm.__exit__.return_value = None
    mock_urlopen.return_value = mock_cm

    assert dvm.download_vad_model(models_dir_path) is True
    out = models_dir_path / dvm.DEFAULT_NAME
    assert out.read_bytes() == b"fake-vad"
    mock_urlopen.assert_called_once()


def test_download_vad_idempotent(models_dir_path):
    existing = models_dir_path / dvm.DEFAULT_NAME
    existing.write_bytes(b"was")
    with patch("download_vad_model.urllib.request.urlopen") as mock_urlopen:
        assert dvm.download_vad_model(models_dir_path) is True
    mock_urlopen.assert_not_called()
    assert existing.read_bytes() == b"was"


@patch("download_vad_model.urllib.request.urlopen")
def test_download_vad_removes_partial_on_error(mock_urlopen, models_dir_path):
    mock_urlopen.side_effect = OSError("network")

    assert dvm.download_vad_model(models_dir_path) is False
    partial = models_dir_path / dvm.DEFAULT_NAME
    assert not partial.exists()
