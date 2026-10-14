# Mi Agente Didáctico — versión full-stack

Aplicación web para docentes universitarios: autenticación real, historial de
conversaciones y archivos guardado en base de datos, y un chat de IA que usa
**Gemini** por defecto (Claude y ChatGPT se pueden activar desde el panel de
administración). Las claves de las IA quedan solo en el servidor: el navegador
nunca las ve.

## Estructura

```
backend/    API en FastAPI + SQLite (auth, chat, archivos)
frontend/   Interfaz en React + Vite
dev.sh      Arranca los dos servidores juntos en una sola terminal
```

Backend y frontend son proyectos completamente independientes (cada uno con
sus propias dependencias) que se conectan solo por HTTP: el frontend llama al
backend usando la URL de `VITE_API_URL` (en `frontend/.env`), y el backend
acepta esas peticiones gracias a `FRONTEND_ORIGIN` (en `backend/.env`). La
sesión viaja entre ambos como una cookie `HttpOnly`.

> **¿Publicar la app para los docentes?** Sigue **`DEPLOY_RAILWAY.md`**: un solo
> servicio en Railway (el backend sirve también el frontend, en una misma
> dirección `https://`), con la base de datos y los archivos en Supabase.
>
> **Rutas de la API:** todas están bajo `/api` (por ejemplo `/api/auth/login`,
> `/api/health`); la documentación interactiva está en `/api/docs`.

> **¿Base de datos en la nube?** Para usar Supabase (PostgreSQL + Storage para
> los archivos), sigue **`INSTALL_SUPABASE.md`**. Incluye un script para copiar
> tus datos actuales y una tarea de GitHub que evita que el proyecto gratuito se
> pause por inactividad.

> **¿Windows, Debian o Linux en general?** Esta guía asume una terminal tipo
> Unix (macOS o Linux). Si usas Windows, sigue en cambio **`INSTALL_WINDOWS.md`**
> — tiene los mismos pasos adaptados, con las soluciones a los problemas más
> comunes de Windows (Python vía Microsoft Store, `uvicorn` no encontrado,
> permisos de npm). Para Debian/Ubuntu, usa **`INSTALL_DEBIAN.md`**; para
> cualquier otra distro de Linux (Fedora, Arch, openSUSE...), usa
> **`INSTALL_LINUX.md`**.

## Arranque rápido (los dos servidores a la vez)

Después de instalar las dependencias de `backend/` y `frontend/` (ver abajo),
puedes levantar todo con un solo comando desde la raíz del proyecto:

```bash
./dev.sh
```

Esto arranca el backend en `http://localhost:8000` y el frontend en
`http://localhost:5173` en la misma terminal. `Ctrl+C` detiene ambos.

## 1. Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt

python scripts/generate_secrets.py   # crea .env y un SECRET_KEY aleatorio real
# Edita .env: agrega GEMINI_API_KEY (créala en https://aistudio.google.com/apikey).
# OPENAI_API_KEY y ANTHROPIC_API_KEY solo hacen falta si activas esas IA
# en el panel de administración. Sin clave, el proveedor devuelve un error
# controlado en vez de fallar de forma confusa.

uvicorn app.main:app --reload --port 8000
```

La API queda en `http://localhost:8000`. Puedes revisar `http://localhost:8000/docs`
para ver la documentación interactiva (Swagger) que genera FastAPI automáticamente.

La base de datos SQLite (`app.db`) y los archivos subidos (`uploads/`) se crean
solos la primera vez que arranca el servidor.

## 2. Frontend (React + Vite)

```bash
cd frontend
npm install
cp .env.example .env   # ya trae VITE_API_URL=http://localhost:8000

npm run dev
```

Abre `http://localhost:5173`. Regístrate con un correo y contraseña, e inicia sesión.

## Cómo se resolvió cada requerimiento del documento

**1. Autenticación real**
- Contraseñas con hash `bcrypt` (usando la librería `bcrypt` directamente,
  nunca se guardan en texto plano).
- Sesión con JWT dentro de una cookie **HttpOnly** (no accesible desde JavaScript,
  mitiga robo de sesión por XSS) en vez de guardar el token en `localStorage`.
- Todas las rutas de chat y archivos exigen `get_current_user`: sin cookie válida,
  responden 401.
- **Iniciar sesión con Google** (opcional): botón oficial de Google Identity
  Services. El backend valida el token contra los servidores de Google antes
  de crear la sesión — ver "Configurar Google Sign-In" más abajo.

**2. Integración de IA (Gemini por defecto; ChatGPT y Claude opcionales)**
- `backend/app/ai_providers.py` hace las llamadas reales a Gemini, OpenAI y Claude.
- **Solo Gemini por defecto:** las instalaciones nuevas arrancan con Claude y
  ChatGPT desactivados; se activan o desactivan en `/admin` > Apariencia y
  funciones. En una base de datos ya existente, se cambian desde ese mismo panel.
