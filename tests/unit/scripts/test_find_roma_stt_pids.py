"""scripts/find_roma_stt_pids.py — разбор вывода wmic (без реального wmic)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import find_roma_stt_pids as frp


def test_pids_for_process_parses_matching_lines():
    line_ok = '"C:\\roma-stt\\.venv\\Scripts\\pythonw.exe" main.py --module cpu          12345      \n'
    stdout = "CommandLine                                                                 ProcessId  \n" + line_ok
    mock_run = MagicMock(returncode=0, stdout=stdout)
    with patch.object(frp.subprocess, "run", return_value=mock_run):
        pids = frp._pids_for_process("pythonw.exe")
    assert pids == ["12345"]


def test_pids_for_process_requires_both_main_and_roma_stt_in_line():
    line_no_roma = '"C:\\proj\\pythonw.exe" main.py --module cpu                            111        \n'
    stdout = "CommandLine                                                                 ProcessId  \n" + line_no_roma
    mock_run = MagicMock(returncode=0, stdout=stdout)
    with patch.object(frp.subprocess, "run", return_value=mock_run):
        assert frp._pids_for_process("pythonw.exe") == []

    line_ok = '"C:\\roma-stt\\.venv\\pythonw.exe" main.py --module cpu                  222        \n'
    stdout2 = "CommandLine                                                                 ProcessId  \n" + line_ok
    mock_run2 = MagicMock(returncode=0, stdout=stdout2)
    with patch.object(frp.subprocess, "run", return_value=mock_run2):
        assert frp._pids_for_process("pythonw.exe") == ["222"]


def test_pids_for_process_empty_on_failure():
    with patch.object(frp.subprocess, "run", return_value=MagicMock(returncode=1, stdout="")):
        assert frp._pids_for_process("pythonw.exe") == []


def test_pids_for_process_empty_when_wmic_missing():
    with patch.object(frp.subprocess, "run", side_effect=FileNotFoundError):
        assert frp._pids_for_process("python.exe") == []
