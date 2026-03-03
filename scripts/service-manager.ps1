param(
    [string]$Action,
    [switch]$Help
)

. "$PSScriptRoot/config.ps1"
. "$PSScriptRoot/utils/helpers.ps1"
. "$PSScriptRoot/modules/logging.ps1"
. "$PSScriptRoot/modules/cloudflare-tunnel.ps1"
. "$PSScriptRoot/modules/process.ps1"
. "$PSScriptRoot/modules/runmode.ps1"

$runMode = Get-RunMode
$appDir = Get-RunModeAppDir
$installDir = if ($appDir) { Split-Path $appDir -Parent } else { $DefaultInstallDir }
$serviceName = "SS54Backend"
$serviceNameDisplay = "SS-54 Backend"
$logsDir = Join-Path $installDir "logs"
$envFile = if ($appDir) { Join-Path $appDir ".env" } else { $null }
$dbCredentialsFile = Join-Path $installDir "db-credentials.txt"
$healthUrl = "http://localhost:8000/api/health"
$cloudflareDomain = "ss54pg.com.br"

# Simple working icons (ASCII-compatible)
$IconSuccess = "[OK]"
$IconError = "[X]"
$IconWarning = "[!]"
$IconGear = "[G]"
$IconDatabase = "[D]"
$IconLock = "[L]"
$IconFolder = "[F]"
$IconChart = "[C]"
$IconRocket = "[R]"
$IconWifi = "[W]"
$IconLogs = "[T]"
$IconRefresh = "[REF]"
$IconTerminal = "[T]"

function Draw-Box {
    param(
        [string[]]$Lines,
        [string]$Title = "",
        [string]$Color = "Cyan",
        [int]$Width = 80
    )

    $line = "-" * ($Width - 2)
    $dashes = "-" * 78

    Write-Host ""
    if ($Title) {
        Write-Host "+$dashes+" -ForegroundColor $Color
        Write-Host "|  $Title" + (" " * (74 - $Title.Length)) + "  |" -ForegroundColor $Color
        Write-Host "+" + $line + "+" -ForegroundColor $Color
    } else {
        Write-Host "+$dashes+" -ForegroundColor $Color
    }

    foreach ($boxLine in $Lines) {
        $padded = $boxLine.PadRight($Width - 2)
        Write-Host "| $padded |" -ForegroundColor $Color
    }

    Write-Host "+$dashes+" -ForegroundColor $Color
    Write-Host ""
}

function Draw-Header {
    param([string]$Title)

    Write-Host ""
    Write-Host ("+" + ("-" * 78) + "+") -ForegroundColor DarkCyan
    Write-Host ("|  " + $Title + (" " * (74 - $Title.Length)) + "  |") -ForegroundColor DarkCyan
    Write-Host ("+" + ("-" * 78) + "+") -ForegroundColor DarkCyan
    Write-Host ""
}

function Draw-MenuSection {
    param(
        [string]$Title,
        [string]$Icon,
        [hashtable]$Options
    )

    Write-Host "  $Icon $Title" -ForegroundColor Cyan
    Write-Host ""

    $keys = $Options.Keys | Sort-Object { [int]$_ }
    foreach ($key in $keys) {
        $desc = $Options[$key]
        $keyDisplay = "[$key]".PadRight(4)
        Write-Host "    $keyDisplay $desc" -ForegroundColor White
    }
    Write-Host ""
}

