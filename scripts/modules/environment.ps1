function Test-EnvironmentRequirements {
    Write-Section "VALIDACAO DO AMBIENTE"
    Write-Info "Verificando requisitos do sistema..."

    $osVersion = [Environment]::OSVersion.VersionString

    Write-Info "Verificando versao do Windows..."

    if ($osVersion -match "Windows 10" -or $osVersion -match "Windows 11" -or $osVersion -match "Windows NT 10" -or $osVersion -match "Server 2019" -or $osVersion -match "Server 2022") {
        Write-Success "Windows $osVersion detectado"
    } else {
        Write-Error "Windows nao suportado: $osVersion"
        Write-Error "Requisito: Windows 10/11 Pro ou Server 2019+"
        Stop-Script 1
    }

    Write-Info "Verificando privilegios de administrador..."
    Add-Type -AssemblyName System.Security.Principal
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

    if ($isAdmin) {
        Write-Success "Executando como Administrador"
    } else {
        Write-Error "Este script requer privilegios de administrador"
        Write-Info "Execute novamente como Administrador:"
        Write-Info "  1. Clique direito no script"
        Write-Info "  2. Selecione 'Executar como administrador'"
        Stop-Script 1
    }

    Write-Info "Verificando memoria RAM..."
    $ram = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)
    Write-Success "$ram GB de RAM detectados"

    if ($ram -lt 4) {
        Write-Warning "Menos de 4GB de RAM detectados. 4GB+ recomendados."
        $continue = Read-Host "Deseja continuar? [S/n]"
        if ($continue -notmatch "^[SsYy]$") {
            Write-Info "Deploy cancelado pelo usuario."
            Stop-Script 0
        }
    }

    Write-Info "Verificando espaco em disco..."
    $driveLetter = (Get-Location).Drive.Name
    $freeSpace = [math]::Round((Get-PSDrive -Name $driveLetter).Free / 1GB, 2)
    Write-Success "$freeSpace GB livres em ${driveLetter}:\"

    if ($freeSpace -lt 20) {
        Write-Error "Menos de 20GB livres detectados. 20GB+ recomendados."
        $continue = Read-Host "Deseja continuar? [S/n]"
        if ($continue -notmatch "^[SsYy]$") {
            Write-Info "Deploy cancelado pelo usuario."
            Stop-Script 0
        }
    }

    $pythonInstalled = $false
    $pythonCmd = $null

    Write-Info "Verificando Python 3.11+..."

    try {
        $pythonVersion = & python --version 2>&1
        if ($pythonVersion -match "Python 3\.1[1-9]") {
            Write-Success "Python $pythonVersion detectado"
            $pythonInstalled = $true
            $pythonCmd = "python"
        } elseif ($pythonVersion -match "Python 3\.[0-9]") {
            Write-Warning "Python $pythonVersion detectado, mas 3.11+ necessario"
        }
    } catch {}

    if (-not $pythonInstalled) {
        try {
            $pythonVersion = & py --version 2>&1
            if ($pythonVersion -match "Python 3\.1[1-9]") {
                Write-Success "Python $pythonVersion detectado (via py launcher)"
                $pythonInstalled = $true
                $pythonCmd = "py"
            } elseif ($pythonVersion -match "Python 3\.[0-9]") {
                Write-Warning "Python $pythonVersion detectado, mas 3.11+ necessario"
            }
        } catch {}
    }

    if (-not $pythonInstalled) {
        Write-Warning "Python 3.11+ nao encontrado"
    }

    if (-not $pythonInstalled) {
        Write-Info "Python 3.11+ nao encontrado. Vou baixar o instalador."
        $autoInstall = Read-Host "Deseja baixar e instalar automaticamente? [S/n]"

        if ($autoInstall -match "^[SsYy]$") {
            Write-Info "Baixando Python 3.11..."
            try {
                $pythonUrl = "https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe"
                $pythonInstaller = "$env:TEMP\python-3.11.0-installer.exe"
                Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller -UseBasicParsing

                Write-Success "Download concluido"
                Write-Info "Iniciando instalador do Python..."
                Write-Info "IMPORTANTE: Marque 'Add Python to PATH' durante a instalacao"
                Start-Process $pythonInstaller -Wait

                Write-Success "Python 3.11 instalado"
                Pause-Continue

                $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
                $pythonInstalled = $true
                $pythonCmd = "python"
            } catch {
                Write-Error "Falha ao baixar Python 3.11"
                Write-Info "Instrucoes de instalacao manual:"
                Write-Info "  1. Acesse: https://www.python.org/downloads/"
                Write-Info "  2. Baixe Python 3.11+"
                Write-Info "  3. Execute o instalador"
                Write-Info "  4. MARQUE 'Add Python to PATH'"

                $continue = Read-Host "Deseja continuar sem Python? [S/n]"
                if ($continue -notmatch "^[SsYy]$") {
                    Write-Info "Deploy cancelado pelo usuario."
                    Stop-Script 0
                }
            }
        } else {
            Write-Info "Instrucoes de instalacao manual:"
            Write-Info "  1. Acesse: https://www.python.org/downloads/"
            Write-Info "  2. Baixe Python 3.11+"
            Write-Info "  3. Execute o instalador"
            Write-Info "  4. MARQUE 'Add Python to PATH'"

            $continue = Read-Host "Deseja continuar sem Python? [S/n]"
            if ($continue -notmatch "^[SsYy]$") {
                Write-Info "Deploy cancelado pelo usuario."
                Stop-Script 0
            }
        }
    }

    $postgresInstalled = $false
    $postgresBinPath = $null
    $psqlCmd = "psql"

    Write-Info "Verificando PostgreSQL 15+..."

    try {
        $postgresVersion = & $psqlCmd --version 2>&1
        if ($postgresVersion -match "1[5-9]\.\d") {
            Write-Success "PostgreSQL $postgresVersion detectado"
            $postgresInstalled = $true
        } else {
            Write-Warning "PostgreSQL $postgresVersion detectado, mas 15+ necessario"
        }
    } catch {}

    if (-not $postgresInstalled) {
        $postgresDirs = @(
            "C:\Program Files\PostgreSQL",
            "${env:ProgramFiles}\PostgreSQL",
            "C:\Program Files (x86)\PostgreSQL"
        )

        foreach ($dir in $postgresDirs) {
            if (Test-Path $dir) {
                $versions = Get-ChildItem -Path $dir -Directory | Where-Object { $_.Name -match "^\d+$" } | Sort-Object -Descending
                foreach ($v in $versions) {
                    $binPath = Join-Path $v.FullName "bin"
                    $psqlPath = Join-Path $binPath "psql.exe"
                    if (Test-Path $psqlPath) {
                        try {
                            $postgresVersion = & $psqlPath --version 2>&1
                            if ($postgresVersion -match "1[5-9]\.\d") {
                                Write-Success "PostgreSQL $postgresVersion detectado em $binPath"
                                $postgresInstalled = $true
                                $postgresBinPath = $binPath
                                $env:Path = "$binPath;$env:Path"
                                break
                            }
                        } catch {}
                    }
                }
                if ($postgresInstalled) { break }
            }
        }
    }

    if (-not $postgresInstalled) {
        Write-Warning "PostgreSQL nao encontrado"
    }

    if ($postgresBinPath) {
        $psqlCmd = Join-Path $postgresBinPath "psql.exe"
    }

    if (-not $postgresInstalled) {
        Write-Info "PostgreSQL nao encontrado. Vou baixar o instalador."
        $autoInstall = Read-Host "Deseja baixar e instalar automaticamente? [S/n]"

        if ($autoInstall -match "^[SsYy]$") {
            Write-Info "Baixando instalador do PostgreSQL..."
            try {
                $postgresUrl = "https://get.enterprisedb.com/postgresql/postgresql-15.0-1-windows-x64.exe"
                $postgresInstaller = "$env:TEMP\postgresql-installer.exe"

                Invoke-WebRequest -Uri $postgresUrl -OutFile $postgresInstaller -UseBasicParsing

                Write-Success "Download concluido"
                Write-Info "Iniciando instalador do PostgreSQL..."
                Write-Info "IMPORTANTE:"
                Write-Info "  - Anote a senha do usuario 'postgres' que voce definir"
                Write-Info "  - Mantenha a porta padrao: 5432"
                Write-Info "  - Instale o pgAdmin 4 (incluido)"

                Start-Process $postgresInstaller -Wait

                Write-Success "PostgreSQL instalado"
                Write-Info "IMPORTANTE: Execute este script novamente apos instalar PostgreSQL"
                Write-Info "O script precisa detectar a instalacao para continuar."
                Stop-Script 0
            } catch {
                Write-Error "Falha ao baixar PostgreSQL"
                Write-Info "Instrucoes de instalacao manual:"
                Write-Info "  1. Acesse: https://www.postgresql.org/download/windows/"
                Write-Info "  2. Baixe PostgreSQL 15+"
                Write-Info "  3. Execute o instalador"
                Write-Info "  4. Defina senha do usuario 'postgres' (ANOTE ESTA SENHA!)"
                Write-Info "  5. Mantenha porta 5432"
                Write-Info "  6. Instale pgAdmin 4"

                $continue = Read-Host "Deseja continuar sem PostgreSQL? [S/n]"
                if ($continue -notmatch "^[SsYy]$") {
                    Write-Info "Deploy cancelado pelo usuario."
                    Stop-Script 0
                }
            }
        } else {
            Write-Info "Instrucoes de instalacao manual:"
            Write-Info "  1. Acesse: https://www.postgresql.org/download/windows/"
            Write-Info "  2. Baixe PostgreSQL 15+"
            Write-Info "  3. Execute o instalador"
            Write-Info "  4. Defina senha do usuario 'postgres' (ANOTE ESTA SENHA!)"
            Write-Info "  5. Mantenha porta 5432"
            Write-Info "  6. Instale pgAdmin 4"
            Write-Info "  7. Execute este script novamente apos instalar"

            $continue = Read-Host "Deseja continuar sem PostgreSQL? [S/n]"
            if ($continue -notmatch "^[SsYy]$") {
                Write-Info "Deploy cancelado pelo usuario."
                Stop-Script 0
            }
        }
    }

    $gitInstalled = $false

    Write-Info "Verificando Git..."

    try {
        $gitVersion = & git --version 2>&1
        if ($gitVersion -match "git version") {
            Write-Success "Git $gitVersion detectado"
            $gitInstalled = $true
        }
    } catch {}

    if (-not $gitInstalled) {
        $gitDirs = @(
            "C:\Program Files\Git",
            "C:\Program Files (x86)\Git",
            "${env:ProgramFiles}\Git",
            "${env:ProgramFiles(x86)}\Git"
        )

        foreach ($dir in $gitDirs) {
            $gitExe = Join-Path $dir "bin\git.exe"
            if (Test-Path $gitExe) {
                try {
                    $gitVersion = & $gitExe --version 2>&1
                    if ($gitVersion -match "git version") {
                        $binPath = Join-Path $dir "bin"
                        Write-Success "Git $gitVersion detectado em $binPath"
                        $gitInstalled = $true
                        $env:Path = "$binPath;$env:Path"
                        break
                    }
                } catch {}
            }
        }
    }

    if (-not $gitInstalled) {
        Write-Warning "Git nao encontrado"
    }

    if (-not $gitInstalled) {
        Write-Info "Git nao encontrado. Vou baixar e instalar automaticamente."
        $autoInstall = Read-Host "Deseja baixar e instalar automaticamente? [S/n]"

        if ($autoInstall -match "^[SsYy]$") {
            Write-Info "Baixando instalador do Git..."
            try {
                $gitUrl = "https://github.com/git-for-windows/git/releases/download/v2.47.0.windows.1/Git-2.47.0-64-bit.exe"
                $gitInstaller = "$env:TEMP\git-installer.exe"

                Invoke-WebRequest -Uri $gitUrl -OutFile $gitInstaller -UseBasicParsing

                Write-Success "Download concluido"
                Write-Info "Instalando Git..."

                $process = Start-Process $gitInstaller -ArgumentList "/VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS" -PassThru -Wait
                Write-Success "Git instalado"

                $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
                Pause-Continue
                $gitInstalled = $true
            } catch {
                Write-Error "Falha ao baixar ou instalar Git"
                Write-Info "Instrucoes de instalacao manual:"
                Write-Info "  1. Acesse: https://git-scm.com/download/win"
                Write-Info "  2. Baixe o instalador para Windows"
                Write-Info "  3. Execute o instalador"

                $continue = Read-Host "Deseja continuar sem Git? [S/n]"
                if ($continue -notmatch "^[SsYy]$") {
                    Write-Info "Deploy cancelado pelo usuario."
                    Stop-Script 0
                }
            }
        } else {
            Write-Info "Instrucoes de instalacao manual:"
            Write-Info "  1. Acesse: https://git-scm.com/download/win"
            Write-Info "  2. Baixe o instalador para Windows"
            Write-Info "  3. Execute o instalador"

            $continue = Read-Host "Deseja continuar sem Git? [S/n]"
            if ($continue -notmatch "^[SsYy]$") {
                Write-Info "Deploy cancelado pelo usuario."
                Stop-Script 0
            }
        }
    }

    $cppInstalled = $false

    Write-Info "Verificando Visual C++ Redistributable..."
    $registryPath = "HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"
    $vcRedistVersion = Get-ItemProperty -Path $registryPath -ErrorAction SilentlyContinue

    if ($vcRedistVersion) {
        Write-Success "Visual C++ Redistributable detectado"
        $cppInstalled = $true
    } else {
        Write-Warning "Visual C++ Redistributable nao encontrado"
    }

    if (-not $cppInstalled) {
        Write-Info "Visual C++ Redistributable e necessario para alguns pacotes Python."
        $autoInstall = Read-Host "Deseja baixar e instalar automaticamente? [S/n]"

        if ($autoInstall -match "^[SsYy]$") {
            Write-Info "Baixando Visual C++ Redistributable..."
            try {
                $vcUrl = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
                $vcInstaller = "$env:TEMP\vc_redist.x64.exe"

                Invoke-WebRequest -Uri $vcUrl -OutFile $vcInstaller -UseBasicParsing

                Write-Success "Download concluido"
                Write-Info "Instalando Visual C++ Redistributable..."

                Start-Process $vcInstaller -ArgumentList "/install /quiet /norestart" -PassThru -Wait
                Write-Success "Visual C++ Redistributable instalado"
            } catch {
                Write-Error "Falha ao baixar ou instalar Visual C++ Redistributable"
                Write-Info "Instrucoes de instalacao manual:"
                Write-Info "  1. Acesse: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist"
                Write-Info "  2. Baixe: VC_redist.x64.exe"
                Write-Info "  3. Execute o instalador"

                $continue = Read-Host "Deseja continuar sem Visual C++? [S/n]"
                if ($continue -notmatch "^[SsYy]$") {
                    Write-Info "Deploy cancelado pelo usuario."
                    Stop-Script 0
                }
            }
        } else {
            Write-Info "Instrucoes de instalacao manual:"
            Write-Info "  1. Acesse: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist"
            Write-Info "  2. Baixe: VC_redist.x64.exe"
            Write-Info "  3. Execute o instalador"

            $continue = Read-Host "Deseja continuar sem Visual C++? [S/n]"
            if ($continue -notmatch "^[SsYy]$") {
                Write-Info "Deploy cancelado pelo usuario."
                Stop-Script 0
            }
        }
    }

    return [PSCustomObject]@{
        pythonInstalled = $pythonInstalled
        pythonCmd = $pythonCmd
        postgresInstalled = $postgresInstalled
        postgresBinPath = $postgresBinPath
        psqlCmd = $psqlCmd
        gitInstalled = $gitInstalled
        cppInstalled = $cppInstalled
    }
}

