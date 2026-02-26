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

    $script:useCloudflare = $false
    Write-Info "Deseja configurar HTTPS com Cloudflare?"
    Write-Info "  [S] Sim - HTTPS gratuito, protecao DDoS, CDN"
    Write-Info "  [N] Nao - HTTP apenas, configuracao manual de DNS"
    $cloudflareChoice = Read-Host "Escolha [N]: "
    $script:useCloudflare = ($cloudflareChoice -eq "S" -or $cloudflareChoice -eq "s" -or $cloudflareChoice -eq "1" -or $cloudflareChoice -eq "sim" -or $cloudflareChoice -eq "Sim" -or $cloudflareChoice -eq "SIM")

    if ($script:useCloudflare) {
        $cloudflareConfig = Show-CloudflareInstructions $publicIP $script:domain $script:useWWW $port
        $script:sslMode = $cloudflareConfig.sslMode
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
        $script:sslMode = "none"
    }

    return @{
        domain = $script:domain
        useWWW = $script:useWWW
        port = $port
        useCloudflare = $script:useCloudflare
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

function Show-CloudflareInstructions($publicIP, $domain, $useWWW, $port) {
    Write-Host ""
    Write-Host "=========================================================" -ForegroundColor $Colors.Header
    Write-Host "CONFIGURACAO HTTPS COM CLOUDFLARE" -ForegroundColor $Colors.Header
    Write-Host "=========================================================" -ForegroundColor $Colors.Header
    Write-Host ""

    $currentPhase = 1
    $totalPhases = 6

    function Show-PhaseBanner {
        param([string]$phaseName)
        Write-Host ""
        Write-Host "----------------------------------------" -ForegroundColor $Colors.Info
        Write-Host "PASSO $($currentPhase)/$($totalPhases): $phaseName" -ForegroundColor $Colors.Success
        Write-Host "----------------------------------------" -ForegroundColor $Colors.Info
        Write-Host ""
    }

    Show-PhaseBanner "Criar conta Cloudflare"

    Write-Host "1. Acesse https://dash.cloudflare.com/sign-up" -ForegroundColor $Colors.Info
    Write-Host "2. Crie uma conta gratuita usando seu email" -ForegroundColor $Colors.Info
    Write-Host "3. Verifique seu email para ativar a conta" -ForegroundColor $Colors.Info
    Write-Host ""
    $null = Read-Host "Pressione Enter apos criar sua conta Cloudflare"

    $currentPhase++
    Show-PhaseBanner "Adicionar site ao Cloudflare"

    Write-Host "1. Faca login em https://dash.cloudflare.com" -ForegroundColor $Colors.Info
    Write-Host "2. Clique em 'Add a Site'" -ForegroundColor $Colors.Info
    Write-Host "3. Digite seu dominio: $domain" -ForegroundColor $Colors.Success
    Write-Host "4. Selecione o plano FREE e clique em 'Continue'" -ForegroundColor $Colors.Info
    Write-Host ""
    $null = Read-Host "Pressione Enter apos adicionar o site"

    $currentPhase++
    Show-PhaseBanner "Atualizar nameservers no registro.br"

    Write-Host "Cloudflare mostrara dois nameservers, por exemplo:" -ForegroundColor $Colors.Info
    Write-Host "  - lana.ns.cloudflare.com" -ForegroundColor $Colors.Warning
    Write-Host "  - mark.ns.cloudflare.com" -ForegroundColor $Colors.Warning
    Write-Host ""
    Write-Host "1. Faca login em https://www.registro.br" -ForegroundColor $Colors.Info
    Write-Host "2. Acesse o painel de dominios" -ForegroundColor $Colors.Info
    Write-Host "3. Clique em '$domain'" -ForegroundColor $Colors.Info
    Write-Host "4. Vá em 'Servidores DNS' ou 'Nameservers'" -ForegroundColor $Colors.Info
    Write-Host "5. Altere os nameservers para os fornecidos pelo Cloudflare" -ForegroundColor $Colors.Info
    Write-Host "6. Salve as alteracoes" -ForegroundColor $Colors.Info
    Write-Host ""
    Write-Warning "IMPORTANTE: Esta alteracao pode levar de 24h a 48h para propagar"
    Write-Warning "Apos a propagacao, Cloudflare sera o provedor de DNS do seu dominio"
    Write-Host ""
    $null = Read-Host "Pressione Enter apos atualizar os nameservers"

    $currentPhase++
    Show-PhaseBanner "Configurar registros DNS no Cloudflare"

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
    if ($useWWW) {
        Write-Host "  B) Registro para www:" -ForegroundColor $Colors.Header
        Write-Host "     - Type: CNAME" -ForegroundColor $Colors.Warning
        Write-Host "     - Name: www" -ForegroundColor $Colors.Warning
        Write-Host "     - Target: $domain" -ForegroundColor $Colors.Success
        Write-Host "     - Proxy status: Proxied (tela laranja)" -ForegroundColor $Colors.Warning
        Write-Host "     - TTL: Auto" -ForegroundColor $Colors.Warning
        Write-Host ""
    }
    $null = Read-Host "Pressione Enter apos configurar os registros"

    $currentPhase++
    Show-PhaseBanner "Configurar registros MX para Gmail"

    Write-Host "Como voce usa Gmail, configure estes registros MX:" -ForegroundColor $Colors.Info
    Write-Host ""
    Write-Host "1. Ainda na aba 'DNS' do Cloudflare" -ForegroundColor $Colors.Info
    Write-Host "2. Clique em 'Add Record' para cada registro:" -ForegroundColor $Colors.Info
    Write-Host ""
    Write-Host "  Registro MX 1:" -ForegroundColor $Colors.Header
    Write-Host "     - Type: MX" -ForegroundColor $Colors.Warning
    Write-Host "     - Name: @" -ForegroundColor $Colors.Warning
    Write-Host "     - Mail server: ASPMX.L.GOOGLE.COM" -ForegroundColor $Colors.Success
    Write-Host "     - Priority: 1" -ForegroundColor $Colors.Warning
    Write-Host "     - Proxy status: DNS only (tela cinza)" -ForegroundColor $Colors.Warning
    Write-Host ""
    Write-Host "  Registro MX 2:" -ForegroundColor $Colors.Header
    Write-Host "     - Type: MX" -ForegroundColor $Colors.Warning
    Write-Host "     - Name: @" -ForegroundColor $Colors.Warning
    Write-Host "     - Mail server: ALT1.ASPMX.L.GOOGLE.COM" -ForegroundColor $Colors.Success
    Write-Host "     - Priority: 5" -ForegroundColor $Colors.Warning
    Write-Host "     - Proxy status: DNS only (tela cinza)" -ForegroundColor $Colors.Warning
    Write-Host ""
    Write-Host "  Registro MX 3:" -ForegroundColor $Colors.Header
    Write-Host "     - Type: MX" -ForegroundColor $Colors.Warning
    Write-Host "     - Name: @" -ForegroundColor $Colors.Warning
    Write-Host "     - Mail server: ALT2.ASPMX.L.GOOGLE.COM" -ForegroundColor $Colors.Success
    Write-Host "     - Priority: 5" -ForegroundColor $Colors.Warning
    Write-Host "     - Proxy status: DNS only (tela cinza)" -ForegroundColor $Colors.Warning
    Write-Host ""
    Write-Host "  Registro MX 4:" -ForegroundColor $Colors.Header
    Write-Host "     - Type: MX" -ForegroundColor $Colors.Warning
    Write-Host "     - Name: @" -ForegroundColor $Colors.Warning
    Write-Host "     - Mail server: ALT3.ASPMX.L.GOOGLE.COM" -ForegroundColor $Colors.Success
    Write-Host "     - Priority: 10" -ForegroundColor $Colors.Warning
    Write-Host "     - Proxy status: DNS only (tela cinza)" -ForegroundColor $Colors.Warning
    Write-Host ""
    Write-Host "  Registro MX 5:" -ForegroundColor $Colors.Header
    Write-Host "     - Type: MX" -ForegroundColor $Colors.Warning
    Write-Host "     - Name: @" -ForegroundColor $Colors.Warning
    Write-Host "     - Mail server: ALT4.ASPMX.L.GOOGLE.COM" -ForegroundColor $Colors.Success
    Write-Host "     - Priority: 10" -ForegroundColor $Colors.Warning
    Write-Host "     - Proxy status: DNS only (tela cinza)" -ForegroundColor $Colors.Warning
    Write-Host ""
    Write-Host "  Registro TXT para SPF:" -ForegroundColor $Colors.Header
    Write-Host "     - Type: TXT" -ForegroundColor $Colors.Warning
    Write-Host "     - Name: @" -ForegroundColor $Colors.Warning
    Write-Host "     - Content: v=spf1 include:_spf.google.com ~all" -ForegroundColor $Colors.Success
    Write-Host "     - Proxy status: DNS only (tela cinza)" -ForegroundColor $Colors.Warning
    Write-Host ""
    $null = Read-Host "Pressione Enter apos configurar os registros MX"

    $currentPhase++
    Show-PhaseBanner "Configurar SSL/TLS"

    Write-Host "1. No painel do Cloudflare, clique na aba 'SSL/TLS'" -ForegroundColor $Colors.Info
    Write-Host "2. Configure o modo SSL/TLS:" -ForegroundColor $Colors.Info
    Write-Host ""
    Write-Host "  Opcoes disponiveis:" -ForegroundColor $Colors.Header
    Write-Host "  [F] Flexible - Recomendado (Cloudflare -> usuario = HTTPS)" -ForegroundColor $Colors.Success
    Write-Host "  [O] Full - Cloudflare -> servidor = HTTPS" -ForegroundColor $Colors.Warning
    Write-Host "  [S] Strict - Full + validacao de certificado" -ForegroundColor $Colors.Warning
    Write-Host ""
    Write-Host "  Flexible:" -ForegroundColor Gray
    Write-Host "    - Mais facil de configurar" -ForegroundColor Gray
    Write-Host "    - Servidor nao precisa de certificado SSL" -ForegroundColor Gray
    Write-Host "    - Conexao entre usuario e Cloudflare e criptografada" -ForegroundColor Gray
    Write-Host "    - Conexao entre Cloudflare e servidor e HTTP" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Full:" -ForegroundColor Gray
    Write-Host "    - Servidor precisa de certificado SSL" -ForegroundColor Gray
    Write-Host "    - Ambas conexoes sao criptografadas" -ForegroundColor Gray
    Write-Host "    - Cloudflare nao valida o certificado" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Strict:" -ForegroundColor Gray
    Write-Host "    - Como Full, mas valida o certificado" -ForegroundColor Gray
    Write-Host "    - Mais seguro, mas requer configuracao correta" -ForegroundColor Gray
    Write-Host ""
    $sslModeChoice = Read-Host "Escolha o modo SSL/TLS [F]: "
    
    $sslMode = "flexible"
    if ($sslModeChoice -eq "O" -or $sslModeChoice -eq "o" -or $sslModeChoice -eq "full") {
        $sslMode = "full"
    } elseif ($sslModeChoice -eq "S" -or $sslModeChoice -eq "s" -or $sslModeChoice -eq "strict") {
        $sslMode = "strict"
    }

    Write-Success "Modo SSL/TLS selecionado: $sslMode"
    Write-Host ""
    $null = Read-Host "Pressione Enter apos configurar o SSL/TLS"

    Write-Host ""
    Write-Host "=========================================================" -ForegroundColor $Colors.Header
    Write-Host "RESUMO DA CONFIGURACAO CLOUDFLARE" -ForegroundColor $Colors.Header
    Write-Host "=========================================================" -ForegroundColor $Colors.Header
    Write-Host ""
    Write-Host "Dominio: $domain" -ForegroundColor $Colors.Success
    Write-Host "IP do servidor: $publicIP" -ForegroundColor $Colors.Success
    Write-Host "Modo SSL/TLS: $sslMode" -ForegroundColor $Colors.Success
    Write-Host ""
    Write-Host "Registros DNS configurados:" -ForegroundColor $Colors.Info
    Write-Host "  - A Record: @ -> $publicIP (Proxied)" -ForegroundColor $Colors.Warning
    if ($useWWW) {
        Write-Host "  - CNAME: www -> $domain (Proxied)" -ForegroundColor $Colors.Warning
    }
    Write-Host "  - MX Records: Configurados para Gmail" -ForegroundColor $Colors.Warning
    Write-Host "  - TXT SPF: Configurado" -ForegroundColor $Colors.Warning
    Write-Host ""
    Write-Host "Apos a propagacao dos nameservers:" -ForegroundColor $Colors.Info
    Write-Host "  - Acesse: https://$domain" -ForegroundColor $Colors.Success
    if ($useWWW) {
        Write-Host "  - Acesse: https://www.$domain" -ForegroundColor $Colors.Success
    }
    Write-Host ""

    if ($sslMode -eq "flexible") {
        Write-Host "Observacoes:" -ForegroundColor $Colors.Info
        Write-Host "  - Servidor continua usando HTTP na porta configurada" -ForegroundColor Gray
        Write-Host "  - Cloudflare lida com o HTTPS automaticamente" -ForegroundColor Gray
        Write-Host "  - Nenhuma configuracao adicional necessaria no servidor" -ForegroundColor Gray
        $portDisplay = if ($port -eq 80) { "80 (HTTP)" } else { "$port (HTTP)" }
        Write-Host "  - Firewall: Apenas porta $portDisplay precisa estar aberta" -ForegroundColor Gray
    } else {
        Write-Host "Observacoes:" -ForegroundColor $Colors.Info
        Write-Host "  - Servidor precisa de certificado SSL configurado" -ForegroundColor Gray
        Write-Host "  - Considere usar certbot para gerar certificado Let's Encrypt" -ForegroundColor Gray
        $portDisplay = if ($port -eq 80) { "80 (HTTP)" } else { "$port (HTTP)" }
        Write-Host "  - Firewall: Portas $portDisplay e 443 (HTTPS) precisam estar abertas" -ForegroundColor Gray
    }
    Write-Host ""

    Write-Host "Comandos uteis:" -ForegroundColor $Colors.Info
    Write-Host "  nslookup $domain" -ForegroundColor $Colors.Success
    Write-Host "  dig $domain" -ForegroundColor $Colors.Success
    Write-Host ""
    
    Write-Host "Para configurar firewall (se necessario):" -ForegroundColor $Colors.Info
    Write-Host "  netsh advfirewall firewall add rule name=`"SS54 HTTP`" dir=in action=allow protocol=TCP localport=$port" -ForegroundColor $Colors.Success
    Write-Host ""

    $null = Read-Host "Pressione Enter para continuar com a instalacao"
    Write-Host ""

    return @{
        sslMode = $sslMode
    }
}

