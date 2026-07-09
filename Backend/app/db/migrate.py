"""
Simple file-based SQL migration runner (PostgreSQL only).

Reads `.sql` files from `app/db/migrations/` in sorted order and applies
any that haven't been recorded in the `_migrations` tracking table.

This avoids the Alembic dependency while still giving us safe, repeatable
schema migrations.
"""

import logging
from pathlib import Path

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def _ensure_tracking_table() -> None:
    """Create the `_migrations` tracking table if it doesn't exist."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS _migrations (
                    filename VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )


def _applied_migrations() -> set[str]:
    """Return the set of migration filenames already applied."""
    with engine.begin() as conn:
        result = conn.execute(text("SELECT filename FROM _migrations"))
        return {row[0] for row in result}


def _mark_applied(filename: str) -> None:
    """Record a migration as applied."""
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO _migrations (filename) VALUES (:f)"),
            {"f": filename},
        )


def run_migrations() -> None:
    """Discover and apply any pending SQL migrations."""
    _ensure_tracking_table()
    applied = _applied_migrations()

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        logger.info("No migration files found in %s", MIGRATIONS_DIR)
        return

    for path in migration_files:
        if path.name in applied:
            logger.debug("Migration %s already applied, skipping", path.name)
            continue

        sql = path.read_text(encoding="utf-8").strip()
        if not sql:
            logger.warning("Migration %s is empty, skipping", path.name)
            continue

        logger.info("Applying migration %s …", path.name)
        with engine.begin() as conn:
            conn.execute(text(sql))

        _mark_applied(path.name)
        logger.info("Migration %s applied successfully.", path.name)