function Show-Menu {
    Clear-Host

    Draw-Header "SS-54 PRAIA GRANDE - SERVICE MANAGER v$ScriptVersion"

    $modeDisplay = if ($runMode -eq "service") { "SERVICO" } elseif ($runMode -eq "process") { "PROCESSO" } else { "NAO CONFIGURADO" }
    Write-Host "  Modo: $modeDisplay" -ForegroundColor $(if ($runMode) { "Green" } else { "Red" })
    Write-Host ""

    if ($runMode -eq "service") {
        Draw-MenuSection "Gerenciamento do Servico" $IconGear @{
            "1" = "Status do Servico"
            "2" = "Iniciar Servico"
            "3" = "Parar Servico"
            "4" = "Reiniciar Servico"
            "5" = "Remover Servico"
            "6" = "Editar Configuracao"
        }
    } elseif ($runMode -eq "process") {
        Draw-MenuSection "Gerenciamento do Processo" $IconGear @{
            "1" = "Status do Processo"
            "2" = "Iniciar Processo"
            "3" = "Parar Processo"
            "4" = "Reiniciar Processo"
        }
    } else {
        Draw-MenuSection "Primeiro, execute o deploy" $IconGear @{
            "1" = "Executar Deploy"
        }
    }

    Draw-MenuSection "Verificacao e Logs" $IconTerminal @{
        "7" = "Health Check"
        "8" = "Ver Logs da App"
        "9" = "Ver Logs Stdout"
        "10" = "Ver Logs Stderr"
        "11" = "Abrir Diretorio Logs"
    }

    Draw-MenuSection "Banco de Dados" $IconDatabase @{
        "12" = "Status do BD"
        "13" = "Resetar Senha BD"
        "14" = "Backup do BD"
    }

    Draw-MenuSection "Cloudflare Tunnel" $IconWifi @{
        "17" = "Status do Tunnel"
        "18" = "Iniciar Tunnel"
        "19" = "Parar Tunnel"
    }

    Draw-MenuSection "Configuracao" $IconLock @{
        "20" = "Editar .env"
        "21" = "Recarregar Config"
    }

    Draw-MenuSection "Outros" $IconChart @{
        "22" = "Informacoes do Sistema"
        "23" = "Atualizar Aplicacao"
        "24" = "Sair"
    }

    Write-Host ("=" * 80) -ForegroundColor DarkGray

    $choice = Read-Host "`n   Selecione uma opcao"

    switch -Regex ($choice) {
        "^[Rr]$" { if ($runMode -eq "service") { Show-ServiceStatus } else { Show-ProcessStatus } }
        "^1$" { 
            if ($runMode -eq "service") { Show-ServiceStatus }
            elseif ($runMode -eq "process") { Show-ProcessStatus }
            else { Write-Host "  Execute o deploy primeiro" -ForegroundColor Yellow; Start-Sleep 2 }
        }
        "^2$" { if ($runMode -eq "service") { Start-SS54Service } elseif ($runMode -eq "process") { Start-SS54Process } }
        "^3$" { if ($runMode -eq "service") { Stop-SS54Service } elseif ($runMode -eq "process") { Stop-SS54Process } }
        "^4$" { if ($runMode -eq "service") { Restart-SS54Service } elseif ($runMode -eq "process") { Restart-SS54Process } }
        "^5$" { if ($runMode -eq "service") { Remove-SS54Service } }
        "^6$" { if ($runMode -eq "service") { Edit-ServiceConfig } }
        "^[Tt]$" { Run-HealthCheck }
        "^7$" { Run-HealthCheck }
        "^8$" { Show-AppLogs }
        "^9$" { Show-StdoutLogs }
        "^10$" { Show-StderrLogs }
        "^11$" { Open-LogsDirectory }
        "^[Dd]$" { Show-DatabaseStatus }
        "^12$" { Show-DatabaseStatus }
        "^13$" { Reset-DatabasePassword }
        "^14$" { Backup-Database }
        "^[Ww]$" { Show-TunnelStatus }
        "^17$" { Show-TunnelStatus }
        "^18$" { Start-CloudflareTunnelFromMenu }
        "^19$" { Stop-CloudflareTunnelFromMenu }
        "^[Ll]$" { Edit-EnvFile }
        "^20$" { Edit-EnvFile }
        "^21$" { Reload-Configuration }
        "^[Cc]$" { Show-SystemInfo }
        "^22$" { Show-SystemInfo }
        "^23$" { Update-Application }
        "^24$" { exit }
        "^[Qq]$" { exit }
        default {
            Write-Host "  [X]  Opcao invalida!" -ForegroundColor Red
            Start-Sleep 2
        }
    }
}

function Show-ServiceStatus {
    Clear-Host
    Draw-Header "STATUS DO SERVICO"

    try {
        $service = Get-Service -Name $serviceName -ErrorAction Stop
        $nssmOutput = & $NssmPath status $serviceName 2>&1

        $statusColor = switch ($service.Status) {
            "Running" { "Green" }
            "Stopped" { "Red" }
            default { "Yellow" }
        }
        $statusIcon = switch ($service.Status) {
            "Running" { $IconSuccess }
            "Stopped" { $IconError }
            default { $IconWarning }
        }

        Draw-Box @(
            ("$statusIcon Nome do Servico:  $serviceNameDisplay ($serviceName)"),
            ("$statusIcon Status (Windows):  $($service.Status) ($($service.StartType))"),
            ("$statusIcon Process ID:         $($service.Id)"),
            ("$IconG  Binario:            $( & $NssmPath get $serviceName Application )"),
            ("$IconF  Diretorio:          $( & $NssmPath get $serviceName AppDirectory )"),
            ("$statusIcon Status (NSSM):      $nssmOutput")
        ) -Title "Informacoes do Servico" -Color $statusColor

        Write-Host "  [REF]  Verificando Health Check..." -ForegroundColor Cyan
        Run-HealthCheck -Quick
    } catch {
        Draw-Box @(
            ("$IconError Servico '$serviceName' nao encontrado."),
            ("  Execute o script de deploy para criar o servico.")
        ) -Color Red -Title "Erro"
    }

    Pause-Continue
}

function Start-SS54Service {
    Clear-Host
    Draw-Header "INICIANDO SERVICO"

    Write-Host "  [REF]  Verificando se servico existe..." -ForegroundColor Cyan
    $serviceExists = Get-Service -Name $serviceName -ErrorAction SilentlyContinue

    if (-not $serviceExists) {
        Write-Host "  [X]  Servico '$serviceName' nao encontrado." -ForegroundColor Red
        Write-Host "  Execute o script de deploy completo." -ForegroundColor Yellow
        Pause-Continue
        return
    }

    $currentStatus = (Get-Service -Name $serviceName).Status

    if ($currentStatus -eq "Running") {
        Draw-Box @(
            ("$IconSuccess Servico ja esta rodando!")
        ) -Color Green -Title "Status"
        Pause-Continue
        return
    }

    Write-Host "  [G]  Iniciando servico..." -ForegroundColor Cyan

    try {
        Write-Host "  Aguarde" -ForegroundColor Yellow -NoNewline
        Start-Service -Name $serviceName -ErrorAction Stop

        $maxWait = 30
        $waited = 0
        while ($waited -lt $maxWait) {
            $status = (Get-Service -Name $serviceName).Status
            if ($status -eq "Running") {
                Write-Host ""
                Draw-Box @(
                    ("$IconSuccess Servico iniciado com sucesso!")
                ) -Color Green -Title "Sucesso"

                Start-Sleep 2
                Run-HealthCheck -Quick
                return
            }
            Start-Sleep 1
            $waited++
            Write-Host "." -NoNewline -ForegroundColor Yellow
        }

        Write-Host ""
        Draw-Box @(
            ("$IconWarning Servico ainda esta iniciando."),
            ("  Verifique logs para detalhes.")
        ) -Color Yellow -Title "Aviso"
    } catch {
        Write-Host ""
        Draw-Box @(
            ("$IconError Falha ao iniciar servico: $_"),
            ("  Verifique logs em: $logsDir")
        ) -Color Red -Title "Erro"
    }

    Pause-Continue
}

