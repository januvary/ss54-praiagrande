# ==============================================================================
# SS-54 Check Cloudflare Tunnel Status
# ==============================================================================

$ErrorActionPreference = "Stop"
$Script:ModulesDir = Split-Path $PSScriptRoot -Parent
$Script:ModulesPath = Join-Path $Script:ModulesDir "modules\cloudflare-tunnel.ps1"

. $Script:ModulesPath

Get-CloudflareTunnelStatus
