# Instalación en Windows

## Opción rápida: script automático

Desde PowerShell, parado en la carpeta raíz del proyecto (`mi-agente-didactico`):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup-windows.ps1
```

Esto instala las dependencias del backend y del frontend, y copia los
`.env.example` a `.env` si no existen todavía. Después solo falta:

1. Editar `backend\.env` y agregar al menos una API key de IA (el `SECRET_KEY` ya se generó solo).
2. Arrancar todo con:
   ```powershell
   .\dev.ps1
   ```
   Esto abre dos ventanas de PowerShell nuevas, una para el backend
   (`http://localhost:8000`) y otra para el frontend (`http://localhost:5173`).

Si prefieres instalar todo a mano, o si el script automático falla en algún
paso, sigue la guía de abajo — incluye las soluciones a los problemas más
comunes en Windows.

## Instalación manual, paso a paso

### 1. Instala Python

Descarga el instalador desde https://www.python.org/downloads/ y, **muy
importante**, marca la casilla **"Add python.exe to PATH"** durante la
instalación.

**Problema común:** si al escribir `python` en una terminal se abre la
Microsoft Store en vez de ejecutar Python, es un alias de Windows que
redirige `python.exe` ahí. Para arreglarlo:

1. Abre **Configuración > Aplicaciones > Configuración avanzada de
   aplicaciones > Alias de ejecución de aplicaciones**.
2. Desactiva los interruptores de `python.exe` y `python3.exe`.
3. Cierra y abre una terminal nueva.

### 2. Instala Node.js

Descarga la versión **LTS** desde https://nodejs.org e instálala con las
opciones por defecto (incluye npm). Reinicia la terminal después.

### 3. Backend (FastAPI)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt

.venv\Scripts\python.exe scripts\generate_secrets.py   # crea .env y un SECRET_KEY aleatorio real
# Edita .env: agrega al menos una API key
# (OPENAI_API_KEY, GEMINI_API_KEY o ANTHROPIC_API_KEY)
```

**Por qué usamos `.venv\Scripts\python.exe -m pip` en vez de solo `pip`:**
en Windows es común que el comando `pip` del PATH apunte a una instalación
de Python distinta a la del entorno virtual — eso deja los paquetes
instalados en el lugar equivocado, y luego el servidor no los encuentra
aunque `pip list` diga que sí están instalados. Llamar al `python.exe` del
`.venv` por su ruta completa evita ese problema de raíz.

Para arrancar el servidor:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

**Por qué sin `--reload`:** en Python 3.13/3.14 + Windows, el proceso hijo
que uvicorn crea para el auto-reinicio a veces no hereda correctamente las
dependencias del entorno virtual, y el servidor falla con
`ModuleNotFoundError` al guardar un cambio. Si editas el código del
backend, detén el servidor (`Ctrl+C`) y vuelve a correr el comando — es un
paso manual de más, pero evita ese error. Si quieres arriesgarte con
`--reload`, funciona bien en Python 3.11/3.12.

**Por qué llamamos a `python -m uvicorn` y no a `uvicorn` directo:** en
algunas instalaciones de Windows el ejecutable `uvicorn.exe` que crea pip
no queda bien enlazado al PATH de la terminal (Git Bash en particular), aun
con el venv activado. Pasar por `python -m` evita depender de eso.

### 4. Frontend (React + Vite)

En otra terminal:

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Abre `http://localhost:5173`.

**Si `npm install` o `npm run dev` fallan con un error de permisos
(`EACCES`, `EPERM`, o "no se puede crear la carpeta"):** casi siempre es
porque el proyecto está dentro de una carpeta sincronizada por OneDrive, o
porque una instalación anterior se corrió con permisos de administrador.
Mueve el proyecto fuera de la carpeta de OneDrive (por ejemplo a
`C:\Users\tu_usuario\proyectos\`), o corre `npm install` sin "Ejecutar como
administrador".

### 5. Arranque rápido (los dos servidores a la vez)

Una vez instalado todo lo anterior, desde la raíz del proyecto:

```powershell
.\dev.ps1
```

## Configurar Google Sign-In (opcional)

Igual que en Linux/macOS — ver la sección "Configurar Google Sign-In" del
`README.md` principal. Los pasos en Google Cloud Console son los mismos sin
importar el sistema operativo; solo cambia dónde editas el `.env`
(`backend\.env` y `frontend\.env` con rutas de Windows).

## Diferencias con la guía de Linux/Debian

- Activar el venv manualmente (si no usas `dev.ps1`):
  `.venv\Scripts\activate` (no `.venv/bin/activate`).
- Los ejecutables de Python instalados en el venv están en
  `.venv\Scripts\`, no en `.venv/bin/`.
- El problema de "python.exe redirige a la Microsoft Store" y el de
  "`uvicorn` no encontrado en el PATH" son específicos de Windows; en
  Linux/macOS no aparecen.
- `dev.sh` (para Git Bash) también funciona en Windows si prefieres una
  sola terminal en vez de dos ventanas — detecta automáticamente la ruta
  `.venv\Scripts` y no necesita `dev.ps1`. `dev.ps1` es la alternativa
  nativa de PowerShell, con cada servidor en su propia ventana.
