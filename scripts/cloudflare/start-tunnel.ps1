# ==============================================================================
# SS-54 Start Cloudflare Tunnel
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

Start-CloudflareTunnel -Port $Port -Domain $Domain -Subdomain $Subdomain
