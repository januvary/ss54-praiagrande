param(
    [switch]$Help
)

. "$PSScriptRoot/config.ps1"
. "$PSScriptRoot/utils/helpers.ps1"
. "$PSScriptRoot/modules/runmode.ps1"
. "$PSScriptRoot/modules/process.ps1"

$runMode = Get-RunMode

if ($Help) {
    Write-Host "SS-54 - Iniciar Aplicacao" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Uso: .\start-app.ps1"
    Write-Host ""
    Write-Host "Inicia a aplicacao SS-54 no modo configurado (Servico ou Processo)"
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
        Write-Error "Servico nao encontrado. Execute o deploy novamente."
        exit 1
    }
    
    if ($service.Status -eq "Running") {
        Write-Host "Servico ja esta rodando" -ForegroundColor Green
        exit 0
    }
    
    Write-Host "Iniciando servico..." -ForegroundColor Cyan
    Start-Service -Name "SS54Backend"
    
    Start-Sleep -Seconds 3
    
    $service = Get-Service -Name "SS54Backend"
    if ($service.Status -eq "Running") {
        Write-Host "Servico iniciado com sucesso!" -ForegroundColor Green
        Write-Host "Acesse: http://localhost:8000" -ForegroundColor Gray
    } else {
        Write-Error "Falha ao iniciar servico. Status: $($service.Status)"
        exit 1
    }
} else {
    $status = Get-AppProcessStatus
    
    if ($status.Running) {
        Write-Host "Processo ja esta rodando (PID: $($status.Pid))" -ForegroundColor Green
        exit 0
    }
    
    $appDir = Get-RunModeAppDir
    
    if (-not $appDir) {
        Write-Error "Diretorio da aplicacao nao encontrado. Execute o deploy novamente."
        exit 1
    }
    
    $venvPython = "$appDir\venv\Scripts\python.exe"
    
    if (-not (Test-Path $venvPython)) {
        Write-Error "Python nao encontrado: $venvPython"
        Write-Host "Execute o deploy primeiro." -ForegroundColor Yellow
        exit 1
    }
    
    Write-Host "Iniciando processo..." -ForegroundColor Cyan
    
    if (Start-AppProcess -appDir $appDir -venvPython $venvPython -port 8000) {
        Write-Host "Processo iniciado com sucesso!" -ForegroundColor Green
        Write-Host "Acesse: http://localhost:8000" -ForegroundColor Gray
    } else {
        Write-Error "Falha ao iniciar processo"
        exit 1
    }
}
