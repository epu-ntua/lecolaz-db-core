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

    bim_dataset = bim_store.get_bim_by_dataset_id(dataset_id)
    if not bim_dataset:
        raise BimNotFoundError("BIM dataset not found")

    try:
        updated_dataset = dataset_store.update_dataset_status(
            dataset_id,
            "processed",
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
