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

From the repository root:

```bash
docker compose -f infra/compose.dev.yaml up -d --build
```

The development Compose file runs:

- `postgres`: TimescaleDB/PostgreSQL on host port `5432` by default
- `minio`: MinIO API on host port `9000` by default
- `minio`: MinIO console on host port `9001` by default
- `backend`: FastAPI on host port `8000` by default

The backend development container runs Uvicorn with `--reload` and bind-mounts `backend/` into `/app`, so backend source changes are picked up without rebuilding the image in most cases.

Useful local URLs:

- Frontend dev server: `http://localhost:5173`
- FastAPI: `http://localhost:8000`
- FastAPI docs: `http://localhost:8000/docs`
- Backend health check: `http://localhost:8000/health`
- MinIO console: `http://localhost:9001`

## Frontend

Run the frontend locally in a separate terminal:

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
docker compose -f infra/compose.dev.yaml exec backend alembic upgrade head
```

This applies the database schema migrations in `backend/alembic/versions/`.

## Stop Services

Stop local services without deleting persisted data:

```bash
docker compose -f infra/compose.dev.yaml down
```

Be careful with volumes:

```bash
docker compose -f infra/compose.dev.yaml down -v
```

`down -v` removes Docker volumes and therefore deletes locally persisted PostgreSQL/TimescaleDB and MinIO data.

## Practical Commands

```bash
docker compose -f infra/compose.dev.yaml ps
docker compose -f infra/compose.dev.yaml logs backend
curl http://localhost:8000/health
```
