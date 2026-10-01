"""Dagster presentation of ingestion diagnostics and model-owned table schemas."""

from contextlib import contextmanager
from time import perf_counter

from sqlalchemy import Table
from sqlalchemy.dialects import postgresql

from dagster import (
    MetadataValue,
    TableColumn,
    TableColumnConstraints,
    TableSchema,
)


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
        "dagster/column_schema": MetadataValue.table_schema(
            TableSchema(
                columns=[
                    TableColumn(
                        name=column.name,
                        type=str(column.type.compile(dialect=postgresql.dialect())),
                        description=column.comment,
                        constraints=TableColumnConstraints(nullable=column.nullable),
                    )
                    for column in table.columns
                ]
            )
        ),
        "row_scope": row_scope,
        "write_semantics": write_semantics,
        "schema_source": "SQLAlchemy model (expected schema; not database introspection)",
    }
