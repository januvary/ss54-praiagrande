. "$PSScriptRoot/config.ps1"
. "$PSScriptRoot/utils/helpers.ps1"

. "$PSScriptRoot/modules/logging.ps1"
. "$PSScriptRoot/modules/environment.ps1"
. "$PSScriptRoot/modules/network.ps1"
. "$PSScriptRoot/modules/database.ps1"
. "$PSScriptRoot/modules/application.ps1"
. "$PSScriptRoot/modules/configuration.ps1"
. "$PSScriptRoot/modules/migration.ps1"
. "$PSScriptRoot/modules/service.ps1"
. "$PSScriptRoot/modules/process.ps1"
. "$PSScriptRoot/modules/runmode.ps1"
. "$PSScriptRoot/modules/verification.ps1"
. "$PSScriptRoot/modules/cloudflare-tunnel.ps1"

Write-Section "SCRIPT DE DEPLOY - SS-54 BACKEND v$ScriptVersion"

$useWWW = $false
$domain = "ss54pg.com.br"
$publicIP = "NAO DETECTADO"
$localIPs = @()
$dbConfig = @{}
$appPort = 8000
$useCloudflare = $false
$useTunnel = $false
$sslMode = "none"
$subdomain = ""
$tunnelStarted = $false
$runMode = $null
$isAdmin = $false
$installDir = $null
$appDir = $null
$venvPython = $null

Write-Section "FASE 1/9: VALIDACAO DO AMBIENTE"

$envResult = Test-EnvironmentRequirements
$pythonInstalled = $envResult.pythonInstalled
$pythonCmd = $envResult.pythonCmd
$postgresInstalled = $envResult.postgresInstalled
$postgresBinPath = $envResult.postgresBinPath
$psqlCmd = $envResult.psqlCmd
$gitInstalled = $envResult.gitInstalled
$cppInstalled = $envResult.cppInstalled
$isAdmin = $envResult.isAdmin

Write-Success "Fase 1 concluida: Ambiente validado"

Write-Section "FASE 2/9: SELECAO DO MODO DE EXECUCAO"

$runMode = Select-RunMode -isAdmin $isAdmin

if ($null -eq $runMode -or $runMode -eq "cancel") {
    Write-Info "Deploy cancelado pelo usuario."
    Stop-Script 0
}

if ($runMode -eq "retry_admin") {
    Write-Info "Reinicie o script como Administrador para usar o modo Servico."
    Write-Info "Ou execute novamente e escolha o modo Processo."
    Stop-Script 0
}

if ($runMode -eq "service") {
    $installDir = $DefaultInstallDir
    Write-Info "Modo Servico selecionado - Instalando em: $installDir"
} else {
    $installDir = Join-Path $env:USERPROFILE "ss54"
    Write-Info "Modo Processo selecionado - Instalando em: $installDir"
}

$appDir = Join-Path $installDir "ss54-praiagrande"
$venvPython = Join-Path $appDir "venv\Scripts\python.exe"

Set-RunMode -Mode $runMode -AppDir $appDir
Write-Success "Fase 2 concluida: Modo definido como '$runMode'"

Pause-Continue

Write-Section "FASE 3/9: CONFIGURACAO DE REDE"

$netConfig = Get-NetworkConfiguration
$publicIP = $netConfig.publicIP
$localIPs = $netConfig.localIPs

$appPort = Configure-Port

$domainConfig = Configure-Domain $publicIP $null $appPort
$domain = $domainConfig.domain
$useWWW = $domainConfig.useWWW
$useCloudflare = $domainConfig.useCloudflare
$useTunnel = $domainConfig.useTunnel
$sslMode = $domainConfig.sslMode

if ($useTunnel) {
    $subdomain = ""
    Write-Host ""
    Write-Host "=========================================================" -ForegroundColor $Colors.Header
    Write-Host "CLOUDFLARE TUNNEL" -ForegroundColor $Colors.Header
    Write-Host "=========================================================" -ForegroundColor $Colors.Header
    Write-Host ""
    $subdomain = Read-Host "Subdominio (deixe vazio para dominio raiz)"
    
    if (Initialize-CloudflareTunnel -Port $appPort -Domain $domain -Subdomain $subdomain) {
        Write-Success "Cloudflare Tunnel configurado com sucesso"
        
        $startTunnel = Read-Host "Iniciar tunnel agora? (s/n)"
        if ($startTunnel -eq 's') {
            if (Start-CloudflareTunnel -Port $appPort -Domain $domain -Subdomain $subdomain) {
                $tunnelStarted = $true
                Write-Success "Tunnel iniciado"
            } else {
                Write-Warning "Falha ao iniciar tunnel. Inicie manualmente apos o deploy."
            }
        }
    } else {
        Write-Warning "Falha ao configurar Cloudflare Tunnel. Continuando sem tunnel."
        Write-Info "Configure manualmente: .\scripts\cloudflare\setup.ps1"
        $useTunnel = $false
    }
}

