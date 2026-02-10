# app/db/base.py
"""
Declarative base for all SQLAlchemy ORM models.

This file defines the single Base class that:
- all ORM models must inherit from
- Alembic uses via Base.metadata to discover the database schema

This file should remain minimal and stable.
"""

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
