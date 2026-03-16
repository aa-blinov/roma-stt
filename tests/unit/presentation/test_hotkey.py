"""Presentation: hotkey parsing (parse_hotkey is pure logic, no win32 in tests)."""

from presentation.hotkey import VK_F9, parse_hotkey


def test_parse_hotkey_ctrl_f9():
    mod, vk = parse_hotkey("Ctrl+F9")
    assert mod != 0
    assert vk == 0x78  # VK_F9


def test_parse_hotkey_ctrl_win():
    """Только модификаторы — по умолчанию vk = F9."""
    mod, vk = parse_hotkey("Ctrl+Win")
    assert mod != 0
    assert vk == VK_F9


def test_parse_hotkey_single_modifier():
    mod, vk = parse_hotkey("Ctrl")
    assert vk == VK_F9


def test_parse_hotkey_with_letter():
    mod, vk = parse_hotkey("Ctrl+A")
    assert vk == ord("A")


def test_parse_hotkey_alt_shift():
    mod, vk = parse_hotkey("Alt+Shift")
    assert vk == VK_F9


def test_parse_hotkey_f12():
    mod, vk = parse_hotkey("Ctrl+Shift+F12")
    assert vk == 0x7B  # VK_F12


def test_parse_hotkey_normalizes_whitespace():
    mod, vk = parse_hotkey("  Ctrl  +  F9  ")
    assert vk == 0x78


def test_parse_hotkey_case_insensitive():
    mod1, vk1 = parse_hotkey("ctrl+f9")
    mod2, vk2 = parse_hotkey("CTRL+F9")
    assert mod1 == mod2 and vk1 == vk2
