# Instala todo lo necesario para correr Mi Agente Didactico en Windows.
#
# Uso: desde PowerShell, parado en la carpeta raiz del proyecto:
#   powershell -ExecutionPolicy Bypass -File scripts\setup-windows.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

function Test-Command($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

Write-Host "==> 1/4 Verificando Python y Node.js"

if (-not (Test-Command "python")) {
    Write-Host ""
    Write-Host "No se encontro Python." -ForegroundColor Yellow
    Write-Host "Instalalo desde https://www.python.org/downloads/ (marca la casilla 'Add python.exe to PATH')."
    Write-Host "Si al escribir 'python' se abre la Microsoft Store en vez de ejecutar Python, ve a:"
    Write-Host "  Configuracion > Aplicaciones > Configuracion avanzada de aplicaciones > Alias de ejecucion de aplicaciones"
    Write-Host "  y desactiva 'python.exe' y 'python3.exe'."
    Write-Host "Vuelve a correr este script despues de instalar."
    exit 1
}

if (-not (Test-Command "node")) {
    Write-Host ""
    Write-Host "No se encontro Node.js." -ForegroundColor Yellow
    Write-Host "Instalalo desde https://nodejs.org (elige la version LTS) y vuelve a correr este script."
    exit 1
}

Write-Host ("Python: " + (python --version))
Write-Host ("Node:   " + (node --version))

Write-Host "==> 2/4 Backend: entorno virtual y dependencias"
Set-Location "$root\backend"

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

# Importante: llamamos SIEMPRE al pip del venv por ruta completa
# (.venv\Scripts\python.exe -m pip), nunca al comando "pip" a secas.
# En Windows es muy comun que "pip" del PATH apunte a otro Python distinto
# del venv, lo que deja paquetes instalados en el lugar equivocado.
& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt

# Crea backend\.env si falta y genera un SECRET_KEY aleatorio real
# (nunca deja el valor de ejemplo).
& ".venv\Scripts\python.exe" scripts\generate_secrets.py
Write-Host "   Solo falta agregar al menos una API key de IA en backend\.env."

Write-Host "==> 3/4 Frontend: dependencias de Node"
Set-Location "$root\frontend"
npm install

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

Write-Host "==> 4/4 Listo."
Write-Host ""
Write-Host "Para arrancar backend y frontend juntos, desde la raiz del proyecto:"
Write-Host "  .\dev.ps1"
Write-Host ""
Write-Host "Para arrancarlos por separado, ve backend\INSTALL_WINDOWS.md en la raiz del proyecto."

Set-Location $root
