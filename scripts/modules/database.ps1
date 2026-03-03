function Initialize-Database {
    param(
        [Parameter(Mandatory=$true)]
        [string]$psqlCmd,

        [Parameter(Mandatory=$true)]
        [string]$DefaultInstallDir,

        [Parameter(Mandatory=$false)]
        [bool]$ResetPassword = $false
    )

    Write-Info "Configurando PostgreSQL para o SS-54..."

    $postgresPassword = Read-Host "Digite a senha do usuario 'postgres' (definida durante instalacao do PostgreSQL)"
    if (-not $postgresPassword) {
        Write-Error "Senha nao fornecida"
        Stop-Script 1
    }

    $env:PGPASSWORD = $postgresPassword

    Write-Info "Testando conexao com PostgreSQL..."
    try {
        $testResult = & $psqlCmd -U postgres -c "SELECT 1;" 2>&1
        Write-Success "Conexao com PostgreSQL estabelecida"
    } catch {
        Write-Error "Falha ao conectar ao PostgreSQL"
        Write-Error "Verifique se o PostgreSQL esta em execucao e a senha esta correta"
        Stop-Script 1
    }

    $dbExists = $false
    $userExists = $false

    $checkDb = & $psqlCmd -U postgres -c "SELECT 1 FROM pg_database WHERE datname='ss54_db';" 2>&1
    if ($checkDb -match "1 row") {
        $dbExists = $true
    }

    $checkUser = & $psqlCmd -U postgres -c "SELECT 1 FROM pg_roles WHERE rolname='ss54_user';" 2>&1
    if ($checkUser -match "1 row") {
        $userExists = $true
    }

    if ($dbExists -or $userExists) {
        Write-Warning "Detectado banco de dados e/ou usuario existente:"
        if ($dbExists) { Write-Warning "  - Banco de dados 'ss54_db' existe" }
        if ($userExists) { Write-Warning "  - Usuario 'ss54_user' existe" }
        Write-Host ""

        Write-Host "Opcoes:" -ForegroundColor $Colors.Info
        Write-Host "  [R] Resetar banco de dados (drop e recriar - PERDA DE TODOS OS DADOS!)" -ForegroundColor Red
        Write-Host "  [K] Manter banco de dados existente (reutilizar credenciais)" -ForegroundColor Green
        Write-Host "  [C] Cancelar deploy" -ForegroundColor Gray
        Write-Host ""

        $choice = Read-Host "Selecione uma opcao (R/K/C)"

        switch ($choice.ToUpper()) {
            "R" {
                Write-Info "Resetando banco de dados e usuario..."
                if ($dbExists) {
                    & $psqlCmd -U postgres -c "DROP DATABASE IF EXISTS ss54_db;" 2>&1 | Out-Null
                    Write-Success "Banco de dados removido"
                }
                if ($userExists) {
                    & $psqlCmd -U postgres -c "DROP USER IF EXISTS ss54_user;" 2>&1 | Out-Null
                    Write-Success "Usuario removido"
                }
                $dbExists = $false
                $userExists = $false
            }
            "K" {
                Write-Info "Mantendo banco de dados e usuario existentes..."
                Write-Info "Reutilizando credenciais existentes"
                if (Test-Path "$DefaultInstallDir\db-credentials.txt") {
                    $credsContent = Get-Content "$DefaultInstallDir\db-credentials.txt" -Raw
                    if ($credsContent -match "Password:\s*(.+)") {
                        $ss54Password = $Matches[1].Trim()
                        Write-Success "Senha existente encontrada"
                    } else {
                        Write-Error "Arquivo de credenciais encontrado, mas sem senha valida"
                        Stop-Script 1
                    }
                } else {
                    Write-Error "Arquivo de credenciais nao encontrado. Nao e possivel continuar sem senha existente."
                    Write-Info "Execute a opcao de reset para criar novas credenciais."
                    Stop-Script 1
                }

                Write-Info "Atualizando privilegios..."
                try {
                    & $psqlCmd -U postgres -d ss54_db -c "GRANT ALL PRIVILEGES ON DATABASE ss54_db TO ss54_user;" 2>&1 | Out-Null
                    & $psqlCmd -U postgres -d ss54_db -c "GRANT ALL ON SCHEMA public TO ss54_user;" 2>&1 | Out-Null
                    & $psqlCmd -U postgres -d ss54_db -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ss54_user;" 2>&1 | Out-Null
                    & $psqlCmd -U postgres -d ss54_db -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ss54_user;" 2>&1 | Out-Null
                    & $psqlCmd -U postgres -d ss54_db -c "ALTER SCHEMA public OWNER TO ss54_user;" 2>&1 | Out-Null
                    Write-Success "Privilegios atualizados"
                } catch {
                    Write-Warning "Avisos durante atualizacao de privilegios: $_"
                }

                $envFile = "$DefaultInstallDir\ss54-praiagrande\.env"
                if (Test-Path $envFile) {
                    Write-Info "Atualizando arquivo .env com senha existente..."
                    $envContent = Get-Content $envFile -Raw
                    $newEnvContent = $envContent -replace 'postgresql\+psycopg://ss54_user:[^@]+@', "postgresql+psycopg://ss54_user:$ss54Password@"
                    Set-Content -Path $envFile -Value $newEnvContent -NoNewline
                    Write-Success "Arquivo .env atualizado"
                }

                Write-Success "Configuracao do banco de dados concluida (modo de manutencao)"
                return @{
                    user = "ss54_user"
                    password = $ss54Password
                    database = "ss54_db"
                    host = "localhost"
                    port = 5432
                    keptExisting = $true
                }
            }
            default {
                Write-Info "Deploy cancelado pelo usuario"
                Stop-Script 0
            }
        }
    }

    Write-Info "Criando banco de dados 'ss54_db'..."
    try {
        $createDb = & $psqlCmd -U postgres -c "CREATE DATABASE ss54_db;" 2>&1
        Write-Success "Banco de dados 'ss54_db' criado"
    } catch {
        if ($_ -match "already exists") {
            Write-Warning "Banco de dados 'ss54_db' ja existe"
        } else {
            Write-Error "Falha ao criar banco de dados: $_"
            Stop-Script 1
        }
    }

    Write-Info "Gerando senha segura para usuario 'ss54_user'..."
    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    $ss54Password = -join (1..32 | ForEach-Object { $chars.Substring((Get-Random -Maximum $chars.Length), 1) })
    Write-Success "Senha gerada (32 caracteres, apenas alfanumerica)"

    Write-Info "Criando usuario 'ss54_user'..."
    try {
        $createUser = & $psqlCmd -U postgres -c "CREATE USER ss54_user WITH PASSWORD '$ss54Password';" 2>&1
        Write-Success "Usuario 'ss54_user' criado"
    } catch {
        if ($_ -match "already exists") {
            Write-Warning "Usuario 'ss54_user' ja existe"
        } else {
            Write-Error "Falha ao criar usuario: $_"
            Stop-Script 1
        }
    }

    Write-Info "Concedendo privilegios de banco..."
    try {
        $grantPrivs = & $psqlCmd -U postgres -d ss54_db -c "GRANT ALL PRIVILEGES ON DATABASE ss54_db TO ss54_user;" 2>&1
        Write-Success "Privilegios de banco concedidos"
    } catch {
        Write-Error "Falha ao conceder privilegios de banco: $_"
        Stop-Script 1
    }

    Write-Info "Concedendo privilegios no schema public..."
    try {
        & $psqlCmd -U postgres -d ss54_db -c "GRANT ALL ON SCHEMA public TO ss54_user;" 2>&1 | Out-Null
        Write-Success "Privilegios de schema concedidos"
    } catch {
        Write-Warning "Falha ao conceder privilegios de schema: $_"
    }

    Write-Info "Concedendo privilegios de criacao de tabelas e sequencias..."
    try {
        & $psqlCmd -U postgres -d ss54_db -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ss54_user;" 2>&1 | Out-Null
        & $psqlCmd -U postgres -d ss54_db -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ss54_user;" 2>&1 | Out-Null
        Write-Success "Privilegios de criacao concedidos"
    } catch {
        Write-Warning "Falha ao conceder privilegios de criacao: $_"
    }

    Write-Info "Definindo dono do schema..."
    try {
        & $psqlCmd -U postgres -d ss54_db -c "ALTER SCHEMA public OWNER TO ss54_user;" 2>&1 | Out-Null
        Write-Success "Dono do schema alterado"
    } catch {
        Write-Warning "Nao foi possivel alterar dono do schema"
    }

    Write-Info "Concedendo privilegio CREATEDB ao usuario..."
    try {
        & $psqlCmd -U postgres -c "ALTER USER ss54_user CREATEDB;" 2>&1 | Out-Null
        Write-Success "Privilegio CREATEDB concedido"
    } catch {
        Write-Warning "Falha ao conceder CREATEDB: $_"
    }

    $credsFile = "$DefaultInstallDir\db-credentials.txt"
    New-Item -ItemType Directory -Path $DefaultInstallDir -Force | Out-Null
    Set-Content -Path $credsFile -Value @"
CREDENCIAIS DO BANCO DE DADOS - SS-54
====================================
Host: localhost
Port: 5432
Database: ss54_db
User: ss54_user
Password: $ss54Password

IMPORTANTE: GUARDE ESTE ARQUIVO EM LOCAL SEGURO!
NAO compartilhe estes dados com ninguem.
====================================

Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
"@
    Write-Success "Credenciais salvas em: $credsFile"
    Write-Warning "GUARDE ESTE ARQUIVO!"

    $envFile = "$DefaultInstallDir\ss54-praiagrande\.env"
    if (Test-Path $envFile) {
        Write-Info "Atualizando arquivo .env com nova senha..."
        $envContent = Get-Content $envFile -Raw
        $newEnvContent = $envContent -replace 'postgresql\+psycopg://ss54_user:[^@]+@', "postgresql+psycopg://ss54_user:$ss54Password@"
        Set-Content -Path $envFile -Value $newEnvContent -NoNewline
        Write-Success "Arquivo .env atualizado com nova senha"
    }

    return @{
        user = "ss54_user"
        password = $ss54Password
        database = "ss54_db"
        host = "localhost"
        port = 5432
        keptExisting = $false
    }
}

