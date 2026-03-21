"""Обёртка над scripts/check_ready.py без subprocess (один ROOT)."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def load_check_ready_module(root: Path):
    path = root / "scripts" / "check_ready.py"
    spec = importlib.util.spec_from_file_location("roma_stt_check_ready", path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(f"check_ready not found: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def get_readiness_summary(root: Path) -> tuple[bool, str]:
    """(all_ok, first_fail_message_or_empty)."""
    try:
        mod = load_check_ready_module(root)
        all_ok, checks = mod.run_checks()
        first_fail = next((m for ok, m in checks if not ok), "")
        return all_ok, first_fail
    except Exception as e:
        return False, str(e)


def get_readiness_lines(root: Path) -> list[str]:
    """Строки как в полном выводе check_ready (без nvcc extra block для краткости — основные проверки)."""
    try:
        mod = load_check_ready_module(root)
        all_ok, checks = mod.run_checks()
        lines = []
        for ok, msg in checks:
            status = "OK" if ok else "FAIL"
            lines.append(f"  [{status}] {msg}")
        lines.append(f"  [{'OK' if all_ok else 'FAIL'}] overall")
        return lines
    except Exception as e:
        return [f"  [FAIL] {e}"]
