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
where cl >nul 2>&1
if not errorlevel 1 (
    echo Компилятор Visual Studio уже найден в PATH.
) else (
    set /p vs="Установить сейчас? (y/N): "
    if /i "!vs!"=="y" (
        echo Устанавливаю Visual Studio Build Tools...
        winget install --id Microsoft.VisualStudio.2022.BuildTools --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools" --accept-package-agreements --accept-source-agreements
        echo Может потребоваться перезагрузка.
    ) else (
        echo Поставьте потом вручную: https://visualstudio.microsoft.com/visual-cpp-build-tools/
    )
)
echo.
echo После установки закройте окно, откройте папку снова и запустите roma-stt.bat.
echo Дальше: пункт 1 ^(Установка^), 2 ^(Проверка^), 5 ^(Запуск^).
exit /b 0
