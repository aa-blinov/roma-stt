"""Entry point: parse --module, run tray + hotkey loop. Windows only."""

import argparse
import logging
import os
import subprocess
import tempfile
import threading
import time
import winsound
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import win32con
import win32gui

from domain.config_validation import validate_model_path
from infrastructure.clipboard_paste import paste_text
from infrastructure.config_repo import load_config, save_config
from infrastructure.recorder import record_to_wav_until_stopped
from infrastructure.whisper_cpp_engine import WhisperCppEngine
from presentation.hotkey import parse_hotkey, register_hotkey
from presentation.tray_app import create_tray_icon

HOTKEY_ID_RECORD = 1
HOTKEY_ID_STOP = 2
CONFIG_FILENAME = "config.yaml"
LOG_RETENTION_DAYS = 5

# Те же кандидаты, что в сканере (пункт 6)
_HOTKEY_FALLBACKS = [f"Ctrl+F{n}" for n in range(1, 13)]
_HOTKEY_FALLBACKS += [f"Ctrl+Shift+F{n}" for n in range(1, 13)]
_HOTKEY_FALLBACKS += [f"Ctrl+Alt+F{n}" for n in range(1, 13)]


def _probe_hotkey_in_process(wanted: str, hotkey_id: int = 1) -> str | None:
    """В этом же процессе найти комбинацию для wanted (или запасную). hotkey_id — для RegisterHotKey."""
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
        candidates = [wanted] + [c for c in _HOTKEY_FALLBACKS if c != wanted]
        for hotkey_str in candidates:
            mod, vk = parse_hotkey(hotkey_str)
            if register_hotkey(hwnd, hotkey_id, mod, vk):
                result.append(hotkey_str)
                win32gui.UnregisterHotKey(hwnd, hotkey_id)
                break
        win32gui.PostQuitMessage(0)
        win32gui.PumpMessages()

    t = threading.Thread(target=thread_fn)
    t.start()
    t.join(timeout=15.0)
    return result[0] if result else None


