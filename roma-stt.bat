@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

rem ANSI colors (ESC char embedded directly — works without for/f trick)
set "C0=[0m"
set "CY=[96m"
set "CG=[92m"
set "CR=[91m"
set "CW=[93m"
set "CD=[90m"

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
echo !CR!Неизвестная команда: %cmd%!C0!
echo Доступные команды: install-tools, install, check, download ^<имя^>, build-whisper, build-check, setup, test-model, start [cpu^|cuda^|amd], stop
exit /b 1

:do_install
uv --version >nul 2>&1
if errorlevel 1 (
    echo !CR!uv not found. Install: winget install astral-sh.uv!C0!
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
echo !CD! ============================================================!C0!
echo  !CY!Roma-STT!C0!  -  Speech to Text ^(голос в текст^)
echo !CD! ============================================================!C0!
echo.
echo   Введите цифру и нажмите Enter.
echo   !CW!Первый запуск: 1 → 2 → 3!C0!
echo.
echo   !CW! 1.!C0! Установка
echo      Один раз: uv, Git, CMake, VS Build Tools, среда, модель, whisper.cpp.
echo.
echo   !CW! 2.!C0! Проверка готовности
echo      Убедиться, что всё установлено. После пункта 1.
echo.
echo   !CW! 3.!C0! Запустить службу ^(в трее^)
echo      Выбор режима: cpu / cuda (NVIDIA) / amd (AMD). Горячая клавиша из config.yaml.
echo.
echo   !CW! 4.!C0! Остановить службу
echo      Завершить работу Roma-STT в трее.
echo.
echo !CD! --- Настройки -----------------------------------------------!C0!
echo.
echo   !CW! 5.!C0! Модели распознавания
echo      Список моделей — выбрать или скачать и выбрать.
echo.
echo   !CW! 6.!C0! Подбор свободной горячей клавиши
echo      Протестировать F-клавиши и записать в config.yaml.
echo.
echo   !CW! 7.!C0! Горячая клавиша записи
echo   !CW! 8.!C0! Горячая клавиша стопа
echo   !CW! 9.!C0! Выбрать язык ^(ru/en/...^)
echo   !CW!10.!C0! Устройство ввода ^(микрофон^)
echo   !CW!11.!C0! Удалить установку
echo   !CW!12.!C0! Уведомления Windows       ^(всплывающие, по умолчанию выключены^)
echo   !CW!13.!C0! Постобработка текста       ^(заглавная, точка, артефакты, по умолчанию включена^)
echo.
echo   !CW!14.!C0! Выход
echo.
set /p choice="Введите цифру (1-14, Enter — обновить меню): "
if "!choice!"=="" goto menu
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
if "%choice%"=="13" goto toggle_postprocess
if "%choice%"=="14" exit /b 0
echo !CR!Неизвестный выбор. Введите цифру от 1 до 14.!C0!
goto menu

:install
echo !CY![1]!C0! Установка...
uv --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo !CR!uv не найден.!C0! Установите командой:
    echo     winget install astral-sh.uv
    echo Затем закройте это окно, откройте заново и снова выберите 1.
    pause
    goto menu
)
call :detect_gpu
set "arch="
if "!gpu_nvidia!"=="0" if "!gpu_amd!"=="0" (
    echo   !CD!Дискретная видеокарта не обнаружена — будет установлен CPU-режим.!C0!
    set arch=1
) else (
    echo   !CW!1!C0! = cpu  ^(без GPU, всегда работает^)
    if "!gpu_nvidia!"=="1" echo   !CW!2!C0! = cuda ^(!gpu_nvidia_name!^)
    if "!gpu_amd!"=="1"    echo   !CW!3!C0! = amd  ^(!gpu_amd_name!^)
    set "arch_hint=1"
    if "!gpu_nvidia!"=="1" set "arch_hint=!arch_hint!/2"
    if "!gpu_amd!"=="1"    set "arch_hint=!arch_hint!/3"
    set /p arch="Архитектура (!arch_hint!, Enter — в главное меню): "
    if "!arch!"=="" goto menu
)
set a=cpu
if "!arch!"=="2" set a=cuda
if "!arch!"=="3" set a=amd
if "!arch!"=="2" if "!gpu_nvidia!"=="0" (
    echo.
    echo !CR! Выбран CUDA, но видеокарта NVIDIA не обнаружена.!C0!
    pause
    goto install
)
if "!arch!"=="3" if "!gpu_amd!"=="0" (
    echo.
    echo !CR! Выбран AMD, но видеокарта AMD/Radeon не обнаружена.!C0!
    pause
    goto install
)
echo.
echo Запуск установки (среда, зависимости, сборка whisper [%a%], модель)...
uv run python scripts\install.py --arch %a%
echo.
echo !CG!Готово. Дальше: пункт 2 (Проверка), затем пункт 3 (Запуск).!C0!
pause
goto menu

