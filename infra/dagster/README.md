# LeColaz Dagster

Self-hosted Dagster runs in the development Compose stack at
[localhost:3000](http://localhost:3000). Backend models and Alembic own the application schema.

## Setup

Follow [environment setup](../../docs/development.md#environment-files).
Compose's `POSTGRES_*` settings must point to the backend's application database.
Dagster and the backend share the MinIO settings in `backend/.env`.

From `infra/`, start dependencies and migrate before loading definitions:

```bash
docker compose up -d --build --wait postgres minio backend
docker compose exec backend alembic upgrade head
docker compose up -d --build dagster-code dagster-webserver dagster-daemon
```

Run `lecolaz_services_smoke_test`, then follow the relevant integration guide:

- [HAM](ham/README.md): reference initialization, daily observations and backfills.
- [OpenMeteo](openmeteo/README.md): sensor registration, raw CSVs and observation loading.

## Shared behavior

Sensors are discovered from PostgreSQL when the code location loads. Reload
**Deployment → Code locations → lecolaz** after registering sensors or editing
names/starting dates. Database/schema errors fail loading rather than hiding assets.

Each observation asset owns one sensor's rows and has UTC daily partitions.
The first day is clipped to `starting_date`; historical days require explicit
backfills. Automation starts stopped and must be enabled in **Sensors**.

Imports upsert values without deleting source-absent rows. Empty imports preserve
existing data but do not mark observation partitions materialized. Such partitions
can make a backfill finish as `COMPLETED_FAILED` even when its runs succeeded.
Pause automation and finish queued work before changing sensor identities or start
dates. Deleting a sensor cascades to its observations; Dagster history remains.

## Storage and maintenance

Dagster metadata uses a separate `DAGSTER_POSTGRES_DB` on the existing PostgreSQL
server. `dagster_storage` holds logs/artifacts; MinIO holds raw ingestion files.

**Existing PostgreSQL volumes** do not rerun initialization scripts. If the Dagster
database is absent, apply the Compose configuration and run from `infra/`:

```bash
docker compose up -d --wait postgres
docker compose exec postgres sh /docker-entrypoint-initdb.d/020-init-dagster.sh
```

For code, YAML or dependency changes, rebuild all three Dagster services using the
last command in Setup. Recreate services after environment changes. A code-location
reload alone does not update files baked into the image.

Before upgrading Dagster, stop active work, back up its database, update pinned
versions, and run `dagster instance migrate` with writers stopped. Back up the
application database and retain `dagster_storage` too. Avoid `docker compose down -v`
unless you intend to delete persistent data.

## Development

- `definitions.py`: resource wiring and database-derived asset catalog.
- `ham/`, `openmeteo/`: each family’s definitions, API client, workflows and mappings.
- `object_storage.py`: partitioned byte IO using the backend's `MinioStore`.
- `backend/app/storage/postgres/`: shared stores; callers own transactions.

See [testing](tests/README.md) for unit, PostgreSQL and deployment checks.
