<#
    ========================================================================
    Script to stop running instance of AdGuard DHCP Panel
    ========================================================================
#>

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (-not $ScriptDir) { $ScriptDir = Get-Location }

# Read configured port if config.json exists
$port = 5001
$cfgPath = Join-Path $ScriptDir "config.json"
if (Test-Path $cfgPath) {
    try {
        $raw = Get-Content $cfgPath -Raw | ConvertFrom-Json
        if ($raw.port) { $port = [int]$raw.port }
    } catch {}
}

$killed = 0
$targetPy1 = Join-Path $ScriptDir "python_portable\python.exe"
$targetPy2 = Join-Path $ScriptDir "python_portable\Scripts\python.exe"

# 1. Search python processes in python_portable or running app.py from this directory
try {
    $procs = Get-CimInstance Win32_Process | Where-Object {
        ($_.ExecutablePath -and ($_.ExecutablePath -eq $targetPy1 -or $_.ExecutablePath -eq $targetPy2)) -or
        ($_.CommandLine -and $_.CommandLine -like "*app.py*" -and $_.CommandLine -like "*$ScriptDir*")
    }
    foreach ($p in $procs) {
        Write-Host "-> Stopping application process (PID: $($p.ProcessId))..." -ForegroundColor Yellow
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        $killed++
    }
} catch {
    Write-Host "[!] Error querying processes: $($_.Exception.Message)" -ForegroundColor Red
}

# 2. Check if any process is still listening on the panel port (e.g. 5001)
try {
    $netConns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $netConns) {
        if ($c.OwningProcess -and $c.OwningProcess -ne 0 -and $c.OwningProcess -ne 4) {
            Write-Host "-> Freeing port $port (PID listening: $($c.OwningProcess))..." -ForegroundColor Yellow
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
            $killed++
        }
    }
} catch {}

if ($killed -gt 0) {
    Write-Host ""
    Write-Host "==================================================================" -ForegroundColor Green
    Write-Host "   [OK] AdGuard DHCP Panel server stopped successfully ($killed processes stopped)." -ForegroundColor Green
    Write-Host "==================================================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "==================================================================" -ForegroundColor Cyan
    Write-Host "   [INFO] No active running instance found." -ForegroundColor Cyan
    Write-Host "   (Port $port is free and no python_portable processes active)" -ForegroundColor Gray
    Write-Host "==================================================================" -ForegroundColor Cyan
}
