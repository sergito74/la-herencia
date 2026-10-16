# Instala la descarga semanal de peajes (scripts/descargar_peajes.py).
# Lo corre Sergio una sola vez, en PowerShell:
#   powershell -ExecutionPolicy Bypass -File C:\dev\LaHerencia\backend\scripts\instalar_descarga_peajes.ps1
# 1) Guarda usuario y contraseña de los dos portales en el Administrador de
#    credenciales de Windows (las contraseñas se tipean acá, no quedan en archivos).
# 2) Crea la tarea programada "LaHerencia - Descarga peajes": lunes 9:00; si la PC
#    estaba apagada, corre apenas se prende.

$python = "C:\Users\Sergio\AppData\Local\Programs\Python\Python313\python.exe"
$backend = "C:\dev\LaHerencia\backend"

function Guardar($cuenta, $usuario) {
    $clave = Read-Host "Contraseña de $cuenta ($usuario)" -AsSecureString
    $plano = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($clave))
    $plano | & $python -c "import sys,keyring; keyring.set_password('LaHerencia-Peajes', sys.argv[1], sys.stdin.readline().rstrip('\r\n')); keyring.set_password('LaHerencia-Peajes', sys.argv[1] + '-usuario', sys.argv[2])" $cuenta $usuario
}

Guardar "telepeajeplus" "Sergito74"
Guardar "telepase" "sgiamberardini@fibertel.com.ar"
Guardar "ceamse" "779446"
Guardar "aubasa" "718901"

$accion = New-ScheduledTaskAction -Execute $python -Argument "-m scripts.descargar_peajes" -WorkingDirectory $backend
$disparo = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 9am
$ajustes = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName "LaHerencia - Descarga peajes" -Action $accion -Trigger $disparo -Settings $ajustes -Description "Baja resumenes y facturas de TelepeajePlus y TelePASE a Dropbox\Compras" -Force | Out-Null

Write-Host "Listo. Prueba inmediata:"
Start-ScheduledTask -TaskName "LaHerencia - Descarga peajes"
Write-Host "Ver el resultado en: $env:USERPROFILE\Dropbox\Giamigli de Bolivar SA\Compras\_descargas_portales.log"
