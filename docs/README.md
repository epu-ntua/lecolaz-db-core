# LeColaz Platform Documentation

LeColaz Platform is a web application repository with a FastAPI backend, a React/Vite frontend, and Docker Compose infrastructure for local and production runtime services.

The current implemented stack includes:

- React / Vite frontend
- FastAPI backend
- PostgreSQL / TimescaleDB
- MinIO object storage
- Docker / Docker Compose
- Nginx for production frontend serving and reverse proxying

## Repository Layout

```text
backend/
frontend/
infra/
```

- `backend/`: FastAPI application, API routers, services, database models, storage adapters, and Alembic migrations.
- `frontend/`: React/Vite application, TypeScript source, UI components, frontend routes, and static assets.
- `infra/`: Docker Compose files and infrastructure support files for PostgreSQL/TimescaleDB, MinIO, and the backend container.

## Documentation

- [Development](development.md): local environment setup, Docker services, frontend workflow, migrations, and useful local commands.
- [Deployment](deployment.md): current production model, manual deployment workflow, Nginx notes, and operational checks.

## Environment Files

Create environment files from the committed examples:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
cp infra/.env.example infra/.env
```

Responsibilities:

- `backend/.env`: FastAPI, database, and object-storage configuration. It contains values such as `POSTGRES_DSN`, MinIO endpoint, MinIO credentials, and bucket name.
- `frontend/.env`: Vite frontend variables. The committed template currently defines `VITE_API_BASE_URL`.
- `infra/.env`: Docker Compose infrastructure settings and local credentials, including Compose project name, database settings, MinIO settings, and published ports.

Production uses the same filenames with production-specific values.

```sql
Never commit real .env files or production credentials.
```

The real `.env` files are ignored by Git. Keep `.env.example` files committed as templates.

## Notes

- This repository currently maintains separate Compose files: `infra/compose.dev.yaml` and `infra/compose.prod.yaml`.
- Architectural or service changes required in both environments must be reflected in both Compose files.
- Linux filenames and paths are case-sensitive. Imports that work accidentally on Windows can fail during a Linux production build if the casing does not exactly match the file on disk.
- Do not commit generated build output such as `frontend/dist/`.
