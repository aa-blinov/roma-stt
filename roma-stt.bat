@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

if not "%~1"=="" goto run_cmd
goto menu

:run_cmd
set "cmd=%~1"
echo Режим команд: %cmd%
echo.
if /i "%cmd%"=="install" goto do_install
if /i "%cmd%"=="check" goto do_check
if /i "%cmd%"=="download" goto do_download
if /i "%cmd%"=="build-check" goto do_build_check
if /i "%cmd%"=="setup" goto do_setup
if /i "%cmd%"=="test-model" goto do_test_model
if /i "%cmd%"=="build-whisper" goto do_build_whisper
if /i "%cmd%"=="install-tools" goto do_install_tools
if /i "%cmd%"=="start" goto do_start
if /i "%cmd%"=="stop" goto do_stop
echo Неизвестная команда: %cmd%
echo Доступные команды: install-tools, install, check, download ^<имя^>, build-whisper, build-check, setup, test-model, start [cpu^|cuda^|amd], stop
exit /b 1

:do_install
uv --version >nul 2>&1
if errorlevel 1 (
    echo uv not found. Install: winget install astral-sh.uv
    exit /b 1
)
uv run python scripts\install.py %2 %3 %4 %5
exit /b %errorlevel%

:do_check
uv run python scripts\check_ready.py
exit /b %errorlevel%

:do_download
if "%~2"=="" (
    echo Usage: roma-stt.bat download ^<name^>   e.g. download base
    exit /b 1
)
uv run python scripts\download_model.py %2
exit /b %errorlevel%

:do_build_check
uv run python scripts\check_build.py
exit /b %errorlevel%

:do_setup
call :do_install
if errorlevel 1 exit /b 1
call :do_check
exit /b %errorlevel%

:do_test_model
uv run python scripts\test_model.py
exit /b %errorlevel%

:do_build_whisper
set "arch_param="
if not "%~2"=="" (
    if /i "%~2"=="cpu" set arch_param=--arch cpu
    if /i "%~2"=="cuda" set arch_param=--arch cuda
    if /i "%~2"=="amd" set arch_param=--arch amd
)
uv run python scripts\build_whisper_cpp.py %arch_param%
exit /b %errorlevel%

:do_start
set "mod=%~2"
if "!mod!"=="" set mod=cpu
uv run python main.py --module !mod!
exit /b %errorlevel%

:do_stop
if exist .roma-stt.pid (
    for /f "usebackq delims=" %%i in (".roma-stt.pid") do taskkill /PID %%i /F >nul 2>nul
    del .roma-stt.pid 2>nul
) else (
    for /f "delims=" %%i in ('uv run python scripts\find_roma_stt_pids.py 2^>nul') do taskkill /PID %%i /F >nul 2>nul
    taskkill /FI "WINDOWTITLE eq Roma-STT*" /F >nul 2>nul
)
echo Stopped.
exit /b 0

:do_install_tools
call scripts\install_tools.bat
exit /b %errorlevel%

:menu
echo.
echo  ============================================================
echo   Roma-STT  -  Speech to Text (голос в текст)
echo  ============================================================
echo.
echo   Это меню. Введите цифру и нажмите Enter.
echo   Для пункта 0 ^(установка программ^) запустите батник от имени администратора:
echo   правый щелчок по roma-stt.bat - "Запуск от имени администратора".
echo.
echo   --- Первый запуск: 0, затем 1, 2, 5 ---
echo.
echo   0. Установить нужные программы
echo      Один раз: uv, Git, CMake, Visual Studio Build Tools. Нужно для пункта 1.
echo      Запустите батник от имени администратора. Если всё уже стоит — переходите к 1.
echo.
echo   1. Установка
echo      Один раз: ставит всё нужное, скачивает модель, собирает программу распознавания.
echo      Сначала выполните пункт 0, если ещё не ставили программы.
echo.
echo   2. Проверка готовности
echo      Проверить, что всё установлено и готово к работе. Запускайте после пункта 1.
echo.
echo   3. Удалить установку
echo      Удалить .venv и папку models (полная очистка, потом снова пункт 1).
echo.
echo   4. Модели распознавания
echo      Список моделей, скачать другую, выбрать активную (подменю 1–4).
echo.
echo   5. Запустить программу (в трее)
echo      При запуске: 1=cpu, 2=cuda, 3=amd. Горячая клавиша из config.yaml.
echo.
echo   6. Остановить программу
echo      Завершить работу Roma-STT в трее.
echo.
echo   7. Подбор свободной горячей клавиши
echo      Протестировать варианты с F-клавишами и записать выбранный в config.yaml.
echo.
echo   8. Указать горячую клавишу вручную
echo      Ввести строку (например Ctrl+F12) и записать в config.yaml.
echo.
echo   9. Выбрать язык (ru/en/...)
echo.
echo  10. Выход
echo.
set /p choice="Введите цифру (0-10): "

