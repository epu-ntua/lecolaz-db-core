import uuid
from typing import Any, Dict

from app.storage.postgres.bim_store import BimStore
from app.storage.postgres.dataset_store import DatasetStore


class BimProcessingError(Exception):
    pass


class BimNotFoundError(BimProcessingError):
    pass


class BimConflictError(BimProcessingError):
    pass


def process_bim(dataset_id: uuid.UUID) -> Dict[str, Any]:
    dataset_store = DatasetStore()
    bim_store = BimStore()

    dataset = dataset_store.get_dataset_by_id(dataset_id)
    if not dataset:
        raise BimNotFoundError("Dataset not found")
    if dataset.get("type") != "bim":
        raise BimProcessingError("Dataset is not a BIM dataset")

    existing_bim = bim_store.get_bim_by_dataset_id(dataset_id)
    if existing_bim:
        raise BimConflictError("BIM dataset is already processed")

    subtype = dataset.get("subtype")
    if not subtype:
        raise BimProcessingError("BIM dataset subtype is missing")

    try:
        bim_id = uuid.uuid4()
        bim_store.create_bim_record(
            bim_id=bim_id,
            dataset_id=dataset_id,
            filename=dataset["filename"],
            format=subtype,
            schema=None,
            extra=None,
        )

        updated_dataset = dataset_store.update_dataset_status(
            dataset_id,
            "processed",
        )
        if not updated_dataset:
            raise BimNotFoundError("Dataset not found during BIM status update")

        return {
            "dataset_id": str(dataset_id),
            "bim_id": str(bim_id),
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
