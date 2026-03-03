param(
    [switch]$Help
)

. "$PSScriptRoot/config.ps1"
. "$PSScriptRoot/utils/helpers.ps1"
. "$PSScriptRoot/modules/runmode.ps1"
. "$PSScriptRoot/modules/process.ps1"

$runMode = Get-RunMode

if ($Help) {
    Write-Host "SS-54 - Parar Aplicacao" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Uso: .\stop-app.ps1"
    Write-Host ""
    Write-Host "Para a aplicacao SS-54 no modo configurado (Servico ou Processo)"
    exit 0
}

if (-not $runMode) {
    Write-Error "Aplicacao nao configurada. Execute o script de deploy primeiro."
    Write-Host "  .\deploy.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host "Modo: $runMode" -ForegroundColor Cyan

if ($runMode -eq "service") {
    $service = Get-Service -Name "SS54Backend" -ErrorAction SilentlyContinue
    
    if (-not $service) {
        Write-Error "Servico nao encontrado."
        exit 1
    }
    
    if ($service.Status -eq "Stopped") {
        Write-Host "Servico ja esta parado" -ForegroundColor Green
        exit 0
    }
    
    Write-Host "Parando servico..." -ForegroundColor Cyan
    Stop-Service -Name "SS54Backend" -Force
    
    Start-Sleep -Seconds 3
    
    $service = Get-Service -Name "SS54Backend"
    if ($service.Status -eq "Stopped") {
        Write-Host "Servico parado com sucesso!" -ForegroundColor Green
    } else {
        Write-Error "Falha ao parar servico. Status: $($service.Status)"
        exit 1
    }
} else {
    $status = Get-AppProcessStatus
    
    if (-not $status.Running) {
        Write-Host "Processo ja esta parado" -ForegroundColor Green
        exit 0
    }
    
    Write-Host "Parando processo (PID: $($status.Pid))..." -ForegroundColor Cyan
    
    if (Stop-AppProcess) {
        Write-Host "Processo parado com sucesso!" -ForegroundColor Green
    } else {
        Write-Error "Falha ao parar processo"
        exit 1
    }
}
