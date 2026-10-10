# Desplegar en Railway

La app se publica como **un solo servicio**: el backend (FastAPI) sirve también el
frontend compilado, todo desde una misma dirección `https://`. Así la sesión de los
docentes funciona en todos los navegadores (sin cookies "de terceros") y Google
Sign-In se configura con un solo origen.

Railway construye la app con el `Dockerfile` de la raíz del proyecto; no hace falta
ningún otro archivo de configuración.

## Antes de empezar

- El proyecto está en GitHub (repositorio privado está bien).
- Supabase ya funciona en tu instalación local: `/api/health` responde
  `"status":"ok"` y `"storage":"supabase"`. **Es obligatorio en Railway**: su disco es
  temporal y se borra en cada despliegue, así que los archivos deben ir a Supabase
  Storage.
- Tienes a mano tu `backend/.env` local: vas a copiar de ahí casi todas las variables.

## 1. Crear el servicio

1. Entra a https://railway.com e inicia sesión con tu cuenta de GitHub.
2. **New Project → Deploy from GitHub repo** y elige el repositorio
   `mi-agente-didactico`. Autoriza a Railway a leerlo si te lo pide.
3. Railway detecta el `Dockerfile` y empieza a construir. El primer despliegue
   **fallará** porque aún no tiene las variables: es normal, sigue con el paso 2.

## 2. Variables de entorno

En el servicio, abre **Variables → Raw Editor** y pega estas líneas, completando
los valores (los secretos, cópialos de tu `backend/.env`):

```
SECRET_KEY=...                 # el mismo de tu .env (o uno nuevo: cierra las sesiones)
API_KEYS_ENCRYPTION_KEY=...    # ¡EL MISMO de tu .env! Si cambia, no se pueden leer
                               # las claves de Gemini que guardaron los docentes
DATABASE_URL=postgresql://postgres.xxxx:CONTRASEÑA@aws-1-us-west-2.pooler.supabase.com:5432/postgres
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SECRET_KEY=sb_secret_...
SUPABASE_BUCKET=uploads

COOKIE_SECURE=true
COOKIE_SAMESITE=lax
FRONTEND_ORIGIN=https://TU-APP.up.railway.app   # lo completas en el paso 3
ADMIN_EMAILS=tu-correo@ejemplo.com

GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
GEMINI_API_KEY=                # vacío = cada docente usa su propia clave
GEMINI_MODEL=gemini-3.5-flash
GEMINI_TIMEOUT=120
MAX_UPLOAD_MB=10
```

**No agregues** `PORT` (Railway lo pone solo) ni `UPLOAD_DIR`. Las variables de
Railway no se suben a GitHub; tu `.env` tampoco debe subirse nunca.

## 3. Dirección pública y chequeo de salud

1. En el servicio: **Settings → Networking → Generate Domain**. Railway te da una
   dirección como `https://mi-agente-didactico-production.up.railway.app`.
2. Vuelve a **Variables** y pon esa dirección en `FRONTEND_ORIGIN` (sin barra al final).
3. En **Settings → Deploy → Healthcheck Path** escribe `/api/health`. Así Railway solo
   pasa el tráfico a una versión nueva cuando confirma que funciona.
4. Railway vuelve a desplegar con cada cambio de variables. Espera a que el
   despliegue aparezca como activo.

## 4. Google Sign-In

En Google Cloud, **Google Auth Platform → Clients →** tu cliente web:

1. En **Authorized JavaScript origins** agrega tu dirección de Railway
   (`https://….up.railway.app`, sin barra final). Puedes dejar también los de
   `localhost` para seguir probando en tu equipo.
2. En **Audience**, pulsa **Publish app** para que puedan entrar todos los docentes
   y no solo los usuarios de prueba. Como la app solo pide nombre y correo,
   normalmente no requiere revisión de Google.

Ya no hace falta poner el Client ID en el frontend: el backend lo entrega desde la
variable `GOOGLE_CLIENT_ID`.

## 5. Comprobar

1. Abre `https://TU-APP.up.railway.app/api/health`: debe responder `"status":"ok"`,
   `"storage":"supabase"`.
2. Abre `https://TU-APP.up.railway.app`, inicia sesión con tu cuenta (con los datos
   migrados a Supabase, tu usuario ya existe) y entra a **Administración**.
3. Prueba con **otra cuenta de Google**, que no sea de prueba, que el registro funciona.
4. Desde el chat, sube un PDF corto y haz una pregunta.

## Antes de invitar a los docentes

- **Página legal:** completa `frontend/src/pages/Legal.jsx` con el nombre de tu
  institución, un correo de contacto real y la normativa de datos de tu país.
- **Panel de administración:** revisa en *Apariencia y funciones* qué funciones
  quieres activas (registro abierto o no, proveedores de IA, subida de archivos).
- **Claves de Gemini:** si `GEMINI_API_KEY` está vacío, cada docente verá en el chat
  un aviso para crear y pegar la suya. Explícales que es gratis y toma un minuto.
- **Copias de seguridad:** el plan gratuito de Supabase no las hace. Exporta la base
  de datos periódicamente desde su panel.

## Actualizar la app

Cada `git push` a la rama principal despliega una versión nueva automáticamente.
Gracias al chequeo de salud, si la versión nueva no arranca, Railway mantiene la
anterior en línea. Los registros (logs) de cada despliegue están en la pestaña
**Deployments** del servicio.

## Dominio propio (cuando lo tengas)

1. En Railway: **Settings → Networking → Custom Domain**, escribe tu dominio (por
   ejemplo `agente.tuuniversidad.edu`) y crea en tu proveedor de DNS el registro que
   Railway te indique. El certificado HTTPS se genera solo.
2. Actualiza `FRONTEND_ORIGIN` con el dominio nuevo.
3. Agrega el dominio en **Authorized JavaScript origins** de Google.

## Problemas frecuentes

- **El despliegue falla y el registro dice "falta SECRET_KEY" o "API_KEYS_ENCRYPTION_KEY":**
  falta esa variable en Railway (paso 2).
- **`/api/health` dice `"degraded"`:** el campo `storage_detail` explica qué falta; lo
  habitual es `SUPABASE_URL` o `SUPABASE_SECRET_KEY` mal copiados.
- **Google muestra "origin_mismatch":** la dirección no está en *Authorized JavaScript
  origins*, o tiene una barra final o `http` en vez de `https`.
- **No se mantiene la sesión:** revisa `COOKIE_SECURE=true` y que entras por
  `https://`.
- **El chat tarda mucho con PDF grandes:** es normal hasta 1–2 minutos; el límite se
  ajusta con `GEMINI_TIMEOUT`.
