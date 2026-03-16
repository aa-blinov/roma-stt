"""Scan candidate global hotkeys and optionally update config.yaml.

Важно: RegisterHotKey в Windows требует, чтобы окно было создано в потоке,
который обрабатывает сообщения (message loop). Без этого API часто возвращает
False без кода ошибки. Поэтому сканирование выполняется в отдельном потоке
с окном и циклом сообщений, как в основной программе.
"""

from __future__ import annotations

import ctypes
import sys
import threading
from pathlib import Path

import win32gui

from infrastructure.config_repo import load_config as load_config_repo
from infrastructure.config_repo import save_config as save_config_repo
from presentation.hotkey import parse_hotkey

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"

# Код ошибки Windows: горячая клавиша уже зарегистрирована
ERROR_HOTKEY_ALREADY_REGISTERED = 1409

# Вызов WinAPI через ctypes, чтобы GetLastError не сбрасывался обёрткой pywin32
_user32 = ctypes.windll.user32  # type: ignore[attr-defined]
_kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
_user32.RegisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
_user32.RegisterHotKey.restype = ctypes.c_int
_user32.UnregisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int]
_user32.UnregisterHotKey.restype = ctypes.c_int


def _register_hotkey_ctypes(hwnd: int, hotkey_id: int, mod: int, vk: int) -> tuple[bool, int]:
    """RegisterHotKey через ctypes; возвращает (успех, GetLastError)."""
    ok = _user32.RegisterHotKey(ctypes.c_void_p(hwnd), hotkey_id, mod, vk)
    err = _kernel32.GetLastError()
    return bool(ok), err


def _run_scan_in_thread(candidates: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
    """Сканировать хоткеи в потоке с окном и message loop."""
    free: list[str] = []
    busy: list[tuple[str, str]] = []

    def thread_fn() -> None:
        wndclass = win32gui.WNDCLASS()
        wndclass.lpfnWndProc = win32gui.DefWindowProc
        wndclass.lpszClassName = "RomaSTT_HotkeyScanner"
        wndclass.hInstance = win32gui.GetModuleHandle(None)
        try:
            win32gui.RegisterClass(wndclass)
        except Exception:
            pass
        hwnd = win32gui.CreateWindow(
            "RomaSTT_HotkeyScanner",
            "Roma-STT Scanner",
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            wndclass.hInstance,
            None,
        )
        if not hwnd:
            busy.append(("?", "не удалось создать окно для теста"))
            return

        for hotkey_id, hotkey_str in enumerate(candidates, start=1):
            mod, vk = parse_hotkey(hotkey_str)
            ok, err = _register_hotkey_ctypes(hwnd, hotkey_id, mod, vk)
            if ok:
                _user32.UnregisterHotKey(ctypes.c_void_p(hwnd), hotkey_id)
                free.append(hotkey_str)
                continue
            if err == ERROR_HOTKEY_ALREADY_REGISTERED:
                busy.append((hotkey_str, "уже занята (1409)"))
            elif err != 0:
                busy.append((hotkey_str, f"ошибка WinAPI: {err}"))
            else:
                busy.append((hotkey_str, "False без кода (консольный процесс?)"))

        win32gui.PostQuitMessage(0)
        win32gui.PumpMessages()

    t = threading.Thread(target=thread_fn)
    t.start()
    t.join(timeout=60.0)
    if t.is_alive():
        busy.append(("?", "таймаут сканирования"))
    return free, busy


def load_config() -> dict:
    return load_config_repo(CONFIG_PATH)


def save_config(cfg: dict) -> None:
    save_config_repo(CONFIG_PATH, cfg)


def main() -> int:
    print("[X] Сканирование свободных горячих клавиш (Ctrl/Alt/Shift + F-клавиши)...")
    print("    (используется окно и цикл сообщений, как в основной программе)")
    candidates: list[str] = []

    # Базовые F-клавиши (Ctrl)
    for n in range(1, 13):
        candidates.append(f"Ctrl+F{n}")
    # С Shift / Alt
    for n in range(1, 13):
        candidates.append(f"Ctrl+Shift+F{n}")
        candidates.append(f"Ctrl+Alt+F{n}")

    free, busy = _run_scan_in_thread(candidates)

    if not free:
        print("Не удалось найти свободные комбинации из списка кандидатов.")
        print("Подробности по первым нескольким проверенным сочетаниям:")
        for hk, reason in busy[:10]:
            print(f"  {hk}: {reason}")
        print()
        if any("без кода" in r for _, r in busy[:5]):
            print(
                "Если везде «False без кода» — так бывает при запуске из консоли (python.exe).\n"
                "Используйте пункт 9: введите комбинацию вручную (например Ctrl+Shift+F12),\n"
                "затем пункт 6: при запуске программы хоткей зарегистрируется в нормальном процессе."
            )
        else:
            print(
                "Комбинации заняты другими программами или системой.\n"
                "Закройте приложения с глобальными хоткеями или укажите свою в пункте 9."
            )
        return 1

    print()
    print("Свободные комбинации (по мнению Windows на данный момент):")
    for idx, hk in enumerate(free, start=1):
        print(f"  {idx}. {hk}")
    print(
        "  (если в пункте 6 выбранная комбинация окажется занятой — подберётся запасная;\n"
        "   закрепите её снова через пункт 8 или 9)"
    )

    print()
    cfg = load_config()
    current = cfg.get("hotkey", "Ctrl+F9")
    print(f"Текущая комбинация из config.yaml: {current}")
    choice = input("Введите номер, чтобы записать в config.yaml (или Enter, чтобы ничего не менять): ").strip()
    if not choice:
        print("Конфиг не изменён.")
        return 0
    try:
        n = int(choice)
    except ValueError:
        print("Некорректный номер. Конфиг не изменён.")
        return 1
    if n < 1 or n > len(free):
        print("Номер вне диапазона. Конфиг не изменён.")
        return 1

    new_hotkey = free[n - 1]
    cfg["hotkey"] = new_hotkey
    save_config(cfg)
    print(f'Готово. В config.yaml записано: hotkey: "{new_hotkey}"')
    print("Теперь выберите пункт 6 в меню, чтобы запустить программу с новой горячей клавишей.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
