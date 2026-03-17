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
echo Доступные команды: install-tools, install, check, download ^<имя^>, build-whisper, build-check, setup, test-model, start [cpu^|cuda^|amd], stop, toggle-notifications
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
echo   --- Первый запуск: 0, 1, 2, затем 3 ^(Запуск^) ---
echo.
echo   0. Установить нужные программы
echo      Один раз: uv, Git, CMake, Visual Studio Build Tools. Нужно для пункта 1.
echo      Запустите батник от имени администратора. Если всё уже стоит — переходите к 1.
echo.
echo   1. Установка
echo      Один раз: среда, модель, сборка whisper. Сначала пункт 0, если ещё не ставили программы.
echo.
echo   2. Проверка готовности
echo      Убедиться, что всё установлено. Запускайте после пункта 1.
echo.
echo   3. Запустить службу (в трее)
echo      При запуске: 1=cpu, 2=cuda, 3=amd. Горячая клавиша из config.yaml.
echo.
echo   4. Остановить службу
echo      Завершить работу Roma-STT в трее.
echo.
echo   5. Модели распознавания
echo      Список моделей, ввод номера/названия — выбрать или скачать и выбрать.
echo.
echo   6. Подбор свободной горячей клавиши
echo      Протестировать F-клавиши и записать выбранные в config.yaml.
echo.
echo   7. Горячая клавиша записи
echo      Ввести строку для записи (например Ctrl+F2).
echo.
echo   8. Горячая клавиша стопа
echo      Ввести строку для стопа (например Ctrl+F3).
echo.
echo   9. Выбрать язык (ru/en/...)
echo.
echo  10. Устройство ввода ^(микрофон^)
echo      Сканировать микрофоны Windows и выбрать номер для записи.
echo.
echo  11. Удалить установку
echo      Удалить .venv и models (полная очистка, потом снова пункт 1).
echo.
echo  12. Уведомления Windows
echo      Включить или выключить всплывающие уведомления (по умолчанию выключены).
echo.
echo  13. Выход
echo.
set /p choice="Введите цифру (0-13, Enter — обновить меню): "
if "!choice!"=="" goto menu
if "%choice%"=="0" goto install_tools
if "%choice%"=="1" goto install
if "%choice%"=="2" goto check
if "%choice%"=="3" goto start
if "%choice%"=="4" goto stop
if "%choice%"=="5" goto models
if "%choice%"=="6" goto scan_hotkeys
if "%choice%"=="7" goto set_hotkey_record
if "%choice%"=="8" goto set_hotkey_stop
if "%choice%"=="9" goto set_language
if "%choice%"=="10" goto set_input_device
if "%choice%"=="11" goto remove
if "%choice%"=="12" goto toggle_notifications
if "%choice%"=="13" exit /b 0
echo Неизвестный выбор. Введите цифру от 0 до 13.
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
set /p arch="Архитектура (1/2/3, Enter — в главное меню): "
if "!arch!"=="" goto menu
set a=cpu
if "!arch!"=="2" set a=cuda
if "!arch!"=="3" set a=amd
echo.
echo Запуск установки (среда, зависимости, сборка whisper [%a%], модель)...
uv run python scripts\install.py --arch %a%
echo.
echo Готово. Дальше: пункт 2 (Проверка), затем пункт 3 (Запуск).
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

:toggle_notifications
echo [12] Уведомления Windows...
if not exist .venv (
    echo Сначала выполните 1 ^(Установка^).
    pause
    goto menu
)
for /f "usebackq tokens=*" %%a in (`uv run python -c "from infrastructure.config_repo import load_config; from pathlib import Path; p=Path('config.yaml'); cfg=load_config(p); print('включены' if cfg.get('notifications', False) else 'выключены')"`) do set "notif_cur=%%a"
echo Сейчас уведомления: !notif_cur!
uv run python -c "from infrastructure.config_repo import load_config, save_config; from pathlib import Path; p=Path('config.yaml'); cfg=load_config(p); cfg['notifications']=not cfg.get('notifications', False); save_config(p,cfg); print('Уведомления теперь:', 'включены' if cfg['notifications'] else 'выключены')"
pause
goto menu

:remove
echo [11] Удаление установки
if not exist .venv (
    echo Удалять нечего — установка ещё не выполнялась. Сначала сделайте 1 ^(Установка^).
    pause
    goto menu
)
echo Имеет смысл только если хотите всё удалить и поставить заново. После удаления снова выполните 1.
set /p confirm="Удалить .venv и models? (y/N, Enter — в главное меню): "
if "!confirm!"=="" goto menu
if /i not "!confirm!"=="y" goto menu
if exist .venv rmdir /s /q .venv
if exist models rmdir /s /q models
echo Удалено. Для новой установки снова выберите пункт 1.
pause
goto menu

:models
echo.
echo [5] Модели распознавания
if not exist .venv (
    echo Сначала выполните 1 ^(Установка^) — тогда появится среда и модель по умолчанию.
    pause
    goto menu
)
uv run python scripts\models.py list-all
set /p num="Номер (1-8) или название (Enter — в главное меню): "
if "!num!"=="" goto menu
uv run python scripts\models.py use "!num!"
pause
goto menu

:scan_hotkeys
echo [6] Подбор свободной горячей клавиши...
echo Тестируются сочетания Ctrl/Shift/Alt с F-клавишами (F1–F24).
echo Можно выбрать найденный вариант, и он будет записан в config.yaml.
uv run python scripts\scan_hotkeys.py
pause
goto menu

