# ==============================================================================
# SS-54 Cloudflare Tunnel Module for Windows
# ==============================================================================

$Script:CloudflaredVersion = "2024.1.5"
$Script:CloudflaredDir = Join-Path $env:USERPROFILE "Apps\cloudflared"
$Script:CloudflaredExe = Join-Path $Script:CloudflaredDir "cloudflared.exe"
$Script:TunnelName = "ss54-backend"
$Script:TunnelConfigDir = Join-Path $env:USERPROFILE ".cloudflared"
$Script:DefaultDomain = "ss54pg.com.br"



function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Test-CloudflaredInstalled {
    if (Get-Command cloudflared -ErrorAction SilentlyContinue) {
        return $true
    }
    
    if (Test-Path $Script:CloudflaredExe) {
        return $true
    }
    
    return $false
}

function Get-CloudflaredPath {
    if (Get-Command cloudflared -ErrorAction SilentlyContinue) {
        return "cloudflared"
    }
    
    if (Test-Path $Script:CloudflaredExe) {
        return $Script:CloudflaredExe
    }
    
    return $null
}

function Install-Cloudflared {
    Write-Info "Installing Cloudflare Tunnel (cloudflared)..."
    
    if (Test-CloudflaredInstalled) {
        Write-Success "Cloudflared already installed"
        return $true
    }
    
    if (-not (Test-Path $Script:CloudflaredDir)) {
        New-Item -ItemType Directory -Path $Script:CloudflaredDir -Force | Out-Null
    }
    
    $url = "https://github.com/cloudflare/cloudflared/releases/download/cloudflared-windows-amd64.exe/cloudflared-windows-amd64.exe"
    
    try {
        Write-Info "Downloading cloudflared..."
        Invoke-WebRequest -Uri $url -OutFile $Script:CloudflaredExe -UseBasicParsing
        Write-Success "Cloudflared installed to: $Script:CloudflaredExe"
        return $true
    } catch {
        Write-Error "Failed to download cloudflared: $_"
        Write-Info "Please install manually from: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
        return $false
    }
}

function Test-CloudflareAuth {
    $cloudflared = Get-CloudflaredPath
    if (-not $cloudflared) {
        return $false
    }
    
    try {
        $result = & $cloudflared tunnel list 2>&1
        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    } catch {}
    
    return $false
}

function Initialize-CloudflareAuth {
    Write-Info "Authenticating with Cloudflare..."
    
    if (Test-CloudflareAuth) {
        Write-Success "Already authenticated with Cloudflare"
        return $true
    }
    
    $cloudflared = Get-CloudflaredPath
    if (-not $cloudflared) {
        Write-Error "Cloudflared not found"
        return $false
    }
    
    Write-Info "A browser window will open for authentication..."
    Write-Info "Please select your domain (ss54pg.com.br) and authorize"
    
    try {
        & $cloudflared tunnel login
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Authentication successful"
            return $true
        } else {
            Write-Error "Authentication failed"
            return $false
        }
    } catch {
        Write-Error "Authentication error: $_"
        return $false
    }
}

function Test-CloudflareTunnel {
    param([string]$TunnelName = $Script:TunnelName)
    
    $cloudflared = Get-CloudflaredPath
    if (-not $cloudflared) {
        return $false
    }
    
    try {
        $result = & $cloudflared tunnel list --output json 2>&1 | ConvertFrom-Json
        $tunnel = $result | Where-Object { $_.Name -eq $TunnelName }
        if ($tunnel) {
            return $true
        }
    } catch {}
    
    return $false
}

function Get-CloudflareTunnelID {
    param([string]$TunnelName = $Script:TunnelName)
    
    $cloudflared = Get-CloudflaredPath
    if (-not $cloudflared) {
        return $null
    }
    
    try {
        $result = & $cloudflared tunnel list --output json 2>&1 | ConvertFrom-Json
        $tunnel = $result | Where-Object { $_.Name -eq $TunnelName }
        if ($tunnel) {
            return $tunnel.ID
        }
    } catch {}
    
    return $null
}

function New-CloudflareTunnel {
    param(
        [string]$TunnelName = $Script:TunnelName,
        [string]$Domain = $Script:DefaultDomain
    )
    
    Write-Info "Creating Cloudflare Tunnel..."
    
    if (Test-CloudflareTunnel -TunnelName $TunnelName) {
        Write-Success "Tunnel '$TunnelName' already exists"
        return $true
    }
    
    $cloudflared = Get-CloudflaredPath
    if (-not $cloudflared) {
        Write-Error "Cloudflared not found"
        return $false
    }
    
    try {
        & $cloudflared tunnel create $TunnelName 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Tunnel '$TunnelName' created"
            
            $tunnelID = Get-CloudflareTunnelID -TunnelName $TunnelName
            if ($tunnelID) {
                Write-Info "Tunnel ID: $tunnelID"
            }
            
            return $true
        } else {
            Write-Error "Failed to create tunnel"
            return $false
        }
    } catch {
        Write-Error "Error creating tunnel: $_"
        return $false
    }
}

