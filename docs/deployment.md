# Deployment

## Current Production Model

```text
Internet
   |
 Nginx
   |---- /        -> built React frontend
   |
   |---- /api/    -> FastAPI on 127.0.0.1:8080

Docker:
  FastAPI
  PostgreSQL / TimescaleDB
  MinIO
```

The production backend port should be bound to localhost rather than publicly exposed. The production Compose file publishes the backend container port using `BACKEND_PORT`, with a default of `8080`. In production `infra/.env`, use a localhost binding such as:

```bash
BACKEND_PORT=127.0.0.1:8080
```

The intended hostname currently discussed is:

```text
lecolaz.epu.ntua.gr
```

Treat this as intended/planned until DNS and server configuration are confirmed. Do not assume DNS, HTTPS, Certbot, authentication, or public deployment are complete unless the server configuration proves it.

## Server Location

The repository currently lives on the production server under approximately:

```text
/home/lecolaz/platform/lecolaz-db-core
```

Do not make scripts depend on this exact path unless the server layout has been confirmed.

## Deployment Workflow

Normal code flow:

```text
Local development
  -> commit / push
  -> GitHub main
  -> production server: git pull
  -> rebuild/restart affected services
```

Development should normally happen locally. The production server should consume code from `main`; it should not be used as the main development environment.

## Backend and Docker Changes

On the production server, from the repository directory:

```bash
git pull origin main
docker compose -f infra/compose.prod.yaml up -d --build
```

Run migrations after deploying backend changes that include database migrations:

```bash
docker compose -f infra/compose.prod.yaml exec backend alembic upgrade head
```

Useful production Compose checks:

```bash
docker compose -f infra/compose.prod.yaml ps
docker compose -f infra/compose.prod.yaml logs
```

## Frontend Changes

The React frontend is built separately and served statically by system Nginx.

On the production server, from the repository directory:

```bash
git pull origin main
cd frontend
npm ci
npm run build
sudo mkdir -p /var/www/lecolaz
sudo rsync -av --delete dist/ /var/www/lecolaz/
```

The Nginx site configuration currently lives under :

```text
/etc/nginx/sites-available/lecolaz
```

It should serve `/var/www/lecolaz` for the frontend and proxy API requests under `/api/` to:

```text
http://127.0.0.1:8080/
```

Do not put server-specific secrets, passwords, tokens, private IP addresses, or certificates into this repository.

## Dev/Prod Compose Files

This repository currently maintains separate Compose files:

- `infra/compose.dev.yaml`
- `infra/compose.prod.yaml`

The development file exposes PostgreSQL, MinIO, the MinIO console, and the backend for local work. It also runs the backend with reload and a source bind mount.

The production file runs PostgreSQL/TimescaleDB, MinIO, and the backend with `restart: unless-stopped`. It does not run the React frontend; production frontend serving is handled by system Nginx.

Because these files are maintained separately, architectural or service changes required in both environments must be reflected in both files.

## Practical Commands

```bash
docker compose -f infra/compose.prod.yaml ps
docker compose -f infra/compose.prod.yaml logs
curl http://127.0.0.1:8080/health
curl http://localhost/api/health
sudo nginx -t
sudo systemctl status nginx
```
