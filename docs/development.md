# Development

## Development model

Le’Colaz is developed locally with **Vite running directly on the host** for fast React hot module replacement, and **FastAPI running in Docker with `--reload`**. PostgreSQL/TimescaleDB, MinIO, Fuseki, and all three Dagster services also run in Docker.

The local setup does **not** need Caddy, a containerized production frontend, or Portainer. These are production services in `infra/compose.prod.yaml`.

## Prerequisites

- Docker with Docker Compose **2.30+** (required by Fuseki `post_start`).
- Node.js 22 and npm (matching the frontend Docker build).
- Git and a terminal (Windows PowerShell works).

## Environment files

From the repository root, create local `.env` files from the tracked examples if they do not already exist:

**PowerShell:**

```powershell
Copy-Item infra/.env.example infra/.env
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

**Bash:**

```bash
cp infra/.env.example infra/.env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Do not overwrite existing `.env` files that already contain working settings.

| File | Purpose |
|---|---|
| `infra/.env` | Compose project `lecolaz-local`, infrastructure credentials/ports, Dagster and ingestion settings |
| `backend/.env` | FastAPI configuration and internal Docker service endpoints |
| `frontend/.env` | Vite build/dev-time variables and optional admin-page links |

The `.env.example` files are the shared, tracked reference for local and production, with comments identifying differences. Keep actual `.env` files out of Git. Credentials must agree across files, particularly PostgreSQL, MinIO and Fuseki.

Typical backend Docker hostnames: `postgres:5432`, `minio:9000`, `fuseki:3030`, `dagster-webserver:3000`. These work **inside containers**; direct host-side processes use forwarded localhost ports instead.

`frontend/src/api/client.ts` currently uses `http://localhost:8000` in development and `/api` in production. The example `VITE_API_BASE_URL` setting is currently unused by this API client.

## Start local development

Run commands from the **repository root** in VS Code / PowerShell.

**Terminal 1 — Docker backend and services:**

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml up -d --build
```

For subsequent ordinary starts (without rebuilding images):

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml up -d
```

FastAPI runs with `--reload` and a bind mount of the local `backend/` folder, so most Python source edits take effect automatically without rebuilding the image. Dependency or Dockerfile changes may still require `--build`.

**Terminal 2 — React/Vite frontend:**

```powershell
cd frontend
npm ci
npm run dev
```

`npm ci` is primarily needed on first setup or when dependencies change. For daily work, `npm run dev` is sufficient.

If Vite reports that port 5173 is occupied and uses 5174, check for another running Vite/Node server. The backend CORS setup is currently intended for `http://localhost:5173`, so prefer keeping that port rather than silently using a different one.

## Local services and URLs

| Service | URL / port |
|---|---|
| React / Vite | http://localhost:5173 |
| FastAPI | http://localhost:8000 |
| Swagger API docs | http://localhost:8000/docs |
| Backend health | http://localhost:8000/health |
| PostgreSQL / TimescaleDB | localhost:5432 |
| MinIO API | http://localhost:9000 |
| MinIO console | http://localhost:9001 |
| Fuseki UI | http://localhost:3030/#/ |
| Dagster UI | http://localhost:3000 |

Docker services: `postgres`, `minio`, `fuseki`, `backend`, `dagster-code`, `dagster-webserver`, and `dagster-daemon`.

## Fuseki and ontology schema

Fuseki hosts the `lecolaz` dataset. Query endpoints (such as `/lecolaz/query` and `/lecolaz/sparql`) are open; administration (`/$/**`) and writes (`/lecolaz/update`, `/lecolaz/data`) require HTTP Basic authentication. The username is `admin`; the password comes from `FUSEKI_ADMIN_PASSWORD` in `infra/.env` and must match `backend/.env`.

