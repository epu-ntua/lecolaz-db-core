# app/db/session.py
"""
Database session and engine configuration.

Defines the SQLAlchemy engine and Session factory used by
storage adapters to interact with the database.

No business logic should be placed here.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(settings.POSTGRES_DSN, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
