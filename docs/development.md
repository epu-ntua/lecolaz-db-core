# Development

## Prerequisites

- Docker with Docker Compose
- Node.js and npm for the frontend

## Environment Files

From the repository root:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
cp infra/.env.example infra/.env
```

Responsibilities:

- `backend/.env`: FastAPI, database, and object-storage configuration.
- `frontend/.env`: Vite frontend variables such as `VITE_API_BASE_URL`.
- `infra/.env`: Docker Compose infrastructure settings and local credentials.

```sql
Never commit real .env files or production credentials.
```

## Start Docker Services

Local Docker Compose commands are run from the `infra` directory. `compose.yaml` is the default development configuration, so no `-f` argument is required.

For an existing PostgreSQL volume without Dagster metadata, first follow
[existing-volume setup](../infra/dagster/README.md#storage-and-maintenance).

```bash
cd infra
docker compose up -d --build --wait postgres minio backend
docker compose exec backend alembic upgrade head
docker compose up -d --build dagster-code dagster-webserver dagster-daemon
```

Migrate first because Dagster reads the application’s `sensors` table when loading
asset definitions. If the schema is already current, Alembic makes no changes.

The development Compose file runs:

- `postgres`: TimescaleDB/PostgreSQL on host port `5432` by default
- `minio`: API on host port `9000`, console on `9001` by default
- `backend`: FastAPI on host port `8000` by default
- `dagster-webserver`: Dagster UI on localhost port `3000` by default
- `dagster-daemon`: automation evaluation and queued-run coordination
- `dagster-code`: asset definitions and run execution

The backend development container runs Uvicorn with `--reload` and bind-mounts `backend/` into `/app`, so backend source changes are picked up without rebuilding the image in most cases.

Useful local URLs:

- Frontend dev server: `http://localhost:5173`
- FastAPI: `http://localhost:8000`
- FastAPI docs: `http://localhost:8000/docs`
- Backend health check: `http://localhost:8000/health`
- MinIO console: `http://localhost:9001`
- Dagster UI: `http://localhost:3000`

## Dagster workflows

1. Set `HAMAPI_API_KEY` in `infra/.env` before starting Dagster; recreate its services if already running.
2. Open <http://localhost:3000> and run `hamapi_initialize`.
3. Review sensor `starting_date` values in PostgreSQL, then reload the `lecolaz` code location.
4. Enable `hamapi_observation_automation` for daily ingestion; backfill historical days from each asset’s partition view.

See the [Dagster guide](../infra/dagster/README.md) for details.

## Frontend

Run the frontend locally in a separate terminal. From the repository root:

```bash
cd frontend
npm install
npm run dev
```

Useful frontend commands:

```bash
npm run build
npm run lint
npm run typecheck
npm run format:check
```

Note: `frontend/.env.example` defines `VITE_API_BASE_URL`, but the current frontend API client is implemented in `frontend/src/api/client.ts`. Check that file when changing API base URL behavior.

## Database Migrations

Apply Alembic migrations to the local development database:

```bash
docker compose exec backend alembic upgrade head
```

This applies the database schema migrations in `backend/alembic/versions/`.

## Stop Services

Stop local services without deleting persisted data:

```bash
docker compose down
```

Be careful with volumes:

```bash
docker compose down -v
```

`down -v` removes this Compose project’s volumes: `postgres_data` (both application
and Dagster databases in one PostgreSQL instance), `dagster_storage` (logs/artifacts),
and `minio_data`. Docker images are retained.

## Practical Commands

```bash
docker compose ps
docker compose logs backend
curl http://localhost:8000/health
```
