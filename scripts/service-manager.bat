@echo off
chcp 65001 >nul 2>&1
setlocal

cd /d "%~dp0"

title SS-54 Service Manager

if "%1"=="" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "service-manager.ps1"
) else (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "service-manager.ps1" %*
)

endlocal
