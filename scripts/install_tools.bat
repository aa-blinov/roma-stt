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
set /p go="Продолжить установку? (y — да, Enter — в главное меню): "
if "!go!"=="" exit /b 0
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
set "vswhere_exe=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not defined vs_installed (
    if exist "!vswhere_exe!" (
        for /f "usebackq delims=" %%i in (`"!vswhere_exe!" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2^>nul`) do set "vs_installed=1"
        if defined vs_installed (
            echo Visual Studio Build Tools уже установлены с компонентом C++.
        )
    )
)
if not defined vs_installed (
    set /p vs="Установить / добавить C++ компонент Build Tools? (y — да, Enter — пропустить): "
    if /i "!vs!"=="y" (
        echo Устанавливаю Visual Studio Build Tools с C++...
        echo ^(Если уже установлено без C++ — winget добавит нужный компонент^)
        winget install --id Microsoft.VisualStudio.2022.BuildTools --force --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended --norestart" --accept-package-agreements --accept-source-agreements
        if errorlevel 1 (
            echo.
            echo Сбой установки. Попробуйте:
            echo 1. Запустить roma-stt.bat от имени администратора и снова выбрать пункт 0.
            echo 2. Либо открыть «Visual Studio Installer» из меню Пуск → Изменить → «Средства сборки C++».
        ) else (
            echo Готово. Закройте консоль, откройте новую и повторите пункт 3.
        )
    ) else (
        echo Поставьте потом вручную: https://visualstudio.microsoft.com/visual-cpp-build-tools/
    )
)
echo.

echo Определяю видеокарту...
set gpu_nvidia=0
set gpu_amd=0
wmic path win32_VideoController get name 2>nul | findstr /i "NVIDIA" >nul
if not errorlevel 1 set gpu_nvidia=1
wmic path win32_VideoController get name 2>nul | findstr /i "AMD" >nul
if not errorlevel 1 set gpu_amd=1
wmic path win32_VideoController get name 2>nul | findstr /i "Radeon" >nul
if not errorlevel 1 set gpu_amd=1
echo.
if "!gpu_nvidia!"=="1" echo   Обнаружена видеокарта NVIDIA.
if "!gpu_amd!"=="1"    echo   Обнаружена видеокарта AMD ^(Radeon^).
if "!gpu_nvidia!"=="0" if "!gpu_amd!"=="0" (
    echo   Дискретная видеокарта NVIDIA или AMD не обнаружена. Будет использоваться CPU.
)
echo.

if "!gpu_nvidia!"=="1" (
    set need_cuda=1
    where nvcc >nul 2>&1
    if not errorlevel 1 (
        echo CUDA Toolkit ^(nvcc^) уже найден в PATH.
        set need_cuda=0
    )
    if "!need_cuda!"=="1" (
        echo CUDA Toolkit ускорит распознавание речи на NVIDIA. Большой пакет ^(~3 ГБ^).
        echo Если достаточно CPU — отвечайте N.
        set /p cuda="Установить CUDA Toolkit? (y/N): "
        if /i "!cuda!"=="y" (
            echo Устанавливаю NVIDIA CUDA Toolkit...
            echo Внимание: установка может предложить перезагрузку Windows — можно отложить.
            winget install -e --id Nvidia.CUDA --accept-package-agreements --accept-source-agreements --silent
            echo После установки закройте это окно, откройте консоль заново и запустите пункт 1.
        ) else (
            echo Пропущено. При запуске выберите режим cpu ^(пункт 3 -^> 1^).
        )
    )
    echo.
)

if "!gpu_amd!"=="1" (
    set need_vulkan=1
    rem Check for actual LunarG SDK (not just runtime from GPU driver)
    rem glslc.exe is only present in the full SDK, not in driver-bundled runtime
    where glslc >nul 2>&1
    if not errorlevel 1 (
        echo Vulkan SDK ^(LunarG^) уже установлен ^(glslc найден^).
        set need_vulkan=0
    )
    if "!need_vulkan!"=="1" (
        if defined VULKAN_SDK (
            if exist "!VULKAN_SDK!\Lib\vulkan-1.lib" (
                echo Vulkan SDK уже установлен ^(VULKAN_SDK=!VULKAN_SDK!^).
                set need_vulkan=0
            )
        )
    )
    if "!need_vulkan!"=="1" (
        if exist "C:\VulkanSDK" (
            echo Vulkan SDK найден в C:\VulkanSDK.
            set need_vulkan=0
        )
    )
    if "!need_vulkan!"=="1" (
        echo Vulkan SDK ускорит распознавание речи на AMD. ~200 МБ.
        echo Если достаточно CPU — отвечайте N.
        set /p vulkan="Установить Vulkan SDK? (y — да, Enter — пропустить): "
        if /i "!vulkan!"=="y" (
            echo Устанавливаю Vulkan SDK ^(KhronosGroup.VulkanSDK^)...
            winget install --id KhronosGroup.VulkanSDK --accept-package-agreements --accept-source-agreements
            echo После установки закройте это окно, откройте консоль заново и запустите пункт 3.
        ) else (
            echo Пропущено. При запуске выберите режим cpu ^(пункт 3 -^> 1^).
        )
    )
    echo.
)

echo После установки закройте окно, откройте папку снова и запустите roma-stt.bat.
echo Дальше: пункт 1 ^(Установка^), 2 ^(Проверка^), 3 ^(Запуск^).
exit /b 0
