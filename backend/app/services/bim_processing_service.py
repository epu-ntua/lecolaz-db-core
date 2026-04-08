import uuid
from datetime import datetime, timezone
from tempfile import NamedTemporaryFile
from typing import Any, Dict
import ifcopenshell

from app.storage.postgres.bim_store import BimStore
from app.storage.postgres.dataset_store import DatasetStore
from app.storage.object.minio import MinioStore


class BimProcessingError(Exception):
    pass


class BimNotFoundError(BimProcessingError):
    pass


class BimConflictError(BimProcessingError):
    pass


def _safe_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _extract_units(ifc_file: ifcopenshell.file) -> list[dict[str, Any]]:
    projects = ifc_file.by_type("IfcProject")
    if not projects:
        return []

    units_in_context = getattr(projects[0], "UnitsInContext", None)
    units = getattr(units_in_context, "Units", None) or []
    result: list[dict[str, Any]] = []
    for unit in units:
        entry = {"type": unit.is_a()}
        unit_type = getattr(unit, "UnitType", None)
        if unit_type:
            entry["unit_type"] = str(unit_type)
        name = getattr(unit, "Name", None)
        if name:
            entry["name"] = str(name)
        prefix = getattr(unit, "Prefix", None)
        if prefix:
            entry["prefix"] = str(prefix)
        result.append(entry)
    return result


def _extract_quantity(space: Any, quantity_types: tuple[str, ...]) -> float | None:
    for rel in getattr(space, "IsDefinedBy", []) or []:
        if not rel.is_a("IfcRelDefinesByProperties"):
            continue
        definition = getattr(rel, "RelatingPropertyDefinition", None)
        if definition is None or not definition.is_a("IfcElementQuantity"):
            continue
        for quantity in getattr(definition, "Quantities", []) or []:
            if quantity.is_a("IfcQuantityArea") and "IfcQuantityArea" in quantity_types:
                return _safe_float(getattr(quantity, "AreaValue", None))
            if quantity.is_a("IfcQuantityVolume") and "IfcQuantityVolume" in quantity_types:
                return _safe_float(getattr(quantity, "VolumeValue", None))
    return None


def _extract_storeys(ifc_file: ifcopenshell.file) -> list[dict[str, Any]]:
    storeys: list[dict[str, Any]] = []
    for storey in ifc_file.by_type("IfcBuildingStorey"):
        global_id = getattr(storey, "GlobalId", None)
        if not global_id:
            continue
        storeys.append(
            {
                "global_id": global_id,
                "name": getattr(storey, "Name", None),
                "elevation": _safe_float(getattr(storey, "Elevation", None)),
            }
        )
    return storeys


def _resolve_space_storey_global_id(space: Any) -> str | None:
    for rel in getattr(space, "ContainedInStructure", []) or []:
        if not rel.is_a("IfcRelContainedInSpatialStructure"):
            continue
        structure = getattr(rel, "RelatingStructure", None)
        if structure is not None and structure.is_a("IfcBuildingStorey"):
            return getattr(structure, "GlobalId", None)

    for rel in getattr(space, "Decomposes", []) or []:
        if not rel.is_a("IfcRelAggregates"):
            continue
        parent = getattr(rel, "RelatingObject", None)
        if parent is not None and parent.is_a("IfcBuildingStorey"):
            return getattr(parent, "GlobalId", None)

    return None


def _extract_spaces(ifc_file: ifcopenshell.file) -> list[dict[str, Any]]:
    spaces: list[dict[str, Any]] = []
    for space in ifc_file.by_type("IfcSpace"):
        global_id = getattr(space, "GlobalId", None)
        if not global_id:
            continue
        spaces.append(
            {
                "global_id": global_id,
                "name": getattr(space, "LongName", None),
                "raw_name": getattr(space, "Name", None),
                "storey_global_id": _resolve_space_storey_global_id(space),
                "area": _extract_quantity(space, ("IfcQuantityArea",)),
                "volume": _extract_quantity(space, ("IfcQuantityVolume",)),
            }
        )
    return spaces


def _parse_ifc_bytes(data: bytes) -> dict[str, Any]:
    with NamedTemporaryFile(suffix=".ifc", delete=True) as tmp:
        tmp.write(data)
        tmp.flush()
        ifc_file = ifcopenshell.open(tmp.name)

    storeys = _extract_storeys(ifc_file)
    spaces = _extract_spaces(ifc_file)
    return {
        "schema": getattr(ifc_file, "schema", None),
        "units": _extract_units(ifc_file),
        "storeys": storeys,
        "spaces": spaces,
        "stats": {
            "storeys": len(storeys),
            "spaces": len(spaces),
            "entities": sum(1 for _ in ifc_file),
        },
    }


def process_bim(dataset_id: uuid.UUID) -> Dict[str, Any]:
    dataset_store = DatasetStore()
    bim_store = BimStore()
    object_store = MinioStore()

    dataset = dataset_store.get_dataset_by_id(dataset_id)
    if not dataset:
        raise BimNotFoundError("Dataset not found")
    if dataset.get("type") != "bim":
        raise BimProcessingError("Dataset is not a BIM dataset")

    bim_dataset = bim_store.get_bim_by_dataset_id(dataset_id)
    if not bim_dataset:
        raise BimNotFoundError("BIM dataset not found")

    try:
        dataset_store.update_dataset_status(
            dataset_id,
            "processing",
            metadata_patch={"processing_error": None},
        )

        model_data = object_store.get_object_bytes(dataset["object_key"])
        parsed = _parse_ifc_bytes(model_data)
        processed_at = datetime.now(timezone.utc)

        bim_store.update_bim_record(
            dataset_id,
            schema=parsed["schema"],
            stats=parsed["stats"],
            units=parsed["units"],
            extra=None,
        )
        bim_store.replace_spatial_structure(
            bim_dataset_id=uuid.UUID(bim_dataset["id"]),
            storeys=parsed["storeys"],
            spaces=parsed["spaces"],
        )

        updated_dataset = dataset_store.update_dataset_status(
            dataset_id,
            "processed",
            metadata_patch={"processing_error": None, "processed_at": processed_at.isoformat()},
        )
        if not updated_dataset:
            raise BimNotFoundError("Dataset not found during BIM status update")

        return {
            "dataset_id": str(dataset_id),
            "bim_id": bim_dataset["id"],
            "status": updated_dataset["status"],
        }
    except Exception as exc:
        dataset_store.update_dataset_status(
            dataset_id,
            "failed",
            metadata_patch={"processing_error": str(exc)},
        )
        if isinstance(exc, BimProcessingError):
            raise
        raise BimProcessingError(str(exc)) from exc
