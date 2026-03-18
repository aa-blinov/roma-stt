"""Вывести PID процессов python.exe / pythonw.exe, в командной строке которых есть main.py и roma-stt.
Для пункта 4 батника (остановка службы). Служба запускается через pythonw.exe — ищем оба имени."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _pids_for_process(name: str) -> list[str]:
    try:
        r = subprocess.run(
            ["wmic", "process", "where", f"name='{name}'", "get", "processid,commandline"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=ROOT,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if r.returncode != 0 or not r.stdout:
        return []
    pids = []
    for line in r.stdout.strip().splitlines()[1:]:
        if "main.py" not in line or "roma-stt" not in line:
            continue
        nums = re.findall(r"\d+", line)
        if nums:
            pids.append(nums[0])
    return pids


def main() -> int:
    for pid in _pids_for_process("pythonw.exe") + _pids_for_process("python.exe"):
        print(pid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
