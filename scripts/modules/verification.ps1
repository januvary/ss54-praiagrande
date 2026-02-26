function Verify-Deployment {
    param(
        [string]$installDir,
        [string]$appDir,
        [string]$domain,
        [bool]$useWWW,
        [string]$publicIP,
        $localIPs,
        [int]$port = 8000
    )

    Write-Section "VERIFICACAO FINAL"

    $maxRetries = 10
    $retryCount = 0
    $success = $false

    while ($retryCount -lt $maxRetries -and -not $success) {
        $retryCount++
        Write-Info "Verificando endpoint de saude (tentativa $retryCount/$maxRetries)..."

        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$($port)/api/health" -Method Get -TimeoutSec 10 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                $success = $true
                Write-Success "Verificacao de saude concluida com sucesso!"
            }
        } catch {
            Write-Info "Aguardando o servico iniciar..."
            Start-Sleep -Seconds 3
        }
    }

    if (-not $success) {
        Write-Error "Verificacao de saude falhou apos $maxRetries tentativas"
        Stop-Script
    }

    Write-Section "CRIANDO SCRIPT DE VERIFICACAO DE SAUDE"

    $healthCheckScript = @"
# Script de Verificacao de Saude para Deploy SS54
# Execute este script para verificar a saude da deploy

Write-Host "`n=== VERIFICACAO DE SAUDE SS54 ===" -ForegroundColor Cyan
Write-Host "Verificando endpoint de saude..." -ForegroundColor Yellow

 try {
     `$response = Invoke-WebRequest -Uri "http://localhost:$($port)/api/health" -Method Get -TimeoutSec 10 -UseBasicParsing
     if (`$response.StatusCode -eq 200) {
        Write-Host "✓ Verificacao de saude passou!" -ForegroundColor Green
        `$content = `$response.Content | ConvertFrom-Json
        Write-Host "Status: `$(`$content.status)" -ForegroundColor Green
        Write-Host "Timestamp: `$(`$content.timestamp)" -ForegroundColor Green
        if (`$content.version) {
            Write-Host "Versao: `$(`$content.version)" -ForegroundColor Green
        }
    } else {
        Write-Host "✗ Verificacao de saude falhou com codigo de status: `$(`$response.StatusCode)" -ForegroundColor Red
    }
}
catch {
    Write-Host "✗ Verificacao de saude falhou: `$(`$_.Exception.Message)" -ForegroundColor Red
    Write-Host "Certifique-se de que o servico esta em execucao: nssm start SS54Backend" -ForegroundColor Yellow
}

Write-Host "`nStatus do servico:" -ForegroundColor Cyan
nssm status SS54Backend

Write-Host "`n" -NoNewline
"@

    $healthCheckPath = Join-Path $installDir "health-check.ps1"
    $healthCheckScript | Out-File -FilePath $healthCheckPath -Encoding UTF8
    Write-Success "Script de verificacao de saude criado: $healthCheckPath"

    Write-Section "CRIANDO RESUMO DA DEPLOYMENT"

     $wwwPrefix = if ($useWWW) { "www." } else { "" }
     $domainUrl = if ($domain) { "https://${wwwPrefix}$domain" } else { "Nao configurado" }
     $localUrl = "http://localhost:$($port)"
     $internalUrl = if ($localIPs.Count -gt 0) { "http://$($localIPs[0]):$($port)" } else { $localUrl }
     $publicUrl = if ($publicIP) { "http://${publicIP}:$($port)" } else { "Nao configurado (requer encaminhamento de porta)" }

    $summary = @"
================================================================================
                    SS54 PRAIA GRANDE - RESUMO DA DEPLOYMENT
================================================================================
Data: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Diretorio de Instalacao: $installDir
Diretorio da Aplicacao: $appDir
================================================================================

URLS DE ACESSO
--------------------------------------------------------------------------------
Acesso Local:        $localUrl
Rede Interna:        $internalUrl
Acesso Publico:      $publicUrl
URL de Dominio:      $domainUrl

================================================================================

PROXIMOS PASSOS
--------------------------------------------------------------------------------

1. CONFIGURACAO DNS
   - Configure os registros DNS do seu dominio para apontar para seu IP publico ($publicIP)
   - Adicione um registro 'A' para: $domain
   $(if ($useWWW) { "- Adicione um registro 'CNAME' para: www.$domain" })

 2. ENCAMINHAMENTO DE PORTA (se acessando de rede externa)
   - Encaminhe a porta $($port) do seu roteador para esta maquina
   - Use o IP interno: $($localIPs[0])

3. CERTIFICADO SSL
   - SSL esta configurado para acesso ao dominio
   - O certificado sera obtido automaticamente via Let's Encrypt
   - Certifique-se de que a porta 80 esteja acessivel para validacao do dominio

4. TESTES
   - Execute: .\health-check.ps1
   - Acesse a aplicacao usando as URLs acima
   - Teste todos os recursos e funcionalidades

================================================================================

GERENCIAMENTO DO SERVICO
--------------------------------------------------------------------------------

Iniciar o servico:
    nssm start SS54Backend

Parar o servico:
    nssm stop SS54Backend

Reiniciar o servico:
    nssm restart SS54Backend

Verificar status do servico:
    nssm status SS54Backend

Ver logs do servico:
    nssm get SS54Backend AppStdout
    nssm get SS54Backend AppStderr

Ou ver arquivos de log:
    Get-Content $appDir\logs\*.log -Tail 50 -Wait

================================================================================

LOCALIZACAO DOS LOGS
--------------------------------------------------------------------------------
Logs da Aplicacao:   $appDir\logs\
Logs do Servico:     $appDir\logs\
Logs do Nginx:       $installDir\nginx\logs\
Logs do Sistema:     Visualizador de Eventos do Windows

================================================================================

ARQUIVOS IMPORTANTES
--------------------------------------------------------------------------------
Configuracao:        $appDir\.env
Config do Servico:   nssm get SS54Backend
Config do Nginx:     $installDir\nginx\conf\nginx.conf
Verificacao de Saude: $healthCheckPath
Este Resumo:         $installDir\deployment-summary.txt

================================================================================

AVISOS DE SEGURANCA
--------------------------------------------------------------------------------

? NOTAS DE SEGURANCA IMPORTANTES:

1. Credenciais Padrao:
   - Altere as senhas padrao imediatamente
   - Use senhas fortes e unicas

 2. Seguranca de Rede:
   - Configure as regras de firewall adequadamente
   - Exponha apenas as portas necessarias ($($port), 443)
   - Considere usar uma VPN para acesso remoto

3. SSL/TLS:
   - Certifique-se de que os certificados SSL sao validos e atualizados
   - Redirecione HTTP para HTTPS quando possivel

4. Atualizacoes Regulares:
   - Mantenha a aplicacao e dependencias atualizadas
   - Aplique patches de seguranca prontamente

5. Backup:
   - Backups regulares de configuracao e dados
   - Teste os procedimentos de restauracao de backup

6. Monitoramento:
   - Monitore os logs por atividades suspeitas
   - Configure alertas para falhas criticas

================================================================================

INFORMACOES DE SUPORTE
--------------------------------------------------------------------------------

Para problemas ou duvidas:
- Verifique os logs em $appDir\logs\
- Execute verificacao de saude: .\health-check.ps1
- Revise este resumo da deployment

Problemas comuns:
- Servico nao iniciando: Verifique logs e status nssm
- Nao e possivel acessar externamente: Verifique encaminhamento de porta
- Erros de certificado: Verifique DNS do dominio e acesso a porta 80

================================================================================

Deployment concluida com sucesso!
Use as informacoes acima para gerenciar e acessar sua instancia SS54 Praia Grande.

================================================================================
"@

    $summaryPath = Join-Path $installDir "deployment-summary.txt"
    $summary | Out-File -FilePath $summaryPath -Encoding UTF8

    Write-Section "RESUMO DA DEPLOYMENT"

    Write-Info "URLs de Acesso:"
    Write-Info "  Local:        $localUrl"
    Write-Info "  Interno:      $internalUrl"
    Write-Info "  Publico:      $publicUrl"
    Write-Info "  Dominio:      $domainUrl"

    Write-Info "`nGerenciamento do Servico:"
    Write-Info "  Iniciar:   nssm start SS54Backend"
    Write-Info "  Parar:     nssm stop SS54Backend"
    Write-Info "  Reiniciar: nssm restart SS54Backend"
    Write-Info "  Status:    nssm status SS54Backend"

    Write-Info "`nArquivos Importantes:"
    Write-Info "  Resumo:           $summaryPath"
    Write-Info "  Verificacao de Saude: $healthCheckPath"
    Write-Info "  Logs:             $appDir\logs\"
    Write-Info "  Config:           $appDir\.env"

    Write-Success "Resumo completo da deployment salvo em: $summaryPath"

    $openBrowser = Read-Host "`nGostaria de abrir o aplicativo no navegador? (s/n)"
    if ($openBrowser -eq 's' -or $openBrowser -eq 'S') {
        Start-Process $localUrl
        Write-Success "Abrindo navegador..."
    }

    Write-Section "COMANDOS DE GERENCIAMENTO"

    Write-Info "Para gerenciar o servico, use estes comandos:"
    Write-Info ""
    Write-Info "  nssm start SS54Backend        - Iniciar o servico"
    Write-Info "  nssm stop SS54Backend         - Parar o servico"
    Write-Info "  nssm restart SS54Backend      - Reiniciar o servico"
    Write-Info "  nssm status SS54Backend       - Verificar status do servico"
    Write-Info "  nssm remove SS54Backend       - Remover o servico"
    Write-Info ""
    Write-Info "Para ver logs:"
    Write-Info "  Get-Content $appDir\logs\*.log -Tail 50 -Wait"
    Write-Info ""
    Write-Info "Para verificar saude:"
    Write-Info "  .\health-check.ps1"

    Write-Section "VERIFICACAO CONCLUIDA"

    Write-Success "Deployment verificada com sucesso!"
}