if "%choice%"=="0" goto install_tools
if "%choice%"=="1" goto install
if "%choice%"=="2" goto check
if "%choice%"=="3" goto remove
if "%choice%"=="4" goto models
if "%choice%"=="5" goto start
if "%choice%"=="6" goto stop
if "%choice%"=="7" goto scan_hotkeys
if "%choice%"=="8" goto set_hotkey_manual
if "%choice%"=="9" goto set_language
if "%choice%"=="10" exit /b 0
echo Неизвестный выбор. Введите цифру от 0 до 10.
goto menu

:install_tools
echo [0] Установка нужных программ (uv, Git, CMake, VS Build Tools)...
echo Если установка не начинается — запустите батник от имени администратора.
call scripts\install_tools.bat
pause
goto menu

:install
echo [1] Установка...
echo Проверка uv...
uv --version >nul 2>&1
if errorlevel 1 (
    echo uv не найден. Установите один раз: winget install astral-sh.uv
    echo Или: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 ^| iex"
    pause
    goto menu
)
echo   1 = cpu  2 = cuda  3 = amd
set /p arch="Архитектура (1/2/3 или Enter для cpu): "
set a=cpu
if "%arch%"=="2" set a=cuda
if "%arch%"=="3" set a=amd
echo.
echo Запуск установки (среда, зависимости, сборка whisper [%a%], модель)...
uv run python scripts\install.py --arch %a%
echo.
echo Готово. Дальше: пункт 2 (Проверка), затем пункт 5 (Запуск).
pause
goto menu

:check
echo [2] Проверка готовности...
if not exist .venv (
    echo.
    echo   Сначала нужна установка. Выберите пункт 1 ^(Установка^), дождитесь окончания, потом снова пункт 2.
    echo.
)
uv run python scripts\check_ready.py
pause
goto menu

:remove
echo [3] Удаление установки
if not exist .venv (
    echo Удалять нечего — установка ещё не выполнялась. Сначала сделайте 1 ^(Установка^).
    pause
    goto menu
)
echo Имеет смысл только если хотите всё удалить и поставить заново. После удаления снова выполните 1.
set /p confirm="Удалить .venv и models? (y/N): "
if /i not "!confirm!"=="y" goto menu
if exist .venv rmdir /s /q .venv
if exist models rmdir /s /q models
echo Удалено. Для новой установки снова выберите пункт 1.
pause
goto menu

:models
echo.
echo [4] Модели распознавания
if not exist .venv (
    echo Сначала выполните 1 ^(Установка^) — тогда появится среда и модель по умолчанию. После этого здесь можно скачать другие модели.
    pause
    goto menu
)
echo   1 = список доступных моделей ^(с номерами для скачивания^)
echo   2 = список уже скачанных
echo   3 = выбрать активную модель
echo   4 = скачать модель ^(номер из списка 1 или название: base, small...^)
set /p m="Введите цифру (1-4): "
if "!m!"=="1" ( uv run python scripts\models.py list-available )
if "!m!"=="2" ( uv run python scripts\models.py list-downloaded )
if "!m!"=="3" (
    set /p name="Имя файла модели: "
    uv run python scripts\models.py set "!name!"
)
if "!m!"=="4" (
    echo Введите номер модели из списка 1 ^(1-8^) или название ^(например base^):
    set /p name="Номер или название: "
    uv run python scripts\download_model.py "!name!"
)
if not "!m!"=="1" if not "!m!"=="2" if not "!m!"=="3" if not "!m!"=="4" (
    echo Неизвестный ввод. Введите цифру от 1 до 4.
)
pause
goto menu

