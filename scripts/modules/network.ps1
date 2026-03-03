function Get-NetworkConfiguration {
    Write-Info "Detectando seu IP publico..."
    try {
        $publicIP = (Invoke-WebRequest -Uri 'https://api.ipify.org?format=json' -UseBasicParsing -TimeoutSec 10 | ConvertFrom-Json).ip
        Write-Success "IP Publico: $publicIP"
    } catch {
        Write-Error "Nao foi possivel detectar IP publico"
        $publicIP = "NAO DETECTADO"
    }

    Write-Info "Detectando IPs locais..."
    $localIPs = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne '127.0.0.1' }
    if ($localIPs.Count -eq 0) {
        Write-Warning "Nenhum IP local detectado (alem de localhost)"
        $localIPs = @()
    } else {
        foreach ($ip in $localIPs) {
            Write-Success "  IP Local: $($ip.IPAddress) ($($ip.InterfaceAlias))"
        }
    }

    return @{
        publicIP = $publicIP
        localIPs = $localIPs
    }
}

function Configure-Domain($publicIP, $existingDomain, $port = 8000) {
    Write-Info "Configurando DNS para dominio..."

    $script:defaultDomain = if ($existingDomain) { $existingDomain } else { "ss54pg.com.br" }
    $domainPrompt = if ($existingDomain) { "[$existingDomain]" } else { "ss54pg.com.br" }
    $domainInput = Read-Host "Confirme o dominio ou digite novo $domainPrompt"
    if ([string]::IsNullOrWhiteSpace($domainInput)) {
        $script:domain = $script:defaultDomain
    } else {
        $script:domain = $domainInput.Trim()
    }

    Write-Info "Dominio configurado: $script:domain"

    $script:useWWW = $false
    Write-Info "Deseja configurar subdominio 'www'?"
    Write-Info "  1) Sim - www.$($script:domain) tambem funcionara"
    Write-Info "  2) Nao - Apenas $($script:domain) funcionara"
    $wwwChoice = Read-Host "Escolha [1]: "
    $script:useWWW = ($wwwChoice -eq "1" -or $wwwChoice -eq "")

    Write-Host ""
    Write-Host "=========================================================" -ForegroundColor $Colors.Header
    Write-Host "CONFIGURACAO DE DNS NECESSARIA" -ForegroundColor $Colors.Header
    Write-Host "=========================================================" -ForegroundColor $Colors.Header
    Write-Host ""
    Write-Host "No seu provedor de dominio (GoDaddy, Namecheap, etc.):" -ForegroundColor $Colors.Info
    Write-Host ""
    Write-Host "1. Acesse o painel de gerenciamento de DNS" -ForegroundColor $Colors.Info
    Write-Host "2. Crie os seguintes registros:" -ForegroundColor $Colors.Info
    Write-Host ""
    Write-Host "  Tipo: A Record" -ForegroundColor $Colors.Header
    Write-Host "  Nome: @" -ForegroundColor $Colors.Header
    Write-Host "  Valor: $publicIP" -ForegroundColor $Colors.Success
    Write-Host "  TTL: 300" -ForegroundColor $Colors.Header
    Write-Host ""
    if ($script:useWWW) {
        Write-Host "  Tipo: A Record" -ForegroundColor $Colors.Header
        Write-Host "  Nome: www" -ForegroundColor $Colors.Header
        Write-Host "  Valor: $publicIP" -ForegroundColor $Colors.Success
        Write-Host "  TTL: 300" -ForegroundColor $Colors.Header
        Write-Host ""
    }

    Write-Host ""
    Write-Host "Como deseja expor sua aplicacao externamente?" -ForegroundColor $Colors.Header
    Write-Host ""
    Write-Host "  [1] Cloudflare DNS (Tradicional)" -ForegroundColor $Colors.Success
    Write-Host "      - Muda nameservers para Cloudflare" -ForegroundColor Gray
    Write-Host "      - Requer IP publico + encaminhamento de porta" -ForegroundColor Gray
    Write-Host "      - HTTPS gratuito, protecao DDoS, CDN" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  [2] Cloudflare Tunnel (Moderno - Recomendado)" -ForegroundColor $Colors.Success
    Write-Host "      - Sem configuracao de rede/IP publico" -ForegroundColor Gray
    Write-Host "      - HTTPS automatico e mais seguro" -ForegroundColor Gray
    Write-Host "      - Instala cloudflared automaticamente" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  [3] DNS Manual" -ForegroundColor $Colors.Warning
    Write-Host "      - Voce configura DNS no seu provedor" -ForegroundColor Gray
    Write-Host "      - Apenas HTTP (sem HTTPS)" -ForegroundColor Gray
    Write-Host ""

    $externalAccess = Read-Host "Escolha [2]: "
    
    $script:useCloudflare = $false
    $script:useTunnel = $false
    $script:sslMode = "none"
    
    if ($externalAccess -eq "1") {
        $script:useCloudflare = $true
        Write-Host ""
        Write-Host "=========================================================" -ForegroundColor $Colors.Header
        Write-Host "CONFIGURACAO HTTPS COM CLOUDFLARE" -ForegroundColor $Colors.Header
        Write-Host "=========================================================" -ForegroundColor $Colors.Header
        Write-Host ""
        Write-Host "IP do servidor: $publicIP" -ForegroundColor $Colors.Success
        Write-Host ""

        $currentPhase = 1
        $totalPhases = 4

        Write-Host "PASSO 1/$($totalPhases): Adicionar site ao Cloudflare" -ForegroundColor $Colors.Info
        Write-Host "----------------------------------------" -ForegroundColor $Colors.Info
        Write-Host "1. Faca login em https://dash.cloudflare.com" -ForegroundColor $Colors.Info
        Write-Host "2. Clique em 'Add a Site'" -ForegroundColor $Colors.Info
        Write-Host "3. Digite seu dominio: $script:domain" -ForegroundColor $Colors.Success
        Write-Host "4. Selecione o plano FREE e clique em 'Continue'" -ForegroundColor $Colors.Info
        Write-Host ""
        $null = Read-Host "Pressione Enter apos adicionar o site"

        $currentPhase++
        Write-Host ""
        Write-Host "PASSO 2/$($totalPhases): Atualizar nameservers no registro.br" -ForegroundColor $Colors.Info
        Write-Host "----------------------------------------" -ForegroundColor $Colors.Info
        Write-Host "Cloudflare mostrara dois nameservers, por exemplo:" -ForegroundColor $Colors.Info
        Write-Host "  - lana.ns.cloudflare.com" -ForegroundColor $Colors.Warning
        Write-Host "  - mark.ns.cloudflare.com" -ForegroundColor $Colors.Warning
        Write-Host ""
        Write-Host "1. Faca login em https://www.registro.br" -ForegroundColor $Colors.Info
        Write-Host "2. Acesse o painel de dominios" -ForegroundColor $Colors.Info
        Write-Host "3. Clique em '$script:domain'" -ForegroundColor $Colors.Info
        Write-Host "4. Vá em 'Servidores DNS' ou 'Nameservers'" -ForegroundColor $Colors.Info
        Write-Host "5. Altere os nameservers para os fornecidos pelo Cloudflare" -ForegroundColor $Colors.Info
        Write-Host "6. Salve as alteracoes" -ForegroundColor $Colors.Info
        Write-Host ""
        Write-Warning "Esta alteracao pode levar de 24h a 48h para propagar"
        Write-Host ""
        $null = Read-Host "Pressione Enter apos atualizar os nameservers"

        $currentPhase++
        Write-Host ""
        Write-Host "PASSO 3/$($totalPhases): Configurar registros DNS no Cloudflare" -ForegroundColor $Colors.Info
        Write-Host "----------------------------------------" -ForegroundColor $Colors.Info
        Write-Host "1. No painel do Cloudflare, clique na aba 'DNS'" -ForegroundColor $Colors.Info
        Write-Host "2. Clique em 'Add Record'" -ForegroundColor $Colors.Info
        Write-Host "3. Adicione os seguintes registros:" -ForegroundColor $Colors.Info
        Write-Host ""
        Write-Host "  A) Registro para o dominio principal:" -ForegroundColor $Colors.Header
        Write-Host "     - Type: A" -ForegroundColor $Colors.Warning
        Write-Host "     - Name: @" -ForegroundColor $Colors.Warning
        Write-Host "     - IPv4 address: $publicIP" -ForegroundColor $Colors.Success
        Write-Host "     - Proxy status: Proxied (tela laranja)" -ForegroundColor $Colors.Warning
        Write-Host "     - TTL: Auto" -ForegroundColor $Colors.Warning
        Write-Host ""
        if ($script:useWWW) {
            Write-Host "  B) Registro para www:" -ForegroundColor $Colors.Header
            Write-Host "     - Type: CNAME" -ForegroundColor $Colors.Warning
            Write-Host "     - Name: www" -ForegroundColor $Colors.Warning
            Write-Host "     - Target: $script:domain" -ForegroundColor $Colors.Success
            Write-Host "     - Proxy status: Proxied (tela laranja)" -ForegroundColor $Colors.Warning
            Write-Host "     - TTL: Auto" -ForegroundColor $Colors.Warning
            Write-Host ""
        }
        $null = Read-Host "Pressione Enter apos configurar os registros"

        $currentPhase++
        Write-Host ""
        Write-Host "PASSO 4/$($totalPhases): Configurar SSL/TLS" -ForegroundColor $Colors.Info
        Write-Host "----------------------------------------" -ForegroundColor $Colors.Info
        Write-Host "1. No painel do Cloudflare, clique na aba 'SSL/TLS'" -ForegroundColor $Colors.Info
        Write-Host "2. Configure o modo SSL/TLS:" -ForegroundColor $Colors.Info
        Write-Host ""
        Write-Host "  [F] Flexible - Recomendado (Cloudflare -> usuario = HTTPS)" -ForegroundColor $Colors.Success
        Write-Host "  [O] Full - Cloudflare -> servidor = HTTPS" -ForegroundColor $Colors.Warning
        Write-Host "  [S] Strict - Full + validacao de certificado" -ForegroundColor $Colors.Warning
        Write-Host ""
        $sslModeChoice = Read-Host "Escolha o modo SSL/TLS [F]: "
        
        $script:sslMode = "flexible"
        if ($sslModeChoice -eq "O" -or $sslModeChoice -eq "o" -or $sslModeChoice -eq "full") {
            $script:sslMode = "full"
        } elseif ($sslModeChoice -eq "S" -or $sslModeChoice -eq "s" -or $sslModeChoice -eq "strict") {
            $script:sslMode = "strict"
        }

        Write-Success "Modo SSL/TLS selecionado: $script:sslMode"
        Write-Host ""
        Write-Host "=========================================================" -ForegroundColor $Colors.Header
        Write-Host "RESUMO DA CONFIGURACAO CLOUDFLARE" -ForegroundColor $Colors.Header
        Write-Host "=========================================================" -ForegroundColor $Colors.Header
        Write-Host ""
        Write-Host "Dominio: $script:domain" -ForegroundColor $Colors.Success
        Write-Host "IP do servidor: $publicIP" -ForegroundColor $Colors.Success
        Write-Host "Modo SSL/TLS: $script:sslMode" -ForegroundColor $Colors.Success
        Write-Host ""
        Write-Host "Apos a propagacao dos nameservers:" -ForegroundColor $Colors.Info
        Write-Host "  - Acesse: https://$script:domain" -ForegroundColor $Colors.Success
        if ($script:useWWW) {
            Write-Host "  - Acesse: https://www.$script:domain" -ForegroundColor $Colors.Success
        }
        Write-Host ""

    } elseif ($externalAccess -eq "2") {
        $script:useTunnel = $true
        $script:sslMode = "flexible"
        Write-Host ""
        Write-Host "=========================================================" -ForegroundColor $Colors.Header
        Write-Host "CLOUDFLARE TUNNEL" -ForegroundColor $Colors.Header
        Write-Host "=========================================================" -ForegroundColor $Colors.Header
        Write-Host ""
        Write-Host "Cloudflare Tunnel sera configurado automaticamente:" -ForegroundColor $Colors.Info
        Write-Host "  - Sem necessidade de IP publico ou firewall" -ForegroundColor $Colors.Success
        Write-Host "  - HTTPS automatico e gratuito" -ForegroundColor $Colors.Success
        Write-Host "  - Instalara cloudflared e criara tunnel" -ForegroundColor $Colors.Success
        Write-Host "  - DNS sera configurado automaticamente para: $script:domain" -ForegroundColor $Colors.Success
        Write-Host ""

    } else {
        Write-Host "3. Salve as alteracoes" -ForegroundColor $Colors.Info
        Write-Host "4. Aguarde a propagacao DNS (pode levar ate 24h)" -ForegroundColor $Colors.Warning
        Write-Host ""
        Write-Host "Apos configurar DNS, o sistema estara acessivel em:" -ForegroundColor $Colors.Info

        $urlPort = if ($port -eq 80) { "" } else { ":$port" }

        if ($script:useWWW) {
            Write-Host "  * http://$($script:domain)$($urlPort)/" -ForegroundColor $Colors.Success
            Write-Host "  * http://www.$($script:domain)$($urlPort)/" -ForegroundColor $Colors.Success
        } else {
            Write-Host "  * http://$($script:domain)$($urlPort)/" -ForegroundColor $Colors.Success
        }
        Write-Host ""
        Write-Host "Encaminhamento de portas no roteador:" -ForegroundColor $Colors.Info
        Write-Host "  - Configure encaminhamento da porta $port para este servidor" -ForegroundColor $Colors.Info
        Write-Host "  - Use UPnP se o roteador suportar" -ForegroundColor $Colors.Info
        Write-Host ""

        Write-Host ""
        $null = Read-Host "Pressione Enter para continuar"
        Write-Host ""
    }

    return @{
        domain = $script:domain
        useWWW = $script:useWWW
        port = $port
        useCloudflare = $script:useCloudflare
        useTunnel = $script:useTunnel
        sslMode = $script:sslMode
    }
}