Write-Success "Fase 3 concluida: Rede configurada"

Pause-Continue

Write-Section "FASE 4/9: CONFIGURACAO DO BANCO DE DADOS"

$dbConfig = Initialize-Database $psqlCmd $installDir
if ($dbConfig.keptExisting) {
    Write-Warning "Banco de dados existente mantido. Dados preservados."
}
Write-Success "Fase 4 concluida: Banco de dados configurado"

Pause-Continue

Write-Section "FASE 5/9: DEPLOY DA APLICACAO"

Deploy-Application $installDir $appDir $GitRepo $pythonCmd $venvPython
Write-Success "Fase 5 concluida: Aplicacao implantada"

Pause-Continue

Write-Section "FASE 6/9: CONFIGURACAO DA APLICACAO"

Create-ApplicationConfig $appDir $installDir $domain $useWWW $dbConfig.password $venvPython $localIPs $publicIP $appPort
Write-Success "Fase 6 concluida: Aplicacao configurada"

Pause-Continue

Write-Section "FASE 7/9: MIGRACAO DO BANCO DE DADOS"

Run-DatabaseMigration $appDir $venvPython $psqlCmd
Write-Success "Fase 7 concluida: Banco de dados migrado"

Write-Section "FASE 8/9: CONFIGURACAO DO SERVICO/PROCESSO"

if ($runMode -eq "service") {
    Configure-WindowsService $appDir $venvPython $installDir $appPort
    Write-Success "Servico Windows configurado"
} else {
    Initialize-ProcessMode $appDir $venvPython $appPort
    Write-Success "Modo Processo configurado"
    
    $addToStartup = Read-Host "Adicionar a inicializacao do Windows? (s/n)"
    if ($addToStartup -eq 's') {
        Add-ProcessToStartup -appDir $appDir -scriptDir $PSScriptRoot
    }
    
    $startNow = Read-Host "Iniciar aplicacao agora? (s/n)"
    if ($startNow -eq 's') {
        Start-AppProcess -appDir $appDir -venvPython $venvPython -port $appPort
    }
}

Write-Success "Fase 8 concluida: Aplicacao configurada"

Write-Section "FASE 9/9: VERIFICACAO FINAL"

Verify-Deployment $installDir $appDir $domain $useWWW $publicIP $localIPs $appPort

Write-Section "RESUMO FINAL"

Write-Host "Modo de execucao:" -ForegroundColor $Colors.Info
if ($runMode -eq "service") {
    Write-Host "  * Servico Windows (requer admin)" -ForegroundColor $Colors.Success
    Write-Host "  * Auto-inicio: Sim (com o Windows)" -ForegroundColor $Colors.Success
    Write-Host "  * Auto-restart: Sim (se travar)" -ForegroundColor $Colors.Success
} else {
    Write-Host "  * Processo (sem admin)" -ForegroundColor $Colors.Success
    $inStartup = Test-ProcessInStartup
    if ($inStartup) {
        Write-Host "  * Auto-inicio: Sim (ao logar)" -ForegroundColor $Colors.Success
    } else {
        Write-Host "  * Auto-inicio: Nao (manual)" -ForegroundColor $Colors.Warning
    }
    Write-Host "  * Auto-restart: Nao" -ForegroundColor $Colors.Warning
}

Write-Host ""
Write-Host "Banco de dados:" -ForegroundColor $Colors.Info
if ($dbConfig.keptExisting) {
    Write-Host "  * Banco de dados existente mantido (dados preservados)" -ForegroundColor $Colors.Success
} else {
    Write-Host "  * Banco de dados criado/resetado (dados novos)" -ForegroundColor $Colors.Success
}

