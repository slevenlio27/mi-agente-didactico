# Instalación en Linux

Esta guía cubre Linux en general. Si usas **Debian o Ubuntu**, `INSTALL_DEBIAN.md`
tiene una versión más detallada con soluciones a problemas específicos de esa
familia — puedes usar cualquiera de las dos, dicen básicamente lo mismo.

## Opción rápida: script automático (detecta tu distro)

```bash
chmod +x scripts/setup-linux.sh
./scripts/setup-linux.sh
```

Detecta si tienes `apt` (Debian/Ubuntu/Mint), `dnf` (Fedora/RHEL/CentOS
Stream), `pacman` (Arch/Manjaro) o `zypper` (openSUSE), instala Python,
Node.js 24 y las herramientas de compilación necesarias con el gestor de
paquetes correspondiente, crea el entorno virtual, instala las dependencias
del backend y del frontend, y copia los `.env.example` a `.env` si no
existen todavía.

Después solo falta:

1. Editar `backend/.env` y agregar al menos una API key de IA (el `SECRET_KEY` ya se generó solo).
2. Arrancar todo con:
   ```bash
   ./dev.sh
   ```

Si tu distro no es ninguna de esas cuatro, o el script falla en algún paso,
sigue la guía manual de abajo.

## Instalación manual, paso a paso

### 1. Paquetes del sistema

Necesitas: Python 3.11 o más nuevo con `venv` y `pip`, herramientas de
compilación (gcc/make), y `curl`.

```bash
# Debian / Ubuntu / Mint
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip python3-dev build-essential curl

# Fedora / RHEL / CentOS Stream
sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ make curl

# Arch / Manjaro
sudo pacman -Sy --needed python python-pip base-devel curl

# openSUSE
sudo zypper install -y python3 python3-pip python3-devel gcc gcc-c++ make curl
```

**Nota sobre PEP 668 ("externally-managed-environment"):** en distros
recientes (Debian 12+, Ubuntu 23.04+, Fedora 38+), `pip install` directo al
sistema está bloqueado a propósito. Esto no afecta a este proyecto porque
siempre instalamos dentro de un entorno virtual (`python3 -m venv .venv`),
que queda fuera de esa restricción — pero si alguna vez ves ese error, es
la causa.

### 2. Node.js

Los repositorios oficiales de Debian/Ubuntu/Fedora suelen traer una versión
de Node.js más vieja que la que tiene soporte activo. La forma más simple de
tener una versión reciente:

```bash
# Debian / Ubuntu (NodeSource)
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt-get install -y nodejs

# Fedora / RHEL (NodeSource)
curl -fsSL https://rpm.nodesource.com/setup_24.x | sudo -E bash -
sudo dnf install -y nodejs

# Arch / Manjaro (el repo oficial ya suele estar al día)
sudo pacman -Sy --needed nodejs npm
```

Verifica con `node -v` — deberías ver v20 o más nuevo (idealmente v24).

### 3. Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

python scripts/generate_secrets.py   # crea .env y un SECRET_KEY aleatorio real
# Edita .env: agrega al menos una API key
# (OPENAI_API_KEY, GEMINI_API_KEY o ANTHROPIC_API_KEY)

uvicorn app.main:app --reload --port 8000
```

En Linux, a diferencia de Windows, `uvicorn` (sin `python -m` delante) y
`--reload` funcionan sin los problemas que documentamos para Windows —
no hace falta ningún rodeo especial aquí.

### 4. Frontend (React + Vite)

En otra terminal:

```bash
cd frontend
npm install
cp .env.example .env   # ya trae VITE_API_URL=http://localhost:8000
npm run dev
```

Abre `http://localhost:5173`.

**Si `npm install` da un error de permisos (`EACCES`):** casi siempre es
porque alguna vez se corrió `npm install` con `sudo`. Solución:
```bash
sudo chown -R $USER:$USER .
rm -rf node_modules package-lock.json
npm install
```
Y de ahí en adelante, nunca antepongas `sudo` a comandos de `npm`.

### 5. Arranque rápido (los dos servidores a la vez)

```bash
chmod +x dev.sh
./dev.sh
```

## Otras guías relacionadas

- **`INSTALL_DEBIAN.md`** — la misma instalación pero con más detalle,
  específica para Debian/Ubuntu.
- **`INSTALL_MYSQL.md`** — si vas a usar MySQL en vez de SQLite.
- **`INSTALL_WINDOWS.md`** — si en cambio estás en Windows.
- La sección "Configurar Google Sign-In" del `README.md` principal — los
  pasos son los mismos sin importar el sistema operativo.