function Stop-SS54Service {
    Clear-Host
    Draw-Header "PARANDO SERVICO"

    Write-Host "  [REF]  Verificando se servico existe..." -ForegroundColor Cyan
    $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue

    if (-not $service) {
        Draw-Box @(
            ("$IconError Servico '$serviceName' nao encontrado.")
        ) -Color Red -Title "Erro"
        Pause-Continue
        return
    }

    $currentStatus = $service.Status

    if ($currentStatus -eq "Stopped") {
        Draw-Box @(
            ("$IconSuccess Servico ja esta parado.")
        ) -Color Green -Title "Status"
        Pause-Continue
        return
    }

    Write-Host "  [G]  Parando servico..." -ForegroundColor Cyan

    try {
        Write-Host "  Aguarde" -ForegroundColor Yellow -NoNewline
        Stop-Service -Name $serviceName -Force -ErrorAction Stop

        $maxWait = 30
        $waited = 0
        while ($waited -lt $maxWait) {
            $status = (Get-Service -Name $serviceName).Status
            if ($status -eq "Stopped") {
                Write-Host ""
                Draw-Box @(
                    ("$IconSuccess Servico parado com sucesso!")
                ) -Color Green -Title "Sucesso"
                return
            }
            Start-Sleep 1
            $waited++
            Write-Host "." -NoNewline -ForegroundColor Yellow
        }

        Write-Host ""
        Draw-Box @(
            ("$IconWarning Servico ainda esta parando.")
        ) -Color Yellow -Title "Aviso"
    } catch {
        Write-Host ""
        Draw-Box @(
            ("$IconError Falha ao parar servico: $_")
        ) -Color Red -Title "Erro"
    }

    Pause-Continue
}

function Restart-SS54Service {
    Clear-Host
    Draw-Header "REINICIANDO SERVICO"

    Write-Host "  [REF]  Verificando se servico existe..." -ForegroundColor Cyan
    $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue

    if (-not $service) {
        Draw-Box @(
            ("$IconError Servico '$serviceName' nao encontrado.")
        ) -Color Red -Title "Erro"
        Pause-Continue
        return
    }

    Write-Host "  [G]  Reiniciando servico..." -ForegroundColor Cyan

    try {
        Write-Host "  Aguarde" -ForegroundColor Yellow -NoNewline
        Restart-Service -Name $serviceName -Force -ErrorAction Stop

        $maxWait = 45
        $waited = 0
        while ($waited -lt $maxWait) {
            $status = (Get-Service -Name $serviceName).Status
            if ($status -eq "Running") {
                Write-Host ""
                Draw-Box @(
                    ("$IconSuccess Servico reiniciado com sucesso!")
                ) -Color Green -Title "Sucesso"

                Start-Sleep 2
                Run-HealthCheck -Quick
                return
            }
            Start-Sleep 1
            $waited++
            Write-Host "." -NoNewline -ForegroundColor Yellow
        }

        Write-Host ""
        Draw-Box @(
            ("$IconWarning Servico ainda esta reiniciando."),
            ("  Verifique logs para detalhes.")
        ) -Color Yellow -Title "Aviso"
    } catch {
        Write-Host ""
        Draw-Box @(
            ("$IconError Falha ao reiniciar servico: $_")
        ) -Color Red -Title "Erro"
    }

    Pause-Continue
}

function Remove-SS54Service {
    Clear-Host
    Draw-Header "REMOVENDO SERVICO"

    Draw-Box @(
        ("$IconWarning  ATENCAO: Isto removera o servico Windows!"),
        ("  A aplicacao continuara instalada, mas nao rodara automaticamente.")
    ) -Color Yellow -Title "Aviso"

    $confirm = Read-Host "`n   [REF]  Deseja continuar? (s/N)"
    if ($confirm -ne 's' -and $confirm -ne 'S') {
        Write-Host "  [OK]  Operacao cancelada." -ForegroundColor Green
        return
    }

    Write-Host "  [G]  Parando servico..." -ForegroundColor Cyan
    Stop-Service -Name $serviceName -ErrorAction SilentlyContinue

    Write-Host "  [G]  Removendo servico NSSM..." -ForegroundColor Cyan
    & $NssmPath remove $serviceName confirm 2>&1 | Out-Null

    Draw-Box @(
        ("$IconSuccess Servico removido com sucesso!"),
        ("  Para recriar, execute o script de deploy completo.")
    ) -Color Green -Title "Sucesso"
}

function Show-ProcessStatus {
    Clear-Host
    Draw-Header "STATUS DO PROCESSO"

    $status = Get-AppProcessStatus

    if ($status.Running) {
        $statusColor = "Green"
        $statusIcon = $IconSuccess
        $statusText = "RODANDO"
    } else {
        $statusColor = "Red"
        $statusIcon = $IconError
        $statusText = "PARADO"
    }

    Draw-Box @(
        ("$statusIcon Status:     $statusText"),
        ("$statusIcon PID:        $(if ($status.Pid) { $status.Pid } else { 'N/A' })"),
        ("$IconG  Porta:      8000"),
        ("$IconF  Diretorio:  $appDir")
    ) -Title "Informacoes do Processo" -Color $statusColor

    Write-Host "  [REF]  Verificando Health Check..." -ForegroundColor Cyan
    Run-HealthCheck -Quick

    Pause-Continue
}

