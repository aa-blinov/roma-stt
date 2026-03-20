"""infrastructure/ui_chimes.py — формат WAV и отсутствие падений при воспроизведении."""

from __future__ import annotations

from unittest.mock import patch

import infrastructure.ui_chimes as uc


def test_mix_to_wav_is_valid_riff():
    data = uc._mix_to_wav_bytes([uc._note_samples(440.0, 0.02, volume=0.1)])
    assert data[:4] == b"RIFF"
    assert data[8:12] == b"WAVE"


@patch.object(uc.winsound, "PlaySound", side_effect=OSError("no device"))
def test_play_wav_swallows_errors(_mock_play):
    uc._play_wav(b"not a wav")  # should not raise


def test_play_recording_chimes_call_playsound():
    with patch.object(uc.winsound, "PlaySound") as mock_play:
        uc.play_recording_started_chime()
        uc.play_recording_stopped_chime()
    assert mock_play.call_count == 2
    for call in mock_play.call_args_list:
        wav_blob = call[0][0]
        assert isinstance(wav_blob, bytes)
        assert wav_blob[:4] == b"RIFF"
