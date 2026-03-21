#Requires -Version 5.1
# Encoding: UTF-8 with BOM — required on Windows PowerShell 5.1 for Cyrillic in this script.
<#
.SYNOPSIS
Roma-STT - меню управления
#>

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
$Host.UI.RawUI.WindowTitle = "Roma-STT"
try {
    $buf = $Host.UI.RawUI.BufferSize
    if ($buf.Height -lt 55) { $buf.Height = 9999; $Host.UI.RawUI.BufferSize = $buf }
    $win = $Host.UI.RawUI.WindowSize
    if ($win.Height -lt 55) { $win.Height = 55; $Host.UI.RawUI.WindowSize = $win }
} catch {}
Set-Location $PSScriptRoot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Pause-Continue {
    Write-Host ""
    $null = Read-Host "Нажмите Enter для продолжения"
}

function Get-Config {
    param([string]$key, [string]$default = "")
    $val = & uv run python -c "from infrastructure.config_repo import load_config; from pathlib import Path; p=Path('config.yaml'); cfg=load_config(p); print(cfg.get('$key','$default'))" 2>$null
    if ($val) { $val.Trim() } else { $default }
}

function Set-Config {
    param([string]$key, [string]$value)
    & uv run python -c "from infrastructure.config_repo import load_config, save_config; from pathlib import Path; import sys; p=Path('config.yaml'); cfg=load_config(p); cfg['$key']=sys.argv[1]; save_config(p,cfg)" $value 2>$null
}

function Refresh-Env {
    # Обновляем PATH и ключевые переменные из реестра  -  после winget install
    $m = [System.Environment]::GetEnvironmentVariable("PATH", "Machine")
    $u = [System.Environment]::GetEnvironmentVariable("PATH", "User")
    if ($m -or $u) { $env:PATH = "$m;$u" }
    foreach ($var in @("VULKAN_SDK", "CUDA_PATH", "CUDA_PATH_V12_0", "CUDA_PATH_V11_8")) {
        $v = [System.Environment]::GetEnvironmentVariable($var, "Machine")
        if (-not $v) { $v = [System.Environment]::GetEnvironmentVariable($var, "User") }
        if ($v) { [System.Environment]::SetEnvironmentVariable($var, $v, "Process") }
    }
}

function Detect-Gpu {
    $nvidiaName = ""
    $amdName    = ""
    try {
        $gpus = Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue |
                Select-Object -ExpandProperty Name
        foreach ($g in $gpus) {
            if ($g -match "NVIDIA") { $nvidiaName = $g }
            if ($g -match "Radeon|AMD") { $amdName = $g }
        }
    } catch {}
    return @{ NvidiaName = $nvidiaName; AmdName = $amdName }
}

# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------

function Get-RunningPid {
    if (Test-Path ".roma-stt.pid") {
        $pidVal = (Get-Content ".roma-stt.pid" -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
        if ($pidVal -match '^\d+$') {
            $proc = Get-Process -Id ([int]$pidVal) -ErrorAction SilentlyContinue
            if ($proc) { return [int]$pidVal }
        }
        # pid-файл есть, но процесс мёртв  -  удаляем зависший файл
        Remove-Item ".roma-stt.pid" -ErrorAction SilentlyContinue
    }
    return $null
}

function Test-CommandLineIsRomaSttService {
    param([int]$ProcessId)
    try {
        $wp = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
        if (-not $wp) { return $false }
        $cmd = [string]$wp.CommandLine
        if ($cmd -notmatch 'main\.py') { return $false }
        if ($cmd -match 'roma-stt|roma_stt') { return $true }
        if ($PSScriptRoot -and ($cmd.IndexOf($PSScriptRoot, [StringComparison]::OrdinalIgnoreCase) -ge 0)) { return $true }
        return $false
    } catch {
        return $false
    }
}

function Get-RomaSttPidsFromPythonScan {
    $ids = New-Object System.Collections.Generic.List[int]
    try {
        $lines = & uv run python scripts/find_roma_stt_pids.py 2>$null
        if ($lines) {
            foreach ($line in $lines) {
                $t = [string]$line.Trim()
                if ($t -match '^\d+$') { $ids.Add([int]$t) }
            }
        }
    } catch { }
    return $ids
}

function Stop-RomaSttProcessWithWait {
    param([int]$ProcessId, [int]$MaxWaitMs = 4500)
    if (-not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) { return $true }
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw.ElapsedMilliseconds -lt $MaxWaitMs) {
        if (-not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) {
            return $true
        }
        Start-Sleep -Milliseconds 160
    }
    return (-not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue))
}

