# app/services/upload_ingestion_service.py

import uuid
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks

from app.services.bim_processing_service import process_bim
from app.services.simulation_processing_service import process_simulation
from app.storage.object.minio import MinioStore
from app.storage.postgres.bim_store import BimStore
from app.storage.postgres.dataset_store import DatasetStore
from app.storage.postgres.simulation_store import SimulationStore


BIM_EXTENSIONS = (".ifc", ".ifczip", ".ifcxml")
ESO_EXTENSIONS = (".eso",)


class UploadIngestionError(Exception):
    pass


def classify_dataset(filename: str) -> tuple[str, str | None]:
    name = (filename or "").lower()
    if name.endswith(BIM_EXTENSIONS):
        return "bim", name.split(".")[-1]
    if name.endswith(ESO_EXTENSIONS):
        return "simulation", "energyplus_eso"
    return "generic", name.split(".")[-1] if "." in name else None


def resolve_dataset_classification(
    filename: str,
    dataset_type: str | None = None,
) -> tuple[str, str | None]:
    inferred_type, inferred_subtype = classify_dataset(filename)
    if dataset_type is None:
        return inferred_type, inferred_subtype
    if dataset_type == inferred_type:
        return inferred_type, inferred_subtype
    raise ValueError(
        f"Provided type '{dataset_type}' does not match file classification '{inferred_type}'"
    )


def is_bim_filename(filename: str) -> bool:
    name = (filename or "").lower()
    return name.endswith(BIM_EXTENSIONS)


def is_energyplus_filename(filename: str) -> bool:
    name = (filename or "").lower()
    return name.endswith(ESO_EXTENSIONS)


def validate_upload_payload(
    *,
    filename: str | None,
    data: bytes,
    dataset_type: str | None,
) -> str:
    normalized_filename = (filename or "").strip()
    if not normalized_filename:
        raise ValueError("Filename is required")
    if not data:
        raise ValueError("Uploaded file is empty")
    if "." not in normalized_filename.strip("."):
        raise ValueError("File extension is required")
    if dataset_type not in (None, "bim", "simulation"):
        raise ValueError("Unsupported dataset type")
    return normalized_filename


def ingest_upload(
    *,
    filename: str,
    content_type: Optional[str],
    data: bytes,
    type: str | None = None,
    bim_dataset_id: uuid.UUID | None = None,
    metadata: Optional[dict] = None,
    background_tasks: Optional[BackgroundTasks] = None,
    object_store: Optional[MinioStore] = None,
    dataset_store: Optional[DatasetStore] = None,
) -> Dict[str, Any]:
    """
    Persists raw uploaded data and registers it as a dataset.
    """
    normalized_filename = validate_upload_payload(
        filename=filename,
        data=data,
        dataset_type=type,
    )
    object_store = object_store or MinioStore()
    dataset_store = dataset_store or DatasetStore()
    bim_store = BimStore()
    simulation_store = SimulationStore()

    dataset_type, subtype = resolve_dataset_classification(filename, type)
    if bim_dataset_id is not None and dataset_type != "simulation":
        raise ValueError("bim_dataset_id is only supported for simulation uploads")
    dataset_id = uuid.uuid4()
    object_key = f"{dataset_type}/{dataset_id}/{normalized_filename}"

    try:
        object_store.put_object(
            object_key=object_key,
            data=data,
            content_type=content_type,
        )
    except Exception as exc:
        raise UploadIngestionError("Failed to store uploaded file") from exc

    try:
        if bim_dataset_id is not None and not bim_store.get_bim_by_id(bim_dataset_id):
            raise ValueError("Referenced BIM dataset not found")
        dataset_store.create_dataset(
            dataset_id=dataset_id,
            dataset_type=dataset_type,
            subtype=subtype,
            filename=normalized_filename,
            object_key=object_key,
            content_type=content_type,
            size_bytes=len(data),
            status="raw",
            source="upload",
            metadata=metadata,
        )
        if dataset_type == "bim":
            bim_store.create_bim_record(
                bim_id=uuid.uuid4(),
                dataset_id=dataset_id,
                filename=normalized_filename,
                format=subtype or "ifc",
                schema=None,
                extra=None,
            )
        if dataset_type == "simulation":
            simulation_store.create_simulation_record(
                simulation_id=uuid.uuid4(),
                dataset_id=dataset_id,
                filename=normalized_filename,
                format=subtype or "eso",
                bim_dataset_id=bim_dataset_id,
                extra=None,
            )
    except Exception as exc:
        try:
            object_store.delete_object(object_key)
        except Exception:
            pass
        raise UploadIngestionError("Failed to register uploaded dataset") from exc

    if dataset_type == "bim":
        if background_tasks is not None:
            background_tasks.add_task(process_bim, dataset_id)
        else:
            process_bim(dataset_id)
    elif dataset_type == "simulation":
        if background_tasks is not None:
            background_tasks.add_task(process_simulation, dataset_id)
        else:
            process_simulation(dataset_id)

    return {
        "dataset_id": str(dataset_id),
        "type": dataset_type,
        "status": "raw",
    }