function Configure-Port() {
    Write-Info "Configurando porta da aplicacao..."
    Write-Host ""
    Write-Host "Opcoes de porta:" -ForegroundColor $Colors.Info
    Write-Host "  [1] Porta 8000 (Padrao - Nao requer administrador)" -ForegroundColor $Colors.Success
    Write-Host "  [2] Porta 80 (Mais amigavel - Requer executar como administrador)" -ForegroundColor $Colors.Warning
    Write-Host "  [3] Porta customizada" -ForegroundColor $Colors.Info
    Write-Host ""
    Write-Host "Notas:" -ForegroundColor $Colors.Info
    Write-Host "  - Porta 8000: URL sera http://dominio.com:8000 (menos amigavel)" -ForegroundColor Gray
    Write-Host "  - Porta 80: URL sera http://dominio.com (mais amigavel, padrao HTTP)" -ForegroundColor Gray
    Write-Host "  - Portas abaixo de 1024 podem requerer configuracao adicional" -ForegroundColor Gray
    Write-Host ""

    $portChoice = Read-Host "Escolha uma opcao [1]: "
    $port = 8000

    if ($portChoice -eq "2" -or $portChoice -eq "80") {
        $port = 80
    } elseif ($portChoice -eq "3") {
        $customPort = Read-Host "Digite a porta desejada (1024-65535)"
        if ($customPort -match '^\d+$' -and [int]$customPort -ge 1024 -and [int]$customPort -le 65535) {
            $port = [int]$customPort
            if ($port -lt 1024) {
                Write-Warning "Portas abaixo de 1024 requerem administrador!"
            }
        } else {
            Write-Warning "Porta invalida. Usando porta 8000."
            $port = 8000
        }
    } else {
        $port = 8000
    }

    Write-Success "Porta configurada: $port"
    Write-Host ""

    return $port
}