Write-Host ""
Write-Host "HTTPS/Cloudflare:" -ForegroundColor $Colors.Info
if ($useTunnel) {
    $hostname = if ($subdomain) { "$subdomain.$domain" } else { $domain }
    Write-Host "  * Cloudflare Tunnel configurado" -ForegroundColor $Colors.Success
    Write-Host "  * HTTPS automatico via Cloudflare" -ForegroundColor $Colors.Success
    Write-Host "  * Aplicacao acessivel apenas via tunnel (mais seguro)" -ForegroundColor $Colors.Success
    Write-Host "  * Acesse: https://$hostname" -ForegroundColor $Colors.Success
    if ($useWWW) {
        Write-Host "  * Acesse: https://www.$hostname" -ForegroundColor $Colors.Success
    }
    if ($tunnelStarted) {
        Write-Host "  * Status: Tunnel em execucao" -ForegroundColor $Colors.Success
    } else {
        Write-Host "  * Status: Tunnel nao iniciado" -ForegroundColor $Colors.Warning
        Write-Host "  * Inicie: .\scripts\cloudflare\start-tunnel.ps1" -ForegroundColor $Colors.Warning
    }
} elseif ($useCloudflare) {
    Write-Host "  * Cloudflare configurado (HTTPS gratuito)" -ForegroundColor $Colors.Success
    Write-Host "  * Modo SSL/TLS: $sslMode" -ForegroundColor $Colors.Success
    if ($sslMode -eq "flexible") {
        Write-Host "  * Acesse: https://$domain" -ForegroundColor $Colors.Warning
        if ($useWWW) {
            Write-Host "  * Acesse: https://www.$domain" -ForegroundColor $Colors.Warning
        }
    } else {
        Write-Host "  * Certificado SSL necessario no servidor" -ForegroundColor $Colors.Warning
        Write-Host "  * Configure SSL antes de acessar via HTTPS" -ForegroundColor $Colors.Warning
    }
} else {
    Write-Host "  * Configuracao manual de DNS" -ForegroundColor $Colors.Warning
    $urlPort = if ($appPort -eq 80) { "" } else { ":$appPort" }
    Write-Host "  * Acesse: http://$domain$urlPort" -ForegroundColor $Colors.Warning
    if ($useWWW) {
        Write-Host "  * Acesse: http://www.$domain$urlPort" -ForegroundColor $Colors.Warning
    }
    Write-Host "  * Recomendacao: Configure Cloudflare Tunnel para HTTPS" -ForegroundColor $Colors.Info
    Write-Host "    Veja: .\scripts\cloudflare\README.md" -ForegroundColor $Colors.Info
}

Write-Host ""
Write-Host "Arquivos importantes:" -ForegroundColor $Colors.Info
Write-Host "  * $appDir\.env - Configuracao da aplicacao" -ForegroundColor $Colors.Success
Write-Host "  * $installDir\db-credentials.txt - Credenciais do banco" -ForegroundColor $Colors.Success
Write-Host "  * $installDir\deployment-summary.txt - Resumo do deploy" -ForegroundColor $Colors.Success

Write-Host ""
Write-Host "Para gerenciar a aplicacao:" -ForegroundColor $Colors.Info

if ($runMode -eq "service") {
    Write-Host "  nssm stop SS54Backend   # Parar" -ForegroundColor $Colors.Success
    Write-Host "  nssm start SS54Backend  # Iniciar" -ForegroundColor $Colors.Success
    Write-Host "  nssm restart SS54Backend # Reiniciar" -ForegroundColor $Colors.Success
    Write-Host "  nssm status SS54Backend  # Verificar" -ForegroundColor $Colors.Success
} else {
    Write-Host "  .\scripts\start-app.ps1  # Iniciar" -ForegroundColor $Colors.Success
    Write-Host "  .\scripts\stop-app.ps1   # Parar" -ForegroundColor $Colors.Success
}

if ($useTunnel) {
    Write-Host ""
    Write-Host "Para gerenciar o Cloudflare Tunnel:" -ForegroundColor $Colors.Info
    Write-Host "  .\scripts\cloudflare\status.ps1      # Verificar status" -ForegroundColor $Colors.Success
    Write-Host "  .\scripts\cloudflare\start-tunnel.ps1   # Iniciar tunnel" -ForegroundColor $Colors.Success
    Write-Host "  .\scripts\cloudflare\stop-tunnel.ps1    # Parar tunnel" -ForegroundColor $Colors.Success
}

Write-Host ""
Write-Host "Logs:" -ForegroundColor $Colors.Info
Write-Host "  $installDir\logs\" -ForegroundColor $Colors.Success

Stop-Script 0
