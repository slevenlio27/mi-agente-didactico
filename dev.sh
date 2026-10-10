#!/usr/bin/env bash
# Arranca backend (FastAPI) y frontend (Vite) juntos, en una sola terminal.
# Funciona igual en Windows (Git Bash) que en Linux/Debian/macOS.
#
# Uso:  ./dev.sh
# Para detener ambos: Ctrl+C

set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Usa directamente el Python del entorno virtual (sin depender de "python" en
# el PATH, que en Windows puede apuntar a la Microsoft Store).
if [ -f "$ROOT/backend/.venv/Scripts/python.exe" ]; then
  PY="$ROOT/backend/.venv/Scripts/python.exe"   # Windows (Git Bash)
elif [ -f "$ROOT/backend/.venv/bin/python" ]; then
  PY="$ROOT/backend/.venv/bin/python"           # Linux / macOS
else
  echo "No encontré backend/.venv. Corre primero la instalación del backend"
  echo "(ver README.md, INSTALL_WINDOWS.md o INSTALL_LINUX.md)."
  exit 1
fi

if [ ! -d "$ROOT/frontend/node_modules" ]; then
  echo "No encontré frontend/node_modules. Corre 'npm install' dentro de frontend/ primero."
  exit 1
fi

cleanup() {
  echo ""
  echo "Deteniendo backend (PID $BACKEND_PID)..."
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "==> Backend en http://localhost:8000"
(
  cd "$ROOT/backend"
  # Garantiza un SECRET_KEY real antes de arrancar (no cambia uno ya válido)
  "$PY" scripts/generate_secrets.py >/dev/null
  "$PY" -m uvicorn app.main:app --port 8000
) &
BACKEND_PID=$!

sleep 2

echo "==> Frontend en http://localhost:5173"
cd "$ROOT/frontend"
npm run dev
