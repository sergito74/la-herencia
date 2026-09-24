param([switch]$Stop, [switch]$Watch, [switch]$NoBrowser, [switch]$Dev)

$ErrorActionPreference = 'Stop'
$Root      = Split-Path -Parent $PSScriptRoot
$Backend   = Join-Path $Root 'backend'
$Frontend  = Join-Path $Root 'frontend'
$Python    = Join-Path $Backend '.venv\Scripts\python.exe'
$RunDir    = Join-Path $PSScriptRoot '.run'
$PidFile   = Join-Path $RunDir 'pids.json'
$ApiPort   = 8000
$WebPort   = 3000
# Todo el sistema (pagina abierta, API, sondeos) usa 127.0.0.1 de punta a
# punta: en esta PC resolver "localhost" agrega ~2 s por request, y ademas
# si la pagina se abre en un host y la API responde en otro, son origenes
# distintos para el navegador y la cookie de sesion de uno no se manda al
# otro (bug real, 2026-09-24: login parecia "no traer datos" en todo el
# sistema porque cada request volvia 401 sin que se notara).
$WebUrl    = "http://127.0.0.1:$WebPort"
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
            if ($visto -and ++$fallas -eq 3) {
                Write-Output "$(Get-Date -Format o) API sin respuesta; se conserva el proceso para no interrumpir trabajo."
            }
            continue
        }
        $grace = if ($e.huboPestana) { $CloseGraceS } else { $NeverOpenedGraceS }
        if ($e.segundosSinActividad -ge $IdleLimitS -or
            ($e.pestanasAbiertas -eq 0 -and $e.segundosSinPestanas -ge $grace)) {
            Write-Output "$(Get-Date -Format o) Apagado por inactividad/cierre de pestanas."
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

# .env.local no se versiona (cada instalacion tiene el suyo) y a veces
# termina con "localhost" en vez de "127.0.0.1" (reinstalado, copiado a
# mano, etc). Resolver "localhost" en esta PC agrega ~2s a cada request
# del navegador y hace que el sistema entero se sienta colgado. Se
# autocorrige en cada arranque para que ese error no dependa de que
# alguien se acuerde.
$EnvLocal = Join-Path $Frontend '.env.local'
$ApiUrlLine = "NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:$ApiPort"
if (-not (Test-Path $EnvLocal) -or (Get-Content $EnvLocal -Raw) -match 'localhost') {
    Set-Content -Path $EnvLocal -Value $ApiUrlLine -Encoding utf8
}

$WebMode = if ($Dev) { 'dev' } else { 'start' }
# Produccion por defecto ("npm run start" sobre el build ya compilado): es
# notablemente mas rapido que "next dev" (que compila cada pagina la primera
# vez que se visita) para el uso diario. El riesgo de esto es servir una
# version vieja si el codigo cambio y nadie corrio el build a mano -- por
# eso, en vez de resignar velocidad pasando a dev por defecto (lo que se
# probo y resulto inaceptablemente lento, 2026-09-24), se reconstruye sola
# cuando hace falta: si falta el build o el codigo fuente es mas nuevo que
# el build existente. Usar -Dev solo para iterar sobre el frontend.
if (-not $Dev -and -not (Test-PortBusy $WebPort)) {
    $buildId = Join-Path $Frontend '.next/BUILD_ID'
    $desactualizado = $true
    if (Test-Path $buildId) {
        $buildTime = (Get-Item $buildId).LastWriteTimeUtc
        $fuenteMasNueva = Get-ChildItem (Join-Path $Frontend 'src') -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTimeUtc -gt $buildTime } | Select-Object -First 1
        $desactualizado = [bool]$fuenteMasNueva
    }
    if ($desactualizado) {
        if (-not $NoBrowser) { Start-Process $Splash }
        $buildProc = Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', 'npm run build' `
            -WorkingDirectory $Frontend -WindowStyle Hidden -PassThru -Wait `
            -RedirectStandardOutput (Join-Path $RunDir 'build.log') `
            -RedirectStandardError  (Join-Path $RunDir 'build.err.log')
        if ($buildProc.ExitCode -ne 0 -or -not (Test-Path $buildId)) {
            Show-Msg "Fallo la compilacion del frontend.`nRevisa: $RunDir\build.err.log" 'Error'
            exit 1
        }
    }
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
        -ArgumentList '-m', 'uvicorn', 'src.main:app', '--host', '127.0.0.1', '--port', $ApiPort `
        -WorkingDirectory $Backend -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $RunDir 'backend.log') `
        -RedirectStandardError  (Join-Path $RunDir 'backend.err.log')
    $pids.backend = $p.Id
}

# --- Frontend ---
if (-not (Test-PortBusy $WebPort)) {
    $p = Start-Process -FilePath 'cmd.exe' `
        -ArgumentList '/c', "npm run $WebMode -- --port", $WebPort `
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
