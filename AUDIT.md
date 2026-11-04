# Auditoría de seguridad

Revisión manual completa del backend y el frontend, más verificación automática
de dependencias (`pip-audit`, `npm audit`). Cada hallazgo de abajo se probó
de verdad (no solo se leyó el código): se escribió una prueba mínima que
reproduce el problema antes del parche y confirma que el parche lo cierra.

## Hallazgos y parches

### 1. Crítico (condicional) — `SECRET_KEY` con valor por defecto público
**Antes:** si `backend/.env` no definía `SECRET_KEY`, el servidor arrancaba
igual usando un valor de ejemplo publicado en este mismo repositorio.
Cualquiera que conociera ese valor podía forjar un token de sesión válido
para cualquier usuario, incluido un administrador.
**Parche:** `backend/app/config.py` ahora se niega a arrancar (`sys.exit`)
si `SECRET_KEY` falta o coincide con el valor de ejemplo.
**⚠️ Acción requerida:** si tu `backend/.env` todavía tiene el valor de
ejemplo, el servidor no va a arrancar hasta que generes uno real:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Medio-alto — Inyección de ruta en la llamada a la API de Gemini
**Antes:** el campo `model` que manda el cliente se pegaba sin validar
directamente en la URL de la petición saliente a Google
(`.../models/{model}:generateContent`). Un docente autenticado podía meter
`/`, `?`, `#` u otros caracteres para intentar que el servidor golpeara
otras rutas de esa API usando la clave del servidor.
**Parche:** `provider` ahora es un `Literal` (solo acepta los tres valores
válidos) y `model` debe cumplir un patrón estricto
(`^[A-Za-z0-9._:-]{1,100}$`), validado tanto en el esquema de entrada como
otra vez dentro de `ai_providers.py` antes de construir la URL.

### 3. Medio — El tipo de archivo se validaba solo por lo que dice el navegador
**Antes:** `Content-Type` es un dato que pone el cliente y se puede
falsificar; el servidor confiaba en él sin revisar el contenido real.
**Parche:** se verifica la firma de bytes real (los primeros bytes del
archivo) contra el tipo declarado para PDF, PNG, JPEG y WEBP antes de
aceptarlo.

### 4. Medio — El límite de tamaño de subida se revisaba después de leer todo el archivo
**Antes:** el servidor leía el archivo completo en memoria y recién
después comparaba el tamaño contra `MAX_UPLOAD_MB`, lo que permitía a
alguien intentar agotar memoria/disco con una subida enorme antes de que
el límite hiciera efecto.
**Parche:** ahora se lee en bloques de 1 MB y se corta apenas se supera el
límite configurado.

### 5. Medio — Sin límite de intentos en login, registro y Google Sign-In
**Antes:** nada impedía probar contraseñas en bucle contra `/auth/login`.
**Parche:** nuevo limitador (`backend/app/rate_limit.py`), en memoria, por
IP: 10 intentos/5 min en login y registro, 20/5 min en Google, 60/min en la
analítica pública. Limitación honesta: es por proceso — con varios workers
detrás de un balanceador, el límite efectivo sube proporcionalmente; para
producción a esa escala habría que moverlo a Redis.

### 6. Bajo-medio — Campos de texto sin límite de longitud
**Antes:** el contenido de un mensaje de chat, el nombre completo, las
claves de API propias y el token de Google no tenían tope de tamaño —
alguien podía mandar un mensaje enorme (costo real contra la API de IA de
pago) o un valor que rompiera al guardarlo en MySQL.
**Parche:** se agregaron límites explícitos (`max_length`) a cada campo,
alineados con el tamaño de columna correspondiente en la base de datos.

### 7. Bajo — Nombre de archivo subido sin sanear
**Antes:** el nombre original del archivo se guardaba tal cual lo mandaba
el cliente, incluyendo posibles caracteres de control.
**Parche:** se limpian caracteres de control y se recorta a 255 caracteres
antes de guardarlo.

