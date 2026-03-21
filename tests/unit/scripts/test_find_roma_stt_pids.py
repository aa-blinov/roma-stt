"""application/control/process_scan.py — разбор вывода wmic (без реального wmic)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from application.control import process_scan as ps


def test_pids_for_process_parses_matching_lines():
    line_ok = '"C:\\roma-stt\\.venv\\Scripts\\pythonw.exe" main.py --module cpu          12345      \n'
    stdout = "CommandLine                                                                 ProcessId  \n" + line_ok
    mock_run = MagicMock(returncode=0, stdout=stdout)
    root = Path("S:/roma-stt")
    with patch.object(ps.subprocess, "run", return_value=mock_run):
        pids = ps._pids_for_process("pythonw.exe", root)
    assert pids == [12345]


def test_pids_for_process_requires_both_main_and_roma_stt_in_line():
    line_no_roma = '"C:\\proj\\pythonw.exe" main.py --module cpu                            111        \n'
    stdout = "CommandLine                                                                 ProcessId  \n" + line_no_roma
    mock_run = MagicMock(returncode=0, stdout=stdout)
    root = Path("S:/roma-stt")
    with patch.object(ps.subprocess, "run", return_value=mock_run):
        assert ps._pids_for_process("pythonw.exe", root) == []

    line_ok = '"C:\\roma-stt\\.venv\\pythonw.exe" main.py --module cpu                  222        \n'
    stdout2 = "CommandLine                                                                 ProcessId  \n" + line_ok
    mock_run2 = MagicMock(returncode=0, stdout=stdout2)
    with patch.object(ps.subprocess, "run", return_value=mock_run2):
        assert ps._pids_for_process("pythonw.exe", root) == [222]


def test_pids_for_process_empty_on_failure():
    root = Path("S:/roma-stt")
    with patch.object(ps.subprocess, "run", return_value=MagicMock(returncode=1, stdout="")):
        assert ps._pids_for_process("pythonw.exe", root) == []


def test_pids_for_process_empty_when_wmic_missing():
    root = Path("S:/roma-stt")
    with patch.object(ps.subprocess, "run", side_effect=FileNotFoundError):
        assert ps._pids_for_process("python.exe", root) == []


def test_find_script_main_delegates_to_scan():
    import find_roma_stt_pids as frp

    with patch.object(frp, "scan_roma_stt_pids", return_value=[1, 2]) as m:
        assert frp.main() == 0
    m.assert_called_once()
