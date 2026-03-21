"""Сортировка подписей хоткеев в Control UI."""

from presentation.control_gui.hotkey_sort import sort_hotkey_labels


def test_sort_f_keys_by_number_not_string():
    raw = ["Ctrl+F10", "Ctrl+F2", "Ctrl+F1"]
    assert sort_hotkey_labels(raw) == ["Ctrl+F1", "Ctrl+F2", "Ctrl+F10"]


def test_sort_same_prefix_groups():
    raw = ["Ctrl+Shift+F2", "Ctrl+F2", "Ctrl+F1"]
    assert sort_hotkey_labels(raw) == ["Ctrl+F1", "Ctrl+F2", "Ctrl+Shift+F2"]
