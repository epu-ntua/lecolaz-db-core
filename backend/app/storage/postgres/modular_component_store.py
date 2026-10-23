from typing import Any, Dict

from sqlalchemy.dialects.postgresql import insert

from app.db.models.modular_component import ModularComponent
from app.db.session import SessionLocal


class ModularComponentStore:
    """Modular component persistence; returns plain records, no ORM objects."""

    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def upsert(self, record: Dict[str, Any]) -> None:
        """Insert a component, or overwrite every given field if its id exists."""
        statement = insert(ModularComponent).values(record)
        statement = statement.on_conflict_do_update(
            index_elements=[ModularComponent.id],
            set_={column: statement.excluded[column] for column in record if column != "id"},
        )
        with self._session_factory() as session:
            session.execute(statement)
            session.commit()