function Get-ReadinessSummary {
    # Компактная строка для шапки меню (scripts/check_ready.py --summary)
    if (-not (Test-Path ".venv")) {
        return @{ Ok = $false; Detail = 'нет .venv, пункт 1' }
    }
    try {
        $out = (& uv run python scripts/check_ready.py --summary 2>$null | Select-Object -First 1)
        if (-not $out) { return @{ Ok = $false; Detail = "не удалось проверить" } }
        $parts = $out.Trim() -split "`t", 2
        $ok = ($parts[0] -eq "1")
        $detail = if ($parts.Count -gt 1 -and $parts[1]) { $parts[1].Trim() } else { "" }
        if ($detail.Length -gt 72) { $detail = $detail.Substring(0, 69) + "..." }
        return @{ Ok = $ok; Detail = $detail }
    } catch {
        return @{ Ok = $false; Detail = "ошибка проверки" }
    }
}

function Get-MenuConfig {
    # JSON одной строкой из scripts/print_menu_state.py (не ломается от предупреждений uv в stdout)
    if (-not (Test-Path ".venv")) { return @{ lang = ""; model = ""; hkr = ""; hks = ""; module = "" } }
    $raw = (& uv run python scripts/print_menu_state.py 2>$null | Select-Object -Last 1)
    if (-not $raw) {
        return @{ lang = "ru"; model = ""; hkr = "Ctrl+F2"; hks = "Ctrl+F3"; module = "cpu" }
    }
    try {
        $o = $raw.Trim() | ConvertFrom-Json
        return @{
            lang   = [string]$o.lang
            model  = [string]$o.model_stem
            hkr    = [string]$o.hotkey_record
            hks    = [string]$o.hotkey_stop
            module = [string]$o.module
        }
    } catch {
        return @{ lang = "ru"; model = ""; hkr = "Ctrl+F2"; hks = "Ctrl+F3"; module = "cpu" }
    }
}