### 8. Informativo — Dependencia `ecdsa` con CVE sin parche disponible
`pip-audit` encontró una vulnerabilidad conocida (`PYSEC-2026-1325`) en el
paquete `ecdsa`, sin versión corregida disponible (los mantenedores no
planean arreglarla — es una limitación de diseño de una librería pura en
Python). Veníamos usando `python-jose`, que trae `ecdsa` como dependencia
obligatoria. **En la práctica no era explotable en este proyecto:** el
JWT de sesión siempre usa HS256 (HMAC, no ECDSA), así que el código
vulnerable nunca se ejecutaba. Aun así, para no depender de un paquete con
una vulnerabilidad sin arreglo, se migró de `python-jose` a `PyJWT`
(misma función, sin esa dependencia). `pip-audit` ya no reporta nada.

## Verificación

- `pip-audit` sobre las dependencias del backend: **0 vulnerabilidades**
  (antes: 1 paquete con CVE sin parche).
- `npm audit` sobre las dependencias del frontend: **0 vulnerabilidades**.
- Cada parche de arriba se probó con una prueba funcional real (no solo
  lectura de código): arranque con/sin `SECRET_KEY`, límite de intentos
  bloqueando correctamente, detección de un archivo HTML disfrazado de
  PNG, rechazo de `provider`/`model` maliciosos, y que login/registro
  siguen funcionando con la librería JWT nueva.


## Segunda revisión (corrección de secretos y panel de configuración)

### 9. Crítico (condicional) — La corrección del hallazgo 1 estaba incompleta
**Error de la primera auditoría:** el servidor rechazaba el secreto
`changeme-please-generate-a-random-secret`, pero `backend/.env.example` traía
**otro** valor de ejemplo (`change-this-to-a-long-random-string`). Quien
copiara `.env.example` sin editarlo arrancaba con una clave pública, que es
justo lo que el hallazgo 1 pretendía impedir.
**Parche:**
- `backend/.env.example` ya no trae ningún valor: `SECRET_KEY=` vacío.
- El servidor rechaza cualquier secreto vacío, cualquier valor de ejemplo
  conocido o que empiece por `change`/`your-`/`tu-`, y cualquier secreto de
  menos de 32 caracteres.
- Nuevo `backend/scripts/generate_secrets.py` (Python puro, funciona en
  Windows, Linux y macOS): crea `backend/.env` si falta y escribe un
  `SECRET_KEY` aleatorio de 64 caracteres, conservando uno ya válido. Los
  scripts de instalación y `dev.sh` / `dev.ps1` lo ejecutan siempre antes de
  arrancar. En Linux/macOS deja el archivo con permisos `600`.
**Verificado:** se probó el arranque con vacío, con los dos valores de
ejemplo y con una clave corta (los cuatro se rechazan), y que el generador
reemplaza el valor de ejemplo y conserva uno válido al correrlo dos veces.

### 10. Medio — Contraseñas de MySQL de ejemplo fijas y puerto expuesto a la red
**Antes:** `docker-compose.mysql.yml` tenía las contraseñas escritas
(`agente_pass`, `change-this-root-password`) y publicaba el puerto 3306 en
todas las interfaces de red.
**Parche:** las contraseñas se leen de un `.env` en la raíz (generado al azar
por `generate_secrets.py --mysql`, incluido en `.gitignore`); si faltan,
Docker se detiene con un error en vez de usar un valor por defecto. El
puerto queda limitado a `127.0.0.1`. La guía `INSTALL_MYSQL.md` ya no incluye
contraseñas de ejemplo.

### 11. Medio — Vinculación de cuentas de Google por correo no verificado
**Antes:** al entrar con Google, si existía una cuenta local con el mismo
correo, se vinculaba automáticamente sin comprobar que Google hubiera
verificado ese correo.
**Parche:** se exige `email_verified` en el token de Google antes de crear
o vincular cualquier cuenta.

### Panel de configuración del sitio (nuevo) — controles aplicados
- Solo administradores pueden leer o cambiar la configuración (`403` para
  el resto, probado).
- Los colores se inyectan como variables CSS en el navegador de todos los
  visitantes, así que solo se acepta el formato exacto `#rrggbb`, validado en
  el servidor y otra vez en el navegador antes de aplicarlo. Se probó que se
  rechazan intentos como `#000000;}body{display:none`.
