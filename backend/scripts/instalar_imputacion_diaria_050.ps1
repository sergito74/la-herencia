# Instala la pasada diaria de la imputación progresiva (050: scripts/imputacion_diaria_050.py).
#   powershell -ExecutionPolicy Bypass -File C:\dev\LaHerencia\backend\scripts\instalar_imputacion_diaria_050.ps1
# Tarea "LaHerencia - Imputacion diaria": todos los dias 21:00; si la PC estaba apagada, corre al prenderse.
# Mientras el criterio no este activado (sin renglones en alcance) no hace nada.

$pythonw = "C:\dev\LaHerencia\backend\.venv\Scripts\pythonw.exe"
$backend = "C:\dev\LaHerencia\backend"
$accion = New-ScheduledTaskAction -Execute $pythonw -Argument "-m scripts.imputacion_diaria_050" -WorkingDirectory $backend
$disparo = New-ScheduledTaskTrigger -Daily -At 9pm
$ajustes = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName "LaHerencia - Imputacion diaria" -Action $accion -Trigger $disparo -Settings $ajustes -Description "Vincula remitos y actualiza la imputacion progresiva de las facturas a cultivo/campaña" -Force | Out-Null
Write-Host "Listo: LaHerencia - Imputacion diaria (21:00)."
