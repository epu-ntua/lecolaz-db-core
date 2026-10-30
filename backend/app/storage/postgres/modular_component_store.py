import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
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

    def list_components(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = (
                select(ModularComponent)
                .order_by(ModularComponent.created_at.desc(), ModularComponent.id)
                .limit(limit)
                .offset(offset)
            )
            return [self._to_dict(obj) for obj in session.execute(stmt).scalars()]

    def get_by_id(self, component_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            obj = session.get(ModularComponent, component_id)
            return self._to_dict(obj) if obj else None

    def update_building(
        self,
        component_id: uuid.UUID,
        bim_dataset_id: Optional[uuid.UUID],
    ) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            obj = session.get(ModularComponent, component_id)
            if not obj:
                return None

            obj.bim_dataset_id = bim_dataset_id
            session.commit()
            session.refresh(obj)
            return self._to_dict(obj)

    @staticmethod
    def _to_dict(obj: ModularComponent) -> Dict[str, Any]:
        return {
            "id": str(obj.id),
            "name": obj.name,
            "component_class": obj.component_class,
            "bim_dataset_id": str(obj.bim_dataset_id) if obj.bim_dataset_id else None,
            "dpp": obj.dpp,
            "photo_object_key": obj.photo_object_key,
            "qr_object_key": obj.qr_object_key,
            "ifc_object_key": obj.ifc_object_key,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
        }
