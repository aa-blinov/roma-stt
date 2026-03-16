"""Paste text via clipboard and Ctrl+V. Infrastructure layer (Windows)."""

import pyperclip


def send_keys_ctrl_v() -> None:
    """Send Ctrl+V to active window (Windows)."""
    import win32api
    import win32con

    # Simulate Ctrl+V
    win32api.keybd_event(0x11, 0, 0, 0)  # VK_CONTROL down
    win32api.keybd_event(ord("V"), 0, 0, 0)  # V down
    win32api.keybd_event(ord("V"), 0, win32con.KEYEVENTF_KEYUP, 0)  # V up
    win32api.keybd_event(0x11, 0, win32con.KEYEVENTF_KEYUP, 0)  # Ctrl up


def paste_text(text: str) -> None:
    """Copy text to clipboard and send Ctrl+V to insert at cursor."""
    pyperclip.copy(text)
    send_keys_ctrl_v()
