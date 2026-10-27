# Instala la descarga semanal de peajes (037: scripts/descargar_peajes.py, el mismo proceso
# que el boton "Descargar ahora" de Compras > Descarga de peajes).
# Lo corre Sergio una sola vez (o de nuevo si cambia una contrasena), en PowerShell:
#   powershell -ExecutionPolicy Bypass -File C:\dev\LaHerencia\backend\scripts\instalar_descarga_peajes.ps1
# 1) Guarda usuario y contrasena de los cuatro portales en el Administrador de
#    credenciales de Windows (las contrasenas se tipean aca, no quedan en archivos).
# 2) Crea la tarea programada "LaHerencia - Descarga peajes": lunes 9:00; si la PC
#    estaba apagada, corre apenas se prende.
#
# 042 (27/10/2026): las credenciales y la programacion pasaron a la Boveda de portales
# (La Herencia > Boveda, solo Administrador) y las corridas programadas las hace la
# aplicacion abierta. Para retirar la tarea semanal de Windows:
#   powershell -ExecutionPolicy Bypass -File C:\dev\LaHerencia\backend\scripts\instalar_descarga_peajes.ps1 -Desinstalar
param([switch]$Desinstalar)

if ($Desinstalar) {
    if (Get-ScheduledTask -TaskName "LaHerencia - Descarga peajes" -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName "LaHerencia - Descarga peajes" -Confirm:$false
        Write-Host "Tarea semanal de peajes eliminada. La descarga sigue desde la Boveda de portales."
    } else {
        Write-Host "La tarea semanal de peajes no estaba instalada."
    }
    exit 0
}

$python = "C:\dev\LaHerencia\backend\.venv\Scripts\python.exe"
$backend = "C:\dev\LaHerencia\backend"

function Guardar($cuenta, $usuario) {
    $clave = Read-Host "Contrasena de $cuenta ($usuario)" -AsSecureString
    $plano = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($clave))
    $plano | & $python -c "import sys,keyring; keyring.set_password('LaHerencia-Peajes', sys.argv[1], sys.stdin.readline().rstrip('\r\n')); keyring.set_password('LaHerencia-Peajes', sys.argv[1] + '-usuario', sys.argv[2])" $cuenta $usuario
}

Guardar "telepeajeplus" "Sergito74"
Guardar "telepase" "sgiamberardini@fibertel.com.ar"
Guardar "ceamse" "779446"
Guardar "aubasa" "718901"

# pythonw: corre sin abrir una ventana de consola los lunes.
$pythonw = "C:\dev\LaHerencia\backend\.venv\Scripts\pythonw.exe"
$accion = New-ScheduledTaskAction -Execute $pythonw -Argument "-m scripts.descargar_peajes --origen semanal" -WorkingDirectory $backend
$disparo = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 9am
$ajustes = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName "LaHerencia - Descarga peajes" -Action $accion -Trigger $disparo -Settings $ajustes -Description "Baja y carga en Compras los comprobantes de TelepeajePlus, TelePASE, CEAMSE y AUBASA" -Force | Out-Null

Write-Host "Listo. Prueba inmediata:"
Start-ScheduledTask -TaskName "LaHerencia - Descarga peajes"
Write-Host "Ver el resultado en La Herencia: Compras > Descarga de peajes"