- Cada interruptor de función se aplica en el servidor (responde `403`),
  incluidas las conversaciones creadas antes de apagar un proveedor. Se
  impide dejar el asistente activo sin ningún proveedor.
- 32 pruebas de la API real cubren todos los interruptores y la validación.

### Verificación tras la segunda revisión
- `pip-audit`: 0 vulnerabilidades. `npm audit`: 0 vulnerabilidades.
- Build de producción del frontend compila sin errores.
- Búsqueda de credenciales de ejemplo en todo el repositorio: ninguna
  (solo aparecen dentro de la lista de valores prohibidos).

## Tercera revisión (claves de API por docente)

### 12. Medio — Claves de API de los docentes guardadas en texto plano
**Antes:** quien obtuviera una copia de la base de datos podía usar las claves
de todos los docentes. **Parche:** cifrado Fernet con una llave dedicada
(`API_KEYS_ENCRYPTION_KEY`, generada por `generate_secrets.py`); el servidor no
arranca sin una llave válida; las claves antiguas se cifran al arrancar.
**Verificado:** la base de datos solo contiene `enc:v1:…`; un valor cifrado con
otra llave se trata como "sin clave" en vez de fallar.

### 13. Medio — La clave de Gemini viajaba en la URL y podía aparecer en errores
**Antes:** se enviaba como `?key=…`; las URL quedan en registros de proxies y
servidores, y el mensaje de error de conexión que veía el docente incluía la URL
completa. **Parche:** encabezado `x-goog-api-key`. **Verificado:** las llamadas
simuladas confirman que la URL ya no contiene la clave.

### Comprobación de claves al guardar
Las claves de Gemini se validan con Google antes de guardarlas (sin gastar cuota
de generación). Solo se rechaza una clave si Google responde con su formato de
error; un 403 de un proxy o firewall no cuenta como clave inválida (se detectó en
una prueba real, donde la red bloqueaba a Google). El guardado de claves tiene
límite de intentos para que no sirva como "probador" masivo de claves ajenas.
18 pruebas cubren cifrado, validación, encabezado, cuota agotada y bloqueo de red.

## Cuarta revisión (Supabase, adjuntos y perfil)

Todas las pruebas se ejecutan ahora contra **PostgreSQL real** (el motor de
Supabase) y contra SQLite: 50 comprobaciones en cada uno. Esto destapó errores
que SQLite ocultaba porque no verifica las claves foráneas:

### 14. Medio — Borrar una conversación con archivos fallaba en PostgreSQL/MySQL
Los archivos subidos desde el chat quedaban vinculados a la conversación y la
base rechazaba el borrado (error 500). **Parche:** los archivos se desvinculan y
siguen en la galería; en bases nuevas la clave foránea usa `ON DELETE SET NULL`.

### 15. Medio (privacidad) — Eliminar una cuenta dejaba sus archivos guardados
El administrador eliminaba los registros pero los archivos seguían en el disco o
el bucket, aunque la política de privacidad promete borrar todos los datos.
**Parche:** se borran también del almacenamiento. **Verificado** con una prueba
que cuenta los archivos antes y después.

### 16. Bajo — Migración de SQLite con filas huérfanas
Las bases SQLite antiguas pueden contener registros que apuntan a filas ya
borradas; PostgreSQL los rechazaría. El script de migración los omite (o
desvincula si la referencia es opcional) e informa cuántos, en una sola
transacción: si algo falla, no copia nada a medias.

### Controles de lo nuevo
- Adjuntos: solo se pueden adjuntar archivos propios (404 si no); tope de tamaño
  por mensaje; las rutas de almacenamiento se validan para no salir de la
  carpeta del docente.
- Supabase Storage: bucket privado; la clave secreta solo vive en el backend; las
  descargas pasan por el backend con verificación de sesión, `nosniff` y sin
  URL públicas. Compatible con las claves nuevas `sb_secret_…`.
- Perfil docente: campos con longitud máxima; se presenta a la IA como datos del
  docente, no como instrucciones que cambien su función.
