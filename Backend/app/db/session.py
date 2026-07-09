# Repo path: Backend/app/db/session.py  (UPDATED — PostgreSQL only)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Supabase requires SSL on its PostgreSQL connection endpoints.
connect_args = {"sslmode": "require"}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    # pool_pre_ping avoids "server closed the connection unexpectedly" errors
    # against Supabase's connection pooler, which can recycle idle connections.
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
