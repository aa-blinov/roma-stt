@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0roma-stt.ps1" %*
if %errorlevel% neq 0 pause