- Dependencias: `pip-audit` y `npm audit` sin vulnerabilidades (se actualizó
  `source-map-js`, dependencia de compilación del frontend, por un aviso nuevo).

## Quinta revisión (despliegue en Railway)

### 17. Alto (en producción) — El límite de intentos habría bloqueado a todos los docentes a la vez
Detrás del proxy de Railway, sin configuración adicional, el backend ve **la misma IP
para todas las peticiones** (la del proxy). El límite de 10 intentos de inicio de sesión
cada 5 minutos se habría aplicado a todos los docentes juntos: bastaban unos pocos
errores de contraseña de cualquiera para bloquear el acceso de todos.
**Parche:** el `Dockerfile` arranca uvicorn con `--proxy-headers`, que toma la IP real
de cada visitante. **Verificado:** 12 intentos desde 12 IPs distintas no se bloquean;
12 desde la misma IP sí.

### Otras medidas del despliegue
- Una sola dirección para frontend y API: la cookie de sesión es "propia" del sitio,
  sin depender de cookies de terceros (que Safari y Firefox pueden bloquear).
- Encabezados de seguridad: `nosniff`, `X-Frame-Options: DENY` (nadie puede incrustar la
  app en otro sitio), `Referrer-Policy`, `Permissions-Policy` y HSTS con HTTPS.
- El servidor de archivos estáticos no permite salir de la carpeta del frontend
  (probado con `/../../etc/passwd`).
- La imagen corre con un usuario sin privilegios y nunca incluye `.env`, bases de datos
  locales ni entornos virtuales (`.dockerignore`).
- `/api/health` avisa si en producción no está configurado Supabase Storage (el disco de
  Railway es temporal y los archivos se perderían).

## Sexta revisión (restablecer contraseña)

- Enlace de un solo uso, válido 24 horas; generar otro anula los anteriores.
- La base de datos guarda solo el hash SHA-256 del código: una copia de la base no
  permite usar los enlaces.
- El código viaja después del `#` (no llega al servidor ni a sus registros); la página
  lo quita de la barra de direcciones al abrirse. **Verificado:** 0 apariciones en el
  registro del servidor tras el flujo completo.
- Solicitudes sin enumeración de cuentas (misma respuesta exista o no el correo),
  sin duplicados y con límite de intentos; validación y confirmación también limitadas.
- El correo se muestra oculto con un formato fijo (`p***@dominio`), que no revela su largo.
- 18 pruebas de backend (SQLite y PostgreSQL) y 15 comprobaciones en navegador real.

## Séptima revisión (aviso de Supabase: «RLS Disabled in Public»)

### 18. Alto — La API REST automática de Supabase exponía las tablas
Supabase publica una API REST (PostgREST) para las tablas del esquema `public`. Sin
seguridad a nivel de filas (RLS), cualquiera con la clave pública del proyecto
(«anon»/«publishable», que no se considera secreta) podía leer y modificar las tablas,
incluida `users` (correos, hashes de contraseñas, claves de API cifradas).
**Parche:** al arrancar, el backend activa RLS en todas las tablas de `public` **sin
políticas**: la API pública queda bloqueada y el backend, dueño de las tablas, no se ve
afectado. Es idempotente y cubre las tablas nuevas.
**Verificado** con un rol `anon` como el de Supabase: antes leía `users`; después no ve
filas y no puede insertar (`InsufficientPrivilege`). Suite completa: 50/50 en PostgreSQL.

## Octava revisión («Planificar con IA»)

- **La respuesta de la IA no se usa a ciegas:** aunque Gemini cumple el esquema JSON, el
  backend normaliza tipos, recorta textos, limita a 6 preguntas y 8 hallazgos, convierte
  campos de opción sin alternativas reales en texto y agrega la pregunta fija de salida.
  Un JSON inválido devuelve un error claro y no deja mensajes a medias.
- **Respuestas del formulario validadas** contra las preguntas guardadas: opciones
  inventadas, números fuera de rango o claves desconocidas se rechazan o se descartan.
