# Cambiar de SQLite a MySQL

Por defecto el proyecto usa SQLite (`backend/app.db`, un solo archivo, cero
configuración). Para producción con varios docentes a la vez, MySQL es más
robusto. Ninguna contraseña de esta guía es un valor de ejemplo: todas se
generan al azar.

## Opción A — MySQL con Docker (recomendado para empezar)

Desde la carpeta `backend`, con el entorno virtual activado:

```bash
python scripts/generate_secrets.py --mysql
```

Esto hace tres cosas:
1. Genera contraseñas aleatorias de MySQL en un archivo `.env` en la **raíz**
   del proyecto (ese archivo lo lee Docker y está en `.gitignore`).
2. Actualiza `DATABASE_URL` en `backend/.env` con esa misma contraseña.
3. Si falta, genera también el `SECRET_KEY`.

Luego, desde la raíz del proyecto:

```bash
docker compose -f docker-compose.mysql.yml up -d
```

MySQL queda escuchando solo en `127.0.0.1:3306` (no es accesible desde otras
máquinas de la red). Si falta alguna contraseña, Docker se detiene con un
error en vez de arrancar con un valor por defecto.

## Opción B — Un MySQL que ya tienes (o en la nube)

Genera una contraseña aleatoria:

```bash
python -c "import secrets; print(secrets.token_hex(24))"
```

Conéctate a tu MySQL y crea la base y el usuario, pegando esa contraseña
donde dice `<CONTRASEÑA_GENERADA>`:

```sql
CREATE DATABASE agente_didactico CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'agente_user'@'localhost' IDENTIFIED BY '<CONTRASEÑA_GENERADA>';
GRANT ALL PRIVILEGES ON agente_didactico.* TO 'agente_user'@'localhost';
FLUSH PRIVILEGES;
```

Usa `'localhost'` si el backend corre en la misma máquina que MySQL; si no,
cambia `'localhost'` por la IP del servidor del backend en vez de `'%'`
(que permitiría conectarse desde cualquier lugar).

En `backend/.env`:

```
DATABASE_URL=mysql+pymysql://agente_user:<CONTRASEÑA_GENERADA>@localhost:3306/agente_didactico
```

Si tu proveedor en la nube te da la cadena de conexión, úsala tal cual
cambiando el prefijo a `mysql+pymysql://`.

## Arrancar

```bash
cd backend
# con el venv activado:
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

Al arrancar, el backend crea todas las tablas automáticamente. El driver
`pymysql` es puro Python: no hay nada que compilar.

## Notas

- Todas las columnas de texto indexadas ya tienen un largo máximo definido
  (lo exige MySQL); el código funciona igual con SQLite y MySQL.
- Migrar **datos** existentes de SQLite a MySQL (no solo el esquema) no está
  cubierto aquí.
- Nunca subas a git el `.env` de la raíz ni `backend/.env`: contienen las
  contraseñas. Ambos están en `.gitignore`.
