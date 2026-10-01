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
  Fuseki (post_start hook loads the ontology schema)
  Dagster (code server, webserver, daemon)
```

The production backend port should be bound to localhost rather than publicly exposed. The production Compose file publishes the backend container port using `BACKEND_PORT`, with a default of `8080`. In production `infra/.env`, use a localhost binding such as:

```bash
BACKEND_PORT=127.0.0.1:8080
```

The production hostname now resolves to the production server:

```text
https://lecolaz.epu.ntua.gr
```

UFW allows public traffic on ports `80` and `443`. PostgreSQL, MinIO, and FastAPI internal ports remain non-public.

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

Use Docker Compose 2.30+ and keep the existing production environment-file and
project settings. Run commands from the repository directory, proceeding only
when the previous step succeeds.

### First Dagster deployment — once per production database

In `infra/.env`, set `DAGSTER_POSTGRES_USER` and
`DAGSTER_POSTGRES_DB` to names distinct from the application user/database, and set a strong
`DAGSTER_POSTGRES_PASSWORD`; production Compose rejects an unset or empty value.
Set `HAMAPI_API_KEY` to enable HAM registration;
OpenMeteo needs no API key.

Existing PostgreSQL volumes do not rerun initialization scripts. Run this sequence
once when introducing Dagster to production; its role and database persist across
deployments and restarts. Fresh volumes initialize them automatically, and the
explicit initialization below is safe to repeat.

```bash
git pull origin main

# Start PostgreSQL with the updated configuration.
docker compose -f infra/compose.prod.yaml up -d --wait postgres

# ONE TIME: create Dagster's role and database on existing volumes.
docker compose -f infra/compose.prod.yaml exec -T postgres \
  sh /docker-entrypoint-initdb.d/020-init-dagster.sh

# Build the backend and migrate before starting Dagster.
docker compose -f infra/compose.prod.yaml build backend
docker compose -f infra/compose.prod.yaml run --rm --no-deps backend \
  alembic upgrade head

# Start the complete stack.
docker compose -f infra/compose.prod.yaml up -d --build --wait
```

### Routine deployments

When there are no new application database migrations, only run:

```bash
git pull origin main
docker compose -f infra/compose.prod.yaml up -d --build --wait
```

**Only when the release includes new Alembic migrations**, insert these commands
between `git pull` and `up`:

```bash
docker compose -f infra/compose.prod.yaml build backend
docker compose -f infra/compose.prod.yaml run --rm --no-deps backend \
  alembic upgrade head
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

The Nginx site configuration currently lives under:

```text
/etc/nginx/sites-available/lecolaz
```

It serves `/var/www/lecolaz` for the frontend and proxies API requests under `/api/` to:

```text
http://127.0.0.1:8080/
```

HTTPS has been configured successfully with Certbot. HTTP should redirect to HTTPS, and the deployed platform is available at:

```text
https://lecolaz.epu.ntua.gr
```

Production uploads through the deployed frontend use the server-side production stack: files go to MinIO, and metadata/records go to PostgreSQL.

Do not put server-specific secrets, passwords, tokens, private IP addresses, or certificates into this repository.

## Dev/Prod Compose Files

This repository currently maintains separate Compose files:

- `infra/compose.yaml`
- `infra/compose.prod.yaml`

The development file exposes PostgreSQL, MinIO, the MinIO console, and the backend for local work. It also runs the backend with reload and a source bind mount.

The production file runs PostgreSQL/TimescaleDB, MinIO, Fuseki, and the backend with `restart: unless-stopped`. Fuseki is not exposed on a host port. A `post_start` hook of the `fuseki` service loads the ontology schema from `resources/ontology/` each time Compose starts the container; this needs Docker Compose 2.30 or newer on the server. A failed load does not stop the deploy and `up -d` does not report it, so after each deploy, and after a `git pull` that changes the schema, run `curl -X POST http://127.0.0.1:8080/ontology/schema/reload` on the server: it reloads the schema from `resources/ontology/` (mounted read-only into the backend) and returns the triple count or the reason it failed. Production `infra/.env` must set `FUSEKI_ADMIN_PASSWORD`, with the same value as in `backend/.env`. Compose refuses to start if it is missing. The Fuseki image writes the password into `shiro.ini` inside the `fuseki_data` volume on first start; changing `FUSEKI_ADMIN_PASSWORD` afterwards has no effect until the `admin=` line in `/fuseki/shiro.ini` is updated and Fuseki is restarted. It does not run the React frontend; production frontend serving is handled by system Nginx.

Shared Dagster service changes apply to both environments; other architectural or
service changes must be reflected in both Compose files.

SSH port forwarding is no longer needed for normal frontend access. It can still be used for debugging internal services.

## Practical Commands

```bash
docker compose -f infra/compose.prod.yaml ps
docker compose -f infra/compose.prod.yaml logs
curl http://127.0.0.1:8080/health
curl http://localhost/api/health
curl -I http://lecolaz.epu.ntua.gr
curl -I https://lecolaz.epu.ntua.gr
sudo nginx -t
sudo systemctl status nginx
```
