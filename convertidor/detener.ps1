# Detiene el servidor y las conversiones en curso.
$procesos = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python' -and $_.CommandLine -match 'server\.py|convertir_worker\.py'
}
if (-not $procesos) { Write-Host 'La app no estaba abierta.'; exit 0 }
foreach ($p in $procesos) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
Write-Host 'Convertidor detenido.'
