#Requires -Version 5.1
<#
.SYNOPSIS
Roma-STT — меню управления
#>

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
$Host.UI.RawUI.WindowTitle = "Roma-STT"
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

function Get-MenuConfig {
    # Одним вызовом Python читаем все нужные для меню значения
    if (-not (Test-Path ".venv")) { return @{ lang = ""; notif = ""; post = ""; model = ""; hkr = ""; hks = "" } }
    $raw = & uv run python -c "from infrastructure.config_repo import load_config; from pathlib import Path; p=Path('config.yaml'); cfg=load_config(p); mp=cfg.get('whisper_model_path',''); model=Path(mp).stem if mp else ''; print(cfg.get('language','ru'), cfg.get('notifications', False), cfg.get('postprocess', True), model, cfg.get('hotkey_record','Ctrl+F2'), cfg.get('hotkey_stop','Ctrl+F3'), sep='|')" 2>$null
    if (-not $raw) { return @{ lang = "ru"; notif = "False"; post = "True"; model = ""; hkr = "Ctrl+F2"; hks = "Ctrl+F3" } }
    $parts = $raw.Trim().Split('|')
    return @{ lang = $parts[0]; notif = $parts[1]; post = $parts[2]; model = $parts[3]; hkr = $parts[4]; hks = $parts[5] }
}

function Show-Menu {
    $cfg = Get-MenuConfig
    $langVal   = if ($cfg.lang)  { $cfg.lang }  else { "?" }
    $notifVal  = if ($cfg.notif -eq "True") { "вкл" } else { "выкл" }
    $postVal   = if ($cfg.post  -eq "False") { "выкл" } else { "вкл" }
    $modelVal  = if ($cfg.model) { $cfg.model -replace '^ggml-','' } else { "?" }
    $hkrVal    = if ($cfg.hkr)  { $cfg.hkr }  else { "?" }
    $hksVal    = if ($cfg.hks)  { $cfg.hks }  else { "?" }

    Clear-Host
    Write-Host ""
    Write-Host " ============================================================" -ForegroundColor DarkGray
    Write-Host "  " -NoNewline
    Write-Host "Roma-STT" -NoNewline -ForegroundColor Cyan
    Write-Host "  -  Speech to Text (голос в текст)"
    Write-Host " ============================================================" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  Введите цифру и нажмите Enter."
    Write-Host "  Первый запуск: 1 -> 2 -> 3" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  " -NoNewline; Write-Host " 1." -NoNewline -ForegroundColor Yellow; Write-Host " Установка"
    Write-Host "     Один раз: uv, Git, CMake, VS Build Tools, среда, модель, whisper.cpp." -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host " 2." -NoNewline -ForegroundColor Yellow; Write-Host " Проверка готовности"
    Write-Host "     Убедиться, что всё установлено. После пункта 1." -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host " 3." -NoNewline -ForegroundColor Yellow; Write-Host " Запустить службу (в трее)"
    Write-Host "     Режим и горячая клавиша из config.yaml." -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host " 4." -NoNewline -ForegroundColor Yellow; Write-Host " Остановить службу"
    Write-Host "     Завершить работу Roma-STT в трее." -ForegroundColor DarkGray
    Write-Host ""
    Write-Host " --- Настройки (применяются после перезапуска: 4 -> 3) ------" -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host " 5." -NoNewline -ForegroundColor Yellow; Write-Host " Модели распознавания       " -NoNewline; Write-Host "[$modelVal]" -ForegroundColor Cyan
    Write-Host "     Список моделей — выбрать или скачать и выбрать." -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host " 6." -NoNewline -ForegroundColor Yellow; Write-Host " Подбор свободной горячей клавиши"
    Write-Host "     Протестировать F-клавиши и записать в config.yaml." -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host " 7." -NoNewline -ForegroundColor Yellow; Write-Host " Горячая клавиша записи     " -NoNewline; Write-Host "[$hkrVal]" -ForegroundColor Cyan
    Write-Host "     Клавиша для начала записи голоса." -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host " 8." -NoNewline -ForegroundColor Yellow; Write-Host " Горячая клавиша стопа      " -NoNewline; Write-Host "[$hksVal]" -ForegroundColor Cyan
    Write-Host "     Клавиша для остановки записи." -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host " 9." -NoNewline -ForegroundColor Yellow; Write-Host " Язык распознавания         " -NoNewline; Write-Host "[$langVal]" -ForegroundColor Cyan
    Write-Host "     Код языка ISO 639-1: ru, en, de, fr, es, it, zh..." -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host "10." -NoNewline -ForegroundColor Yellow; Write-Host " Устройство ввода (микрофон)"
    Write-Host "     Выбрать микрофон из списка устройств." -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host "11." -NoNewline -ForegroundColor Yellow; Write-Host " Удалить установку"
    Write-Host "     Удалить .venv и models — для переустановки с нуля." -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host "12." -NoNewline -ForegroundColor Yellow; Write-Host " Уведомления Windows        " -NoNewline; Write-Host "[$notifVal]" -ForegroundColor Cyan
    Write-Host "     Всплывающие уведомления при вставке текста." -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host "13." -NoNewline -ForegroundColor Yellow; Write-Host " Постобработка текста       " -NoNewline; Write-Host "[$postVal]"  -ForegroundColor Cyan
    Write-Host "     Заглавная буква, точка в конце, удаление артефактов Whisper." -ForegroundColor DarkGray
    Write-Host "  " -NoNewline; Write-Host "14." -NoNewline -ForegroundColor Yellow; Write-Host " Выход"
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
            Write-Host "Пропущено — сборка whisper.cpp может не сработать." -ForegroundColor DarkGray
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
                Write-Host "После установки может потребоваться перезагрузка." -ForegroundColor Yellow
            }
        }
    }

    # Vulkan SDK (только для режима amd)
    if ($arch -eq "amd") {
        if (Get-Command vulkaninfo -ErrorAction SilentlyContinue) {
            Write-Host "Vulkan SDK уже установлен." -ForegroundColor DarkGray
        } else {
            Write-Host ""
            Write-Host "Vulkan SDK нужен для режима amd (~200 МБ)." -ForegroundColor Yellow
            $vulkan = Read-Host "Установить сейчас? (y/N)"
            if ($vulkan -match '^[yYдД]$') {
                & winget install --id KhronosGroup.VulkanSDK --accept-package-agreements --accept-source-agreements
            }
        }
    }

    return $true
}

