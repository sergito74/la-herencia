param([switch]$Stop, [switch]$Watch, [switch]$NoBrowser)

$ErrorActionPreference = 'Stop'
$Root      = Split-Path -Parent $PSScriptRoot
$Backend   = Join-Path $Root 'backend'
$Frontend  = Join-Path $Root 'frontend'
$Python    = Join-Path $Backend '.venv\Scripts\python.exe'
$RunDir    = Join-Path $PSScriptRoot '.run'
$PidFile   = Join-Path $RunDir 'pids.json'
$ApiPort   = 8000
$WebPort   = 3000
$WebUrl    = "http://localhost:$WebPort"
# Los sondeos van por 127.0.0.1: en esta PC cada request a "localhost" tarda ~2 s.
$WebProbe  = "http://127.0.0.1:$WebPort"
$ApiHealth = "http://127.0.0.1:$ApiPort/health"
$ApiSesion = "http://127.0.0.1:$ApiPort/api/sesion"
$Splash    = Join-Path $PSScriptRoot 'splash.html'

# Apagado automatico: 10 min sin actividad, o cerrada la ultima pestana
# (8 s de gracia para recargas; 120 s si el navegador nunca llego a abrirse).
$IdleLimitS       = 600
$CloseGraceS      = 8
$NeverOpenedGraceS = 120

New-Item -ItemType Directory -Force $RunDir | Out-Null

function Show-Msg($text, $icon = 'Information') {
    Add-Type -AssemblyName System.Windows.Forms
    [void][System.Windows.Forms.MessageBox]::Show($text, 'La Herencia', 'OK', $icon)
}

# Consultar los puertos en escucha es instantaneo; sondear un puerto cerrado
# con HTTP tarda ~2 s en Windows (reintento de SYN).
function Test-PortBusy($port) {
    [bool]([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() |
        Where-Object { $_.Port -eq $port })
}

function Test-Url($url) {
    if (-not (Test-PortBusy ([uri]$url).Port)) { return $false }
    try { (Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 10).StatusCode -lt 500 } catch { $false }
}

function Stop-Watchers {
    Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
        Where-Object { $_.CommandLine -match 'LaHerencia\.ps1.*-Watch' -and $_.ProcessId -ne $PID } |
        ForEach-Object { Stop-Tree $_.ProcessId }
}

function Stop-Tree($procId) {
    if ($procId) { & cmd.exe /c "taskkill /PID $procId /T /F >nul 2>&1" }
}

function Stop-Port($port) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Tree $_.OwningProcess }
}

function Wait-Until($test, $seconds) {
    $limit = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $limit) {
        if (& $test) { return $true }
        Start-Sleep -Milliseconds 200
    }
    $false
}

function Stop-All {
    Stop-Watchers
    if (Test-Path $PidFile) {
        $p = Get-Content $PidFile -Raw | ConvertFrom-Json
        Stop-Tree $p.backend
        Stop-Tree $p.frontend
        if ($p.watcher -ne $PID) { Stop-Tree $p.watcher }
        Remove-Item $PidFile -Force
    }
    # Hijos que puedan haber sobrevivido (workers de next dev).
    Stop-Port $ApiPort
    Stop-Port $WebPort
}

if ($Stop) { Stop-All; exit 0 }

if ($Watch) {
    $fallas = 0
    $visto = $false
    while ($true) {
        Start-Sleep -Seconds 2
        try {
            $e = Invoke-RestMethod "$ApiSesion/estado" -TimeoutSec 5
            $fallas = 0
            $visto = $true
        } catch {
            # Solo cuenta si alguna vez vio al backend arriba: durante el arranque
            # todavia no responde y eso no significa que se haya caido.
            if ($visto -and ++$fallas -ge 3) { Stop-All; exit 0 }
            continue
        }
        $grace = if ($e.huboPestana) { $CloseGraceS } else { $NeverOpenedGraceS }
        if ($e.segundosSinActividad -ge $IdleLimitS -or
            ($e.pestanasAbiertas -eq 0 -and $e.segundosSinPestanas -ge $grace)) {
            Stop-All
            exit 0
        }
    }
}

if (-not (Test-Path $Python)) {
    Show-Msg "No se encontro el entorno Python del backend:`n$Python`n`nCrealo con: python -m venv backend\.venv && backend\.venv\Scripts\pip install -r backend\requirements.txt" 'Error'
    exit 1
}
if (-not (Test-Path (Join-Path $Frontend 'node_modules'))) {
    Show-Msg "Faltan las dependencias del frontend.`n`nEjecuta 'npm install' en:`n$Frontend" 'Error'
    exit 1
}

$listo = (Test-Url $ApiHealth) -and (Test-Url $WebProbe)
# Arranque desde cero: un vigilante de una sesion anterior podria apagar lo nuevo.
if (-not $listo) { Stop-Watchers }
if (-not $listo -and -not $NoBrowser) { Start-Process $Splash }

$pids = @{ backend = $null; frontend = $null; watcher = $null }
if (Test-Path $PidFile) {
    $old = Get-Content $PidFile -Raw | ConvertFrom-Json
    $pids.backend = $old.backend; $pids.frontend = $old.frontend; $pids.watcher = $old.watcher
}

# --- Backend ---
if (-not (Test-PortBusy $ApiPort)) {
    $p = Start-Process -FilePath $Python `
        -ArgumentList '-m', 'uvicorn', 'src.main:app', '--port', $ApiPort `
        -WorkingDirectory $Backend -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $RunDir 'backend.log') `
        -RedirectStandardError  (Join-Path $RunDir 'backend.err.log')
    $pids.backend = $p.Id
}

# --- Frontend ---
if (-not (Test-PortBusy $WebPort)) {
    $p = Start-Process -FilePath 'cmd.exe' `
        -ArgumentList '/c', 'npm run dev -- --port', $WebPort `
        -WorkingDirectory $Frontend -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $RunDir 'frontend.log') `
        -RedirectStandardError  (Join-Path $RunDir 'frontend.err.log')
    $pids.frontend = $p.Id
}

$pids | ConvertTo-Json | Set-Content $PidFile

if (-not (Wait-Until { Test-Url $ApiHealth } 60)) {
    Show-Msg "El backend no arranco a tiempo.`nRevisa: $RunDir\backend.err.log" 'Error'
    exit 1
}
if (-not (Wait-Until { Test-Url $WebProbe } 120)) {
    Show-Msg "El frontend no arranco a tiempo.`nRevisa: $RunDir\frontend.err.log" 'Error'
    exit 1
}

# Plazos de apagado desde cero, recien ahora que todo responde.
Invoke-RestMethod "$ApiSesion/inicio" -Method Post | Out-Null

if (-not ($pids.watcher -and (Get-Process -Id $pids.watcher -ErrorAction SilentlyContinue))) {
    $w = Start-Process -FilePath 'powershell.exe' `
        -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-File', "`"$PSCommandPath`"", '-Watch' `
        -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $RunDir 'watcher.log') `
        -RedirectStandardError  (Join-Path $RunDir 'watcher.err.log')
    $pids.watcher = $w.Id
    $pids | ConvertTo-Json | Set-Content $PidFile
}

if ($listo -and -not $NoBrowser) { Start-Process $WebUrl }