function Start-SS54Process {
    Clear-Host
    Draw-Header "INICIANDO PROCESSO"

    $status = Get-AppProcessStatus

    if ($status.Running) {
        Draw-Box @(
            ("$IconSuccess Processo ja esta rodando!"),
            ("  PID: $($status.Pid)")
        ) -Color Green -Title "Status"
        Pause-Continue
        return
    }

    Write-Host "  [G]  Iniciando processo..." -ForegroundColor Cyan

    $venvPython = Join-Path $appDir "venv\Scripts\python.exe"
    
    if (-not (Test-Path $venvPython)) {
        Draw-Box @(
            ("$IconError Python nao encontrado: $venvPython"),
            ("  Execute o script de deploy primeiro.")
        ) -Color Red -Title "Erro"
        Pause-Continue
        return
    }

    if (Start-AppProcess -appDir $appDir -venvPython $venvPython -port 8000) {
        Draw-Box @(
            ("$IconSuccess Processo iniciado com sucesso!")
        ) -Color Green -Title "Sucesso"

        Start-Sleep 2
        Run-HealthCheck -Quick
    } else {
        Draw-Box @(
            ("$IconError Falha ao iniciar processo"),
            ("  Verifique os logs em: $logsDir")
        ) -Color Red -Title "Erro"
    }

    Pause-Continue
}

function Stop-SS54Process {
    Clear-Host
    Draw-Header "PARANDO PROCESSO"

    $status = Get-AppProcessStatus

    if (-not $status.Running) {
        Draw-Box @(
            ("$IconSuccess Processo ja esta parado.")
        ) -Color Green -Title "Status"
        Pause-Continue
        return
    }

    Write-Host "  [G]  Parando processo (PID: $($status.Pid))..." -ForegroundColor Cyan

    if (Stop-AppProcess) {
        Draw-Box @(
            ("$IconSuccess Processo parado com sucesso!")
        ) -Color Green -Title "Sucesso"
    } else {
        Draw-Box @(
            ("$IconError Falha ao parar processo")
        ) -Color Red -Title "Erro"
    }

    Pause-Continue
}

function Restart-SS54Process {
    Clear-Host
    Draw-Header "REINICIANDO PROCESSO"

    Write-Host "  [G]  Parando processo..." -ForegroundColor Cyan
    Stop-AppProcess | Out-Null
    Start-Sleep -Seconds 2

    Write-Host "  [G]  Iniciando processo..." -ForegroundColor Cyan

    $venvPython = Join-Path $appDir "venv\Scripts\python.exe"
    
    if (Start-AppProcess -appDir $appDir -venvPython $venvPython -port 8000) {
        Draw-Box @(
            ("$IconSuccess Processo reiniciado com sucesso!")
        ) -Color Green -Title "Sucesso"

        Start-Sleep 2
        Run-HealthCheck -Quick
    } else {
        Draw-Box @(
            ("$IconError Falha ao reiniciar processo"),
            ("  Verifique os logs em: $logsDir")
        ) -Color Red -Title "Erro"
    }

    Pause-Continue
}

function Edit-ServiceConfig {
    Clear-Host
    Draw-Header "EDITAR CONFIGURACAO DO SERVICO"

    Write-Host "  [G]  Configuracoes atuais:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "    Application:     $( & $NssmPath get $serviceName Application )" -ForegroundColor Gray
    Write-Host "    AppDirectory:     $( & $NssmPath get $serviceName AppDirectory )" -ForegroundColor Gray
    Write-Host "    AppParameters:    $( & $NssmPath get $serviceName AppParameters )" -ForegroundColor Gray
    Write-Host "    AppStdout:        $( & $NssmPath get $serviceName AppStdout )" -ForegroundColor Gray
    Write-Host "    AppStderr:        $( & $NssmPath get $serviceName AppStderr )" -ForegroundColor Gray
    Write-Host "    AppRotateFiles:   $( & $NssmPath get $serviceName AppRotateFiles )" -ForegroundColor Gray
    Write-Host "    AppRotateBytes:    $( & $NssmPath get $serviceName AppRotateBytes )" -ForegroundColor Gray

    Write-Host ""
    Write-Host "  [REF]  Opcoes de edicao:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "    [1] Editar AppParameters (args do Python)" -ForegroundColor White
    Write-Host "    [2] Editar rotacao de logs" -ForegroundColor White
    Write-Host "    [3] Editar tipo de inicio" -ForegroundColor White
    Write-Host "    [0] Voltar" -ForegroundColor Gray

    $choice = Read-Host "`n   Selecione uma opcao"

    switch ($choice) {
        "1" {
            $newParams = Read-Host "`n   Novos AppParameters"
            if ($newParams) {
                & $NssmPath set $serviceName AppParameters $newParams
                Write-Host "`n  [OK]  AppParameters atualizado." -ForegroundColor Green
                Write-Host "  [!]  Reinicie o servico para aplicar mudancas." -ForegroundColor Yellow
            }
        }
        "2" {
            $rotateBytes = Read-Host "`n   Novo AppRotateBytes em bytes (padrao: 1048576 = 1MB)"
            if ($rotateBytes -match '^\d+$') {
                & $NssmPath set $serviceName AppRotateBytes $rotateBytes
                Write-Host "`n  [OK]  Rotacao de logs atualizada." -ForegroundColor Green
            } else {
                Write-Host "`n  [X]  Valor invalido." -ForegroundColor Red
            }
        }
        "3" {
            Write-Host "`n   Tipos de inicio:" -ForegroundColor Cyan
            Write-Host "    [0] Automatic (padrao)" -ForegroundColor Gray
            Write-Host "    [1] Manual" -ForegroundColor Gray
            Write-Host "    [2] Disabled" -ForegroundColor Gray
            $startType = Read-Host "`n   Selecione o tipo de inicio"
            & $NssmPath set $serviceName Start $startType
            Write-Host "`n  [OK]  Tipo de inicio atualizado." -ForegroundColor Green
        }
    }

    Pause-Continue
}