function Show-Menu {
    $cfg = Get-MenuConfig
    $langVal   = if ($cfg.lang)  { $cfg.lang }  else { "?" }
    $modelVal  = if ($cfg.model) { $cfg.model -replace '^ggml-','' } else { "?" }
    $hkrVal    = if ($cfg.hkr)  { $cfg.hkr }  else { "?" }
    $hksVal    = if ($cfg.hks)  { $cfg.hks }  else { "?" }
    $modVal    = if ($cfg.module) { $cfg.module } else { "cpu" }

    $runningPid = Get-RunningPid
    $statusText  = if ($runningPid) { "работает  (PID $runningPid)" } else { "остановлена" }
    $statusColor = if ($runningPid) { "Green" } else { "DarkGray" }

    $ready = Get-ReadinessSummary

    Clear-Host
    Write-Host ""
    Write-Host " ============================================================" -ForegroundColor DarkGray
    Write-Host "  " -NoNewline
    Write-Host "Roma-STT" -NoNewline -ForegroundColor Cyan
    Write-Host "  -  Speech to Text (голос в текст)"
    Write-Host "  Служба: " -NoNewline; Write-Host $statusText -NoNewline -ForegroundColor $statusColor
    Write-Host "  |  Режим: " -NoNewline; Write-Host $modVal -NoNewline -ForegroundColor Cyan
    Write-Host "  |  Модель: " -NoNewline; Write-Host $modelVal -ForegroundColor Cyan
    Write-Host "  Готовность: " -NoNewline
    if ($ready.Ok) {
        Write-Host "OK" -ForegroundColor Green
    } else {
        Write-Host "не готово" -NoNewline -ForegroundColor Yellow
        if ($ready.Detail) { Write-Host ('  - ' + $ready.Detail) -ForegroundColor DarkYellow }
        else { Write-Host "" }
    }
    Write-Host " ============================================================" -ForegroundColor DarkGray
    Write-Host "  Введите цифру и нажмите Enter."
    Write-Host "  Первый запуск — пункт 1, затем 2" -ForegroundColor Yellow
    Write-Host "  " -NoNewline; Write-Host " 1." -NoNewline -ForegroundColor Yellow; Write-Host " Установка / переустановка / удаление"
    Write-Host "     Первый раз  -  полная установка или обновление/удаление установки" -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host " 2." -NoNewline -ForegroundColor Yellow; Write-Host " Запустить службу (в трее)"
    Write-Host "     Режим и горячая клавиша из config.yaml" -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host " 3." -NoNewline -ForegroundColor Yellow; Write-Host " Остановить службу"
    Write-Host "     Завершить работу Roma-STT в трее" -ForegroundColor DarkGray
    Write-Host " --- Настройки (после изменений: 3 -> 2) ---------------------" -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host " 4." -NoNewline -ForegroundColor Yellow; Write-Host " Модели распознавания       " -NoNewline; Write-Host "[$modelVal]" -ForegroundColor Cyan
    Write-Host "     Зелёный — файл уже в models; серый — не скачан; размер HF, сравнение, статус в строке (как в окне управления)" -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host " 5." -NoNewline -ForegroundColor Yellow; Write-Host " Подбор свободной горячей клавиши"
    Write-Host "     Протестировать F-клавиши и записать в config.yaml" -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host " 6." -NoNewline -ForegroundColor Yellow; Write-Host " Горячая клавиша записи     " -NoNewline; Write-Host "[$hkrVal]" -ForegroundColor Cyan
    Write-Host "     Клавиша для начала записи голоса" -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host " 7." -NoNewline -ForegroundColor Yellow; Write-Host " Горячая клавиша стопа      " -NoNewline; Write-Host "[$hksVal]" -ForegroundColor Cyan
    Write-Host "     Клавиша для остановки записи" -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host " 8." -NoNewline -ForegroundColor Yellow; Write-Host " Язык распознавания         " -NoNewline; Write-Host "[$langVal]" -ForegroundColor Cyan
    Write-Host "     Код языка ISO 639-1: ru, en, de, fr, es, it, zh..." -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host " 9." -NoNewline -ForegroundColor Yellow; Write-Host " Устройство ввода (микрофон)"
    Write-Host "     Выбрать микрофон из списка устройств" -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host "10." -NoNewline -ForegroundColor Yellow; Write-Host " Выход"
    Write-Host ""
}

# ---------------------------------------------------------------------------
# Menu actions
# ---------------------------------------------------------------------------

