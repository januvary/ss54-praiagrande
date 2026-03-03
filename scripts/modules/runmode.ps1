$RunModeFile = Join-Path $env:USERPROFILE "ss54\runmode.txt"
$RunModeServiceFile = "C:\ss54\runmode.txt"
$AppDirFile = Join-Path $env:USERPROFILE "ss54\appdir.txt"

function Get-RunMode {
    $serviceExists = $null -ne (Get-Service -Name "SS54Backend" -ErrorAction SilentlyContinue)
    
    # Check for service mode file first
    if (Test-Path $RunModeServiceFile) {
        return "service"
    }
    
    # Check for process mode file
    if (Test-Path $RunModeFile) {
        $mode = (Get-Content $RunModeFile -Raw).Trim()
        if ($mode -eq "service" -or $mode -eq "process") {
            return $mode
        }
    }
    
    return $null
}

function Test-RunModeConfigured {
    $mode = Get-RunMode
    return $null -ne $mode
}

function Get-RunModeAppDir {
    $mode = Get-RunMode

    switch ($mode) {
        "service" {
            # Service mode uses appdir.txt in C:\ss54\
            if (Test-Path $RunModeServiceFile) {
                $serviceAppDir = Join-Path $env:USERPROFILE "ss54\appdir.txt"
                if (Test-Path $serviceAppDir) {
                    return (Get-Content $serviceAppDir -Raw).Trim()
                }
            }
            return "C:\ss54\ss54-praiagrande"
        }
        "process" {
            # Process mode uses appdir.txt in user profile
            if (Test-Path $AppDirFile) {
                return (Get-Content $AppDirFile -Raw).Trim()
            }
            return Join-Path $env:USERPROFILE "ss54\ss54-praiagrande"
        }
        default {
            return $null
        }
    }
}

function Get-RunModeInstallDir {
    $appDir = Get-RunModeAppDir
    if ($appDir) {
        return Split-Path $appDir -Parent
    }
    return $null
}

function Select-RunMode {
    param(
        [bool]$isAdmin
    )

    Write-Host ""
    Write-Host "  MODO DE EXECUCAO" -ForegroundColor Cyan
    Write-Host "  ================" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  [1] Servico Windows" -ForegroundColor White
    Write-Host "      - Inicia automaticamente com o Windows" -ForegroundColor Gray
    Write-Host "      - Reinicia automaticamente se travar" -ForegroundColor Gray
    Write-Host "      - Roda em segundo plano (mesmo deslogado)" -ForegroundColor Gray
    if (-not $isAdmin) {
        Write-Host "      - REQUER EXECUTAR COMO ADMINISTRADOR" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "  [2] Processo" -ForegroundColor White
    Write-Host "      - NAO requer administrador" -ForegroundColor Gray
    Write-Host "      - Pode iniciar automaticamente ao logar" -ForegroundColor Gray
    Write-Host "      - Mais simples de configurar" -ForegroundColor Gray
    Write-Host "      - Precisa estar logado para rodar" -ForegroundColor Gray
    Write-Host ""

    $choice = Read-Host "  Selecione o modo [1 ou 2]"

    switch ($choice) {
        "1" {
            if (-not $isAdmin) {
                Write-Host ""
                Write-Warning "Modo Servico requer privilegios de administrador!"
                Write-Host ""
                Write-Host "  Opcoes:" -ForegroundColor Yellow
                Write-Host "  [R] Executar como administrador" -ForegroundColor White
                Write-Host "  [2] Usar modo Processo (sem admin)" -ForegroundColor White
                Write-Host "  [C] Cancelar" -ForegroundColor White
                Write-Host ""

                $retry = Read-Host "  Escolha"
                switch -Regex ($retry) {
                    "^[Rr]$" { return "retry_admin" }
                    "^[2]$" { return "process" }
                    default { return "cancel" }
                }
            }
            return "service"
        }
        "2" {
            return "process"
        }
        default {
            Write-Warning "Opcao invalida"
            return $null
        }
    }
}

function Set-RunMode {
    param(
        [ValidateSet("service", "process")]
        [string]$Mode,
        [string]$AppDir
    )

    # Ensure directory for runmode.txt exists
    $runModeDir = Split-Path $RunModeFile -Parent
    if (-not (Test-Path $runModeDir)) {
        New-Item -ItemType Directory -Path $runModeDir -Force | Out-Null
    }

    # Write mode to runmode.txt (always in user profile)
    Set-Content -Path $RunModeFile -Value $Mode -NoNewline

    # Determine correct appDir file location
    $appDirFile = if ($Mode -eq "service") {
        $RunModeServiceFile
    } else {
        $AppDirFile
    }
    
    # Ensure directory exists
    $modeDir = Split-Path $appDirFile -Parent
    if (-not (Test-Path $modeDir)) {
        New-Item -ItemType Directory -Path $modeDir -Force | Out-Null
    }

    # Write appDir to correct file
    Set-Content -Path $appDirFile -Value $AppDir -NoNewline

    Write-Success "Modo definido: $Mode"
    return $true
}

function Write-RunModeSummary {
    param(
        [string]$Mode,
        [int]$Port = 8000
    )

    Write-Host ""
    Write-Host "  MODO: $Mode" -ForegroundColor Cyan
    Write-Host "  " -NoNewline

    switch ($Mode) {
        "service" {
            Write-Host "Gerenciado via Windows Service (NSSM)" -ForegroundColor Gray
            Write-Host ""
            Write-Host "  Comandos:" -ForegroundColor White
            Write-Host "    nssm start SS54Backend" -ForegroundColor Gray
            Write-Host "    nssm stop SS54Backend" -ForegroundColor Gray
            Write-Host "    nssm restart SS54Backend" -ForegroundColor Gray
            Write-Host "    nssm status SS54Backend" -ForegroundColor Gray
        }
        "process" {
            Write-Host "Gerenciado via scripts PowerShell" -ForegroundColor Gray
            Write-Host ""
            Write-Host "  Comandos:" -ForegroundColor White
            Write-Host "    start-app.ps1  # Iniciar" -ForegroundColor Gray
            Write-Host "    stop-app.ps1   # Parar" -ForegroundColor Gray

            if (Test-ProcessInStartup) {
                Write-Host ""
                Write-Host "  Auto-inicio: ATIVADO" -ForegroundColor Green
            }
        }
    }

    Write-Host ""
    Write-Host "  Porta: $Port" -ForegroundColor White
    Write-Host "  Acesso local: http://localhost:$Port" -ForegroundColor Gray
}
