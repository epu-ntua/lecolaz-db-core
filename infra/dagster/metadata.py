"""Dagster presentation of ingestion diagnostics and model-owned table schemas."""

from contextlib import contextmanager
from datetime import datetime
from time import perf_counter

from dagster import MetadataValue, TableColumn, TableColumnConstraints, TableRecord, TableSchema
from sqlalchemy import Table
from sqlalchemy.dialects import postgresql

from infra.dagster.ham.observation_values import PreparedObservations


@contextmanager
def measure_duration(metadata: dict, name: str):
    """Measure a completed phase, including transaction commit when inside the block."""
    started = perf_counter()
    yield
    metadata[name] = perf_counter() - started


def table_metadata(table: Table, row_scope: str, write_semantics: str) -> dict:
    """Describe the expected model schema without querying the deployed database."""
    schema = table.schema or "public"
    return {
        "dagster/table_name": f"{schema}.{table.name}",
        "dagster/column_schema": MetadataValue.table_schema(TableSchema(columns=[
            TableColumn(
                name=column.name,
                type=str(column.type.compile(dialect=postgresql.dialect())),
                description=column.comment,
                constraints=TableColumnConstraints(nullable=column.nullable),
            )
            for column in table.columns
        ])),
        "row_scope": row_scope,
        "write_semantics": write_semantics,
        "schema_source": "SQLAlchemy model (expected schema; not database introspection)",
    }


READING_SUMMARY_SCHEMA = TableSchema(columns=[
    TableColumn("reading_key", "string"),
    TableColumn("selected_rows", "int"),
    TableColumn("null_values", "int"),
    TableColumn("first_timestamp", "string", description="Earliest valid incoming timestamp (UTC ISO 8601)."),
    TableColumn("last_timestamp", "string", description="Latest valid incoming timestamp (UTC ISO 8601)."),
    TableColumn("minimum", "float"),
    TableColumn("maximum", "float"),
])


def observation_metadata(prepared: PreparedObservations) -> dict:
    """Use typed metadata for timestamps, lists, and the per-reading summary."""
    metadata = dict(prepared.diagnostics)
    metadata["ignored_series_keys"] = MetadataValue.json(metadata["ignored_series_keys"])
    for name in ("first_observation_at", "last_observation_at"):
        if name in metadata:
            metadata[name] = MetadataValue.timestamp(metadata[name])
    metadata["reading_summary"] = MetadataValue.table(
        records=[TableRecord({
            name: value.isoformat() if isinstance(value, datetime) else value
            for name, value in reading.items()
        }) for reading in prepared.reading_summary],
        schema=READING_SUMMARY_SCHEMA,
    )
    return metadata
