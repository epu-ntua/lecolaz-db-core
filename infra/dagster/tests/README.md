# Dagster tests

[Overview](../README.md)

From the repository root, with `infra/dagster/requirements.txt` installed:

```bash
PYTHONPATH=backend:. python -m unittest discover -s infra/dagster/tests -v
```

Or use the pinned image:

```bash
docker build -t lecolaz-dagster:1.13.23 -f infra/dagster/Dockerfile .
docker run --rm lecolaz-dagster:1.13.23 python -m unittest discover -s infra/dagster/tests -v
```

Tests use fixture API responses. OpenMeteo fixtures cover `1334/564/232` on
2026-01-01 (144 observations), captured on 2026-09-30. PostgreSQL tests require
`HAMAPI_TEST_POSTGRES_DSN` pointing to a migrated test database; they use
session-local temporary tables. Without that setting, database tests skip.

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
test_compose exec -T -e HAMAPI_TEST_POSTGRES_DSN=postgresql+psycopg://fixture:fixture@postgres:5432/dagster_fixture dagster-code python -m unittest discover -s infra/dagster/tests -v
test_compose exec -T dagster-code python -m infra.dagster.tests.check_deployment
test_compose restart dagster-code dagster-webserver dagster-daemon
test_compose up -d --wait
test_compose exec -T dagster-code python -m infra.dagster.tests.check_deployment --after-restart
test_compose down
```

This checks queued execution, HAM initialization/backfills, empty results,
idempotency, catalog reloads and persistence across restarts. `down` keeps test
volumes; remove those separately only when their data is no longer needed.
