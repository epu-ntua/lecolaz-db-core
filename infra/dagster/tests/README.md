# Dagster tests

[Overview](../README.md)

From the repository root, with `backend/requirements.txt` and
`infra/dagster/requirements.txt` installed and
`POSTGRES_DSN` set (as in `backend/.env`). The stores import the backend session
factory; this creates an engine but does not connect to the database:

```bash
PYTHONPATH=backend:. python -m unittest discover -s infra/dagster/tests -v
```

For containerized tests, use the full deployment check below. The suite needs
backend modules and dependencies absent from the Dagster runtime image.

Tests use fixture API responses. OpenMeteo fixtures cover `1334/564/232` on
2026-01-01 (144 observations), captured on 2026-09-30. PostgreSQL tests require
`HAMAPI_TEST_POSTGRES_DSN` pointing to a migrated test database; they use
session-local temporary tables. Without that setting, database tests skip.

Registration backfill integration tests use temporary Dagster SQLite storage and
the real GraphQL schema without external services or a daemon:

```bash
PYTHONPATH=backend:. python -m unittest infra.dagster.tests.test_sensor_backfill -v
```

They cover arbitrary asset names and stage counts, downstream replay, active
backfill/run exclusion, pagination, repeat registration, static/unpartitioned
assets, and ambiguous submission failures. Run them with the pinned Dagster
version when upgrading the GraphQL dependency.

## Full deployment check

Use this disposable project with Compose 2.30+. Never substitute the normal
application project name. From the repository root:

```bash
test_compose() {
  docker compose --env-file infra/.env.example -p lecolaz-dagster-test \
    -f infra/compose.yaml -f infra/dagster/tests/compose.yaml "$@"
}
test_compose up -d --build --wait postgres minio backend
test_compose exec -T backend alembic upgrade head
test_compose up -d --build --wait
test_compose exec -T -w /opt/lecolaz -e HAMAPI_TEST_POSTGRES_DSN=postgresql+psycopg://fixture:fixture@postgres:5432/dagster_fixture backend python -m unittest discover -s infra/dagster/tests -v
test_compose exec -T dagster-code python -m infra.dagster.tests.check_deployment
test_compose restart dagster-code dagster-webserver dagster-daemon
test_compose up -d --wait
test_compose exec -T dagster-code python -m infra.dagster.tests.check_deployment --after-restart
test_compose down
```

This checks queued execution, HAM initialization/backfills, empty results,
idempotency, catalog reloads and persistence across restarts. `down` keeps test
volumes; remove those separately only when their data is no longer needed.