function Install-Tools {
    param([string]$arch = "cpu")

    # winget
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Host "winget не найден. Пробую установить автоматически..." -ForegroundColor Yellow
        try {
            powershell -NoProfile -Command @'
$progressPreference='silentlyContinue'
Install-PackageProvider -Name NuGet -Force -Scope CurrentUser | Out-Null
Install-Module -Name Microsoft.WinGet.Client -Force -Repository PSGallery -Scope CurrentUser | Out-Null
Repair-WinGetPackageManager -AllUsers 2>$null
'@
        } catch {}
        if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
            Write-Host "winget не установлен. Установите программы вручную:" -ForegroundColor Red
            Write-Host "  uv:    winget install astral-sh.uv"
            Write-Host "  Git:   winget install Git.Git"
            Write-Host "  CMake: winget install Kitware.CMake"
            Write-Host "  VS:    https://visualstudio.microsoft.com/visual-cpp-build-tools/"
            return $false
        }
        Write-Host "winget установлен." -ForegroundColor Green
    }

    # uv
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Host "uv уже установлен." -ForegroundColor DarkGray
    } else {
        Write-Host "Устанавливаю uv..." -ForegroundColor Yellow
        & winget install --id astral-sh.uv --accept-package-agreements --accept-source-agreements
    }

    # Git
    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-Host "Git уже установлен." -ForegroundColor DarkGray
    } else {
        Write-Host "Устанавливаю Git..." -ForegroundColor Yellow
        & winget install --id Git.Git --accept-package-agreements --accept-source-agreements
    }

    # CMake
    if (Get-Command cmake -ErrorAction SilentlyContinue) {
        Write-Host "CMake уже установлен." -ForegroundColor DarkGray
    } else {
        Write-Host "Устанавливаю CMake..." -ForegroundColor Yellow
        & winget install --id Kitware.CMake --accept-package-agreements --accept-source-agreements
    }

    # VS Build Tools
    $vsInstalled = $false
    if (Get-Command cl -ErrorAction SilentlyContinue) {
        $vsInstalled = $true
        Write-Host "Компилятор Visual Studio уже найден в PATH." -ForegroundColor DarkGray
    }
    if (-not $vsInstalled) {
        $vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
        if (Test-Path $vswhere) {
            $vsPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2>$null
            if ($vsPath) { $vsInstalled = $true; Write-Host "Visual Studio Build Tools уже установлены." -ForegroundColor DarkGray }
        }
    }
    if (-not $vsInstalled) {
        Write-Host ""
        Write-Host "Visual Studio Build Tools (C++) нужны для сборки распознавания речи." -ForegroundColor Yellow
        $vs = Read-Host "Установить сейчас? Большой пакет (~5 ГБ). (y/N)"
        if ($vs -match '^[yYдД]$') {
            Write-Host "Устанавливаю VS Build Tools..."
            & winget install --id Microsoft.VisualStudio.2022.BuildTools --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools" --accept-package-agreements --accept-source-agreements
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Сбой. Откройте Visual Studio Installer из меню Пуск → Изменить → C++ Build Tools." -ForegroundColor Red
            } else {
                Write-Host "Может потребоваться перезагрузка." -ForegroundColor Yellow
            }
        } else {
            Write-Host "Пропущено  -  сборка whisper.cpp может не сработать." -ForegroundColor DarkGray
        }
    }

    # CUDA (только для режима cuda)
    if ($arch -eq "cuda") {
        if (Get-Command nvcc -ErrorAction SilentlyContinue) {
            Write-Host "CUDA Toolkit уже установлен." -ForegroundColor DarkGray
        } else {
            Write-Host ""
            Write-Host "CUDA Toolkit нужен для режима cuda (~3 ГБ)." -ForegroundColor Yellow
            $cuda = Read-Host "Установить сейчас? (y/N)"
            if ($cuda -match '^[yYдД]$') {
                & winget install -e --id Nvidia.CUDA --accept-package-agreements --accept-source-agreements --silent
                Refresh-Env
                Write-Host "После установки может потребоваться перезагрузка." -ForegroundColor Yellow
            }
        }
    }

    # Vulkan SDK (только для режима amd)
    # vulkaninfo есть в GPU-драйверах, но без dev-части (заголовков/glslc)
    # Нужен полный LunarG SDK: проверяем VULKAN_SDK или glslc
    if ($arch -eq "amd") {
        $vulkanDev = ($env:VULKAN_SDK -and (Test-Path $env:VULKAN_SDK)) -or (Get-Command glslc -ErrorAction SilentlyContinue)
        if ($vulkanDev) {
            Write-Host "Vulkan SDK (dev) уже установлен." -ForegroundColor DarkGray
        } else {
            Write-Host ""
            Write-Host "Vulkan SDK (LunarG) нужен для режима amd (~200 МБ)." -ForegroundColor Yellow
            Write-Host "  (vulkaninfo из GPU-драйвера не считается  -  нужны заголовки и glslc)" -ForegroundColor DarkGray
            $vulkan = Read-Host "Установить сейчас? (y/N)"
            if ($vulkan -match '^[yYдД]$') {
                & winget install --id KhronosGroup.VulkanSDK --accept-package-agreements --accept-source-agreements
                Refresh-Env
                Write-Host "Vulkan SDK установлен. VULKAN_SDK=$env:VULKAN_SDK" -ForegroundColor Green
            }
        }
    }

    return $true
}

