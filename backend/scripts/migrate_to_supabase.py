"""
Copia todos los datos de la base actual (SQLite) a Supabase (PostgreSQL) y,
opcionalmente, los archivos del disco local a Supabase Storage.

Uso, desde la carpeta backend con el entorno virtual activado:

    python scripts/migrate_to_supabase.py \\
        --source "sqlite:///./app.db" \\
        --target "postgresql://postgres.xxxx:CONTRASEÑA@aws-0-xx.pooler.supabase.com:5432/postgres" \\
        --copy-files

- No modifica la base de origen.
- Se niega a continuar si la base de destino ya tiene usuarios (para no duplicar).
- --copy-files necesita SUPABASE_URL y SUPABASE_SECRET_KEY en backend/.env.
- Las claves de API de los docentes se copian tal cual (cifradas): sigue usando el
  mismo API_KEYS_ENCRYPTION_KEY o no se podrán leer.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, inspect, select, text  # noqa: E402

from app import models  # noqa: E402,F401  (registra todas las tablas)
from app.database import Base, normalize_database_url  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Migrar datos de SQLite a Supabase")
    ap.add_argument("--source", required=True, help='Base de origen, p. ej. "sqlite:///./app.db"')
    ap.add_argument("--target", required=True, help="Cadena de conexión de Supabase (Session pooler)")
    ap.add_argument("--copy-files", action="store_true", help="Subir también los archivos a Supabase Storage")
    args = ap.parse_args()

    src = create_engine(normalize_database_url(args.source))
    dst = create_engine(normalize_database_url(args.target), connect_args={"prepare_threshold": None})

    Base.metadata.create_all(dst)
    with dst.connect() as c:
        if c.execute(text("SELECT count(*) FROM users")).scalar():
            sys.exit("La base de destino ya tiene usuarios. Para no duplicar datos, la migración se detiene.")

    src_tables = set(inspect(src).get_table_names())
    total = skipped = unlinked = 0
    copied = {}  # tabla -> ids copiados, para detectar filas huérfanas
    with src.connect() as s, dst.begin() as d:
        for table in Base.metadata.sorted_tables:  # orden que respeta las claves foráneas
            if table.name not in src_tables:
                continue
            src_cols = {c["name"] for c in inspect(src).get_columns(table.name)}
            cols = [c for c in table.columns if c.name in src_cols]
            rows = [dict(r._mapping) for r in s.execute(select(*[table.c[c.name] for c in cols]))]
            # SQLite no verifica las claves foráneas, así que puede tener filas que apuntan a
            # registros ya borrados. PostgreSQL las rechazaría: se omiten (o se desvinculan
            # si la referencia es opcional), en vez de abortar toda la migración.
            clean = []
            for row in rows:
                keep = True
                for col in cols:
                    for fk in col.foreign_keys:
                        parent = fk.column.table.name
                        value = row.get(col.name)
                        if value is None or parent not in copied or value in copied[parent]:
                            continue
                        if col.nullable and not col.primary_key:
                            row[col.name] = None
                            unlinked += 1
                        else:
                            keep = False
                if keep:
                    clean.append(row)
            skipped += len(rows) - len(clean)
            if clean:
                d.execute(table.insert(), clean)
            if "id" in table.c:
                copied[table.name] = {r["id"] for r in clean}
            print(f"  {table.name}: {len(clean)} filas" + (f" ({len(rows) - len(clean)} huérfanas omitidas)" if len(rows) != len(clean) else ""))
            total += len(clean)
        # Que los próximos registros no choquen con los ids copiados
        for table in Base.metadata.sorted_tables:
            if "id" in table.c and table.c["id"].primary_key and table.c["id"].autoincrement is not False:
                d.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {table.name}), 1), "
                    f"(SELECT MAX(id) FROM {table.name}) IS NOT NULL)"
                ))
    print(f"Datos copiados: {total} filas en total."
          + (f" Se omitieron {skipped} filas huérfanas" if skipped else "")
          + (f" y se desvincularon {unlinked} referencias a registros borrados." if unlinked else ""))

    if args.copy_files:
        from app.config import settings
        from app.storage import LocalStorage, SupabaseStorage

        if not (settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY):
            sys.exit("Para --copy-files configura SUPABASE_URL y SUPABASE_SECRET_KEY en backend/.env.")
        local = LocalStorage()
        remote = SupabaseStorage(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY, settings.SUPABASE_BUCKET)
        ok = missing = 0
        with src.connect() as s:
            for f in s.execute(text("SELECT user_id, stored_name, content_type FROM uploaded_files")):
                key = f"{f.user_id}/{f.stored_name}"
                data = local.read(key)
                if data is None:
                    missing += 1
                    continue
                remote.save(key, data, f.content_type)
                ok += 1
        print(f"Archivos subidos a Supabase Storage: {ok}" + (f" (no encontrados en disco: {missing})" if missing else ""))

    print("Listo. Ahora pon esa misma cadena en DATABASE_URL de backend/.env y reinicia el backend.")


if __name__ == "__main__":
    main()
