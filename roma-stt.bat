@echo off
REM Интерактивное меню и формулировки (в т.ч. про модели Whisper) — в roma-stt.ps1 рядом с этим файлом.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0roma-stt.ps1" %*
if %errorlevel% neq 0 pause