function Invoke-RomaInstall {
    # Полная цепочка: архитектура, winget-инструменты, scripts/install.py (без проверок «уже есть .venv»)
    $gpu = Detect-Gpu
    $a = "cpu"
    if ($gpu.NvidiaName -or $gpu.AmdName) {
        Write-Host "   1 = cpu  (без GPU, всегда работает)"
        if ($gpu.NvidiaName) { Write-Host "   2 = cuda ($($gpu.NvidiaName))" -ForegroundColor Yellow }
        if ($gpu.AmdName)    { Write-Host "   3 = amd  ($($gpu.AmdName))"    -ForegroundColor Yellow }
        $hint = "1"
        if ($gpu.NvidiaName) { $hint += "/2" }
        if ($gpu.AmdName)    { $hint += "/3" }
        $arch = Read-Host "Архитектура ($hint, Enter  -  назад)"
        if (-not $arch) { return }
        if ($arch -eq "2") {
            if (-not $gpu.NvidiaName) { Write-Host "Выбран CUDA, но NVIDIA не обнаружена." -ForegroundColor Red; Pause-Continue; return }
            $a = "cuda"
        } elseif ($arch -eq "3") {
            if (-not $gpu.AmdName) { Write-Host "Выбран AMD, но AMD/Radeon не обнаружена." -ForegroundColor Red; Pause-Continue; return }
            $a = "amd"
        }
    } else {
        Write-Host "  Дискретная видеокарта не обнаружена  -  будет CPU-режим." -ForegroundColor DarkGray
    }

    Write-Host ""
    Write-Host "Шаг 1/2: Проверка и установка системных инструментов..." -ForegroundColor Cyan
    $ok = Install-Tools $a
    if (-not $ok) { Pause-Continue; return }

    Refresh-Env

    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host ""
        Write-Host "uv только что установлен, но PATH ещё не обновился." -ForegroundColor Yellow
        Write-Host "Закройте это окно, откройте снова и пункт 1  -  переустановить (п.1 в подменю)." -ForegroundColor Yellow
        Pause-Continue; return
    }

    Write-Host ""
    Write-Host "Шаг 2/2: Установка окружения, сборка whisper [$a], загрузка модели..." -ForegroundColor Cyan
    & uv run python scripts/install.py --arch $a
    Pause-Continue
}

function Do-Install {
    Write-Host "[1] Установка..." -ForegroundColor Cyan
    if (-not (Test-Path ".venv")) {
        Invoke-RomaInstall
        return
    }

    Write-Host "Установка уже есть (.venv)." -ForegroundColor Yellow
    Write-Host "  1  -  переустановить / обновить (winget, uv sync, сборка whisper)"
    Write-Host "  2  -  удалить установку (.venv и папка models)"
    $sub = Read-Host "Выбор (1-2, Enter  -  в главное меню)"
    if (-not $sub) { return }

    if ($sub -eq "2") {
        Write-Host "Будут удалены папки .venv и models (если есть)."
        $confirm = Read-Host "Удалить? (y/N, Enter  -  отмена)"
        if (-not $confirm -or $confirm -notmatch "^[yYдД]$") { return }
        if (Test-Path ".venv")  { Remove-Item ".venv"  -Recurse -Force }
        if (Test-Path "models") { Remove-Item "models" -Recurse -Force }
        Write-Host "Удалено. Чтобы поставить снова, снова выберите пункт 1." -ForegroundColor Green
        Pause-Continue
        return
    }

    if ($sub -eq "1") {
        Invoke-RomaInstall
        return
    }

    Write-Host "Неизвестный выбор." -ForegroundColor Red
    Start-Sleep -Seconds 1
}