- Solo se pueden analizar archivos propios y enviar formularios de conversaciones propias;
  un formulario no se puede enviar dos veces. Si la IA falla al generar, el formulario vuelve
  a quedar disponible sin duplicar mensajes. Límite de análisis por IP.
- **Error encontrado y corregido en el frontend:** si el docente cambiaba de conversación
  mientras la IA respondía, al terminar la vista volvía a la conversación anterior. Ahora solo
  se actualiza la conversación que sigue abierta (también en el envío normal de mensajes).
- La tabla nueva (`message_forms`) queda con RLS automáticamente en Supabase.
- 31 pruebas de backend (SQLite y PostgreSQL) y 13 comprobaciones en navegador real.

## Novena revisión (auditoría del sitio, noviembre de 2026)

Medida con Lighthouse 12 y axe-core 4.14 sobre una copia idéntica a producción, el
Security/Performance Advisor de Supabase en vivo, pip-audit y npm audit.

| Lighthouse | Antes | Después |
| --- | --- | --- |
| Celular: rendimiento / accesibilidad / buenas prácticas / SEO | 86 / 89 / 96 / 82 | 96 / 100 / 96* / 100 |
| Computadora | 100 / 96 / 96 / 82 | 100 / 100 / 96* / 100 |

\* El único aviso restante es el script de Google, que no carga en el entorno de pruebas sin internet.

### 19. Alto — Cambiar la contraseña no cerraba las sesiones abiertas
Una sesión robada seguía valiendo hasta 24 h tras restablecer la contraseña. **Parche:** el
token lleva su fecha de emisión (`iat`) y `users.password_changed_at` invalida las anteriores.
### 20. Medio — Sin Content-Security-Policy
**Parche:** CSP estricta (scripts solo del sitio y de Google Sign-In; sin incrustación).
### 21. Medio — 7 claves foráneas sin índice (Supabase Performance Advisor)
**Parche:** índices en los modelos y migración idempotente al arrancar (`upgrade_schema`).
### 22. Medio — Accesibilidad: contraste insuficiente (27 elementos) y estructura
**Parche:** variante de acento para texto (`--accent-ink`, ≥4,5:1 en las 8 materias),
región `<main>`, menús con nombre, nombres accesibles. axe: 0 problemas en 6 pantallas.
### 23. Bajo — Vite con avisos de seguridad (solo servidor de desarrollo)
**Parche:** Vite 8.3.5 en `package-lock.json`. npm audit: 0 vulnerabilidades.
### 24. Bajo — Rendimiento y SEO
Caché de un año para archivos con huella; portada sin carga diferida; meta descripción y
Open Graph; `favicon.svg` y `robots.txt` reales; 404 real para archivos inexistentes; la
comprobación de sesión al cargar ya no genera errores 401 en la consola.

## Lo que se revisó y no dio hallazgos

- Control de acceso a conversaciones, archivos y eventos de agenda: todos
  filtran correctamente por `user_id` del dueño (sin IDOR).
- Endpoints de administrador: protegidos con `get_current_admin`, con
  protección contra que un admin se quite permisos o se elimine a sí mismo.
- Sin SQL crudo ni `eval`/`exec`/`pickle` en el backend.
- Sin `dangerouslySetInnerHTML` ni `eval` en el frontend — el contenido de
  los mensajes se renderiza como texto plano de React, que escapa HTML
  automáticamente (sin XSS almacenado vía chat).
- Verificación del token de Google: se valida firma, emisor y audiencia
  contra los servidores de Google (no se decodifica sin más).
- Algoritmo JWT fijo en el servidor (`HS256`), sin posibilidad de ataque
  de confusión de algoritmo vía el token.

## No cubierto por esta auditoría

Esto fue una revisión manual dirigida por el código fuente, no un
despliegue real. Cosas que dependen de cómo lo despliegues y que no se
pueden verificar desde el código:
- Configuración real de HTTPS/TLS en producción.
- Backups y cifrado en reposo de la base de datos.
- Políticas de tu proveedor de hosting (firewall, DDoS, etc.).
- Si alguna vez agregas más funcionalidades, conviene repetir este tipo de
  revisión — esta cubre el código tal como está hoy.
