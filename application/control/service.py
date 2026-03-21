"""Старт/стоп процесса трея (main.py), как пункты 2–3 в roma-stt.ps1."""

from __future__ import annotations

import ctypes
import subprocess
import time
from pathlib import Path

from application.control.process_scan import is_pid_roma_stt_service, scan_roma_stt_pids
from infrastructure.config_repo import load_config, save_config

PID_FILENAME = ".roma-stt.pid"
# main.py пишет PID только после создания движка и потока хоткеев — на слабом ПК это может занять >6 с.
PID_FILE_WAIT_SEC = 20.0


def pid_file_path(root: Path) -> Path:
    return root / PID_FILENAME


def _tray_window_exists() -> bool:
    """То же, что проверка второго экземпляра в main.py: окно класса RomaSTT (hidden для хоткеев)."""
    try:
        return bool(ctypes.windll.user32.FindWindowW("RomaSTT", None))
    except (OSError, AttributeError, ValueError):
        return False


def is_tray_running(root: Path) -> bool:
    """Служба считается запущенной, если есть pid-файл, процесс в списке или окно трея (как в main.py)."""
    if get_running_pid(root) is not None:
        return True
    if scan_roma_stt_pids(root):
        return True
    return _tray_window_exists()


def get_running_pid(root: Path) -> int | None:
    """PID из .roma-stt.pid, если процесс жив и это наш main.py."""
    path = pid_file_path(root)
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip().splitlines()
        if not raw:
            return None
        pid = int(raw[0].strip())
    except (ValueError, OSError):
        return None
    if not _process_exists(pid):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return None
    if is_pid_roma_stt_service(pid, root):
        return pid
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
    return None


def _process_exists(pid: int) -> bool:
    try:
        r = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        return str(pid) in (r.stdout or "")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _stop_one_pid(pid: int, timeout_ms: float = 4500.0) -> bool:
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/F"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    deadline = time.monotonic() + timeout_ms / 1000.0
    while time.monotonic() < deadline:
        if not _process_exists(pid):
            return True
        time.sleep(0.16)
    return not _process_exists(pid)


def stop_tray_service(root: Path) -> tuple[bool, str]:
    """Остановить все подходящие процессы Roma-STT; удалить pid-файл."""
    to_stop: set[int] = set()
    path = pid_file_path(root)
    if path.is_file():
        try:
            raw = path.read_text(encoding="utf-8").strip().splitlines()
            if raw:
                candidate = int(raw[0].strip())
                if is_pid_roma_stt_service(candidate, root):
                    to_stop.add(candidate)
        except (ValueError, OSError):
            pass
    for scan_pid in scan_roma_stt_pids(root):
        to_stop.add(scan_pid)

    if not to_stop:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return True, "Запущенный Roma-STT не найден — останавливать нечего."

    any_stopped = False
    for proc_id in to_stop:
        if _stop_one_pid(proc_id):
            any_stopped = True

    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass

    if any_stopped:
        return True, "Служба остановлена."
    return False, "Процесс не завершился за отведённое время. Повторите или снимите задачу вручную."


def _resolve_module_and_hint_exe(root: Path, config: dict) -> tuple[str, bool]:
    """Вернуть module и True если bin для этого модуля есть (как в Do-Start)."""
    mod = (config.get("module") or "cpu").strip() or "cpu"
    candidates: list[str] = [f"bin/main-{mod}.exe"]
    if mod == "cpu":
        candidates.append("bin/main.exe")
    for c in candidates:
        if (root / c).is_file():
            return mod, True
    for try_name in ("bin/main-cuda.exe", "bin/main-amd.exe", "bin/main-cpu.exe", "bin/main.exe"):
        p = root / try_name
        if p.is_file():
            if "cuda" in try_name:
                return "cuda", True
            if "amd" in try_name:
                return "amd", True
            return "cpu", True
    return mod, False


def start_tray_service(root: Path) -> tuple[bool, str]:
    """Запустить pythonw main.py --module (после check_ready)."""
    venv_pythonw = root / ".venv" / "Scripts" / "pythonw.exe"
    if not venv_pythonw.is_file():
        return False, "Нет .venv — сначала выполните установку (п. 1 в меню)."

    if is_tray_running(root):
        return (
            False,
            "Служба уже запущена или ещё стартует (окно/процесс найден). "
            "Дождитесь появления в шапке или нажмите «Остановить».",
        )

    config_path = root / "config.yaml"
    config = load_config(config_path)
    mod, has_exe = _resolve_module_and_hint_exe(root, config)
    if not has_exe:
        return False, "Ни один whisper-бинарник не найден в bin/. Выполните установку."

    if mod != (config.get("module") or "cpu"):
        config["module"] = mod
        save_config(config_path, config)

    # Проверка готовности
    from application.control.readiness import load_check_ready_module

    try:
        chk = load_check_ready_module(root)
        all_ok, _ = chk.run_checks()
    except Exception as e:
        return False, f"Проверка готовности не удалась: {e}"
    if not all_ok:
        return (
            False,
            "Проверка готовности не прошла. Выполните установку / настройте config и модели.",
        )

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        subprocess.Popen(
            [str(venv_pythonw), "main.py", "--module", mod],
            cwd=str(root),
            creationflags=creationflags,
        )
    except OSError as e:
        return False, f"Не удалось запустить: {e}"

    # Ждём появления pid-файла (см. main.py — запись после старта движка и хоткеев)
    waited = 0.0
    step = 0.25
    while waited < PID_FILE_WAIT_SEC:
        if pid_file_path(root).is_file():
            return True, "Служба запущена."
        time.sleep(step)
        waited += step
    return (
        False,
        "Служба не успела полностью запуститься за "
        f"{int(PID_FILE_WAIT_SEC)} с. Откройте logs/roma-stt.log — там будет причина "
        "(ошибка, долгая загрузка CUDA/модели или не хватило времени; попробуйте «Запустить» снова).",
    )


def get_service_status(root: Path) -> dict:
    """Сводка для UI: pid, module из конфига, пути."""
    pid = get_running_pid(root)
    scanned = scan_roma_stt_pids(root)
    if pid is None and scanned:
        pid = scanned[0]
    window = _tray_window_exists()
    running = pid is not None or bool(scanned) or window
    cfg = load_config(root / "config.yaml")
    return {
        "running": running,
        "pid": pid,
        "module": cfg.get("module", "cpu"),
        "hotkey_record": cfg.get("hotkey_record", "Ctrl+F2"),
        "hotkey_stop": cfg.get("hotkey_stop", "Ctrl+F3"),
    }
