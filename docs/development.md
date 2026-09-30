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
docker compose up -d --build
```

The development Compose file runs:

- `postgres`: TimescaleDB/PostgreSQL on host port `5432` by default
- `minio`: MinIO API on host port `9000` by default
- `minio`: MinIO console on host port `9001` by default
- `fuseki`: Apache Jena Fuseki (RDF triple store) on host port `3030` by default
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
- Fuseki UI: `http://localhost:3030/#/`
- Dagster UI: `http://localhost:3000`

## Fuseki

The `fuseki` service hosts the `lecolaz` dataset. Access is split:

- Queries (`/lecolaz/query`, `/lecolaz/sparql`) are open.
- The admin UI data (`/$/**`) and writes (`/lecolaz/update`, `/lecolaz/data`) require HTTP Basic Auth.

Credentials: user `admin`, password `FUSEKI_ADMIN_PASSWORD` from `infra/.env` (`lecolaz` by default).

The backend writes to Fuseki with the same credentials, so `FUSEKI_ADMIN_PASSWORD` must be identical in `infra/.env` and `backend/.env`.

### Ontology schema

The ontology schema lives in `resources/ontology/` and is versioned in git. A `post_start` hook of the `fuseki` service (`infra/fuseki/load-schema.sh`) loads it into the named graph `https://w3id.org/lecolaz/graph/schema` each time Compose starts the `fuseki` container. This needs Docker Compose 2.30 or newer.

The hook may fire before Fuseki is ready, so the script first waits until the `lecolaz` dataset answers on `/$/datasets/lecolaz` (server up and dataset created), then uploads.

The load is an HTTP PUT, so it replaces the schema graph wholesale and does not touch the BIM graphs written by the backend. Changes made to the schema graph through the Fuseki UI are overwritten on the next load: edit the file in git instead.

The hook does not run again on `docker compose up` while `fuseki` is already running. To load a changed schema without restarting anything, call the backend endpoint (also available in Swagger at `http://localhost:8000/docs`):

```bash
curl -X POST http://localhost:8000/ontology/schema/reload
```

It reads the same file (mounted read-only into the backend at `/resources/ontology/`, see `LECO_SCHEMA_PATH`), checks that it exists, is not empty and parses as Turtle, and PUTs it into the schema graph. It returns `{"graph_uri": ..., "triple_count": ...}` on success, 500 if the file is missing, empty or invalid, and 502 if Fuseki rejects the PUT or is unreachable. The same load can also be run inside the Fuseki container with `docker compose exec fuseki bash /init/load-schema.sh`.

To publish a new schema version, edit `resources/ontology/le_colaz_ontology_schema.ttl` (keep the same filename; the version lives in `owl:versionInfo` and git history), commit it, and call the endpoint above.

A failed load does not stop the stack: the hook always reports success, so Fuseki and the backend start normally, possibly with an old or missing schema. The script's messages are printed only when `up` runs in the foreground (without `-d`); they do not appear in `docker compose logs`. After `up -d`, check that the schema loaded by calling the endpoint above: it returns the triple count or the reason it failed. Requests Fuseki rejected (e.g. a Turtle syntax error with its line number) also show in `docker compose logs fuseki`.

### Logging in to the UI

The UI page itself loads without a password, but the dataset list is fetched from the protected `/$/` endpoints. If the browser does not show a login prompt, the UI spins forever.

To log in reliably:

1. Open `http://localhost:3030/$/server` first. The browser shows a login prompt.
2. Enter `admin` and the password above.
3. Open `http://localhost:3030/#/`. The browser remembers the credentials until it is fully closed.

If `/$/server` shows "This site can't be reached" instead of a login prompt, the browser has cached a cancelled or wrong login for `localhost:3030`. Fully close the browser (including background processes) and try again, or use a private/incognito window.

Check that Fuseki is up without a browser:

```bash
curl http://localhost:3030/$/ping
curl -u admin:lecolaz http://localhost:3030/$/server
```

## Dagster workflows
Apply alembic migrations first because Dagster reads the application’s `sensors` table when loading asset definitions. If the schema is already current, Alembic makes no changes.


Set `HAMAPI_API_KEY` in `infra/.env` before starting Dagster; recreate its services
if already running. HAM registration and daily ingestion start automatically.

Review sensor `starting_date` values in PostgreSQL and reload the `lecolaz` code
location if you change them. Backfill historical days from each asset’s partition
view at <http://localhost:3000>.

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
and `minio_data`.

## Practical Commands

```bash
docker compose ps
docker compose logs backend
curl http://localhost:8000/health
```