:check
echo !CY![2]!C0! Проверка готовности...
uv run python scripts\check_ready.py
pause
goto menu

:toggle_notifications
echo !CY![12]!C0! Уведомления Windows...
if not exist .venv (
    echo !CR!Сначала выполните 1 (Установка).!C0!
    pause
    goto menu
)
for /f "usebackq tokens=*" %%a in (`uv run python -c "from infrastructure.config_repo import load_config; from pathlib import Path; p=Path('config.yaml'); cfg=load_config(p); print('включены' if cfg.get('notifications', False) else 'выключены')"`) do set "notif_cur=%%a"
echo Сейчас уведомления: !CY!!notif_cur!!C0!
uv run python -c "from infrastructure.config_repo import load_config, save_config; from pathlib import Path; p=Path('config.yaml'); cfg=load_config(p); cfg['notifications']=not cfg.get('notifications', False); save_config(p,cfg); print('Уведомления теперь:', 'включены' if cfg['notifications'] else 'выключены')"
pause
goto menu

:toggle_postprocess
echo !CY![13]!C0! Постобработка текста...
if not exist .venv (
    echo !CR!Сначала выполните 1 (Установка).!C0!
    pause
    goto menu
)
for /f "usebackq tokens=*" %%a in (`uv run python -c "from infrastructure.config_repo import load_config; from pathlib import Path; p=Path('config.yaml'); cfg=load_config(p); print('включена' if cfg.get('postprocess', True) else 'выключена')"`) do set "pp_cur=%%a"
echo Сейчас постобработка: !CY!!pp_cur!!C0!
echo Что делает: заглавная буква, точка в конце, удаление [BLANK_AUDIO] и других артефактов Whisper.
uv run python -c "from infrastructure.config_repo import load_config, save_config; from pathlib import Path; p=Path('config.yaml'); cfg=load_config(p); cfg['postprocess']=not cfg.get('postprocess', True); save_config(p,cfg); print('Постобработка теперь:', 'включена' if cfg['postprocess'] else 'выключена')"
pause
goto menu

:remove
echo !CY![11]!C0! Удаление установки
if not exist .venv (
    echo !CR!Удалять нечего — установка ещё не выполнялась.!C0! Сначала сделайте 1 (Установка).
    pause
    goto menu
)
echo Имеет смысл только если хотите всё удалить и поставить заново. После удаления снова выполните 1.
set /p confirm="Удалить .venv и models? (y/N, Enter — в главное меню): "
if "!confirm!"=="" goto menu
if /i not "!confirm!"=="y" goto menu
if exist .venv rmdir /s /q .venv
if exist models rmdir /s /q models
echo !CG!Удалено. Для новой установки снова выберите пункт 1.!C0!
pause
goto menu

