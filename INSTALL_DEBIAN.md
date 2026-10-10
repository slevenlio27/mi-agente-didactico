# Instalación en Debian (13 "trixie")

Esta guía asume Debian 13 (trixie), la versión estable actual, que trae
Python 3.13 por defecto. Si usas Debian 12 (bookworm), casi todo aplica igual;
la única diferencia es que Python por defecto es la 3.11 en vez de la 3.13
(sigue funcionando bien con este proyecto).

## Opción rápida: script automático

```bash
chmod +x scripts/setup-debian.sh
./scripts/setup-debian.sh
```

Esto instala los paquetes del sistema, Node.js 24 LTS vía NodeSource, crea el
entorno virtual de Python, instala las dependencias del backend y del
frontend, y copia los `.env.example` a `.env` si no existen todavía.

Después de correrlo, solo falta:
1. Editar `backend/.env` y agregar al menos una API key de IA (el `SECRET_KEY` ya se generó solo).
2. Arrancar ambos servidores (ver el final de esta guía).

## Opción manual, paso a paso

### 1. Paquetes del sistema

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip python3-dev \
  build-essential curl ca-certificates
```

`python3-venv` y `build-essential` son necesarios: Debian bloquea instalar
paquetes de Python fuera de un entorno virtual (PEP 668), y algunos paquetes
de Python todavía necesitan compilar una pequeña parte en C.

### 2. Node.js

El `nodejs` que trae el repositorio normal de Debian 13 es la rama 20.x, que
ya salió de soporte LTS. Instala una versión con soporte activo desde
NodeSource:

```bash
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt-get install -y nodejs
node -v   # debería mostrar v24.x
```

### 3. Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

python scripts/generate_secrets.py   # crea .env y un SECRET_KEY aleatorio real
# Edita .env: agrega al menos una API key
# (OPENAI_API_KEY y/o GEMINI_API_KEY y/o ANTHROPIC_API_KEY)

uvicorn app.main:app --reload --port 8000
```

En Linux, a diferencia de Windows, el comando `uvicorn` (sin `python -m`
delante) funciona sin problemas una vez que el venv está activado con
`source .venv/bin/activate` — nota la ruta `.venv/bin/activate`, no
`.venv/Scripts/activate` como en Windows.

### 4. Frontend (React + Vite)

En otra terminal:

```bash
cd frontend
npm install
cp .env.example .env   # ya trae VITE_API_URL=http://localhost:8000
npm run dev
```

Abre `http://localhost:5173`.

## Diferencias con la guía de Windows

- Activar el venv: `source .venv/bin/activate` (no `.venv/Scripts/activate`).
- `uvicorn` y `pip` normalmente sí se encuentran en el `PATH` una vez activado
  el venv en Linux — no hace falta el rodeo de `python -m` que usamos en
  Windows para esquivar el problema de los alias de Microsoft Store.
- No existe el problema de "python.exe redirige a la Microsoft Store": eso es
  específico de Windows.
