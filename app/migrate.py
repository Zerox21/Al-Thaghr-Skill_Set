from __future__ import annotations
from sqlalchemy import text
from flask import current_app
from . import db

def _is_sqlite() -> bool:
    return db.engine.url.get_backend_name() == "sqlite"

def _has_column_sqlite(table: str, column: str) -> bool:
    rows = db.session.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == column for r in rows)

def _has_column_pg(table: str, column: str) -> bool:
    q = text("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = :table AND column_name = :col
        LIMIT 1
    """)
    r = db.session.execute(q, {"table": table, "col": column}).fetchone()
    return r is not None

def ensure_schema():
    backend = db.engine.url.get_backend_name()
    current_app.logger.info("Schema check on %s", backend)

    if _is_sqlite():
        if not _has_column_sqlite("skill", "pass_pct"):
            db.session.execute(text("ALTER TABLE skill ADD COLUMN pass_pct INTEGER"))
        if not _has_column_sqlite("attempt", "passed"):
            db.session.execute(text("ALTER TABLE attempt ADD COLUMN passed BOOLEAN"))
        db.session.commit()
        return

    if backend in ("postgresql","postgres"):
        if not _has_column_pg("skill", "pass_pct"):
            db.session.execute(text("ALTER TABLE skill ADD COLUMN pass_pct INTEGER"))
        if not _has_column_pg("attempt", "passed"):
            db.session.execute(text("ALTER TABLE attempt ADD COLUMN passed BOOLEAN"))
        db.session.commit()