:set_hotkey_record
echo [7] Горячая клавиша записи...
echo Примеры: Ctrl+F2, Ctrl+Shift+F12. Enter = Ctrl+F2.
set /p newrec="Введите строку (Enter = Ctrl+F2): "
if "!newrec!"=="" set "newrec=Ctrl+F2"
echo Записываем в config.yaml: hotkey_record: !newrec!
uv run python -c "from infrastructure.config_repo import load_config, save_config; from pathlib import Path; import sys; p=Path('config.yaml'); cfg=load_config(p); cfg['hotkey_record']=sys.argv[1]; save_config(p,cfg)" "!newrec!"
echo Готово.
pause
goto menu

:set_hotkey_stop
echo [8] Горячая клавиша стопа...
echo Примеры: Ctrl+F3, Ctrl+Shift+F12. Enter = Ctrl+F3.
set /p newstop="Введите строку (Enter = Ctrl+F3): "
if "!newstop!"=="" set "newstop=Ctrl+F3"
echo Записываем в config.yaml: hotkey_stop: !newstop!
uv run python -c "from infrastructure.config_repo import load_config, save_config; from pathlib import Path; import sys; p=Path('config.yaml'); cfg=load_config(p); cfg['hotkey_stop']=sys.argv[1]; save_config(p,cfg)" "!newstop!"
echo Готово.
pause
goto menu

:set_language
echo [9] Выбрать язык...
echo Текущий язык: 
uv run python -c "from infrastructure.config_repo import load_config; from pathlib import Path; p=Path('config.yaml'); cfg=load_config(p); print(cfg.get('language', 'ru'))"
echo.
echo Примеры: ru, en, de, fr, es, it, jp, zh.
set /p newlang="Введите код языка (Enter — в главное меню): "
if "!newlang!"=="" goto menu
echo.
echo Записываем в config.yaml: language: "%newlang%"
uv run python -c "from infrastructure.config_repo import load_config, save_config; from pathlib import Path; import sys; p=Path('config.yaml'); cfg=load_config(p); cfg['language']=sys.argv[1]; save_config(p,cfg)" "%newlang%"
echo Готово.
pause
goto menu

:set_input_device
echo [10] Устройство ввода (микрофон)...
if not exist .venv (
    echo Сначала выполните 1 ^(Установка^).
    pause
    goto menu
)
uv run python scripts\list_audio_devices.py
set /p devnum="Номер устройства (Enter — в главное меню): "
if "!devnum!"=="" goto menu
uv run python scripts\list_audio_devices.py --set !devnum!
pause
goto menu

:start
echo [3] Запуск службы...
if not exist .venv (
    echo Сначала выполните 1 ^(Установка^), затем 2 ^(Проверка^). Когда в пункте 2 всё будет OK — снова выберите 3.
    pause
    goto menu
)
echo   1 = cpu  2 = cuda  3 = amd
set /p mod="Режим (1/2/3, Enter — в главное меню): "
if "!mod!"=="" goto menu
if "!mod!"=="1" set mod=cpu
if "!mod!"=="2" set mod=cuda
if "!mod!"=="3" set mod=amd
if not exist "bin\main-!mod!.exe" (
    echo Бинарник bin\main-!mod!.exe не найден. Запускается сборка whisper.cpp [!mod!]...
    echo Это займёт несколько минут. Не закрывайте окно.
    uv run python scripts\build_whisper_cpp.py --arch !mod!
    if errorlevel 1 (
        echo.
        echo Сборка завершилась с ошибкой. Проверьте зависимости ^(пункт 0^) и повторите.
        pause
        goto menu
    )
    echo Сборка завершена.
    echo.
)
set "cfgfile=config.yaml"
uv run python -c "from infrastructure.config_repo import load_config, save_config; from pathlib import Path; import sys; p=Path('!cfgfile!'); cfg=load_config(p); cfg['module']=sys.argv[1]; save_config(p,cfg)" "!mod!"
uv run python scripts\check_ready.py >nul 2>&1
if errorlevel 1 (
    echo Проверка готовности не прошла. Сделайте по порядку: 1 ^(Установка^), потом 2 ^(Проверка^). Когда в пункте 2 будет «Ready» — снова выберите 3.
    pause
    goto menu
)
for /f "usebackq tokens=*" %%a in (`uv run python -c "from infrastructure.config_repo import load_config; from pathlib import Path; p=Path('config.yaml'); cfg=load_config(p); print(cfg.get('hotkey_record', 'Ctrl+F2'))"`) do set "hk_r=%%a"
for /f "usebackq tokens=*" %%b in (`uv run python -c "from infrastructure.config_repo import load_config; from pathlib import Path; p=Path('config.yaml'); cfg=load_config(p); print(cfg.get('hotkey_stop', 'Ctrl+F3'))"`) do set "hk_s=%%b"
echo Служба запускается в трее. Запись: !hk_r!, Стоп: !hk_s!
echo Остановить: пункт 4 или закройте это окно.
start /B "Roma-STT" uv run python main.py --module !mod!
pause
goto menu

:stop
echo [4] Остановка Roma-STT...
if exist .roma-stt.pid (
    for /f "usebackq delims=" %%i in (".roma-stt.pid") do taskkill /PID %%i /F >nul 2>nul
    del .roma-stt.pid 2>nul
) else (
    for /f "delims=" %%i in ('uv run python scripts\find_roma_stt_pids.py 2^>nul') do taskkill /PID %%i /F >nul 2>nul
    taskkill /FI "WINDOWTITLE eq Roma-STT*" /F >nul 2>nul
)
echo Готово.
echo Если служба не была запущена — ничего страшного. Чтобы начать: сначала 1 ^(Установка^), потом 2 ^(Проверка^), потом 3 ^(Запуск^).
pause
goto menu