function Run-HealthCheck {
    param([switch]$Quick)

    if (-not $Quick) {
        Clear-Host
        Draw-Header "HEALTH CHECK"
    }

    try {
        $response = Invoke-WebRequest -Uri $healthUrl -Method Get -TimeoutSec 10 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            $content = $response.Content | ConvertFrom-Json

            if ($Quick) {
                Write-Host "`n  [OK]  Health: OK" -ForegroundColor Green
                if ($content.version) {
                    Write-Host "  [REF]  Versao: $($content.version)" -ForegroundColor Gray
                }
            } else {
                Draw-Box @(
                    ("$IconSuccess Status:        $($content.status)"),
                    ("$IconRefresh Timestamp:     $($content.timestamp)"),
                    ("$(if ($content.version) {"$IconR  Versao:         $($content.version)"})")
                ) -Color Green -Title "Health Check PASSOU"
            }
        } else {
            if ($Quick) {
                Write-Host "`n  [X]  Health: FAIL (Status: $($response.StatusCode))" -ForegroundColor Red
            } else {
                Draw-Box @(
                    ("$IconError Health check FALHOU"),
                    ("  Status: $($response.StatusCode)")
                ) -Color Red -Title "Erro"
            }
        }
    } catch {
        if ($Quick) {
            Write-Host "`n  [X]  Health: FAIL ($_) " -ForegroundColor Red
        } else {
            Draw-Box @(
                ("$IconError Health check FALHOU"),
                ("  Erro: $_"),
                ("  Certifique-se de que o servico esta rodando.")
            ) -Color Red -Title "Erro"
        }
    }

    if (-not $Quick) {
        Pause-Continue
    }
}

function Show-AppLogs {
    Clear-Host
    Draw-Header "LOGS DA APLICACAO"

    if (-not (Test-Path $logsDir)) {
        Draw-Box @(
            ("$IconError Diretorio de logs nao encontrado: $logsDir")
        ) -Color Red -Title "Erro"
        Pause-Continue
        return
    }

    Write-Host "  [F]  Arquivos de log disponiveis:" -ForegroundColor Cyan
    Get-ChildItem -Path $logsDir -Filter "*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 5 | ForEach-Object {
        $size = [math]::Round($_.Length / 1KB, 2)
        $modified = $_.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
        Write-Host "    [LG]  $($_.Name) ($size KB - $modified)" -ForegroundColor Gray
    }

    Write-Host ""
    Write-Host "  [T]  Abrindo app.log (ultimas 50 linhas)..." -ForegroundColor Cyan
    Write-Host "  Pressione Ctrl+C para sair." -ForegroundColor Yellow

    if (Test-Path (Join-Path $logsDir "app.log")) {
        Get-Content (Join-Path $logsDir "app.log") -Tail 50 -Wait
    } else {
        Draw-Box @(
            ("$IconError app.log nao encontrado.")
        ) -Color Red -Title "Erro"
        Pause-Continue
    }
}

function Show-StdoutLogs {
    Clear-Host
    Draw-Header "LOGS STDOUT"

    if (Test-Path (Join-Path $logsDir "service-stdout.log")) {
        Write-Host "  [T]  Abrindo service-stdout.log (ultimas 50 linhas)..." -ForegroundColor Cyan
        Write-Host "  Pressione Ctrl+C para sair." -ForegroundColor Yellow
        Get-Content (Join-Path $logsDir "service-stdout.log") -Tail 50 -Wait
    } else {
        Draw-Box @(
            ("$IconError service-stdout.log nao encontrado.")
        ) -Color Red -Title "Erro"
        Pause-Continue
    }
}

function Show-StderrLogs {
    Clear-Host
    Draw-Header "LOGS STDERR"

    if (Test-Path (Join-Path $logsDir "service-stderr.log")) {
        Write-Host "  [T]  Abrindo service-stderr.log (ultimas 50 linhas)..." -ForegroundColor Cyan
        Write-Host "  Pressione Ctrl+C para sair." -ForegroundColor Yellow
        Get-Content (Join-Path $logsDir "service-stderr.log") -Tail 50 -Wait
    } else {
        Draw-Box @(
            ("$IconError service-stderr.log nao encontrado.")
        ) -Color Red -Title "Erro"
        Pause-Continue
    }
}

function Open-LogsDirectory {
    Clear-Host
    Draw-Header "ABRINDO DIRETORIO DE LOGS"

    Write-Host "  [F]  Abrindo diretorio de logs..." -ForegroundColor Cyan
    if (Test-Path $logsDir) {
        Start-Process explorer.exe -ArgumentList $logsDir
        Write-Host "  [OK]  Diretorio aberto!" -ForegroundColor Green
    } else {
        Write-Host "  [X]  Diretorio de logs nao encontrado: $logsDir" -ForegroundColor Red
    }
    Pause-Continue
}

