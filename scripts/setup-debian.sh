#!/usr/bin/env bash
# Instala todo lo necesario para correr Mi Agente Didáctico en Debian
# (probado pensando en Debian 13 "trixie"). Uso:
#   chmod +x scripts/setup-debian.sh
#   ./scripts/setup-debian.sh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE_MAJOR=24   # Node 24 "Krypton" = LTS activa hasta 2028

echo "==> 1/5 Paquetes del sistema (Python, herramientas de compilación, curl)"
sudo apt-get update
sudo apt-get install -y \
  python3 python3-venv python3-pip python3-dev \
  build-essential curl ca-certificates

echo "==> 2/5 Node.js ${NODE_MAJOR}.x desde NodeSource"
# El "nodejs" que trae el repositorio normal de Debian suele quedarse en una
# versión vieja (en trixie es la 20.x, que ya salió de soporte LTS). NodeSource
# da una versión moderna y con soporte activo.
if ! command -v node >/dev/null 2>&1 || [ "$(node -v | cut -d. -f1 | tr -d v)" -lt "$NODE_MAJOR" ]; then
  curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | sudo -E bash -
  sudo apt-get install -y nodejs
else
  echo "Ya tienes Node $(node -v), se omite la instalación."
fi

echo "==> 3/5 Entorno virtual y dependencias del backend"
cd "$PROJECT_ROOT/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
# Crea backend/.env si falta y genera un SECRET_KEY aleatorio real
# (nunca deja el valor de ejemplo).
python scripts/generate_secrets.py
echo "   Solo falta agregar al menos una API key de IA en backend/.env."
deactivate

echo "==> 4/5 Dependencias del frontend"
cd "$PROJECT_ROOT/frontend"
npm install
if [ ! -f .env ]; then
  cp .env.example .env
fi

echo "==> 5/5 Listo."
echo ""
echo "Para arrancar el backend:"
echo "  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000"
echo ""
echo "Para arrancar el frontend (en otra terminal):"
echo "  cd frontend && npm run dev"
