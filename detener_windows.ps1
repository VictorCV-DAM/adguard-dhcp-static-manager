<#
    ========================================================================
    Script para detener la instancia en ejecución de AdGuard DHCP Panel
    ========================================================================
#>

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (-not $ScriptDir) { $ScriptDir = Get-Location }

# Leer puerto configurado si existe config.json
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

# 1. Buscar procesos python en python_portable o ejecutando app.py desde esta carpeta
try {
    $procs = Get-CimInstance Win32_Process | Where-Object {
        ($_.ExecutablePath -and ($_.ExecutablePath -eq $targetPy1 -or $_.ExecutablePath -eq $targetPy2)) -or
        ($_.CommandLine -and $_.CommandLine -like "*app.py*" -and $_.CommandLine -like "*$ScriptDir*")
    }
    foreach ($p in $procs) {
        Write-Host "-> Deteniendo proceso de la aplicación (PID: $($p.ProcessId))..." -ForegroundColor Yellow
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        $killed++
    }
} catch {
    Write-Host "[!] Error consultando procesos: $($_.Exception.Message)" -ForegroundColor Red
}

# 2. Buscar si aún queda algún proceso escuchando en el puerto del panel (ej. 5001)
try {
    $netConns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $netConns) {
        if ($c.OwningProcess -and $c.OwningProcess -ne 0 -and $c.OwningProcess -ne 4) {
            Write-Host "-> Liberando puerto $port (PID escuchando: $($c.OwningProcess))..." -ForegroundColor Yellow
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
            $killed++
        }
    }
} catch {}

if ($killed -gt 0) {
    Write-Host ""
    Write-Host "==================================================================" -ForegroundColor Green
    Write-Host "   [OK] Servidor AdGuard DHCP Panel detenido con éxito ($killed procesos detenidos)." -ForegroundColor Green
    Write-Host "==================================================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "==================================================================" -ForegroundColor Cyan
    Write-Host "   [INFO] No se encontró ninguna instancia activa en ejecución." -ForegroundColor Cyan
    Write-Host "   (Puerto $port libre y sin procesos de python_portable activos)" -ForegroundColor Gray
    Write-Host "==================================================================" -ForegroundColor Cyan
}