function Show-DatabaseStatus {
    Clear-Host
    Draw-Header "STATUS DO BANCO DE DADOS"

    if (-not (Test-Path $dbCredentialsFile)) {
        Draw-Box @(
            ("$IconError Arquivo de credenciais nao encontrado: $dbCredentialsFile")
        ) -Color Red -Title "Erro"
        Pause-Continue
        return
    }

    $dbCreds = Get-Content $dbCredentialsFile
    Write-Host "  [L]  Credenciais:" -ForegroundColor Cyan
    $dbCreds | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }

    Write-Host ""
    Write-Host "  [DB]  Verificando conexao PostgreSQL..." -ForegroundColor Cyan

    try {
        $result = & psql -U ss54_user -d ss54_db -c "SELECT version();" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK]  Conexao com PostgreSQL funcionando!" -ForegroundColor Green
            Write-Host ""

            Write-Host "  [LG]  Tabelas no banco:" -ForegroundColor Cyan
            $tables = & psql -U ss54_user -d ss54_db -c "\dt" 2>&1
            $tables | Select-Object -Skip 2 | Select-Object -SkipLast 1 | ForEach-Object {
                if ($_ -match '^\|.*\|') {
                    $tableName = ($_ -split '\|')[1].Trim()
                    if ($tableName -ne "") {
                        Write-Host "    [OK]  $tableName" -ForegroundColor Green
                    }
                }
            }

            Write-Host ""
            Write-Host "  [C]  Tamanho do banco:" -ForegroundColor Cyan
            $size = & psql -U ss54_user -d ss54_db -c "SELECT pg_size_pretty(pg_database_size('ss54_db'));" 2>&1 | Select-Object -Skip 2 | Select-Object -SkipLast 1
            Write-Host "    $size" -ForegroundColor Gray
        } else {
            Draw-Box @(
                ("$IconError Nao foi possivel conectar ao PostgreSQL."),
                ("  Verifique se o servico PostgreSQL esta rodando.")
            ) -Color Red -Title "Erro"
        }
    } catch {
        Draw-Box @(
            ("$IconError Erro ao verificar banco de dados: $_")
        ) -Color Red -Title "Erro"
    }

    Pause-Continue
}

function Reset-DatabasePassword {
    Clear-Host
    Draw-Header "RESETAR SENHA DO BANCO DE DADOS"

    Draw-Box @(
        ("$IconWarning  ATENCAO: Isto ira resetar a senha do usuario ss54_user.")
    ) -Color Yellow -Title "Aviso"

    if (-not (Test-Path $dbCredentialsFile)) {
        Draw-Box @(
            ("$IconError Arquivo de credenciais nao encontrado.")
        ) -Color Red -Title "Erro"
        Pause-Continue
        return
    }

    $currentCreds = Get-Content $dbCredentialsFile
    Write-Host "  [L]  Senha atual:" -ForegroundColor Cyan
    $currentCreds | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }

    Write-Host ""
    $newPassword = Read-Host "   Nova senha (deixe vazio para gerar automaticamente)"
    $autoGenerate = -not $newPassword

    if ($autoGenerate) {
        $newPassword = -join (48..57 + 65..90 + 97..122 | Get-Random -Count 32 | % {[char]$_})
        Write-Host "  [OK]  Senha gerada automaticamente." -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "  [L]  Digite a senha do usuario 'postgres' para continuar:" -ForegroundColor Cyan
    $postgresPassword = Read-Host -AsSecureString

    Write-Host ""
    $confirm = Read-Host "   [REF]  Deseja resetar a senha? (s/N)"

    if ($confirm -ne 's' -and $confirm -ne 'S') {
        Write-Host "  [OK]  Operacao cancelada." -ForegroundColor Green
        Pause-Continue
        return
    }

    Write-Host "  [G]  Resetando senha..." -ForegroundColor Cyan

    try {
        $env:PGPASSWORD = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($postgresPassword))

        & psql -U postgres -d ss54_db -c "ALTER USER ss54_user PASSWORD '$newPassword';" 2>&1 | Out-Null

        Remove-Item $dbCredentialsFile -Force -ErrorAction SilentlyContinue
@"
CREDENCIAIS DO BANCO DE DADOS - SS-54
====================================
Host: localhost
Port: 5432
Database: ss54_db
User: ss54_user
Password: $newPassword

IMPORTANTE: GUARDE ESTE ARQUIVO EM LOCAL SEGURO!
NAO compartilhe estes dados com ninguem.
====================================

Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
"@ | Out-File -FilePath $dbCredentialsFile -Encoding UTF8

        Write-Host "  [OK]  Senha resetada com sucesso!" -ForegroundColor Green

        if (Test-Path $envFile) {
            Write-Host "  [G]  Atualizando arquivo .env..." -ForegroundColor Cyan
            $envContent = Get-Content $envFile
            $envContent = $envContent -replace 'DATABASE_URL=.*', "DATABASE_URL=postgresql+psycopg://ss54_user:$newPassword@localhost:5432/ss54_db"
            $envContent | Set-Content $envFile -Encoding UTF8
            Write-Host "  [OK]  Arquivo .env atualizado." -ForegroundColor Green
            Write-Host "  [!]  Reinicie o servico para aplicar mudancas." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  [X]  Falha ao resetar senha: $_" -ForegroundColor Red
    }

    $env:PGPASSWORD = $null
    Pause-Continue
}

