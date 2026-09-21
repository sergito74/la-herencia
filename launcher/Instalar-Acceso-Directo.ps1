$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$Here    = $PSScriptRoot
$Desktop = [Environment]::GetFolderPath('Desktop')
$IcoPath = Join-Path $Here 'LaHerencia.ico'

# Icono: "LH" blanco sobre verde, ICO con PNG embebido de 64x64.
$bmp = New-Object System.Drawing.Bitmap 64, 64
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = 'AntiAlias'
$g.TextRenderingHint = 'AntiAlias'
$g.Clear([System.Drawing.Color]::Transparent)
$g.FillEllipse((New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 34, 110, 62))), 1, 1, 62, 62)
$font = New-Object System.Drawing.Font 'Segoe UI', 24, ([System.Drawing.FontStyle]::Bold), ([System.Drawing.GraphicsUnit]::Pixel)
$fmt = New-Object System.Drawing.StringFormat
$fmt.Alignment = 'Center'; $fmt.LineAlignment = 'Center'
$g.DrawString('LH', $font, [System.Drawing.Brushes]::White, (New-Object System.Drawing.RectangleF 0, 0, 64, 64), $fmt)
$g.Dispose()
$ms = New-Object System.IO.MemoryStream
$bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
$png = $ms.ToArray()
$bw = New-Object System.IO.BinaryWriter ([System.IO.File]::Create($IcoPath))
$bw.Write([uint16]0); $bw.Write([uint16]1); $bw.Write([uint16]1)
$bw.Write([byte]64); $bw.Write([byte]64); $bw.Write([byte]0); $bw.Write([byte]0)
$bw.Write([uint16]1); $bw.Write([uint16]32)
$bw.Write([uint32]$png.Length); $bw.Write([uint32]22)
$bw.Write($png); $bw.Close()

function New-Shortcut($name, $description) {
    $ws = New-Object -ComObject WScript.Shell
    $lnk = $ws.CreateShortcut((Join-Path $Desktop "$name.lnk"))
    $lnk.TargetPath = 'wscript.exe'
    $lnk.Arguments = "`"$(Join-Path $Here 'LaHerencia.vbs')`""
    $lnk.WorkingDirectory = $Here
    $lnk.IconLocation = $IcoPath
    $lnk.Description = $description
    $lnk.Save()
}

New-Shortcut 'La Herencia' 'Inicia el sistema La Herencia; se apaga solo al cerrar la pestana o tras 10 min sin actividad'

$viejo = Join-Path $Desktop 'Detener La Herencia.lnk'
if (Test-Path $viejo) { Remove-Item $viejo }

Write-Host "Acceso directo creado en: $Desktop"
