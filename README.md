# Roma-STT

Локальное распознавание речи в текст (Speech-to-Text) для Windows: приложение в трее, глобальная горячая клавиша, движок [whisper.cpp](https://github.com/ggml-org/whisper.cpp) (CPU / CUDA / AMD). **Только для Windows.**

Мой друг Рома сломал правую руку, поэтому я написал это приложение — чтобы он мог набирать текст голосом: без лишних телодвижений, одним сочетанием клавиш (запись → стоп → текст вставляется в месте курсора).

**Подробная инструкция для пользователя:** см. [ИНСТРУКЦИЯ.md](ИНСТРУКЦИЯ.md).

## Необходимые программы

Нужны один раз (или при смене машины). **Обычно** их подтягивает сам установщик: в меню выберите **1** (Установка) — в процессе вызывается **winget** (если он есть в системе), ставятся **uv**, **Git**, **CMake** и при необходимости **Visual Studio Build Tools**; уже установленное не переустанавливается.

Если **winget недоступен** или установка инструментов из меню не сработала — поставьте компоненты **вручную** по таблице (или отдельно: **`roma-stt.bat install-tools`** — отдельное окно со скриптом `scripts/install_tools.bat`, при ошибках winget иногда нужен запуск **от имени администратора**).

| Программа | Назначение | Команда (winget) | Ссылка |
|-----------|------------|---------------------|--------|
| **uv** | Среда Python и зависимости | `winget install astral-sh.uv` | [astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/) |
| **Git** | Скачивание whisper.cpp | `winget install Git.Git` | [git-scm.com](https://git-scm.com/download/win) |
| **CMake** | Сборка whisper.cpp | `winget install Kitware.CMake` | [cmake.org](https://cmake.org/download/) |
| **VS Build Tools** | Компилятор C++ | `winget install Microsoft.VisualStudio.2022.BuildTools --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools"` | [visualstudio.microsoft.com](https://visualstudio.microsoft.com/visual-cpp-build-tools/) |

## Установка и запуск

1. Выберите в меню **1** (Установка). Скрипт при необходимости поставит системные инструменты через winget, создаст виртуальную среду, **скачает/соберёт whisper.cpp** под выбранную архитектуру (CPU/GPU) и подготовит модель.
2. Когда в шапке меню **«Готовность: OK»**, выберите **2** (запуск в трее).

### Варианты запуска

- **Окно управления (PySide6):** после `uv sync --extra gui` — `uv run python -m presentation.control_gui` или `uv run roma-stt-control`. Сверху — шапка и **«Служба в трее»**; **вкладки** — **установка** (включая полный отчёт `check_ready` и `install.py`), модель, хоткеи, язык, микрофон.
- **Интерактивный (меню):** запустите **`roma-stt.bat`** без аргументов. Первый раз: **1** (установка), затем **2** (запуск в трее). Остановка — **3**.
- **Командная строка:** **`roma-stt.bat <команда> [аргументы]`**:
  - `install-tools` — только системные программы (uv, Git, CMake, VS Build Tools через отдельный bat; полная установка проекта — это **`install`**).
  - `install [--arch cpu|cuda|amd]` — полная установка (venv, сборка whisper, модель).
  - `check` — проверка готовности.
  - `download <имя>` — скачать модель (например, `download small`).
  - `build-whisper [--arch cpu|cuda|amd]` — только пересборка whisper.cpp.
  - `start [cpu|cuda|amd]` — запуск приложения в трее.
  - `stop` — остановка приложения.

### Пункты меню (`roma-stt.bat` → PowerShell)

В **шапке** отображаются: состояние службы, режим, модель и строка **«Готовность: OK»** или **«не готово»** с краткой причиной (та же логика, что у `scripts/check_ready.py`). Отдельного пункта «Проверка готовности» нет; полный отчёт по-прежнему: `roma-stt.bat check` или `uv run python scripts/check_ready.py`.

- **1** — Установка: если нет `.venv` — полная установка; если уже есть — подменю: **1** переустановить/обновить, **2** удалить `.venv` и `models`.
- **2** — Запустить службу (трей).
- **3** — Остановить службу.
- **4** — Модели распознавания.
- **5** — Подбор свободной горячей клавиши (тест F-клавиш, запись в `config.yaml`).
- **6** / **7** — Горячая клавиша записи / стопа.
- **8** — Язык распознавания.
- **9** — Устройство ввода (микрофон).
- **10** — Выход.

Постобработка распознанного текста (заглавная буква, точка, очистка артефактов Whisper) **всегда включена**, отдельного пункта меню нет.

## Конфигурация (`config.yaml`)

- `whisper_vad` / `whisper_vad_model_path`: для `--vad` в whisper.cpp нужен **файл модели VAD** (`-vm`). Путь по умолчанию: `models/ggml-silero-v6.2.0.bin`. При установке (пункт 1) модель **качается автоматически** вместе с остальным; вручную: `roma-stt.bat download-vad`. Пока файла нет, распознавание идёт **без VAD** (без ошибки). Установка с `--no-download` пропускает и VAD.
- `module`: текущий режим работы (`cpu`, `cuda` или `amd`).
- `hotkey_record`: клавиша записи (по умолчанию `Ctrl+F2`).
- `hotkey_stop`: клавиша стопа (по умолчанию `Ctrl+F3`).
- `whisper_cpp_path_*`: пути к исполняемым файлам whisper.cpp.
- `whisper_model_path`: путь к мультиязычной модели.
- `language`: язык распознавания (ru, en и др.).
- `input_device`: индекс микрофона (пункт 9 — сканировать устройства); не задан — системный по умолчанию.
- `notifications`: всплывающие уведомления из трея при вставке текста; **по умолчанию `false`**. В меню пункта нет — только **`notifications: true`** в `config.yaml`.

## whisper.cpp и GPU

При установке (пункт **1**) или пересборке (`build-whisper`) выбирается архитектура (CPU / CUDA / AMD).

- **CUDA** (NVIDIA): нужен [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-downloads). В ходе установки при выборе **cuda** может быть предложена установка через winget (`Nvidia.CUDA`). Если cmake не находит `nvcc`, задайте `CUDAToolkit_ROOT` (например `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.x`).
- **AMD** (Vulkan): нужен [Vulkan SDK](https://vulkan.lunarg.com/). При выборе **amd** может быть предложена установка через winget (`KhronosGroup.VulkanSDK`).
- GPU-ускорение включается на уровне компиляции whisper.cpp (флаги `-DGGML_CUDA=ON` / `-DGGML_VULKAN=ON`). Если выбрана архитектура cuda или amd, движок также передаёт `-ngl 99` при распознавании; если бинарник не поддерживает этот флаг — автоматически повторяет запуск без него.

## Использование

1. Запустите службу (меню — пункт **2**). Иконка появится в трее (рядом с часами).
2. Нажмите клавишу записи (по умолчанию **Ctrl+F2**), говорите, затем клавишу стопа (**Ctrl+F3**):
   - Короткий **восходящий** сигнал — запись началась.
   - **Нисходящий** сигнал — запись остановлена, дальше распознавание и вставка в место курсора.

## Разработка и тесты

Версия интерпретатора для **`uv`** зафиксирована в [`.python-version`](.python-version) (**3.12**); в `pyproject.toml` по-прежнему `requires-python = ">=3.11"`.

```bash
uv run pytest tests/ -v
```

Юнит-тесты для CLI в `scripts/` — в [`tests/unit/scripts/`](tests/unit/scripts/). Общие фикстуры (`project_root`, `roma_tmp_layout`, `write_yaml_config`, …) и добавление `scripts/` в `sys.path` — в [`tests/conftest.py`](tests/conftest.py).

При push/PR в ветки `main` или `master` в GitHub Actions выполняется та же проверка (**Windows**, `uv sync --frozen` + `pytest`). Файл: [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
