# Arranca backend (FastAPI) y frontend (Vite) juntos, cada uno en su propia
# ventana de PowerShell.
#
# Uso: desde la raiz del proyecto:  .\dev.ps1
# Para detener: cierra las dos ventanas nuevas, o Ctrl+C dentro de cada una.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

if (-not (Test-Path "$root\backend\.venv\Scripts\python.exe")) {
    Write-Host "No encontre backend\.venv. Corre primero: powershell -ExecutionPolicy Bypass -File scripts\setup-windows.ps1"
    exit 1
}
if (-not (Test-Path "$root\frontend\node_modules")) {
    Write-Host "No encontre frontend\node_modules. Corre primero: powershell -ExecutionPolicy Bypass -File scripts\setup-windows.ps1"
    exit 1
}

# Garantiza un SECRET_KEY real antes de arrancar (no cambia uno ya valido)
& "$root\backend\.venv\Scripts\python.exe" "$root\backend\scripts\generate_secrets.py" | Out-Null

Write-Host "==> Backend en http://localhost:8000 (ventana nueva)"
# Nota: se omite --reload a proposito. En Python 3.13/3.14 + Windows, el
# proceso hijo que crea uvicorn para el auto-reinicio no siempre hereda
# correctamente las dependencias del venv (falla con "ModuleNotFoundError").
# Si editas el codigo del backend, detén esta ventana (Ctrl+C) y vuelve a
# correr .\dev.ps1.
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$root\backend'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000"
)

Start-Sleep -Seconds 2

Write-Host "==> Frontend en http://localhost:5173 (ventana nueva)"
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$root\frontend'; npm run dev"
)

Write-Host ""
Write-Host "Se abrieron dos ventanas de PowerShell, una por servidor. Cierralas para detenerlos."
