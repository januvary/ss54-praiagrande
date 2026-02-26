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
. "$PSScriptRoot/modules/verification.ps1"

Write-Section "SCRIPT DE DEPLOY - SS-54 BACKEND v$ScriptVersion"

$installDir = $DefaultInstallDir
$appDir = "$installDir\ss54-praiagrande"
$venvPython = "$appDir\venv\Scripts\python.exe"

$useWWW = $false
$domain = "ss54pg.com.br"
$publicIP = "NAO DETECTADO"
$localIPs = @()
$dbConfig = @{}
$appPort = 8000
$useCloudflare = $false
$sslMode = "none"

Write-Section "FASE 1/8: VALIDACAO DO AMBIENTE"

$envResult = Test-EnvironmentRequirements
$pythonInstalled = $envResult.pythonInstalled
$pythonCmd = $envResult.pythonCmd
$postgresInstalled = $envResult.postgresInstalled
$postgresBinPath = $envResult.postgresBinPath
$psqlCmd = $envResult.psqlCmd
$gitInstalled = $envResult.gitInstalled
$cppInstalled = $envResult.cppInstalled

Write-Success "Fase 1 concluida: Ambiente validado"

Write-Section "FASE 2/8: CONFIGURACAO DE REDE"

$netConfig = Get-NetworkConfiguration
$publicIP = $netConfig.publicIP
$localIPs = $netConfig.localIPs

$appPort = Configure-Port

$domainConfig = Configure-Domain $publicIP $null $appPort
$domain = $domainConfig.domain
$useWWW = $domainConfig.useWWW
$useCloudflare = $domainConfig.useCloudflare
$sslMode = $domainConfig.sslMode

Write-Success "Fase 2 concluida: Rede configurada"

Pause-Continue

Write-Section "FASE 3/8: CONFIGURACAO DO BANCO DE DADOS"

$dbConfig = Initialize-Database $psqlCmd $DefaultInstallDir
if ($dbConfig.keptExisting) {
    Write-Warning "Banco de dados existente mantido. Dados preservados."
}
Write-Success "Fase 3 concluida: Banco de dados configurado"

Pause-Continue

Write-Section "FASE 4/8: DEPLOY DA APLICACAO"

Deploy-Application $installDir $appDir $GitRepo $pythonCmd $venvPython
Write-Success "Fase 4 concluida: Aplicacao implantada"

Pause-Continue

Write-Section "FASE 5/8: CONFIGURACAO DA APLICACAO"

Create-ApplicationConfig $appDir $installDir $domain $useWWW $dbConfig.password $venvPython $localIPs $publicIP $appPort
Write-Success "Fase 5 concluida: Aplicacao configurada"

Pause-Continue

Write-Section "FASE 6/8: MIGRACAO DO BANCO DE DADOS"

Run-DatabaseMigration $appDir $venvPython $psqlCmd
Write-Success "Fase 6 concluida: Banco de dados migrado"

Write-Section "FASE 7/8: CONFIGURACAO DO SERVICO WINDOWS"

Configure-WindowsService $appDir $venvPython $installDir $appPort
Write-Success "Fase 7 concluida: Servico Windows configurado"

Write-Section "FASE 8/8: VERIFICACAO FINAL"

Verify-Deployment $installDir $appDir $domain $useWWW $publicIP $localIPs $appPort

Write-Section "RESUMO FINAL"

Write-Host "Banco de dados:" -ForegroundColor $Colors.Info
if ($dbConfig.keptExisting) {
    Write-Host "  * Banco de dados existente mantido (dados preservados)" -ForegroundColor $Colors.Success
} else {
    Write-Host "  * Banco de dados criado/resetado (dados novos)" -ForegroundColor $Colors.Success
}

Write-Host ""
Write-Host "HTTPS/Cloudflare:" -ForegroundColor $Colors.Info
if ($useCloudflare) {
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
}

Write-Host ""
Write-Host "Arquivos importantes:" -ForegroundColor $Colors.Info
Write-Host "  * $appDir\.env - Configuracao da aplicacao" -ForegroundColor $Colors.Success
Write-Host "  * $installDir\db-credentials.txt - Credenciais do banco" -ForegroundColor $Colors.Success
Write-Host "  * $installDir\deployment-summary.txt - Resumo do deploy" -ForegroundColor $Colors.Success

Write-Host ""
Write-Host "Para gerenciar o servico:" -ForegroundColor $Colors.Info
Write-Host "  nssm stop SS54Backend   # Parar" -ForegroundColor $Colors.Success
Write-Host "  nssm start SS54Backend  # Iniciar" -ForegroundColor $Colors.Success
Write-Host "  nssm restart SS54Backend # Reiniciar" -ForegroundColor $Colors.Success
Write-Host "  nssm status SS54Backend  # Verificar" -ForegroundColor $Colors.Success

Write-Host ""
Write-Host "Logs:" -ForegroundColor $Colors.Info
Write-Host "  $installDir\logs\" -ForegroundColor $Colors.Success

Stop-Script 0
