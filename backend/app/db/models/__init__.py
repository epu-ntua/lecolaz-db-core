"""
Model registry for SQLAlchemy ORM models.

Importing this module ensures that all ORM models are loaded and
registered on Base.metadata.

Alembic imports this file to discover the full database schema.
No logic should live here.
"""

from .file_metadata import FileMetadata  # noqa: F401
from .bim_metadata import BimModel  # noqa: F401
