"""Entry point: parse --module, run tray + hotkey loop. Windows only."""

import argparse
import os
import tempfile
import threading
import winsound
from pathlib import Path

import win32con
import win32gui

from domain.config_validation import validate_model_path
from infrastructure.clipboard_paste import paste_text
from infrastructure.config_repo import load_config
from infrastructure.recorder import record_to_wav_until_stopped
from infrastructure.whisper_cpp_engine import WhisperCppEngine
from presentation.hotkey import parse_hotkey, register_hotkey
from presentation.tray_app import create_tray_icon

HOTKEY_ID = 1
CONFIG_FILENAME = "config.yaml"

# Те же кандидаты, что в сканере (пункт 8)
_HOTKEY_FALLBACKS = [f"Ctrl+F{n}" for n in range(1, 13)]
_HOTKEY_FALLBACKS += [f"Ctrl+Shift+F{n}" for n in range(1, 13)]
_HOTKEY_FALLBACKS += [f"Ctrl+Alt+F{n}" for n in range(1, 13)]


def _probe_hotkey_in_process(config_hotkey: str) -> str | None:
    """В этом же процессе найти комбинацию, которую удаётся зарегистрировать (окно + message loop).
    Возвращает первую подошедшую или None. После проверки хоткей снимается — его займёт уже рабочий поток.
    """
    result: list[str] = []

    def thread_fn() -> None:
        wndclass = win32gui.WNDCLASS()
        wndclass.lpfnWndProc = win32gui.DefWindowProc
        wndclass.lpszClassName = "RomaSTT_Probe"
        wndclass.hInstance = win32gui.GetModuleHandle(None)
        try:
            win32gui.RegisterClass(wndclass)
        except Exception:
            pass
        hwnd = win32gui.CreateWindow("RomaSTT_Probe", "Probe", 0, 0, 0, 0, 0, 0, 0, wndclass.hInstance, None)
        if not hwnd:
            return
        candidates = [config_hotkey] + [c for c in _HOTKEY_FALLBACKS if c != config_hotkey]
        for i, hotkey_str in enumerate(candidates):
            mod, vk = parse_hotkey(hotkey_str)
            if register_hotkey(hwnd, 1, mod, vk):
                result.append(hotkey_str)
                win32gui.UnregisterHotKey(hwnd, 1)
                break
        win32gui.PostQuitMessage(0)
        win32gui.PumpMessages()

    t = threading.Thread(target=thread_fn)
    t.start()
    t.join(timeout=15.0)
    return result[0] if result else None


def get_config_path() -> Path:
    """Конфиг из текущей папки (как у сканера и батника) или рядом с main.py."""
    cwd_config = Path.cwd() / CONFIG_FILENAME
    if cwd_config.exists():
        return cwd_config
    return Path(__file__).resolve().parent / CONFIG_FILENAME


def create_engine(module: str, config: dict) -> WhisperCppEngine:
    """Build WhisperCppEngine for given module from config."""
    key = f"whisper_cpp_path_{module}"
    exe = config.get(key) or config.get("whisper_cpp_path_cpu", "")
    model = config.get("whisper_model_path", "")
    if not exe or not model:
        raise ValueError(f"Config must set {key} and whisper_model_path")
    validate_model_path(model)
    return WhisperCppEngine(exe_path=exe, model_path=model)


