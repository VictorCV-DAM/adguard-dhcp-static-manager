<#
    ========================================================================
    Auto-instalador de AdGuard DHCP Panel Privado para Windows
    Instala una instancia PORTABLE y aislada de Python (sin tocar tu PC)
    ========================================================================
#>

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (-not $ScriptDir) { $ScriptDir = Get-Location }
Set-Location $ScriptDir

$TargetDir = Join-Path $ScriptDir "python_portable"
$ReqFile = Join-Path $ScriptDir "requirements.txt"
$ConfigFile = Join-Path $ScriptDir "config.json"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "   Instalador Portable - AdGuard DHCP Panel Privado (Windows)" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "Directorio del proyecto: $ScriptDir" -ForegroundColor Gray
Write-Host "Destino de Python portable: $TargetDir" -ForegroundColor Gray
Write-Host ""

$pyExe = $null

# 1. Comprobar si ya existe una instancia previa en python_portable
if (Test-Path (Join-Path $TargetDir "python.exe")) {
    $pyExe = Join-Path $TargetDir "python.exe"
    Write-Host "[OK] Detectada instancia portable existente en python_portable\python.exe" -ForegroundColor Green
} elseif (Test-Path (Join-Path $TargetDir "Scripts\python.exe")) {
    $pyExe = Join-Path $TargetDir "Scripts\python.exe"
    Write-Host "[OK] Detectada instancia virtual/portable en python_portable\Scripts\python.exe" -ForegroundColor Green
} else {
    Write-Host "[1/3] Descargando y configurando Python Portable oficial (Embeddable 3.11)..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

    $is64Bit = [Environment]::Is64BitOperatingSystem
    $pyVer = "3.11.9"
    $arch = if ($is64Bit) { "amd64" } else { "win32" }
    $zipUrl = "https://www.python.org/ftp/python/$pyVer/python-$pyVer-embed-$arch.zip"
    $zipPath = Join-Path $TargetDir "python_embed.zip"

    $embedSuccess = $false
    try {
        Write-Host "      Descargando paquete oficial de Python.org ($arch)..." -ForegroundColor Gray
        Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing -TimeoutSec 45
        
        Write-Host "      Descomprimiendo archivos..." -ForegroundColor Gray
        Expand-Archive -Path $zipPath -DestinationPath $TargetDir -Force
        Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

        # Habilitar soporte de paquetes (site-packages) en el archivo ._pth
        $pthFile = Get-ChildItem -Path $TargetDir -Filter "*._pth" | Select-Object -First 1
        if ($pthFile) {
            $rawPth = [System.IO.File]::ReadAllText($pthFile.FullName)
            $rawPth = $rawPth -replace '#\s*import\s+site', "import site`r`nLib\site-packages"
            $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
            [System.IO.File]::WriteAllText($pthFile.FullName, $rawPth, $utf8NoBom)
        }

        # Descargar e instalar pip
        Write-Host "      Instalando gestor de paquetes pip en la instancia portable..." -ForegroundColor Gray
        $pipUrl = "https://bootstrap.pypa.io/get-pip.py"
        $pipPath = Join-Path $TargetDir "get-pip.py"
        Invoke-WebRequest -Uri $pipUrl -OutFile $pipPath -UseBasicParsing -TimeoutSec 45

        $candidatePy = Join-Path $TargetDir "python.exe"
        & $candidatePy $pipPath --no-warn-script-location
        Remove-Item $pipPath -Force -ErrorAction SilentlyContinue

        # Verificar
        $pipVer = & $candidatePy -m pip --version 2>$null
        if ($pipVer) {
            $pyExe = $candidatePy
            $embedSuccess = $true
            Write-Host "[OK] Python Portable 3.11 instalado correctamente en python_portable\" -ForegroundColor Green
        }
    } catch {
        Write-Host "      [!] No se pudo completar la descarga del paquete embeddable ($($_.Exception.Message))" -ForegroundColor Yellow
    }

    # Fallback: Si el embeddable falla (ej. sin conexión a python.org), crear entorno aislado con python local
    if (-not $embedSuccess) {
        Write-Host "      Intentando crear entorno aislado portable mediante el intérprete local..." -ForegroundColor Yellow
        $sysPython = (Get-Command py, python, python3 -ErrorAction SilentlyContinue | Select-Object -First 1).Source
        if ($sysPython) {
            Write-Host "      Creando entorno virtual aislado en python_portable..." -ForegroundColor Gray
            & $sysPython -m venv $TargetDir
            if (Test-Path (Join-Path $TargetDir "Scripts\python.exe")) {
                $pyExe = Join-Path $TargetDir "Scripts\python.exe"
                Write-Host "[OK] Entorno virtual portable creado en python_portable\" -ForegroundColor Green
            }
        }
    }
}