- **Modelo de Gemini configurable:** `GEMINI_MODEL` en `backend/.env`
  (por defecto `gemini-3.5-flash`). Google retira modelos antiguos — por
  ejemplo `gemini-1.5-flash` ya no existe y respondía error 404 —, así que si
  algún día el chat de Gemini falla con 404, cambia este valor por un modelo
  vigente de https://ai.google.dev/gemini-api/docs/models.
- **Registros en tu cuenta de Google (opcional):** cada conversación ya se
  guarda en la cuenta del docente dentro de la app. Además, si en
  https://aistudio.google.com/logs > Settings activas el registro de la API
  `generateContent` para tu proyecto, Google guarda una copia de cada
  solicitud (hasta 55 días; exportable como dataset). Requiere un proyecto con
  facturación activa. La política de privacidad (`/legal`) ya lo informa.
- Las API keys del servidor viven solo en variables de entorno (`.env`), nunca se
  envían al frontend ni se guardan en el navegador.
- **Clave propia por docente:** en "Preferencias de IA" (o directamente en
  el chat, ver abajo), cada docente puede pegar su propia API key. Se usa en
  lugar de la clave del servidor para sus conversaciones, así el consumo va
  a su propia cuenta. Las claves de Gemini se **comprueban con Google antes
  de guardarlas**, y todas se guardan **cifradas** (Fernet) con la llave
  `API_KEYS_ENCRYPTION_KEY` de `backend/.env`, distinta del `SECRET_KEY`.
  Nunca se devuelven al navegador: solo se informa si existen
  (`GET /auth/me/api-keys`). Las claves que versiones anteriores guardaron
  en texto plano se cifran solas al arrancar el servidor.
  **No pierdas `API_KEYS_ENCRYPTION_KEY`**: sin ella las claves guardadas no
  se pueden leer y cada docente tendría que volver a pegar la suya.
- **Que cada docente use su propia cuenta de Gemini:** deja `GEMINI_API_KEY`
  vacío en `backend/.env`. Quien abra el asistente sin clave verá un aviso con
  un botón a https://aistudio.google.com/apikey y un campo para pegar su clave
  ahí mismo. Los planes de consumo de Google AI (Pro/Ultra) no sirven para
  esto: Google los aplica solo dentro de AI Studio, no a la API.
- La clave viaja a Google en el encabezado `x-goog-api-key`, nunca en la URL.
  Si la red bloquea a Google (proxy o firewall, frecuente en redes
  universitarias), el chat lo explica en vez de decir que la clave es inválida;
  hay que permitir `generativelanguage.googleapis.com`.
- El frontend solo manda `provider` (y opcionalmente `model`) al crear una
  conversación; el backend decide qué API llamar y con qué clave.
- Manejo de errores: si falta una clave o la API tarda/falla, se devuelve un
  mensaje claro (`502` con detalle) en vez de romper la conversación.

**¿Olvidaste tu contraseña?**
- En la ventana de inicio de sesión, el docente pulsa «¿Olvidaste tu contraseña?» y
  escribe su correo. La respuesta es siempre la misma, exista o no la cuenta (así
  nadie puede averiguar qué correos están registrados).
- En `/admin`, el administrador ve las solicitudes pendientes y genera un **enlace
  de un solo uso que vence en 24 horas** (también desde el botón «Restablecer
  contraseña» de cualquier docente). Lo copia o lo envía por correo con un clic.
- El docente abre el enlace (`/restablecer#token=…`) y elige su contraseña nueva.
  El código va después del `#`, así que nunca llega al servidor ni a sus registros;
  en la base de datos solo se guarda su hash. Generar un enlace nuevo anula los
  anteriores.
- No necesita configurar correo. Cuando haya un dominio propio, se puede agregar
  el envío automático del enlace por correo.

**El asistente lee los archivos y conoce al docente**
- **Adjuntos:** los PDF e imágenes que el docente adjunta en el chat se envían a
  Gemini junto con la pregunta, y los archivos de texto se envían como texto
  (también a ChatGPT y Claude, que en esta app solo reciben texto). Como la IA no
  recuerda entre mensajes, los adjuntos de la conversación se reenvían en cada
  mensaje, priorizando los más recientes hasta `MAX_ATTACHMENTS_MB` (13 MB por
  defecto, por el límite de 20 MB por petición de Gemini); los que no caben se
  le mencionan a la IA para que pida volver a adjuntarlos.
- **Perfil docente:** en el Panel docente, cada docente indica su materia, el
  nivel de sus estudiantes, la duración de sus clases y su estilo preferido. Se
  envía como instrucción de sistema en todas sus conversaciones.
- La IA **no se reentrena** con el material de nadie: cada docente solo aporta
  contexto a sus propias conversaciones.

**3. Panel de usuario privado**
- **Historial de consultas**: tabla `chat_sessions` + `chat_messages` en SQLite;
  el frontend lista, busca por título y permite retomar cualquier conversación.
