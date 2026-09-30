"""Dagster metadata for HAM observation diagnostics."""

from datetime import datetime

from dagster import MetadataValue, TableColumn, TableRecord, TableSchema
from infra.dagster.ham.observation_values import PreparedObservations

READING_SUMMARY_SCHEMA = TableSchema(
    columns=[
        TableColumn("reading_key", "string"),
        TableColumn("selected_rows", "int"),
        TableColumn("null_values", "int"),
        TableColumn(
            "first_timestamp",
            "string",
            description="Earliest valid incoming timestamp (UTC ISO 8601).",
        ),
        TableColumn(
            "last_timestamp",
            "string",
            description="Latest valid incoming timestamp (UTC ISO 8601).",
        ),
        TableColumn("minimum", "float"),
        TableColumn("maximum", "float"),
    ]
)


def observation_metadata(prepared: PreparedObservations) -> dict:
    """Use typed metadata for timestamps, lists, and the per-reading summary."""
    metadata = dict(prepared.diagnostics)
    metadata["ignored_series_keys"] = MetadataValue.json(metadata["ignored_series_keys"])
    for name in ("first_observation_at", "last_observation_at"):
        if name in metadata:
            metadata[name] = MetadataValue.timestamp(metadata[name])
    metadata["reading_summary"] = MetadataValue.table(
        records=[
            TableRecord(
                {
                    name: value.isoformat() if isinstance(value, datetime) else value
                    for name, value in reading.items()
                }
            )
            for reading in prepared.reading_summary
        ],
        schema=READING_SUMMARY_SCHEMA,
    )
    return metadata