function Do-Start {
    Write-Host "[2] Запуск службы..." -ForegroundColor Cyan
    if (-not (Test-Path ".venv")) {
        Write-Host "Сначала выполните 1 (Установка)." -ForegroundColor Red
        Pause-Continue; return
    }
    $runningPid = Get-RunningPid
    if ($runningPid) {
        Write-Host "Служба уже запущена (PID $runningPid). Для перезапуска сначала остановите её (пункт 3)." -ForegroundColor Red
        Pause-Continue; return
    }
    $mod = Get-Config "module" "cpu"
    if (-not $mod) { $mod = "cpu" }

    # Find exe, with fallback
    $mainexe = $null
    $candidates = @("bin\main-$mod.exe")
    if ($mod -eq "cpu") { $candidates += "bin\main.exe" }
    foreach ($c in $candidates) { if (Test-Path $c) { $mainexe = $c; break } }

    if (-not $mainexe) {
        foreach ($try in @("bin\main-cuda.exe","bin\main-amd.exe","bin\main-cpu.exe","bin\main.exe")) {
            if (Test-Path $try) {
                $mainexe = $try
                $mod = if ($try -match "cuda") {"cuda"} elseif ($try -match "amd") {"amd"} else {"cpu"}
                Set-Config "module" $mod
                break
            }
        }
    }
    if (-not $mainexe) {
        Write-Host "Ни один бинарник не найден. Пункт 1  -  установка или переустановка." -ForegroundColor Red
        Pause-Continue; return
    }

    $readyOut = & uv run python scripts/check_ready.py 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Проверка готовности не прошла:" -ForegroundColor Red
        $readyOut | ForEach-Object { Write-Host $_ }
        Write-Host ""
        Write-Host "Пункт 1 (установка / переустановка). Статус в шапке меню, затем снова 2."
        Pause-Continue; return
    }

    $hkr = Get-Config "hotkey_record" "Ctrl+F2"
    $hks = Get-Config "hotkey_stop"   "Ctrl+F3"
    Write-Host "Режим: " -NoNewline; Write-Host $mod -NoNewline -ForegroundColor Cyan
    Write-Host ", Запись: " -NoNewline; Write-Host $hkr -NoNewline -ForegroundColor Cyan
    Write-Host ", Стоп: "  -NoNewline; Write-Host $hks -ForegroundColor Cyan
    Write-Host "Остановить: пункт 3. Это окно можно закрыть."
    $pythonw = Join-Path $PSScriptRoot ".venv\Scripts\pythonw.exe"
    Start-Process $pythonw -ArgumentList @("main.py", "--module", $mod) -WorkingDirectory $PSScriptRoot

    # Ждём появления pid-файла (до 6 секунд)
    $waited = 0
    while (-not (Test-Path ".roma-stt.pid") -and $waited -lt 6) {
        Start-Sleep -Milliseconds 500
        $waited += 0.5
    }
    if (Test-Path ".roma-stt.pid") {
        Write-Host "Служба запущена." -ForegroundColor Green
    } else {
        Write-Host "Служба не ответила за 6 секунд  -  возможна ошибка. Проверьте логи." -ForegroundColor Yellow
    }
    Pause-Continue
}

