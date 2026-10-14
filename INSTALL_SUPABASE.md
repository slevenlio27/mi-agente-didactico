# Usar Supabase (base de datos y archivos)

Con Supabase, la base de datos pasa a PostgreSQL en la nube y los archivos de los
docentes, a Supabase Storage. El inicio de sesión sigue siendo el de la app
(correo, contraseña y Google), sin cambios.

Todo es opcional: sin configurar nada, la app sigue funcionando en local con
SQLite y archivos en disco.

## 1. Crear el proyecto

1. Entra a https://supabase.com, crea una cuenta y un proyecto nuevo.
2. Anota la **contraseña de la base de datos** que eliges al crearlo (la
   necesitarás para la cadena de conexión). Si la olvidas, se puede cambiar en
   la configuración de la base de datos del proyecto.

## 2. Conectar la base de datos

1. En el panel del proyecto, pulsa **Connect** y copia la cadena del
   **Session pooler** (puerto 5432). Tiene esta forma:
   `postgresql://postgres.xxxx:[YOUR-PASSWORD]@aws-0-xx.pooler.supabase.com:5432/postgres`
2. Cambia `[YOUR-PASSWORD]` por la contraseña de la base de datos.
3. En `backend/.env`:
   ```
   DATABASE_URL=postgresql://postgres.xxxx:TU_CONTRASEÑA@aws-0-xx.pooler.supabase.com:5432/postgres
   ```
   Puedes pegarla tal cual con `postgresql://`; el backend la adapta a su driver.

Se recomienda el **Session pooler** porque funciona en redes solo IPv4 (como la
mayoría de las redes domésticas y universitarias). El backend también funciona
con el pooler de transacciones (puerto 6543): ya desactiva las "prepared
statements", que ese modo no admite.

Al arrancar el backend, se crean todas las tablas solas.

## 3. Archivos en Supabase Storage

1. En el panel: **Storage > New bucket**. Nombre: `uploads`. Déjalo **privado**
   (no actives "Public bucket").
2. En **Settings > API Keys**, copia una **secret key** (empieza por
   `sb_secret_`). Los proyectos creados desde noviembre de 2025 ya no tienen la
   antigua clave `service_role`, y Supabase planea eliminarla para todos.
3. En `backend/.env`:
   ```
   SUPABASE_URL=https://xxxx.supabase.co
   SUPABASE_SECRET_KEY=sb_secret_...
   SUPABASE_BUCKET=uploads
   ```

**La clave secreta da acceso total al proyecto.** Va solo en
`backend/.env`, nunca en `frontend/.env` ni en GitHub. Los docentes nunca
reciben un enlace directo al bucket: el backend descarga cada archivo y se lo
entrega solo a su dueño, después de verificar su sesión.

Para comprobar que todo quedó bien, abre `http://localhost:8000/health`. Debe
responder `"status": "ok"`, `"storage": "supabase"` y `"storage_detail":
"bucket 'uploads' accesible"`. Si dice `"degraded"`, el detalle explica qué
falta (clave rechazada o bucket inexistente).

## 4. Pasar tus datos actuales a Supabase

Si ya tienes usuarios y conversaciones en SQLite, cópialos (desde `backend`,
con el venv activado, y **antes** de cambiar `DATABASE_URL`):

```bash
python scripts/migrate_to_supabase.py \
  --source "sqlite:///./app.db" \
  --target "LA_CADENA_DEL_SESSION_POOLER" \
  --copy-files
```

- No modifica la base de origen y se detiene si el destino ya tiene usuarios.
- Omite las filas "huérfanas" que SQLite deja al borrar conversaciones e
  informa cuántas fueron.
- `--copy-files` sube los archivos del disco al bucket (necesita
  `SUPABASE_URL` y `SUPABASE_SECRET_KEY` en `backend/.env`).
- Las claves de API de los docentes se copian cifradas: **conserva el mismo
  `API_KEYS_ENCRYPTION_KEY`**, o no se podrán leer.

Después, pon la cadena en `DATABASE_URL` y reinicia el backend.

## 5. Evitar que el proyecto gratuito se pause

En el plan gratuito, Supabase pausa el proyecto tras 7 días sin actividad. El
repositorio incluye `.github/workflows/supabase-keepalive.yml`, que hace una
consulta mínima cada 3 días. Para activarlo:

1. En GitHub: tu repositorio > **Settings > Secrets and variables > Actions >
   New repository secret**.
2. Nombre: `SUPABASE_DB_URL`. Valor: la misma cadena de `DATABASE_URL`.
3. En la pestaña **Actions**, ejecútalo una vez a mano ("Run workflow") para
   comprobar que funciona.

GitHub desactiva las tareas programadas de los repositorios que pasan 60 días
sin cambios; si eso ocurre, la pestaña Actions muestra un aviso para
reactivarla.

## Límites del plan gratuito a tener en cuenta

500 MB de base de datos, 1 GB de archivos y sin copias de seguridad
automáticas. Si muchos docentes suben PDF, el gigabyte de archivos se llena
rápido: considera bajar `MAX_UPLOAD_MB` en `backend/.env` o pasar al plan de
pago. Haz exportaciones periódicas de la base de datos desde el panel.

## Seguridad: la API REST automática de Supabase

Supabase publica una API REST para las tablas del esquema `public`. Esta app no la usa
(el backend se conecta directo a la base de datos), así que el backend la **bloquea** al
arrancar: activa la seguridad a nivel de filas (RLS) en todas las tablas, sin políticas.
Por eso el **Security Advisor** de Supabase no debe mostrar avisos «RLS Disabled in
Public». Si aparecen en una tabla nueva, reinicia el backend (o vuelve a desplegar).
