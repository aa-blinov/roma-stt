"""Вывести PID процессов python.exe, в командной строке которых есть main.py и roma-stt. Для пункта 7 батника.
Использует wmic (не PowerShell), чтобы не менять шрифт/настройки консоли."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    # wmic не меняет настройки консоли в отличие от PowerShell
    try:
        r = subprocess.run(
            ["wmic", "process", "where", "name='python.exe'", "get", "processid,commandline"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=ROOT,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 0
    if r.returncode != 0 or not r.stdout:
        return 0
    lines = r.stdout.strip().splitlines()
    if not lines:
        return 0
    # Первая строка — заголовок (ProcessId  CommandLine), дальше — данные
    for line in lines[1:]:
        if "main.py" not in line or "roma-stt" not in line:
            continue
        # PID — первое число в строке (колонка ProcessId идёт первой в wmic get processid,commandline)
        nums = re.findall(r"\d+", line)
        if nums:
            print(nums[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
