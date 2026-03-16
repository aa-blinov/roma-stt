@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
echo.
echo [0] Установка нужных программ для Roma-STT (через winget)
echo Запустите roma-stt.bat от имени администратора, если winget выдаёт ошибку.
echo.
winget --version >nul 2>&1
if errorlevel 1 (
    echo winget не найден. Пробую установить WinGet автоматически...
    echo Запустите roma-stt.bat от имени администратора, если появится ошибка.
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -Command "& {$progressPreference='silentlyContinue'; Install-PackageProvider -Name NuGet -Force -Scope CurrentUser | Out-Null; Install-Module -Name Microsoft.WinGet.Client -Force -Repository PSGallery -Scope CurrentUser | Out-Null; Repair-WinGetPackageManager -AllUsers 2>$null; if (-not $?) { Write-Host 'Если не сработало, выполните шаг 0 в ИНСТРУКЦИЯ.md вручную.' }}"
    echo.
    winget --version >nul 2>&1
    if errorlevel 1 (
        echo WinGet после установки не найден. Закройте это окно, снова запустите roma-stt.bat от имени администратора и выберите 0.
        echo Либо установите программы вручную — ссылки в ИНСТРУКЦИЯ.md.
        exit /b 1
    )
    echo WinGet установлен.
)
echo winget найден, проверяю остальное...
echo.
set need_uv=1
uv --version >nul 2>&1
if not errorlevel 1 (
    echo uv уже установлен.
    set need_uv=0
)
if "!need_uv!"=="1" (
    echo Устанавливаю uv...
    winget install --id astral-sh.uv --accept-package-agreements --accept-source-agreements
)
echo.

set need_git=1
git --version >nul 2>&1
if not errorlevel 1 (
    echo Git уже установлен.
    set need_git=0
)
if "!need_git!"=="1" (
    echo Устанавливаю Git...
    winget install --id Git.Git --accept-package-agreements --accept-source-agreements
)
echo.

set need_cmake=1
cmake --version >nul 2>&1
if not errorlevel 1 (
    echo CMake уже установлен.
    set need_cmake=0
)
if "!need_cmake!"=="1" (
    echo Устанавливаю CMake...
    winget install --id Kitware.CMake --accept-package-agreements --accept-source-agreements
)
echo.

echo Visual Studio Build Tools ^(для сборки распознавания речи^) — большой пакет.
set "vs_installed="
where cl >nul 2>&1
if not errorlevel 1 (
    set "vs_installed=1"
    echo Компилятор Visual Studio уже найден в PATH.
)
if not defined vs_installed (
    set "vswhere=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
    if exist "!vswhere!" (
        for /f "usebackq delims=" %%i in (`"!vswhere!" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2^>nul`) do set "vs_installed=1"
        if defined vs_installed (
            echo Visual Studio Build Tools уже установлены ^(cl не в PATH — откройте новую консоль или «Developer Command Prompt for VS 2022»^).
        )
    )
)
if not defined vs_installed (
    set /p vs="Установить сейчас? (y/N): "
    if /i "!vs!"=="y" (
        echo Устанавливаю Visual Studio Build Tools...
        winget install --id Microsoft.VisualStudio.2022.BuildTools --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools" --accept-package-agreements --accept-source-agreements
        if errorlevel 1 (
            echo.
            echo Сбой установки. Попробуйте:
            echo 1. Запустить roma-stt.bat от имени администратора и снова выбрать пункт 0.
            echo 2. Либо открыть «Visual Studio Installer» из меню Пуск - Изменить - отметить «Средства сборки C++».
            echo 3. Если Build Tools уже стоят, закройте все окна консоли и откройте новую — затем пункт 1.
        ) else (
            echo Может потребоваться перезагрузка. После установки закройте консоль и откройте новую.
        )
    ) else (
        echo Поставьте потом вручную: https://visualstudio.microsoft.com/visual-cpp-build-tools/
    )
)
echo.

set need_cuda=1
where nvcc >nul 2>&1
if not errorlevel 1 (
    echo CUDA Toolkit ^(nvcc^) уже найден в PATH.
    set need_cuda=0
)
if "!need_cuda!"=="1" (
    echo CUDA Toolkit ^(для сборки под видеокарту NVIDIA^) — большой пакет ^(~3 ГБ^).
    set /p cuda="Установить сейчас? (y/N): "
    if /i "!cuda!"=="y" (
        echo Устанавливаю NVIDIA CUDA Toolkit ^(winget install -e --id Nvidia.CUDA^)...
        echo Внимание: установка может предложить перезагрузку Windows — можно отложить.
        winget install -e --id Nvidia.CUDA --accept-package-agreements --accept-source-agreements --silent
        echo После установки закройте это окно, откройте консоль заново и запустите пункт 1 или build-whisper с архитектурой cuda.
    ) else (
        echo Поставьте потом: winget install -e --id Nvidia.CUDA или https://developer.nvidia.com/cuda-downloads
    )
)
echo.
echo После установки закройте окно, откройте папку снова и запустите roma-stt.bat.
echo Дальше: пункт 1 ^(Установка^), 2 ^(Проверка^), 5 ^(Запуск^).
exit /b 0
