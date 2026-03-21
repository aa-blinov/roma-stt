"""Главное окно Control UI: шапка + блок «Служба в трее», вкладки — настройки и диагностика."""

from __future__ import annotations

import html
import shutil
from datetime import datetime
from functools import partial
from pathlib import Path

from presentation.control_gui.hotkey_sort import sort_hotkey_labels

from PySide6.QtCore import QProcess, QProcessEnvironment, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QApplication,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


def load_config_module(root: Path) -> str:
    from infrastructure.config_repo import load_config

    return str(load_config(root / "config.yaml").get("module") or "cpu")


def _whisper_language_choices() -> list[tuple[str, str]]:
    """Коды для whisper.cpp `-l` (ISO 639-1). Порядок: частые варианты, затем по алфавиту кода."""
    return [
        ("ru", "Русский"),
        ("en", "English"),
        ("uk", "Українська"),
        ("be", "Беларуская"),
        ("de", "Deutsch"),
        ("fr", "Français"),
        ("es", "Español"),
        ("it", "Italiano"),
        ("pl", "Polski"),
        ("pt", "Português"),
        ("tr", "Türkçe"),
        ("zh", "中文"),
        ("ja", "日本語"),
        ("ko", "한국어"),
        ("ar", "العربية"),
        ("hi", "हिन्दी"),
        ("nl", "Nederlands"),
        ("sv", "Svenska"),
        ("cs", "Čeština"),
        ("ro", "Română"),
        ("bg", "Български"),
        ("el", "Ελληνικά"),
        ("he", "עברית"),
        ("id", "Indonesia"),
        ("th", "ไทย"),
        ("vi", "Tiếng Việt"),
        ("kk", "Қазақ"),
        ("az", "Azərbaycan"),
        ("hy", "Հայերեն"),
        ("ka", "ქართული"),
        ("fa", "فارسی"),
        ("hu", "Magyar"),
        ("fi", "Suomi"),
        ("da", "Dansk"),
        ("no", "Norsk"),
        ("sk", "Slovenčina"),
        ("sl", "Slovenščina"),
        ("hr", "Hrvatski"),
        ("sr", "Српски"),
        ("et", "Eesti"),
        ("lv", "Latviešu"),
        ("lt", "Lietuvių"),
        ("sw", "Kiswahili"),
        ("ta", "தமிழ்"),
        ("te", "తెలుగు"),
        ("bn", "বাংলা"),
        ("ur", "اردو"),
        ("ms", "Bahasa Melayu"),
    ]


# Список моделей: зелёный — файл есть, серый — ещё не скачан (читаемо в светлой и тёмной теме)
_MODEL_ROW_COLOR_DOWNLOADED = QColor(129, 199, 132)
_MODEL_ROW_COLOR_NOT_DOWNLOADED = QColor(176, 190, 197)
# Язык: зелёный — код в config, серый — остальные строки
_LANG_ROW_COLOR_IN_CONFIG = QColor(129, 199, 132)
_LANG_ROW_COLOR_OTHER = QColor(176, 190, 197)


class ServiceTaskThread(QThread):
    task_done = Signal(bool, str)

    def __init__(self, task: str, root: Path) -> None:
        super().__init__()
        self._task = task
        self._root = root

    def run(self) -> None:
        from application.control.service import start_tray_service, stop_tray_service

        if self._task == "start":
            ok, msg = start_tray_service(self._root)
        elif self._task == "stop":
            ok, msg = stop_tray_service(self._root)
        else:
            ok, msg = True, ""
        self.task_done.emit(ok, msg)


class ModelsUseThread(QThread):
    done = Signal(bool, str)
    download_progress = Signal(int, int)  # downloaded_bytes, total_bytes (0 = неизвестно)

    def __init__(self, root: Path, spec: str) -> None:
        super().__init__()
        self._root = root
        self._spec = spec

    def run(self) -> None:
        from application.control.models_facade import run_models_use

        def _cb(downloaded: int, total: int) -> None:
            self.download_progress.emit(downloaded, total)

        ok, msg = run_models_use(self._root, self._spec, on_download_progress=_cb)
        self.done.emit(ok, msg)


class ScanHotkeysThread(QThread):
    done = Signal(list, list)
    failed = Signal(str)

    def __init__(self, root: Path) -> None:
        super().__init__()
        self._root = root

    def run(self) -> None:
        try:
            from application.control.hotkey_facade import scan_free_hotkeys

            free, busy = scan_free_hotkeys(self._root)
            self.done.emit(free, busy)
        except Exception as e:
            self.failed.emit(str(e))


