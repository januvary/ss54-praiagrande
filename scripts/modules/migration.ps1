function Run-DatabaseMigration {
    param(
        [Parameter(Mandatory=$true)]
        [string]$appDir,
        
        [Parameter(Mandatory=$true)]
        [string]$venvPython,
        
        [Parameter(Mandatory=$true)]
        [string]$psqlCmd
    )

    Write-Section "MIGRACAO DO BANCO DE DADOS"

    Write-Info "O que vou fazer:"
    Write-Host "  1. Criar as tabelas do banco de dados" -ForegroundColor $Colors.Info
    Write-Host "  2. Definir estrutura (schema) do banco" -ForegroundColor $Colors.Info
    Write-Host "  3. Aplicar todas as migracoes pendentes" -ForegroundColor $Colors.Info
    Write-Host ""
    Write-Host "Isso cria as tabelas necessarias para:" -ForegroundColor $Colors.Info
    Write-Host "  - Pacientes" -ForegroundColor $Colors.Info
    Write-Host "  - Processos" -ForegroundColor $Colors.Info
    Write-Host "  - Documentos" -ForegroundColor $Colors.Info
    Write-Host "  - Usuarios" -ForegroundColor $Colors.Info
    Write-Host "  - Logs de atividade" -ForegroundColor $Colors.Info
    Write-Host "  - E muito mais..." -ForegroundColor $Colors.Info
    Write-Host ""
    Write-Host "AVISO" -ForegroundColor $Colors.Warning
    Write-Host "Se ja existirem dados no banco, eles serao preservados." -ForegroundColor $Colors.Warning
    Write-Host "Apenas estruturas faltantes serao criadas." -ForegroundColor $Colors.Warning
    Write-Host ""

    $choice = Read-Host "Deseja executar a migracao agora? [S/n]"
    if ($choice -notmatch "^[SsYy]$") {
        Write-Info "Migracao cancelada pelo usuario."
        Stop-Script 0
    }

    Write-Info "Executando Alembic (migracao do banco de dados)..."

    try {
        Set-Location $appDir
        
        & $venvPython -m alembic upgrade head 2>&1 | Out-Null
        Write-Success "Migracao concluida com sucesso!"
        
        Write-Info "Verificando tabelas criadas..."
        $tablesResult = & $psqlCmd -U ss54_user -d ss54_db -c "\dt" 2>&1
        
        Write-Success "Tabelas criadas:"
        foreach ($line in $tablesResult) {
            if ($line -match '^\|.*\|') {
                $tableName = ($line -split '\|')[1].Trim()
                if ($tableName -ne "" -and $tableName -ne "List") {
                    Write-Success "  - $tableName"
                }
            }
        }
    } catch {
        Write-Error "Falha ao executar migracao: $_"
        Write-Info "Verifique se:"
        Write-Info "  1. O banco de dados esta configurado corretamente"
        Write-Info "  2. As credenciais estao corretas"
        Write-Info "  3. O arquivo .env esta configurado"
        Stop-Script 1
    }

    Write-Success "Banco de dados migrado"
    Pause-Continue
}

