"""Одна строка JSON для шапки меню roma-stt.ps1 (без лишнего вывода от uv)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.control.menu_state import get_menu_state


def main() -> None:
    data = get_menu_state(ROOT / "config.yaml")
    print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    main()
