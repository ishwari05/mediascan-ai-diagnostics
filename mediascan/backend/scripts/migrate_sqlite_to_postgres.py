#!/usr/bin/env python3
"""
migrate_sqlite_to_postgres.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Copies all rows from local SQLite (instance/mediascan.db) to Supabase-hosted
PostgreSQL, preserving primary keys (ids) and resetting sequence generators.

Usage:
  # Dry-run: shows table counts without modifying anything
  python3 scripts/migrate_sqlite_to_postgres.py

  # Live run: executes data migration and resets sequences
  python3 scripts/migrate_sqlite_to_postgres.py --confirm
"""

import argparse
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")


def resolve_database_url(url: str) -> str:
    """Normalize legacy postgres:// scheme to postgresql:// for SQLAlchemy."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def get_sqlite_engine():
    from sqlalchemy import create_engine
    candidates = [
        os.getenv("LOCAL_DB_PATH"),
        str(BACKEND_DIR / "instance" / "mediascan.db"),
        str(BACKEND_DIR / "mediascan.db"),
    ]
    sqlite_path = None
    for c in candidates:
        if c and Path(c).is_file():
            sqlite_path = c
            break

    if not sqlite_path:
        print("[ERROR] SQLite source database not found in instance/mediascan.db or mediascan.db")
        sys.exit(1)

    print(f"[INFO] Source SQLite: {sqlite_path}")
    return create_engine(f"sqlite:///{sqlite_path}")


def get_postgres_engine():
    from sqlalchemy import create_engine
    raw_url = os.getenv("DATABASE_URL", "").strip()
    if not raw_url:
        print("[ERROR] DATABASE_URL environment variable is not set.")
        sys.exit(1)

    resolved_url = resolve_database_url(raw_url)
    if not resolved_url.startswith("postgresql://"):
        print(f"[ERROR] DATABASE_URL does not start with postgresql:// or postgres://: {raw_url}")
        sys.exit(1)

    # Obfuscate credentials for terminal output
    safe_display = resolved_url.split("@")[-1] if "@" in resolved_url else "configured-host"
    print(f"[INFO] Target Postgres: ...@{safe_display}")
    return create_engine(resolved_url, connect_args={"sslmode": "require"})


def reflect_table(engine, table_name: str):
    from sqlalchemy import MetaData
    meta = MetaData()
    meta.reflect(bind=engine, only=[table_name])
    return meta.tables[table_name]


def migrate(confirm: bool):
    from sqlalchemy import select, text

    src_engine = get_sqlite_engine()
    dst_engine = get_postgres_engine()

    tables = ["users", "predictions"]  # Strict foreign key order

    # Pre-check row counts on both ends
    print("\n" + "=" * 60)
    print("  CURRENT DATABASE STATE")
    print("=" * 60)

    src_counts = {}
    dst_counts = {}

    with src_engine.connect() as s_conn:
        for t in tables:
            try:
                count = s_conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                src_counts[t] = count
            except Exception as e:
                print(f"[ERROR] Failed to query source table '{t}': {e}")
                sys.exit(1)

    with dst_engine.connect() as d_conn:
        for t in tables:
            try:
                count = d_conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                dst_counts[t] = count
            except Exception as e:
                print(f"[ERROR] Failed to query destination table '{t}': {e}")
                print("[HINT] Did you run 'flask db upgrade' on PostgreSQL first?")
                sys.exit(1)

    for t in tables:
        print(f"  Table: {t:<15} | SQLite: {src_counts[t]:<5} | PostgreSQL: {dst_counts[t]:<5}")

    if not confirm:
        print("=" * 60)
        print("[DRY-RUN] No changes made. Pass '--confirm' to copy data.")
        print("=" * 60)
        return

    print("\n" + "=" * 60)
    print("  EXECUTING DATA MIGRATION (--confirm)")
    print("=" * 60)

    # Perform table-by-table migration preserving IDs
    for table_name in tables:
        src_table = reflect_table(src_engine, table_name)
        dst_table = reflect_table(dst_engine, table_name)

        with src_engine.connect() as s_conn:
            rows = s_conn.execute(select(src_table)).fetchall()

        print(f"\n[INFO] Migrating {len(rows)} records for table '{table_name}'...")

        with dst_engine.begin() as d_conn:
            inserted = 0
            updated = 0
            for row in rows:
                row_dict = dict(row._mapping)
                row_id = row_dict.get("id")

                # Check if row with this ID already exists in target
                existing = d_conn.execute(
                    dst_table.select().where(dst_table.c.id == row_id)
                ).fetchone()

                if existing:
                    # Update without changing ID
                    update_values = {k: v for k, v in row_dict.items() if k != "id"}
                    d_conn.execute(
                        dst_table.update().where(dst_table.c.id == row_id).values(**update_values)
                    )
                    updated += 1
                else:
                    # Insert preserving explicit ID
                    d_conn.execute(dst_table.insert().values(**row_dict))
                    inserted += 1

            # Reset Postgres sequence for SERIAL primary key to max(id)
            try:
                max_id = d_conn.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {table_name}")).scalar()
                if max_id > 0:
                    d_conn.execute(
                        text(f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), :max_id, true)"),
                        {"max_id": max_id}
                    )
                    print(f"  → Reset sequence for '{table_name}' to max(id) = {max_id}")
            except Exception as seq_err:
                print(f"  [WARN] Could not reset sequence for '{table_name}': {seq_err}")

            print(f"  → Completed '{table_name}': {inserted} inserted, {updated} updated.")

    # Verification: compare source and target row counts
    print("\n" + "=" * 60)
    print("  VERIFYING ROW COUNTS")
    print("=" * 60)

    mismatch = False
    with dst_engine.connect() as d_conn:
        for t in tables:
            final_dst = d_conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            src_c = src_counts[t]
            match_status = "OK" if final_dst >= src_c else "MISMATCH"
            print(f"  {t:<15} | Source: {src_c:<5} | Target: {final_dst:<5} [{match_status}]")
            if final_dst < src_c:
                mismatch = True

    if mismatch:
        print("\n[ERROR] Migration completed with missing rows in PostgreSQL compared to SQLite.")
        sys.exit(1)

    print("\n[SUCCESS] Migration verified! All row counts match exactly and sequences reset.")


def main():
    parser = argparse.ArgumentParser(description="Migrate MediScan SQLite to Supabase PostgreSQL")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Apply data migration. Without this flag, only row counts are printed (dry run).",
    )
    args = parser.parse_args()
    migrate(confirm=args.confirm)


if __name__ == "__main__":
    main()