def main() -> None:
    parser = argparse.ArgumentParser(description="Roma-STT: Speech-to-Text tray app (Windows)")
    parser.add_argument("--module", choices=["cpu", "cuda", "amd"], default="cpu", help="STT module")
    args = parser.parse_args()
    config_path = get_config_path()
    config = load_config(config_path)
    module = args.module or config.get("module", "cpu")
    config["module"] = module

    # Не запускать второй экземпляр — иначе горячие клавиши конфликтуют
    if win32gui.FindWindow("RomaSTT", None):
        print("Roma-STT уже запущена в трее. Остановите её пунктом 7, затем запустите снова.")
        return

    # В этом процессе проверить, какую комбинацию реально удаётся занять (сканер — пункт 8 — другой процесс)
    wanted = config.get("hotkey", "Ctrl+F9")
    probed = _probe_hotkey_in_process(wanted)
    if probed:
        config["hotkey"] = probed
        if probed != wanted:
            print(f"Выбранная в пункте 8 комбинация ({wanted}) в этом процессе занята.")
            print(f"Используется: {probed}. Чтобы сделать её по умолчанию — снова пункт 8 или 9.")
    # Если проба ничего не нашла — всё равно запускаем поток с хоткеем (другое окно/поток может сработать)

    try:
        engine = create_engine(module, config)
    except (ValueError, FileNotFoundError) as e:
        print(f"Config error: {e}. Run roma-stt.bat -> Install, then set paths in config.")
        return

    stop_event = threading.Event()
    record_thread: threading.Thread | None = None
    wav_path: str | None = None
    pid_file = get_config_path().parent / ".roma-stt.pid"

    def remove_pid_file():
        pid_file.unlink(missing_ok=True)

    icon = create_tray_icon(
        Path(__file__).parent / "tray_icon.svg",
        on_before_exit=remove_pid_file,
        hotkey_hint=config.get("hotkey", "Ctrl+F9"),
    )
    tray_ref: list = [icon]  # for notifications from hotkey thread

    def on_hotkey() -> None:
        nonlocal record_thread, wav_path
        if record_thread is None or not record_thread.is_alive():
            # Start recording
            try:
                winsound.Beep(880, 120)  # один короткий высокий звук — запись началась
            except Exception:
                pass
            if tray_ref and tray_ref[0]:
                try:
                    tray_ref[0].notify(
                        "Говорите. Нажмите горячую клавишу ещё раз, чтобы остановить и вставить текст.",
                        "Roma-STT — запись",
                    )
                except Exception:
                    pass
            stop_event.clear()
            fd, wav_path = tempfile.mkstemp(suffix=".wav")
            import os

            os.close(fd)
            record_thread = threading.Thread(
                target=record_to_wav_until_stopped,
                args=(wav_path, stop_event),
                daemon=True,
            )
            record_thread.start()
        else:
            # Stop recording, transcribe, paste
            try:
                winsound.Beep(440, 80)
                winsound.Beep(440, 80)  # два коротких низких звука — запись остановлена
            except Exception:
                pass
            if tray_ref and tray_ref[0]:
                try:
                    tray_ref[0].notify("Остановка записи, распознавание...", "Roma-STT")
                except Exception:
                    pass
            stop_event.set()
            record_thread.join(timeout=10)
            record_thread = None
            if wav_path:
                try:
                    lang = config.get("language", "ru")
                    # Use GPU if module is not cpu
                    gpu_layers = 99 if module != "cpu" else 0
                    text = engine.transcribe(wav_path, language=lang, n_gpu_layers=gpu_layers)
                    paste_text(text)
                    if tray_ref and tray_ref[0]:
                        try:
                            tray_ref[0].notify("Текст вставлен.", "Roma-STT")
                        except Exception:
                            pass
                finally:
                    Path(wav_path).unlink(missing_ok=True)
                wav_path = None

    def wnd_proc(hwnd, msg, wparam, lparam):
        if msg == win32con.WM_HOTKEY and wparam == HOTKEY_ID:
            on_hotkey()
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def run_hotkey_loop():
        wndclass = win32gui.WNDCLASS()
        wndclass.lpfnWndProc = wnd_proc
        wndclass.lpszClassName = "RomaSTT"
        wndclass.hInstance = win32gui.GetModuleHandle(None)
        win32gui.RegisterClass(wndclass)
        hwnd = win32gui.CreateWindow("RomaSTT", "Roma-STT", 0, 0, 0, 0, 0, 0, 0, wndclass.hInstance, None)
        # Тот же parse_hotkey и RegisterHotKey, что в сканере (пункт 8); mod/vk — как в WinAPI
        hotkey_str = config.get("hotkey", "Ctrl+F9")
        mod, vk = parse_hotkey(hotkey_str)
        ok = register_hotkey(hwnd, HOTKEY_ID, mod, vk)
        used_fallback = False
        if not ok:
            # Те же комбинации, что сканер (пункт 8) — перебираем, пока одна не зарегистрируется
            fallbacks = [f"Ctrl+F{n}" for n in range(1, 13)]
            fallbacks += [f"Ctrl+Shift+F{n}" for n in range(1, 13)]
            fallbacks += [f"Ctrl+Alt+F{n}" for n in range(1, 13)]
            for candidate in fallbacks:
                m, v = parse_hotkey(candidate)
                if register_hotkey(hwnd, HOTKEY_ID, m, v):
                    hotkey_str = candidate
                    used_fallback = True
                    ok = True
                    break
        if not ok:
            print("Не удалось зарегистрировать ни одну комбинацию в этом процессе. Выход.")
            os._exit(1)
        print(f"Горячая клавиша: {hotkey_str}", end="")
        if used_fallback:
            print(" (запасная; чтобы закрепить — пункт 8 или 9)")
        else:
            print()
        win32gui.PumpMessages()

    hotkey_thread = threading.Thread(target=run_hotkey_loop, daemon=True)
    hotkey_thread.start()

    # Файл с PID — пункт 7 батника убивает процесс по этому PID
    pid_file.write_text(str(os.getpid()), encoding="utf-8")
    icon.run()


if __name__ == "__main__":
    main()