function Do-Install {
    Write-Host "[1] Установка..." -ForegroundColor Cyan

    # Выбор архитектуры (до установки инструментов — не нужен uv)
    $gpu = Detect-Gpu
    $a = "cpu"
    if ($gpu.NvidiaName -or $gpu.AmdName) {
        Write-Host "   1 = cpu  (без GPU, всегда работает)"
        if ($gpu.NvidiaName) { Write-Host "   2 = cuda ($($gpu.NvidiaName))" -ForegroundColor Yellow }
        if ($gpu.AmdName)    { Write-Host "   3 = amd  ($($gpu.AmdName))"    -ForegroundColor Yellow }
        $hint = "1"
        if ($gpu.NvidiaName) { $hint += "/2" }
        if ($gpu.AmdName)    { $hint += "/3" }
        $arch = Read-Host "Архитектура ($hint, Enter — в главное меню)"
        if (-not $arch) { return }
        if ($arch -eq "2") {
            if (-not $gpu.NvidiaName) { Write-Host "Выбран CUDA, но NVIDIA не обнаружена." -ForegroundColor Red; Pause-Continue; return }
            $a = "cuda"
        } elseif ($arch -eq "3") {
            if (-not $gpu.AmdName) { Write-Host "Выбран AMD, но AMD/Radeon не обнаружена." -ForegroundColor Red; Pause-Continue; return }
            $a = "amd"
        }
    } else {
        Write-Host "  Дискретная видеокарта не обнаружена — будет CPU-режим." -ForegroundColor DarkGray
    }

    # Установка системных инструментов через winget
    Write-Host ""
    Write-Host "Шаг 1/2: Проверка и установка системных инструментов..." -ForegroundColor Cyan
    $ok = Install-Tools $a
    if (-not $ok) { Pause-Continue; return }

    # Проверяем uv после установки (PATH может не обновиться без перезапуска)
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host ""
        Write-Host "uv только что установлен, но PATH ещё не обновился." -ForegroundColor Yellow
        Write-Host "Закройте это окно, откройте снова и снова выберите 1." -ForegroundColor Yellow
        Pause-Continue; return
    }

    # Установка Python-окружения, whisper.cpp, модели
    Write-Host ""
    Write-Host "Шаг 2/2: Установка окружения, сборка whisper [$a], загрузка модели..." -ForegroundColor Cyan
    & uv run python scripts/install.py --arch $a
    Pause-Continue
}

function Do-Check {
    Write-Host "[2] Проверка готовности..." -ForegroundColor Cyan
    & uv run python scripts/check_ready.py
    Pause-Continue
}

