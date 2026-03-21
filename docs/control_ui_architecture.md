# Архитектура Control UI (PySide6) для Roma-STT

## Цель

Отдельное окно управления заменяет интерактивное меню `roma-stt.ps1`, **без дублирования логики** в QML/скриптах и **без** «обёртки вокруг батника» как основного API.

## Принципы

1. **Один источник правды — Python** в репозитории: установка, проверка готовности, старт/стоп процесса, конфиг, модели, микрофон. Скрипты `scripts/*.py` и будущий GUI вызывают **одни и те же функции** из слоя `application/control`.
2. **PS1/bat — тонкие оболочки** (как сейчас для CLI): могут вызывать `uv run python -m application.control` или `scripts/*.py`, но **не наоборот** — GUI не запускает `roma-stt.ps1` как главный движок.
3. **GUI не блокирует поток Qt**: длительные операции (`install`, `winget`, сборка whisper) — `QThread` + сигналы или `QProcess` с чтением stdout/stderr в лог-виджет.
4. **Трей (`main.py`)** — отдельный процесс пользователя; Control UI — **отдельный процесс** (настройки, установка). Оба читают `config.yaml` и при необходимости согласуются через **файл и PID** (как сейчас), без обязательного IPC-сокета на первом этапе.

## Слои

| Слой | Что здесь |
|------|-----------|
| `application/control/` | Фасады: `get_menu_state()`, `start_tray_service()`, `stop_tray_service()`, `run_install_wizard()`, обёртки над `scripts/install.py` и т.д. |
| `infrastructure/` | Уже есть: `config_repo`, пути, при необходимости — обёртка над `subprocess` для `winget` (или вызов готового `.bat` **одной** командой из фасада). |
| `presentation/control_gui/` | Только Qt: окна, вкладки, список логов, прогресс. Импортирует **только** `application.control` и Qt. |
| `scripts/*.py` | CLI: `argparse` → вызов функции из `application/control` (после рефакторинга). |

## Соответствие пунктам меню PS1

| Пункт | Логика в Python | Примечание |
|-------|-----------------|------------|
| 1 Установка / переустановка / удаление | `install.py` + `Install-Tools` (winget) | Порты winget лучше вынести в один модуль `application/control/system_tools.py` или вызывать `scripts/install_tools.bat` через `powershell` с логированием — **один** путь, не копировать 200 строк в Qt. |
| 2 Запуск службы | Тот же `Start-Process pythonw main.py` → в фасаде `start_tray_service(root, module)` | Проверка `check_ready` до старта — внутри фасада. |
| 3 Остановка | Логика из `Do-Stop` → `stop_tray_service(root)` | Объединить PID-файл + `find_roma_stt_pids.py` в одном Python-модуле. |
| 4 Модели | `scripts/models.py` | Вызов из фасада `subprocess` или импорт функций после лёгкого рефакторинга `models.py`. |
| 5 Подбор хоткеев | `scripts/scan_hotkeys.py` | Интерактивный консольный скрипт: в GUI — отдельное окно с `QProcess` или перенос ввода в виджеты (второй этап). |
| 6–7 Хоткеи записи/стопа | `config_repo` | Прямое чтение/запись + валидация строки. |
| 8 Язык | `config_repo` | Аналогично. |
| 9 Микрофон | `scripts/list_audio_devices.py` | Фасад вызывает существующий скрипт или функции из него. |

## Чего избегать

- **Не** делать главный цикл приложения в виде `QProcess("roma-stt.ps1")` — это хрупко и не даёт нормального прогресса.
- **Не** дублировать `Get-Config` через `python -c` из GUI — только `load_config` / `save_config`.
- **Не** смешивать в одном виджете установку и запуск трея без отмены/лога — пользователь должен видеть вывод длинных команд.

## Зависимости

- `PySide6` — в **optional-dependencies** в `pyproject.toml` (`gui = ["PySide6"]`).
- Установка GUI: `uv sync --extra gui`
- Запуск окна: `uv run python -m presentation.control_gui.main` или `uv run roma-stt-control`

## Этапы внедрения

1. **Фасады + вынос `get_menu_state()`** в `application/control` (скрипт `print_menu_state.py` остаётся тонкой обёрткой).
2. **Остановка/старт** в `application/control/service.py` (копия логики из PS1).
3. **Окно PySide6** (`presentation/control_gui/`): шапка + **«Служба в трее»**; вкладка **Установка** объединяет отчёт `check_ready` и запуск `install.py`; далее **Модель**, **Горячие клавиши**, **Язык**, **Микрофон**.
4. (Опционально) Упростить `roma-stt.ps1` до вызова тех же фасадов.

## Итог

Так UI получается **не костылем**: Qt — только отображение и потоки; вся бизнес-логика в `application/control` и существующих `scripts` после тонкого рефакторинга.