The ontology is versioned at `resources/ontology/le_colaz_ontology_schema.ttl`. The Fuseki service's `post_start` hook invokes `infra/fuseki/load-schema.sh`, waits for the dataset and uploads the schema via HTTP PUT to the named graph `https://w3id.org/lecolaz/graph/schema`. This replaces only the schema graph, **not** BIM graphs. Do not edit the schema manually in the Fuseki UI; edits can be overwritten by the next load.

The hook does not rerun if Fuseki remains up. Reload ontology changes through the backend:

```powershell
curl.exe -X POST http://localhost:8000/ontology/schema/reload
```

The endpoint validates the Turtle file and reports the graph URI/triple count on success. A failed schema load does not prevent backend startup, so explicitly check this response after changes. Fuseki logs can also reveal parser/rejection errors.

For the UI's protected dataset list, visit `http://localhost:3030/$/server` first and log in with `admin` and your configured password, then open `http://localhost:3030/#/`. If browser credentials are cached incorrectly, try a private window.

## Dagster workflows

The development Compose stack runs three Dagster services: `dagster-code` (definitions/execution), `dagster-webserver` (UI), and `dagster-daemon` (automation and run coordination). Dagster uses a separate database within the existing PostgreSQL instance, controlled by `DAGSTER_POSTGRES_USER`, `DAGSTER_POSTGRES_PASSWORD`, and `DAGSTER_POSTGRES_DB` in `infra/.env`.

Fresh database volumes initialize Dagster's user/database through the bundled initialization script. For an **existing** PostgreSQL volume that predates Dagster, initialize them after PostgreSQL starts:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml exec -T postgres sh /docker-entrypoint-initdb.d/020-init-dagster.sh
```

FastAPI applies Alembic migrations before starting Uvicorn. Set `HAMAPI_API_KEY` in `infra/.env` for HAM-accessed data; Compose passes it to the backend and Dagster services. OpenMeteo ingestion does not require an API key. Changes to environment variables normally require recreating affected containers.

Daily ingestion is enabled by default. Set sensor start dates during registration; use Dagster's partition views for historical backfills. See the [Dagster guide](../infra/dagster/README.md) for workflow details.

## Database migrations

The backend container runs `alembic upgrade head` before Uvicorn. If migrations fail, the backend will not start normally. Inspect:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml logs backend
```

## Mock data

Modular components have no real data source yet. `backend/mock_data/` holds three mock components (one per component class) with their draft DPP, photo, placeholder QR image and, for the interior wall, an IFC file. The seed uploads the files to MinIO and inserts the `modular_components` rows. It never runs automatically, including in production; run it once after migrations have created the table:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml exec backend python -m mock_data.seed_modular_components
```

It is safe to re-run: component ids are fixed, so files are overwritten and rows are updated rather than duplicated. Edit a component's `dpp.json` and re-run the seed to apply the change.

## Everyday commands

From the **repository root**:

```powershell
# Service status
docker compose --env-file infra/.env -f infra/compose.yaml ps

# Backend and other logs
docker compose --env-file infra/.env -f infra/compose.yaml logs -f backend

# Health check
curl.exe http://localhost:8000/health

# Stop local services, retain volumes
docker compose --env-file infra/.env -f infra/compose.yaml down
```

To run frontend quality checks, from `frontend/`:

```powershell
npm run build
npm run lint
npm run typecheck
npm run format:check
```

**Warning:** `docker compose ... down -v` deletes local project volumes, including PostgreSQL application/Dagster databases, `dagster_storage` artifacts, MinIO data, and any other Compose-defined volumes. Use only when you deliberately want to reset local data.

## Production separation and planned administration URLs

Local development remains unchanged: **Vite on the Windows host, FastAPI with reload in Docker, and supporting services in the local Compose project**. Do not start the production `caddy`, `frontend` or `portainer` containers during normal development.

The production configuration serves the platform through Caddy at `https://lecolaz.epu.ntua.gr`, with Portainer at `/portainer/`. Dedicated service subdomains are planned but are not configured in the current Caddyfile. See the [Deployment guide](deployment.md).
