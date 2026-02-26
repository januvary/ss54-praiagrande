function Configure-WindowsService {
    param(
        [string]$appDir,
        [string]$venvPython,
        [string]$installDir,
        [int]$port = 8000
    )

    Write-Info "Configurando gerenciador de servico..."
    $nssmDir = "C:\nssm"
    $nssmExe = "$nssmDir\nssm.exe"
    $useNssm = $false

    $nssmUrls = @(
        "https://nssm.cc/release/nssm-2.24.zip",
        "https://web.archive.org/web/2023/https://nssm.cc/release/nssm-2.24.zip"
    )

    if (Test-Path $nssmExe) {
        Write-Success "NSSM ja instalado"
        $useNssm = $true
    } else {
        foreach ($url in $nssmUrls) {
            try {
                New-Item -ItemType Directory -Path $nssmDir -Force | Out-Null
                $nssmZip = "$env:TEMP\nssm-2.24.zip"

                Write-Info "Tentando baixar NSSM..."
                Invoke-WebRequest -Uri $url -OutFile $nssmZip -UseBasicParsing -TimeoutSec 30

                Write-Info "Extraindo NSSM..."
                Expand-Archive -Path $nssmZip -DestinationPath $nssmDir -Force

                $nssmFound = Get-ChildItem -Path $nssmDir -Recurse -Filter "nssm.exe" | Select-Object -First 1
                if ($nssmFound) {
                    Copy-Item $nssmFound.FullName $nssmExe -Force
                    $useNssm = $true
                    Write-Success "NSSM instalado"
                    break
                }
            } catch {
                Write-Warning "Falha ao baixar de $url"
            }
        }
    }

    Write-Info "Instalando servico Windows: SS54Backend..."

    $existingService = Get-Service -Name SS54Backend -ErrorAction SilentlyContinue
    if ($existingService) {
        Write-Info "Removendo servico existente..."
        Stop-Service -Name SS54Backend -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2

        try {
            & sc.exe delete SS54Backend 2>&1 | Out-Null
        } catch {
            Write-Warning "Falha ao remover servico antigo (pode ja ter sido removido)"
        }
        Start-Sleep -Seconds 2
    }

    if ($useNssm) {
        try {
            & $nssmExe install SS54Backend $venvPython 2>&1 | Out-Null
            & $nssmExe set SS54Backend AppParameters "-m app.main" 2>&1 | Out-Null
            & $nssmExe set SS54Backend AppDirectory $appDir 2>&1 | Out-Null
            & $nssmExe set SS54Backend DisplayName "SS-54 Backend Service" 2>&1 | Out-Null
            & $nssmExe set SS54Backend Description "SS-54 Sistema de Assistencia Farmaceutica" 2>&1 | Out-Null
            & $nssmExe set SS54Backend Start SERVICE_AUTO_START 2>&1 | Out-Null
            & $nssmExe set SS54Backend AppRestartDelay 10000 2>&1 | Out-Null
            & $nssmExe set SS54Backend AppStdout "$installDir\logs\service-stdout.log" 2>&1 | Out-Null
            & $nssmExe set SS54Backend AppStderr "$installDir\logs\service-stderr.log" 2>&1 | Out-Null
            $envString = "PYTHONUNBUFFERED=1`nPYTHONIOENCODING=utf-8"
            & $nssmExe set SS54Backend AppEnvironmentExtra $envString 2>&1 | Out-Null
            & $nssmExe set SS54Backend AppThrottle 15000 2>&1 | Out-Null
            & $nssmExe set SS54Backend AppRestart 1 2>&1 | Out-Null
            & $nssmExe set SS54Backend AppExit Default Restart 2>&1 | Out-Null
            & $nssmExe set SS54Backend AppExit 0 Restart 2>&1 | Out-Null
            & $nssmExe set SS54Backend AppExit 1 Restart 2>&1 | Out-Null
            & $nssmExe set SS54Backend AppExit 2 Restart 2>&1 | Out-Null
            Write-Success "Servico instalado via NSSM"
        } catch {
            Write-Warning "Falha ao configurar via NSSM, usando metodo alternativo"
            $useNssm = $false
        }
    }

    if ($useNssm) {
        try {
            & sc.exe failure SS54Backend reset= 86400 actions= restart/10000/restart/30000/restart/60000 2>&1 | Out-Null
            Write-Success "Politicas de reinicio configuradas (indefinidas com backoff)"
        } catch {
            Write-Warning "Falha ao configurar politicas de falha"
        }
    }

    if (-not $useNssm) {
        Write-Info "Usando metodo nativo do Windows..."

        $wrapperBat = "$installDir\start-service.bat"
        Set-Content -Path $wrapperBat -Value @"
@echo off
cd /d $appDir
"$venvPython" -m app.main
"@

        try {
            & sc.exe create SS54Backend binPath= "$wrapperBat" start= auto DisplayName= "SS-54 Backend Service" 2>&1 | Out-Null
            & sc.exe description SS54Backend "SS-54 Sistema de Assistencia Farmaceutica" 2>&1 | Out-Null
            & sc.exe failure SS54Backend reset= 86400 actions= restart/10000/restart/30000/restart/60000 2>&1 | Out-Null
            Write-Success "Servico instalado via sc.exe"
            Write-Success "Politicas de reinicio configuradas (indefinidas com backoff)"
        } catch {
            Write-Error "Falha ao instalar servico: $_"
            Stop-Script 1
        }
    }

    Write-Info "Configurando Firewall do Windows..."

     try {
         Remove-NetFirewallRule -DisplayName "SS-54 Backend" -ErrorAction SilentlyContinue
         New-NetFirewallRule -DisplayName "SS-54 Backend" -Direction Inbound -Protocol TCP -LocalPort $port -Action Allow -ErrorAction Stop
         Write-Success "Regra de firewall criada: SS-54 Backend (Porta $($port)/TCP)"
     } catch {
        Write-Warning "Falha ao configurar firewall (pode ja existir): $_"
    }

    Write-Info "Iniciando servico: SS54Backend..."

    try {
        if ($useNssm) {
            & $nssmExe start SS54Backend 2>&1 | Out-Null
        } else {
            Start-Service -Name SS54Backend 2>&1 | Out-Null
        }
        Start-Sleep -Seconds 5

        $service = Get-Service -Name SS54Backend -ErrorAction SilentlyContinue
        if ($service.Status -eq "Running") {
            Write-Success "Servico iniciado com sucesso!"
        } else {
            Write-Error "Servico nao iniciou. Status: $($service.Status)"
            Write-Info "Verifique os logs em: $installDir\logs\"
            Stop-Script 1
        }
    } catch {
        Write-Error "Falha ao iniciar servico: $_"
        Stop-Script 1
    }
}