- **Galería de archivos**: tabla `uploaded_files`; cada archivo subido queda
  asociado al docente (y opcionalmente a una conversación) y aparece en
  "Mi galería" con descarga y borrado.
- **Carga de archivos**: guardados en disco local bajo `backend/uploads/<user_id>/`,
  con nombre aleatorio para evitar colisiones/sobrescritura y una whitelist de
  tipos permitidos (PDF, PNG, JPEG, WEBP, TXT, MD) para no aceptar cualquier
  archivo. Si más adelante migras a un servicio en la nube (S3, GCS, etc.), el
  único lugar que hay que cambiar es `backend/app/routers/files.py`.

## Configurar Google Sign-In (opcional)

Si no configuras esto, la app funciona igual con correo y contraseña — el
botón de Google simplemente no aparece.

1. Ve a https://console.cloud.google.com/apis/credentials
2. Crea un "ID de cliente de OAuth" de tipo **Aplicación web**.
3. En "Orígenes de JavaScript autorizados" agrega `http://localhost:5173`.
4. Copia el "Client ID" generado (termina en `.apps.googleusercontent.com`).
5. Pégalo en **ambos** archivos `.env`:
   - `backend/.env` → `GOOGLE_CLIENT_ID=...`
   - `frontend/.env` → `VITE_GOOGLE_CLIENT_ID=...`
6. Reinicia los dos servidores.

El backend nunca recibe la contraseña de la cuenta de Google del docente —
solo un token firmado por Google que contiene su correo, nombre y un
identificador único, y ese token se valida contra Google antes de confiar
en él.

## Panel de administración

En `/admin` (solo cuentas de administrador) hay, además de las estadísticas y
la gestión de docentes, una sección **Apariencia y funciones**:

- **Apariencia:** nombre del sitio, color institucional (modo claro y oscuro)
  y color del chat para cada IA. Los cambios se ven en vivo mientras editas y
  se aplican a todos los visitantes al guardar.
- **Funciones:** activar o desactivar el registro de cuentas nuevas, el inicio
  de sesión con Google, el asistente, la subida de archivos, la agenda, las
  claves de API propias, cada proveedor de IA, las estadísticas de visitas, el
  aviso de cookies y los colores por materia.

Los interruptores se aplican **en el servidor**, no solo ocultando botones:
una función apagada responde `403` aunque alguien llame a la API
directamente. Para que nadie pierda acceso a sus datos, apagar la subida de
archivos o la agenda solo impide crear cosas nuevas; ver, descargar y borrar
lo propio sigue funcionando. Los administradores conservan el acceso con
Google aunque esté apagado para el resto.

## Páginas legales

`/legal` contiene la **Política de privacidad**, los **Términos y condiciones**
y la **Política de cookies**, enlazadas desde el pie de página. Un aviso de
cookies aparece la primera vez que alguien visita el sitio. Revisa y adapta
el texto a tu institución (nombre del responsable, correo de contacto,
normativa local de protección de datos) antes de publicar.

## Seguridad

El detalle completo de la última auditoría (hallazgos, parches y cómo se
verificó cada uno) está en **`AUDIT.md`**. Lo que cambia en la práctica:

- **`SECRET_KEY` se genera solo y nunca se usa un valor de ejemplo.** Los
  scripts de instalación y `dev.sh` / `dev.ps1` ejecutan
  `backend/scripts/generate_secrets.py`, que crea un secreto aleatorio si falta
  o si detecta un valor de ejemplo, y conserva uno válido. El backend además se
  niega a arrancar con un secreto vacío, de ejemplo o de menos de 32 caracteres.
  Para cambiarlo a propósito (cierra todas las sesiones):
  `python scripts/generate_secrets.py --rotate`.
- **Contraseñas de MySQL generadas**, nunca escritas en el repositorio (ver
  `INSTALL_MYSQL.md`).
- **Límite de intentos** en login, registro y Google (10–20 cada 5 minutos por
  IP). Si ves `429 Demasiados intentos`, espera unos minutos. Es un límite en
  memoria por proceso; con varios workers o instancias, conviene moverlo a Redis.
- **JWT con PyJWT** en vez de `python-jose` (se eliminó una dependencia con una
  vulnerabilidad conocida sin parche). Si actualizas desde una versión anterior,
  reinstala dependencias: `pip install -r requirements.txt`.
- **Subida de archivos más estricta:** se verifica el contenido real del
  archivo (no solo la extensión o el tipo declarado) y se corta la subida en
  cuanto supera `MAX_UPLOAD_MB`.
- Si el frontend y el backend viven en **dominios distintos** (no solo puertos
  distintos de localhost), usa `COOKIE_SAMESITE=none` y `COOKIE_SECURE=true`
  (requiere HTTPS).
- SQLite es perfecto para desarrollo; para producción con varios usuarios
  concurrentes, usa MySQL (ver `INSTALL_MYSQL.md`).
