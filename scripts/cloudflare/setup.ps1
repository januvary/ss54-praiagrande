# ==============================================================================
# SS-54 Cloudflare Tunnel Setup Script for Windows
# ==============================================================================

param(
    [Parameter()]
    [int]$Port = 8000,

    [Parameter()]
    [string]$Domain = "ss54pg.com.br",

    [Parameter()]
    [string]$Subdomain = ""
)

$ErrorActionPreference = "Stop"
$Script:ModulesDir = Split-Path $PSScriptRoot -Parent
$Script:ModulesPath = Join-Path $Script:ModulesDir "modules\cloudflare-tunnel.ps1"

. $Script:ModulesPath

$hostname = if ($Subdomain) { "$Subdomain.$Domain" } else { $Domain }

Write-ColorOutput ""
Write-ColorOutput "======================================" "Magenta"
Write-ColorOutput "  SS-54 Cloudflare Tunnel Setup" "Magenta"
Write-ColorOutput "======================================" "Magenta"
Write-ColorOutput ""
Write-ColorOutput "Domain: $Domain" "Cyan"
if ($Subdomain) {
    Write-ColorOutput "Subdomain: $Subdomain" "Cyan"
    Write-ColorOutput "Full URL: https://$hostname" "Cyan"
} else {
    Write-ColorOutput "Full URL: https://$hostname" "Cyan"
}
Write-ColorOutput "Port: $Port" "Cyan"
Write-ColorOutput ""

$continue = Read-Host "Continue with setup? (y/n)"
if ($continue -ne 'y') {
    Write-Warning "Setup cancelled."
    exit 0
}

if (Initialize-CloudflareTunnel -Port $Port -Domain $Domain -Subdomain $Subdomain) {
    Write-ColorOutput ""
    Write-ColorOutput "======================================" "Green"
    Write-ColorOutput "  ✓ Cloudflare Tunnel Setup Complete!" "Green"
    Write-ColorOutput "======================================" "Green"
    Write-ColorOutput ""
    Write-ColorOutput "Next steps:" "Cyan"
    Write-ColorOutput "  1. Start your application:" "White"
    Write-ColorOutput "     .\scripts\deploy.ps1 start" "White"
    Write-ColorOutput ""
    Write-ColorOutput "  2. Start the tunnel:" "White"
    Write-ColorOutput "     .\scripts\cloudflare\start-tunnel.ps1" "White"
    Write-ColorOutput ""
    Write-ColorOutput "  3. Access your app at:" "White"
    Write-ColorOutput "     https://$hostname" "Green"
    Write-ColorOutput ""
} else {
    Write-ColorOutput ""
    Write-ColorOutput "======================================" "Red"
    Write-ColorOutput "  ✗ Setup Failed" "Red"
    Write-ColorOutput "======================================" "Red"
    Write-ColorOutput ""
    Write-ColorOutput "Please check the error messages above." "Yellow"
    Write-ColorOutput ""
    Write-ColorOutput "Common issues:" "Yellow"
    Write-ColorOutput "  - No internet connection" "White"
    Write-ColorOutput "  - Cloudflare account not configured" "White"
    Write-ColorOutput "  - Domain not added to Cloudflare" "White"
    Write-ColorOutput ""
    Write-ColorOutput "For help, see: scripts\cloudflare\README.md" "Cyan"
    exit 1
}
