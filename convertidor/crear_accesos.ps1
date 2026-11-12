# Crea: (1) inicio automatico con Windows, (2) acceso directo en el escritorio a la pagina.
# Todo en ASCII a proposito (PowerShell 5 lee mal los acentos sin BOM).
$ErrorActionPreference = 'Stop'
$carpeta = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $env:LOCALAPPDATA 'Convertidor\venv\Scripts\python.exe'

if (-not (Test-Path $py)) {
    Write-Host 'Primero abri iniciar.bat una vez (para preparar la app) y despues volve a ejecutar este archivo.'
    exit 1
}

$puerto = 8000
$cfg = Join-Path $carpeta 'config.env'
if (Test-Path $cfg) {
    foreach ($linea in Get-Content $cfg) {
        if ($linea -match '^\s*PUERTO\s*=\s*"?(\d+)"?\s*$') { $puerto = [int]$Matches[1] }
    }
}

$vbs = Join-Path $carpeta 'iniciar_en_segundo_plano.vbs'
$sh = New-Object -ComObject WScript.Shell

# 1) Inicio automatico: acceso directo en la carpeta Inicio de Windows
$inicio = [Environment]::GetFolderPath('Startup')
$ruta = Join-Path $inicio 'Convertidor (inicio automatico).lnk'
$lnk = $sh.CreateShortcut($ruta)
$lnk.TargetPath = Join-Path $env:WINDIR 'System32\wscript.exe'
$lnk.Arguments = '"' + $vbs + '"'
$lnk.WorkingDirectory = $carpeta
$lnk.Description = 'Inicia el Convertidor a Markdown en segundo plano'
$lnk.Save()
Write-Host "Inicio automatico creado: $ruta"

# 2) Escritorio: acceso directo que abre la pagina
$escritorio = [Environment]::GetFolderPath('Desktop')
$url = Join-Path $escritorio 'Convertidor.url'
Set-Content -Path $url -Value "[InternetShortcut]`r`nURL=http://localhost:$puerto/`r`n" -Encoding ASCII
Write-Host "Acceso directo creado: $url"

# 3) Arrancar ya mismo, sin esperar a reiniciar
Start-Process -FilePath 'wscript.exe' -ArgumentList ('"' + $vbs + '"')
Write-Host ''
Write-Host 'Listo. La app se esta iniciando en segundo plano (tarda unos segundos).'