function Backup-Database {
    Clear-Host
    Draw-Header "BACKUP DO BANCO DE DADOS"

    $backupDir = Join-Path $installDir "backups"
    if (-not (Test-Path $backupDir)) {
        New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
        Write-Host "  [OK]  Diretorio de backups criado: $backupDir" -ForegroundColor Green
    }

    $timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    $backupFile = Join-Path $backupDir "ss54_db_backup_$timestamp.sql"

    Write-Host "  [DB]  Criando backup em: $backupFile" -ForegroundColor Cyan
    Write-Host "  Aguarde" -ForegroundColor Yellow -NoNewline

    try {
        & pg_dump -U ss54_user -d ss54_db -f $backupFile 2>&1 | Out-Null

        Write-Host "." -NoNewline -ForegroundColor Yellow

        if ($LASTEXITCODE -eq 0) {
            $size = [math]::Round((Get-Item $backupFile).Length / 1MB, 2)
            Write-Host ""
            Draw-Box @(
                ("$IconSuccess Backup concluido!"),
                ("  Arquivo: $backupFile"),
                ("  Tamanho: $size MB")
            ) -Color Green -Title "Sucesso"
        } else {
            Write-Host ""
            Draw-Box @(
                ("$IconError Falha ao criar backup.")
            ) -Color Red -Title "Erro"
        }
    } catch {
        Write-Host ""
        Draw-Box @(
            ("$IconError Erro ao criar backup: $_")
        ) -Color Red -Title "Erro"
    }

    Pause-Continue
}

function Edit-EnvFile {
    Clear-Host
    Draw-Header "EDITAR ARQUIVO .ENV"

    if (-not (Test-Path $envFile)) {
        Draw-Box @(
            ("$IconError Arquivo .env nao encontrado: $envFile")
        ) -Color Red -Title "Erro"
        Pause-Continue
        return
    }

    Write-Host "  [G]  Abrindo arquivo .env..." -ForegroundColor Cyan
    notepad.exe $envFile

    Write-Host ""
    $reload = Read-Host "  [REF]  Deseja reiniciar o servico para aplicar mudancas? (s/N)"
    if ($reload -eq 's' -or $reload -eq 'S') {
        Restart-SS54Service
    }
}

function Show-TunnelStatus {
    Clear-Host
    Draw-Header "STATUS DO CLOUDFLARE TUNNEL"
    
    Get-CloudflareTunnelStatus
    
    Pause-Continue
}

function Start-CloudflareTunnelFromMenu {
    Clear-Host
    Draw-Header "INICIAR CLOUDFLARE TUNNEL"
    
    Write-Host "  [W]  Iniciando tunnel..." -ForegroundColor Cyan
    
    $subdomain = Read-Host "   Subdominio (deixe vazio para dominio raiz '$cloudflareDomain')"
    
    if (Start-CloudflareTunnel -Port 8000 -Domain $cloudflareDomain -Subdomain $subdomain) {
        $hostname = if ($subdomain) { "$subdomain.$cloudflareDomain" } else { $cloudflareDomain }
        Draw-Box @(
            ("$IconSuccess Tunnel iniciado com sucesso!"),
            ("  Acesse: https://$hostname")
        ) -Color Green -Title "Sucesso"
    } else {
        Draw-Box @(
            ("$IconError Falha ao iniciar tunnel."),
            ("  Verifique se o tunnel foi configurado."),
            ("  Execute: .\scripts\cloudflare\setup.ps1")
        ) -Color Red -Title "Erro"
    }
    
    Pause-Continue
}

function Stop-CloudflareTunnelFromMenu {
    Clear-Host
    Draw-Header "PARAR CLOUDFLARE TUNNEL"
    
    if (Stop-CloudflareTunnel) {
        Draw-Box @(
            ("$IconSuccess Tunnel parado com sucesso!")
        ) -Color Green -Title "Sucesso"
    } else {
        Draw-Box @(
            ("$IconError Falha ao parar tunnel.")
        ) -Color Red -Title "Erro"
    }
    
    Pause-Continue
}

function Reload-Configuration {
    Clear-Host
    Draw-Header "RECARREGAR CONFIGURACAO"

    Write-Host "  [L]  Lendo arquivo .env..." -ForegroundColor Cyan
    if (Test-Path $envFile) {
        $lines = Get-Content $envFile
        $displayLines = $lines | Select-Object -First 20
        $displayLines | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
        if ($lines.Count -gt 20) {
            Write-Host ("    ... (+$($lines.Count - 20) linhas)") -ForegroundColor Yellow
        }
    } else {
        Draw-Box @(
            ("$IconError Arquivo .env nao encontrado.")
        ) -Color Red -Title "Erro"
        Pause-Continue
        return
    }

    Write-Host ""
    $confirm = Read-Host "  [REF]  Deseja reiniciar o servico para recarregar configuracao? (s/N)"

    if ($confirm -eq 's' -or $confirm -eq 'S') {
        Restart-SS54Service
    } else {
        Pause-Continue
    }
}