function Do-Start {
    Write-Host "[3] Запуск службы..." -ForegroundColor Cyan
    if (-not (Test-Path ".venv")) {
        Write-Host "Сначала выполните 1 (Установка)." -ForegroundColor Red
        Pause-Continue; return
    }
    if (Test-Path ".roma-stt.pid") {
        Write-Host "Служба уже запущена. Для перезапуска сначала остановите её (пункт 4)." -ForegroundColor Red
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
        Write-Host "Ни один бинарник не найден. Сначала выполните 1 (Установка)." -ForegroundColor Red
        Pause-Continue; return
    }

    & uv run python scripts/check_ready.py *>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Проверка готовности не прошла:" -ForegroundColor Red
        & uv run python scripts/check_ready.py
        Write-Host ""
        Write-Host "Сделайте: 1 (Установка), потом 2 (Проверка). Когда в пункте 2 будет OK — снова выберите 3."
        Pause-Continue; return
    }

    $hkr = Get-Config "hotkey_record" "Ctrl+F2"
    $hks = Get-Config "hotkey_stop"   "Ctrl+F3"
    Write-Host "Служба запускается в трее. " -NoNewline -ForegroundColor Green
    Write-Host "Режим: " -NoNewline; Write-Host $mod -NoNewline -ForegroundColor Cyan
    Write-Host ", Запись: " -NoNewline; Write-Host $hkr -NoNewline -ForegroundColor Cyan
    Write-Host ", Стоп: "  -NoNewline; Write-Host $hks -ForegroundColor Cyan
    Write-Host "Остановить: пункт 4. Это окно можно закрыть."
    $pythonw = Join-Path $PSScriptRoot ".venv\Scripts\pythonw.exe"
    Start-Process $pythonw -ArgumentList @("main.py", "--module", $mod) -WorkingDirectory $PSScriptRoot
    Pause-Continue
}

