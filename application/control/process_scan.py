"""Поиск PID процессов Roma-STT (main.py в пути roma-stt). Логика совпадает с scripts/find_roma_stt_pids.py."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


def _pids_for_process(exe_name: str, root: Path) -> list[int]:
    try:
        r = subprocess.run(
            ["wmic", "process", "where", f"name='{exe_name}'", "get", "processid,commandline"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(root),
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if r.returncode != 0 or not r.stdout:
        return []
    pids: list[int] = []
    for line in r.stdout.strip().splitlines()[1:]:
        if "main.py" not in line or "roma-stt" not in line:
            continue
        nums = re.findall(r"\d+", line)
        if nums:
            try:
                pids.append(int(nums[0]))
            except ValueError:
                continue
    return pids


def scan_roma_stt_pids(root: Path) -> list[int]:
    """PID всех python/pythonw с main.py и roma-stt в командной строке."""
    seen: set[int] = set()
    out: list[int] = []
    for exe_name in ("pythonw.exe", "python.exe"):
        for pid in _pids_for_process(exe_name, root):
            if pid not in seen:
                seen.add(pid)
                out.append(pid)
    return out


def is_pid_roma_stt_service(pid: int, root: Path) -> bool:
    """Как Test-CommandLineIsRomaSttService в roma-stt.ps1: main.py + (roma-stt|путь к проекту)."""
    try:
        r = subprocess.run(
            ["wmic", "process", "where", f"processid={pid}", "get", "commandline"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(root),
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    if r.returncode != 0 or not r.stdout:
        return False
    cmd = (r.stdout or "").lower()
    if "main.py" not in cmd:
        return False
    if "roma-stt" in cmd or "roma_stt" in cmd:
        return True
    root_s = str(root.resolve()).lower()
    return root_s in cmd
