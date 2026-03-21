"""Сортировка подписей хоткеев для Control UI (без Qt — можно тестировать без PySide6)."""

from __future__ import annotations

import re


def sort_hotkey_labels(items: list[str]) -> list[str]:
    """Сортировка для выпадающих списков: по алфавиту, но F1…F12 по номеру (а не F10 перед F2)."""

    def sort_key(s: str) -> tuple:
        m = re.search(r"(?i)\bf\s*(\d{1,2})\b", s)
        if m:
            head = s[: m.start()].lower()
            return (0, head, int(m.group(1)), s.lower())
        return (1, s.lower())

    return sorted(items, key=sort_key)