function Do-Stop {
    Write-Host "[4] Остановка Roma-STT..." -ForegroundColor Cyan
    if (Test-Path ".roma-stt.pid") {
        $pidVal = (Get-Content ".roma-stt.pid" -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
        if ($pidVal) { Stop-Process -Id ([int]$pidVal) -Force -ErrorAction SilentlyContinue }
        Remove-Item ".roma-stt.pid" -ErrorAction SilentlyContinue
    } else {
        $pids = & uv run python scripts/find_roma_stt_pids.py 2>$null
        foreach ($p in $pids) {
            $p = $p.Trim()
            if ($p -match '^\d+$') { Stop-Process -Id ([int]$p) -Force -ErrorAction SilentlyContinue }
        }
    }
    Write-Host "Готово." -ForegroundColor Green
    Pause-Continue
}

function Do-Models {
    Write-Host ""
    Write-Host "[5] Модели распознавания" -ForegroundColor Cyan
    if (-not (Test-Path ".venv")) {
        Write-Host "Сначала выполните 1 (Установка)." -ForegroundColor Red
        Pause-Continue; return
    }
    & uv run python scripts/models.py list-all
    $num = Read-Host "Номер (1-8) или название (Enter — в главное меню)"
    if (-not $num) { return }
    & uv run python scripts/models.py use $num
    Pause-Continue
}

function Do-ScanHotkeys {
    Write-Host "[6] Подбор свободной горячей клавиши..." -ForegroundColor Cyan
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
    $label    = if ($isRecord) { "[7] Горячая клавиша записи" } else { "[8] Горячая клавиша стопа" }
    $cfgKey   = if ($isRecord) { "hotkey_record" } else { "hotkey_stop" }
    $default  = if ($isRecord) { "Ctrl+F2" } else { "Ctrl+F3" }
    Write-Host "$label..." -ForegroundColor Cyan
    if (-not (Test-Path ".venv")) {
        Write-Host "Сначала выполните 1 (Установка)." -ForegroundColor Red
        Pause-Continue; return
    }
    $cur = Get-Config $cfgKey $default
    Write-Host "Сейчас: " -NoNewline; Write-Host $cur -ForegroundColor Cyan
    Write-Host "Примеры: Ctrl+F2, Ctrl+Shift+F12. Enter — оставить текущую."
    $new = Read-Host "Введите строку (Enter — оставить $cur)"
    if (-not $new) { return }
    Set-Config $cfgKey $new
    Write-Host "Готово." -ForegroundColor Green
    Write-Host "Перезапустите службу (пункт 4, затем 3), чтобы изменение вступило в силу."
    Pause-Continue
}

function Do-SetLanguage {
    Write-Host "[9] Выбрать язык..." -ForegroundColor Cyan
    $cur = Get-Config "language" "ru"
    Write-Host "Текущий язык: " -NoNewline; Write-Host $cur -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Примеры: ru, en, de, fr, es, it, jp, zh."
    while ($true) {
        $new = Read-Host "Введите код языка (Enter — в главное меню)"
        if (-not $new) { return }
        if ($new -eq "russian") { Write-Host 'Используйте код "ru", а не "russian".' -ForegroundColor Red; continue }
        if ($new -eq "english") { Write-Host 'Используйте код "en", а не "english".' -ForegroundColor Red; continue }
        Set-Config "language" $new
        Write-Host "Язык установлен: $new" -ForegroundColor Green
        Pause-Continue; return
    }
}

function Do-SetInputDevice {
    Write-Host "[10] Устройство ввода (микрофон)..." -ForegroundColor Cyan
    if (-not (Test-Path ".venv")) {
        Write-Host "Сначала выполните 1 (Установка)." -ForegroundColor Red
        Pause-Continue; return
    }
    & uv run python scripts/list_audio_devices.py
    $devnum = Read-Host "Номер устройства (Enter — в главное меню)"
    if (-not $devnum) { return }
    & uv run python scripts/list_audio_devices.py --set $devnum
    Pause-Continue
}

function Do-Remove {
    Write-Host "[11] Удаление установки" -ForegroundColor Cyan
    if (-not (Test-Path ".venv")) {
        Write-Host "Удалять нечего — установка ещё не выполнялась." -ForegroundColor Red
        Pause-Continue; return
    }
    Write-Host "Имеет смысл только если хотите всё удалить и поставить заново. После удаления снова выполните 1."
    $confirm = Read-Host "Удалить .venv и models? (y/N, Enter — в главное меню)"
    if (-not $confirm -or $confirm -notmatch "^[yY]$") { return }
    if (Test-Path ".venv")  { Remove-Item ".venv"  -Recurse -Force }
    if (Test-Path "models") { Remove-Item "models" -Recurse -Force }
    Write-Host "Удалено. Для новой установки снова выберите пункт 1." -ForegroundColor Green
    Pause-Continue
}

function Do-ToggleNotifications {
    Write-Host "[12] Уведомления Windows..." -ForegroundColor Cyan
    if (-not (Test-Path ".venv")) {
        Write-Host "Сначала выполните 1 (Установка)." -ForegroundColor Red
        Pause-Continue; return
    }
    $curVal = Get-Config "notifications" "False"
    $cur = if ($curVal -eq "True") { "включены" } else { "выключены" }
    Write-Host "Сейчас уведомления: " -NoNewline; Write-Host $cur -ForegroundColor Cyan
    & uv run python -c "from infrastructure.config_repo import load_config, save_config; from pathlib import Path; p=Path('config.yaml'); cfg=load_config(p); cfg['notifications']=not cfg.get('notifications', False); save_config(p,cfg)" 2>$null
    $newVal = Get-Config "notifications" "False"
    $new = if ($newVal -eq "True") { "включены" } else { "выключены" }
    Write-Host "Уведомления теперь: $new" -ForegroundColor Green
    Pause-Continue
}

function Do-TogglePostprocess {
    Write-Host "[13] Постобработка текста..." -ForegroundColor Cyan
    if (-not (Test-Path ".venv")) {
        Write-Host "Сначала выполните 1 (Установка)." -ForegroundColor Red
        Pause-Continue; return
    }
    $curVal = Get-Config "postprocess" "True"
    $cur = if ($curVal -ne "False") { "включена" } else { "выключена" }
    Write-Host "Сейчас постобработка: " -NoNewline; Write-Host $cur -ForegroundColor Cyan
    Write-Host "Что делает: заглавная буква, точка в конце, удаление [BLANK_AUDIO] и других артефактов Whisper."
    & uv run python -c "from infrastructure.config_repo import load_config, save_config; from pathlib import Path; p=Path('config.yaml'); cfg=load_config(p); cfg['postprocess']=not cfg.get('postprocess', True); save_config(p,cfg)" 2>$null
    $newVal = Get-Config "postprocess" "True"
    $new = if ($newVal -ne "False") { "включена" } else { "выключена" }
    Write-Host "Постобработка теперь: $new" -ForegroundColor Green
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
    $choice = Read-Host "Введите цифру (1-14, Enter — обновить меню)"
    switch ($choice) {
        "1"  { Do-Install }
        "2"  { Do-Check }
        "3"  { Do-Start }
        "4"  { Do-Stop }
        "5"  { Do-Models }
        "6"  { Do-ScanHotkeys }
        "7"  { Do-SetHotkey "record" }
        "8"  { Do-SetHotkey "stop" }
        "9"  { Do-SetLanguage }
        "10" { Do-SetInputDevice }
        "11" { Do-Remove }
        "12" { Do-ToggleNotifications }
        "13" { Do-TogglePostprocess }
        "14" { exit 0 }
        ""   { }  # просто обновить меню
        default { Write-Host "Неизвестный выбор. Введите цифру от 1 до 14." -ForegroundColor Red; Start-Sleep -Seconds 1 }
    }
}
