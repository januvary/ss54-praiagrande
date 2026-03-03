@echo off
chcp 65001 >nul
echo.
echo Este script iniciara o PowerShell para executar o deploy.ps1
echo.
pause
echo.
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy.ps1"
if %errorlevel% equ 0 (
    echo.
    echo Deploy concluido com sucesso!
) else (
    echo.
    echo Ocorreu um erro durante o deploy. Codigo: %errorlevel%
)
echo.
pause