function Set-CloudflareDNS {
    param(
        [string]$TunnelName = $Script:TunnelName,
        [string]$Domain = $Script:DefaultDomain,
        [string]$Subdomain = ""
    )
    
    $cloudflared = Get-CloudflaredPath
    if (-not $cloudflared) {
        Write-Error "Cloudflared not found"
        return $false
    }
    
    $hostname = if ($Subdomain) { "$Subdomain.$Domain" } else { $Domain }
    
    Write-Info "Configuring DNS for $hostname..."
    
    try {
        & $cloudflared tunnel route dns $TunnelName $hostname 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "DNS configured: $hostname → $TunnelName"
            return $true
        } else {
            Write-Warning "DNS configuration may already exist"
            return $true
        }
    } catch {
        Write-Warning "DNS configuration error (may already exist): $_"
        return $true
    }
}

function Start-CloudflareTunnel {
    param(
        [string]$TunnelName = $Script:TunnelName,
        [int]$Port = 8000,
        [string]$Domain = $Script:DefaultDomain,
        [string]$Subdomain = ""
    )
    
    Write-Info "Starting Cloudflare Tunnel..."
    
    $cloudflared = Get-CloudflaredPath
    if (-not $cloudflared) {
        Write-Error "Cloudflared not found"
        return $false
    }
    
    if (-not (Test-CloudflareTunnel -TunnelName $TunnelName)) {
        Write-Error "Tunnel '$TunnelName' does not exist"
        return $false
    }
    
    $hostname = if ($Subdomain) { "$Subdomain.$Domain" } else { $Domain }
    
    $tunnelConfig = @"
tunnel: $TunnelName
credentials-file: $(Join-Path $Script:TunnelConfigDir "$TunnelName.json")

ingress:
  - hostname: $hostname
    service: http://localhost:$Port
  - hostname: www.$hostname
    service: http://localhost:$Port
  - service: http_status:404
"@
    
    $configFile = Join-Path $Script:TunnelConfigDir "config.yml"
    if (-not (Test-Path $Script:TunnelConfigDir)) {
        New-Item -ItemType Directory -Path $Script:TunnelConfigDir -Force | Out-Null
    }
    
    $tunnelConfig | Out-File -FilePath $configFile -Encoding UTF8
    
    $process = Start-Process -FilePath $cloudflared -ArgumentList "tunnel", "--config", $configFile, "run", $TunnelName -WindowStyle Hidden -PassThru
    
    if ($process) {
        Start-Sleep -Seconds 3
        
        if (-not $process.HasExited) {
            Write-Success "Tunnel started successfully"
            Write-Info "Access your app at: https://$hostname"
            return $true
        } else {
            Write-Error "Tunnel process exited unexpectedly"
            return $false
        }
    } else {
        Write-Error "Failed to start tunnel process"
        return $false
    }
}

function Stop-CloudflareTunnel {
    Write-Info "Stopping Cloudflare Tunnel..."
    
    $processes = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
    if ($processes) {
        $processes | Stop-Process -Force
        Write-Success "Tunnel stopped"
    } else {
        Write-Info "No tunnel process found"
    }
    
    return $true
}

function Get-CloudflareTunnelStatus {
    param([string]$TunnelName = $Script:TunnelName)
    
    $cloudflared = Get-CloudflaredPath
    
    Write-ColorOutput "`nCloudflare Tunnel Status:" "Cyan"
    Write-ColorOutput "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "Cyan"
    
    if (-not $cloudflared) {
        Write-Warning "Cloudflared not installed"
        Write-Info "Run: .\deploy-user.ps1 tunnel-setup"
        return
    }
    
    Write-Success "Cloudflared: Installed"
    
    if (Test-CloudflareAuth) {
        Write-Success "Authentication: Configured"
    } else {
        Write-Warning "Authentication: Not configured"
        Write-Info "Run: .\deploy-user.ps1 tunnel-setup"
        return
    }
    
    if (Test-CloudflareTunnel -TunnelName $TunnelName) {
        $tunnelID = Get-CloudflareTunnelID -TunnelName $TunnelName
        Write-Success "Tunnel: $TunnelName ($tunnelID)"
        
        $processes = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
        if ($processes) {
            Write-Success "Status: Running"
            Write-Info "Access: https://$Script:DefaultDomain"
        } else {
            Write-Warning "Status: Stopped"
            Write-Info "Start: .\deploy-user.ps1 tunnel-start"
        }
    } else {
        Write-Warning "Tunnel: Not created"
        Write-Info "Run: .\deploy-user.ps1 tunnel-setup"
    }
}

function Initialize-CloudflareTunnel {
    param(
        [int]$Port = 8000,
        [string]$Domain = $Script:DefaultDomain,
        [string]$Subdomain = ""
    )
    
    Write-ColorOutput "`n━━━ Cloudflare Tunnel Setup ━━━" "Magenta"
    
    if (-not (Install-Cloudflared)) {
        return $false
    }
    
    if (-not (Initialize-CloudflareAuth)) {
        return $false
    }
    
    if (-not (New-CloudflareTunnel -Domain $Domain)) {
        return $false
    }
    
    if (-not (Set-CloudflareDNS -Domain $Domain -Subdomain $Subdomain)) {
        Write-Warning "DNS configuration had issues, continuing..."
    }
    
    return $true
}


