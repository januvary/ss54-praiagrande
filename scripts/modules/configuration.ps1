function Create-ApplicationConfig {
    param(
        [string]$appDir,
        [string]$installDir,
        [string]$domain,
        [bool]$useWWW,
        [string]$ss54Password,
        [string]$venvPython,
        $localIPs,
        [string]$publicIP,
        [int]$port = 8000
    )

    $dbUser = "ss54_user"

    Write-Info "Usando configuracao de banco fornecida:"
    Write-Info "  Usuario: $dbUser"
    Write-Info "  Banco: $($dbConfig.database)"
    Write-Host ""

    $ExistingConfig = @{}
    $envFilePath = "$appDir\.env"
    if (Test-Path $envFilePath) {
        Write-Info "Carregando configuracao existente..."
        $envLines = Get-Content $envFilePath
        foreach ($line in $envLines) {
            if ($line -match '^(.+?)=(.*)$') {
                $key = $Matches[1].Trim()
                $value = $Matches[2].Trim()
                $ExistingConfig[$key] = $value
            }
        }
    }

    Write-Section "FASE 5/8: CONFIGURACAO DA APLICACAO"

    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    $secretKey = -join (1..64 | ForEach-Object { $chars.Substring((Get-Random -Maximum $chars.Length), 1) })
    Write-Success "SECRET_KEY gerado: $($secretKey.Substring(0,20))..."

    Write-Info "Configurando email via Gmail SMTP..."

    Write-Host ""
    Write-Host "=========================================================" -ForegroundColor $Colors.Header
    Write-Host "CRIANDO SENHA DE APLICACAO DO GMAIL" -ForegroundColor $Colors.Header
    Write-Host "=========================================================" -ForegroundColor $Colors.Header
    Write-Host ""
    Write-Host "ATENCAO" -ForegroundColor $Colors.Warning
    Write-Host "NAO use sua senha normal do Gmail!" -ForegroundColor $Colors.Warning
    Write-Host "E necessario criar uma 'Senha de Aplicacao'." -ForegroundColor $Colors.Warning
    Write-Host ""
    Write-Host "Passo a passo:" -ForegroundColor $Colors.Info
    Write-Host "  1. Acesse: https://myaccount.google.com/apppasswords" -ForegroundColor $Colors.Info
    Write-Host "  2. Faca login na sua conta Google" -ForegroundColor $Colors.Info
    Write-Host "  3. Selecione: Mail" -ForegroundColor $Colors.Info
    Write-Host "  4. Clique em: Gerar" -ForegroundColor $Colors.Info
    Write-Host "  5. Copie a senha de 16 caracteres" -ForegroundColor $Colors.Info
    Write-Host ""

    if ($ExistingConfig.ContainsKey("SMTP_USER")) {
        $existingValue = $ExistingConfig["SMTP_USER"]
        Write-Host "" -ForegroundColor $Colors.Info
        Write-Host "[Config existente detectado]" -ForegroundColor $Colors.Success
        Write-Host "  SMTP_USER = $existingValue" -ForegroundColor $Colors.Success
        
        $choice = Read-Host "Usar este valor? [S/n]"
        if ($choice -notmatch "^[Nn]$") {
            $smtpUser = $existingValue
        } else {
            $smtpUser = Read-Host "Digite seu email do Gmail (ex: seu.email@gmail.com)"
        }
    } else {
        $smtpUser = Read-Host "Digite seu email do Gmail (ex: seu.email@gmail.com)"
    }
    
    if (-not $smtpUser) {
        Write-Error "Email nao fornecido"
        Stop-Script 1
    }
    
    Write-Info "Agora, crie a Senha de Aplicacao seguindo as instrucoes acima."
    Write-Info "Apos criar, cole abaixo:"

    if ($ExistingConfig.ContainsKey("SMTP_PASSWORD") -and $ExistingConfig["SMTP_PASSWORD"] -match "^[a-zA-Z0-9]{16}$") {
        Write-Host "" -ForegroundColor $Colors.Info
        Write-Host "[Config existente detectado]" -ForegroundColor $Colors.Success
        Write-Host "  SMTP_PASSWORD = $($ExistingConfig["SMTP_PASSWORD"])" -ForegroundColor $Colors.Success
        
        $useExistingPassword = Read-Host "Usar senha de aplicacao salva? [S/n]"
        if ($useExistingPassword -notmatch "^[Nn]$") {
            $smtpPassword = $ExistingConfig["SMTP_PASSWORD"]
            Write-Success "Usando senha de aplicacao salva"
        } else {
            $smtpPassword = (Read-Host "Cole a Senha de Aplicacao (16 caracteres)").Replace(" ", "")
        }
    } else {
        $smtpPassword = (Read-Host "Cole a Senha de Aplicacao (16 caracteres)").Replace(" ", "")
    }
    
    if (-not $smtpPassword) {
        Write-Error "Senha nao fornecida"
        Stop-Script 1
    }

    Write-Success "Email configurado: $smtpUser"

    Write-Info "Configurando painel de administracao..."
    Write-Info ""

    $adminPasswordPlain = ""
    $adminPasswordHash = ""

    if ($ExistingConfig.ContainsKey("ADMIN_PASSWORD_HASH")) {
        Write-Host ""
        Write-Host "[Config existente detectado]" -ForegroundColor $Colors.Success
        Write-Host "  ADMIN_PASSWORD_HASH ja configurado" -ForegroundColor $Colors.Success
        $useExistingHash = Read-Host "Usar hash de senha existente? [S/n]"
        if ($useExistingHash -notmatch "^[Nn]$") {
            $adminPasswordHash = $ExistingConfig["ADMIN_PASSWORD_HASH"]
            Write-Success "Usando hash de senha existente"
            Write-Info "(Pulando configuracao de senha de administrador)"
        }
    }

    if (-not $adminPasswordHash) {
        $adminPassword = ""
        $adminPasswordConfirm = ""
        do {
            $adminPassword = Read-Host "Digite uma senha para o administrador" -AsSecureString
            $adminPasswordPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
                [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($adminPassword))

            $adminPasswordConfirm = Read-Host "Confirme a senha" -AsSecureString
            $adminPasswordConfirmPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
                [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($adminPasswordConfirm))

            if ($adminPasswordPlain -ne $adminPasswordConfirmPlain) {
                Write-Warning "Senhas nao conferem. Tente novamente."
            }
        } while ($adminPasswordPlain -ne $adminPasswordConfirmPlain)

        Write-Success "Senha configurada"

        Write-Info "Gerando hash da senha de administrador..."
        $tempFile = "$env:TEMP\ss54-admin-pw.txt"
        $tempFilePy = $tempFile.Replace('\', '/')
        [IO.File]::WriteAllText($tempFile, $adminPasswordPlain)
        $bcryptResult = & $venvPython -c "import bcrypt; print(bcrypt.hashpw(open(r'$tempFilePy').read().strip().encode('utf-8'), bcrypt.gensalt()).decode('utf-8'))"
        $adminPasswordHash = $bcryptResult.Trim()
        Remove-Item $tempFile -ErrorAction SilentlyContinue
        Write-Success "Hash gerado"
    }

    Write-Info "Configurando IPs permitidos para o painel de administracao..."
    Write-Host ""
    Write-Host "SEGURANCA IMPORTANTE" -ForegroundColor $Colors.Warning
    Write-Host "O painel de administracao so e acessivel de IPs autorizados." -ForegroundColor $Colors.Warning
    Write-Host "Isso protege contra ataques externos." -ForegroundColor $Colors.Warning
    Write-Host ""

    $allowedIPs = @("127.0.0.1", "::1")
    Write-Success "  - 127.0.0.1 (localhost)"
    Write-Success "  - ::1 (localhost IPv6)"

    $existingIPs = if ($ExistingConfig.ContainsKey("ADMIN_ALLOWED_IPS")) { $ExistingConfig["ADMIN_ALLOWED_IPS"] } else { $null }
    $skipIPConfig = $false
    
    if ($existingIPs) {
        Write-Host ""
        Write-Host "[Config existente detectado]" -ForegroundColor $Colors.Success
        Write-Host "  ADMIN_ALLOWED_IPS = $existingIPs" -ForegroundColor $Colors.Success
        $useExistingIPs = Read-Host "Usar whitelist existente? [S/n]"
        if ($useExistingIPs -notmatch "^[Nn]$") {
            $allowedIPs = $existingIPs -split ','
            Write-Success "Usando whitelist existente"
            foreach ($ip in $allowedIPs) {
                Write-Success "  - $ip"
            }
            Write-Host ""
            Write-Info "Deseja adicionar mais IPs?"
            $addMore = Read-Host "[S/n] "
            if ($addMore -notmatch "^[SsYy]$") {
                $skipIPConfig = $true
            }
        }
    }

    if (-not $skipIPConfig) {
        if ($localIPs.Count -gt 0) {
            foreach ($ip in $localIPs) {
                $choice = Read-Host "Adicionar IP local $($ip.IPAddress) a whitelist? [S/n]"
                if ($choice -match "^[SsYy]$") {
                    $allowedIPs += $ip.IPAddress
                    Write-Success "  - $($ip.IPAddress) (rede interna)"
                }
            }
        }
        
        $choice = Read-Host "Adicionar IP publico $publicIP a whitelist? [S/n]"
        if ($choice -match "^[SsYy]$") {
            $allowedIPs += $publicIP
            Write-Success "  - $publicIP (IP publico)"
        }
        
        Write-Host ""
        Write-Info "Deseja adicionar mais IPs?"
        Write-Info "Exemplos de formatos aceitos:"
        Write-Info "  - IP individual: 192.168.1.100"
        Write-Info "  - Sub-rede (CIDR): 192.168.1.0/24 (permite toda sub-rede)"
        
        $anotherIP = "yes"
        while ($anotherIP -match "^[SsYy]$") {
            $anotherIP = Read-Host "IP/CIDR adicional (ou deixe em branco para continuar): "
            if ($anotherIP -and $anotherIP.Trim() -ne "") {
                $allowedIPs += $anotherIP.Trim()
                Write-Success "  - $($anotherIP.Trim())"
            } else {
                break
            }
        }
        
        Write-Host ""
        Write-Info "Resumo da whitelist:"
        foreach ($ip in $allowedIPs) {
            Write-Success "  - $ip"
        }
    }

    Write-Info "Criando arquivo de configuracao .env..."

    $envFile = "$appDir\.env"
    $frontendUrl = "http://$domain"
    $allowedOrigins = "http://$domain"
    if ($useWWW) {
        $allowedOrigins = "http://$domain,http://www.$domain"
    }

    Set-Content -Path $envFile -Value @"
# ===========================================
# CONFIGURACAO DO SS-54 - NAO COMPARTILHE!
# ===========================================

# Banco de Dados
DATABASE_URL=postgresql+psycopg://ss54_user:$ss54Password@localhost:5432/ss54_db

# Seguranca
SECRET_KEY=$secretKey
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_DAYS=7
MAGIC_LINK_EXPIRE_MINUTES=15

# Frontend URL (para links magicos)
FRONTEND_URL=$frontendUrl

# Email SMTP (Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=$smtpUser
SMTP_PASSWORD=$smtpPassword
EMAILS_FROM_EMAIL=$smtpUser
EMAILS_FROM_NAME=SS-54 Assistencia Farmaceutica de Praia Grande

# Emails DRS
DRS_RENOVACAO_EMAIL=drs-renovacao@saude.sp.gov.br
DRS_SOLICITACAO_EMAIL=drs-solicitacao@saude.sp.gov.br

# Configuracoes da Aplicacao
APP_NAME=SS-54
DEBUG=false
ALLOWED_ORIGINS=$allowedOrigins

# Upload de Arquivos
UPLOAD_DIR=$installDir\uploads
MAX_FILE_SIZE=10485760

# Configuracoes do Painel Admin
ADMIN_ALLOWED_IPS=$($allowedIPs -join ',')
ADMIN_PASSWORD_HASH=$adminPasswordHash
ADMIN_SESSION_DAYS=7

# Configuracoes do Servidor
HOST=0.0.0.0
PORT=$port

# Retencao de Dados (LGPD)
DATA_RETENTION_YEARS=5
DATA_RETENTION_ENABLED=true

# Configuracoes do Agendador
SCHEDULER_ENABLED=true
SCHEDULER_TIMEZONE=America/Sao_Paulo
BATCH_SEND_HOUR=9
DRS_FOLLOWUP_HOUR=10
AUTO_EXPIRE_HOUR=8

# ===========================================
# GERADO AUTOMATICAMENTE PELO SCRIPT DE DEPLOY
# Data: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# ===========================================
"@

    Write-Success "Arquivo .env criado: $envFile"
    Write-Warning "NAO compartilhe o arquivo .env!"

    Write-Info "Criando diretorios de uploads e logs..."
    New-Item -ItemType Directory -Path "$installDir\uploads\documents" -Force | Out-Null
    New-Item -ItemType Directory -Path "$installDir\uploads\temp" -Force | Out-Null
    New-Item -ItemType Directory -Path "$installDir\uploads\generated_pdfs" -Force | Out-Null
    New-Item -ItemType Directory -Path "$installDir\logs" -Force | Out-Null
    Write-Success "Diretorios criados"

    Write-Success "Fase 5 concluida: Aplicacao configurada"
}
