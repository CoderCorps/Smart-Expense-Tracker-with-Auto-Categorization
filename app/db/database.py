"""
SQLAlchemy engine + session setup. Uses SQLite by default so the whole team
can run this with zero setup (no database server to install). Every model
in app/models/ imports `Base` from here.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a DB session and always closes it after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
