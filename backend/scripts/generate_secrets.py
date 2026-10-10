"""
Genera secretos aleatorios reales para el proyecto. Nunca deja valores de ejemplo.

Uso (desde la carpeta backend):
    python scripts/generate_secrets.py            # crea/corrige SECRET_KEY en backend/.env
    python scripts/generate_secrets.py --mysql    # además, contraseñas de MySQL para Docker
    python scripts/generate_secrets.py --rotate   # fuerza un SECRET_KEY nuevo (cierra todas las sesiones)

Es seguro correrlo varias veces: si un secreto ya es válido, lo conserva.
Los secretos no se muestran en pantalla, solo se escriben en los archivos .env.
"""

import argparse
import base64
import os
import secrets
import shutil
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
BACKEND_ENV = BACKEND_DIR / ".env"
BACKEND_ENV_EXAMPLE = BACKEND_DIR / ".env.example"
ROOT_ENV = PROJECT_ROOT / ".env"  # lo lee docker compose automáticamente

KNOWN_PLACEHOLDERS = {
    "changeme-please-generate-a-random-secret",
    "change-this-to-a-long-random-string",
    "agente_pass",
    "change-this-root-password",
}
MIN_LENGTH = 32


def is_weak(value: str) -> bool:
    value = (value or "").strip()
    return (
        not value
        or value in KNOWN_PLACEHOLDERS
        or value.lower().startswith(("change", "your-", "tu-"))
        or len(value) < MIN_LENGTH
    )


def read_env(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def get_value(lines: list[str], key: str) -> str | None:
    for line in lines:
        if line.strip().startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return None


def set_value(lines: list[str], key: str, value: str) -> list[str]:
    out, found = [], False
    for line in lines:
        if line.strip().startswith(f"{key}=") and not found:
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}={value}")
    return out


def write_env(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if os.name == "posix":
        os.chmod(path, 0o600)  # solo el dueño puede leerlo


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mysql", action="store_true", help="genera también contraseñas de MySQL para Docker")
    parser.add_argument("--rotate", action="store_true", help="reemplaza SECRET_KEY aunque ya sea válido")
    args = parser.parse_args()

    if not BACKEND_ENV.exists():
        if not BACKEND_ENV_EXAMPLE.exists():
            sys.exit("No encontré backend/.env.example. Corre este script desde el proyecto completo.")
        shutil.copy(BACKEND_ENV_EXAMPLE, BACKEND_ENV)
        print("• Creé backend/.env a partir de .env.example")

    lines = read_env(BACKEND_ENV)

    current = get_value(lines, "SECRET_KEY")
    if args.rotate or is_weak(current):
        lines = set_value(lines, "SECRET_KEY", secrets.token_hex(32))
        reason = "rotado a pedido" if args.rotate and not is_weak(current) else "faltaba o era un valor de ejemplo"
        print(f"• SECRET_KEY generado ({reason}). Las sesiones abiertas se cerrarán.")
    else:
        print("• SECRET_KEY ya era válido; se conserva.")

    enc = get_value(lines, "API_KEYS_ENCRYPTION_KEY")
    valid_enc = False
    try:
        valid_enc = bool(enc) and len(base64.urlsafe_b64decode(enc.encode())) == 32
    except Exception:
        pass
    if not valid_enc:
        # No se rota automáticamente: cambiarla haría ilegibles las claves ya guardadas.
        lines = set_value(lines, "API_KEYS_ENCRYPTION_KEY", base64.urlsafe_b64encode(os.urandom(32)).decode())
        print("• API_KEYS_ENCRYPTION_KEY generada (cifra las claves de API de los docentes).")
    else:
        print("• API_KEYS_ENCRYPTION_KEY ya era válida; se conserva.")

    if args.mysql:
        root_lines = read_env(ROOT_ENV)
        user_pw = get_value(root_lines, "MYSQL_PASSWORD")
        if is_weak(user_pw):
            user_pw = secrets.token_hex(24)  # solo hex: no rompe la URL de conexión
            root_lines = set_value(root_lines, "MYSQL_PASSWORD", user_pw)
            print("• MYSQL_PASSWORD generado en .env (raíz del proyecto)")
        if is_weak(get_value(root_lines, "MYSQL_ROOT_PASSWORD")):
            root_lines = set_value(root_lines, "MYSQL_ROOT_PASSWORD", secrets.token_hex(24))
            print("• MYSQL_ROOT_PASSWORD generado en .env (raíz del proyecto)")
        write_env(ROOT_ENV, root_lines)

        url = f"mysql+pymysql://agente_user:{user_pw}@localhost:3306/agente_didactico"
        lines = [l for l in lines if not l.strip().startswith("# DATABASE_URL=mysql")]
        lines = set_value(lines, "DATABASE_URL", url)
        print("• DATABASE_URL de backend/.env apunta ahora al MySQL de Docker")

    write_env(BACKEND_ENV, lines)
    print("Listo. Los secretos quedaron en los archivos .env (no se muestran aquí).")


if __name__ == "__main__":
    main()
