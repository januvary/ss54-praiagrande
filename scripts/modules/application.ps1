function Deploy-Application {
    param(
        [string]$installDir,
        [string]$appDir,
        [string]$GitRepo,
        [string]$pythonCmd,
        [string]$venvPython
    )

    Write-Info "Criando diretorio de instalacao..."
    try {
        New-Item -ItemType Directory -Path $installDir -Force | Out-Null
        Write-Success "Diretorio criado: $installDir"
    } catch {
        Write-Error "Falha ao criar diretorio: $_"
        Stop-Script 1
    }

    Write-Info "Clonando repositorio do GitHub..."
    Write-Info "Caminho da aplicacao: $appDir"
    Write-Info "Verificando se existe: $(Test-Path $appDir)"
    if (Test-Path $appDir) {
        Write-Warning "Diretorio ja existe. Atualizando..."

        $appDirUnix = $appDir -replace '\\', '/'
        & git config --global --add safe.directory $appDirUnix 2>&1 | Out-Null

        Set-Location $appDir
        & git pull origin main 2>&1 | Tee-Object -Variable gitOutput
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Repositorio atualizado"
        } else {
            Write-Error "Falha ao atualizar repositorio: exit code $LASTEXITCODE"
            Write-Error "Detalhes: $gitOutput"
            Stop-Script 1
        }
    } else {
        $appDirUnix = $appDir -replace '\\', '/'
        & git config --global --add safe.directory $appDirUnix 2>&1 | Out-Null

        Set-Location $installDir
        Write-Info "Clonando de: $GitRepo"
        & git clone $GitRepo 2>&1 | Tee-Object -Variable gitOutput
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Repositorio clonado"
        } else {
            Write-Error "Falha ao clonar repositorio: exit code $LASTEXITCODE"
            Write-Error "Detalhes: $gitOutput"
            Write-Info "Repositorio: $GitRepo"
            Write-Info "Diretorio destino: $appDir"
            Stop-Script 1
        }
    }

    Write-Info "Preparando ambiente virtual Python..."
    $venvPath = Join-Path $appDir "venv"

    if (Test-Path $venvPath) {
        Write-Info "Ambiente virtual ja existe. Removendo..."
        try {
            Remove-Item -Path $venvPath -Recurse -Force -ErrorAction Stop
            Write-Success "Ambiente virtual removido"
        } catch {
            Write-Warning "Falha ao remover ambiente virtual: $_"
            Write-Info "Continuando mesmo assim..."
        }
    }

    Write-Info "Criando ambiente virtual Python..."
    try {
        Set-Location $appDir
        & $pythonCmd -m venv venv 2>&1
        Write-Success "Ambiente virtual criado"
    } catch {
        Write-Error "Falha ao criar ambiente virtual: $_"
        Stop-Script 1
    }

    Write-Info "Ativando ambiente virtual e atualizando pip..."
    try {
        & $venvPython -m pip install --upgrade pip --quiet 2>&1 | Out-Null
        Write-Success "Pip atualizado"
    } catch {
        Write-Warning "Falha ao atualizar pip, continuando..."
    }

    Write-Info "Instalando dependencias do Python (requirements.txt)..."
    try {
        $requirementsFile = Join-Path $appDir "requirements.txt"
        if (-not (Test-Path $requirementsFile)) {
            Write-Error "Arquivo requirements.txt nao encontrado em $appDir"
            Stop-Script 1
        }
        
        & $venvPython -m pip install -r $requirementsFile --quiet 2>&1 | Out-Null
        Write-Success "Todas as dependencias instaladas"
    } catch {
        Write-Error "Falha ao instalar dependencias: $_"
        Stop-Script 1
    }
}

