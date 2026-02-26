function Write-Section($title) {
    Write-Host ""
    Write-Host "=========================================================" -ForegroundColor $Colors.Header
    Write-Host "$title" -ForegroundColor $Colors.Header
    Write-Host "=========================================================" -ForegroundColor $Colors.Header
    Write-Host ""
}

function Write-Success($message) {
    Write-Host "[OK] $message" -ForegroundColor $Colors.Success
}

function Write-Warning($message) {
    Write-Host "[!] $message" -ForegroundColor $Colors.Warning
}

function Write-Error($message) {
    Write-Host "[X] $message" -ForegroundColor $Colors.Error
    Write-Host ""
}

function Write-Info($message) {
    Write-Host "[i] $message" -ForegroundColor $Colors.Info
}

