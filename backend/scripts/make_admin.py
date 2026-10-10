"""
Promueve una cuenta existente a administrador, a mano, sin pasar por ADMIN_EMAILS.

Uso (desde la carpeta backend, con el entorno virtual activado):
    python scripts/make_admin.py correo@ejemplo.com
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app import models


def main():
    if len(sys.argv) != 2:
        print("Uso: python scripts/make_admin.py correo@ejemplo.com")
        sys.exit(1)

    email = sys.argv[1].strip().lower()
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            print(f"No existe ninguna cuenta con el correo {email}. Regístrate primero desde el sitio.")
            sys.exit(1)
        if user.is_admin:
            print(f"{email} ya es administrador.")
            return
        user.is_admin = True
        db.commit()
        print(f"Listo: {email} ahora es administrador.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
