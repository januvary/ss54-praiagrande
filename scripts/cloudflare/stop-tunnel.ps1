# ==============================================================================
# SS-54 Stop Cloudflare Tunnel
# ==============================================================================

$ErrorActionPreference = "Stop"
$Script:ModulesDir = Split-Path $PSScriptRoot -Parent
$Script:ModulesPath = Join-Path $Script:ModulesDir "modules\cloudflare-tunnel.ps1"

. $Script:ModulesPath

Stop-CloudflareTunnel
