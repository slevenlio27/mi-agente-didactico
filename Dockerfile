# Imagen única: el backend (FastAPI) sirve también el frontend compilado (React).
# Railway la construye automáticamente al encontrar este archivo.

# ── 1) Compilar el frontend ─────────────────────────────────────────────
FROM node:24-alpine AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Sin VITE_API_URL: en producción el frontend llama a la API en su misma dirección (/api)
RUN npm run build

# ── 2) Backend ──────────────────────────────────────────────────────────
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt
COPY backend/ backend/
COPY --from=frontend /build/frontend/dist frontend/dist

# No correr como root
RUN useradd --create-home --uid 10001 app && chown -R app /app
USER app
WORKDIR /app/backend

# Railway inyecta PORT. --proxy-headers hace que la app vea la IP real de cada
# docente (detrás del proxy de Railway); sin esto, el límite de intentos de login
# trataría a todos los docentes como una sola IP y los bloquearía a la vez.
# Un solo proceso: el límite de intentos vive en memoria.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
