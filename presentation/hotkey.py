import pywintypes
import win32con
import win32gui


def register_hotkey(hwnd: int, hotkey_id: int, mod: int, vk: int) -> bool:
    """Register global hotkey. Returns True if successful, False if already busy."""
    try:
        win32gui.RegisterHotKey(hwnd, hotkey_id, mod, vk)
        return True
    except pywintypes.error as e:
        if e.winerror == 1409:  # Hotkey already registered
            return False
        raise


# VK для F1..F12 (Windows)
VK_F1, VK_F2, VK_F3, VK_F4, VK_F5, VK_F6 = 0x70, 0x71, 0x72, 0x73, 0x74, 0x75
VK_F7, VK_F8, VK_F9, VK_F10, VK_F11, VK_F12 = 0x76, 0x77, 0x78, 0x79, 0x7A, 0x7B

F_KEYS = {
    "f1": VK_F1,
    "f2": VK_F2,
    "f3": VK_F3,
    "f4": VK_F4,
    "f5": VK_F5,
    "f6": VK_F6,
    "f7": VK_F7,
    "f8": VK_F8,
    "f9": VK_F9,
    "f10": VK_F10,
    "f11": VK_F11,
    "f12": VK_F12,
}


def parse_hotkey(hotkey_str: str) -> tuple[int, int]:
    """Parse hotkey string like 'Ctrl+F9' or 'Ctrl+Win' into (mod, vk)."""
    mod = 0
    vk = 0
    parts = hotkey_str.replace("+", " ").strip().lower().split()
    for p in parts:
        if p == "ctrl":
            mod |= win32con.MOD_CONTROL
        elif p == "alt":
            mod |= win32con.MOD_ALT
        elif p == "shift":
            mod |= win32con.MOD_SHIFT
        elif p == "win":
            mod |= win32con.MOD_WIN
        elif p in F_KEYS:
            vk = F_KEYS[p]
        else:
            if len(p) == 1:
                vk = ord(p.upper())
            else:
                vk = 0
    if vk == 0:
        vk = VK_F9  # по умолчанию F9, если только модификаторы
    return mod, vk
