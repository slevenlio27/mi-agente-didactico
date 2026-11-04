import os
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, engine
from .routers import admin, agenda, analytics, auth, chat, files, password_reset, profile, site

# Crea las tablas si no existen (SQLite/PostgreSQL vía SQLAlchemy)
Base.metadata.create_all(bind=engine)

# Columnas e índices nuevos en tablas que ya existían (idempotente)
from .database import upgrade_schema  # noqa: E402

upgrade_schema()

# Supabase: bloquea la API REST pública sobre nuestras tablas (activa RLS sin políticas)
from .database import lock_public_api_access  # noqa: E402

_locked = lock_public_api_access()
if _locked:
    print(f"Seguridad a nivel de filas (RLS) activada en {_locked} tablas.")

# Cifra las claves de API que versiones anteriores guardaron en texto plano.
from .database import SessionLocal  # noqa: E402
from .secret_box import encrypt_legacy_plaintext_keys  # noqa: E402

with SessionLocal() as _db:
    # Crea la configuración del sitio antes de recibir peticiones, para que varias
    # peticiones simultáneas a una base nueva no intenten crearla a la vez.
    from .site_settings import get_site_settings  # noqa: E402
    get_site_settings(_db)
    _n = encrypt_legacy_plaintext_keys(_db)
    if _n:
        print(f"Se cifraron {_n} claves de API guardadas en texto plano.")

# ¿Estamos en un servidor de producción? (Railway define estas variables)
IN_PRODUCTION = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_ENVIRONMENT_NAME"))

app = FastAPI(title="Mi Agente Didáctico API", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json")

# Comprime las respuestas antes de enviarlas (historiales largos, listas de archivos…)
app.add_middleware(GZipMiddleware, minimum_size=500)

# CORS solo hace falta en desarrollo, cuando el frontend (puerto 5173) y el backend
# (puerto 8000) son orígenes distintos. En producción todo sale de la misma dirección.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Política de seguridad de contenido: el navegador solo ejecuta scripts del propio sitio y del
# inicio de sesión de Google (orígenes que Google documenta para «Sign in with Google»).
CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self' https://accounts.google.com/gsi/client",
    "style-src 'self' 'unsafe-inline' https://accounts.google.com/gsi/style",
    "frame-src https://accounts.google.com/gsi/",
    "connect-src 'self' https://accounts.google.com/gsi/",
    "img-src 'self' data: blob: https://*.googleusercontent.com",
    "font-src 'self' data:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")  # nadie puede incrustar la app en otro sitio
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Content-Security-Policy", CSP)
    if settings.COOKIE_SECURE:  # solo con HTTPS
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return response


# ── API: todo bajo /api, para no chocar con las páginas del frontend (/admin, /panel…)
api = APIRouter(prefix="/api")
for r in (auth, password_reset, chat, files, agenda, analytics, admin, site, profile):
    api.include_router(r.router)


@api.get("/health")
def health():
    """Comprueba la base de datos y el almacenamiento. Railway lo usa para saber si la
    versión nueva está lista antes de enviarle tráfico."""
    from .database import ping_database
    from .storage import storage as _storage

    ping_database()
    ok, detail = _storage.check()
    if IN_PRODUCTION and _storage.name == "local":
        # En Railway el disco es temporal: se borra en cada despliegue.
        ok, detail = False, "almacenamiento en disco local en un servidor temporal: configura Supabase Storage o se perderán los archivos"
    return {"status": "ok" if ok else "degraded", "storage": _storage.name, "storage_detail": detail}


app.include_router(api)
app.add_api_route("/health", health, methods=["GET"], include_in_schema=False)  # alias, como antes


# ── Frontend compilado (npm run build): se sirve desde la misma dirección
DIST = Path(os.getenv("FRONTEND_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist")).resolve()

if (DIST / "index.html").is_file():
    if (DIST / "assets").is_dir():
        # Archivos con huella en el nombre (index-a1b2c3.js): se pueden guardar en caché mucho tiempo
        class ImmutableStatic(StaticFiles):
            async def get_response(self, path, scope):
                resp = await super().get_response(path, scope)
                if resp.status_code == 200:
                    resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
                return resp

        app.mount("/assets", ImmutableStatic(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Ruta de la API no encontrada.")
        candidate = (DIST / full_path).resolve()
        # Archivos reales de la raíz (favicon, robots.txt…), sin poder salir de la carpeta
        if full_path and candidate.is_file() and DIST in candidate.parents:
            return FileResponse(candidate)
        # Un archivo que no existe (/sitemap.xml, /favicon.ico…) es un 404 real, no la portada
        if "." in full_path.rsplit("/", 1)[-1]:
            raise HTTPException(status_code=404, detail="Archivo no encontrado.")
        # Cualquier otra ruta (/panel, /admin, /legal…) la resuelve React
        return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-cache"})
else:

    @app.get("/", include_in_schema=False)
    def root():
        return {"status": "ok", "service": "Mi Agente Didáctico API", "frontend": "no compilado (usa npm run dev en desarrollo)"}
