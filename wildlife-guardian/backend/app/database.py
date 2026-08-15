"""
Database engine and session configuration.

Defaults to a local SQLite file so the platform runs out of the box for
evaluation and small-conservancy deployments. Set DATABASE_URL to point at
PostgreSQL (recommended for production, e.g. multi-ranger concurrent writes).
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./wildlife_guardian.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
