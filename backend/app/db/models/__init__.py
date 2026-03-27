"""
Model registry for SQLAlchemy ORM models.

Importing this module ensures that all ORM models are loaded and
registered on Base.metadata.

Alembic imports this file to discover the full database schema.
No logic should live here.
"""

from .dataset import Dataset  # noqa: F401
from .bim_dataset import BimDataset  # noqa: F401
from .simulation_dataset import SimulationDataset  # noqa: F401
from .simulation_timeseries import SimulationTimeseries  # noqa: F401
from .simulation_variable import SimulationVariable  # noqa: F401