function Do-Stop {
    Write-Host "[3] Остановка Roma-STT..." -ForegroundColor Cyan

    # Раньше: только PID из файла ИЛИ только скан Python — при сбое Stop-Process файл всё равно
    # удалялся, и со второго раза срабатывал fallback. Теперь всегда объединяем оба источника,
    # проверяем командную строку (не чужой процесс) и ждём завершения.
    $toStop = New-Object 'System.Collections.Generic.HashSet[int]'

    if (Test-Path ".roma-stt.pid") {
        $raw = (Get-Content ".roma-stt.pid" -ErrorAction SilentlyContinue | Select-Object -First 1)
        $pidStr = if ($null -ne $raw) { [string]$raw.Trim() } else { "" }
        if ($pidStr -match '^\d+$') {
            $candidate = [int]$pidStr
            if (Test-CommandLineIsRomaSttService -ProcessId $candidate) {
                [void]$toStop.Add($candidate)
            }
        }
    }

    foreach ($scanPid in (Get-RomaSttPidsFromPythonScan)) {
        [void]$toStop.Add($scanPid)
    }

    if ($toStop.Count -eq 0) {
        Remove-Item ".roma-stt.pid" -ErrorAction SilentlyContinue
        Write-Host "Запущенный Roma-STT не найден — останавливать нечего" -ForegroundColor DarkGray
        Pause-Continue
        return
    }

    $anyStopped = $false
    foreach ($procId in $toStop) {
        if (Stop-RomaSttProcessWithWait -ProcessId $procId) {
            $anyStopped = $true
        }
    }

    Remove-Item ".roma-stt.pid" -ErrorAction SilentlyContinue

    if ($anyStopped) {
        Write-Host "Служба остановлена." -ForegroundColor Green
    } else {
        Write-Host "Процесс не завершился за отведённое время. Повторите пункт 3 или снимите задачу вручную." -ForegroundColor Yellow
    }
    Pause-Continue
}

function Do-Models {
    Write-Host ""
    Write-Host "[4] Модели распознавания" -ForegroundColor Cyan
    if (-not (Test-Path ".venv")) {
        Write-Host "Сначала выполните 1 (Установка)." -ForegroundColor Red
        Pause-Continue; return
    }
    Write-Host ""
    Write-Host "Модели Whisper (тот же смысл, что подсказка на вкладке «Модель» в окне управления):" -ForegroundColor DarkGray
    Write-Host "  Строки зелёным — файл уже в папке models, серым — ещё не скачан."
    Write-Host "  Для каждой строки указан примерный размер скачиваемого файла (ggerganov/whisper.cpp на Hugging Face)."
    Write-Host "  В конце строки в скобках статус; перед скобками — краткое сравнение."
    Write-Host "  Список обновляется при каждом входе в пункт 4; при скачивании в консоли виден ход загрузки (в GUI — полоса прогресса)."
    Write-Host "  Номер или имя: если модель скачана — выберется активной; если нет — скачается и выберется (кнопка «Выбрать / скачать и выбрать»)."
    Write-Host ""
    & uv run python scripts/models.py list-all
    $num = Read-Host "Номер из списка или название (Enter  -  в главное меню)"
    if (-not $num) { return }
    & uv run python scripts/models.py use $num
    Pause-Continue
}

function Do-ScanHotkeys {
    Write-Host "[5] Подбор свободной горячей клавиши..." -ForegroundColor Cyan
    if (-not (Test-Path ".venv")) {
        Write-Host "Сначала выполните 1 (Установка)." -ForegroundColor Red
        Pause-Continue; return
    }
    Write-Host "Тестируются сочетания Ctrl/Shift/Alt с F-клавишами (F1-F24)."
    Write-Host "Можно выбрать найденный вариант, и он будет записан в config.yaml."
    & uv run python scripts/scan_hotkeys.py
    Pause-Continue
}

function Do-SetHotkey {
    param([string]$which)
    $isRecord = ($which -eq "record")
    $label    = if ($isRecord) { "[6] Горячая клавиша записи" } else { "[7] Горячая клавиша стопа" }
    $cfgKey   = if ($isRecord) { "hotkey_record" } else { "hotkey_stop" }
    $default  = if ($isRecord) { "Ctrl+F2" } else { "Ctrl+F3" }
    Write-Host "$label..." -ForegroundColor Cyan
    if (-not (Test-Path ".venv")) {
        Write-Host "Сначала выполните 1 (Установка)." -ForegroundColor Red
        Pause-Continue; return
    }
    $cur = Get-Config $cfgKey $default
    Write-Host "Сейчас: " -NoNewline; Write-Host $cur -ForegroundColor Cyan
    Write-Host "Примеры: Ctrl+F2, Ctrl+Shift+F12. Enter  -  оставить текущую."
    $new = Read-Host "Введите строку (Enter  -  оставить $cur)"
    if (-not $new) { return }
    Set-Config $cfgKey $new
    Write-Host "Готово." -ForegroundColor Green
    Write-Host "Перезапустите службу (пункт 3, затем 2), чтобы изменение вступило в силу."
    Pause-Continue
}

