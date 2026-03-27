import uuid
from typing import Optional, List, Dict, Any

from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models.simulation_metadata import SimulationModel


class SimulationStore:
    """
    PostgreSQL-backed implementation of simulation metadata persistence.
    Mirrors FileStore boundary rules:
    - DB only (no FastAPI, no business workflows)
    - Returns dicts (no ORM leaks)
    """

    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def create_simulation_record(
        self,
        simulation_id: uuid.UUID,
        file_id: uuid.UUID,
        filename: str,
        format: str,
        schema: Optional[str] = None,
        status: str = "uploaded",
        extra: Optional[dict] = None,
    ) -> None:
        with self._session_factory() as session:
            obj = SimulationModel(
                id=simulation_id,
                file_id=file_id,
                filename=filename,
                format=format,
                schema=schema,
                status=status,
                extra=extra,
            )
            session.add(obj)
            session.commit()

    def list_simulation_models(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = (
                select(SimulationModel)
                .order_by(SimulationModel.created_at.desc())
                .limit(limit)
            )
            rows = session.execute(stmt).scalars().all()
            return [self._to_dict(r) for r in rows]

    def get_simulation_by_id(
        self,
        simulation_id: uuid.UUID,
    ) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = select(SimulationModel).where(SimulationModel.id == simulation_id)
            row = session.execute(stmt).scalars().first()
            return self._to_dict(row) if row else None

    def get_simulation_by_file_id(
        self,
        file_id: uuid.UUID,
    ) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = select(SimulationModel).where(SimulationModel.file_id == file_id)
            row = session.execute(stmt).scalars().first()
            return self._to_dict(row) if row else None

    def update_simulation_status(
        self,
        simulation_id: uuid.UUID,
        status: str,
        extra_patch: Optional[dict] = None,
    ) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = select(SimulationModel).where(SimulationModel.id == simulation_id)
            obj = session.execute(stmt).scalars().first()
            if not obj:
                return None

            obj.status = status
            if extra_patch:
                merged_extra = dict(obj.extra or {})
                merged_extra.update(extra_patch)
                obj.extra = merged_extra

            session.commit()
            session.refresh(obj)
            return self._to_dict(obj)

    @staticmethod
    def _to_dict(obj: SimulationModel) -> Dict[str, Any]:
        return {
            "id": str(obj.id),
            "file_id": str(obj.file_id),
            "filename": obj.filename,
            "format": obj.format,
            "schema": obj.schema,
            "status": obj.status,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "extra": obj.extra,
        }
