$ScriptVersion = "1.0.4"
$DefaultInstallDir = "C:\ss54"
$PostgreSQLVersion = "18"
$PostgreSQLUrl = "https://sbp.enterprisedb.com/getfile.jsp?fileid=1260009"
$GitRepo = "https://github.com/januvary/ss54-praiagrande.git"
$NssmPath = "C:\nssm\nssm.exe"

$PythonUrl = "https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe"
$GitUrl = "https://github.com/git-for-windows/git/releases/download/v2.47.0.windows.1/Git-2.47.0-64-bit.exe"
$VcRedistUrl = "https://aka.ms/vs/17/release/vc_redist.x64.exe"

$NssmUrls = @(
    "https://nssm.cc/release/nssm-2.24.zip",
    "https://web.archive.org/web/2023/https://nssm.cc/release/nssm-2.24.zip"
)

$Colors = @{
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Info = "Cyan"
    Header = "White"
}

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$ExistingConfig = @{}
$skipIPConfig = $false

function Load-ExistingConfig {
    param(
        [string]$InstallDir = $DefaultInstallDir
    )
    
    $envFilePath = "$InstallDir\ss54-praiagrande\.env"
    $config = @{}
    
    if (Test-Path $envFilePath) {
        Write-Host "Loading existing configuration..." -ForegroundColor $Colors.Info
        $envLines = Get-Content $envFilePath
        foreach ($line in $envLines) {
            if ($line -match '^(.+?)=(.*)$') {
                $key = $Matches[1].Trim()
                $value = $Matches[2].Trim()
                $config[$key] = $value
            }
        }
    }
    
    return $config
}
