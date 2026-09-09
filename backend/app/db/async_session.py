# app/db/async_session.py
"""
Async database engine/session configuration.

The rest of the app talks to Postgres synchronously (see app/db/session.py).
This module exists solely so isolated, IO-bound background workflows (the
ontology sync service) can use SQLAlchemy's async API without changing the
request/response path used everywhere else. It points at the same database
via the same psycopg3 driver, which supports both sync and async engines.

No business logic should be placed here.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

async_engine = create_async_engine(settings.POSTGRES_DSN, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)