function Show-SystemInfo {
    Clear-Host
    Draw-Header "INFORMACOES DO SISTEMA"

    Write-Host "  [C]  Sistema:" -ForegroundColor Cyan
    Write-Host ("    OS:           $([System.Environment]::OSVersion.VersionString)") -ForegroundColor Gray
    Write-Host ("    Maquina:      $env:COMPUTERNAME") -ForegroundColor Gray
    Write-Host ("    Usuario:       $env:USERNAME") -ForegroundColor Gray

    Write-Host ""
    Write-Host "  [R]  Hardware:" -ForegroundColor Cyan
    $ram = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)
    Write-Host ("    RAM:          $ram GB") -ForegroundColor Gray
    $cpu = Get-CimInstance Win32_Processor
    Write-Host ("    CPU:          $($cpu.Name)") -ForegroundColor Gray
    Write-Host ("    Cores:        $($cpu.NumberOfCores)") -ForegroundColor Gray

    Write-Host ""
    Write-Host "  [F]  Diretorios:" -ForegroundColor Cyan
    Write-Host ("    Install Dir:  $installDir") -ForegroundColor Gray
    Write-Host ("    App Dir:      $appDir") -ForegroundColor Gray
    Write-Host ("    Logs Dir:     $logsDir") -ForegroundColor Gray

    Write-Host ""
    Write-Host "  [G]  Servicos:" -ForegroundColor Cyan
    
    if ($runMode -eq "service") {
        $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
        if ($service) {
            $statusColor = if ($service.Status -eq "Running") { "Green" } else { "Red" }
            $statusIcon = if ($service.Status -eq "Running") { $IconSuccess } else { $IconError }
            Write-Host ("    $statusIcon  SS54Backend:  $($service.Status)") -ForegroundColor $statusColor
        } else {
            Write-Host "    [!]  SS54Backend:  NAO INSTALADO" -ForegroundColor Yellow
        }
    } elseif ($runMode -eq "process") {
        $processStatus = Get-AppProcessStatus
        if ($processStatus.Running) {
            Write-Host ("    $IconSuccess  SS54Backend:  RODANDO (PID: $($processStatus.Pid))") -ForegroundColor Green
        } else {
            Write-Host ("    [!]  SS54Backend:  PARADO") -ForegroundColor Yellow
        }
    } else {
        Write-Host "    [!]  SS54Backend:  NAO CONFIGURADO" -ForegroundColor Yellow
    }
    
    $tunnelProcess = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
    if ($tunnelProcess) {
        Write-Host ("    $IconSuccess  Cloudflare Tunnel:  Rodando (PID: $($tunnelProcess.Id))") -ForegroundColor Green
    } else {
        Write-Host ("    [!]  Cloudflare Tunnel:  Parado") -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "  [T]  Processos:" -ForegroundColor Cyan
    $processes = Get-Process | Where-Object { $_.ProcessName -like "*python*" -or $_.ProcessName -like "*postgres*" } | Select-Object -First 10
    $processes | ForEach-Object {
        Write-Host ("    [G]  $($_.ProcessName.PadRight(15)) PID: $($_.Id.ToString().PadLeft(6)) RAM: $([math]::Round($_.WorkingSet64/1MB, 1).ToString().PadLeft(6)) MB") -ForegroundColor Gray
    }

    Write-Host ""
    Write-Host "  [W]  Rede:" -ForegroundColor Cyan
    $ipconfig = Get-NetIPAddress | Where-Object { $_.AddressFamily -eq "IPv4" -and $_.IPAddress -ne "127.0.0.1" }
    $ipconfig | ForEach-Object {
        Write-Host ("    [W]  $($_.InterfaceAlias): $($_.IPAddress)") -ForegroundColor Gray
    }

    Pause-Continue
}

function Update-Application {
    Clear-Host
    Draw-Header "ATUALIZAR APLICACAO"

    Draw-Box @(
        ("$IconWarning  ATENCAO: Isto ira atualizar a aplicacao do repositorio GitHub."),
        ("  Recomendado faca backup antes de atualizar.")
    ) -Color Yellow -Title "Aviso"

    $confirm = Read-Host "`n   [REF]  Deseja continuar? (s/N)"

    if ($confirm -ne 's' -and $confirm -ne 'S') {
        Write-Host "  [OK]  Atualizacao cancelada." -ForegroundColor Green
        Pause-Continue
        return
    }

    Write-Host "  [G]  Parando servico..." -ForegroundColor Cyan
    Stop-Service -Name $serviceName -ErrorAction SilentlyContinue

    Write-Host "  [DB]  Atualizando repositorio git..." -ForegroundColor Cyan
    Set-Location $appDir
    & git fetch origin 2>&1 | Out-Null
    & git pull origin main 2>&1 | Out-Null

    Write-Host "  [G]  Atualizando dependencias Python..." -ForegroundColor Cyan
    $venvPython = Join-Path $appDir "venv\Scripts\python.exe"
    & $venvPython -m pip install -r requirements.txt --upgrade 2>&1 | Out-Null

    Write-Host "  [OK]  Aplicacao atualizada!" -ForegroundColor Green
    Write-Host "  [G]  Iniciando servico..." -ForegroundColor Cyan
    Start-Service -Name $serviceName -ErrorAction SilentlyContinue

    Pause-Continue
}

function Show-Help {
    Clear-Host
    Draw-Header "AJUDA DO SERVICE MANAGER"

    Draw-Box @(
        ("SS-54 SERVICE MANAGER v$ScriptVersion"),
        (""),
        ("Uso: .\service-manager.ps1 [OPCAO]"),
        (""),
        ("Opcoes:"),
        ("  --help, -h          Mostra esta ajuda"),
        (""),
        ("Menu interativo (sem opcoes):"),
        ("  Abre o menu interativo com todas as opcoes"),
        (""),
        ("Exemplos:"),
        ("  .\service-manager.ps1              Abre o menu interativo"),
        ("  .\service-manager.ps1 --help       Mostra esta ajuda")
    ) -Color Cyan -Title "Ajuda"
}

if ($Help) {
    Show-Help
    exit 0
}

if ($Action) {
    Draw-Box @(
        ("[!]  Modo de comando unico nao implementado ainda."),
        ("  Use o menu interativo.")
    ) -Color Yellow -Title "Aviso"
    exit 1
}

while ($true) {
    Show-Menu
}
