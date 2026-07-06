# Repo path: Backend/app/db/session.py  (UPDATED)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

settings = get_settings()

is_sqlite = settings.DATABASE_URL.startswith("sqlite")
is_postgres = settings.DATABASE_URL.startswith("postgresql")

if is_sqlite:
    # SQLite needs this for FastAPI's threaded request handling.
    connect_args = {"check_same_thread": False}
elif is_postgres:
    # Supabase requires SSL on its connection endpoints.
    connect_args = {"sslmode": "require"}
else:
    connect_args = {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    # pool_pre_ping avoids "server closed the connection unexpectedly" errors
    # against Supabase's connection pooler, which can recycle idle connections.
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)