if (-not $pyExe -or -not (Test-Path $pyExe)) {
    Write-Host ""
    Write-Host "[ERROR] No se pudo preparar la instancia portable de Python." -ForegroundColor Red
    Write-Host "Verifica tu conexión a Internet para descargar Python Portable o instala Python en Windows." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[2/3] Instalando dependencias en la instancia portable..." -ForegroundColor Yellow
Write-Host "      (Tu instalación principal de Python NO será tocada ni alterada)" -ForegroundColor Cyan

if (Test-Path $ReqFile) {
    & $pyExe -m pip install -r $ReqFile --no-warn-script-location
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Advertencia: pip devolvió un código de error al instalar requerimientos." -ForegroundColor Yellow
    } else {
        Write-Host "[OK] Dependencias instaladas satisfactoriamente en python_portable." -ForegroundColor Green
    }
} else {
    Write-Host "[!] No se encontró requirements.txt. Instalando flask y cryptography directamente..." -ForegroundColor Yellow
    & $pyExe -m pip install flask cryptography --no-warn-script-location
}

# 3. Comprobar o generar config.json
Write-Host ""
Write-Host "[3/3] Comprobando archivo de configuración config.json..." -ForegroundColor Yellow
if (-not (Test-Path $ConfigFile)) {
    $defaultConfig = @"
{
  "adguard_url": "http://192.168.1.2:80",
  "adguard_user": "admin",
  "adguard_pass": "admin",
  "port": 5001,
  "debug": false,
  "home_assistant_instances": [],
  "session_secret": "$([Guid]::NewGuid().ToString('N'))"
}
"@
    $defaultConfig | Set-Content -Path $ConfigFile -Encoding UTF8
    Write-Host "[OK] Se ha creado un archivo config.json con valores por defecto. Puedes editarlo con tus datos de AdGuard Home." -ForegroundColor Green
} else {
    Write-Host "[OK] config.json ya existe." -ForegroundColor Green
}

# 4. Crear lanzadores .bat
$launcherContent = @"
@echo off
chcp 65001 >nul
title AdGuard DHCP Panel (Portable)
cd /d "%~dp0"

echo ==================================================================
echo   Iniciando AdGuard DHCP Panel Privado (Instancia Portable)
echo ==================================================================

if exist "python_portable\python.exe" (
    "python_portable\python.exe" app.py
) else if exist "python_portable\Scripts\python.exe" (
    "python_portable\Scripts\python.exe" app.py
) else (
    echo [ERROR] No se encontro la instancia portable de Python.
    echo Ejecuta primero instalar_windows.bat
    pause
    exit /b 1
)

pause
"@

$launcherPath1 = Join-Path $ScriptDir "iniciar_windows.bat"
$launcherPath2 = Join-Path $ScriptDir "start_windows.bat"
$launcherContent | Set-Content -Path $launcherPath1 -Encoding ASCII
$launcherContent | Set-Content -Path $launcherPath2 -Encoding ASCII

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "   ¡Instalación completada con éxito!" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "La instancia portable está lista en: python_portable\" -ForegroundColor Gray
Write-Host "Para iniciar el servidor ejecuta: iniciar_windows.bat (o start_windows.bat)" -ForegroundColor Cyan
Write-Host ""
