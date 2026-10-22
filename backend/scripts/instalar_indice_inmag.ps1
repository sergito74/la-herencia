# Instala la carga diaria del indice INMAG (039: scripts/indice_inmag.py, el mismo proceso
# que el boton "Actualizar ahora" de Ventas > Pastaje > Indice).
# Lo corre Sergio una sola vez, en PowerShell:
#   powershell -ExecutionPolicy Bypass -File C:\dev\LaHerencia\backend\scripts\instalar_indice_inmag.ps1
# Crea la tarea programada "LaHerencia - Indice INMAG": todos los dias 19:00 (el Mercado
# publica al cierre); si la PC estaba apagada, corre apenas se prende. Recupera los ultimos
# 10 dias faltantes y, del 1 al 10 de cada mes, prepara los borradores de liquidacion de pastaje.

$pythonw = "C:\dev\LaHerencia\backend\.venv\Scripts\pythonw.exe"
$backend = "C:\dev\LaHerencia\backend"
$accion = New-ScheduledTaskAction -Execute $pythonw -Argument "-m scripts.indice_inmag --liquidar" -WorkingDirectory $backend
$disparo = New-ScheduledTaskTrigger -Daily -At 7pm
$ajustes = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
Register-ScheduledTask -TaskName "LaHerencia - Indice INMAG" -Action $accion -Trigger $disparo -Settings $ajustes -Description "Carga el indice INMAG del Mercado Agroganadero y prepara las liquidaciones de pastaje" -Force | Out-Null

Write-Host "Listo. Prueba inmediata:"
Start-ScheduledTask -TaskName "LaHerencia - Indice INMAG"
Write-Host "Ver el resultado en La Herencia: Ventas > Pastaje > Indice"
