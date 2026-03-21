"""Вывести PID процессов python.exe / pythonw.exe, в командной строке которых есть main.py и roma-stt.
Логика в application.control.process_scan (единый источник)."""

import sys
from pathlib import Path

from application.control.process_scan import scan_roma_stt_pids

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    for pid in scan_roma_stt_pids(ROOT):
        print(pid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
