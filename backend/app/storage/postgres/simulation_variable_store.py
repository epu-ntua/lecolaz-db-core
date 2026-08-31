import uuid
from typing import Any, Dict, List

from sqlalchemy import delete, select

from app.db.models.simulation_variable import SimulationVariable
from app.db.session import SessionLocal


class SimulationVariableStore:
    _BATCH_SIZE = 1000

    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def replace_variables(
        self,
        simulation_dataset_id: uuid.UUID,
        variables: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        with self._session_factory() as session:
            variable_id_map: Dict[str, str] = {}
            records: List[SimulationVariable] = []
            for variable in variables:
                record = SimulationVariable(
                    id=uuid.uuid4(),
                    simulation_dataset_id=simulation_dataset_id,
                    bim_space_id=variable.get("bim_space_id"),
                    variable_id=variable["variable_id"],
                    variable_name=variable["variable_name"],
                    unit=variable.get("unit"),
                    frequency=variable.get("frequency"),
                    key=variable.get("key"),
                )
                records.append(record)
                variable_id_map[variable["variable_id"]] = str(record.id)

            for start in range(0, len(records), self._BATCH_SIZE):
                session.add_all(records[start:start + self._BATCH_SIZE])
                session.flush()
            session.commit()
            return variable_id_map

    def delete_by_simulation_dataset_id(self, simulation_dataset_id: uuid.UUID) -> None:
        with self._session_factory() as session:
            session.execute(
                delete(SimulationVariable).where(
                    SimulationVariable.simulation_dataset_id == simulation_dataset_id
                )
            )
            session.commit()

    def list_by_simulation_dataset_id(
        self,
        simulation_dataset_id: uuid.UUID,
    ) -> List[Dict[str, Any]]:
        with self._session_factory() as session:
            stmt = (
                select(SimulationVariable)
                .where(SimulationVariable.simulation_dataset_id == simulation_dataset_id)
                .order_by(SimulationVariable.created_at.asc())
            )
            rows = session.execute(stmt).scalars().all()
            return [self._to_dict(row) for row in rows]

    @staticmethod
    def _to_dict(obj: SimulationVariable) -> Dict[str, Any]:
        return {
            "id": str(obj.id),
            "simulation_dataset_id": str(obj.simulation_dataset_id),
            "bim_space_id": str(obj.bim_space_id) if obj.bim_space_id else None,
            "variable_id": obj.variable_id,
            "variable_name": obj.variable_name,
            "unit": obj.unit,
            "frequency": obj.frequency,
            "key": obj.key,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
        }
