$ProcessModeDir = Join-Path $env:USERPROFILE "ss54"
$ProcessPidFile = Join-Path $ProcessModeDir "ss54-app.pid"
$ProcessLogFile = Join-Path $ProcessModeDir "logs\app.log"
$ProcessStdoutFile = Join-Path $ProcessModeDir "logs\stdout.log"
$ProcessStderrFile = Join-Path $ProcessModeDir "logs\stderr.log"
$ProcessModeFile = Join-Path $ProcessModeDir "runmode.txt"

function Get-ProcessModeDir {
    return $ProcessModeDir
}

function Test-ProcessModeConfigured {
    return Test-Path $ProcessModeFile
}

function Get-ProcessAppDir {
    if (Test-Path $ProcessModeFile) {
        return (Get-Content $ProcessModeFile -Raw).Trim()
    }
    return $null
}

function Initialize-ProcessMode {
    param(
        [string]$appDir,
        [string]$venvPython,
        [int]$port = 8000
    )

    Write-Info "Configurando modo Processo (sem admin)..."

    if (-not (Test-Path $ProcessModeDir)) {
        New-Item -ItemType Directory -Path $ProcessModeDir -Force | Out-Null
        Write-Success "Diretorio criado: $ProcessModeDir"
    }

    $logsDir = Join-Path $ProcessModeDir "logs"
    if (-not (Test-Path $logsDir)) {
        New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
        Write-Success "Diretorio de logs criado: $logsDir"
    }

    Set-Content -Path $ProcessModeFile -Value $appDir -NoNewline

    return $true
}

function Start-AppProcess {
    param(
        [string]$appDir,
        [string]$venvPython,
        [int]$port = 8000
    )

    if (Test-Path $ProcessPidFile) {
        $existingPid = (Get-Content $ProcessPidFile -Raw).Trim()
        $process = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
        if ($process) {
            Write-Warning "Aplicacao ja esta rodando (PID: $existingPid)"
            return $true
        }
        Remove-Item $ProcessPidFile -Force
    }

    Write-Info "Iniciando aplicacao como processo..."

    $logsDir = Join-Path $ProcessModeDir "logs"
    if (-not (Test-Path $logsDir)) {
        New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
    }

    $psi = @{
        FilePath = $venvPython
        ArgumentList = @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", $port)
        WorkingDirectory = $appDir
        WindowStyle = "Hidden"
    }

    try {
        $process = Start-Process @psi -PassThru

        $process.Id | Out-File -FilePath $ProcessPidFile -NoNewline

        Start-Sleep -Seconds 3

        $process = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
        if ($process) {
            Write-Success "Aplicacao iniciada (PID: $($process.Id))"
            Write-Info "Acesse: http://localhost:$port"
            return $true
        } else {
            Write-Error "Processo iniciou mas terminou inesperadamente"
            return $false
        }
    } catch {
        Write-Error "Falha ao iniciar processo: $_"
        return $false
    }
}

function Stop-AppProcess {
    if (-not (Test-Path $ProcessPidFile)) {
        Write-Warning "Aplicacao nao esta rodando (PID file nao encontrado)"
        return $true
    }

    $appPid = (Get-Content $ProcessPidFile -Raw).Trim()
    $process = Get-Process -Id $appPid -ErrorAction SilentlyContinue

    if (-not $process) {
        Write-Warning "Aplicacao nao esta rodando (processo nao encontrado)"
        Remove-Item $ProcessPidFile -Force -ErrorAction SilentlyContinue
        return $true
    }

    Write-Info "Parando aplicacao (PID: $appPid)..."

    try {
        Stop-Process -Id $appPid -Force
        Start-Sleep -Seconds 2

        $process = Get-Process -Id $appPid -ErrorAction SilentlyContinue
        if ($process) {
            Write-Warning "Processo ainda rodando, forçando parada..."
            Stop-Process -Id $appPid -Force -ErrorAction SilentlyContinue
        }

        Remove-Item $ProcessPidFile -Force -ErrorAction SilentlyContinue
        Write-Success "Aplicacao parada"

        return $true
    } catch {
        Write-Error "Falha ao parar processo: $_"
        return $false
    }
}

function Get-AppProcessStatus {
    $result = @{
        Running = $false
        Pid = $null
        Port = 8000
        HealthOk = $false
    }

    if (-not (Test-Path $ProcessPidFile)) {
        return $result
    }

    $appPid = (Get-Content $ProcessPidFile -Raw).Trim()
    $process = Get-Process -Id $appPid -ErrorAction SilentlyContinue

    if (-not $process) {
        Remove-Item $ProcessPidFile -Force -ErrorAction SilentlyContinue
        return $result
    }

    $result.Running = $true
    $result.Pid = $appPid

    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -Method Get -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            $result.HealthOk = $true
        }
    } catch {}

    return $result
}

function Add-ProcessToStartup {
    param(
        [string]$appDir,
        [string]$scriptDir = $PSScriptRoot
    )

    $startupFolder = [Environment]::GetFolderPath("Startup")
    $shortcutPath = Join-Path $startupFolder "SS-54 Backend.lnk"

    $startScript = Join-Path $scriptDir "start-app.ps1"

    if (-not (Test-Path $startScript)) {
        Write-Error "Script de inicializacao nao encontrado. Execute o deploy primeiro."
        return $false
    }

    try {
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut($shortcutPath)
        $Shortcut.TargetPath = "powershell.exe"
        $Shortcut.Arguments = "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$startScript`""
        $Shortcut.WorkingDirectory = $scriptDir
        $Shortcut.Description = "SS-54 Backend"
        $Shortcut.Save()

        Write-Success "Atalho de inicializacao criado: $shortcutPath"
        Write-Info "A aplicacao iniciara automaticamente ao fazer login"
        return $true
    } catch {
        Write-Error "Falha ao criar atalho de inicializacao: $_"
        return $false
    }
}

function Remove-ProcessFromStartup {
    $startupFolder = [Environment]::GetFolderPath("Startup")
    $shortcutPath = Join-Path $startupFolder "SS-54 Backend.lnk"

    if (Test-Path $shortcutPath) {
        Remove-Item $shortcutPath -Force
        Write-Success "Atalho de inicializacao removido"
        return $true
    }

    Write-Info "Nenhum atalho de inicializacao encontrado"
    return $true
}

function Test-ProcessInStartup {
    $startupFolder = [Environment]::GetFolderPath("Startup")
    $shortcutPath = Join-Path $startupFolder "SS-54 Backend.lnk"
    return Test-Path $shortcutPath
}
