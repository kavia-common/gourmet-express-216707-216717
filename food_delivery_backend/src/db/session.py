from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.config import get_database_url

# Create engine once at import time. In this template, that's acceptable and simple.
DATABASE_URL = get_database_url()

# NOTE: psycopg2 driver is used via "psycopg2-binary"
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# PUBLIC_INTERFACE
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy Session and ensures it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
