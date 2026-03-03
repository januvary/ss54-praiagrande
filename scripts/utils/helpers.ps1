function Test-Command($command) {
    try {
        $null = Invoke-Expression "$command 2>&1"
        return $true
    } catch {
        return $false
    }
}

function Pause-Continue {
    Write-Host ""
    $null = Read-Host "Pressione Enter para continuar"
    Write-Host ""
}

function Stop-Script($code) {
    Write-Host ""
    Write-Host "Pressione Enter para sair..." -ForegroundColor $Colors.Warning
    $null = Read-Host
    exit $code
}

function Get-ConfigValue($key, $prompt, $defaultValue, $secure = $false) {
    if ($ExistingConfig.ContainsKey($key)) {
        $existingValue = $ExistingConfig[$key]
        Write-Host "" -ForegroundColor $Colors.Info
        Write-Host "[Config existente detectado]" -ForegroundColor $Colors.Success
        Write-Host "  $key = $existingValue" -ForegroundColor $Colors.Success

        $choice = Read-Host "Usar este valor? [S/n]"
        if ($choice -notmatch "^[Nn]$") {
            if ($key -eq "ADMIN_PASSWORD_HASH") {
                return $existingValue
            }
            return $existingValue
        }
    }

    if ($secure) {
        return Read-Host $prompt -AsSecureString
    } else {
        $input = Read-Host "$prompt [$defaultValue]"
        if (-not $input) { return $defaultValue }
        return $input
    }
}