def setup_logging(log_dir: Path) -> logging.Logger:
    """Настроить логирование в файл с ротацией по дням и хранением 5 дней."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "roma-stt.log"
    handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=LOG_RETENTION_DAYS,
        encoding="utf-8",
    )
    handler.suffix = "%Y-%m-%d"
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger = logging.getLogger("roma_stt")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(handler)
    return logger


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
    log_dir = config_path.parent / "logs"
    logger = setup_logging(log_dir)
    logger.info("startup | config=%s", config_path)

    config = load_config(config_path)
    module = args.module or config.get("module", "cpu")
    config["module"] = module
    logger.info("config loaded | module=%s language=%s", module, config.get("language", "ru"))

    # Не запускать второй экземпляр — иначе горячие клавиши конфликтуют
    if win32gui.FindWindow("RomaSTT", None):
        logger.warning("second instance rejected (window already exists)")
        print("Roma-STT уже запущена в трее. Остановите её пунктом 4, затем запустите снова.")
        return

    # Две клавиши: запись и стоп (по умолчанию Ctrl+F2 и Ctrl+F3)
    hotkey_record = config.get("hotkey_record") or "Ctrl+F2"
    hotkey_stop = config.get("hotkey_stop") or "Ctrl+F3"
    probed_record = _probe_hotkey_in_process(hotkey_record, HOTKEY_ID_RECORD)
    probed_stop = _probe_hotkey_in_process(hotkey_stop, HOTKEY_ID_STOP)
    if probed_record:
        config["hotkey_record"] = probed_record
        if probed_record != hotkey_record:
            logger.info("hotkey_record fallback | wanted=%s used=%s", hotkey_record, probed_record)
    if probed_stop:
        config["hotkey_stop"] = probed_stop
        if probed_stop != hotkey_stop:
            logger.info("hotkey_stop fallback | wanted=%s used=%s", hotkey_stop, probed_stop)
    if not probed_record or not probed_stop:
        logger.info("hotkey probe missed one or both (will retry in worker thread)")
    single_hotkey_mode = [config.get("hotkey_record") == config.get("hotkey_stop")]

    try:
        engine = create_engine(module, config)
        logger.info("engine created | module=%s", module)
    except (ValueError, FileNotFoundError) as e:
        logger.exception("engine creation failed: %s", e)
        print(f"Config error: {e}. Run roma-stt.bat -> Install, then set paths in config.")
        return

    stop_event = threading.Event()
    record_thread: threading.Thread | None = None
    wav_path: str | None = None
    fallback_used: list = [False]  # recorder sets True if device was invalid and fell back to default
    pid_file = get_config_path().parent / ".roma-stt.pid"

    def remove_pid_file():
        pid_file.unlink(missing_ok=True)
        logger.info("pid file removed, exiting")

    icon = create_tray_icon(
        Path(__file__).parent / "tray_icon.svg",
        on_before_exit=remove_pid_file,
        hotkey_hint=f"Запись: {config.get('hotkey_record', 'Ctrl+F2')}, Стоп: {config.get('hotkey_stop', 'Ctrl+F3')}",
    )
    tray_ref: list = [icon]  # for notifications from hotkey thread

    def on_record() -> None:
        """Старт записи (только по клавише «запись»)."""
        nonlocal record_thread, wav_path
        if record_thread is not None and record_thread.is_alive():
            return  # уже идёт запись — игнорируем повторное нажатие
        # Start recording — один высокий длинный тон
        logger.info("recording started")
        try:
            winsound.Beep(880, 220)  # один тон — запись началась
        except Exception:
            pass
        stop_event.clear()
        fd, wav_path = tempfile.mkstemp(suffix=".wav")
        import os

        os.close(fd)
        fallback_used[0] = False
        input_device = config.get("input_device")
        if input_device is not None:
            try:
                input_device = int(input_device)
            except (TypeError, ValueError):
                input_device = None
        record_thread = threading.Thread(
            target=record_to_wav_until_stopped,
            args=(wav_path, stop_event),
            kwargs={"device": input_device, "fallback_used": fallback_used},
            daemon=True,
        )
        record_thread.start()
        logger.info("recording thread started | wav=%s device=%s", wav_path, input_device)

    def on_stop() -> None:
        """Стоп записи и распознавание (только по клавише «стоп»)."""
        nonlocal record_thread, wav_path
        if record_thread is None or not record_thread.is_alive():
            return  # запись не идёт — игнорируем
        # Stop recording — два низких «тук-тук»
        logger.info("recording stop requested")
        try:
            winsound.Beep(330, 100)
            time.sleep(0.12)
            winsound.Beep(330, 100)  # два чётких удара — запись остановлена
        except Exception:
            pass
        stop_event.set()
        record_thread.join(timeout=10)
        record_thread = None
        if fallback_used[0]:
            config["input_device"] = None
            try:
                save_config(config_path, config)
            except Exception as e:
                logger.exception("save_config after device fallback: %s", e)
            logger.warning("input device was invalid, used default; cleared input_device in config")
            if tray_ref and tray_ref[0]:
                try:
                    tray_ref[0].notify(
                        "Микрофон из конфига недоступен. Использован системный по умолчанию. Выберите устройство в пункте 10.",
                        "Roma-STT",
                    )
                except Exception:
                    pass
        if wav_path:
            try:
                lang = config.get("language", "ru")
                gpu_layers = 99 if module != "cpu" else 0
                logger.info("transcribe start | lang=%s gpu_layers=%s wav=%s", lang, gpu_layers, wav_path)
                text = engine.transcribe(wav_path, language=lang, n_gpu_layers=gpu_layers)
                length = len(text) if text else 0
                preview = (text[:80] + "…") if text and len(text) > 80 else (text or "")
                logger.info("transcribe done | length=%d preview=%r", length, preview)
                if not (text and text.strip()):
                    logger.warning("transcribe empty result")
                    if tray_ref and tray_ref[0]:
                        try:
                            tray_ref[0].notify(
                                "Ничего не распознано. Говорите чётко, подольше; проверьте микрофон.",
                                "Roma-STT",
                            )
                        except Exception:
                            pass
                else:
                    paste_text(text)
                    logger.info("paste done | length=%d", length)
                    if tray_ref and tray_ref[0]:
                        try:
                            tray_ref[0].notify("Текст вставлен.", "Roma-STT")
                        except Exception:
                            pass
            except (FileNotFoundError, subprocess.CalledProcessError) as e:
                logger.exception("transcribe failed: %s", e)
                if tray_ref and tray_ref[0]:
                    try:
                        tray_ref[0].notify(
                            "Ошибка распознавания (нет exe или сбой). Пункт 2 — проверка, пункт 1 — установка.",
                            "Roma-STT",
                        )
                    except Exception:
                        pass
            except Exception as e:
                logger.exception("unexpected error: %s", e)
                if tray_ref and tray_ref[0]:
                    try:
                        tray_ref[0].notify(f"Ошибка: {e}", "Roma-STT")
                    except Exception:
                        pass
            finally:
                Path(wav_path).unlink(missing_ok=True)
            wav_path = None

    def wnd_proc(hwnd, msg, wparam, lparam):
        if msg != win32con.WM_HOTKEY:
            return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
        if wparam == HOTKEY_ID_RECORD:
            if single_hotkey_mode[0]:
                if record_thread is not None and record_thread.is_alive():
                    on_stop()
                else:
                    on_record()
            else:
                on_record()
        elif wparam == HOTKEY_ID_STOP:
            on_stop()
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def run_hotkey_loop():
        wndclass = win32gui.WNDCLASS()
        wndclass.lpfnWndProc = wnd_proc
        wndclass.lpszClassName = "RomaSTT"
        wndclass.hInstance = win32gui.GetModuleHandle(None)
        win32gui.RegisterClass(wndclass)
        hwnd = win32gui.CreateWindow("RomaSTT", "Roma-STT", 0, 0, 0, 0, 0, 0, 0, wndclass.hInstance, None)
        record_str = config.get("hotkey_record") or "Ctrl+F2"
        stop_str = config.get("hotkey_stop") or "Ctrl+F3"
        fallbacks = (
            [f"Ctrl+F{n}" for n in range(1, 13)]
            + [f"Ctrl+Shift+F{n}" for n in range(1, 13)]
            + [f"Ctrl+Alt+F{n}" for n in range(1, 13)]
        )
        ok_record = False
        ok_stop = False
        if record_str != stop_str:
            mod_r, vk_r = parse_hotkey(record_str)
            ok_record = register_hotkey(hwnd, HOTKEY_ID_RECORD, mod_r, vk_r)
            if not ok_record:
                for c in fallbacks:
                    if c == stop_str:
                        continue
                    m, v = parse_hotkey(c)
                    if register_hotkey(hwnd, HOTKEY_ID_RECORD, m, v):
                        config["hotkey_record"] = c
                        ok_record = True
                        break
            mod_s, vk_s = parse_hotkey(stop_str)
            ok_stop = register_hotkey(hwnd, HOTKEY_ID_STOP, mod_s, vk_s)
            if not ok_stop:
                for c in fallbacks:
                    if c == record_str or c == config.get("hotkey_record"):
                        continue
                    m, v = parse_hotkey(c)
                    if register_hotkey(hwnd, HOTKEY_ID_STOP, m, v):
                        config["hotkey_stop"] = c
                        ok_stop = True
                        break
        else:
            # одна клавиша на оба (обратная совместимость) — регистрируем один раз, по ней переключаем запись/стоп
            mod, vk = parse_hotkey(record_str)
            ok_one = register_hotkey(hwnd, HOTKEY_ID_RECORD, mod, vk)
            if not ok_one:
                for c in fallbacks:
                    m, v = parse_hotkey(c)
                    if register_hotkey(hwnd, HOTKEY_ID_RECORD, m, v):
                        config["hotkey_record"] = config["hotkey_stop"] = c
                        ok_one = True
                        break
            ok_record = ok_stop = ok_one
        if not ok_record or not ok_stop:
            logger.error("hotkey registration failed, exiting")
            print("Не удалось зарегистрировать горячие клавиши. Выход.")
            os._exit(1)
        logger.info("hotkeys registered | record=%s stop=%s", config.get("hotkey_record"), config.get("hotkey_stop"))
        win32gui.PumpMessages()

    hotkey_thread = threading.Thread(target=run_hotkey_loop, daemon=True)
    hotkey_thread.start()

    # Файл с PID — пункт 4 батника убивает процесс по этому PID
    pid_file.write_text(str(os.getpid()), encoding="utf-8")
    logger.info("service running | pid=%s log_dir=%s", os.getpid(), log_dir)
    icon.run()


if __name__ == "__main__":
    main()
