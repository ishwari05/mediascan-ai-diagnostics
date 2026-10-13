#!/usr/bin/env python3
"""
migrate_sqlite_to_postgres.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Copy all data from the local SQLite database to a Supabase-hosted
PostgreSQL database.

Usage
-----
    # Dry-run (default) — shows counts only, no writes
    python scripts/migrate_sqlite_to_postgres.py

    # Live run — actually inserts/upserts data
    python scripts/migrate_sqlite_to_postgres.py --confirm

Requirements
------------
  DATABASE_URL must be set to the Supabase Postgres connection string.
  The script reads LOCAL_DB_PATH (defaults to instance/mediascan.db).

Safety guarantees
-----------------
  * Without --confirm the script exits after printing row counts.
  * Users are upserted (email is the conflict key); existing rows keep
    their passwords and roles.
  * Predictions are inserted only if the (user_id, session_id) pair is
    absent — no duplicate scans.
  * The script never touches the SQLite file.
"""

import argparse
import os
import sys
from pathlib import Path

# ── allow running from the repo root or from the scripts/ dir ──────────────── #
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")


def _resolve_url(url: str) -> str:
    """Fix legacy postgres:// → postgresql:// scheme."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def get_sqlite_engine():
    from sqlalchemy import create_engine
    local_db = os.getenv("LOCAL_DB_PATH", str(BACKEND_DIR / "instance" / "mediascan.db"))
    if not Path(local_db).exists():
        print(f"[ERROR] SQLite database not found: {local_db}")
        sys.exit(1)
    print(f"[INFO]  SQLite source : {local_db}")
    return create_engine(f"sqlite:///{local_db}")


def get_postgres_engine():
    from sqlalchemy import create_engine
    raw = os.getenv("DATABASE_URL", "")
    if not raw:
        print("[ERROR] DATABASE_URL is not set.")
        sys.exit(1)
    url = _resolve_url(raw)
    if not url.startswith("postgresql://"):
        print(f"[ERROR] DATABASE_URL does not look like a PostgreSQL URL: {raw}")
        sys.exit(1)
    print(f"[INFO]  Postgres target: {url[:40]}…")
    return create_engine(url, connect_args={"sslmode": "require"})


def reflect_table(engine, table_name):
    from sqlalchemy import MetaData, Table
    meta = MetaData()
    meta.reflect(bind=engine, only=[table_name])
    return meta.tables[table_name]


def migrate(dry_run: bool):
    from sqlalchemy import select, text

    src = get_sqlite_engine()
    dst = get_postgres_engine()

    # ── 1. Users ──────────────────────────────────────────────────────────── #
    src_users = reflect_table(src, "users")
    dst_users = reflect_table(dst, "users")

    with src.connect() as s_conn:
        rows = s_conn.execute(select(src_users)).fetchall()

    print(f"\n[INFO]  Users to migrate  : {len(rows)}")
    if dry_run:
        print("[DRY-RUN] Skipping write.  Pass --confirm to execute.")
    else:
        with dst.begin() as d_conn:
            inserted = updated = 0
            for row in rows:
                row_dict = dict(row._mapping)
                # Check for existing user
                existing = d_conn.execute(
                    dst_users.select().where(dst_users.c.email == row_dict["email"])
                ).fetchone()
                if existing:
                    # Update mutable fields; keep password & role intact
                    d_conn.execute(
                        dst_users.update()
                        .where(dst_users.c.email == row_dict["email"])
                        .values(
                            name=row_dict.get("name"),
                            age=row_dict.get("age"),
                            gender=row_dict.get("gender"),
                            phone=row_dict.get("phone"),
                            last_login=row_dict.get("last_login"),
                            is_active=row_dict.get("is_active", True),
                        )
                    )
                    updated += 1
                else:
                    # Strip id so Postgres SERIAL assigns a fresh one
                    row_dict.pop("id", None)
                    d_conn.execute(dst_users.insert().values(**row_dict))
                    inserted += 1
        print(f"[OK]    Users  — inserted: {inserted}, updated: {updated}")

    # Build email→new_id map for remapping foreign keys
    with dst.connect() as d_conn:
        email_to_id = {
            r.email: r.id
            for r in d_conn.execute(dst_users.select()).fetchall()
        }

    # ── 2. Predictions ────────────────────────────────────────────────────── #
    src_preds = reflect_table(src, "predictions")
    dst_preds = reflect_table(dst, "predictions")

    with src.connect() as s_conn:
        pred_rows = s_conn.execute(select(src_preds)).fetchall()

    print(f"[INFO]  Predictions to migrate: {len(pred_rows)}")
    if dry_run:
        print("[DRY-RUN] Skipping write.  Pass --confirm to execute.")
        return

    with dst.begin() as d_conn:
        inserted = skipped = 0
        for row in pred_rows:
            row_dict = dict(row._mapping)

            # Remap user_id to the new Postgres id
            src_user_email = None
            with src.connect() as s_conn2:
                u = s_conn2.execute(
                    src_users.select().where(src_users.c.id == row_dict["user_id"])
                ).fetchone()
                if u:
                    src_user_email = u.email

            new_uid = email_to_id.get(src_user_email) if src_user_email else None
            if not new_uid:
                print(f"[WARN]  Skipping prediction id={row_dict['id']}: user not found in Postgres")
                skipped += 1
                continue

            row_dict["user_id"] = new_uid
            row_dict.pop("id", None)  # let Postgres assign PK

            # Skip if already present (idempotency)
            existing = d_conn.execute(
                dst_preds.select().where(
                    (dst_preds.c.user_id == new_uid)
                    & (dst_preds.c.session_id == row_dict["session_id"])
                )
            ).fetchone()

            if existing:
                skipped += 1
                continue

            d_conn.execute(dst_preds.insert().values(**row_dict))
            inserted += 1

    print(f"[OK]    Predictions — inserted: {inserted}, skipped/duplicate: {skipped}")
    print("\n[DONE] Migration complete.")


def main():
    parser = argparse.ArgumentParser(description="Migrate MediScan SQLite → Supabase Postgres")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually write data (omit for a dry-run that only prints counts)",
    )
    args = parser.parse_args()

    dry_run = not args.confirm
    if dry_run:
        print("=" * 60)
        print("  DRY-RUN mode — no data will be written")
        print("  Re-run with --confirm to execute the migration")
        print("=" * 60)

    migrate(dry_run=dry_run)


if __name__ == "__main__":
    main()
