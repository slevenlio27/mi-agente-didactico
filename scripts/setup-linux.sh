#!/usr/bin/env bash
# Instala todo lo necesario para correr Mi Agente Didáctico en cualquier
# distribución de Linux (detecta automáticamente el gestor de paquetes).
#
# Uso:
#   chmod +x scripts/setup-linux.sh
#   ./scripts/setup-linux.sh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE_MAJOR=24   # Node 24 "Krypton" = LTS activa hasta 2028

echo "==> 1/5 Detectando gestor de paquetes"

if command -v apt-get >/dev/null 2>&1; then
  PKG_MANAGER="apt"
elif command -v dnf >/dev/null 2>&1; then
  PKG_MANAGER="dnf"
elif command -v pacman >/dev/null 2>&1; then
  PKG_MANAGER="pacman"
elif command -v zypper >/dev/null 2>&1; then
  PKG_MANAGER="zypper"
else
  echo "No reconocí tu gestor de paquetes (probé apt, dnf, pacman, zypper)."
  echo "Instala manualmente: Python 3.11+, python3-venv/pip, build tools, curl y Node.js 20+"
  echo "y vuelve a correr este script — se saltará este paso si ya detecta 'python3' y 'node'."
  PKG_MANAGER="none"
fi

echo "   Detectado: $PKG_MANAGER"

echo "==> 2/5 Paquetes del sistema (Python, herramientas de compilación, curl)"
case "$PKG_MANAGER" in
  apt)
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-pip python3-dev \
      build-essential curl ca-certificates
    ;;
  dnf)
    sudo dnf install -y python3 python3-pip python3-devel \
      gcc gcc-c++ make curl ca-certificates
    ;;
  pacman)
    sudo pacman -Sy --needed --noconfirm python python-pip base-devel curl ca-certificates
    ;;
  zypper)
    sudo zypper install -y python3 python3-pip python3-devel \
      gcc gcc-c++ make curl ca-certificates
    ;;
  none)
    echo "   Omitido — instala Python y las herramientas de compilación tú mismo."
    ;;
esac

echo "==> 3/5 Node.js ${NODE_MAJOR}.x"
CURRENT_NODE_MAJOR="0"
if command -v node >/dev/null 2>&1; then
  CURRENT_NODE_MAJOR="$(node -v | sed 's/^v//' | cut -d. -f1)"
fi

if [ "$CURRENT_NODE_MAJOR" -lt "$NODE_MAJOR" ]; then
  if [ "$PKG_MANAGER" = "pacman" ]; then
    # Arch suele traer una versión de Node ya reciente en el repo oficial.
    sudo pacman -Sy --needed --noconfirm nodejs npm
  elif [ "$PKG_MANAGER" = "apt" ] || [ "$PKG_MANAGER" = "dnf" ]; then
    # El "nodejs" de los repos de Debian/Ubuntu/Fedora suele quedarse atrás
    # de las versiones con soporte activo — usamos NodeSource en su lugar.
    curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" 2>/dev/null | sudo -E bash - 2>/dev/null || true
    if [ "$PKG_MANAGER" = "apt" ]; then
      sudo apt-get install -y nodejs
    else
      curl -fsSL "https://rpm.nodesource.com/setup_${NODE_MAJOR}.x" | sudo -E bash -
      sudo dnf install -y nodejs
    fi
  else
    echo "   Instala Node.js ${NODE_MAJOR}+ manualmente desde https://nodejs.org o con tu gestor de paquetes."
  fi
else
  echo "   Ya tienes Node $(node -v), se omite la instalación."
fi

echo "==> 4/5 Backend: entorno virtual y dependencias"
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

echo "==> 5/5 Frontend: dependencias de Node"
cd "$PROJECT_ROOT/frontend"
npm install
if [ ! -f .env ]; then
  cp .env.example .env
fi

echo ""
echo "Listo. Para arrancar backend y frontend juntos, desde la raíz del proyecto:"
echo "  ./dev.sh"
echo ""
echo "Para arrancarlos por separado, o si tu distro no quedó cubierta arriba,"
echo "ve INSTALL_LINUX.md."
