"""Точка входа: Roma-STT Control — окно без консольного меню."""

from __future__ import annotations

import sys
from pathlib import Path

# Корень репозитория: presentation/control_gui/main.py -> ../..
ROOT = Path(__file__).resolve().parent.parent.parent


def _ensure_project_path() -> None:
    r = str(ROOT)
    if r not in sys.path:
        sys.path.insert(0, r)


def main() -> None:
    _ensure_project_path()

    from PySide6.QtWidgets import QApplication

    from presentation.control_gui.main_window import ControlMainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Roma-STT Control")
    w = ControlMainWindow(ROOT)
    w.show()
    sys.exit(app.exec())
