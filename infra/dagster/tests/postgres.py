"""Isolated PostgreSQL tables shared by the database integration tests."""

import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool


class PostgresTestCase(unittest.TestCase):
    def setUp(self):
        dsn = os.environ.get("HAMAPI_TEST_POSTGRES_DSN")
        if not dsn:
            self.skipTest("Set HAMAPI_TEST_POSTGRES_DSN to test PostgreSQL")

        # Reuse one connection: its temporary tables shadow the migrated application
        # tables and are removed on dispose. No persistent application rows change.
        self.engine = create_engine(dsn, poolclass=StaticPool)
        self.addCleanup(self.engine.dispose)
        with self.engine.begin() as connection:
            for table in ("sensors", "observation_types", "observation_values"):
                connection.exec_driver_sql(
                    f"CREATE TEMP TABLE {table} (LIKE public.{table} INCLUDING ALL)"
                )
            # LIKE does not copy foreign keys; restore them against the temp tables.
            connection.exec_driver_sql(
                "ALTER TABLE observation_values ADD FOREIGN KEY (sensor_id) "
                "REFERENCES sensors(id) ON DELETE CASCADE"
            )
            connection.exec_driver_sql(
                "ALTER TABLE observation_values ADD FOREIGN KEY (observation_type_id) "
                "REFERENCES observation_types(id) ON DELETE CASCADE"
            )
