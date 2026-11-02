<#
    ========================================================================
    Portable Auto-Installer for AdGuard DHCP Panel (Windows)
    Installs an isolated PORTABLE instance of Python (zero system modification)
    ========================================================================
#>

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (-not $ScriptDir) { $ScriptDir = Get-Location }
Set-Location $ScriptDir

# Check if running on remote network drive or sshfs
$isRemote = $false
try {
    $driveLetter = if ($ScriptDir.Length -ge 2 -and $ScriptDir[1] -eq ':') { $ScriptDir.Substring(0, 2) } else { "" }
    if ($driveLetter) {
        $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$driveLetter'" -ErrorAction SilentlyContinue
        if ($disk -and $disk.DriveType -eq 4) { $isRemote = $true }
    }
} catch {}
if ($ScriptDir.StartsWith("\\") -or $ScriptDir -match "sshfs" -or $ScriptDir.Contains([char]0xf03a)) {
    $isRemote = $true
}

if ($isRemote) {
    Write-Host ""
    Write-Host "==================================================================" -ForegroundColor Red
    Write-Host "   [CRITICAL ERROR] NETWORK DRIVE OR SSHFS EXECUTION DETECTED" -ForegroundColor Red
    Write-Host "==================================================================" -ForegroundColor Red
    Write-Host "Detected path: $ScriptDir" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Python environments and SQLite require running on a local physical disk" -ForegroundColor White
    Write-Host "to ensure file locking and dependencies work reliably." -ForegroundColor White
    Write-Host ""
    Write-Host "OPTIONS:" -ForegroundColor Cyan
    Write-Host "------------------------------------------------------------------" -ForegroundColor Cyan
    Write-Host "OPTION 1: To run the panel on this local Windows machine:" -ForegroundColor Green
    Write-Host "   1. Copy the full folder to a local disk (e.g. C:\adguard-panel)" -ForegroundColor White
    Write-Host "   2. Open the copied folder and double-click start_windows.bat" -ForegroundColor White
    Write-Host ""
    Write-Host "OPTION 2: To run the panel on the remote server directly:" -ForegroundColor Green
    Write-Host "   1. Connect directly to the server (via SSH or local terminal)." -ForegroundColor White
    Write-Host "   2. Navigate to the project folder on that server and run:" -ForegroundColor White
    Write-Host "      ./start_linux.sh" -ForegroundColor Yellow
    Write-Host "==================================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Press any key to exit..." -ForegroundColor Gray
    try { $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") } catch {}
    exit 1
}

# Isolate environment variables from any system Python
$env:PYTHONHOME = $null
$env:PYTHONPATH = $ScriptDir

$TargetDir = Join-Path $ScriptDir "python_portable"
$ReqFile = Join-Path $ScriptDir "requirements.txt"
$ConfigFile = Join-Path $ScriptDir "config.json"

# Ensure Lib\site-packages exists
$sitePkgDir = Join-Path $TargetDir "Lib\site-packages"
if (-not (Test-Path $sitePkgDir)) {
    New-Item -ItemType Directory -Path $sitePkgDir -Force | Out-Null
}

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "   Portable Installer - AdGuard DHCP Panel (Windows)" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "Project directory: $ScriptDir" -ForegroundColor Gray
Write-Host "Portable Python target: $TargetDir" -ForegroundColor Gray
Write-Host ""

$pyExe = $null

function Update-PthFile($dir) {
    $spDir = Join-Path $dir "Lib\site-packages"
    if (-not (Test-Path $spDir)) {
        New-Item -ItemType Directory -Path $spDir -Force | Out-Null
    }

    $pthFiles = Get-ChildItem -Path $dir -Filter "*._pth"
    foreach ($pth in $pthFiles) {
        $rawPth = [System.IO.File]::ReadAllText($pth.FullName)
        $rawPth = $rawPth -replace '#\s*import\s+site', 'import site'
        if ($rawPth -notmatch 'import\s+site') {
            $rawPth += "`r`nimport site"
        }
        if ($rawPth -notmatch 'Lib\\site-packages') {
            $rawPth += "`r`nLib\site-packages"
        }
        if ($rawPth -notmatch 'site-packages') {
            $rawPth += "`r`nsite-packages"
        }
        if ($rawPth -notmatch '(?m)^\.\.$') {
            $rawPth += "`r`n..`r`n."
        }
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($pth.FullName, $rawPth, $utf8NoBom)
    }
}

# 1. Check for existing python_portable instance
if (Test-Path (Join-Path $TargetDir "Scripts\python.exe")) {
    $pyExe = Join-Path $TargetDir "Scripts\python.exe"
    Write-Host "[OK] Detected virtual/portable instance in python_portable\Scripts\python.exe" -ForegroundColor Green
} elseif (Test-Path (Join-Path $TargetDir "python.exe")) {
    $pyExe = Join-Path $TargetDir "python.exe"
    Update-PthFile $TargetDir
    Write-Host "[OK] Detected portable instance in python_portable\python.exe" -ForegroundColor Green
} else {
    # 1.1 Fast venv creation if host system has python
    $sysPython = (Get-Command py, python, python3 -ErrorAction SilentlyContinue | Select-Object -First 1).Source
    if ($sysPython) {
        Write-Host "[1/3] Creating isolated portable instance in python_portable\..." -ForegroundColor Yellow
        Write-Host "      (Your primary Python installation will NOT be modified)" -ForegroundColor Gray
        & $sysPython -m venv $TargetDir
        $candidateExe = Join-Path $TargetDir "Scripts\python.exe"
        if ($LASTEXITCODE -eq 0 -and (Test-Path $candidateExe)) {
            $pyExe = $candidateExe
            Write-Host "[OK] Portable instance configured in seconds in python_portable\" -ForegroundColor Green
        } else {
            Write-Host "[WARNING] venv creation failed. Falling back to embeddable package..." -ForegroundColor Yellow
            Remove-Item -Recurse -Force $TargetDir -ErrorAction SilentlyContinue
        }
    }

    # 1.2 Fallback to official embeddable package
    if (-not $pyExe) {
        Write-Host "[1/3] Downloading official Python Portable (Embeddable 3.11)..." -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

        $is64Bit = [Environment]::Is64BitOperatingSystem
        $pyVer = "3.11.9"
        $arch = if ($is64Bit) { "amd64" } else { "win32" }
        $zipUrl = "https://www.python.org/ftp/python/$pyVer/python-$pyVer-embed-$arch.zip"
        $zipPath = Join-Path $TargetDir "python_embed.zip"

        try {
            Write-Host "      Downloading official Python.org package ($arch)..." -ForegroundColor Gray
            Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing -TimeoutSec 45
            
            Write-Host "      Extracting files..." -ForegroundColor Gray
            Expand-Archive -Path $zipPath -DestinationPath $TargetDir -Force
            Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

            Update-PthFile $TargetDir

            Write-Host "      Installing pip package manager in portable instance..." -ForegroundColor Gray
            $pipUrl = "https://bootstrap.pypa.io/get-pip.py"
            $pipPath = Join-Path $TargetDir "get-pip.py"
            Invoke-WebRequest -Uri $pipUrl -OutFile $pipPath -UseBasicParsing -TimeoutSec 45

            $candidatePy = Join-Path $TargetDir "python.exe"
            & $candidatePy $pipPath --no-warn-script-location
            Remove-Item $pipPath -Force -ErrorAction SilentlyContinue

            $pipVer = & $candidatePy -m pip --version 2>$null
            if ($pipVer) {
                $pyExe = $candidatePy
                Write-Host "[OK] Python Portable 3.11 installed successfully in python_portable\" -ForegroundColor Green
            }
        } catch {
            Write-Host "      [!] Embeddable Python download failed: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

if (-not $pyExe -or -not (Test-Path $pyExe)) {
    Write-Host ""
    Write-Host "[ERROR] Could not prepare portable Python instance." -ForegroundColor Red
    Write-Host "Check your internet connection or install Python on Windows." -ForegroundColor Red
    exit 1
}

# 1.3 Ensure pip in python_portable
Update-PthFile $TargetDir
$hasPip = & $pyExe -m pip --version 2>$null
if (-not $hasPip) {
    Write-Host "      Configuring pip in python_portable..." -ForegroundColor Yellow
    $pipUrl = "https://bootstrap.pypa.io/get-pip.py"
    $pipPath = Join-Path $TargetDir "get-pip.py"
    try {
        Invoke-WebRequest -Uri $pipUrl -OutFile $pipPath -UseBasicParsing -TimeoutSec 45
        & $pyExe $pipPath --no-warn-script-location
        Remove-Item $pipPath -Force -ErrorAction SilentlyContinue
    } catch {
        Write-Host "      [!] Warning with get-pip.py: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "[2/3] Installing dependencies in portable instance..." -ForegroundColor Yellow
Write-Host "      (Your primary system Python will NOT be modified)" -ForegroundColor Cyan

if (Test-Path $ReqFile) {
    & $pyExe -m pip install -r $ReqFile --no-warn-script-location --prefer-binary --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Warning: pip returned a non-zero exit code." -ForegroundColor Yellow
    } else {
        Write-Host "[OK] Dependencies installed successfully in python_portable." -ForegroundColor Green
    }
} else {
    Write-Host "[!] requirements.txt not found. Installing flask and cryptography directly..." -ForegroundColor Yellow
    & $pyExe -m pip install flask cryptography --no-warn-script-location --prefer-binary --disable-pip-version-check
}

# Verify Flask
Update-PthFile $TargetDir
$verifyFlask = & $pyExe -c "import flask; print('FLASK_OK')" 2>$null
if ($verifyFlask -notmatch 'FLASK_OK') {
    Write-Host "      Ensuring Flask installation in site-packages..." -ForegroundColor Yellow
    & $pyExe -m pip install flask cryptography --prefer-binary --no-warn-script-location --force-reinstall
}

# 3. Check or generate config.json
Write-Host ""
Write-Host "[3/3] Checking configuration file config.json..." -ForegroundColor Yellow
if (-not (Test-Path $ConfigFile)) {
    $defaultConfig = @"
{
  "adguard_url": "",
  "adguard_user": "",
  "adguard_pass": "",
  "port": 5001,
  "debug": false,
  "home_assistant_instances": [],
  "routers": [],
  "session_secret": "$([Guid]::NewGuid().ToString('N'))"
}
"@
    $defaultConfig | Set-Content -Path $ConfigFile -Encoding UTF8
    Write-Host "[OK] Created clean, neutral config.json file." -ForegroundColor Green
} else {
    Write-Host "[OK] config.json already exists." -ForegroundColor Green
}

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "   Installation completed successfully!" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "Portable instance ready in: python_portable\" -ForegroundColor Gray
Write-Host "To start the server, run: start_windows.bat" -ForegroundColor Cyan
Write-Host ""