:scan_hotkeys
echo [7] Подбор свободной горячей клавиши...
echo Тестируются сочетания Ctrl/Shift/Alt с F-клавишами (F1–F24).
echo Можно выбрать найденный вариант, и он будет записан в config.yaml.
uv run python scripts\scan_hotkeys.py
pause
goto menu

:set_hotkey_manual
echo [8] Указать горячую клавишу вручную...
echo Примеры: Ctrl+F9, Ctrl+Shift+F12, Ctrl+Alt+F10.
set /p newhk="Введите строку для hotkey (или Enter, чтобы отменить): "
if "%newhk%"=="" goto menu
echo.
echo Записываем в config.yaml: hotkey: "%newhk%"
uv run python -c "from infrastructure.config_repo import load_config, save_config; from pathlib import Path; import sys; p=Path('config.yaml'); cfg=load_config(p); cfg['hotkey']=sys.argv[1]; save_config(p,cfg)" "%newhk%"
echo Готово. Теперь можно запустить пункт 5 (Запуск программы).
pause
goto menu

:set_language
echo [9] Выбрать язык...
echo Текущий язык: 
uv run python -c "from infrastructure.config_repo import load_config; from pathlib import Path; p=Path('config.yaml'); cfg=load_config(p); print(cfg.get('language', 'ru'))"
echo.
echo Примеры: ru, en, de, fr, es, it, jp, zh.
set /p newlang="Введите код языка (или Enter, чтобы оставить как есть): "
if "%newlang%"=="" goto menu
echo.
echo Записываем в config.yaml: language: "%newlang%"
uv run python -c "from infrastructure.config_repo import load_config, save_config; from pathlib import Path; import sys; p=Path('config.yaml'); cfg=load_config(p); cfg['language']=sys.argv[1]; save_config(p,cfg)" "%newlang%"
echo Готово.
pause
goto menu

:start
echo [5] Запуск программы...
if not exist .venv (
    echo Сначала выполните 1 ^(Установка^), затем 2 ^(Проверка^). Когда в пункте 2 всё будет OK — снова выберите 5.
    pause
    goto menu
)
uv run python scripts\check_ready.py >nul 2>&1
if errorlevel 1 (
    echo Проверка готовности не прошла. Сделайте по порядку: 1 ^(Установка^), потом 2 ^(Проверка^). Когда в пункте 2 будет «Ready» — снова выберите 5.
    pause
    goto menu
)
for /f "usebackq tokens=*" %%i in (`uv run python -c "from infrastructure.config_repo import load_config; from pathlib import Path; p=Path('config.yaml'); cfg=load_config(p); print(cfg.get('module', 'cpu'))"`) do set "current_mod=%%i"
echo   1 = cpu  2 = cuda  3 = amd
set /p mod="Режим (1/2/3 или Enter для !current_mod!): "
if "!mod!"=="" set mod=!current_mod!
if "!mod!"=="1" set mod=cpu
if "!mod!"=="2" set mod=cuda
if "!mod!"=="3" set mod=amd
set "cfgfile=config.yaml"
uv run python -c "from infrastructure.config_repo import load_config, save_config; from pathlib import Path; import sys; p=Path('!cfgfile!'); cfg=load_config(p); cfg['module']=sys.argv[1]; save_config(p,cfg)" "!mod!"
echo Программа запускается в трее. Горячая клавиша — из config.yaml (запись — стоп — вставка текста).
echo Остановить: пункт 6 или закройте это окно.
start /B "Roma-STT" uv run python main.py --module !mod!
pause
goto menu

:stop
echo [6] Остановка Roma-STT...
if exist .roma-stt.pid (
    for /f "usebackq delims=" %%i in (".roma-stt.pid") do taskkill /PID %%i /F >nul 2>nul
    del .roma-stt.pid 2>nul
) else (
    for /f "delims=" %%i in ('uv run python scripts\find_roma_stt_pids.py 2^>nul') do taskkill /PID %%i /F >nul 2>nul
    taskkill /FI "WINDOWTITLE eq Roma-STT*" /F >nul 2>nul
)
echo Готово.
echo Если программа не была запущена — ничего страшного. Чтобы начать: сначала 1 ^(Установка^), потом 2 ^(Проверка^), потом 5 ^(Запуск^).
pause
goto menu
