"""
Limitador de peticiones simple, en memoria, por IP.

Nota honesta: esto vive en la memoria de un solo proceso. Si despliegas con
varios workers/procesos detrás de un balanceador, cada uno cuenta por su
cuenta y el límite real efectivo sube (ej. 4 workers = 4x el límite). Para
un despliegue serio con varios workers o varias instancias, hay que mover
esto a un almacén compartido (Redis) — aquí se prioriza no sumar otra
dependencia de infraestructura para un proyecto de este tamaño.
"""

import time
from collections import defaultdict

from fastapi import HTTPException, Request

# path -> ip -> [timestamps de intentos recientes]
_attempts: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))


def rate_limit(key: str, max_attempts: int, window_seconds: int):
    """Devuelve una dependencia de FastAPI que limita a max_attempts
    peticiones cada window_seconds segundos, por IP, para esa 'key'."""

    def dependency(request: Request):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        bucket = _attempts[key][ip]

        # descarta intentos fuera de la ventana de tiempo
        cutoff = now - window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)

        if len(bucket) >= max_attempts:
            raise HTTPException(
                status_code=429,
                detail="Demasiados intentos. Espera un momento antes de volver a intentarlo.",
            )

        bucket.append(now)

    return dependency