class ControlMainWindow(QMainWindow):
    """Окно управления. `_LOADING_TEXT` / `_REFRESH_UI_MS` — единый паттерн «Обновление…»."""

    _REFRESH_UI_MS = 80
    _LOADING_TEXT = "Обновление…"
    # Единый компактный стиль всех QPushButton в окне управления (шапка, вкладки).
    _CONTROL_PUSHBUTTON_QSS = """
QPushButton {
    border-radius: 4px;
    padding: 3px 10px;
    min-height: 22px;
}
QPushButton:enabled {
    color: #e8e8e8;
    background-color: #454545;
    border: 1px solid #666666;
}
QPushButton:enabled:hover {
    background-color: #505050;
    border: 1px solid #777777;
}
QPushButton:enabled:pressed {
    background-color: #3a3a3a;
}
QPushButton:disabled {
    color: #9e9e9e;
    background-color: #3d3d3d;
    border: 1px solid #555555;
}
"""

    def __init__(self, root: Path) -> None:
        super().__init__()
        self._root = root
        self.setWindowTitle("Roma-STT — управление")
        self.resize(720, 560)

        self._service_thread: ServiceTaskThread | None = None
        self._models_thread: ModelsUseThread | None = None
        self._scan_thread: ScanHotkeysThread | None = None
        self._install_process: QProcess | None = None
        self._hotkeys_tab_autoscan_done: bool = False
        self._install_job_line: str = "Последняя установка: ещё не запускали."
        self._last_install_arch: str = ""

        container = QWidget()
        outer = QVBoxLayout(container)
        self._header_line1 = QLabel()
        self._header_line1.setWordWrap(True)
        self._header_line2 = QLabel()
        self._header_line2.setWordWrap(True)
        header_frame = QFrame()
        header_frame.setObjectName("statusHeader")
        header_frame.setStyleSheet(
            "#statusHeader { border: 1px solid #888; border-radius: 6px; padding: 10px; "
            "background: palette(base); }"
        )
        hf_layout = QVBoxLayout(header_frame)
        hf_layout.addWidget(self._header_line1)
        hf_layout.addWidget(self._header_line2)
        outer.addWidget(header_frame)

        svc_group = QGroupBox("Служба в трее")
        svc_row = QHBoxLayout(svc_group)
        self._btn_start = QPushButton("Запустить")
        self._btn_start.setToolTip(
            "Запускает Roma-STT в системном трее (распознавание по горячим клавишам)."
        )
        self._btn_stop = QPushButton("Остановить")
        self._btn_stop.setToolTip("Останавливает программу в трее.")
        self._btn_refresh = QPushButton("Обновить сведения")
        self._btn_refresh.setToolTip(
            "Обновляет шапку, текст проверки на вкладке «Установка», "
            "статус последней установки и список доступных режимов для видеокарты."
        )
        svc_row.addWidget(self._btn_start)
        svc_row.addWidget(self._btn_stop)
        svc_row.addStretch()
        svc_row.addWidget(self._btn_refresh)
        outer.addWidget(svc_group)
        self._btn_refresh.clicked.connect(self._on_header_refresh_clicked)
        self._btn_start.clicked.connect(lambda: self._run_service_task("start"))
        self._btn_stop.clicked.connect(lambda: self._run_service_task("stop"))

        self._tabs = QTabWidget()
        outer.addWidget(self._tabs)
        self.setCentralWidget(container)

        self._tabs.addTab(self._build_tab_install(), "Установка")
        self._tabs.addTab(self._build_tab_models(), "Модель")
        self._tabs.addTab(self._build_tab_hotkeys(), "Горячие клавиши")
        self._tabs.addTab(self._build_tab_language(), "Язык")
        self._tabs.addTab(self._build_tab_audio(), "Микрофон")

        self.centralWidget().setStyleSheet(ControlMainWindow._CONTROL_PUSHBUTTON_QSS)

        self._tabs.currentChanged.connect(self._on_tab_changed)
        self._refresh_all()

    def _begin_sweep_refresh(self) -> None:
        """Шапка + поле проверки на «Установке» — перед полным _refresh_all."""
        self._header_line1.setTextFormat(Qt.TextFormat.PlainText)
        self._header_line1.setText(self._LOADING_TEXT)
        self._header_line2.setText("")
        self._install_readiness.setPlainText(self._LOADING_TEXT)
        QApplication.processEvents()

    def _finish_refresh_sweep(self, buttons: list[QPushButton]) -> None:
        try:
            self._refresh_all()
        finally:
            for b in buttons:
                b.setEnabled(True)

    def _on_header_refresh_clicked(self) -> None:
        self._btn_refresh.setEnabled(False)
        self._begin_sweep_refresh()
        QTimer.singleShot(self._REFRESH_UI_MS, partial(self._finish_refresh_sweep, [self._btn_refresh]))

    def _add_loading_list_placeholder(self, list_widget: QListWidget) -> None:
        list_widget.clear()
        item = QListWidgetItem(self._LOADING_TEXT)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        list_widget.addItem(item)

    def _on_tab_changed(self, index: int) -> None:
        if self._tabs.tabText(index) == "Установка":
            self._refresh_install_status_panel()
        if self._tabs.tabText(index) == "Модель":
            self._refresh_models_tab()
        if self._tabs.tabText(index) == "Язык":
            self._refresh_language_tab()
        if self._tabs.tabText(index) == "Горячие клавиши":
            self._maybe_autoscan_hotkeys()

    def _refresh_all(self) -> None:
        self._refresh_header()
        self._refresh_install_status_panel()
        self._populate_install_arch_combo()

    def _refresh_header(self) -> None:
        from application.control.header_state import get_header_state

        h = get_header_state(self._root)
        self._header_line1.setTextFormat(Qt.TextFormat.RichText)
        pid = h.get("pid")
        pid_s = html.escape(str(pid)) if pid is not None else "?"
        if h["running"]:
            svc_part = (
                f'<span style="color:#81c784;font-weight:600">запущена</span>, PID {pid_s}'
            )
        else:
            svc_part = '<span style="color:#9E9E9E">остановлена</span>'
        mod = html.escape(str(h["module"]))
        model_d = html.escape(str(h["model_display"]))
        hk_r = html.escape(str(h["hotkey_record"]))
        hk_s = html.escape(str(h["hotkey_stop"]))
        lang = html.escape(str(h["lang"]))
        self._header_line1.setText(
            f"Служба: {svc_part}  |  Режим: {mod}  |  Модель: {model_d}  |  "
            f"Запись: {hk_r}  |  Стоп: {hk_s}  |  Язык: {lang}"
        )
        if h["ready_ok"]:
            self._header_line2.setText("Готовность: OK")
        else:
            self._header_line2.setText(f"Готовность: не готово — {h['ready_detail']}")
        self._apply_service_buttons_state(h)

    def _apply_service_buttons_state(self, h: dict | None = None) -> None:
        """Запустить/Остановить — по фактическому running; не вызывать во время busy."""
        from application.control.header_state import get_header_state

        if h is None:
            h = get_header_state(self._root)
        running = h["running"]
        self._btn_start.setEnabled(not running)
        self._btn_stop.setEnabled(running)

    def _set_service_busy(self, busy: bool) -> None:
        self._btn_refresh.setEnabled(not busy)
        if busy:
            self._btn_start.setEnabled(False)
            self._btn_stop.setEnabled(False)
        else:
            self._apply_service_buttons_state()

    def _run_service_task(self, task: str) -> None:
        self._set_service_busy(True)
        self._service_thread = ServiceTaskThread(task, self._root)
        self._service_thread.task_done.connect(self._on_service_done)
        self._service_thread.finished.connect(self._service_thread.deleteLater)
        self._service_thread.start()

    def _on_service_done(self, ok: bool, msg: str) -> None:
        self._set_service_busy(False)
        self._service_thread = None
        self._refresh_all()
        # Успех (запущена/остановлена) — только шапка с PID и статусом, без всплывашки
        if msg and not ok:
            QMessageBox.warning(self, "Ошибка", msg)

    def _populate_install_arch_combo(self) -> None:
        """Только доступные архитектуры: cuda — при NVIDIA, amd — при AMD/Radeon."""
        from application.control.gpu_detect import available_whisper_archs, detect_gpu
        from infrastructure.config_repo import load_config

        prev = self._install_arch.currentText() if self._install_arch.count() else ""
        gpu = detect_gpu()
        archs = available_whisper_archs(gpu)
        self._install_arch.clear()
        self._install_arch.addItems(archs)
        cfg_mod = (load_config(self._root / "config.yaml").get("module") or "cpu").strip()
        if cfg_mod in archs:
            self._install_arch.setCurrentText(cfg_mod)
        elif prev in archs:
            self._install_arch.setCurrentText(prev)
        else:
            self._install_arch.setCurrentIndex(0)

        parts: list[str] = []
        if gpu["has_nvidia"]:
            parts.append(f"NVIDIA — {gpu['nvidia_name']}")
        if gpu["has_amd"]:
            parts.append(f"AMD — {gpu['amd_name']}")
        if not parts:
            self._install_gpu_label.setText(
                "Видеокарта NVIDIA или AMD не обнаружена — в списке только CPU (как в меню установки)."
            )
        else:
            self._install_gpu_label.setText("Обнаружено: " + " · ".join(parts))

    def _refresh_install_status_panel(self) -> None:
        """Блок «статус установки»: check_ready + строка про последний запуск install.py."""
        from application.control.readiness import get_readiness_lines

        lines = get_readiness_lines(self._root)
        try:
            from application.control.readiness import load_check_ready_module

            mod = load_check_ready_module(self._root)
            nvcc_ok, nvcc_msg = mod.check_nvcc()
            tag = "OK" if nvcc_ok else "WARN"
            lines.append(f"  [{tag}] {nvcc_msg}")
            lines.append(f"  [--] module (config): {load_config_module(self._root)}")
        except Exception:
            pass
        lines.append(
            f"  [--] Дата проверки: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        )
        self._install_readiness.setPlainText("\n".join(lines))
        self._install_job_status.setText(self._install_job_line)

    # --- Установка ---
    def _build_tab_install(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        _install_intro = QLabel(
            "Сверху — подробная проверка: всё ли установлено для работы. "
            "Обновить этот текст и шапку — кнопка «Обновить сведения» в блоке «Служба в трее» выше. "
            "Ниже — режим сборки, кнопка установки и журнал. Краткий итог — в шапке окна."
        )
        _install_intro.setWordWrap(True)
        layout.addWidget(_install_intro)
        self._install_gpu_label = QLabel()
        self._install_gpu_label.setWordWrap(True)
        layout.addWidget(self._install_gpu_label)

        st_group = QGroupBox("Проверка готовности и статус установки")
        st_layout = QVBoxLayout(st_group)
        self._install_job_status = QLabel()
        self._install_job_status.setWordWrap(True)
        st_layout.addWidget(self._install_job_status)
        self._install_readiness = QPlainTextEdit()
        self._install_readiness.setReadOnly(True)
        self._install_readiness.setMinimumHeight(160)
        st_layout.addWidget(self._install_readiness)
        layout.addWidget(st_group)

        row = QHBoxLayout()
        row.addWidget(QLabel("Режим сборки:"))
        self._install_arch = QComboBox()
        row.addWidget(self._install_arch)
        self._btn_install_run = QPushButton("Запустить установку")
        self._btn_install_tools = QPushButton("Окно установки инструментов (winget)…")
        self._btn_uninstall = QPushButton("Удалить .venv и models")
        row.addWidget(self._btn_install_run)
        row.addWidget(self._btn_install_tools)
        row.addWidget(self._btn_uninstall)
        layout.addLayout(row)
        self._install_log = QPlainTextEdit()
        self._install_log.setReadOnly(True)
        self._install_log.setPlaceholderText("Сообщения установки появятся здесь во время работы…")
        layout.addWidget(QLabel("Журнал установки:"))
        layout.addWidget(self._install_log)
        self._btn_install_run.clicked.connect(self._start_install_process)
        self._btn_install_tools.clicked.connect(self._start_install_tools_bat)
        self._btn_uninstall.clicked.connect(self._confirm_uninstall)
        return w

    def _start_install_process(self) -> None:
        if self._install_process and self._install_process.state() != QProcess.NotRunning:
            QMessageBox.warning(self, "Занято", "Установка уже выполняется.")
            return
        uv = shutil.which("uv")
        if not uv:
            QMessageBox.critical(
                self,
                "uv не найден",
                "Установите uv и добавьте в PATH, либо используйте кнопку установки инструментов.",
            )
            return
        arch = self._install_arch.currentText()
        self._last_install_arch = arch
        self._install_job_line = f"Установка выполняется… (архитектура {arch})"
        self._refresh_install_status_panel()
        self._install_log.appendPlainText(f"$ uv run python scripts/install.py --arch {arch}\n")
        proc = QProcess(self)
        self._install_process = proc
        proc.setWorkingDirectory(str(self._root))
        env = QProcessEnvironment.systemEnvironment()
        proc.setProcessEnvironment(env)
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.setProgram(uv)
        proc.setArguments(["run", "python", "scripts/install.py", "--arch", arch])
        proc.readyReadStandardOutput.connect(lambda: self._append_install_log(proc))
        proc.readyReadStandardError.connect(lambda: self._append_install_log(proc))
        proc.finished.connect(self._on_install_finished)
        self._btn_install_run.setEnabled(False)
        proc.start()

    def _append_install_log(self, proc: QProcess) -> None:
        data = proc.readAllStandardOutput().data().decode("utf-8", errors="replace")
        if data:
            self._install_log.appendPlainText(data)

    def _on_install_finished(self, *_args: object) -> None:
        proc = self._install_process
        if proc:
            data = proc.readAllStandardOutput().data().decode("utf-8", errors="replace")
            if data:
                self._install_log.appendPlainText(data)
        self._btn_install_run.setEnabled(True)
        code = proc.exitCode() if proc else -1
        self._install_log.appendPlainText(f"\n--- код выхода: {code} ---\n")
        arch = self._last_install_arch or "?"
        if code == 0:
            self._install_job_line = f"Последняя установка: успешно (код 0), архитектура {arch}."
        else:
            self._install_job_line = (
                f"Последняя установка: ошибка (код {code}), архитектура {arch}. См. журнал ниже."
            )
        self._refresh_install_status_panel()
        QMessageBox.information(
            self,
            "Установка",
            "Готово." if code == 0 else f"Завершено с кодом {code}. См. лог выше.",
        )
        self._refresh_all()

    def _start_install_tools_bat(self) -> None:
        bat = self._root / "scripts" / "install_tools.bat"
        if not bat.is_file():
            QMessageBox.warning(self, "Нет файла", str(bat))
            return
        # Отдельное консольное окно — как раньше
        p = QProcess(self)
        p.setProgram("cmd.exe")
        p.setArguments(["/c", "start", "", str(bat)])
        p.start()

    def _confirm_uninstall(self) -> None:
        r = QMessageBox.question(
            self,
            "Удаление",
            "Удалить папки .venv и models? Сначала остановите службу кнопкой «Остановить» выше.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if r != QMessageBox.Yes:
            return
        from application.control.install_actions import remove_venv_and_models

        ok, msg = remove_venv_and_models(self._root)
        self._install_job_line = "После удаления: выполните установку заново."
        QMessageBox.information(self, "Удаление", msg)
        self._refresh_all()

    # --- Модель ---
    def _build_tab_models(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        _models_hint = QLabel(
            "Модели Whisper: строки <b>зелёным</b> — файл уже в <code>models</code>, "
            "<b>серым</b> — ещё не скачан. Для каждой строки указан примерный "
            "<b>размер скачиваемого файла</b> (ggerganov/whisper.cpp на Hugging Face). "
            "В конце строки в скобках статус; перед скобками — краткое сравнение. "
            "Список перечитывается при каждом открытии этой вкладки. "
            "При скачивании показывается полоса прогресса ниже."
        )
        _models_hint.setWordWrap(True)
        _models_hint.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(_models_hint)
        self._models_list = QListWidget()
        layout.addWidget(self._models_list)
        self._models_progress = QProgressBar()
        self._models_progress.setVisible(False)
        self._models_progress.setTextVisible(True)
        self._models_progress.setMinimumHeight(22)
        layout.addWidget(self._models_progress)
        models_row = QHBoxLayout()
        self._btn_models_apply = QPushButton("Выбрать / скачать и выбрать")
        self._btn_models_delete = QPushButton("Удалить модель")
        self._btn_models_delete.setToolTip(
            "Удаляет файл скачанной модели из папки models. "
            "Если она была выбрана в config — путь whisper_model_path сбрасывается. "
            "Если служба в трее использует эту модель — сначала остановите её."
        )
        models_row.addWidget(self._btn_models_apply, 1)
        models_row.addWidget(self._btn_models_delete, 1)
        layout.addLayout(models_row)
        self._btn_models_apply.clicked.connect(self._apply_model)
        self._btn_models_delete.clicked.connect(self._delete_model)
        self._refresh_models_tab()
        return w

    def _model_stem_for_match(self) -> str:
        from application.control.menu_state import get_menu_state

        stem = (get_menu_state(self._root / "config.yaml").get("model_stem") or "").strip()
        if stem.lower().startswith("ggml-"):
            stem = stem[5:]
        return stem

    def _select_current_model_in_list(self) -> None:
        target = self._model_stem_for_match()
        if not target:
            return
        for i in range(self._models_list.count()):
            it = self._models_list.item(i)
            if it is None:
                continue
            name = it.data(Qt.ItemDataRole.UserRole)
            if name and str(name) == target:
                self._models_list.setCurrentItem(it)
                self._models_list.scrollToItem(it)
                return

    def _refresh_models_tab(self) -> None:
        self._models_list.clear()
        try:
            from application.control.models_facade import list_model_rows

            rows = list_model_rows(self._root)
        except Exception as e:
            self._models_list.addItem(f"Ошибка списка моделей: {e}")
            return
        for r in rows:
            status = "скачано" if r["downloaded"] else "не скачано"
            text = (
                f"{r['index']}. {r['name']} — {r['description']}. "
                f"~{r['size_label']} на диске (HF). {r['compare_hint']} ({status})"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, r["name"])
            item.setForeground(
                QBrush(
                    _MODEL_ROW_COLOR_DOWNLOADED
                    if r["downloaded"]
                    else _MODEL_ROW_COLOR_NOT_DOWNLOADED
                )
            )
            item.setToolTip(
                f"{r['name']}\n"
                f"Размер ggml-*.bin на Hugging Face: ~{r['size_label']}\n"
                f"{r['description']}\n\n"
                f"Сравнение: {r['compare_hint']}\n\n"
                f"{'Файл модели уже в папке models.' if r['downloaded'] else 'Файла ещё нет — при выборе будет скачан.'}"
            )
            self._models_list.addItem(item)
        self._select_current_model_in_list()

    def _apply_model(self) -> None:
        item = self._models_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Модель", "Выберите строку в списке.")
            return
        spec = item.data(Qt.ItemDataRole.UserRole)
        if not spec:
            QMessageBox.warning(self, "Модель", "Некорректная строка (переключите вкладку и откройте «Модель» снова).")
            return
        spec = str(spec).strip()
        if not spec:
            QMessageBox.warning(self, "Модель", "Пустой выбор.")
            return
        self._btn_models_apply.setEnabled(False)
        self._btn_models_delete.setEnabled(False)
        self._models_progress.setVisible(False)
        self._models_progress.setRange(0, 100)
        self._models_progress.setValue(0)
        self._models_thread = ModelsUseThread(self._root, spec)
        self._models_thread.download_progress.connect(self._on_models_download_progress)
        self._models_thread.done.connect(self._on_models_done)
        self._models_thread.finished.connect(self._models_thread.deleteLater)
        self._models_thread.start()

    def _on_models_download_progress(self, downloaded: int, total: int) -> None:
        self._models_progress.setVisible(True)
        if total > 0:
            self._models_progress.setRange(0, total)
            self._models_progress.setValue(downloaded)
            pct = int(100 * downloaded / total)
            dm = downloaded // (1024 * 1024)
            tm = total // (1024 * 1024)
            self._models_progress.setFormat(f"{dm} / {tm} MiB ({pct}%)")
        else:
            self._models_progress.setRange(0, 0)
            self._models_progress.setFormat("Загрузка…")

    def _on_models_done(self, ok: bool, msg: str) -> None:
        self._btn_models_apply.setEnabled(True)
        self._btn_models_delete.setEnabled(True)
        self._models_progress.setVisible(False)
        self._models_thread = None
        self._refresh_models_tab()
        self._refresh_all()
        text = msg if msg else ("OK" if ok else "Ошибка")
        if ok:
            QMessageBox.information(self, "Модель", text)
        else:
            QMessageBox.warning(self, "Модель", text)

    def _delete_model(self) -> None:
        item = self._models_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Модель", "Выберите строку в списке.")
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        if not name:
            QMessageBox.warning(self, "Модель", "Некорректная строка (переключите вкладку и откройте «Модель» снова).")
            return
        name = str(name).strip()
        if not name:
            QMessageBox.warning(self, "Модель", "Пустой выбор.")
            return
        from application.control.models_facade import list_model_rows, run_delete_model

        rows = list_model_rows(self._root)
        row = next((r for r in rows if r["name"] == name), None)
        if not row or not row["downloaded"]:
            QMessageBox.warning(self, "Удаление модели", "Эта модель не скачана — удалять нечего.")
            return
        r = QMessageBox.question(
            self,
            "Удаление модели",
            f"Удалить файл модели «{name}» с диска?\n\n"
            "Если служба в трее запущена и использует эту модель — сначала остановите её.\n"
            "Если модель была активной в config, путь в config будет сброшен.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if r != QMessageBox.Yes:
            return
        ok, msg = run_delete_model(self._root, name)
        self._refresh_models_tab()
        self._refresh_all()
        if ok:
            QMessageBox.information(self, "Удаление модели", msg)
        else:
            QMessageBox.warning(self, "Удаление модели", msg)

    # --- Хоткеи ---
    def _maybe_autoscan_hotkeys(self) -> None:
        """Один раз за сеанс: при первом открытии вкладки — автосканирование."""
        if self._hotkeys_tab_autoscan_done:
            return
        self._hotkeys_tab_autoscan_done = True
        self._scan_hotkeys()

    def _build_tab_hotkeys(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        box = QGroupBox("Запись и стоп")
        fl = QFormLayout(box)
        self._hk_record = QComboBox()
        self._hk_stop = QComboBox()
        for c in (self._hk_record, self._hk_stop):
            c.setEditable(True)
            c.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        fl.addRow("Запись:", self._hk_record)
        fl.addRow("Стоп:", self._hk_stop)
        layout.addWidget(box)
        self._btn_hk_save = QPushButton("Сохранить")
        self._btn_hk_save.setToolTip("Записать выбранные комбинации в config.yaml (перезапустите службу в трее).")
        self._btn_hk_save.clicked.connect(self._save_hotkeys)
        layout.addWidget(self._btn_hk_save)
        self._hk_scan_status = QLabel("")
        self._hk_scan_status.setVisible(False)
        self._hk_scan_status.setWordWrap(True)
        layout.addWidget(self._hk_scan_status)
        self._load_hotkeys_into_fields()
        return w

    def _load_hotkeys_into_fields(self) -> None:
        from infrastructure.config_repo import load_config

        cfg = load_config(self._root / "config.yaml")
        rec = str(cfg.get("hotkey_record", "Ctrl+F2"))
        stp = str(cfg.get("hotkey_stop", "Ctrl+F3"))
        for combo, val in ((self._hk_record, rec), (self._hk_stop, stp)):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(val)
            combo.setCurrentText(val)
            combo.blockSignals(False)

    def _fill_hotkey_combos_from_scan(self, free: list[str]) -> None:
        """Подставить отсканированные строки в выпадающие списки, сохранив текущий выбор если возможно."""
        rec = self._hk_record.currentText().strip()
        stp = self._hk_stop.currentText().strip()
        bag: set[str] = set()
        for x in free:
            if x:
                bag.add(x)
        for x in (rec, stp):
            if x:
                bag.add(x)
        items = sort_hotkey_labels(list(bag))

        def refill(combo: QComboBox, preferred: str) -> None:
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(items if items else [preferred])
            idx = combo.findText(preferred, Qt.MatchFlag.MatchExactly)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                combo.setCurrentText(preferred)
            combo.blockSignals(False)

        refill(self._hk_record, rec)
        refill(self._hk_stop, stp)

    def _save_hotkeys(self) -> None:
        from application.control.config_edits import set_hotkeys

        ok, msg = set_hotkeys(self._root, self._hk_record.currentText().strip(), self._hk_stop.currentText().strip())
        if ok:
            QMessageBox.information(self, "Горячие клавиши", msg)
            self._refresh_all()
        else:
            QMessageBox.warning(self, "Горячие клавиши", msg)

    def _scan_hotkeys(self) -> None:
        self._btn_hk_save.setEnabled(False)
        self._hk_scan_status.setText(self._LOADING_TEXT)
        self._hk_scan_status.setVisible(True)
        self._scan_thread = ScanHotkeysThread(self._root)
        self._scan_thread.done.connect(self._on_scan_done)
        self._scan_thread.failed.connect(self._on_scan_failed)
        self._scan_thread.finished.connect(self._scan_thread.deleteLater)
        self._scan_thread.start()

    def _on_scan_done(self, free: list, busy: list) -> None:
        self._hk_scan_status.setVisible(False)
        self._btn_hk_save.setEnabled(True)
        self._scan_thread = None
        if not free:
            detail = "\n".join(f"{hk}: {reason}" for hk, reason in busy[:8])
            QMessageBox.warning(
                self,
                "Горячие клавиши",
                "Не найдено свободных комбинаций из списка кандидатов.\n\n" + detail
                if detail
                else "Не найдено свободных комбинаций.",
            )
            return
        self._fill_hotkey_combos_from_scan(free)

    def _on_scan_failed(self, err: str) -> None:
        self._hk_scan_status.setVisible(False)
        self._btn_hk_save.setEnabled(True)
        self._scan_thread = None
        QMessageBox.warning(self, "Сканирование хоткеев", err)

    # --- Язык ---
    def _build_tab_language(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        _lang_hint = QLabel(
            "Код языка для whisper.cpp (<code>-l</code>): выберите строку и нажмите «Сохранить». "
            "Текущий язык в config подсвечен <b>зелёным</b>. Если в config указан код не из списка — "
            "он показывается отдельной строкой сверху."
        )
        _lang_hint.setWordWrap(True)
        _lang_hint.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(_lang_hint)
        self._lang_list = QListWidget()
        layout.addWidget(self._lang_list)
        self._btn_lang = QPushButton("Сохранить")
        self._btn_lang.clicked.connect(self._save_language)
        layout.addWidget(self._btn_lang)
        self._refresh_language_tab()
        return w

    def _refresh_language_tab(self) -> None:
        from infrastructure.config_repo import load_config

        cfg = load_config(self._root / "config.yaml")
        current = str(cfg.get("language", "ru")).strip()
        if not current:
            current = "ru"
        self._lang_list.clear()
        choices = _whisper_language_choices()
        known_codes = {c for c, _ in choices}
        if current not in known_codes:
            item = QListWidgetItem(f"{current} — (в config, нет в списке ниже)")
            item.setData(Qt.ItemDataRole.UserRole, current)
            item.setToolTip(
                "Этот код взят из config.yaml. Выберите другой язык из списка и сохраните, "
                "чтобы заменить."
            )
            self._lang_list.addItem(item)
        for code, title in choices:
            item = QListWidgetItem(f"{code} — {title}")
            item.setData(Qt.ItemDataRole.UserRole, code)
            item.setToolTip(f"Код для whisper.cpp (-l): {code}")
            self._lang_list.addItem(item)
        self._apply_language_list_colors(current)
        self._select_language_in_list(current)

    def _apply_language_list_colors(self, current_code: str) -> None:
        cur = (current_code or "").strip() or "ru"
        for i in range(self._lang_list.count()):
            it = self._lang_list.item(i)
            if it is None:
                continue
            d = it.data(Qt.ItemDataRole.UserRole)
            row_code = str(d).strip() if d is not None else ""
            if row_code == cur:
                it.setForeground(QBrush(_LANG_ROW_COLOR_IN_CONFIG))
            else:
                it.setForeground(QBrush(_LANG_ROW_COLOR_OTHER))

    def _select_language_in_list(self, code: str) -> None:
        c = (code or "").strip() or "ru"
        for i in range(self._lang_list.count()):
            it = self._lang_list.item(i)
            if it is None:
                continue
            d = it.data(Qt.ItemDataRole.UserRole)
            if d is not None and str(d).strip() == c:
                self._lang_list.setCurrentItem(it)
                self._lang_list.scrollToItem(it)
                return
        if self._lang_list.count() > 0:
            self._lang_list.setCurrentRow(0)

    def _save_language(self) -> None:
        from application.control.config_edits import set_language

        item = self._lang_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Язык", "Выберите строку в списке.")
            return
        code = item.data(Qt.ItemDataRole.UserRole)
        if code is None:
            QMessageBox.warning(self, "Язык", "Некорректная строка.")
            return
        code = str(code).strip()
        if not code:
            QMessageBox.warning(self, "Язык", "Пустой код языка.")
            return
        ok, msg = set_language(self._root, code)
        if ok:
            self._refresh_all()
            self._refresh_language_tab()
        else:
            QMessageBox.warning(self, "Язык", msg)

    # --- Микрофон ---
    def _build_tab_audio(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Устройства ввода (индекс PortAudio = номер в списке):"))
        self._audio_list = QListWidget()
        layout.addWidget(self._audio_list)
        row = QHBoxLayout()
        self._btn_audio_set = QPushButton("Выбрать выделенное")
        self._btn_audio_default = QPushButton("Системный по умолчанию")
        self._btn_audio_refresh = QPushButton("Обновить список")
        row.addWidget(self._btn_audio_set)
        row.addWidget(self._btn_audio_default)
        row.addWidget(self._btn_audio_refresh)
        layout.addLayout(row)
        self._btn_audio_refresh.clicked.connect(self._on_audio_refresh_clicked)
        self._btn_audio_set.clicked.connect(self._set_audio_device)
        self._btn_audio_default.clicked.connect(self._reset_audio_device)
        self._refresh_audio_tab()
        return w

    def _on_audio_refresh_clicked(self) -> None:
        self._btn_audio_refresh.setEnabled(False)
        self._add_loading_list_placeholder(self._audio_list)
        QApplication.processEvents()
        QTimer.singleShot(self._REFRESH_UI_MS, partial(self._finish_audio_list_refresh))

    def _finish_audio_list_refresh(self) -> None:
        try:
            self._refresh_audio_tab()
        finally:
            self._btn_audio_refresh.setEnabled(True)

    def _refresh_audio_tab(self) -> None:
        self._audio_list.clear()
        try:
            from application.control.audio_facade import list_input_devices

            devices = list_input_devices(self._root)
        except Exception as e:
            self._audio_list.addItem(f"Ошибка: {e}")
            return
        for d in devices:
            self._audio_list.addItem(f"{d['index']}. {d['name']} ({d['channels']} ch)")

    def _set_audio_device(self) -> None:
        item = self._audio_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Микрофон", "Выберите строку в списке.")
            return
        text = item.text()
        try:
            idx = int(text.split(".", 1)[0].strip())
        except ValueError:
            return
        from application.control.audio_facade import set_input_device_index

        ok, msg = set_input_device_index(self._root, idx)
        QMessageBox.information(self, "Микрофон", msg)

    def _reset_audio_device(self) -> None:
        from application.control.audio_facade import reset_input_device_default

        ok, msg = reset_input_device_default(self._root)
        QMessageBox.information(self, "Микрофон", msg)
