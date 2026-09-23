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

The backend development container runs Uvicorn with `--reload` and bind-mounts `backend/` into `/app`, so backend source changes are picked up without rebuilding the image in most cases.

Useful local URLs:

- Frontend dev server: `http://localhost:5173`
- FastAPI: `http://localhost:8000`
- FastAPI docs: `http://localhost:8000/docs`
- Backend health check: `http://localhost:8000/health`
- MinIO console: `http://localhost:9001`
- Fuseki UI: `http://localhost:3030/#/`

## Fuseki

The `fuseki` service hosts the `lecolaz` dataset. Access is split:

- Queries (`/lecolaz/query`, `/lecolaz/sparql`) are open.
- The admin UI data (`/$/**`) and writes (`/lecolaz/update`, `/lecolaz/data`) require HTTP Basic Auth.

Credentials: user `admin`, password `FUSEKI_ADMIN_PASSWORD` from `infra/.env` (`lecolaz` by default).

The backend writes to Fuseki with the same credentials, so `FUSEKI_ADMIN_PASSWORD` must be identical in `infra/.env` and `backend/.env`.

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

`down -v` removes Docker volumes and therefore deletes locally persisted PostgreSQL/TimescaleDB and MinIO data.

## Practical Commands

```bash
docker compose ps
docker compose logs backend
curl http://localhost:8000/health
```