function Do-SetLanguage {
    Write-Host "[8] Выбрать язык..." -ForegroundColor Cyan
    $cur = Get-Config "language" "ru"
    Write-Host "Текущий язык: " -NoNewline; Write-Host $cur -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Примеры: ru, en, de, fr, es, it, jp, zh."
    while ($true) {
        $new = Read-Host "Введите код языка (Enter  -  в главное меню)"
        if (-not $new) { return }
        if ($new -eq "russian") { Write-Host 'Используйте код "ru", а не "russian".' -ForegroundColor Red; continue }
        if ($new -eq "english") { Write-Host 'Используйте код "en", а не "english".' -ForegroundColor Red; continue }
        Set-Config "language" $new
        Write-Host "Язык установлен: $new" -ForegroundColor Green
        Start-Sleep -Seconds 1; return
    }
}

function Do-SetInputDevice {
    Write-Host "[9] Устройство ввода (микрофон)..." -ForegroundColor Cyan
    if (-not (Test-Path ".venv")) {
        Write-Host "Сначала выполните 1 (Установка)." -ForegroundColor Red
        Pause-Continue; return
    }
    & uv run python scripts/list_audio_devices.py
    $devnum = Read-Host "Номер устройства (Enter  -  в главное меню)"
    if (-not $devnum) { return }
    & uv run python scripts/list_audio_devices.py --set $devnum
    Pause-Continue
}

# ---------------------------------------------------------------------------
# CLI mode (roma-stt.bat install / check / build-whisper / start / stop / ...)
# ---------------------------------------------------------------------------

if ($args.Count -gt 0) {
    $cmd = $args[0]
    switch -Exact ($cmd) {
        "install"        { & uv run python scripts/install.py ($args[1..($args.Length-1)]); exit $LASTEXITCODE }
        "check"          { & uv run python scripts/check_ready.py; exit $LASTEXITCODE }
        "download"       { & uv run python scripts/download_model.py $args[1]; exit $LASTEXITCODE }
        "download-vad"   { & uv run python scripts/download_vad_model.py; exit $LASTEXITCODE }
        "build-whisper"  { & uv run python scripts/build_whisper_cpp.py ($args[1..($args.Length-1)]); exit $LASTEXITCODE }
        "build-check"    { & uv run python scripts/check_build.py; exit $LASTEXITCODE }
        "setup"          { & uv run python scripts/install.py; if ($LASTEXITCODE -eq 0) { & uv run python scripts/check_ready.py }; exit $LASTEXITCODE }
        "test-model"     { & uv run python scripts/test_model.py; exit $LASTEXITCODE }
        "start"          { $m = if ($args[1]) {$args[1]} else {"cpu"}; & uv run python main.py --module $m; exit $LASTEXITCODE }
        "stop"           { Do-Stop; exit 0 }
        "install-tools"  { & "$PSScriptRoot\scripts\install_tools.bat"; exit $LASTEXITCODE }
        default          { Write-Host "Неизвестная команда: $cmd" -ForegroundColor Red; exit 1 }
    }
}

# ---------------------------------------------------------------------------
# Interactive menu loop
# ---------------------------------------------------------------------------

while ($true) {
    Show-Menu
    $choice = Read-Host "Введите цифру (1-10, Enter  -  обновить меню)"
    switch ($choice) {
        "1"  { Do-Install }
        "2"  { Do-Start }
        "3"  { Do-Stop }
        "4"  { Do-Models }
        "5"  { Do-ScanHotkeys }
        "6"  { Do-SetHotkey "record" }
        "7"  { Do-SetHotkey "stop" }
        "8"  { Do-SetLanguage }
        "9"  { Do-SetInputDevice }
        "10" { exit 0 }
        ""   { }  # просто обновить меню
        default { Write-Host "Неизвестный выбор. Введите цифру от 1 до 10." -ForegroundColor Red; Start-Sleep -Seconds 1 }
    }
}