:models
echo.
echo !CY![5]!C0! Модели распознавания
if not exist .venv (
    echo !CR!Сначала выполните 1 (Установка)!C0! — тогда появится среда и модель по умолчанию.
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
echo !CY![6]!C0! Подбор свободной горячей клавиши...
echo Тестируются сочетания Ctrl/Shift/Alt с F-клавишами (F1–F24).
echo Можно выбрать найденный вариант, и он будет записан в config.yaml.
uv run python scripts\scan_hotkeys.py
pause
goto menu

:set_hotkey_record
echo !CY![7]!C0! Горячая клавиша записи...
for /f "usebackq tokens=*" %%a in (`uv run python -c "from infrastructure.config_repo import load_config; from pathlib import Path; p=Path('config.yaml'); cfg=load_config(p); print(cfg.get('hotkey_record','Ctrl+F2'))"`) do set "cur_rec=%%a"
echo Сейчас: !CY!!cur_rec!!C0!
echo Примеры: Ctrl+F2, Ctrl+Shift+F12. Enter — оставить текущую.
set /p newrec="Введите строку (Enter — оставить !cur_rec!): "
if "!newrec!"=="" goto menu
uv run python -c "from infrastructure.config_repo import load_config, save_config; from pathlib import Path; import sys; p=Path('config.yaml'); cfg=load_config(p); cfg['hotkey_record']=sys.argv[1]; save_config(p,cfg)" "!newrec!"
echo !CG!Готово.!C0! Перезапустите службу (пункт 4, затем 3), чтобы изменение вступило в силу.
pause
goto menu

:set_hotkey_stop
echo !CY![8]!C0! Горячая клавиша стопа...
for /f "usebackq tokens=*" %%a in (`uv run python -c "from infrastructure.config_repo import load_config; from pathlib import Path; p=Path('config.yaml'); cfg=load_config(p); print(cfg.get('hotkey_stop','Ctrl+F3'))"`) do set "cur_stop=%%a"
echo Сейчас: !CY!!cur_stop!!C0!
echo Примеры: Ctrl+F3, Ctrl+Shift+F12. Enter — оставить текущую.
set /p newstop="Введите строку (Enter — оставить !cur_stop!): "
if "!newstop!"=="" goto menu
uv run python -c "from infrastructure.config_repo import load_config, save_config; from pathlib import Path; import sys; p=Path('config.yaml'); cfg=load_config(p); cfg['hotkey_stop']=sys.argv[1]; save_config(p,cfg)" "!newstop!"
echo !CG!Готово.!C0! Перезапустите службу (пункт 4, затем 3), чтобы изменение вступило в силу.
pause
goto menu

:set_language
echo !CY![9]!C0! Выбрать язык...
for /f "usebackq tokens=*" %%a in (`uv run python -c "from infrastructure.config_repo import load_config; from pathlib import Path; p=Path('config.yaml'); cfg=load_config(p); print(cfg.get('language', 'ru'))"`) do set "cur_lang=%%a"
echo Текущий язык: !CY!!cur_lang!!C0!
echo.
echo Примеры: ru, en, de, fr, es, it, jp, zh.
set /p newlang="Введите код языка (Enter — в главное меню): "
if "!newlang!"=="" goto menu
if "!newlang!"=="russian" ( echo !CR!Используйте код "ru", а не "russian".!C0! & pause & goto set_language )
if "!newlang!"=="english" ( echo !CR!Используйте код "en", а не "english".!C0! & pause & goto set_language )
uv run python -c "from infrastructure.config_repo import load_config, save_config; from pathlib import Path; import sys; p=Path('config.yaml'); cfg=load_config(p); cfg['language']=sys.argv[1]; save_config(p,cfg)" "!newlang!"
echo !CG!Язык установлен: !newlang!!C0!
pause
goto menu

:set_input_device
echo !CY![10]!C0! Устройство ввода (микрофон)...
if not exist .venv (
    echo !CR!Сначала выполните 1 (Установка).!C0!
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
echo !CY![3]!C0! Запуск службы...
if not exist .venv (
    echo !CR!Сначала выполните 1 (Установка), затем 2 (Проверка). Когда в пункте 2 всё будет OK — снова выберите 3.!C0!
    pause
    goto menu
)
if exist .roma-stt.pid (
    echo !CR!Служба уже запущена.!C0! Для перезапуска сначала остановите её ^(пункт 4^).
    pause
    goto menu
)
call :detect_gpu
set "mod="
if "!gpu_nvidia!"=="0" if "!gpu_amd!"=="0" (
    echo   !CD!Дискретная видеокарта не обнаружена — запускается CPU-режим.!C0!
    set mod=cpu
) else (
    echo   !CW!1!C0! = cpu  ^(без GPU, всегда работает^)
    if "!gpu_nvidia!"=="1" echo   !CW!2!C0! = cuda ^(!gpu_nvidia_name!^)
    if "!gpu_amd!"=="1"    echo   !CW!3!C0! = amd  ^(!gpu_amd_name!^)
    set "mod_hint=1"
    if "!gpu_nvidia!"=="1" set "mod_hint=!mod_hint!/2"
    if "!gpu_amd!"=="1"    set "mod_hint=!mod_hint!/3"
    set /p mod="Режим (!mod_hint!, Enter — в главное меню): "
    if "!mod!"=="" goto menu
    if "!mod!"=="1" set mod=cpu
    if "!mod!"=="2" set mod=cuda
    if "!mod!"=="3" set mod=amd
    if not "!mod!"=="cpu" if not "!mod!"=="cuda" if not "!mod!"=="amd" (
        echo !CR!Неверный выбор. Введите одну из предложенных цифр.!C0!
        pause
        goto start
    )
)
if "!mod!"=="cuda" if "!gpu_nvidia!"=="0" (
    echo.
    echo !CR! Выбран CUDA, но видеокарта NVIDIA не обнаружена.!C0!
    pause
    goto start
)
if "!mod!"=="amd" if "!gpu_amd!"=="0" (
    echo.
    echo !CR! Выбран AMD, но видеокарта AMD/Radeon не обнаружена.!C0!
    pause
    goto start
)
if not exist "bin\main-!mod!.exe" (
    echo Бинарник bin\main-!mod!.exe не найден. Запускается сборка whisper.cpp [!mod!]...
    echo Это займёт несколько минут. Не закрывайте окно.
    uv run python scripts\build_whisper_cpp.py --arch !mod!
    if errorlevel 1 (
        echo.
        echo !CR!Сборка завершилась с ошибкой. Проверьте зависимости ^(пункт 0^) и повторите.!C0!
        pause
        goto menu
    )
    echo !CG!Сборка завершена.!C0!
    set "cfgfile=config.yaml"
    uv run python -c "from infrastructure.config_repo import load_config, save_config; from pathlib import Path; import sys; p=Path('!cfgfile!'); cfg=load_config(p); cfg['module']=sys.argv[1]; save_config(p,cfg)" "!mod!"
    goto start_now
)
set "cfgfile=config.yaml"
uv run python -c "from infrastructure.config_repo import load_config, save_config; from pathlib import Path; import sys; p=Path('!cfgfile!'); cfg=load_config(p); cfg['module']=sys.argv[1]; save_config(p,cfg)" "!mod!"
uv run python scripts\check_ready.py >nul 2>&1
if errorlevel 1 (
    echo !CR!Проверка готовности не прошла:!C0!
    uv run python scripts\check_ready.py
    echo.
    echo Сделайте по порядку: 1 ^(Установка^), потом 2 ^(Проверка^). Когда в пункте 2 будет «Ready» — снова выберите 3.
    pause
    goto menu
)
:start_now
for /f "usebackq tokens=*" %%a in (`uv run python -c "from infrastructure.config_repo import load_config; from pathlib import Path; p=Path('config.yaml'); cfg=load_config(p); print(cfg.get('hotkey_record', 'Ctrl+F2'))"`) do set "hk_r=%%a"
for /f "usebackq tokens=*" %%b in (`uv run python -c "from infrastructure.config_repo import load_config; from pathlib import Path; p=Path('config.yaml'); cfg=load_config(p); print(cfg.get('hotkey_stop', 'Ctrl+F3'))"`) do set "hk_s=%%b"
echo !CG!Служба запускается в трее.!C0! Запись: !CY!!hk_r!!C0!, Стоп: !CY!!hk_s!!C0!
echo Остановить: пункт 4. Это окно можно закрыть.
start "" /B .venv\Scripts\pythonw.exe main.py --module !mod!
goto menu

:stop
echo !CY![4]!C0! Остановка Roma-STT...
if exist .roma-stt.pid (
    for /f "usebackq delims=" %%i in (".roma-stt.pid") do taskkill /PID %%i /F >nul 2>nul
    del .roma-stt.pid 2>nul
) else (
    for /f "delims=" %%i in ('uv run python scripts\find_roma_stt_pids.py 2^>nul') do taskkill /PID %%i /F >nul 2>nul
    taskkill /FI "WINDOWTITLE eq Roma-STT*" /F >nul 2>nul
)
echo !CG!Готово.!C0!
pause
goto menu

:detect_gpu
set gpu_nvidia=0
set gpu_amd=0
set "gpu_nvidia_name=NVIDIA"
set "gpu_amd_name=AMD/Radeon"
for /f "tokens=2 delims==" %%G in ('wmic path win32_VideoController get name /format:value 2^>nul') do (
    set "gpuline=%%G"
    rem Strip trailing CR that wmic adds to each value line
    set "gpuline=!gpuline:~0,-1!"
    if not "!gpuline!"=="" (
        echo !gpuline! | findstr /i "NVIDIA" >nul
        if not errorlevel 1 (
            set gpu_nvidia=1
            set "gpu_nvidia_name=!gpuline!"
        )
        echo !gpuline! | findstr /i "Radeon" >nul
        if not errorlevel 1 (
            set gpu_amd=1
            set "gpu_amd_name=!gpuline!"
        )
        if "!gpu_amd!"=="0" (
            echo !gpuline! | findstr /i "AMD" >nul
            if not errorlevel 1 (
                set gpu_amd=1
                set "gpu_amd_name=!gpuline!"
            )
        )
    )
)
exit /b 0
